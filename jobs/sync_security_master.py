#!/usr/bin/env python
"""
Sync the research-store security master (rs_security_master) from EODHD.

Survivorship-free: ingests both active and delisted AU securities. SEPARATE from
the production `universe` table — this job never touches it. Run weekly.

Usage:
    python jobs/sync_security_master.py
"""
import asyncio
import logging

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.security_master import refresh_security_master
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def main() -> None:
    today = clock.today()
    await init_pool()
    client = get_client()

    async with JobMonitor(
        job_name="sync_security_master",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_security_master,
    ) as monitor:
        async with acquire() as conn:
            counts = await refresh_security_master(client, conn)

        monitor.rows_written = counts["inserted"] + counts["updated"]
        log.info(
            "sync_security_master done — "
            f"active={counts['active']} delisted={counts['delisted']} "
            f"inserted={counts['inserted']} updated={counts['updated']} "
            f"relisted={counts['relisted']} skipped_no_code={counts['skipped_no_code']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
