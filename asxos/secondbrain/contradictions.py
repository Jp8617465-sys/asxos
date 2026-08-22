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

from pydantic import BaseModel, ConfigDict

from asxos.secondbrain.project_state import (
    FieldObservation,
    ProbeRecord,
    ProjectStateSnapshot,
)

__all__ = [
    "SEMANTICS_VERSION",
    "Contradiction",
    "CrossSourceEquality",
    "CROSS_SOURCE_EQUALITIES",
    "LEAF_INTERNAL_EQUALITIES",
    "LeafInternalEquality",
    "Severity",
    "check_snapshot",
    "check_transition",
    "reduce_snapshots",
]

SEMANTICS_VERSION: Final = 1

Severity = Literal["info", "warning", "critical"]

DEFAULT_MAX_PROBE_AGE: Final = timedelta(hours=24)
"""How far a probe may lag its snapshot before the snapshot is mixing epochs."""


class Contradiction(BaseModel):
    """One detected inconsistency. Frozen: a finding is evidence, not a workspace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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


CROSS_SOURCE_EQUALITIES: Final[tuple[CrossSourceEquality, ...]] = (
    CrossSourceEquality(
        code="migration_drift",
        left_path="data.migrations",
        left_key="applied_count",
        right_probe="code.required_migrations",
        severity="critical",
        detail=(
            "the applied-migration count in the database disagrees with "
            "REQUIRED_MIGRATIONS in the code"
        ),
    ),
)
"""Cross-source form: the code constant arrives as its own probe."""


@dataclass(frozen=True, slots=True)
class LeafInternalEquality:
    """Two keys INSIDE one leaf's payload that must agree."""

    code: str
    path: str
    left_key: str
    right_key: str
    severity: Severity
    detail: str


LEAF_INTERNAL_EQUALITIES: Final[tuple[LeafInternalEquality, ...]] = (
    LeafInternalEquality(
        code="migration_drift",
        path="data.migrations",
        left_key="applied_count",
        right_key="required_migrations",
        severity="critical",
        detail=(
            "the applied-migration count in the database disagrees with "
            "REQUIRED_MIGRATIONS in the code"
        ),
    ),
)
"""Observed 2026-08-22: the DB was at 97 while the constant read 96, and the
startup guard (`count < REQUIRED_MIGRATIONS`) cannot catch drift in that
direction — it only fires when the DB is BEHIND.

This is the form that actually matches the canonical snapshot: the real
`docs/product/state/latest-snapshot.json` already carries `applied_count` and
`required_migrations` together inside `data.migrations`, so the check needs no
new probe. The cross-source variant above stays for a fact whose two sources
genuinely arrive separately. Found by hand; now mechanical.
"""

_MONOTONIC_COUNTERS: Final[tuple[tuple[str, str], ...]] = (("data.migrations", "applied_count"),)
"""Facts that can only increase. A decrease means one of the two readings is wrong."""


def _leaves(snapshot: ProjectStateSnapshot) -> dict[str, FieldObservation]:
    return {
        f"{section}.{field}": getattr(getattr(snapshot, section), field)
        for section in ("repository", "github", "production", "data")
        for field in type(getattr(snapshot, section)).model_fields
    }


def _probes_by_name(snapshot: ProjectStateSnapshot) -> dict[str, ProbeRecord]:
    return {probe.name: probe for probe in snapshot.probes}


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

    for path, leaf in _leaves(snapshot).items():
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
    """Staleness (`sb2_deferred_staleness_evaluation`): SB1 carries ages, SB2 judges them."""
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
    leaves = _leaves(snapshot)
    probes = _probes_by_name(snapshot)

    for rule in rules:
        leaf = leaves.get(rule.left_path)
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
    leaves = _leaves(snapshot)

    for rule in rules:
        leaf = leaves.get(rule.path)
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


def check_snapshot(
    snapshot: ProjectStateSnapshot,
    *,
    max_probe_age: timedelta = DEFAULT_MAX_PROBE_AGE,
    cross_source: Iterable[CrossSourceEquality] = CROSS_SOURCE_EQUALITIES,
    leaf_internal: Iterable[LeafInternalEquality] = LEAF_INTERNAL_EQUALITIES,
) -> tuple[Contradiction, ...]:
    """Every intra-snapshot check, ordered deterministically."""
    found = [
        *_check_leaf_probe_agreement(snapshot),
        *_check_probe_ages(snapshot, max_probe_age=max_probe_age),
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

    prev_leaves, cur_leaves = _leaves(previous), _leaves(current)

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
