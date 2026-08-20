#!/usr/bin/env python
"""
Sync prices from EODHD — three phases (M15).

Phase 1 (AU bulk):  ASX bulk endpoint — single API call, all active AU symbols.
Phase 2 (US):       Per-symbol targeted fetch for US holdings in current_holdings.
Phase 3 (FX):       AUDUSD.FOREX daily rate — fetched from earliest US acquisition
                    date so all historical lots have a rate for Div 775 calculations.

Default (self-healing): fetch every weekday from the day after the latest
observed price date through today (UTC), skipping weekends, idempotent UPSERT.
This auto-fills any gap (missed cron, holiday, EODHD latency) and corrects the
prior "yesterday-only" cadence bug that never ingested Thursday/Friday ASX
sessions. Auto-heal is capped at _MAX_AUTO_BACKFILL_DAYS; deeper gaps need --from.
Backfill: --from YYYY-MM-DD loops each weekday (unbounded; AU bulk + US/FX).

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
from asxos.domain.prices.coverage import (
    classify_sync_completeness,
    latest_observed_price_date,
)
from asxos.domain.prices.fx import foreign_symbol_sql
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.prices import (
    fetch_and_upsert_bulk,
    fetch_and_upsert_index_symbol,
    fetch_and_upsert_us_symbol,
    to_fx_rows,
    upsert_fx_rates,
)
from asxos.jobs.utils.job_monitor import JobMonitor
from asxos.redaction import redact_secrets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# Auto-heal lookback cap (calendar days). A gap older than this is almost
# certainly a deeper outage; healing it silently could fire hundreds of bulk
# calls against the free-tier EODHD quota, so we clamp and tell the operator to
# run an explicit --from backfill instead.
_MAX_AUTO_BACKFILL_DAYS = 10


def _weekdays_in_range(start: date, end: date) -> list[date]:
    """Weekdays (Mon-Fri) in ``[start, end]`` inclusive. Empty when start > end."""
    out: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            out.append(current)
        current += timedelta(days=1)
    return out


async def _resolve_start(from_date: date | None, today: date, conn) -> date:
    """First date to attempt in default self-heal mode.

    - Explicit ``--from`` → use it verbatim (unbounded; deep manual backfills).
    - Else self-heal from the day after ``MAX(prices.dt)`` over the active universe.
    - No prices at all → bootstrap from ``today - _MAX_AUTO_BACKFILL_DAYS``.
    - Gap older than the cap → clamp to the floor and WARN to run ``--from`` for a
      full historical backfill.
    """
    if from_date is not None:
        return from_date
    floor = today - timedelta(days=_MAX_AUTO_BACKFILL_DAYS)
    last = await latest_observed_price_date(conn)
    if last is None:
        return floor
    start = last + timedelta(days=1)
    if start < floor:
        log.warning(
            "sync_prices: latest price date %s is >%d days stale; auto-healing only "
            "from %s. Run --from %s for a full backfill.",
            last,
            _MAX_AUTO_BACKFILL_DAYS,
            floor,
            start,
        )
        return floor
    return start


async def get_active_universe() -> set[str]:
    async with acquire() as conn:
        rows = await conn.fetch("SELECT symbol FROM universe WHERE is_active")
        return {r["symbol"] for r in rows}


async def _resolve_index_start(
    index_symbols: list[str], from_date: date | None, today: date, conn
) -> date:
    """First date to attempt for index symbols in self-heal mode.

    The index has its OWN latest-observed floor — it must NOT inherit the equity
    `start` (MAX over the active universe). Otherwise an index-only gap (EODHD
    missed AXJO while equities synced fine, or the index was seeded after the
    equities were already current) would never self-heal, because the equity
    start would have advanced past it. An explicit --from wins. A freshly-seeded
    index with no rows bootstraps from the auto-backfill floor; a full multi-year
    history load still needs an explicit --from (the floor caps auto-heal depth).
    """
    if from_date is not None:
        return from_date
    floor = today - timedelta(days=_MAX_AUTO_BACKFILL_DAYS)
    last = await conn.fetchval(
        "SELECT MAX(dt) FROM prices WHERE symbol = ANY($1)", index_symbols
    )
    if last is None:
        return floor
    start = last + timedelta(days=1)
    if start < floor:
        log.warning(
            "sync_prices index: latest index price date %s is >%d days stale; "
            "auto-healing only from %s. Run --from %s for a full index backfill.",
            last,
            _MAX_AUTO_BACKFILL_DAYS,
            floor,
            start,
        )
        return floor
    return start


async def get_index_symbols() -> list[str]:
    """Benchmark index symbols (e.g. AXJO.INDX) — independent of is_active.

    Indices are seeded is_active=FALSE (migration 0031): they are benchmark
    references, not tradeable-equity universe members, so every equity job's
    `WHERE is_active` (sync_fundamentals, refresh_universe's delisting sweep)
    naturally excludes them — no edits needed there. They still need price
    ingestion, so this dedicated suffix query feeds Phase 1.5. The
    prices→universe FK is satisfied by the seed row.
    """
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT symbol FROM universe WHERE symbol LIKE '%.INDX' ORDER BY symbol"
        )
        return [r["symbol"] for r in rows]


async def get_us_holding_symbols() -> list[str]:
    """Held US-exchange symbols (e.g. HUBS.NYSE) — independent of is_active.

    A held US holding is shaped like an index (the AXJO.INDX precedent): it needs
    prices but is NOT an ASX-equity-universe member, so it is is_active=FALSE and
    every `WHERE is_active` ML reader (generate_signals, retrain, sync_fundamentals)
    excludes it for free — no junk US signal enters the ASX model / portfolio
    candidates. Phase 2 therefore can't derive these from the *active* universe;
    it sources them from the **open holding lots** directly (the only US names we
    actually hold), so coverage auto-stops when a lot closes. The prices→universe
    FK holds because the holding's universe row already exists.
    """
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT symbol FROM holding_lots"
            f" WHERE disposed_at IS NULL AND {foreign_symbol_sql('symbol')}"
            " ORDER BY symbol"
        )
        return [r["symbol"] for r in rows]


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
            # redact_secrets: an httpx error embeds the ?api_token=<KEY> URL.
            log.warning("sync_prices US: %s failed: %s", sym, redact_secrets(str(res)))
        else:
            total += res
    return total


async def _sync_index_prices(
    index_symbols: list[str],
    from_date: date,
    client,
    conn,
) -> int:
    """Phase 1.5: fetch + upsert prices for each index symbol concurrently.

    Benchmark indices (e.g. AXJO.INDX) are NOT returned by the AU bulk endpoint
    (equities only), so they need the per-symbol /eod path — mirroring the US
    phase. A single index failure does not abort the run (return_exceptions).
    """
    if not index_symbols:
        return 0
    results = await asyncio.gather(
        *[
            fetch_and_upsert_index_symbol(sym, from_date, client, conn)
            for sym in index_symbols
        ],
        return_exceptions=True,
    )
    total = 0
    for sym, res in zip(index_symbols, results, strict=False):
        if isinstance(res, Exception):
            # redact_secrets: an httpx error embeds the ?api_token=<KEY> URL.
            log.warning("sync_prices index: %s failed: %s", sym, redact_secrets(str(res)))
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
        idx_rows = 0

        # Phase 1 — AU bulk, self-healing. One unified weekday loop from `start`
        # (day after the latest observed price date, or an explicit --from)
        # through today (UTC), idempotent UPSERT per day. This corrects the prior
        # "yesterday-only" cadence bug that never ingested Thursday/Friday ASX
        # sessions and auto-fills any gap (missed cron, holiday, EODHD latency).
        async with acquire() as conn:
            start = await _resolve_start(from_date, today, conn)
        days = _weekdays_in_range(start, today)
        day_counts: dict[date, int] = {}
        if not days:
            log.info("sync_prices AU: already current through %s — nothing to fetch", today)
        for current in days:
            async with acquire() as conn:
                n = await fetch_and_upsert_bulk(current, client, conn, universe)
            log.info("  %s: %d rows", current, n)
            day_counts[current] = n
            au_rows += n
            await asyncio.sleep(0.25)
        if days:
            log.info(
                "sync_prices AU: %d rows across %d weekday(s) %s..%s",
                au_rows,
                len(days),
                days[0],
                days[-1],
            )

        # Phase 1.5 — index prices (benchmark framing). AXJO.INDX and any other
        # `.INDX` symbol are fetched per-symbol because the AU bulk endpoint
        # returns equities only. Index symbols are is_active=FALSE, so they come
        # from a dedicated suffix query (not the active universe). Self-heals over
        # the same window from `start`. snapshot_portfolio reads these to populate
        # the benchmark columns of portfolio_daily_snapshots.
        index_symbols = await get_index_symbols()
        if index_symbols:
            # The index self-heals from its OWN latest-observed date, independent
            # of the equity `start` (see _resolve_index_start).
            async with acquire() as conn:
                index_start = await _resolve_index_start(
                    index_symbols, from_date, today, conn
                )
            log.info(
                "sync_prices index: %d symbols %s from %s",
                len(index_symbols),
                index_symbols,
                index_start,
            )
            async with acquire() as conn:
                idx_rows = await _sync_index_prices(
                    index_symbols, index_start, client, conn
                )
            log.info("sync_prices index: %d rows", idx_rows)

        # Phase 2 + 3 — US prices and FX rates (only when US holdings exist).
        # US holdings are is_active=FALSE (held, not ASX-equity-universe members),
        # so they come from a dedicated open-lot query, NOT the active universe.
        # Both self-heal over the same window by fetching from `start`.
        us_symbols = await get_us_holding_symbols()
        async with acquire() as conn:
            us_acquired_start: date | None = await conn.fetchval(
                "SELECT MIN(acquired_at) FROM holding_lots"
                f" WHERE {foreign_symbol_sql('symbol')}"
            )

        if us_symbols:
            log.info("sync_prices US: %d symbols", len(us_symbols))
            async with acquire() as conn:
                us_rows = await _sync_us_prices(us_symbols, start, client, conn)
            log.info("sync_prices US: %d rows", us_rows)

        if us_acquired_start is not None:
            # Fetch FX history from earliest US acquisition so all lots have a rate
            fx_from = min(us_acquired_start, start)
            async with acquire() as conn:
                fx_rows = await _sync_fx_rates(fx_from, client, conn)
        else:
            log.info("sync_prices FX: no US lots — skipping AUDUSD fetch")

        # Price-completeness classification (Batch 1 Step 2 — additive, NON-gating).
        # Classifies ASX-equity coverage from the Phase-1 AU bulk count of the
        # *freshest weekday fetched* alone, so US/FX residue can never read as a
        # full ASX session (the 2026-06-14 incident wrote 12/14 US/FX residue rows
        # on a non-trading day). OBSERVATIONAL ONLY: job_runs.status stays
        # exception-driven and rows_written keeps its combined-total value, so no
        # downstream gate (generate_signals / snapshot_portfolio / compose_brief)
        # changes. Skipped when nothing was fetched (already current).
        if day_counts:
            latest_day = max(day_counts)
            latest_au = day_counts[latest_day]
            verdict = classify_sync_completeness(
                latest_day, au_rows=latest_au, us_rows=us_rows, fx_rows=fx_rows
            )
            if verdict.is_complete:
                log.info(
                    "sync_prices completeness: %s COMPLETE (%d ASX equity rows)",
                    latest_day,
                    latest_au,
                )
            else:
                log.warning(
                    "sync_prices completeness: %s %s — ASX=%d US=%d FX=%d; "
                    "US/FX rows are NOT ASX equity coverage.",
                    latest_day,
                    verdict.status.value.upper(),
                    latest_au,
                    us_rows,
                    fx_rows,
                )
                # A non-COMPLETE day must reach job_runs.error_message, not
                # just the log (R1, 2026-08-08 review). A PARTIAL EODHD day
                # exits 0, workflow ordering does not block it, and
                # validate_price_data now anchors to the last COMPLETE day —
                # so without this note, a partial day was invisible to every
                # check: pipeline-health's degraded check reads exactly this
                # field. Counts + status only; nothing vendor-controlled.
                monitor.note = (
                    f"sync_prices degraded: {latest_day} "
                    f"{verdict.status.value.upper()} — ASX={latest_au}"
                )

        monitor.rows_written = au_rows + us_rows + fx_rows + idx_rows

    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from",
        dest="from_date",
        type=date.fromisoformat,
        default=None,
        help="Backfill start date (YYYY-MM-DD). Omit to self-heal from the "
        "latest observed price date (capped at the auto-backfill window).",
    )
    asyncio.run(main(parser.parse_args().from_date))
