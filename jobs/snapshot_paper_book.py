#!/usr/bin/env python
"""
Write today's arbi-declared paper book to paper_book_snapshots (F-E2E r2, S3).

The paper book is arbi's (AGENTS.md §2.2; sprint §4 decision 2026-09-16): its
capital is declared in daily-brief.yml's env block as ASXOS_PAPER_CAPITAL_AUD and
every row is labelled paper. No paper holdings ledger exists yet, so the book is
100% cash by construction. The table is append-only (0053): a same-day re-run keeps
the first row and reports 0 written with a note, never a duplicate.

This job names no live-book table and the paper table is named only by
asxos/domain/decision_engine/paper_book.py — the C1/D15 separation
(tests/test_paper_book_c1.py) holds through the job as well.

Usage:
    ASXOS_PERSONAL_USE=1 ASXOS_PAPER_CAPITAL_AUD=25000 python jobs/snapshot_paper_book.py
"""

import asyncio
import logging

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine.paper_book import (
    declared_paper_capital,
    paper_snapshot_id,
    write_daily_paper_snapshot,
)
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME = "snapshot_paper_book"


async def main() -> None:
    require_personal_use_job()
    capital = declared_paper_capital()
    as_of = clock.today()
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=as_of,
        healthcheck_url=settings.healthcheck_url_snapshot_paper_book,
    ) as monitor:
        async with acquire() as conn:
            written = await write_daily_paper_snapshot(conn, as_of=as_of, capital_aud=capital)
        monitor.rows_written = 1 if written else 0
        if not written:
            monitor.note = f"same-day re-run: {paper_snapshot_id(as_of)} already stored (append-only)"
        log.info(
            "snapshot_paper_book %s: %s capital=%s cash=100%%",
            as_of, "written" if written else "already stored", capital,
        )
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
