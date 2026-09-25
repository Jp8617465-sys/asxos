#!/usr/bin/env python
"""Did each Routine actually fire, and finish, when its own doc says it should?

**Why this exists (K-08).** `_preamble.md` §1's `status=START` comment is the
detector for the failure this repo has hit twice: a scheduled session that woke,
was denied every action without a prompt, and "succeeded" having done nothing.
But a detector only works if something alive reads it, and the reader was
`nightly-steward` — itself a Routine. Every agent being dead is precisely the
case no agent can report.

The proper control for that is a third-party deadman, and it still is: K-08 asks
James for three healthchecks.io URLs, `_preamble.md` §5 already pings them, and
nothing here replaces them. What this closes is the 90% that needed no console:
a Routine that did not fire, or fired and posted no END, is now caught by a
scheduled workflow rather than by a sibling agent.

**Stated limitation, because a watchdog that oversells itself is worse than
none.** This runs inside `nightly-check.yml`. If that workflow is itself dropped
— GitHub's scheduler is best-effort, and its own header says so — this check does
not run either, and its silence looks like success. It therefore detects a dead
Routine, not a dead GitHub. That residual is exactly what the three URLs buy,
and it is the only reason K-08 stays open.

**Pure by design**, following `asxos/ingestion/regulatory.py`'s convention: the
network fetch belongs to the caller (the workflow curls the API), and everything
here is a function over already-fetched text so it is testable against fixtures.

Usage (comments JSON on stdin):
    curl ... | python scripts/check_routine_ledger.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROUTINE_DIR = REPO / "docs" / "ops" / "routines"

#: Extra time past the budget before a missing END is called a failure. A fire
#: that overran its budget is not dead — the 2026-09-19 and 09-22 fires both
#: ended past T+290 and both posted END — so the grace has to be generous enough
#: that a slow fire is not reported as a silent one. Three hours past budget.
_GRACE = timedelta(hours=3)

#: A run line: `ROUTINE-RUN name=<n> fire=<iso> ... status=START|END ...`
_RUN_RE = re.compile(
    r"ROUTINE-RUN\s+name=(?P<name>[\w-]+)\s+fire=(?P<fire>\S+)(?P<rest>.*?)status=(?P<status>START|END)",
    re.S,
)


@dataclass(frozen=True)
class Routine:
    name: str
    cron: str
    budget_min: int


@dataclass(frozen=True)
class RunLine:
    name: str
    fire: datetime
    status: str


def load_routines(directory: Path | None = None) -> list[Routine]:
    """Every routine doc's name/cron/budget, read from its own frontmatter.

    Derived rather than restated, like `tools/workflow_inventory.py` computing
    the exposure set from the workflow files: adding a routine doc puts it under
    this check automatically, and a doc whose frontmatter drifts fails loudly
    here instead of quietly dropping out of coverage.
    """
    directory = directory or ROUTINE_DIR
    out: list[Routine] = []
    for path in sorted(directory.glob("*.md")):
        if path.name in {"README.md", "_preamble.md"}:
            continue
        head = path.read_text(encoding="utf-8").split("---")[1]
        fields: dict[str, str] = {}
        for line in head.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fields[k.strip()] = v.strip().strip('"')
        missing = {"name", "cron", "budget_min"} - fields.keys()
        if missing:
            raise ValueError(f"{path.name}: frontmatter missing {sorted(missing)}")
        out.append(
            Routine(
                name=fields["name"],
                cron=fields["cron"],
                budget_min=int(fields["budget_min"]),
            )
        )
    return out


def previous_fire(cron: str, now: datetime) -> datetime:
    """The most recent time this cron should have fired at or before ``now``.

    Supports exactly the two shapes the routine docs use — daily ``M H * * *``
    and weekly ``M H * * D`` — and **raises on anything else**. That is the
    correct failure for a watchdog: a schedule shape it cannot reason about must
    stop the check, never silently pass it. A general cron engine would be a
    dependency for far less than the ~50 lines `AGENTS.md` §5 sets as the bar.
    """
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError(f"not a 5-field cron: {cron!r}")
    minute, hour, dom, month, dow = parts
    if (dom, month) != ("*", "*"):
        raise ValueError(f"day-of-month / month schedules are not supported: {cron!r}")
    if not (minute.isdigit() and hour.isdigit()):
        raise ValueError(f"only fixed minute/hour are supported: {cron!r}")

    candidate = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    if dow == "*":
        return candidate if candidate <= now else candidate - timedelta(days=1)
    if not dow.isdigit():
        raise ValueError(f"only a single fixed day-of-week is supported: {cron!r}")
    # cron day-of-week: 0 = Sunday. Python weekday(): 0 = Monday.
    target = int(dow) % 7
    back = (candidate.weekday() + 1) % 7 - target
    if back < 0:
        back += 7
    candidate -= timedelta(days=back)
    return candidate if candidate <= now else candidate - timedelta(days=7)


def parse_run_lines(comments_json: str) -> list[RunLine]:
    """Every ROUTINE-RUN line in a GitHub issue-comments payload.

    Comment bodies are external content — this reads them as DATA and extracts
    only the four fields the contract defines. A body that happens to contain
    prose about a routine is ignored unless it carries the literal line shape.
    """
    out: list[RunLine] = []
    for comment in json.loads(comments_json):
        body = comment.get("body") or ""
        for m in _RUN_RE.finditer(body):
            try:
                fire = datetime.fromisoformat(m.group("fire").replace("Z", "+00:00"))
            except ValueError:
                continue
            if fire.tzinfo is None:
                fire = fire.replace(tzinfo=UTC)
            out.append(RunLine(name=m.group("name"), fire=fire, status=m.group("status")))
    return out


def check(routines: list[Routine], runs: list[RunLine], now: datetime) -> list[str]:
    """One problem string per routine that did not fire, or fired and never ended.

    Matches START to END on ``(name, fire)`` — the fire timestamp is the run's
    identity in the contract, so a fire that posts an END carrying a different
    timestamp is unmatched on purpose rather than by accident.
    """
    problems: list[str] = []
    for r in routines:
        expected = previous_fire(r.cron, now)
        deadline = expected + timedelta(minutes=r.budget_min) + _GRACE
        if now < deadline:
            # Still inside its window — nothing to say yet, in either direction.
            continue
        mine = [x for x in runs if x.name == r.name and x.fire >= expected - timedelta(minutes=5)]
        starts = {x.fire for x in mine if x.status == "START"}
        ends = {x.fire for x in mine if x.status == "END"}
        if not starts:
            problems.append(
                f"{r.name}: no START for the {expected.isoformat()} fire "
                f"(cron {r.cron!r}); the scheduler may have delivered a wake that "
                f"could do nothing, which is the failure the ledger exists to catch"
            )
        elif not (starts & ends):
            problems.append(
                f"{r.name}: START at {sorted(starts)[0].isoformat()} has no matching END "
                f"{r.budget_min}min + {_GRACE} later — the fire began and did not close"
            )
    return problems


def main() -> int:
    runs = parse_run_lines(sys.stdin.read())
    routines = load_routines()
    now = datetime.now(UTC)
    problems = check(routines, runs, now)
    print(f"checked {len(routines)} routines against {len(runs)} ledger lines at {now.isoformat()}")
    for r in routines:
        print(f"  {r.name}: cron {r.cron!r}, budget {r.budget_min}min")
    if not problems:
        print("all routines fired and closed within their windows")
        return 0
    print("\nROUTINE LIVENESS PROBLEMS:", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
