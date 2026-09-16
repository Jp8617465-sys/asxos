#!/usr/bin/env python
"""
Close the outcome loop on every decision packet, daily (F-E2E r2, S7).

Daily, after "Build decision packets" in daily-brief.yml. Two passes, both
append-only (migration 0052):

  1. t0 for every `decision_packets` row that has no `thesis_outcomes` t0 row
     yet: `outcomes.materialise_t0` records what was known and claimed and
     schedules the 21/63/126-session horizons through the packet's own trading
     calendar.
  2. Observation for every scheduled horizon whose due session has arrived:
     `outcomes.observe_at_due_session` measures the security's return from the
     packet's reference price to the last close at or before the PROMISED
     session (never the catch-up date); the benchmark leg reports unavailable
     until AXJOA.INDX exists in `prices` (governor ruling F1, never a proxy).

One packet failing (a malformed price token, a calendar that cannot reach a
horizon) is recorded in the job_runs note and the others continue; the run
fails only when nothing was written and something failed. Idempotent: a t0
row already stored excludes its packet from pass 1, an observed horizon is
excluded from pass 2, and every INSERT is ON CONFLICT DO NOTHING.

One observation is never an alpha claim: this job writes measurements and named
unavailability states, no verdict (outcomes.py module docstring, property 3).

Personal-advice firewall: packets are personal investment content, so
ASXOS_PERSONAL_USE=1 is required (daily-brief.yml sets it).

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/observe_decision_outcomes.py
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Final

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine import repository
from asxos.domain.decision_engine.outcomes import (
    OutcomeError,
    due_horizons,
    load_outcomes,
    materialise_t0,
    observe_at_due_session,
    save_outcome,
)
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "observe_decision_outcomes"
SQL_PACKETS_WITHOUT_T0: Final[str] = (
    "SELECT p.decision_packet_id FROM decision_packets p "
    "WHERE NOT EXISTS (SELECT 1 FROM thesis_outcomes o "
    "WHERE o.decision_packet_id = p.decision_packet_id AND o.horizon_trading_days = 0) "
    "ORDER BY p.created_at, p.decision_packet_id"
)
SQL_PACKETS_WITH_DUE_HORIZONS: Final[str] = (
    "SELECT DISTINCT decision_packet_id FROM thesis_outcomes "
    "WHERE horizon_trading_days > 0 AND observation_state = 'recorded' AND due_at <= $1 "
    "ORDER BY decision_packet_id"
)


async def record_t0(conn: Any, packet_id: str, *, created_at: datetime) -> int:
    """t0 plus the scheduled horizons for one packet; returns rows written."""
    case = await repository.load_case(packet_id, conn=conn)
    rows = materialise_t0(case, created_at=created_at)
    for row in rows:
        await save_outcome(conn, row)
    return len(rows)


async def observe_due(conn: Any, packet_id: str, *, cutoff: datetime) -> list[str]:
    """Observe every horizon of one packet whose session has arrived; returns outcome ids."""
    rows = await load_outcomes(conn, packet_id)
    observed: list[str] = []
    for row in due_horizons(rows, cutoff):
        filled = await observe_at_due_session(conn, row)
        await save_outcome(conn, filled)
        observed.append(filled.outcome_id)
    return observed


async def run(*, monitor: JobMonitor, cutoff: datetime) -> dict[str, Any]:
    t0: dict[str, int] = {}
    observed: dict[str, list[str]] = {}
    failed: dict[str, str] = {}
    written = 0
    async with acquire() as conn:
        for row in await conn.fetch(SQL_PACKETS_WITHOUT_T0):
            packet_id = str(row["decision_packet_id"])
            try:
                t0[packet_id] = await record_t0(conn, packet_id, created_at=cutoff)
                written += t0[packet_id]
                monitor.rows_written = written
            except (OutcomeError, ValueError, RuntimeError) as exc:
                failed[f"t0:{packet_id}"] = f"{type(exc).__name__}: {exc}"
                log.warning("t0 not recorded for %s: %s", packet_id, exc)
        for row in await conn.fetch(SQL_PACKETS_WITH_DUE_HORIZONS, cutoff):
            packet_id = str(row["decision_packet_id"])
            try:
                ids = await observe_due(conn, packet_id, cutoff=cutoff)
            except (OutcomeError, ValueError, RuntimeError) as exc:
                failed[f"observe:{packet_id}"] = f"{type(exc).__name__}: {exc}"
                log.warning("observation failed for %s: %s", packet_id, exc)
                continue
            if ids:
                observed[packet_id] = ids
                written += len(ids)
                monitor.rows_written = written
    summary = {
        "cutoff": cutoff.isoformat(),
        "t0_recorded": t0,
        "observed": observed,
        "failed": failed,
        "rows_written": written,
    }
    log.info("observe_decision_outcomes done — %s", json.dumps(summary))
    if failed and not written:
        raise RuntimeError(f"no outcome row written; every packet failed: {json.dumps(failed)}")
    if failed:
        monitor.note = f"{len(failed)} packet pass(es) failed: {json.dumps(failed)}"
    elif not written:
        monitor.note = "nothing to record: every packet has its t0 and no horizon is due"
    return summary


async def main() -> None:
    require_personal_use_job()
    cutoff = datetime.now(UTC)
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=cutoff.date(),
        healthcheck_url=settings.healthcheck_url_observe_decision_outcomes,
    ) as monitor:
        await run(monitor=monitor, cutoff=cutoff)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
