#!/usr/bin/env python
"""
Build the normalized segment_map (D3/S3, segment-valuation architecture doc).

Pure DB-to-DB: reads rs_security_master (gics_sector) + universe (sector) and
writes segment_map, resolving the two coexisting sector vocabularies into one
GICS-preferred, alias-normalized key per symbol. No EODHD. Run weekly, AFTER
sync_security_master (populates rs_security_master) and sync_universe
(populates universe) -- the same dependency shape as sync_financial_statements.

Idempotent UPSERT on (symbol, taxonomy_version); safe to re-run.

Usage:
    python jobs/build_segment_map.py
"""
import asyncio
import logging

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.research.segment_map import refresh_segment_map
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main() -> None:
    today = clock.today()
    await init_pool()

    async with JobMonitor(
        job_name="build_segment_map",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_build_segment_map,
    ) as monitor:
        async with acquire() as conn:
            counts = await refresh_segment_map(conn, as_of=today)
            if counts["symbols"] == 0:
                raise RuntimeError(
                    "no symbols to resolve — rs_security_master is empty. "
                    "Run sync_security_master first."
                )
            monitor.rows_written = counts["symbols"]
        log.info(
            "build_segment_map done — symbols=%d resolved_gics=%d "
            "resolved_alias=%d unresolved=%d",
            counts["symbols"],
            counts["resolved_gics"],
            counts["resolved_alias"],
            counts["unresolved"],
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
