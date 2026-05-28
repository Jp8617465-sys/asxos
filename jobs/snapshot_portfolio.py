#!/usr/bin/env python
"""
Daily portfolio capital snapshot — M-Thesis-0.

Computes (capital_aud, holdings_mv_aud, cash_aud, benchmark_xjo_close,
benchmark_tr_level, trailing_div_yield_pct, holdings_count) and UPSERTs
into portfolio_daily_snapshots.

Schedule: weekdays 20:40 UTC (after sync_prices 20:30, before compose_brief 21:00).

Hard-fail conditions (CLAUDE.md non-negotiable #10):
  - No active profile in profiles table (RuntimeError)
  - sync_prices job_runs.status != 'success' for as_of (UpstreamBlocked)
  - holdings_mv_aud computation fails (e.g. asyncpg error) (unhandled exception)

Soft-degrade conditions (NULL column instead of failure):
  - benchmark_xjo_close: AXJO.INDX not yet in prices table
  - benchmark_tr_level: trailing_div_yield_pct source not wired in v1
  - trailing_div_yield_pct: stub returns None until D4 source is implemented

cash_aud in v1: profile.cash_floor_pct * profile.capital_aud (profile's
configured capital baseline). This is a conservative estimate. A real cash
ledger replaces this after M13.8 paper-trade sign-off.

XJO benchmark: EODHD symbol AXJO.INDX. Not yet added to sync_prices ingestion
pipeline — benchmark columns stay NULL until that's wired. Add AXJO.INDX to
sync_prices Phase 1 (universe) to enable benchmark framing in the V2 brief.

Usage:
    python jobs/snapshot_portfolio.py                         # yesterday
    python jobs/snapshot_portfolio.py --as-of 2026-05-27
    python jobs/snapshot_portfolio.py --from 2026-01-01       # backfill
"""
import argparse
import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs._helpers import UpstreamBlocked
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# EODHD symbol for ASX 200 (price-return index).
# Not in prices until AXJO.INDX is added to sync_prices ingestion.
_XJO_SYMBOL = "AXJO.INDX"

JOB_NAME = "snapshot_portfolio"


async def _upstream_ok(conn, as_of: date) -> bool:
    row = await conn.fetchrow(
        "SELECT status FROM job_runs WHERE job_name = 'sync_prices' AND as_of = $1",
        as_of,
    )
    return row is not None and row["status"] == "success"


async def _fetch_active_profile(conn) -> dict:
    """Return active profile or raise RuntimeError (hard-fail per CLAUDE.md #10)."""
    row = await conn.fetchrow(
        "SELECT capital_aud, cash_floor_pct FROM profiles WHERE is_active = TRUE LIMIT 1"
    )
    if row is None:
        raise RuntimeError(
            "No active profile found. Create one with `asx profile init --activate`."
        )
    return {
        "capital_aud": Decimal(str(row["capital_aud"])),
        "cash_floor_pct": Decimal(str(row["cash_floor_pct"])),
    }


async def _compute_holdings_mv(conn, as_of: date) -> tuple[Decimal, int]:
    """Compute total market value of current_holdings on as_of.

    AU symbols: price in AUD, no FX conversion needed.
    US symbols: price in USD, converted to AUD via most recent AUDUSD rate.
    Returns (holdings_mv_aud, holdings_count).
    """
    # Fetch the most recent AUDUSD rate on or before as_of (monthly data)
    fx_row = await conn.fetchrow(
        """
        SELECT rate FROM fx_rates
        WHERE pair = 'AUDUSD' AND dt <= $1
        ORDER BY dt DESC
        LIMIT 1
        """,
        as_of,
    )
    audusd_rate = Decimal(str(fx_row["rate"])) if fx_row else None

    rows = await conn.fetch(
        """
        SELECT ch.symbol, ch.quantity, p.close
        FROM current_holdings ch
        JOIN prices p ON p.symbol = ch.symbol AND p.dt = $1
        """,
        as_of,
    )

    if not rows:
        return Decimal("0"), 0

    total_mv = Decimal("0")
    for r in rows:
        qty = Decimal(str(r["quantity"]))
        close = Decimal(str(r["close"]))
        price_aud: Decimal
        if r["symbol"].endswith(".US"):
            if audusd_rate is None:
                raise RuntimeError(
                    f"No AUDUSD FX rate on or before {as_of} — "
                    "cannot convert US holdings to AUD. Run sync_prices first."
                )
            # AUDUSD rate = USD per 1 AUD; USD → AUD = price / rate
            price_aud = close / audusd_rate
        else:
            price_aud = close
        total_mv += qty * price_aud

    return total_mv.quantize(Decimal("0.000001")), len(rows)


async def _fetch_xjo_close(conn, as_of: date) -> Decimal | None:
    """Fetch AXJO.INDX close for as_of. Returns None if not yet ingested."""
    row = await conn.fetchrow(
        "SELECT close FROM prices WHERE symbol = $1 AND dt = $2",
        _XJO_SYMBOL,
        as_of,
    )
    return Decimal(str(row["close"])) if row else None


def _fetch_trailing_div_yield() -> Decimal | None:
    """Trailing ASX 200 dividend yield — stub for v1.

    Returns None until the D4 source (ASX/RBA monthly stats) is wired.
    When None, benchmark_tr_level stays NULL; brief degrades to price-only.
    """
    return None


async def _snapshot_one_day(as_of: date, monitor: JobMonitor) -> None:
    async with acquire() as conn:
        upstream_ok = await _upstream_ok(conn, as_of)

    if not upstream_ok:
        raise UpstreamBlocked(
            f"sync_prices has no success row for {as_of}. "
            "Snapshot requires fresh prices. Retry after sync_prices completes."
        )

    async with acquire() as conn:
        profile = await _fetch_active_profile(conn)
        holdings_mv_aud, holdings_count = await _compute_holdings_mv(conn, as_of)
        xjo_close = await _fetch_xjo_close(conn, as_of)

    trailing_yield = _fetch_trailing_div_yield()
    cash_aud = (profile["cash_floor_pct"] * profile["capital_aud"]).quantize(
        Decimal("0.000001")
    )
    capital_aud = (holdings_mv_aud + cash_aud).quantize(Decimal("0.000001"))

    benchmark_tr_level: Decimal | None = None
    if xjo_close is not None and trailing_yield is not None:
        # TR ≈ price-return × (1 + annual_yield_pct/100 × days/365) — stub
        benchmark_tr_level = xjo_close

    if xjo_close is None:
        log.warning(
            "AXJO.INDX not in prices for %s — benchmark_xjo_close will be NULL. "
            "Add AXJO.INDX to sync_prices to enable benchmark framing.",
            as_of,
        )

    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO portfolio_daily_snapshots
                (as_of, capital_aud, holdings_mv_aud, cash_aud,
                 benchmark_xjo_close, benchmark_tr_level,
                 trailing_div_yield_pct, holdings_count, ingested_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (as_of) DO UPDATE SET
                capital_aud            = EXCLUDED.capital_aud,
                holdings_mv_aud        = EXCLUDED.holdings_mv_aud,
                cash_aud               = EXCLUDED.cash_aud,
                benchmark_xjo_close    = EXCLUDED.benchmark_xjo_close,
                benchmark_tr_level     = EXCLUDED.benchmark_tr_level,
                trailing_div_yield_pct = EXCLUDED.trailing_div_yield_pct,
                holdings_count         = EXCLUDED.holdings_count,
                ingested_at            = NOW()
            """,
            as_of,
            capital_aud,
            holdings_mv_aud,
            cash_aud,
            xjo_close,
            benchmark_tr_level,
            trailing_yield,
            holdings_count,
        )

    monitor.rows_written = 1
    log.info(
        "snapshot %s: capital=%.2f mv=%.2f cash=%.2f holdings=%d xjo=%s",
        as_of,
        capital_aud,
        holdings_mv_aud,
        cash_aud,
        holdings_count,
        xjo_close or "NULL",
    )


async def main(as_of_arg: date | None, from_date: date | None) -> None:
    await init_pool()
    try:
        if from_date is not None:
            # Backfill: one JobMonitor per weekday, tracked independently.
            today = date.today()
            current = from_date
            while current < today:
                if current.weekday() < 5:
                    async with JobMonitor(
                        job_name=JOB_NAME,
                        as_of=current,
                        healthcheck_url="",  # no ping on backfill runs
                    ) as monitor:
                        await _snapshot_one_day(current, monitor)
                current += timedelta(days=1)
            log.info("backfill complete through %s", current - timedelta(days=1))
        else:
            as_of = as_of_arg or date.today() - timedelta(days=1)
            async with JobMonitor(
                job_name=JOB_NAME,
                as_of=as_of,
                healthcheck_url=settings.healthcheck_url_snapshot_portfolio,
            ) as monitor:
                await _snapshot_one_day(as_of, monitor)
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily portfolio snapshot")
    parser.add_argument(
        "--as-of",
        metavar="YYYY-MM-DD",
        help="Snapshot date (default: yesterday)",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        metavar="YYYY-MM-DD",
        help="Backfill from this date up to (but not including) today",
    )
    args = parser.parse_args()

    as_of_arg: date | None = None
    from_date: date | None = None

    if args.as_of:
        as_of_arg = date.fromisoformat(args.as_of)
    if args.from_date:
        from_date = date.fromisoformat(args.from_date)

    if as_of_arg and from_date:
        parser.error("--as-of and --from are mutually exclusive")

    asyncio.run(main(as_of_arg, from_date))
