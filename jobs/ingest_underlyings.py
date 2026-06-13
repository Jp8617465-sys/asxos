"""
Daily underlying price ingest — M-Underlyings.

Runs at 20:48 UTC (Sun-Thu) — between ingest_market_context (20:45) and
generate_signals (20:50).

Pipeline:
  1. seed_defaults(conn)  — idempotent catalog upsert
  2. For each active underlying with eodhd/fred data_source:
     - Determine date range (last known price + 1d, or backfill from
       earliest holding_lot acquired_at / 2 years ago on first run)
     - Fetch prices from EODHD or FRED
     - Upsert via upsert_price()
  3. lithium_carbonate (data_source='manual') — skipped, logged to stderr

Hard-fail: DB connection or seed failure.
Soft-degrade: individual symbol fetch failures logged to stderr (job succeeds).
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from asxos.clients.fred import get_client as get_fred_client
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.underlyings.service import list_underlyings, seed_defaults, upsert_price
from asxos.ingestion.eodhd import get_client as get_eodhd_client
from asxos.jobs.utils.job_monitor import JobMonitor


async def _get_fetch_start(conn: object, underlying_id: int, as_of: date) -> date:
    """Return the date from which to start fetching prices.

    If prices exist: day after the last known price date.
    First run: earliest holding_lot acquired_at, bounded to max 2 years ago.
    """
    last = await conn.fetchval(  # type: ignore[union-attr]
        "SELECT MAX(as_of) FROM underlying_prices WHERE underlying_id = $1",
        underlying_id,
    )
    if last is not None:
        return last + timedelta(days=1)

    earliest = await conn.fetchval(  # type: ignore[union-attr]
        "SELECT MIN(acquired_at)::date FROM holding_lots WHERE disposed_at IS NULL"
    )
    two_years_ago = as_of - timedelta(days=730)
    if earliest is not None and earliest > two_years_ago:
        return earliest
    return two_years_ago


def _to_dec(v: object) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation:
        return None


async def _fetch_eodhd_prices(
    eodhd: object,
    symbol: str,
    from_date: date,
    as_of: date,
) -> list[tuple[date, Decimal]]:
    rows = await eodhd.daily_prices(symbol, from_date=from_date.isoformat())  # type: ignore[union-attr]
    result: list[tuple[date, Decimal]] = []
    for r in rows:
        dt_str = r.get("date", "")
        raw = r.get("adjusted_close") or r.get("close")
        if not dt_str or raw is None:
            continue
        try:
            dt = date.fromisoformat(dt_str)
            price = Decimal(str(raw))
        except (ValueError, InvalidOperation):
            continue
        if from_date <= dt <= as_of:
            result.append((dt, price))
    return result


async def _fetch_fred_prices(
    fred: object,
    series_id: str,
    from_date: date,
    as_of: date,
) -> list[tuple[date, Decimal]]:
    observations = await fred.get_series(  # type: ignore[union-attr]
        series_id,
        observation_start=from_date.isoformat(),
        sort_order="asc",
    )
    result: list[tuple[date, Decimal]] = []
    for obs in observations:
        if obs.value is None:
            continue
        if from_date <= obs.date <= as_of:
            result.append((obs.date, obs.value))
    return result


async def _run(as_of: date) -> None:
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_INGEST_UNDERLYINGS", "")
    rows_written = 0
    soft_warnings: list[str] = []

    await init_pool()
    try:
        async with JobMonitor("ingest_underlyings", as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                await seed_defaults(conn)
                underlyings = await list_underlyings(conn, include_inactive=False)

                fetch_plan: list[tuple] = []
                for u in underlyings:
                    source = u.data_source or ""
                    if not source or source == "manual":
                        print(f"[skip] {u.code}: data_source={source!r} (manual — no fetch)", file=sys.stderr)
                        continue
                    start = await _get_fetch_start(conn, u.underlying_id, as_of)
                    if start > as_of:
                        print(f"[skip] {u.code}: prices already current (last >= {as_of})", file=sys.stderr)
                        continue
                    fetch_plan.append((u, start))

            eodhd = get_eodhd_client()
            fred = get_fred_client()

            async with acquire() as conn:
                for u, start in fetch_plan:
                    source = u.data_source or ""
                    prices: list[tuple[date, Decimal]] = []

                    try:
                        if source.startswith("eodhd:"):
                            eodhd_symbol = source[len("eodhd:"):]
                            prices = await _fetch_eodhd_prices(eodhd, eodhd_symbol, start, as_of)
                        elif source.startswith("fred:"):
                            fred_series = source[len("fred:"):]
                            prices = await _fetch_fred_prices(fred, fred_series, start, as_of)
                        else:
                            soft_warnings.append(f"{u.code}: unknown data_source {source!r}")
                            continue
                    except Exception as exc:
                        soft_warnings.append(f"{u.code}: fetch failed — {exc}")
                        continue

                    for dt, spot in prices:
                        await upsert_price(conn, u.code, dt, spot)
                        rows_written += 1

            monitor.rows_written = rows_written

            if soft_warnings:
                for w in soft_warnings:
                    print(f"[warn] {w}", file=sys.stderr)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_run(date.today()))
