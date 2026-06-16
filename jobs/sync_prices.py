#!/usr/bin/env python
"""
Sync prices from EODHD — three phases (M15).

Phase 1 (AU bulk):  ASX bulk endpoint — single API call, all active AU symbols.
Phase 2 (US):       Per-symbol targeted fetch for US holdings in current_holdings.
Phase 3 (FX):       AUDUSD.FOREX daily rate — fetched from earliest US acquisition
                    date so all historical lots have a rate for Div 775 calculations.

Default: yesterday for all phases.
Backfill: --from YYYY-MM-DD loops each weekday at 4 req/s (AU bulk only).

Usage:
    python jobs/sync_prices.py
    python jobs/sync_prices.py --from 2024-01-01
"""
import argparse
import asyncio
import logging
from datetime import date, timedelta

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.prices import (
    classify_sync_completeness,
    fetch_and_upsert_bulk,
    fetch_and_upsert_us_symbol,
    to_fx_rows,
    upsert_fx_rates,
)
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def get_active_universe() -> set[str]:
    async with acquire() as conn:
        rows = await conn.fetch("SELECT symbol FROM universe WHERE is_active")
        return {r["symbol"] for r in rows}


async def _sync_us_prices(
    us_symbols: list[str],
    from_date: date,
    client,
    conn,
) -> int:
    """Phase 2: fetch + upsert prices for each US holding concurrently.

    Uses asyncio.gather with return_exceptions=True — a single ticker failure
    does not abort the run (mirrors ingest_news pattern).
    """
    if not us_symbols:
        return 0
    results = await asyncio.gather(
        *[
            fetch_and_upsert_us_symbol(sym, from_date, client, conn)
            for sym in us_symbols
        ],
        return_exceptions=True,
    )
    total = 0
    for sym, res in zip(us_symbols, results, strict=False):
        if isinstance(res, Exception):
            log.warning("sync_prices US: %s failed: %s", sym, res)
        else:
            total += res
    return total


async def _sync_fx_rates(from_date: date, client, conn) -> int:
    """Phase 3: fetch AUDUSD daily rates from from_date to today, upsert fx_rates."""
    raw = await client.daily_prices("AUDUSD.FOREX", from_date=from_date.isoformat())
    rows = to_fx_rows(raw, pair="AUDUSD")
    n = await upsert_fx_rates(conn, rows)
    log.info("sync_prices FX: %d AUDUSD rows from %s", n, from_date)
    return n


async def main(from_date: date | None) -> None:
    today = date.today()
    target = from_date or today - timedelta(days=1)

    await init_pool()
    client = get_client()
    universe = await get_active_universe()
    log.info(f"Universe: {len(universe)} active symbols")

    async with JobMonitor(
        job_name="sync_prices",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_prices,
    ) as monitor:
        # Per-phase counters kept distinct so the ASX equity count (au_rows) can
        # be classified on its own. rows_written below preserves the previous
        # combined-total semantics exactly (au + us + fx).
        au_rows = 0
        us_rows = 0
        fx_rows = 0

        # Phase 1 — AU bulk (unchanged behaviour)
        if from_date is None:
            async with acquire() as conn:
                au_rows = await fetch_and_upsert_bulk(target, client, conn, universe)
            log.info(f"sync_prices AU bulk: {au_rows} rows for {target}")
        else:
            current = from_date
            while current <= today:
                if current.weekday() < 5:
                    async with acquire() as conn:
                        n = await fetch_and_upsert_bulk(current, client, conn, universe)
                    log.info(f"  {current}: {n} rows")
                    au_rows += n
                    await asyncio.sleep(0.25)
                current += timedelta(days=1)
            log.info(f"backfill done: {au_rows} AU rows total")

        # Phase 2 + 3 — US prices and FX rates (only when US holdings exist)
        _NON_AU_SUFFIXES = (".US", ".NYSE", ".NASDAQ", ".AMEX")
        async with acquire() as conn:
            us_symbols = [s for s in universe if any(s.endswith(sfx) for sfx in _NON_AU_SUFFIXES)]
            us_acquired_start: date | None = await conn.fetchval(
                "SELECT MIN(acquired_at) FROM holding_lots"
                " WHERE symbol LIKE '%.US'"
                "    OR symbol LIKE '%.NYSE'"
                "    OR symbol LIKE '%.NASDAQ'"
                "    OR symbol LIKE '%.AMEX'"
            )

        if us_symbols:
            log.info("sync_prices US: %d symbols", len(us_symbols))
            async with acquire() as conn:
                us_rows = await _sync_us_prices(us_symbols, target, client, conn)
            log.info("sync_prices US: %d rows", us_rows)

        if us_acquired_start is not None:
            # Fetch FX history from earliest US acquisition so all lots have a rate
            fx_from = min(us_acquired_start, target)
            async with acquire() as conn:
                fx_rows = await _sync_fx_rates(fx_from, client, conn)
        else:
            log.info("sync_prices FX: no US lots — skipping AUDUSD fetch")

        # Price-completeness classification (Batch 1 Step 2 — additive, NON-gating).
        # Classifies ASX-equity coverage from the Phase-1 AU bulk count alone, so
        # US/FX residue can never read as a full ASX session (the 2026-06-14
        # incident wrote 12/14 US/FX residue rows on a non-trading day). This is
        # OBSERVATIONAL ONLY this pass: job_runs.status stays exception-driven and
        # rows_written keeps its combined-total value, so no downstream gate
        # (generate_signals / snapshot_portfolio / compose_brief) changes. Skipped
        # for backfill, where au_rows is a multi-day sum and the verdict is moot.
        if from_date is None:
            verdict = classify_sync_completeness(
                target, au_rows=au_rows, us_rows=us_rows, fx_rows=fx_rows
            )
            if verdict.is_complete:
                log.info(
                    "sync_prices completeness: %s COMPLETE (%d ASX equity rows)",
                    target,
                    au_rows,
                )
            else:
                log.warning(
                    "sync_prices completeness: %s %s — ASX=%d US=%d FX=%d; "
                    "US/FX rows are NOT ASX equity coverage.",
                    target,
                    verdict.status.value.upper(),
                    au_rows,
                    us_rows,
                    fx_rows,
                )

        monitor.rows_written = au_rows + us_rows + fx_rows

    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from",
        dest="from_date",
        type=date.fromisoformat,
        default=None,
        help="Backfill start date (YYYY-MM-DD). Omit for yesterday only.",
    )
    asyncio.run(main(parser.parse_args().from_date))
