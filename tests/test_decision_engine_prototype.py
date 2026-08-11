"""Adversarial contract and surface tests for the synthetic decision-engine slice."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from asxos.domain.decision_engine.demo import build_demo_brief
from asxos.domain.decision_engine.renderer import (
    presentation_for,
    render_decision_brief,
)
from asxos.domain.decision_engine.types import (
    ACTION_STATES,
    UNIVERSAL_CONSTRAINTS,
    ArchitectureStage,
    ChallengeResult,
    DecisionBrief,
    DecisionCase,
    DecisionPacket,
    EvidencePacket,
    MemoVerdict,
    PortfolioAssessment,
    RecommendationState,
    SizeRange,
    TaxAssessmentReference,
    ThesisVersion,
    TradingSessionCalendar,
    UpstreamArtifactHashes,
    default_packet_expiry,
    memo_verdict_for,
    verify_content_hash,
)
from asxos.prototype.app import app


def _without_hashes(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_hashes(item)
            for key, item in value.items()
            if key != "content_hash"
        }
    if isinstance(value, list | tuple):
        return type(value)(_without_hashes(item) for item in value)
    return value


def _rebuild_case(payload: dict[str, Any]) -> DecisionCase:
    """Re-seal a mutated case so a targeted invariant, not an old hash, is tested."""
    clean = _without_hashes(payload)
    evidence = EvidencePacket.model_validate(clean["evidence"])
    thesis = ThesisVersion.model_validate(clean["thesis"])
    challenge = ChallengeResult.model_validate(clean["challenge"])
    portfolio = PortfolioAssessment.model_validate(clean["portfolio"])
    decision_payload = clean["decision"]
    tax_reference = TaxAssessmentReference.model_validate(
        decision_payload["tax_assessment_reference"]
    )
    decision_payload["tax_assessment_reference"] = tax_reference
    decision_payload["upstream_hashes"] = UpstreamArtifactHashes(
        evidence_packet=evidence.content_hash,
        thesis_version=thesis.content_hash,
        challenge_result=challenge.content_hash,
        portfolio_assessment=portfolio.content_hash,
        tax_assessment_reference=tax_reference.content_hash,
    ).model_dump(mode="python")
    decision = DecisionPacket.model_validate(decision_payload)
    return DecisionCase(
        case_id=clean["case_id"],
        label=clean["label"],
        changed_since_prior=clean["changed_since_prior"],
        evidence=evidence,
        thesis=thesis,
        challenge=challenge,
        portfolio=portfolio,
        decision=decision,
    )


def _case_for_state(state: RecommendationState) -> DecisionCase:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["case_id"] = f"case-{state}"
    payload["portfolio"]["assessment_state"] = state
    payload["decision"]["recommendation_state"] = state
    payload["decision"]["decision_packet_id"] = f"dpk-{state}"
    cutoff = payload["decision"]["knowledge_cutoff"]
    calendar = TradingSessionCalendar.model_validate(
        payload["decision"]["trading_calendar"]
    )
    expiry = default_packet_expiry(cutoff, state, calendar)
    payload["evidence"]["expires_at"] = expiry
    payload["decision"]["expires_at"] = expiry
    payload["decision"]["expiry_reason"] = "default"
    if state not in ACTION_STATES:
        zero = {"minimum_pct": Decimal("0"), "maximum_pct": Decimal("0")}
        payload["portfolio"]["size_range"] = zero
        payload["portfolio"]["loss_budget_aud"] = Decimal("0")
        payload["decision"]["size_range"] = zero
    return _rebuild_case(payload)


def _brief_for_case(case: DecisionCase) -> DecisionBrief:
    source = build_demo_brief()
    return DecisionBrief(
        title=source.title,
        as_of=source.as_of,
        disclaimer=source.disclaimer,
        one_thing=source.one_thing,
        architecture_stages=source.architecture_stages,
        cases=(case,),
    )


def test_demo_builds_two_complete_content_addressed_identity_chains() -> None:
    brief = build_demo_brief()

    assert [case.case_id for case in brief.cases] == ["paper-ready", "blocked-abstain"]
    assert [case.decision.recommendation_state for case in brief.cases] == [
        "initiate",
        "abstain",
    ]
    for case in brief.cases:
        assert case.thesis.security_id.startswith("sec-synthetic-")
        assert case.evidence.data_mode == "synthetic"
        assert case.decision.model_independence is True
        assert case.decision.tax_assessment_reference.tax_assessment_id
        assert all(
            verify_content_hash(artifact)
            for artifact in (
                case.evidence,
                case.thesis,
                case.challenge,
                case.portfolio,
                case.decision.tax_assessment_reference,
                case.decision,
            )
        )
        assert case.decision.upstream_hashes == UpstreamArtifactHashes(
            evidence_packet=case.evidence.content_hash,
            thesis_version=case.thesis.content_hash,
            challenge_result=case.challenge.content_hash,
            portfolio_assessment=case.portfolio.content_hash,
            tax_assessment_reference=case.decision.tax_assessment_reference.content_hash,
        )


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("initiate", "ADD"),
        ("add", "ADD"),
        ("trim", "TRIM"),
        ("exit_review", "EXIT-CANDIDATE"),
        ("watch", "REVIEW"),
        ("avoid", "REVIEW"),
        ("abstain", "REVIEW"),
        (None, "GOOD HOLD"),
    ],
)
def test_state_to_memo_verdict_mapping_is_exhaustive(
    state: RecommendationState | None, expected: MemoVerdict
) -> None:
    assert memo_verdict_for(state) == expected


@pytest.mark.parametrize(
    ("state", "days", "expected"),
    [
        ("initiate", 5, datetime(2026, 8, 17, 8, tzinfo=UTC)),
        ("add", 5, datetime(2026, 8, 17, 8, tzinfo=UTC)),
        ("trim", 5, datetime(2026, 8, 17, 8, tzinfo=UTC)),
        ("exit_review", 5, datetime(2026, 8, 17, 8, tzinfo=UTC)),
        ("watch", 21, datetime(2026, 9, 8, 8, tzinfo=UTC)),
        ("avoid", 21, datetime(2026, 9, 8, 8, tzinfo=UTC)),
        ("abstain", 21, datetime(2026, 9, 8, 8, tzinfo=UTC)),
    ],
)
def test_f3_expiry_defaults_are_resolved_by_the_injected_session_calendar(
    state: RecommendationState, days: int, expected: datetime
) -> None:
    case = _case_for_state(state)
    payload = _without_hashes(case.decision.model_dump(mode="python"))
    payload.pop("expires_at")

    packet = DecisionPacket.model_validate(payload)

    assert days in {5, 21}
    assert packet.expires_at == expected


def test_exchange_holiday_is_not_counted_as_a_trading_session() -> None:
    cutoff = datetime(2026, 12, 18, 5, tzinfo=UTC)
    session_dates = (21, 22, 23, 24, 29)
    calendar = TradingSessionCalendar(
        calendar_id="XASX",
        calendar_version="asx-2026-test-fixture",
        sessions=tuple(datetime(2026, 12, day, 5, tzinfo=UTC) for day in session_dates),
    )

    expiry = default_packet_expiry(cutoff, "initiate", calendar)

    assert expiry == datetime(2026, 12, 29, 5, tzinfo=UTC)
    assert all(session.date().isoformat() != "2026-12-25" for session in calendar.sessions)


def test_decision_packet_requires_a_deterministic_trading_calendar() -> None:
    payload = _without_hashes(
        build_demo_brief().cases[0].decision.model_dump(mode="python")
    )
    payload.pop("trading_calendar")

    with pytest.raises(ValidationError, match="trading_calendar"):
        DecisionPacket.model_validate(payload)


def test_event_driven_expiry_may_be_earlier_but_never_later_than_f3_default() -> None:
    decision = build_demo_brief().cases[0].decision
    payload = _without_hashes(decision.model_dump(mode="python"))
    payload["expiry_reason"] = "material_event"
    payload["expires_at"] = decision.knowledge_cutoff + timedelta(days=1)
    assert DecisionPacket.model_validate(payload).expires_at == payload["expires_at"]

    payload["expires_at"] = default_packet_expiry(
        decision.knowledge_cutoff,
        decision.recommendation_state,
        decision.trading_calendar,
    ) + timedelta(seconds=1)
    with pytest.raises(ValidationError, match="strictly earlier"):
        DecisionPacket.model_validate(payload)

    payload["expires_at"] = default_packet_expiry(
        decision.knowledge_cutoff,
        decision.recommendation_state,
        decision.trading_calendar,
    )
    with pytest.raises(ValidationError, match="strictly earlier"):
        DecisionPacket.model_validate(payload)


@pytest.mark.parametrize("state", ["initiate", "add", "trim", "exit_review"])
def test_revise_challenge_cannot_reach_any_action_state(state: RecommendationState) -> None:
    payload = _case_for_state(state).model_dump(mode="python")
    payload["challenge"]["outcome"] = "revise"

    with pytest.raises(ValidationError, match="revise challenge cannot accompany"):
        _rebuild_case(payload)


def test_blocking_revise_challenge_forces_abstain() -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["challenge"]["outcome"] = "revise"
    payload["challenge"]["findings"][0]["severity"] = "blocking"

    with pytest.raises(ValidationError, match="blocking challenge finding must force"):
        _rebuild_case(payload)


@pytest.mark.parametrize("status", ["fail", "unknown"])
def test_unresolved_blocking_constraint_rejects_action(status: str) -> None:
    payload = build_demo_brief().cases[0].portfolio.model_dump(mode="python")
    payload = _without_hashes(payload)
    payload["constraints"][0]["status"] = status

    with pytest.raises(ValidationError, match="blocking constraint must block"):
        PortfolioAssessment.model_validate(payload)


def test_unknown_reporting_only_constraint_does_not_invent_a_hard_risk_mandate() -> None:
    payload = _without_hashes(
        build_demo_brief().cases[0].portfolio.model_dump(mode="python")
    )
    payload["constraints"] += (
        {
            "name": "portfolio_beta",
            "status": "unknown",
            "blocking": False,
            "detail": "Beta is reporting-only until the calibrated risk mandate exists.",
        },
    )

    assessment = PortfolioAssessment.model_validate(payload)
    assert assessment.assessment_state == "initiate"
    assert assessment.constraints[-1].name == "portfolio_beta"


def test_constraints_checked_must_exactly_reconcile_to_portfolio() -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["decision"]["constraints_checked"] = ("model_a_quarantine",)

    with pytest.raises(ValidationError, match="exactly match portfolio constraints"):
        _rebuild_case(payload)


@pytest.mark.parametrize(
    "path",
    [
        ("evidence", "items", 0, "claim"),
        ("thesis", "thesis_summary"),
        ("challenge", "strongest_bear_case"),
        ("portfolio", "marginal_risk"),
        ("decision", "decision_ask"),
        ("decision", "tax_assessment_reference", "tax_assessment_id"),
        ("decision", "model_and_prompt_manifest", 0, "version"),
    ],
)
def test_any_artifact_mutation_with_retained_hash_is_rejected(path: tuple[Any, ...]) -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    target: Any = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = "tampered"

    with pytest.raises(ValidationError, match="content_hash does not match"):
        DecisionCase.model_validate(payload)


def test_decision_hash_manifest_commits_to_changed_upstream_content() -> None:
    case = build_demo_brief().cases[0]
    thesis_payload = _without_hashes(case.thesis.model_dump(mode="python"))
    thesis_payload["thesis_summary"] = "Validly re-sealed but different thesis content."
    changed_thesis = ThesisVersion.model_validate(thesis_payload)

    with pytest.raises(ValidationError, match="upstream hashes do not match"):
        DecisionCase(
            case_id=case.case_id,
            label=case.label,
            changed_since_prior=case.changed_since_prior,
            evidence=case.evidence,
            thesis=changed_thesis,
            challenge=case.challenge,
            portfolio=case.portfolio,
            decision=case.decision,
        )


def test_contracts_are_deeply_immutable_and_revalidation_catches_model_copy() -> None:
    case = build_demo_brief().cases[0]
    assert isinstance(case.decision.model_and_prompt_manifest, tuple)
    with pytest.raises(ValidationError, match="frozen"):
        case.decision.model_and_prompt_manifest[0].version = "changed"
    with pytest.raises(ValidationError, match="frozen"):
        case.decision.decision_ask = "changed"

    copied = case.decision.model_copy(update={"decision_ask": "bypassed validation"})
    assert not verify_content_hash(copied)
    brief = build_demo_brief().model_copy(
        update={"cases": (case.model_copy(update={"decision": copied}),)}
    )
    with pytest.raises(ValidationError, match="content_hash does not match"):
        render_decision_brief(brief, evaluated_at=case.decision.knowledge_cutoff)


@pytest.mark.parametrize(
    "forbidden",
    [
        "model_a",
        "model_a_ml",
        "model_a_v2",
        "prefix model_a_ml signal",
        "Model-A",
        "model a",
        "v1_5",
    ],
)
def test_model_a_and_v1_5_are_rejected_from_manifest(forbidden: str) -> None:
    payload = _without_hashes(
        build_demo_brief().cases[0].decision.model_dump(mode="python")
    )
    payload["model_and_prompt_manifest"][1]["version"] = forbidden

    with pytest.raises(ValidationError, match="quarantined"):
        DecisionPacket.model_validate(payload)


def test_explicit_model_independence_and_quarantine_gate_are_mandatory() -> None:
    payload = _without_hashes(
        build_demo_brief().cases[0].decision.model_dump(mode="python")
    )
    payload["model_independence"] = False
    with pytest.raises(ValidationError, match="literal_error"):
        DecisionPacket.model_validate(payload)

    case_payload = build_demo_brief().cases[0].model_dump(mode="python")
    case_payload["portfolio"]["constraints"] = tuple(
        item
        for item in case_payload["portfolio"]["constraints"]
        if item["name"] != "model_a_quarantine"
    )
    case_payload["decision"]["constraints_checked"] = tuple(
        name
        for name in case_payload["decision"]["constraints_checked"]
        if name != "model_a_quarantine"
    )
    with pytest.raises(ValidationError, match="Model A quarantine constraint"):
        _rebuild_case(case_payload)


@pytest.mark.parametrize(
    "constraint_name",
    sorted(UNIVERSAL_CONSTRAINTS - {"model_a_quarantine"}),
)
def test_every_ratified_universal_constraint_is_mandatory(constraint_name: str) -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["portfolio"]["constraints"] = tuple(
        item for item in payload["portfolio"]["constraints"] if item["name"] != constraint_name
    )
    payload["decision"]["constraints_checked"] = tuple(
        name for name in payload["decision"]["constraints_checked"] if name != constraint_name
    )

    with pytest.raises(ValidationError, match="missing universal constraints"):
        _rebuild_case(payload)


def test_universal_constraints_cannot_be_downgraded_to_reporting_only() -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    target = next(
        item
        for item in payload["portfolio"]["constraints"]
        if item["name"] == "no_broker_execution"
    )
    target["blocking"] = False

    with pytest.raises(ValidationError, match="universal constraints must be blocking"):
        _rebuild_case(payload)


def test_typed_tax_reference_blocks_action_when_not_ready() -> None:
    payload = _without_hashes(
        build_demo_brief().cases[0].decision.model_dump(mode="python")
    )
    payload["tax_assessment_reference"]["readiness"] = "unknown"

    with pytest.raises(ValidationError, match="tax readiness"):
        DecisionPacket.model_validate(payload)

    blocked = build_demo_brief().cases[1]
    assert blocked.decision.tax_assessment_reference.readiness == "unknown"
    assert blocked.decision.recommendation_state == "abstain"


def test_security_master_identity_replaces_ticker_regex_identity() -> None:
    payload = _without_hashes(build_demo_brief().cases[0].thesis.model_dump(mode="python"))
    payload.update(security_id="sec-live-hubs", symbol="HUBS", exchange="NYSE")

    thesis = ThesisVersion.model_validate(payload)

    assert thesis.security_id == "sec-live-hubs"
    assert (thesis.symbol, thesis.exchange) == ("HUBS", "NYSE")


def test_evidence_tier_and_data_mode_are_separate_and_cannot_be_mixed() -> None:
    case = build_demo_brief().cases[0]
    item = case.evidence.items[0]
    assert item.evidence_tier == "verified"
    assert item.data_mode == "synthetic"

    payload = _without_hashes(case.evidence.model_dump(mode="python"))
    payload["data_mode"] = "real"
    with pytest.raises(ValidationError, match="data_mode differs"):
        EvidencePacket.model_validate(payload)

    case_payload = case.model_dump(mode="python")
    case_payload["evidence"]["data_mode"] = "real"
    for evidence_item in case_payload["evidence"]["items"]:
        evidence_item["data_mode"] = "real"
    real_case = _rebuild_case(case_payload)
    with pytest.raises(ValidationError, match="only synthetic evidence"):
        _brief_for_case(real_case)


def test_point_in_time_packet_rejects_late_and_future_observed_evidence() -> None:
    packet = build_demo_brief().cases[0].evidence
    payload = _without_hashes(packet.model_dump(mode="python"))
    payload["items"][0]["known_at"] = packet.knowledge_cutoff + timedelta(seconds=1)
    with pytest.raises(ValidationError, match="known after the packet cutoff"):
        EvidencePacket.model_validate(payload)

    payload = _without_hashes(packet.model_dump(mode="python"))
    payload["items"][0]["observed_at"] = packet.as_of + timedelta(days=1)
    payload["items"][0]["known_at"] = packet.knowledge_cutoff
    with pytest.raises(ValidationError, match="observed_at cannot be later than known_at"):
        EvidencePacket.model_validate(payload)


@pytest.mark.parametrize(
    ("artifact", "field"),
    [
        ("evidence", "knowledge_cutoff"),
        ("thesis", "created_at"),
        ("challenge", "created_at"),
        ("portfolio", "created_at"),
        ("decision", "created_at"),
    ],
)
def test_all_artifact_datetimes_require_utc(artifact: str, field: str) -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    aware = payload[artifact][field]
    payload[artifact][field] = aware.replace(tzinfo=None)

    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        _rebuild_case(payload)


def test_cross_artifact_cutoff_expiry_and_creation_order_are_enforced() -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["thesis"]["knowledge_cutoff"] -= timedelta(hours=1)
    with pytest.raises(ValidationError, match="share the evidence knowledge_cutoff"):
        _rebuild_case(payload)

    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["challenge"]["created_at"] += timedelta(hours=2)
    with pytest.raises(ValidationError, match="decision-chain order"):
        _rebuild_case(payload)

    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["evidence"]["expires_at"] = payload["decision"]["expires_at"] - timedelta(seconds=1)
    with pytest.raises(ValidationError, match="cannot outlive"):
        _rebuild_case(payload)


def test_contracts_reject_float_input_recursively() -> None:
    with pytest.raises(ValidationError, match="float input is forbidden"):
        SizeRange.model_validate({"minimum_pct": 1.5, "maximum_pct": "4"})

    payload = _without_hashes(
        build_demo_brief().cases[0].decision.model_dump(mode="python")
    )
    payload["model_and_prompt_manifest"] = ({"component": "x", "version": 1.5},)
    with pytest.raises(ValidationError, match="float input is forbidden"):
        DecisionPacket.model_validate(payload)


@pytest.mark.parametrize(
    ("state", "verdict"),
    [
        ("initiate", "ADD"),
        ("add", "ADD"),
        ("trim", "TRIM"),
        ("exit_review", "EXIT-CANDIDATE"),
        ("watch", "REVIEW"),
        ("avoid", "REVIEW"),
        ("abstain", "REVIEW"),
    ],
)
def test_renderer_handles_every_packet_state_without_inventing_a_verdict(
    state: RecommendationState, verdict: MemoVerdict
) -> None:
    case = _case_for_state(state)
    html = render_decision_brief(
        _brief_for_case(case), evaluated_at=case.decision.knowledge_cutoff
    )

    assert f'data-recommendation-state="{state}"' in html
    assert f'data-verdict="{verdict}"' in html
    assert ("data-actionable=\"true\"" in html) is (state in ACTION_STATES)


def test_expired_packet_is_non_actionable_and_original_ask_is_suppressed() -> None:
    case = build_demo_brief().cases[0]
    presentation = presentation_for(case.decision, evaluated_at=case.decision.expires_at)
    html = render_decision_brief(
        _brief_for_case(case), evaluated_at=case.decision.expires_at
    )

    assert presentation.expired is True
    assert presentation.actionable is False
    assert "EXPIRED - ADD" in html
    assert 'data-actionable="false"' in html
    assert "refresh required" in html
    assert case.decision.decision_ask not in html


def test_renderer_autoescapes_untrusted_text_and_attributes() -> None:
    payload = build_demo_brief().cases[0].model_dump(mode="python")
    payload["case_id"] = 'x"><img src=x onerror=alert(1)>'
    payload["thesis"]["thesis_summary"] = "<script>alert(2)</script>"
    case = _rebuild_case(payload)
    html = render_decision_brief(
        _brief_for_case(case), evaluated_at=case.decision.knowledge_cutoff
    )

    assert "<script>alert(2)</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in html


async def test_prototype_serves_the_same_typed_synthetic_contract_as_html_and_json() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        page = await client.get("/")
        case = await client.get("/api/cases/paper-ready")
        missing = await client.get("/api/cases/not-there")
        health = await client.get("/health")

    assert page.status_code == 200
    assert case.status_code == 200
    body = case.json()
    assert body["thesis"]["security_id"] == "sec-synthetic-grid-au"
    assert body["evidence"]["data_mode"] == "synthetic"
    assert body["decision"]["model_independence"] is True
    assert body["decision"]["tax_assessment_reference"]["readiness"] == "pass"
    assert body["decision"]["size_range"] == {
        "minimum_pct": "2",
        "maximum_pct": "4",
    }
    assert missing.status_code == 404
    assert health.json() == {"status": "ok", "mode": "synthetic_prototype"}


def test_architecture_stage_contract_remains_unknown_field_rejecting() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ArchitectureStage.model_validate(
            {"name": "Evidence", "status": "future", "detail": "x", "surprise": True}
        )
