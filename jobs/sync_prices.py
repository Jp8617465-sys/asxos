#!/usr/bin/env python
"""
Sync ASX prices from EODHD.

Default (no args): fetches yesterday's bulk prices in a single API call.
Backfill mode: loops over each date from --from to today, one bulk call per day.

Usage:
    python jobs/sync_prices.py                    # yesterday's prices
    python jobs/sync_prices.py --from 2024-01-01  # full backfill

Only inserts prices for symbols already in the universe table.
Idempotent — UPSERT on (symbol, dt).
"""
import argparse
import asyncio
import logging
from datetime import date, timedelta

import httpx

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

EODHD_BASE = "https://eodhd.com/api"


def to_symbol(code: str) -> str:
    return code if "." in code else f"{code}.AU"


async def fetch_bulk(target_date: date, client: httpx.AsyncClient) -> list[dict]:
    r = await client.get(
        f"{EODHD_BASE}/eod-bulk-last-day/AU",
        params={
            "api_token": settings.eodhd_api_key,
            "fmt": "json",
            "date": target_date.isoformat(),
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


async def get_universe(conn) -> set[str]:
    rows = await conn.fetch("SELECT symbol FROM universe WHERE is_active")
    return {r["symbol"] for r in rows}


def to_price_rows(raw: list[dict], universe: set[str]) -> list[tuple]:
    rows = []
    for item in raw:
        symbol = to_symbol(item.get("code", ""))
        if symbol not in universe:
            continue
        close = item.get("close")
        if close is None:
            continue
        rows.append((
            symbol,
            date.fromisoformat(item["date"]),
            item.get("open"),
            item.get("high"),
            item.get("low"),
            close,
            item.get("volume"),
            item.get("adjusted_close"),
        ))
    return rows


async def upsert_prices(conn, rows: list[tuple]) -> None:
    if not rows:
        return
    await conn.executemany(
        """
        INSERT INTO prices (symbol, dt, open, high, low, close, volume, adj_close)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (symbol, dt) DO UPDATE SET
            open      = EXCLUDED.open,
            high      = EXCLUDED.high,
            low       = EXCLUDED.low,
            close     = EXCLUDED.close,
            volume    = EXCLUDED.volume,
            adj_close = EXCLUDED.adj_close
        """,
        rows,
    )


async def sync_single_date(target: date, universe: set[str], client: httpx.AsyncClient) -> int:
    log.info(f"Fetching bulk prices for {target}...")
    raw = await fetch_bulk(target, client)
    rows = to_price_rows(raw, universe)
    if rows:
        async with acquire() as conn:
            await upsert_prices(conn, rows)
    log.info(f"  {target}: {len(rows)} rows written")
    return len(rows)


async def main(from_date: date | None) -> None:
    today = date.today()
    target = from_date or today - timedelta(days=1)

    await init_pool()

    async with acquire() as conn:
        universe = await get_universe(conn)

    log.info(f"Universe: {len(universe)} active symbols")

    async with JobMonitor(
        job_name="sync_prices",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_prices,
    ) as monitor:
        async with httpx.AsyncClient() as client:
            if from_date is None:
                # Daily mode: single date
                total = await sync_single_date(target, universe, client)
            else:
                # Backfill mode: loop over each calendar day, skip weekends
                total = 0
                current = from_date
                while current <= today:
                    if current.weekday() < 5:  # Mon–Fri only
                        total += await sync_single_date(current, universe, client)
                        await asyncio.sleep(0.25)  # 4 req/s — well within 100k/day limit
                    current += timedelta(days=1)

        monitor.rows_written = total
        log.info(f"sync_prices done: {total} rows total, as_of={today}")

    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from",
        dest="from_date",
        type=date.fromisoformat,
        default=None,
        help="Start date for backfill (YYYY-MM-DD). Omit for yesterday only.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.from_date))
