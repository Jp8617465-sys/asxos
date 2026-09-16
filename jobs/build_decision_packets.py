#!/usr/bin/env python
"""
Build a challenged decision packet for every approved thesis (F-E2E r2, S5).

Daily, after "Compose and send brief" in daily-brief.yml (so a failure here can
never cost the brief). For each thesis with governance_status='approved' and no
close date: challenge it against the arbi-declared paper book (S3,
`paper_book_snapshots`, never the live book — C1/D15) with the active profile's
sizing policy, the name's annualised vol, and the latest valuation_runs row (S1,
via S2's `valuation=`), then persist the five-artifact case (0048). Same-day
idempotent: a packet id already stored for the day is skipped, never rebuilt.

One thesis failing to build (no price plan, no income row, stale snapshot) is
recorded and the others continue; the run fails only when nothing was built and
something failed — CLAUDE.md #10 without letting one boilerplate thesis hide all
the others. No delivery receipt is written: this job delivers nothing; S6
renders the latest packet in the brief.

Personal-advice firewall: packets are personal investment content, so
ASXOS_PERSONAL_USE=1 is required (daily-brief.yml sets it).

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/build_decision_packets.py
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Final

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine import repository
from asxos.domain.decision_engine.builder import ChallengeContext, build_decision_case
from asxos.domain.decision_engine.challenge import DispositionLog
from asxos.domain.decision_engine.paper_book import latest_paper_snapshot_id, load_paper_book_state
from asxos.domain.decision_engine.portfolio_state import (
    load_annualised_vol,
    load_peer_vols,
    load_sizing_policy,
)
from asxos.domain.valuation.repository import latest_run_for_symbol
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "build_decision_packets"
SQL_APPROVED_THESES: Final[str] = (
    "SELECT thesis_id, symbol FROM theses "
    "WHERE governance_status = 'approved' AND closed_at IS NULL ORDER BY thesis_id"
)
SQL_PACKET_EXISTS: Final[str] = "SELECT 1 FROM decision_packets WHERE decision_packet_id = $1"


def packet_id_for(symbol: str, thesis_id: int, cutoff: datetime) -> str:
    """The builder's own id shape (`dpk-<slug>-<thesis_id>-<as_of>`), so the skip is exact."""
    display, _ = symbol.split(".", 1)
    return f"dpk-{display.lower()}-{thesis_id}-{cutoff.date().isoformat()}"


async def build_one(conn: Any, *, thesis_id: int, symbol: str, cutoff: datetime, paper_snapshot_id: str) -> str:
    """Build, challenge and persist one packet; returns its id."""
    day = cutoff.date()
    state = await load_paper_book_state(conn, paper_snapshot_id)
    policy = await load_sizing_policy(conn, day)
    vol = await load_annualised_vol(conn, symbol, day)
    peers = await load_peer_vols(conn, state, day)
    valuation = await latest_run_for_symbol(conn, symbol=symbol, as_of=day)
    ctx = ChallengeContext(
        portfolio_state=state, sizing=policy, proposed_annualised_vol=vol, peers=peers,
        dispositions=DispositionLog(),
    )
    case = await build_decision_case(
        conn, cutoff=cutoff, thesis_id=thesis_id, context=ctx, valuation=valuation
    )
    await repository.save(case, conn=conn)
    return case.decision.decision_packet_id


async def run(*, monitor: JobMonitor, cutoff: datetime) -> dict[str, Any]:
    day = cutoff.date()
    built: list[str] = []
    skipped: list[str] = []
    failed: dict[str, str] = {}
    async with acquire() as conn:
        paper_snapshot_id = await latest_paper_snapshot_id(conn, as_of=day)
        if paper_snapshot_id is None:
            raise RuntimeError(
                f"no paper_book_snapshots row at or before {day} — snapshot_paper_book (S3) must "
                "precede the packet build; the live book is never used here (C1/D15)"
            )
        theses = await conn.fetch(SQL_APPROVED_THESES)
        for row in theses:
            thesis_id, symbol = int(row["thesis_id"]), str(row["symbol"])
            packet_id = packet_id_for(symbol, thesis_id, cutoff)
            if await conn.fetchrow(SQL_PACKET_EXISTS, packet_id) is not None:
                skipped.append(packet_id)
                continue
            try:
                built.append(
                    await build_one(
                        conn, thesis_id=thesis_id, symbol=symbol, cutoff=cutoff,
                        paper_snapshot_id=paper_snapshot_id,
                    )
                )
                monitor.rows_written = len(built)
            except (ValueError, RuntimeError) as exc:
                failed[f"{symbol}#{thesis_id}"] = f"{type(exc).__name__}: {exc}"
                log.warning("packet not built for %s thesis %d: %s", symbol, thesis_id, exc)
    summary = {
        "as_of": day.isoformat(),
        "paper_snapshot_id": paper_snapshot_id,
        "approved": len(theses),
        "built": built,
        "skipped_same_day": skipped,
        "failed": failed,
    }
    log.info("build_decision_packets done — %s", json.dumps(summary))
    if failed and not built and not skipped:
        raise RuntimeError(f"no packet built; every approved thesis failed: {json.dumps(failed)}")
    if failed:
        monitor.note = f"{len(failed)} of {len(theses)} approved theses did not build: {json.dumps(failed)}"
    elif not theses:
        monitor.note = "no approved theses — nothing to challenge"
    return summary


async def main() -> None:
    require_personal_use_job()
    # UTC, like every decision-engine cutoff: the contracts require as_of == the
    # UTC cutoff date. At the scheduled 20:30 UTC run the UTC date and the Sydney
    # date the live snapshot carries coincide; a dispatch before 14:00 UTC fails
    # loudly in load_sizing_policy (no exact snapshot for the UTC date) rather
    # than building against yesterday's caps.
    cutoff = datetime.now(UTC)
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=cutoff.date(),
        healthcheck_url=settings.healthcheck_url_build_decision_packets,
    ) as monitor:
        await run(monitor=monitor, cutoff=cutoff)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
