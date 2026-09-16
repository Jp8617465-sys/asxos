#!/usr/bin/env python
"""Materialise live brief sections into brief_section_gold.

Runs collect() once (existing sequential collect), then persist() on one
connection, sequential upserts. UndefinedTableError is re-raised so GHA
compose cannot run against an unapplied 0047.

Usage:
    python jobs/materialise_brief_sections.py
    python jobs/materialise_brief_sections.py --as-of 2026-05-22
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import date

from asxos import clock
from asxos.brief.compose import collect
from asxos.brief.gold import persist
from asxos.brief.section import SECTION_ORDER
from asxos.jobs._helpers import require_personal_use_job

# Module-level stubs — tests patch these at the jobs.materialise_brief_sections
# namespace. Production main() lazy-imports the real implementations.
init_pool = None  # type: ignore[assignment]
close_pool = None  # type: ignore[assignment]
JobMonitor = None  # type: ignore[assignment]
acquire = None  # type: ignore[assignment]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main(as_of: date) -> None:
    require_personal_use_job()

    _init_pool = globals()["init_pool"]
    _close_pool = globals()["close_pool"]
    _JobMonitor = globals()["JobMonitor"]
    _acquire = globals()["acquire"]

    if _init_pool is None:
        from asxos.db import close_pool as _close_pool  # type: ignore[assignment]
        from asxos.db import init_pool as _init_pool  # type: ignore[assignment]
    if _JobMonitor is None:
        from asxos.jobs.utils.job_monitor import (
            JobMonitor as _JobMonitor,  # type: ignore[assignment]
        )
    if _acquire is None:
        from asxos.db import acquire as _acquire  # type: ignore[assignment]

    await _init_pool()
    try:
        # This job had no deadman at all until 2026-09-17 — the only JobMonitor call
        # site without a healthcheck. os.environ, not settings, to match the ten
        # sibling jobs and to keep this module's imports lazy/patchable.
        async with _JobMonitor(
            job_name="materialise_brief_sections",
            as_of=as_of,
            healthcheck_url=os.environ.get("HEALTHCHECK_URL_MATERIALISE_BRIEF_SECTIONS", ""),
        ) as monitor:
            data = await collect(as_of)
            async with _acquire() as conn:
                await persist(conn, data)
            monitor.rows_written = len(SECTION_ORDER) + 2
            log.info("materialised %s gold rows for %s", monitor.rows_written, as_of)
    finally:
        await _close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Brief date (YYYY-MM-DD). Defaults to today.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.as_of or clock.today()))
