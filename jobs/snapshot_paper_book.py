#!/usr/bin/env python
"""
Write today's arbi-declared paper book to paper_book_snapshots (F-E2E r2, S3).

The paper book's capital is JAMES'S C1 RULING (2026-09-07, ADR D15) and lives in
`paper_book_snapshots` itself: this job reads the most recent paper row and carries
its `capital_aud` forward, recording in each label which row it inherited. It does
not declare, default or infer a figure — changing the paper capital means writing a
new declaring row, not editing code or a workflow.

Corrected 2026-09-16 (same day it shipped): the first version read the capital from
an `ASXOS_PAPER_CAPITAL_AUD` env value in daily-brief.yml, which restated 25000 in
git beside the governed row. One ruling, two homes — the defect James named when he
asked what is hard-coded. No paper holdings ledger exists yet, so the book is 100%
cash by construction. The table is append-only (0053): a same-day re-run keeps the
first row and reports 0 written with a note, never a duplicate.

This job names no live-book table and the paper table is named only by
asxos/domain/decision_engine/paper_book.py — the C1/D15 separation
(tests/test_paper_book_c1.py) holds through the job as well.

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/snapshot_paper_book.py
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
    as_of = clock.today()
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=as_of,
        healthcheck_url=settings.healthcheck_url_snapshot_paper_book,
    ) as monitor:
        async with acquire() as conn:
            capital, carried_from = await declared_paper_capital(conn, as_of=as_of)
            written = await write_daily_paper_snapshot(
                conn, as_of=as_of, capital_aud=capital, carried_from=carried_from
            )
        monitor.rows_written = 1 if written else 0
        if not written:
            monitor.note = f"same-day re-run: {paper_snapshot_id(as_of)} already stored (append-only)"
        log.info(
            "snapshot_paper_book %s: %s capital=%s (carried from %s) cash=100%%",
            as_of, "written" if written else "already stored", capital, carried_from,
        )
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
