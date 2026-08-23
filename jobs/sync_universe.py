#!/usr/bin/env python
"""
Sync ASX universe from EODHD exchange symbol list.
Detects additions and delistings. Run weekly.

Usage:
    python jobs/sync_universe.py
"""
import asyncio
import logging

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.universe import refresh_universe
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def main() -> None:
    today = clock.today()
    await init_pool()
    client = get_client()

    async with JobMonitor(
        job_name="sync_universe",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_universe,
    ) as monitor:
        async with acquire() as conn:
            counts = await refresh_universe(client, conn)

        total = counts["added"] + counts["reactivated"]
        monitor.rows_written = total
        log.info(
            f"sync_universe done — added={counts['added']} reactivated={counts['reactivated']} "
            f"delisted={counts['delisted']} unchanged={counts['unchanged']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
