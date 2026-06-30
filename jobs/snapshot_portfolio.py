#!/usr/bin/env python
"""
Daily portfolio capital snapshot — M-Thesis-0.

Computes (capital_aud, holdings_mv_aud, cash_aud, benchmark_xjo_close,
benchmark_tr_level, trailing_div_yield_pct, holdings_count) and UPSERTs
into portfolio_daily_snapshots.

Schedule: weekdays 20:40 UTC (after sync_prices 20:30, before compose_brief 21:00).

Hard-fail conditions (CLAUDE.md non-negotiable #10):
  - No active profile in profiles table (RuntimeError)
  - sync_prices job_runs.status != 'success' for as_of (UpstreamBlocked);
    --from backfill skips missing days instead of aborting (see main())
  - holdings_mv_aud computation fails (e.g. asyncpg error) (unhandled exception)

Soft-degrade conditions (NULL column instead of failure):
  - benchmark_xjo_close: AXJO.INDX not yet in prices table (before first
    sync_prices Phase 1.5 run after migration 0031 seeds the universe row)
  - benchmark_tr_level: NULL only while benchmark_xjo_close is NULL

cash_aud in v1: profile.cash_floor_pct * profile.capital_aud (profile's
configured capital baseline). This is a conservative estimate. A real cash
ledger replaces this after M13.8 paper-trade sign-off.

XJO benchmark: EODHD symbol AXJO.INDX (price index), ingested by sync_prices
Phase 1.5 once seeded in `universe` (migration 0031). benchmark_tr_level is the
dividend-inclusive "bar to beat": the real S&P/ASX 200 accumulation index
(_XJO_TR_SYMBOL) when ingested, else a documented compounding gross-yield
approximation on the price close (see _accumulation_tr_level). trailing_div_yield_pct
records which path ran (NULL = real index, assumed % = approximation).

Usage:
    python jobs/snapshot_portfolio.py                         # yesterday
    python jobs/snapshot_portfolio.py --as-of 2026-05-27
    python jobs/snapshot_portfolio.py --from 2026-01-01       # backfill; days without a sync_prices success row are skipped, not hard-failed
"""
import argparse
import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.prices.fx import foreign_symbol_sql, is_foreign_symbol
from asxos.jobs._helpers import UpstreamBlocked
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# EODHD symbol for ASX 200 (price-return index). Ingested via sync_prices
# Phase 1.5 once seeded in `universe` (migration 0031).
_XJO_SYMBOL = "AXJO.INDX"

# Candidate EODHD symbol for the S&P/ASX 200 *accumulation* (total-return) index.
# Preferred for benchmark_tr_level WHEN PRESENT in `prices` — the moment this is
# confirmed available on EODHD and seeded into `universe`, snapshot_portfolio
# upgrades from the documented approximation below to the real index, no code
# change. Left unseeded until verified on Render (where EODHD_API_KEY exists).
_XJO_TR_SYMBOL = "AXJOA.INDX"

# Documented total-return approximation used until the real accumulation index is
# wired. The S&P/ASX 200 cash dividend yield runs ~4%/yr; a price-only benchmark
# understates the "bar to beat" by that much. We accrue it as a compounding
# overlay on the price level:
#     tr(t) = xjo_close(t) × (1 + _ASX200_TR_YIELD) ** ((t − _TR_EPOCH)/365)
# The epoch is a fixed anchor that CANCELS in the brief's since-inception ratio
# tr(t1)/tr(t0), so its exact value is immaterial — it only fixes the level.
# This is an APPROXIMATION (cash yield, not franking-grossed-up; constant, not
# the realised monthly yield). Cited in the brief as "XJO-TR (approx)".
_ASX200_TR_YIELD = Decimal("0.04")
_TR_EPOCH = date(2020, 1, 1)

JOB_NAME = "snapshot_portfolio"


def _accumulation_tr_level(xjo_close: Decimal, as_of: date) -> Decimal:
    """Approximate ASX 200 total-return level from the price close (see above).

    Pure Decimal. The epoch anchor cancels in the brief's since-inception ratio,
    so only the *increment* y×Δt/365 of dividend return over a holding window
    survives — which is exactly the dividend drag a price-only benchmark omits.
    """
    years = Decimal((as_of - _TR_EPOCH).days) / Decimal("365")
    return (xjo_close * (Decimal("1") + _ASX200_TR_YIELD) ** years).quantize(
        Decimal("0.000001")
    )


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


async def _compute_holdings_mv(
    conn, as_of: date
) -> tuple[Decimal, int, Decimal | None, Decimal | None, Decimal | None]:
    """Compute total market value of current_holdings on as_of.

    AU symbols: price in AUD, no FX conversion needed.
    US-exchange (USD) symbols — any FOREIGN_SUFFIXES (.US/.NYSE/.NASDAQ/.AMEX):
    price in USD, converted to AUD via most recent AUDUSD rate.
    Returns (holdings_mv_aud, holdings_count, us_mv_aud, us_cost_aud, fx_rate_audusd).
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
        return Decimal("0"), 0, None, None, audusd_rate

    total_mv = Decimal("0")
    us_mv_aud: Decimal | None = None
    for r in rows:
        qty = Decimal(str(r["quantity"]))
        close = Decimal(str(r["close"]))
        price_aud: Decimal
        if is_foreign_symbol(r["symbol"]):
            if audusd_rate is None:
                raise RuntimeError(
                    f"No AUDUSD FX rate on or before {as_of} — "
                    "cannot convert US holdings to AUD. Run sync_prices first."
                )
            # AUDUSD rate = USD per 1 AUD; USD → AUD = price / rate
            price_aud = close / audusd_rate
            us_mv_aud = (us_mv_aud or Decimal("0")) + qty * price_aud
        else:
            price_aud = close
        total_mv += qty * price_aud

    # US cost_base_normal is stored in AUD; joining holding_lots directly
    # because the current_holdings VIEW does not include cost_base_normal.
    us_cost_aud: Decimal | None = None
    if us_mv_aud is not None:
        us_cost_rows = await conn.fetch(
            f"""
            SELECT SUM(hl.cost_base_normal) AS total_cost_aud
            FROM holding_lots hl
            WHERE hl.disposed_at IS NULL AND {foreign_symbol_sql("hl.symbol")}
            """
        )
        if us_cost_rows and us_cost_rows[0]["total_cost_aud"] is not None:
            us_cost_aud = Decimal(str(us_cost_rows[0]["total_cost_aud"]))

    if us_mv_aud is not None:
        us_mv_aud = us_mv_aud.quantize(Decimal("0.000001"))

    return total_mv.quantize(Decimal("0.000001")), len(rows), us_mv_aud, us_cost_aud, audusd_rate


async def _fetch_xjo_close(conn, as_of: date) -> Decimal | None:
    """Fetch AXJO.INDX close for as_of. Returns None if not yet ingested."""
    row = await conn.fetchrow(
        "SELECT close FROM prices WHERE symbol = $1 AND dt = $2",
        _XJO_SYMBOL,
        as_of,
    )
    return Decimal(str(row["close"])) if row else None


async def _fetch_accum_close(conn, as_of: date) -> Decimal | None:
    """Fetch the real accumulation-index close for as_of, if it has been ingested.

    Returns None until _XJO_TR_SYMBOL is confirmed on EODHD and seeded into
    `universe` — at which point benchmark_tr_level upgrades from the documented
    approximation to the genuine total-return index with no code change.
    """
    row = await conn.fetchrow(
        "SELECT close FROM prices WHERE symbol = $1 AND dt = $2",
        _XJO_TR_SYMBOL,
        as_of,
    )
    return Decimal(str(row["close"])) if row else None


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
        holdings_mv_aud, holdings_count, us_mv_aud, us_cost_aud, fx_rate = (
            await _compute_holdings_mv(conn, as_of)
        )
        xjo_close = await _fetch_xjo_close(conn, as_of)
        accum_close = await _fetch_accum_close(conn, as_of)

    cash_aud = (profile["cash_floor_pct"] * profile["capital_aud"]).quantize(
        Decimal("0.000001")
    )
    capital_aud = (holdings_mv_aud + cash_aud).quantize(Decimal("0.000001"))

    # benchmark_tr_level — the dividend-inclusive "bar to beat". Prefer the real
    # accumulation index when ingested; otherwise overlay the documented yield
    # approximation on the price close. trailing_div_yield_pct records which path
    # ran: NULL when the real index embeds dividends, the assumed % otherwise.
    benchmark_tr_level: Decimal | None = None
    trailing_yield: Decimal | None = None
    if accum_close is not None:
        benchmark_tr_level = accum_close
    elif xjo_close is not None:
        benchmark_tr_level = _accumulation_tr_level(xjo_close, as_of)
        trailing_yield = _ASX200_TR_YIELD * Decimal("100")

    if xjo_close is None:
        log.warning(
            "AXJO.INDX not in prices for %s — benchmark columns will be NULL. "
            "Seed AXJO.INDX in universe (migration 0031) so sync_prices Phase 1.5 "
            "ingests it.",
            as_of,
        )

    unrealised_fx_pnl: Decimal | None = None
    if us_mv_aud is not None and us_cost_aud is not None:
        unrealised_fx_pnl = (us_mv_aud - us_cost_aud).quantize(Decimal("0.000001"))

    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO portfolio_daily_snapshots
                (as_of, capital_aud, holdings_mv_aud, cash_aud,
                 benchmark_xjo_close, benchmark_tr_level,
                 trailing_div_yield_pct, holdings_count,
                 us_holdings_mv_aud, us_holdings_cost_aud,
                 fx_rate_audusd, unrealised_fx_pnl_aud, ingested_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
            ON CONFLICT (as_of) DO UPDATE SET
                capital_aud            = EXCLUDED.capital_aud,
                holdings_mv_aud        = EXCLUDED.holdings_mv_aud,
                cash_aud               = EXCLUDED.cash_aud,
                benchmark_xjo_close    = EXCLUDED.benchmark_xjo_close,
                benchmark_tr_level     = EXCLUDED.benchmark_tr_level,
                trailing_div_yield_pct = EXCLUDED.trailing_div_yield_pct,
                holdings_count         = EXCLUDED.holdings_count,
                us_holdings_mv_aud     = EXCLUDED.us_holdings_mv_aud,
                us_holdings_cost_aud   = EXCLUDED.us_holdings_cost_aud,
                fx_rate_audusd         = EXCLUDED.fx_rate_audusd,
                unrealised_fx_pnl_aud  = EXCLUDED.unrealised_fx_pnl_aud,
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
            us_mv_aud,
            us_cost_aud,
            fx_rate,
            unrealised_fx_pnl,
        )

    monitor.rows_written = 1
    log.info(
        "snapshot %s: capital=%.2f mv=%.2f cash=%.2f holdings=%d xjo=%s us_fx_pnl=%s",
        as_of,
        capital_aud,
        holdings_mv_aud,
        cash_aud,
        holdings_count,
        xjo_close or "NULL",
        unrealised_fx_pnl or "NULL",
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
                    # Backfill escape hatch: skip rather than abort when a day has no
                    # sync_prices success row. Aborting on the first gap would make a
                    # catch-up backfill useless after any period of missed syncs.
                    # The daily --as-of path still hard-fails (UpstreamBlocked) —
                    # this softer behavior is operator-run only.
                    async with acquire() as gate_conn:
                        gate_ok = await _upstream_ok(gate_conn, current)
                    if not gate_ok:
                        log.warning(
                            "backfill: skipping %s — no sync_prices success row",
                            current,
                        )
                    else:
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
