"""Tests for SB2-01/SB2-02 contradiction and staleness detection.

The packet's completion proof is "Known contradictions fail fixtures" — so the
fixtures below are the drifts actually found by hand in the 2026-08-21/22
session, and each must be caught mechanically.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import JsonValue

from asxos.secondbrain.contradictions import (
    CROSS_SOURCE_EQUALITIES,
    LEAF_INTERNAL_EQUALITIES,
    MIN_SCHEDULED_ROWS,
    SCHEDULED_LANES,
    SEMANTICS_VERSION,
    Contradiction,
    check_snapshot,
    check_transition,
    reduce_snapshots,
)
from asxos.secondbrain.probes import ProbeSpec, build_snapshot, run_probes
from asxos.secondbrain.project_state import ProjectStateSnapshot

T0 = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)


def _snapshot(
    specs: list[ProbeSpec], *, observed_at: datetime = T0, snapshot_id: str = "s"
) -> ProjectStateSnapshot:
    return build_snapshot(
        run_probes(specs, observed_at=observed_at),
        snapshot_id=snapshot_id,
        observed_at=observed_at,
    )


def _spec(name: str, value: JsonValue) -> ProbeSpec:
    return ProbeSpec(name, f"test:{name}", lambda: value)


def _codes(found: tuple[Contradiction, ...]) -> set[str]:
    return {c.code for c in found}


# --------------------------------------------------------------------------
# The real drifts, as fixtures
# --------------------------------------------------------------------------


def test_migration_drift_rule_is_retired_with_its_constant() -> None:
    """v3 (2026-09-07): `REQUIRED_MIGRATIONS` was removed by #189, so the probe
    `code.required_migrations` can never be produced again. The 2026-08-22 shape
    (DB 97, constant 96) must therefore produce NO finding — the rule is gone, not
    dormant. Drift is now the name-set difference in `asxos/schema_drift.py`, run by
    the scheduled `migration-drift` workflow the snapshot carries in `workflow_runs`.
    """
    snap = _snapshot(
        [
            _spec("data.migrations", {"applied_count": 97, "latest_version": "20260821080458"}),
            _spec("code.required_migrations", 96),
        ]
    )
    assert "migration_drift" not in _codes(check_snapshot(snap))

def test_a_retirement_note_in_the_migrations_leaf_is_not_a_count_mismatch() -> None:
    """The 2026-09-06 wake carried the retirement as prose in the migrations leaf and
    the v2 leaf-internal rule compared `applied_count` (104) with that string and
    reported a critical. v3 carries no such rule."""
    snap = _snapshot(
        [
            _spec(
                "data.migrations",
                {
                    "applied_count": 104,
                    "latest_version": "20260903025557",
                    "required_migrations_note": "retired by #189 — drift is the name-set difference",
                },
            )
        ]
    )
    assert not [c for c in check_snapshot(snap) if c.severity == "critical"]

def test_cross_source_rule_needs_both_sides_present() -> None:
    """A missing counterpart is absence of evidence, not a contradiction."""
    snap = _snapshot([_spec("data.migrations", {"applied_count": 97})])
    assert "migration_drift" not in _codes(check_snapshot(snap))


def test_a_leaf_may_not_claim_more_than_its_probe_observed() -> None:
    """SB1 deliberately validates a self-contradictory snapshot; SB2 is where it fails."""
    snap = _snapshot([_spec("data.coverage", {"universe_active": 2384})])
    mutated = snap.model_copy(
        update={
            "data": snap.data.model_copy(
                update={"migrations": snap.data.coverage}  # observed leaf, no backing probe
            )
        }
    )

    found = check_snapshot(mutated)
    assert "unbacked_leaf" in _codes(found)
    assert next(c for c in found if c.code == "unbacked_leaf").subject == "data.migrations"


def test_stale_probe_is_flagged_against_its_own_snapshot() -> None:
    old = T0 - timedelta(hours=30)
    records = [
        *run_probes([_spec("data.coverage", 1)], observed_at=old),
        *run_probes([_spec("data.migrations", {"applied_count": 97})], observed_at=T0),
    ]
    snap = build_snapshot(records, snapshot_id="s", observed_at=T0)

    found = check_snapshot(snap)
    stale = [c for c in found if c.code == "stale_probe"]

    assert [c.subject for c in stale] == ["data.coverage"]
    assert stale[0].severity == "warning"


def test_probe_timestamped_after_its_snapshot_is_critical() -> None:
    records = run_probes([_spec("data.coverage", 1)], observed_at=T0 + timedelta(minutes=1))
    snap = build_snapshot(records, snapshot_id="s", observed_at=T0)

    found = check_snapshot(snap)
    assert "probe_after_snapshot" in _codes(found)
    assert next(c for c in found if c.code == "probe_after_snapshot").severity == "critical"


def test_fresh_probes_produce_no_findings() -> None:
    snap = _snapshot([_spec("data.coverage", {"universe_active": 2384})])
    assert check_snapshot(snap) == ()


# --------------------------------------------------------------------------
# Transitions — the correction-rule half of SB2-01
# --------------------------------------------------------------------------


def test_a_monotonic_counter_going_backwards_is_critical() -> None:
    before = _snapshot([_spec("data.migrations", {"applied_count": 97})], snapshot_id="a")
    after = _snapshot(
        [_spec("data.migrations", {"applied_count": 96})],
        observed_at=T0 + timedelta(hours=1),
        snapshot_id="b",
    )

    found = check_transition(before, after)
    regression = next(c for c in found if c.code == "counter_went_backwards")

    assert regression.severity == "critical"
    assert (regression.left, regression.right) == ("97", "96")


def test_an_observed_leaf_becoming_unreadable_is_flagged() -> None:
    before = _snapshot([_spec("data.coverage", 1)], snapshot_id="a")
    after = _snapshot([], observed_at=T0 + timedelta(hours=1), snapshot_id="b")

    found = check_transition(before, after)
    regressed = [c for c in found if c.code == "observation_regressed"]

    assert "data.coverage" in {c.subject for c in regressed}
    assert all(c.severity == "warning" for c in regressed)


def test_a_snapshot_that_predates_what_it_supersedes_is_critical() -> None:
    before = _snapshot([], snapshot_id="a")
    after = _snapshot([], observed_at=T0 - timedelta(hours=1), snapshot_id="b")

    assert "snapshot_order_reversed" in _codes(check_transition(before, after))


def test_a_normal_forward_transition_is_silent() -> None:
    before = _snapshot([_spec("data.migrations", {"applied_count": 96})], snapshot_id="a")
    after = _snapshot(
        [_spec("data.migrations", {"applied_count": 97})],
        observed_at=T0 + timedelta(hours=1),
        snapshot_id="b",
    )
    assert check_transition(before, after) == ()


# --------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------


def test_reduce_returns_the_latest_snapshot_regardless_of_input_order() -> None:
    early = _snapshot([_spec("data.migrations", {"applied_count": 96})], snapshot_id="early")
    late = _snapshot(
        [_spec("data.migrations", {"applied_count": 97})],
        observed_at=T0 + timedelta(hours=2),
        snapshot_id="late",
    )

    for ordering in ([early, late], [late, early]):
        latest, _ = reduce_snapshots(ordering)
        assert latest is not None and latest.snapshot_id == "late"


def test_reduce_surfaces_both_transition_and_latest_snapshot_findings() -> None:
    early = _snapshot([_spec("data.migrations", {"applied_count": 97})], snapshot_id="early")
    late = _snapshot(
        [
            _spec("data.migrations", {"applied_count": 96}),
            _spec("github.workflow_runs", _runs(("pipeline-health", "success"))),
        ],
        observed_at=T0 + timedelta(hours=1),
        snapshot_id="late",
    )

    _, found = reduce_snapshots([early, late])

    assert "counter_went_backwards" in _codes(found)  # from the transition
    assert "latest_only_scheduled_lane" in _codes(found)  # from the latest snapshot


def test_reduce_of_nothing_is_not_an_error() -> None:
    assert reduce_snapshots([]) == (None, ())


def test_findings_are_deterministically_ordered() -> None:
    snap = _snapshot(
        [
            _spec("data.migrations", {"applied_count": 97}),
            _spec("code.required_migrations", 96),
        ]
    )
    first, second = check_snapshot(snap), check_snapshot(snap)

    assert first == second
    assert list(first) == sorted(first, key=lambda c: (c.subject, c.code))


def test_a_finding_is_frozen() -> None:
    found = check_snapshot(
        _snapshot([_spec("github.workflow_runs", _runs(("pipeline-health", "success")))])
    )
    with pytest.raises(Exception, match=r"frozen|Instance is frozen"):
        found[0].code = "tampered"  # type: ignore[misc]


def test_semantics_version_is_pinned() -> None:
    """Changing what a check MEANS is a version bump — consumers diff across wakes.
    v3 retired `migration_drift` (both forms) and added `latest_only_scheduled_lane`."""
    assert SEMANTICS_VERSION == 3
    assert CROSS_SOURCE_EQUALITIES == ()
    assert LEAF_INTERNAL_EQUALITIES == ()

# --------------------------------------------------------------------------
# Regression: shapes taken from the REAL checked-in snapshot
#
# The first cut of _check_leaf_probe_agreement demanded leaf.value ==
# probe.value and produced three false criticals when run against
# docs/product/state/latest-snapshot.json, because the actual convention is
# leaf = full detail, probe = provenance summary. These pin the corrected rule.
# --------------------------------------------------------------------------


def test_probe_summarising_its_leaf_is_not_a_contradiction() -> None:
    """github.open_prs: nine-entry list on the leaf, {"count": 9} on the probe."""
    snap = _snapshot([_spec("github.open_prs", [{"number": 144}, {"number": 143}])])
    summarised = snap.model_copy(
        update={
            "probes": [snap.probes[0].model_copy(update={"value": {"count": 2, "all_draft": True}})]
        }
    )
    assert "leaf_probe_value_mismatch" not in _codes(check_snapshot(summarised))


def test_extra_keys_on_either_side_are_not_a_contradiction() -> None:
    """data.freshness: the leaf carries signals_note, the probe carries job_runs_last_3d.

    Both were flagged critical by the first cut; neither side contradicts the other.
    """
    snap = _snapshot(
        [_spec("data.freshness", {"prices_max_dt": "2026-08-18", "signals_note": "frozen"})]
    )
    other_keys = snap.model_copy(
        update={
            "probes": [
                snap.probes[0].model_copy(
                    update={
                        "value": {
                            "prices_max_dt": "2026-08-18",
                            "job_runs_last_3d": "all green",
                        }
                    }
                )
            ]
        }
    )
    assert "leaf_probe_value_mismatch" not in _codes(check_snapshot(other_keys))


def test_a_shared_key_that_actually_disagrees_is_still_critical() -> None:
    """The check must not have been softened into uselessness."""
    snap = _snapshot([_spec("data.freshness", {"prices_max_dt": "2026-08-18"})])
    mismatched = snap.model_copy(
        update={
            "probes": [snap.probes[0].model_copy(update={"value": {"prices_max_dt": "2026-08-11"}})]
        }
    )

    found = check_snapshot(mismatched)
    hit = next(c for c in found if c.code == "leaf_probe_value_mismatch")

    assert hit.severity == "critical"
    assert hit.subject == "data.freshness.prices_max_dt"
    assert (hit.left, hit.right) == ("'2026-08-18'", "'2026-08-11'")


def test_the_old_one_leaf_migration_shape_no_longer_fires() -> None:
    """Even a snapshot still carrying the pre-#189 `required_migrations` key gets no
    `migration_drift`: the constant it compared against does not exist."""
    snap = _snapshot(
        [
            _spec(
                "data.migrations",
                {"applied_count": 97, "latest_version": "20260821080458", "required_migrations": 96},
            )
        ]
    )
    assert "migration_drift" not in _codes(check_snapshot(snap))

def test_unbacked_leaf_is_info_not_a_failure() -> None:
    """Probe linkage is a convention (sb1_02_deferred_probe_linkage), not a contract —
    5 of 11 leaves in the real snapshot are unbacked, so warning-level would be noise."""
    snap = _snapshot([_spec("data.coverage", 1)])
    promoted = snap.model_copy(
        update={"data": snap.data.model_copy(update={"migrations": snap.data.coverage})}
    )

    hit = next(c for c in check_snapshot(promoted) if c.code == "unbacked_leaf")
    assert hit.severity == "info"


def test_a_scalar_leaf_disagreeing_with_its_scalar_probe_is_critical() -> None:
    """repository.base_sha is a bare string on BOTH sides in the real snapshot.

    A scalar cannot summarise a scalar, so skipping non-mapping values entirely
    left the snapshot's most load-bearing fact — which commit this state
    describes — completely unchecked.
    """
    snap = _snapshot([_spec("repository.base_sha", "56596fc")])
    forked = snap.model_copy(
        update={
            "repository": snap.repository.model_copy(
                update={
                    "base_sha": snap.repository.base_sha.model_copy(update={"value": "deadbee"})
                }
            )
        }
    )

    hit = next(c for c in check_snapshot(forked) if c.code == "leaf_probe_value_mismatch")

    assert hit.severity == "critical"
    assert hit.subject == "repository.base_sha"
    assert (hit.left, hit.right) == ("'deadbee'", "'56596fc'")


def test_a_probe_summarising_one_level_down_is_not_a_contradiction() -> None:
    """The detail/summary convention has to hold at every depth, not just the top."""
    snap = _snapshot([_spec("data.freshness", {"prices": {"max_dt": "2026-08-18", "rows": 900}})])
    nested = snap.model_copy(
        update={
            "probes": [
                snap.probes[0].model_copy(update={"value": {"prices": {"max_dt": "2026-08-18"}}})
            ]
        }
    )
    assert "leaf_probe_value_mismatch" not in _codes(check_snapshot(nested))


def test_a_nested_shared_scalar_that_disagrees_is_still_critical() -> None:
    snap = _snapshot([_spec("data.freshness", {"prices": {"max_dt": "2026-08-18"}})])
    nested = snap.model_copy(
        update={
            "probes": [
                snap.probes[0].model_copy(update={"value": {"prices": {"max_dt": "2026-08-11"}}})
            ]
        }
    )

    hit = next(c for c in check_snapshot(nested) if c.code == "leaf_probe_value_mismatch")
    assert hit.subject == "data.freshness.prices.max_dt"


# --------------------------------------------------------------------------
# SB2-02's actual completion proof: "Known contradictions fail fixtures".
#
# These run against the repo's own checked-in fixtures, not synthetic ones.
# Before 2026-08-22 all five returned 0 findings above `info` — the proof was
# unmet while the work order was reported complete.
# --------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "project_state_snapshot"


def _fixture(name: str) -> ProjectStateSnapshot:
    return ProjectStateSnapshot.model_validate(json.loads((FIXTURE_DIR / name).read_text()))


def _above_info(snap: ProjectStateSnapshot) -> list[Contradiction]:
    return [c for c in check_snapshot(snap) if c.severity != "info"]


def test_the_contradictory_fixture_fails() -> None:
    """Two probes both named data.migrations — that IS the fixture's contradiction."""
    found = _above_info(_fixture("contradictory.json"))
    dup = next(c for c in found if c.code == "duplicate_probe_name")

    assert dup.severity == "critical"
    assert dup.subject == "data.migrations"
    assert dup.left != dup.right, "the two probes must be reported as differing sources"


def test_the_stale_fixture_fails() -> None:
    """stale.json encodes staleness ONLY in freshness payloads — both timestamps match."""
    found = _above_info(_fixture("stale.json"))
    stale = [c for c in found if c.code == "stale_freshness"]

    assert {c.subject for c in stale} == {"data.freshness", "repository.base_sha"}
    assert all(c.severity == "warning" for c in stale)


@pytest.mark.parametrize("name", ["branch_only.json", "partial.json", "unavailable.json"])
def test_the_legitimate_fixtures_stay_silent(name: str) -> None:
    """These record valid states. A checker that flags them is noise, not signal.

    Specifically pins the false positive removed on 2026-08-22: an
    `uncorroborated_release_identity` rule fired on branch_only (a feature branch
    legitimately differs from production's released commit) and on partial (whose
    `recent_merges` is `status: error`, so nothing COULD corroborate). Both turned
    "could not corroborate" into "contradiction" — the mistake
    `test_cross_source_rule_needs_both_sides_present` already guards against.
    """
    assert _above_info(_fixture(name)) == []


def test_duplicate_probe_names_survive_a_json_round_trip() -> None:
    """build_snapshot rejects duplicates; a snapshot LOADED from JSON never sees it.

    That is every snapshot a wake actually reads, which is why the guard has to
    exist in check_snapshot too and not only at construction.
    """
    snap = _snapshot([_spec("data.migrations", {"applied_count": 97})])
    twinned = snap.model_copy(
        update={
            "probes": [
                *snap.probes,
                snap.probes[0].model_copy(update={"value": {"applied_count": 12}}),
            ]
        }
    )
    reloaded = ProjectStateSnapshot.model_validate_json(twinned.model_dump_json())

    assert "duplicate_probe_name" in _codes(check_snapshot(reloaded))


def test_freshness_within_bound_is_silent() -> None:
    snap = _snapshot([ProbeSpec("data.freshness", "t", lambda: 1, {"age_days": 3})])
    assert "stale_freshness" not in _codes(check_snapshot(snap))


def test_freshness_ignores_non_integer_and_boolean_payloads() -> None:
    """A bool is an int in Python; `True` must not read as an age of 1."""
    for payload in ({"age_days": "13"}, {"age_days": True}, {"age_days": None}, {"other": 99}):
        snap = _snapshot([ProbeSpec("data.freshness", "t", lambda: 1, payload)])
        assert "stale_freshness" not in _codes(check_snapshot(snap)), payload


# --------------------------------------------------------------------------
# v3: a latest-run-only view of a scheduled lane masks reds (2026-09-06)
# --------------------------------------------------------------------------


def _runs(*rows: tuple[str, str]) -> list[dict[str, str]]:
    return [{"name": n, "branch": "main", "conclusion": c, "started": "2026-09-06T00:00:00Z"} for n, c in rows]


def test_a_scheduled_lane_with_one_conclusion_is_flagged_as_latest_only() -> None:
    """The real 2026-09-06 shape: one green pipeline-health row hid three scheduled reds."""
    snap = _snapshot([_spec("github.workflow_runs", _runs(("pipeline-health", "success")))])
    found = [c for c in check_snapshot(snap) if c.code == "latest_only_scheduled_lane"]
    assert [c.subject for c in found] == ["github.workflow_runs.pipeline-health"]
    assert found[0].severity == "info"
    assert (found[0].left, found[0].right) == ("1", str(MIN_SCHEDULED_ROWS))


def test_a_scheduled_lane_with_enough_conclusions_is_silent() -> None:
    rows = _runs(("pipeline-health", "success"), ("pipeline-health", "failure"), ("pipeline-health", "failure"))
    snap = _snapshot([_spec("github.workflow_runs", rows)])
    assert "latest_only_scheduled_lane" not in _codes(check_snapshot(snap))


def test_only_scheduled_lanes_are_held_to_the_depth_rule() -> None:
    """A push-triggered check appears once per push by nature; only lanes with a
    `schedule:` trigger have reds nobody is watching."""
    snap = _snapshot([_spec("github.workflow_runs", _runs(("full-check", "success")))])
    assert "latest_only_scheduled_lane" not in _codes(check_snapshot(snap))


def test_an_absent_scheduled_lane_is_the_wakes_choice_not_a_finding() -> None:
    snap = _snapshot([_spec("github.workflow_runs", _runs(("backup", "success"), ("backup", "success"), ("backup", "success")))])
    assert "latest_only_scheduled_lane" not in _codes(check_snapshot(snap))


def test_scheduled_lanes_mirror_the_workflows_that_carry_a_schedule_trigger() -> None:
    """Measured, not declared: parse every workflow and collect the `name:` of each one
    whose `on:` block has a `schedule:` key. PyYAML reads a bare `on` as the boolean
    True, so both spellings are accepted. Adding or removing a `schedule:` trigger
    without updating SCHEDULED_LANES fails here."""
    import yaml

    workflows = Path(__file__).resolve().parent.parent / ".github" / "workflows"
    scheduled: set[str] = set()
    for path in sorted(workflows.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        on_block = doc.get("on", doc.get(True))
        if isinstance(on_block, dict) and "schedule" in on_block:
            scheduled.add(str(doc["name"]))
    assert scheduled == set(SCHEDULED_LANES)
