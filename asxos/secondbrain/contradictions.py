"""Contradiction and staleness detection over ProjectStateSnapshot — SB2-01/SB2-02.

SB1 records faithfully and deliberately validates a self-contradictory snapshot;
this module is where those contradictions are detected. Every check here exists
because the equivalent drift was found BY HAND in a real session — the point is
to stop that being a human's job.

Semantics are versioned (`SEMANTICS_VERSION`): changing what a check means, or
its severity, is a version bump, because downstream consumers compare results
across wakes.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from itertools import pairwise
from typing import Final, Literal

from asxos.secondbrain._schema import FrozenModel
from asxos.secondbrain.project_state import (
    FieldObservation,
    ProbeRecord,
    ProjectStateSnapshot,
    leaves,
)

__all__ = [
    "CROSS_SOURCE_EQUALITIES",
    "FRESHNESS_BOUNDS",
    "LEAF_INTERNAL_EQUALITIES",
    "SEMANTICS_VERSION",
    "Contradiction",
    "CrossSourceEquality",
    "FreshnessBound",
    "LeafInternalEquality",
    "Severity",
    "check_snapshot",
    "check_transition",
    "reduce_snapshots",
]

SEMANTICS_VERSION: Final = 3
"""v3 (2026-09-07): RETIRED `migration_drift` (both forms) and ADDED
`latest_only_scheduled_lane`.

`REQUIRED_MIGRATIONS` was removed by #189 (2026-09-05) — drift is now the
migration-name set difference in `asxos/schema_drift.py`, run by the scheduled
`migration-drift` workflow, whose conclusion the snapshot carries in
`github.workflow_runs`. A probe named `code.required_migrations` and a leaf key
`required_migrations` can therefore never exist again, so both rules could only
mis-fire: on the 2026-09-06 wake the leaf-internal rule compared `applied_count`
(104) with the retirement note the snapshot carried in the key's place and
reported a critical. A rule that can only fire on a mistake is retired, not left
dormant.

`latest_only_scheduled_lane` (info): the same wake's snapshot listed one
conclusion per workflow — the latest — and so showed `pipeline-health` green
while its three preceding scheduled runs (09-02/03/04 UTC) were red. See
`SCHEDULED_LANES`.

v2 (2026-08-22): added `duplicate_probe_name` and `stale_freshness`.

Bumped on an ADDITION, not a redefinition, and deliberately. The version exists so a
consumer diffing findings across wakes knows the comparison is apples-to-apples; a
finding that newly appears must be attributable to new drift, not to new detection.
Two codes that could not previously be emitted breaks that guarantee, so it is a
semantics change from the consumer's side even though no existing check changed
meaning. Under-bumping is the failure that bites; over-bumping costs a constant.
"""

Severity = Literal["info", "warning", "critical"]

DEFAULT_MAX_PROBE_AGE: Final = timedelta(hours=24)
"""How far a probe may lag its snapshot before the snapshot is mixing epochs."""


class Contradiction(FrozenModel):
    """One detected inconsistency. Frozen: a finding is evidence, not a workspace."""

    code: str
    severity: Severity
    subject: str
    detail: str
    left: str | None = None
    right: str | None = None


@dataclass(frozen=True, slots=True)
class CrossSourceEquality:
    """Two independently-observed facts that MUST agree.

    `left_path` is a schema leaf whose value is a mapping; `left_key` selects the
    field inside it. `right_probe` is a probe carrying the same fact from another
    source. Disagreement is the drift class that is invisible until something
    breaks, because each source is internally consistent.
    """

    code: str
    left_path: str
    left_key: str
    right_probe: str
    severity: Severity
    detail: str


CROSS_SOURCE_EQUALITIES: Final[tuple[CrossSourceEquality, ...]] = ()
"""Cross-source form: a code constant arriving as its own probe.

Empty since v3. The only rule it ever held, `migration_drift` against the
`code.required_migrations` probe, was retired with `REQUIRED_MIGRATIONS` (#189).
The shape stays so the next constant-vs-database fact has a home; the v2 rule is
in git history."""


@dataclass(frozen=True, slots=True)
class LeafInternalEquality:
    """Two keys INSIDE one leaf's payload that must agree."""

    code: str
    path: str
    left_key: str
    right_key: str
    severity: Severity
    detail: str


LEAF_INTERNAL_EQUALITIES: Final[tuple[LeafInternalEquality, ...]] = ()
"""Leaf-internal form: two keys on one leaf that must agree.

Empty since v3 — `migration_drift` (`applied_count` vs `required_migrations`) was
retired with the constant; see `SEMANTICS_VERSION`. The history below is kept
because the drift it caught was real and the direction matters.

Observed 2026-08-22: the DB was at 97 while the constant read 96, and the
startup guard (`count < REQUIRED_MIGRATIONS`) cannot catch drift in that
direction — it only fires when the DB is BEHIND.

This is the form that actually matches the canonical snapshot: the real
`docs/product/state/latest-snapshot.json` already carries `applied_count` and
`required_migrations` together inside `data.migrations`, so the check needs no
new probe. The cross-source variant above stays for a fact whose two sources
genuinely arrive separately. Found by hand; now mechanical.
"""

_MONOTONIC_COUNTERS: Final[tuple[tuple[str, str], ...]] = (("data.migrations", "applied_count"),)

SCHEDULED_LANES: Final[tuple[str, ...]] = (
    "backup",
    "daily-brief",
    "daily-digest",
    "migration-drift",
    "nightly-check",
    "pipeline-health",
    "us-positions",
    "weekly-research",
)
"""The workflows that carry a `schedule:` trigger — measured from
`.github/workflows/*.yml` (2026-09-07; `daily-digest` added 2026-09-26) and pinned by
`tests/test_secondbrain_contradictions.py`, which parses the files rather than
trusting this tuple. A scheduled lane is the one whose reds nobody is watching."""

MIN_SCHEDULED_ROWS: Final = 3
"""How many conclusions `github.workflow_runs` must carry per scheduled lane before
"green" means anything. One row is the latest run only; on 2026-09-06 that view
showed `pipeline-health` green after three consecutive scheduled reds."""
"""Facts that can only increase. A decrease means one of the two readings is wrong."""


@dataclass(frozen=True, slots=True)
class FreshnessBound:
    """A `freshness` payload key carrying an age, and the age past which it is stale."""

    key: str
    max_days: int
    severity: Severity


FRESHNESS_BOUNDS: Final[tuple[FreshnessBound, ...]] = (
    FreshnessBound("age_days", 7, "warning"),
    FreshnessBound("observed_minus_commit_days", 7, "warning"),
)
"""Closes `sb2_deferred_staleness_evaluation` — "Judging `freshness` values".

SB1-01 carries `freshness` verbatim and never evaluates it; this is where it is judged.
The 7-day bound matches `scripts/check_project_state.py`'s `DEFAULT_MAX_AGE_DAYS`, so the
snapshot's own freshness rule and its probes' are not two different numbers.

Found 2026-08-22: the first cut of this module judged the *skew between a probe's
`observed_at` and its snapshot's*, which is a different quantity, and left `freshness`
unread. `tests/fixtures/project_state_snapshot/stale.json` encodes its staleness purely
as `freshness` payloads with both timestamps identical, so it produced zero findings.

Two limits, stated rather than silently held:

* **Top-level keys only.** A nested `{"prices": {"age_days": 20}}` is a false negative.
  `_value_disagreements` recurses; this does not. Left narrow deliberately — no producer
  emits a nested age today, and widening a staleness rule without a driving case buys
  false positives.
* **No live producer emits this shape at all.** `probes.py` sets no age keys, and the
  live snapshot carries `freshness` as prose (`"job_runs window 2026-08-17..08-18"`),
  which the mapping guard skips. So this closes the contract as the freeze doc defines
  it — "pinned by the `stale` fixture test" — not live coverage.
"""


def _probes_by_name(snapshot: ProjectStateSnapshot) -> dict[str, ProbeRecord]:
    """First probe of each name wins — see :func:`_check_duplicate_probes` for why.

    Deliberately NOT last-wins: with a duplicate present the choice is arbitrary either
    way, and first-wins makes the paired contradiction reproducible.
    """
    by_name: dict[str, ProbeRecord] = {}
    for probe in snapshot.probes:
        by_name.setdefault(probe.name, probe)
    return by_name


def _check_duplicate_probes(snapshot: ProjectStateSnapshot) -> list[Contradiction]:
    """Two probes claiming the same name are two sources disagreeing — the core case.

    `build_snapshot` rejects duplicates at construction, so this cannot arise from a
    snapshot this codebase builds. It arises from one LOADED FROM JSON — which is every
    snapshot a wake actually reads, including `docs/product/state/latest-snapshot.json`
    and the checked-in fixtures.

    Found 2026-08-22: `tests/fixtures/project_state_snapshot/contradictory.json` carries
    two probes named `data.migrations`, and that IS its contradiction. The first cut of
    this module indexed probes with a dict comprehension, so the second silently
    overwrote the first and the disagreement was destroyed before any check ran — the
    fixture named for contradictions produced zero findings above `info`.
    """
    seen: dict[str, ProbeRecord] = {}
    found: list[Contradiction] = []

    for probe in snapshot.probes:
        first = seen.get(probe.name)
        if first is None:
            seen[probe.name] = probe
            continue
        found.append(
            Contradiction(
                code="duplicate_probe_name",
                severity="critical",
                subject=probe.name,
                detail="two probes claim the same name; only one can be the observation",
                left=f"{first.source}={first.value!r}",
                right=f"{probe.source}={probe.value!r}",
            )
        )

    return found


def _mapping_value(observation: FieldObservation, key: str) -> object | None:
    if observation.status != "observed" or not isinstance(observation.value, dict):
        return None
    return observation.value.get(key)


def _value_disagreements(
    subject: str, leaf_value: object, probe_value: object
) -> list[Contradiction]:
    """Compare a leaf against its probe wherever the two carry the SAME shape.

    Measured against the real checked-in snapshot (2026-08-22): the convention is
    that a leaf holds full detail while its probe holds a provenance summary —
    `github.open_prs` is a nine-entry PR list on the leaf and `{"count": 9, ...}`
    on the probe. Demanding whole-value equality flagged three of four criticals
    as false positives.

    Three cases, and the recursion matters — a summary can be nested, so the same
    rule has to hold at every depth, not just the top:

    * both mappings -> recurse into the keys they BOTH carry, nothing else;
    * shapes differ (one side a mapping or list, the other not), or either side
      is a list -> a summary by construction, not compared; the probe's job there
      is provenance, not duplication;
    * both scalars -> compared directly. A scalar cannot summarise a scalar, so
      inequality here is exactly the two-sources-disagree class this module
      exists for (`repository.base_sha` is the load-bearing one).
    """
    if isinstance(leaf_value, dict) and isinstance(probe_value, dict):
        return [
            found
            for key in sorted(leaf_value.keys() & probe_value.keys())
            for found in _value_disagreements(f"{subject}.{key}", leaf_value[key], probe_value[key])
        ]

    if isinstance(leaf_value, dict | list) or isinstance(probe_value, dict | list):
        return []

    if leaf_value == probe_value:
        return []

    return [
        Contradiction(
            code="leaf_probe_value_mismatch",
            severity="critical",
            subject=subject,
            detail="leaf and its backing probe disagree on a value they both carry",
            left=repr(leaf_value),
            right=repr(probe_value),
        )
    ]


def _check_leaf_probe_agreement(
    snapshot: ProjectStateSnapshot,
) -> list[Contradiction]:
    """A leaf must not claim more than the probe backing it actually observed."""
    found: list[Contradiction] = []
    probes = _probes_by_name(snapshot)

    for path, leaf in leaves(snapshot).items():
        probe = probes.get(path)

        if leaf.status == "observed" and probe is None:
            found.append(
                Contradiction(
                    code="unbacked_leaf",
                    severity="info",
                    subject=path,
                    detail="leaf is 'observed' but no probe of that name backs it",
                    left="observed",
                    right="no probe",
                )
            )
        elif probe is not None and leaf.status != probe.status:
            found.append(
                Contradiction(
                    code="leaf_probe_status_mismatch",
                    severity="critical",
                    subject=path,
                    detail="leaf status disagrees with its backing probe",
                    left=leaf.status,
                    right=probe.status,
                )
            )
        elif probe is not None and leaf.status == "observed":
            found.extend(_value_disagreements(path, leaf.value, probe.value))

    return found


def _check_probe_ages(
    snapshot: ProjectStateSnapshot, *, max_probe_age: timedelta
) -> list[Contradiction]:
    """EPOCH SKEW: how far a probe lags the snapshot that contains it.

    NOT `sb2_deferred_staleness_evaluation` — an earlier version of this docstring
    claimed that, and it was wrong. That registry item is about judging `freshness`
    VALUES, which is :data:`FRESHNESS_BOUNDS`. This measures a different quantity: a
    snapshot whose probes were taken hours apart is mixing epochs even when every
    `freshness` payload is well inside bounds.
    """
    found: list[Contradiction] = []

    for probe in snapshot.probes:
        if probe.observed_at > snapshot.observed_at:
            found.append(
                Contradiction(
                    code="probe_after_snapshot",
                    severity="critical",
                    subject=probe.name,
                    detail="probe is timestamped after the snapshot that contains it",
                    left=probe.observed_at.isoformat(),
                    right=snapshot.observed_at.isoformat(),
                )
            )
            continue

        age = snapshot.observed_at - probe.observed_at
        if age > max_probe_age:
            found.append(
                Contradiction(
                    code="stale_probe",
                    severity="warning",
                    subject=probe.name,
                    detail=f"probe lags its snapshot by {age}, over the {max_probe_age} bound",
                    left=probe.observed_at.isoformat(),
                    right=snapshot.observed_at.isoformat(),
                )
            )

    return found


def _check_cross_source(
    snapshot: ProjectStateSnapshot,
    rules: Iterable[CrossSourceEquality],
) -> list[Contradiction]:
    found: list[Contradiction] = []
    by_path = leaves(snapshot)
    probes = _probes_by_name(snapshot)

    for rule in rules:
        leaf = by_path.get(rule.left_path)
        probe = probes.get(rule.right_probe)
        if leaf is None or probe is None or probe.status != "observed":
            continue

        left = _mapping_value(leaf, rule.left_key)
        if left is None or left == probe.value:
            continue

        found.append(
            Contradiction(
                code=rule.code,
                severity=rule.severity,
                subject=f"{rule.left_path}.{rule.left_key}",
                detail=rule.detail,
                left=repr(left),
                right=repr(probe.value),
            )
        )

    return found


def _check_leaf_internal(
    snapshot: ProjectStateSnapshot, rules: Iterable[LeafInternalEquality]
) -> list[Contradiction]:
    found: list[Contradiction] = []
    by_path = leaves(snapshot)

    for rule in rules:
        leaf = by_path.get(rule.path)
        if leaf is None:
            continue
        left = _mapping_value(leaf, rule.left_key)
        right = _mapping_value(leaf, rule.right_key)
        if left is None or right is None or left == right:
            continue
        found.append(
            Contradiction(
                code=rule.code,
                severity=rule.severity,
                subject=f"{rule.path}.{rule.left_key}",
                detail=rule.detail,
                left=repr(left),
                right=repr(right),
            )
        )

    return found


def _check_scheduled_lane_depth(snapshot: ProjectStateSnapshot) -> list[Contradiction]:
    """A scheduled lane carried with fewer than `MIN_SCHEDULED_ROWS` conclusions is a
    latest-run-only view, and a latest-run-only view masks reds. Info, not failure:
    the wake decides coverage; this names the lanes it covered too thinly."""
    leaf = leaves(snapshot).get("github.workflow_runs")
    if leaf is None or leaf.status != "observed" or not isinstance(leaf.value, list):
        return []
    counts: dict[str, int] = {}
    for row in leaf.value:
        name = row.get("name") if isinstance(row, dict) else None
        if isinstance(name, str):
            counts[name] = counts.get(name, 0) + 1
    return [
        Contradiction(
            code="latest_only_scheduled_lane",
            severity="info",
            subject=f"github.workflow_runs.{lane}",
            detail=(
                "a scheduled lane is carried with too few conclusions to see a red "
                "behind the latest run"
            ),
            left=str(counts[lane]),
            right=str(MIN_SCHEDULED_ROWS),
        )
        for lane in SCHEDULED_LANES
        if 0 < counts.get(lane, 0) < MIN_SCHEDULED_ROWS
    ]


def _check_freshness_bounds(
    snapshot: ProjectStateSnapshot, bounds: Iterable[FreshnessBound]
) -> list[Contradiction]:
    """Judge `freshness` payload ages — the SB1-deferred half of staleness."""
    found: list[Contradiction] = []

    for probe in snapshot.probes:
        if not isinstance(probe.freshness, dict):
            continue
        for bound in bounds:
            age = probe.freshness.get(bound.key)
            if not isinstance(age, int) or isinstance(age, bool) or age <= bound.max_days:
                continue
            found.append(
                Contradiction(
                    code="stale_freshness",
                    severity=bound.severity,
                    subject=probe.name,
                    detail=(
                        f"probe reports {bound.key}={age}, over the {bound.max_days}-day bound"
                    ),
                    left=str(age),
                    right=str(bound.max_days),
                )
            )

    return found


def check_snapshot(
    snapshot: ProjectStateSnapshot,
    *,
    max_probe_age: timedelta = DEFAULT_MAX_PROBE_AGE,
    cross_source: Iterable[CrossSourceEquality] = CROSS_SOURCE_EQUALITIES,
    leaf_internal: Iterable[LeafInternalEquality] = LEAF_INTERNAL_EQUALITIES,
    freshness_bounds: Iterable[FreshnessBound] = FRESHNESS_BOUNDS,
) -> tuple[Contradiction, ...]:
    """Every intra-snapshot check, ordered deterministically."""
    found = [
        *_check_duplicate_probes(snapshot),
        *_check_leaf_probe_agreement(snapshot),
        *_check_probe_ages(snapshot, max_probe_age=max_probe_age),
        *_check_freshness_bounds(snapshot, freshness_bounds),
        *_check_scheduled_lane_depth(snapshot),
        *_check_cross_source(snapshot, cross_source),
        *_check_leaf_internal(snapshot, leaf_internal),
    ]
    return tuple(sorted(found, key=lambda c: (c.subject, c.code)))


def check_transition(
    previous: ProjectStateSnapshot, current: ProjectStateSnapshot
) -> tuple[Contradiction, ...]:
    """Inter-snapshot checks — the correction rules half of SB2-01.

    Later-wins is the projection rule, but a fact that goes BACKWARDS is not a
    correction, it is evidence that one of the two readings is wrong.
    """
    found: list[Contradiction] = []

    if current.observed_at < previous.observed_at:
        found.append(
            Contradiction(
                code="snapshot_order_reversed",
                severity="critical",
                subject="observed_at",
                detail="the 'current' snapshot predates the one it supersedes",
                left=current.observed_at.isoformat(),
                right=previous.observed_at.isoformat(),
            )
        )

    prev_leaves, cur_leaves = leaves(previous), leaves(current)

    for path, key in _MONOTONIC_COUNTERS:
        before = _mapping_value(prev_leaves[path], key)
        after = _mapping_value(cur_leaves[path], key)
        if isinstance(before, int) and isinstance(after, int) and after < before:
            found.append(
                Contradiction(
                    code="counter_went_backwards",
                    severity="critical",
                    subject=f"{path}.{key}",
                    detail="a monotonic counter decreased between snapshots",
                    left=str(before),
                    right=str(after),
                )
            )

    for path, cur_leaf in cur_leaves.items():
        prev_leaf = prev_leaves[path]
        if prev_leaf.status == "observed" and cur_leaf.status != "observed":
            found.append(
                Contradiction(
                    code="observation_regressed",
                    severity="warning",
                    subject=path,
                    detail="a leaf that was observed is no longer readable",
                    left="observed",
                    right=cur_leaf.status,
                )
            )

    return tuple(sorted(found, key=lambda c: (c.subject, c.code)))


def reduce_snapshots(
    snapshots: Sequence[ProjectStateSnapshot],
) -> tuple[ProjectStateSnapshot | None, tuple[Contradiction, ...]]:
    """Project a sequence to current state (later wins) plus every contradiction found.

    Returns `(None, ())` for an empty sequence — no snapshots is not an error, it
    is simply nothing observed yet.

    Note: `snapshot_order_reversed` is unreachable from here, because this sorts
    by `observed_at` before pairing. It stays live on the public
    :func:`check_transition`, where the caller chooses the order — do not assume
    this function will catch a clock inversion.
    """
    if not snapshots:
        return None, ()

    ordered = sorted(snapshots, key=lambda s: s.observed_at)
    found: list[Contradiction] = []

    for previous, current in pairwise(ordered):
        found.extend(check_transition(previous, current))

    latest = ordered[-1]
    found.extend(check_snapshot(latest))

    deduped = {(c.code, c.subject, c.left, c.right): c for c in found}
    return latest, tuple(sorted(deduped.values(), key=lambda c: (c.subject, c.code)))
