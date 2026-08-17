"""Execution-controller contracts: transitions, evidence, and selection."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from asxos.secondbrain.execution import (
    CheckResult,
    CompiledRoadmap,
    MissionEnvelope,
    MissionEvent,
    MissionReceipt,
    MissionState,
    MissionTimeline,
    RoadmapItem,
    select_next_item,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def item(
    item_id: str,
    order: int,
    *,
    dependencies: tuple[str, ...] = (),
    external_gates: tuple[str, ...] = (),
) -> RoadmapItem:
    return RoadmapItem(
        item_id=item_id,
        objective=f"Build {item_id}",
        route="arbi-mission",
        dependencies=dependencies,
        external_gates=external_gates,
        completion_proof="Tests and observed outcome",
        order=order,
        source="synthetic.md",
        source_line=order + 1,
    )


def roadmap(*items: RoadmapItem) -> CompiledRoadmap:
    return CompiledRoadmap(
        source="synthetic.md",
        source_sha256="a" * 64,
        authority="candidate_backlog",
        items=items,
    )


def event(
    sequence: int,
    state: MissionState,
    *,
    evidence: tuple[str, ...] = (),
    mission_id: str = "mission-a",
    roadmap_item_id: str = "SB1-02",
) -> MissionEvent:
    return MissionEvent(
        mission_id=mission_id,
        roadmap_item_id=roadmap_item_id,
        sequence=sequence,
        state=state,
        observed_at=NOW,
        evidence=evidence,
    )


def test_compiled_roadmap_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate work-order IDs"):
        roadmap(item("SB1-02", 0), item("SB1-02", 1))


def test_compiled_roadmap_rejects_missing_dependency() -> None:
    with pytest.raises(ValidationError, match="undeclared work orders: SB1-01"):
        roadmap(item("SB1-02", 0, dependencies=("SB1-01",)))


def test_compiled_roadmap_rejects_dependency_cycle() -> None:
    with pytest.raises(ValidationError, match="dependency cycle"):
        roadmap(
            item("SB1-01", 0, dependencies=("SB1-02",)),
            item("SB1-02", 1, dependencies=("SB1-01",)),
        )


def test_claim_states_require_evidence() -> None:
    with pytest.raises(ValidationError, match="requires at least one evidence"):
        event(1, MissionState.BLOCKED)


def valid_envelope_payload() -> dict[str, object]:
    return {
        "mission_id": "sb-loop-wave-1",
        "programme_id": "outcome-engine-second-brain",
        "roadmap_item_id": "SB1-02",
        "roadmap_stage": "wave-2",
        "source_authority": "direct_instruction",
        "objective": "Build read-only project-state probes",
        "baseline_sha": "a" * 40,
        "scope": ("asxos/secondbrain/", "tests/test_secondbrain_execution.py"),
        "allowed_actions": ("edit_code", "run_tests"),
        "forbidden_boundaries": ("production_write", "merge"),
        "dependencies": ("SB1-01",),
        "required_inputs": ("ProjectStateSnapshot v1",),
        "expected_artifacts": ("probe adapters",),
        "acceptance_checks": ("pytest tests/test_secondbrain_execution.py",),
        "independent_reviews": ("security-engineer",),
        "stop_conditions": ("secret required",),
        "rollback": "revert the branch commit",
        "outcome_observation": "normalized snapshot fixture matches",
    }


def test_mission_envelope_accepts_only_executable_authority() -> None:
    envelope = MissionEnvelope.model_validate(valid_envelope_payload())
    assert envelope.max_repair_attempts == 2

    payload = valid_envelope_payload()
    payload["source_authority"] = "candidate_backlog"
    with pytest.raises(ValidationError):
        MissionEnvelope.model_validate(payload)


def test_mission_envelope_rejects_unbounded_scope() -> None:
    payload = valid_envelope_payload()
    payload["scope"] = ("**/*",)
    with pytest.raises(ValidationError, match="bounded repository paths"):
        MissionEnvelope.model_validate(payload)


def test_mission_envelope_caps_repairs_at_two() -> None:
    payload = valid_envelope_payload()
    payload["max_repair_attempts"] = 3
    with pytest.raises(ValidationError):
        MissionEnvelope.model_validate(payload)


def valid_receipt_payload() -> dict[str, object]:
    return {
        "mission_id": "sb-loop-wave-1",
        "roadmap_item_id": "SB1-02",
        "baseline_sha": "a" * 40,
        "head_sha": "b" * 40,
        "changed_files": ("asxos/secondbrain/execution.py",),
        "checks": (
            CheckResult(
                name="targeted-tests",
                command="pytest tests/test_secondbrain_execution.py",
                status="PASS",
                evidence="ci://run/123",
            ),
        ),
        "review_receipts": ("review://security/pass",),
        "pr_url": "https://github.com/example/repo/pull/1",
        "blockers": (),
        "readiness": "READY_FOR_REVIEW",
        "emitted_at": NOW,
    }


def test_ready_receipt_requires_green_checks_and_pr() -> None:
    receipt = MissionReceipt.model_validate(valid_receipt_payload())
    assert receipt.readiness == "READY_FOR_REVIEW"

    payload = valid_receipt_payload()
    payload["checks"] = (
        CheckResult(
            name="targeted-tests",
            command="pytest tests/test_secondbrain_execution.py",
            status="FAIL",
            evidence="ci://run/123",
        ),
    )
    with pytest.raises(ValidationError, match="requires every check to pass"):
        MissionReceipt.model_validate(payload)


def test_blocked_receipt_requires_named_blocker() -> None:
    payload = valid_receipt_payload()
    payload.update({"readiness": "BLOCKED", "pr_url": None, "blockers": ()})
    with pytest.raises(ValidationError, match="requires at least one blocker"):
        MissionReceipt.model_validate(payload)


def test_timeline_requires_proposed_first() -> None:
    with pytest.raises(ValidationError, match="start at PROPOSED"):
        MissionTimeline(events=(event(1, MissionState.CHALLENGED),))


def test_timeline_rejects_sequence_gap() -> None:
    with pytest.raises(ValidationError, match="sequences must be contiguous"):
        MissionTimeline(
            events=(
                event(1, MissionState.PROPOSED),
                event(3, MissionState.CHALLENGED),
            )
        )


def test_timeline_rejects_skipped_transition() -> None:
    with pytest.raises(ValidationError, match="PROPOSED -> RUNNING"):
        MissionTimeline(
            events=(
                event(1, MissionState.PROPOSED),
                event(2, MissionState.RUNNING),
            )
        )


def test_valid_timeline_reaches_observed() -> None:
    timeline = MissionTimeline(
        events=(
            event(1, MissionState.PROPOSED),
            event(2, MissionState.CHALLENGED),
            event(3, MissionState.APPROVED),
            event(4, MissionState.RUNNING),
            event(5, MissionState.READY_FOR_REVIEW, evidence=("ci://run/1",)),
            event(6, MissionState.MERGED_BY_JAMES, evidence=("git://sha/abc",)),
            event(7, MissionState.OBSERVED, evidence=("runtime://run/2",)),
        )
    )
    assert timeline.current_state == MissionState.OBSERVED
    assert timeline.roadmap_item_id == "SB1-02"


def test_candidate_backlog_is_inert_without_activation() -> None:
    compiled = roadmap(item("SB1-01", 0))
    result = select_next_item(compiled, activated_item_ids=())
    assert result.status == "NO_ACTIVATION"
    assert result.item_id is None


def test_unknown_activation_fails_closed() -> None:
    compiled = roadmap(item("SB1-01", 0))
    with pytest.raises(ValueError, match="not declared: SB9-99"):
        select_next_item(compiled, activated_item_ids=("SB9-99",))


def test_selector_chooses_first_activated_ready_item() -> None:
    compiled = roadmap(item("SB1-01", 0), item("SB1-02", 1))
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-01", "SB1-02"),
    )
    assert result.status == "READY"
    assert result.item_id == "SB1-01"


def test_merge_without_observation_does_not_satisfy_dependency() -> None:
    compiled = roadmap(
        item("SB1-01", 0),
        item("SB1-02", 1, dependencies=("SB1-01",)),
    )
    merged = MissionTimeline(
        events=(
            event(1, MissionState.PROPOSED, roadmap_item_id="SB1-01"),
            event(2, MissionState.CHALLENGED, roadmap_item_id="SB1-01"),
            event(3, MissionState.APPROVED, roadmap_item_id="SB1-01"),
            event(4, MissionState.RUNNING, roadmap_item_id="SB1-01"),
            event(
                5,
                MissionState.READY_FOR_REVIEW,
                evidence=("ci://green",),
                roadmap_item_id="SB1-01",
            ),
            event(
                6,
                MissionState.MERGED_BY_JAMES,
                evidence=("git://merge",),
                roadmap_item_id="SB1-01",
            ),
        )
    )
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-02",),
        timelines={"SB1-01": merged},
    )
    assert result.status == "BLOCKED"
    assert result.blockers == ("dependency not observed: SB1-01",)


def test_observed_dependency_unlocks_next_item() -> None:
    compiled = roadmap(
        item("SB1-01", 0),
        item("SB1-02", 1, dependencies=("SB1-01",)),
    )
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-02",),
        completed_item_ids=("SB1-01",),
    )
    assert result.status == "READY"
    assert result.item_id == "SB1-02"


def test_external_gate_blocks_until_explicitly_satisfied() -> None:
    compiled = roadmap(item("P3-03", 0, external_gates=("approvals",)))
    blocked = select_next_item(compiled, activated_item_ids=("P3-03",))
    ready = select_next_item(
        compiled,
        activated_item_ids=("P3-03",),
        satisfied_external_gates=("approvals",),
    )
    assert blocked.status == "BLOCKED"
    assert blocked.blockers == ("external gate not satisfied: approvals",)
    assert ready.status == "READY"


def test_active_mission_prevents_task_switching() -> None:
    compiled = roadmap(item("SB1-01", 0), item("SB1-02", 1))
    active = MissionTimeline(
        events=(
            event(1, MissionState.PROPOSED),
            event(2, MissionState.CHALLENGED),
            event(3, MissionState.APPROVED),
            event(4, MissionState.RUNNING),
        )
    )
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-02", "SB1-01"),
        timelines={"SB1-02": active},
    )
    assert result.status == "ACTIVE"
    assert result.item_id == "SB1-02"


def test_blocked_mission_prevents_task_switching_and_reports_block() -> None:
    compiled = roadmap(item("SB1-01", 0), item("SB1-02", 1))
    blocked = MissionTimeline(
        events=(
            event(1, MissionState.PROPOSED),
            event(2, MissionState.CHALLENGED),
            event(3, MissionState.BLOCKED, evidence=("blocker://missing-input",)),
        )
    )
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-01", "SB1-02"),
        timelines={"SB1-02": blocked},
    )
    assert result.status == "BLOCKED"
    assert result.item_id == "SB1-02"
    assert result.blockers == ("mission state is BLOCKED",)


def test_stopped_mission_requires_explicit_reactivation() -> None:
    compiled = roadmap(item("SB1-01", 0))
    stopped = MissionTimeline(
        events=(
            event(1, MissionState.PROPOSED, roadmap_item_id="SB1-01"),
            event(
                2,
                MissionState.STOPPED,
                evidence=("stop://authority-boundary",),
                roadmap_item_id="SB1-01",
            ),
        )
    )
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-01",),
        timelines={"SB1-01": stopped},
    )
    assert result.status == "BLOCKED"
    assert result.blockers == ("mission state is STOPPED; explicit reactivation is required",)


def test_all_activated_items_observed_is_complete() -> None:
    compiled = roadmap(item("SB1-01", 0))
    result = select_next_item(
        compiled,
        activated_item_ids=("SB1-01",),
        completed_item_ids=("SB1-01",),
    )
    assert result.status == "COMPLETE"
