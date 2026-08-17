"""Contract tests for the frozen ``ProjectStateSnapshot`` schema (SB1-01).

Pins, against the SB1 packet section of
``docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md``
(shape lines 495-522, rules 524-526, acceptance 528-530):

1. the frozen field SET, by field-set equality on every model (the expected
   sets are hardcoded HERE, not imported, so any schema drift fails);
2. the closed-set / version-bump rule -- adding a field at version 1 fails;
3. ``unavailable``-is-first-class semantics (observed requires a non-null
   value; unavailable/error forbid one; no leaf has a default);
4. the five acceptance fixtures -- stale, unavailable, branch-only, partial,
   contradictory -- all SYNTHETIC (never live data), all validating;
5. normalization determinism -- the same input always produces the same
   normalized snapshot.

Fixtures live in ``tests/fixtures/project_state_snapshot/``.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from asxos.secondbrain.project_state import (
    SCHEMA_VERSION,
    DataState,
    FieldObservation,
    GithubState,
    ProbeRecord,
    ProductionState,
    ProjectStateSnapshot,
    RepositoryState,
)

FIXTURES = Path(__file__).parent / "fixtures" / "project_state_snapshot"
FIXTURE_NAMES = ["stale", "unavailable", "branch_only", "partial", "contradictory"]


def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURES / f"{name}.json").open() as f:
        data: dict[str, Any] = json.load(f)
    return data


def minimal_snapshot_dict() -> dict[str, Any]:
    """A minimal valid v1 snapshot payload for negative-case surgery."""
    observed = {"status": "observed", "value": "x"}
    return {
        "snapshot_id": "snap-synthetic-minimal-0001",
        "schema_version": 1,
        "observed_at": "2026-01-01T00:00:00+00:00",
        "repository": {
            "base_sha": observed,
            "branch": observed,
            "dirty_state": {"status": "observed", "value": False},
        },
        "github": {
            "open_prs": {"status": "observed", "value": []},
            "recent_merges": {"status": "unavailable"},
            "workflow_runs": {"status": "unavailable"},
        },
        "production": {
            "release_identity": observed,
            "scheduler_owners": {"status": "unavailable"},
        },
        "data": {
            "migrations": {"status": "unavailable"},
            "freshness": {"status": "unavailable"},
            "coverage": {"status": "unavailable"},
        },
        "probes": [],
    }


# ---------------------------------------------------------------------------
# 1. Frozen field sets -- field-set equality, hardcoded expected sets.
# ---------------------------------------------------------------------------


def test_top_level_field_set_is_frozen() -> None:
    # Packet lines 496-514: the exact top-level shape, verbatim and only that.
    assert set(ProjectStateSnapshot.model_fields) == {
        "snapshot_id",
        "schema_version",
        "observed_at",
        "repository",
        "github",
        "production",
        "data",
        "probes",
    }


def test_repository_field_set_is_frozen() -> None:
    # Packet lines 499-502.
    assert set(RepositoryState.model_fields) == {"base_sha", "branch", "dirty_state"}


def test_github_field_set_is_frozen() -> None:
    # Packet lines 503-506.
    assert set(GithubState.model_fields) == {"open_prs", "recent_merges", "workflow_runs"}


def test_production_field_set_is_frozen() -> None:
    # Packet lines 507-509.
    assert set(ProductionState.model_fields) == {"release_identity", "scheduler_owners"}


def test_data_field_set_is_frozen() -> None:
    # Packet lines 510-513.
    assert set(DataState.model_fields) == {"migrations", "freshness", "coverage"}


def test_probe_record_field_set_is_frozen() -> None:
    # Packet lines 514-521.
    assert set(ProbeRecord.model_fields) == {
        "name",
        "status",
        "source",
        "observed_at",
        "value",
        "freshness",
        "error_class",
    }


def test_field_observation_field_set_is_frozen() -> None:
    # The leaf wrapper: status vocabulary from packet line 516, value iff observed.
    assert set(FieldObservation.model_fields) == {"status", "value"}


# ---------------------------------------------------------------------------
# 2. Closed set + version-bump rule.
# ---------------------------------------------------------------------------


def test_schema_version_constant_is_1() -> None:
    assert SCHEMA_VERSION == 1


def test_schema_version_is_required_and_pinned() -> None:
    payload = minimal_snapshot_dict()
    ProjectStateSnapshot.model_validate(payload)  # version 1 validates

    payload["schema_version"] = 2
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)

    del payload["schema_version"]
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)


def test_adding_a_top_level_field_at_version_1_fails() -> None:
    payload = minimal_snapshot_dict()
    # Doc-truth/contradiction items are SB2's job (sb2_deferred_contradiction_fields);
    # smuggling one in at v1 must fail, not silently pass through.
    payload["doc_truth"] = {"status": "observed", "value": "smuggled"}
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)


def test_adding_a_section_field_at_version_1_fails() -> None:
    payload = minimal_snapshot_dict()
    payload["repository"]["remote_url"] = {"status": "observed", "value": "smuggled"}
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)


def test_adding_a_probe_field_at_version_1_fails() -> None:
    payload = minimal_snapshot_dict()
    payload["probes"] = [
        {
            "name": "repository.base_sha",
            "status": "observed",
            "source": "synthetic",
            "observed_at": "2026-01-01T00:00:00+00:00",
            "value": "x",
            "retries": 3,  # not a packet field
        }
    ]
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)


def test_adding_a_leaf_wrapper_field_at_version_1_fails() -> None:
    payload = minimal_snapshot_dict()
    payload["repository"]["base_sha"] = {"status": "observed", "value": "x", "note": "smuggled"}
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)


# ---------------------------------------------------------------------------
# 3. Unavailable is first-class (packet line 524).
# ---------------------------------------------------------------------------


def test_observed_requires_a_value() -> None:
    with pytest.raises(ValidationError):
        FieldObservation.model_validate({"status": "observed"})


def test_observed_null_value_is_rejected() -> None:
    # "Observed but null" is unrepresentable -- null-by-accident cannot
    # masquerade as an observation.
    with pytest.raises(ValidationError):
        FieldObservation.model_validate({"status": "observed", "value": None})


@pytest.mark.parametrize("value", [False, 0, "", []])
def test_falsy_but_real_values_are_valid_observations(value: Any) -> None:
    obs = FieldObservation.model_validate({"status": "observed", "value": value})
    assert obs.value == value


def test_unavailable_must_not_carry_a_value() -> None:
    with pytest.raises(ValidationError):
        FieldObservation.model_validate({"status": "unavailable", "value": 0})


def test_unavailable_is_expressible_and_distinct() -> None:
    obs = FieldObservation.model_validate({"status": "unavailable"})
    assert obs.status == "unavailable"
    assert obs.value is None


def test_error_leaf_status_is_expressible() -> None:
    # Leaves share the packet's probe status vocabulary; error DETAIL lives
    # on the backing ProbeRecord (sb1_02_deferred_probe_linkage).
    obs = FieldObservation.model_validate({"status": "error"})
    assert obs.value is None
    with pytest.raises(ValidationError):
        FieldObservation.model_validate({"status": "error", "value": "boom"})


def test_status_vocabulary_is_closed() -> None:
    with pytest.raises(ValidationError):
        FieldObservation.model_validate({"status": "green", "value": "x"})


def test_sections_have_no_defaults() -> None:
    # "Missing probes do not become zero/green" (packet lines 528-529): a leaf
    # that was never probed cannot validate at all -- there is no default.
    with pytest.raises(ValidationError):
        RepositoryState.model_validate({"base_sha": {"status": "unavailable"}})
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(
            {k: v for k, v in minimal_snapshot_dict().items() if k != "data"}
        )


def test_probe_error_requires_error_class() -> None:
    base = {
        "name": "github.recent_merges",
        "status": "error",
        "source": "synthetic",
        "observed_at": "2026-01-01T00:00:00+00:00",
    }
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate(base)
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate({**base, "error_class": ""})
    probe = ProbeRecord.model_validate({**base, "error_class": "network_timeout"})
    assert probe.error_class == "network_timeout"
    assert probe.value is None


def test_probe_observed_forbids_error_class() -> None:
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate(
            {
                "name": "repository.base_sha",
                "status": "observed",
                "source": "synthetic",
                "observed_at": "2026-01-01T00:00:00+00:00",
                "value": "x",
                "error_class": "network_timeout",
            }
        )


def test_probe_unavailable_forbids_value_and_freshness() -> None:
    base = {
        "name": "data.coverage",
        "status": "unavailable",
        "source": "synthetic",
        "observed_at": "2026-01-01T00:00:00+00:00",
    }
    ProbeRecord.model_validate(base)  # bare unavailable is valid
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate({**base, "value": 0})
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate({**base, "freshness": {"age_days": 1}})


def test_probe_name_and_source_must_be_nonempty() -> None:
    base = {
        "name": "x",
        "status": "unavailable",
        "source": "y",
        "observed_at": "2026-01-01T00:00:00+00:00",
    }
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate({**base, "name": ""})
    with pytest.raises(ValidationError):
        ProbeRecord.model_validate({**base, "source": ""})


def test_observed_at_must_be_timezone_aware() -> None:
    payload = minimal_snapshot_dict()
    payload["observed_at"] = "2026-01-01T00:00:00"  # naive -- no offset
    with pytest.raises(ValidationError):
        ProjectStateSnapshot.model_validate(payload)


def test_snapshot_instances_are_immutable() -> None:
    snapshot = ProjectStateSnapshot.model_validate(minimal_snapshot_dict())
    with pytest.raises(ValidationError):
        snapshot.snapshot_id = "snap-synthetic-mutated"
    with pytest.raises(ValidationError):
        snapshot.repository.base_sha = FieldObservation(status="unavailable")


# ---------------------------------------------------------------------------
# 4. The five acceptance fixtures (packet lines 528-530). All synthetic.
# ---------------------------------------------------------------------------


def all_leaves(snapshot: ProjectStateSnapshot) -> dict[str, FieldObservation]:
    leaves: dict[str, FieldObservation] = {}
    for section_name in ("repository", "github", "production", "data"):
        section = getattr(snapshot, section_name)
        for field_name in type(section).model_fields:
            leaves[f"{section_name}.{field_name}"] = getattr(section, field_name)
    return leaves


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_validates(name: str) -> None:
    snapshot = ProjectStateSnapshot.model_validate(load_fixture(name))
    assert snapshot.schema_version == SCHEMA_VERSION


def test_stale_fixture_carries_staleness_verbatim() -> None:
    # The schema records freshness; judging staleness is SB2's job
    # (sb2_deferred_staleness_evaluation).
    snapshot = ProjectStateSnapshot.model_validate(load_fixture("stale"))
    assert snapshot.observed_at == datetime(2025, 6, 1, tzinfo=UTC)
    freshness = snapshot.data.freshness
    assert freshness.status == "observed"
    assert freshness.value == {"prices_as_of": "2025-05-19", "age_days": 13}
    assert snapshot.probes[1].freshness == {"age_days": 13}


def test_unavailable_fixture_is_honest_everywhere() -> None:
    # A total observability outage is still a VALID snapshot -- and nothing
    # in it defaults to a value ("missing probes do not become zero/green").
    snapshot = ProjectStateSnapshot.model_validate(load_fixture("unavailable"))
    for path, leaf in all_leaves(snapshot).items():
        assert leaf.status == "unavailable", path
        assert leaf.value is None, path
    assert all(probe.status == "unavailable" for probe in snapshot.probes)


def test_branch_only_fixture_records_branch_identity() -> None:
    # "Branch-only is never main truth" (packet lines 524-525) is a CONSUMER rule;
    # the schema's job is to record the branch identity that lets a consumer
    # apply it. The fixture shows branch work that is visibly not on main.
    snapshot = ProjectStateSnapshot.model_validate(load_fixture("branch_only"))
    assert snapshot.repository.branch.value == "claude/synthetic-feature-branch"
    assert snapshot.repository.branch.value != "main"
    open_prs = snapshot.github.open_prs.value
    assert isinstance(open_prs, list)
    first = open_prs[0]
    assert isinstance(first, dict)
    assert first["merged"] is False
    assert snapshot.github.recent_merges.value == []


def test_partial_fixture_mixes_statuses_without_invention() -> None:
    snapshot = ProjectStateSnapshot.model_validate(load_fixture("partial"))
    statuses = {leaf.status for leaf in all_leaves(snapshot).values()}
    assert statuses == {"observed", "unavailable", "error"}
    # The errored leaf carries no value; its detail lives in the probe log.
    assert snapshot.github.recent_merges.status == "error"
    assert snapshot.github.recent_merges.value is None
    error_probes = [p for p in snapshot.probes if p.status == "error"]
    assert [p.error_class for p in error_probes] == ["http_5xx"]


def test_contradictory_fixture_validates_and_carries_both_claims() -> None:
    # Contradiction DETECTION is deferred by name to SB2
    # (sb2_deferred_contradiction_fields): SB1 records faithfully, so a
    # self-contradictory snapshot VALIDATES with every conflicting claim intact.
    snapshot = ProjectStateSnapshot.model_validate(load_fixture("contradictory"))
    migrations = snapshot.data.migrations.value
    assert isinstance(migrations, dict)
    assert migrations["applied_count"] == 12
    probe_values = [
        p.value for p in snapshot.probes if p.name == "data.migrations" and p.value is not None
    ]
    assert {"applied_count": 12} in probe_values
    assert {"file_count": 14} in probe_values  # disagrees with the leaf -- kept
    # Release identity disagrees with repository.base_sha and recent merges -- kept.
    assert snapshot.production.release_identity.value != snapshot.repository.base_sha.value


# ---------------------------------------------------------------------------
# 5. Normalization determinism (packet line 528).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_same_inputs_produce_the_same_normalized_snapshot(name: str) -> None:
    first = ProjectStateSnapshot.model_validate(load_fixture(name))
    second = ProjectStateSnapshot.model_validate(load_fixture(name))
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_round_trip_is_lossless(name: str) -> None:
    original = ProjectStateSnapshot.model_validate(load_fixture(name))
    round_tripped = ProjectStateSnapshot.model_validate_json(original.model_dump_json())
    assert round_tripped == original
    assert round_tripped.model_dump_json() == original.model_dump_json()
