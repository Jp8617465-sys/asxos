#!/usr/bin/env python
"""A-47 one-off: record the packet examinations that already happened.

`jobs/build_decision_packets.py` now writes a `packet_examined` row as each packet
is built. The packets built BEFORE that landed have no such row -- measured
2026-09-17, CBA (thesis 1) has three (2026-09-01, 09-04, 09-16) and a ledger
that has moved once, ever. This job replays exactly those, through the same
`record_packet_examination` the daily job uses, so the ledger reflects the
examinations that occurred rather than the ones that should have.

WHAT IT DOES NOT DO. It never writes `theses.last_revisited_at` or
`revisit_due_at` (discipline.py's clock-reset invariant), never touches
`governance_status`, and writes nothing to `decision_packets`. Idempotent: a
packet already recorded is skipped, so re-dispatching is safe.

`--dry-run` is the default. It loads every case and prints the rows it WOULD
write, opening no write path. Pass `--persist` to write.

Usage:
    python jobs/backfill_packet_examinations.py
    python jobs/backfill_packet_examinations.py --persist
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Final

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine import repository
from asxos.domain.decision_engine.writeback import (
    citations_for,
    evidence_confidence_for,
    examination_exists,
    record_packet_examination,
)
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "backfill_packet_examinations"

#: Every packet whose thesis_version resolves to an approved, open thesis. The
#: join is the composed key -- thesis_versions keys on (symbol, exchange),
#: theses on 'SYM.EXCH' -- verified live on 2026-09-17 (1:CBA.AU). Mirrors the
#: daily job's SQL_APPROVED_THESES predicate so the two never disagree on
#: which theses are in scope.
SQL_PACKETS_FOR_APPROVED_THESES: Final[str] = """
    SELECT t.thesis_id, t.symbol, p.decision_packet_id, p.as_of
      FROM decision_packets p
      JOIN thesis_versions tv ON tv.thesis_version_id = p.thesis_version_id
      JOIN theses t ON tv.symbol || '.' || tv.exchange = t.symbol
     WHERE t.governance_status = 'approved' AND t.closed_at IS NULL
     ORDER BY t.thesis_id, p.as_of
"""


async def run(*, persist: bool, monitor: JobMonitor | None = None) -> dict[str, Any]:
    written: list[str] = []
    skipped: list[str] = []
    planned: list[dict[str, Any]] = []
    async with acquire() as conn:
        rows = await conn.fetch(SQL_PACKETS_FOR_APPROVED_THESES)
        for row in rows:
            thesis_id, packet_id = int(row["thesis_id"]), str(row["decision_packet_id"])
            if await examination_exists(conn, thesis_id=thesis_id, packet_id=packet_id):
                skipped.append(packet_id)
                continue
            case = await repository.load_case(packet_id, conn=conn)
            if not persist:
                planned.append({
                    "thesis_id": thesis_id, "symbol": str(row["symbol"]), "packet": packet_id,
                    "as_of": str(row["as_of"]),
                    "recommendation_state": case.decision.recommendation_state,
                    "evidence_confidence": evidence_confidence_for(case),
                    "citations": citations_for(case),
                })
                continue
            if await record_packet_examination(conn, thesis_id=thesis_id, case=case):
                written.append(packet_id)
                if monitor is not None:
                    monitor.rows_written = len(written)
    summary = {
        "persist": persist, "packets_in_scope": len(rows),
        "written": written, "skipped_already_recorded": skipped, "planned": planned,
    }
    log.info("%s done — %s", JOB_NAME, json.dumps(summary, default=str))
    if not persist:
        for p in planned:
            log.info("  DRY RUN would write: %s", json.dumps(p, default=str))
        log.info("DRY RUN — wrote nothing. %s rows would be written, %s already recorded.",
                 len(planned), len(skipped))
    return summary


async def main() -> None:
    require_personal_use_job()
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", action="store_true", help="Write the rows (default: dry-run)")
    args = ap.parse_args()

    await init_pool()
    try:
        if not args.persist:
            await run(persist=False)
            return
        # JobMonitor keys job_runs on as_of; for a one-off replay the honest
        # as_of is the dispatch date, not any packet's.
        async with JobMonitor(job_name=JOB_NAME, as_of=datetime.now(UTC).date()) as monitor:
            await run(persist=True, monitor=monitor)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
