#!/usr/bin/env python
"""
Sync ASX prices from EODHD.

Default: yesterday's bulk prices (single API call, ~2s).
Backfill: --from YYYY-MM-DD loops each weekday at 4 req/s.

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
from asxos.ingestion.prices import fetch_and_upsert_bulk
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def get_active_universe() -> set[str]:
    async with acquire() as conn:
        rows = await conn.fetch("SELECT symbol FROM universe WHERE is_active")
        return {r["symbol"] for r in rows}


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
        if from_date is None:
            async with acquire() as conn:
                total = await fetch_and_upsert_bulk(target, client, conn, universe)
            log.info(f"sync_prices done: {total} rows for {target}")
        else:
            total = 0
            current = from_date
            while current <= today:
                if current.weekday() < 5:
                    async with acquire() as conn:
                        n = await fetch_and_upsert_bulk(current, client, conn, universe)
                    log.info(f"  {current}: {n} rows")
                    total += n
                    await asyncio.sleep(0.25)
                current += timedelta(days=1)
            log.info(f"backfill done: {total} rows total")

        monitor.rows_written = total

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
