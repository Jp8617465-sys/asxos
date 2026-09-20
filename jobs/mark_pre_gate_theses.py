#!/usr/bin/env python
"""One-off: retire the two theses that hold `approved` from before the gate existed.

THE FINDING. Measured 2026-09-20, theses 1 (`CBA.AU`) and 2 (`HUBS.NYSE`) are the
only rows at `governance_status = 'approved'` with **zero** `thesis_evidence`
rows. They are not approvals that passed a gate: `approve_object()`'s evidence
check (`service.py`, "no non-speculative evidence exists") and the writer that
fills `thesis_evidence` both landed 2026-09-16, and these rows were opened
2026-05-28 and 2026-05-31. Their `approved` is the column DEFAULT that migration
`0059` dropped on 2026-09-17 for exactly this reason. `0059` closed the mechanism;
it did not retro-correct the rows already laundered through it. This does.

WHY RETIRE AND NOT BACKFILL EVIDENCE. Neither row records a research decision, so
evidence written for them would be a basis manufactured for a decision nobody
made -- the precise failure the evidence architecture exists to prevent. James's
reading: CBA is a demo, HUBS is an ESPP holding. The honest remedy is to say what
they are.

WHY RETIRE AND NOT REJECT. `reject_object()` refuses to run from `approved`
(`_REJECTABLE_FROM`), and its docstring is right about why: reject means "never
accepted", retire means "was accepted, is finished". These rows WERE accepted --
wrongly, by a DEFAULT -- so retire is the available verb and the accurate one.
The reasoning text carries the rest.

WHAT EACH ROW ACTUALLY IS, measured rather than asserted:

  CBA.AU (thesis 1) -- a demo fixture. Entry band 42.00-45.00 against a
  2026-09-17 close of 154.01, so the band sits 3.4x below market; NULL
  actual_entry_price; NULL conviction_level; zero evidence rows; revisit_due_at
  2026-06-27, 85 days overdue. Four `packet_examined` rows show the decision-packet
  job has been building against it since 2026-09-01 and abstaining every time.

  HUBS.NYSE (thesis 2) -- a real position, an unformed thesis. The lot is real
  (holding_lots id=1, 24 shares, ESPP-2026-05-31) and stays untouched. The THESIS
  is not one James formed: its stop_price 230.00 sits ABOVE its own
  actual_entry_price 187.54 -- a stop above entry on a long, already flagged in
  ADR D16 -- and the 2026-09-17 close of 229.58 is under it, so the discipline card
  reports a standing stop breach on a holding James recorded on 2026-07-04 as
  unsellable inside a locked ESPP trading window. That is not discipline; it is a
  permanent false alarm on numbers nobody chose, and no action on it is possible.

WHAT THIS DOES NOT TOUCH. `holding_lots`, `current_holdings` and every portfolio
surface read from them: the HUBS POSITION stays fully visible and fully counted.
Only the thesis stops claiming to be trustworthy content. It writes no
`thesis_evidence` row, no `thesis_revisions` row, and never
`last_revisited_at`/`revisit_due_at` -- `discipline.py`'s invariant that every
clock reset is a human keystroke is untouched.

WHAT IT DOES WRITE. Through `svc.retire_object()`, the same helper
`asx thesis retire` uses: one `governance_events` row then one `theses` UPDATE,
in that order, in one transaction -- the order migration 0034's BEFORE UPDATE
trigger requires, and the order `portfolio-conventions.md` records as the thing
that must be live-verified rather than assumed. The reasoning text IS the marking:
it is what a reader six months from now finds when they ask why the row is retired.

Idempotent: a thesis already retired is skipped, so a re-dispatch writes nothing.

`--dry-run` is the DEFAULT. It reads both rows and prints what it would write,
opening no write path. Pass `--persist` to write.

Usage:
    python jobs/mark_pre_gate_theses.py
    python jobs/mark_pre_gate_theses.py --persist
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Final

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.theses import service as svc
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "mark_pre_gate_theses"

#: thesis_id -> (expected symbol, the reasoning that becomes the governance_events row).
#:
#: The symbol is checked before anything is written. These are hardcoded ids, and a
#: hardcoded id that has been reused or renumbered would retire the wrong thesis --
#: so the job refuses rather than trusting the number.
MARKINGS: Final[dict[int, tuple[str, str]]] = {
    1: (
        "CBA.AU",
        "Demo fixture, not a research decision. Retired because this row's "
        "'approved' predates the approval gate entirely: it is the theses."
        "governance_status column DEFAULT that migration 0059 dropped on "
        "2026-09-17, not a judgement anyone made -- approve_object()'s evidence "
        "check and the thesis_evidence writer both landed 2026-09-16, and this "
        "row was opened 2026-05-28. Measured 2026-09-20: entry band 42.00-45.00 "
        "against a 2026-09-17 close of 154.01 (3.4x below market), NULL "
        "actual_entry_price, NULL conviction_level, zero thesis_evidence rows, "
        "revisit_due_at 2026-06-27 (85 days overdue), and four packet_examined "
        "rows recording decision packets built against it since 2026-09-01, every "
        "one abstaining. No evidence was backfilled for it: writing evidence for a "
        "decision nobody made is the failure this architecture exists to prevent.",
    ),
    2: (
        "HUBS.NYSE",
        "A real position, not a thesis James formed. The HOLDING is untouched and "
        "stays fully counted -- holding_lots id=1, 24 shares, broker_ref "
        "ESPP-2026-05-31 -- and every portfolio surface reads from there, not from "
        "this row. What is retired is the claim that this row is trustworthy "
        "research content. Its 'approved' predates the approval gate: the row was "
        "opened 2026-05-31, while approve_object()'s evidence check and the "
        "thesis_evidence writer both landed 2026-09-16, so its status is the column "
        "DEFAULT migration 0059 dropped rather than a judgement anyone made. "
        "Measured 2026-09-20: zero thesis_evidence rows, and "
        "stop_price 230.00 sits ABOVE its own actual_entry_price 187.54 -- a stop "
        "above entry on a long, already flagged in ADR D16 -- with the 2026-09-17 "
        "close at 229.58 under it, so the discipline card reported a standing stop "
        "breach on shares James recorded on 2026-07-04 (thesis_revisions id=13) as "
        "unsellable inside a locked ESPP trading window. A breach nobody can act on, "
        "against a number nobody chose, is a false alarm rather than discipline. No "
        "evidence was backfilled: an ESPP acquisition is not a research decision.",
    ),
}


async def run(*, persist: bool, monitor: JobMonitor | None = None) -> dict[str, Any]:
    retired: list[str] = []
    skipped: list[str] = []
    planned: list[dict[str, Any]] = []

    async with acquire() as conn:
        # TWO PASSES, AND THE SPLIT IS LOAD-BEARING. Validate every premise across
        # every thesis BEFORE writing anything. A single validate-then-write loop
        # retires CBA and then aborts on HUBS, leaving the correction half applied
        # and a re-dispatch unable to tell a deliberate partial state from this one.
        # A correction job is all-or-nothing on its premises or it is a new mess.
        for thesis_id, (expected_symbol, reasoning) in sorted(MARKINGS.items()):
            thesis = await svc.get_thesis(conn, thesis_id)
            if thesis is None:
                raise RuntimeError(
                    f"Thesis {thesis_id} does not exist. This job hardcodes two ids; "
                    "refusing to continue against a database that does not match."
                )
            if thesis.symbol != expected_symbol:
                raise RuntimeError(
                    f"Thesis {thesis_id} is {thesis.symbol!r}, expected {expected_symbol!r}. "
                    "A hardcoded id that has been renumbered would retire the wrong thesis; "
                    "refusing."
                )
            if thesis.governance_status == "retired":
                log.info("thesis %s (%s) already retired — skipping", thesis_id, thesis.symbol)
                skipped.append(thesis.symbol)
                continue
            if thesis.governance_status != "approved":
                raise RuntimeError(
                    f"Thesis {thesis_id} ({thesis.symbol}) is "
                    f"{thesis.governance_status!r}, not 'approved'. This job exists to "
                    "correct rows that took the pre-0059 DEFAULT; a row in any other "
                    "state was moved deliberately and is not this job's to touch."
                )

            evidence = await svc.list_thesis_evidence(conn, thesis_id)
            if evidence:
                raise RuntimeError(
                    f"Thesis {thesis_id} ({thesis.symbol}) now carries "
                    f"{len(evidence)} evidence row(s). The premise of this job is that "
                    "these two rows have none; someone has cited evidence since it was "
                    "written, so the marking needs re-deciding rather than replaying."
                )

            planned.append(
                {
                    "thesis_id": thesis_id,
                    "symbol": thesis.symbol,
                    "from_status": thesis.governance_status,
                    "to_status": "retired",
                    "reasoning": reasoning,
                }
            )

        if persist:
            for p in planned:
                await svc.retire_object(
                    conn, int(p["thesis_id"]), reasoning=str(p["reasoning"])
                )
                log.info("retired thesis %s (%s)", p["thesis_id"], p["symbol"])
                retired.append(str(p["symbol"]))

    summary: dict[str, Any] = {
        "persist": persist,
        "planned": [p["symbol"] for p in planned],
        "retired": retired,
        "skipped_already_retired": skipped,
    }
    if monitor is not None:
        monitor.rows_written = len(retired)
    log.info("%s done — %s", JOB_NAME, json.dumps(summary, default=str))
    if not persist:
        for p in planned:
            log.info("  DRY RUN would retire: %s", json.dumps(p, default=str))
        log.info(
            "DRY RUN — wrote nothing. %s thesis(es) would be retired, %s already retired.",
            len(planned), len(skipped),
        )
    return summary


async def main() -> None:
    require_personal_use_job()
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--persist",
        action="store_true",
        help="Write the retirements (default: dry-run, opens no write path)",
    )
    args = ap.parse_args()

    await init_pool()
    try:
        if not args.persist:
            await run(persist=False)
            return
        # JobMonitor keys job_runs on as_of; for a one-off correction the honest
        # as_of is the dispatch date, not either thesis's opened_at.
        async with JobMonitor(job_name=JOB_NAME, as_of=datetime.now(UTC).date()) as monitor:
            await run(persist=True, monitor=monitor)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
