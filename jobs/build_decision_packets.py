#!/usr/bin/env python
"""
Build a challenged decision packet for every approved thesis (F-E2E r2, S5).

Daily, after "Compose and send brief" in daily-brief.yml (so a failure here can
never cost the brief). For each thesis with governance_status='approved' and no
close date: challenge it against the arbi-declared paper book (S3,
`paper_book_snapshots`, never the live book — C1/D15) with the active profile's
sizing policy, the name's annualised vol, the latest valuation_runs row (S1,
via S2's `valuation=`) and the G12 dividend characterisation (S9), then persist the five-artifact case (0048). Same-day
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
from asxos.domain.decision_engine.writeback import record_packet_examination
from asxos.domain.tax.feed import load_dividend_characterisation
from asxos.domain.theses.plan import has_price_plan
from asxos.domain.valuation.repository import latest_run_for_symbol
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "build_decision_packets"
#: The price-plan columns ride along so the set can be partitioned BEFORE the
#: builder is called — see `run()`. Selecting them here and testing them with
#: the shared `has_price_plan` is what keeps this job and
#: `build_decision_case`'s own guard from drifting apart.
SQL_APPROVED_THESES: Final[str] = (
    "SELECT thesis_id, symbol, entry_band_lower, entry_band_upper, "
    "stop_price, target_price, actual_entry_price FROM theses "
    "WHERE governance_status = 'approved' AND closed_at IS NULL ORDER BY thesis_id"
)
SQL_PACKET_EXISTS: Final[str] = "SELECT 1 FROM decision_packets WHERE decision_packet_id = $1"
#: Has the data layer EVER served a financial statement for this symbol? Not
#: "at the cutoff" — ever. The distinction is the whole safety property of the
#: partition below: zero-ever means the vendor does not cover the name and no
#: run will ever build it; some-rows-but-none-admissible-at-the-cutoff is a
#: real degradation and must still fail loudly.
SQL_SYMBOL_HAS_STATEMENTS: Final[str] = (
    "SELECT 1 FROM rs_financial_statements WHERE symbol = $1 LIMIT 1"
)


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
    dividends = await load_dividend_characterisation(conn, symbol, cutoff)
    ctx = ChallengeContext(
        portfolio_state=state, sizing=policy, proposed_annualised_vol=vol, peers=peers,
        dispositions=DispositionLog(),
    )
    case = await build_decision_case(
        conn, cutoff=cutoff, thesis_id=thesis_id, context=ctx, valuation=valuation, dividends=dividends
    )
    await repository.save(case, conn=conn)
    # A-47: the packet is the system examining this thesis -- say so on the
    # thesis's own discipline ledger. This never resets last_revisited_at (see
    # decision_engine/writeback.py and discipline.py's clock-reset invariant).
    await record_packet_examination(conn, thesis_id=thesis_id, case=case)
    return case.decision.decision_packet_id


async def run(*, monitor: JobMonitor, cutoff: datetime) -> dict[str, Any]:
    day = cutoff.date()
    built: list[str] = []
    skipped: list[str] = []
    awaiting_plan: list[str] = []
    no_data_coverage: list[str] = []
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
            # An approved thesis with no price plan is not a failure to report,
            # it is a row waiting on James. Calling the builder for it would
            # raise every night, land in `monitor.note`, and page through
            # check_cron_health forever — the shape of issue #327, and what
            # migration 0059's eleven rows did for 84 days. It is set aside
            # before the builder is called and surfaced where it belongs: the
            # brief's candidates card, which already renders these rows.
            if not has_price_plan(
                entry_band_lower=row["entry_band_lower"],
                entry_band_upper=row["entry_band_upper"],
                stop_price=row["stop_price"],
                target_price=row["target_price"],
                actual_entry_price=row["actual_entry_price"],
            ):
                awaiting_plan.append(f"{symbol}#{thesis_id}")
                continue
            # The second structural precondition, same reasoning as the first
            # (issue #327). `build_decision_case` needs an admissible yearly
            # income row; if the data layer has NEVER held a statement for this
            # symbol, no run will ever produce one and calling the builder just
            # re-raises the same ValueError every night into `monitor.note`.
            #
            # Measured 2026-09-19 on the first weekly-research run after #328's
            # held-US-name union shipped: it concluded `success` and
            # sync_financial_statements wrote 437,031 rows, yet HUBS.NYSE has
            # ZERO and so do ALL non-.AU symbols — 0 of 3,379 distinct symbols
            # in rs_financial_statements are non-.AU. The vendor does not serve
            # them. That is a coverage fact, not this job's health.
            #
            # Deliberately "ever", not "at this cutoff": a symbol WITH history
            # whose cutoff yields nothing admissible is a regression, stays in
            # `failed`, and still pages. This partition can only ever quiet a
            # name the data layer has never once covered.
            if await conn.fetchrow(SQL_SYMBOL_HAS_STATEMENTS, symbol) is None:
                no_data_coverage.append(f"{symbol}#{thesis_id}")
                continue
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
        "awaiting_plan": awaiting_plan,
        "no_data_coverage": no_data_coverage,
        "failed": failed,
    }
    log.info("build_decision_packets done — %s", json.dumps(summary))
    if failed and not built and not skipped:
        raise RuntimeError(f"no packet built; every approved thesis failed: {json.dumps(failed)}")
    if failed:
        monitor.note = f"{len(failed)} of {len(theses)} approved theses did not build: {json.dumps(failed)}"
    # An EMPTY register sets no note either, for the same reason and on measured
    # evidence. It used to set "no approved theses — nothing to challenge", and
    # after #352 retired the last two pre-gate theses on 2026-09-20 that fired on
    # every run: check_cron_health was red on 09-20, 09-21 and 09-22 carrying it.
    # Zero approved theses is a fact about the register — here, the DESIGNED state
    # after a governance sweep — not a fault in this job. `rows_written = 0` on a
    # `success` row already records it losslessly, and the brief's candidates card
    # shows the queue.
    #
    # `awaiting_plan`, `no_data_coverage` and the empty register all set NO note.
    # One is a fact about James's review queue, one about vendor coverage, one
    # about governance state; none is about this job's health, and the note
    # channel is an alerting channel (job_monitor.py:139 -> check_cron_health.py:152).
    # A watchdog that pages nightly on a condition nobody can fix trains its
    # reader to ignore it, which is the failure mode check_cron_health's own
    # header names twice.
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
