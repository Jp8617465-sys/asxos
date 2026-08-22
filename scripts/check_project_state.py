#!/usr/bin/env python3
"""check_project_state.py — validate the checked-in project-state snapshot.

WHY THIS EXISTS (production-loop optimisation ruling, 2026-08-20):
    The loop's operational state has lived in prose (``roadmap-state.md``'s
    Last-wake-snapshot block), which rots: the block carried its own
    four-week freshness-correction box, and three stale-claim errors in one
    session (2026-08-18) all traced to trusting written state over live
    probes. SB1-01 froze a machine-checkable snapshot schema
    (``asxos/secondbrain/project_state.py``) precisely so wakes read
    validated data instead of reconstructing state from prose — but nothing
    consumed it. This script is the consumer seam: it validates
    ``docs/product/state/latest-snapshot.json`` against the frozen v1
    schema and (outside ``--schema-only``) checks the snapshot is fresh.

WHAT IT DOES NOT DO — and must never do:
    It never writes or repairs a snapshot. A fabricated or auto-patched
    snapshot is worse than a stale one, for exactly the reason
    ``check_ledger_coverage.sh`` never writes a ledger row (L18 clause 2):
    it corrupts the record the next wake trusts. Probe execution and
    snapshot production stay a wake-time, read-only human/agent act
    (SB1-02's lane). This script reports; a wake refreshes.

FRESHNESS vs CI:
    ``--schema-only`` skips the freshness check. CI must run with
    ``--schema-only`` — a snapshot ages by the clock, so a freshness
    failure in CI would redden every build purely from time passing, which
    trains people to ignore the check. Freshness is a *wake-time* check:
    ``/arbi`` runs this script without the flag before trusting the file.

USAGE
    python scripts/check_project_state.py [PATH] [--max-age-days N] [--schema-only]
      PATH defaults to docs/product/state/latest-snapshot.json.
      --max-age-days defaults to 7.
    Exit 0 = snapshot validates (and is fresh, unless --schema-only).
    Exit 1 = schema-invalid or stale (details printed).
    Exit 2 = the check could not run (file missing/unreadable, bad JSON).

REQUIRES: pydantic (already a core dependency). Read-only: no writes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import ValidationError

from asxos.secondbrain.contradictions import Contradiction, check_snapshot
from asxos.secondbrain.project_state import SCHEMA_VERSION, ProjectStateSnapshot

DEFAULT_PATH = Path("docs/product/state/latest-snapshot.json")
DEFAULT_MAX_AGE_DAYS = 7


def load_snapshot(path: Path) -> ProjectStateSnapshot:
    """Parse and schema-validate the snapshot at ``path``.

    Raises the underlying error; exit-code mapping is main()'s job so tests
    can assert on the failure class rather than on stdout text.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProjectStateSnapshot.model_validate(raw)


# Honest clock skew between the probing machine and the checking machine is
# not evidence corruption; anything beyond this is a future-dated snapshot.
_CLOCK_SKEW_ALLOWANCE = timedelta(minutes=5)


def freshness_problem(
    snapshot: ProjectStateSnapshot, *, now: datetime, max_age_days: int
) -> str | None:
    """Return a human-readable freshness defect, or ``None`` if fresh.

    Two failure modes, both exit 1 in main():

    * STALE — ``observed_at`` older than ``max_age_days`` (strictly: exactly
      N days old is still fresh, matching ``check_doc_expiry.sh``'s ``-gt``).
    * FUTURE-DATED — ``observed_at`` after ``now`` (beyond a small skew
      allowance). A snapshot claiming to be observed in the future is corrupt
      evidence, which is worse than stale evidence; it must never PASS
      (refactoring-expert review, 2026-08-20).
    """
    age = now - snapshot.observed_at
    if age < -_CLOCK_SKEW_ALLOWANCE:
        return (
            f"observed_at {snapshot.observed_at.isoformat()} is in the future "
            f"(now {now.isoformat()}) — a future-dated snapshot is corrupt "
            "evidence, not a fresh one"
        )
    if age > timedelta(days=max_age_days):
        return (
            f"snapshot is {age.days}d old, past the {max_age_days}d freshness "
            "limit. Refresh it at the next wake (probe live state, write a new "
            "snapshot); never hand-edit the old one"
        )
    return None


def report_contradictions(found: tuple[Contradiction, ...]) -> int:
    """Print SB2 findings; return the count of `critical` ones.

    Severity decides the exit code, deliberately: `info` records a convention
    not followed (probe linkage is deferred, so most leaves are legitimately
    unbacked) and `warning` records staleness a wake should refresh. Only
    `critical` — two sources disagreeing on the same fact — is a failure, the
    class that silently misinforms every later reader.
    """
    if not found:
        print("[project-state] no contradictions detected")
        return 0

    criticals = [c for c in found if c.severity == "critical"]
    for c in found:
        stream = sys.stderr if c.severity == "critical" else sys.stdout
        print(
            f"[project-state] {c.severity.upper():8} {c.code}: {c.subject} — {c.detail}",
            file=stream,
        )
        if c.left is not None or c.right is not None:
            print(f"                         left={c.left} right={c.right}", file=stream)

    if criticals:
        print(f"[project-state] FAIL — {len(criticals)} critical contradiction(s)", file=sys.stderr)
    return len(criticals)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="skip the freshness check (REQUIRED in CI — snapshots age by the clock)",
    )
    parser.add_argument(
        "--no-contradictions",
        action="store_true",
        help="skip SB2 contradiction detection (schema + freshness only)",
    )
    args = parser.parse_args(argv)

    snapshot_path: Path = args.path
    try:
        snapshot = load_snapshot(snapshot_path)
    except FileNotFoundError:
        print(
            f"[project-state] {snapshot_path} not found — run from the repo root", file=sys.stderr
        )
        return 2
    # UnicodeDecodeError is a ValueError but belongs with "unreadable" (exit 2),
    # not "checked and failed" (exit 1). Do NOT broaden this tuple to ValueError:
    # json.JSONDecodeError and pydantic.ValidationError both subclass it, and a
    # broad catch would silently reroute schema failures from exit 1 to exit 2
    # (refactoring-expert review, 2026-08-20).
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"[project-state] cannot read {snapshot_path}: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(
            f"[project-state] FAIL — snapshot does not validate against the frozen v{SCHEMA_VERSION} schema:",
            file=sys.stderr,
        )
        # errors(include_input=False): never echo input fragments to stderr/CI
        # logs — if a future adapter bug put a secret into a failing field,
        # str(exc) would leak it into logs that outlive a git-history purge
        # (security-engineer review, 2026-08-20).
        for err in exc.errors(include_input=False):
            loc = ".".join(str(part) for part in err["loc"]) or "<root>"
            print(f"  {loc}: {err['msg']}", file=sys.stderr)
        return 1

    observed = sum(1 for p in snapshot.probes if p.status == "observed")
    print(
        f"[project-state] {snapshot_path}: schema v{snapshot.schema_version} valid — "
        f"snapshot_id={snapshot.snapshot_id!r}, observed_at={snapshot.observed_at.isoformat()}, "
        f"probes={observed}/{len(snapshot.probes)} observed"
    )

    critical = 0
    if not args.no_contradictions:
        critical = report_contradictions(check_snapshot(snapshot))

    if args.schema_only:
        if critical:
            return 1
        print("[project-state] PASS (schema-only; freshness not checked)")
        return 0

    problem = freshness_problem(snapshot, now=datetime.now(UTC), max_age_days=args.max_age_days)
    if problem is not None:
        print(f"[project-state] FAIL — {problem}.", file=sys.stderr)
        return 1

    if critical:
        return 1

    print("[project-state] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
