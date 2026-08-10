"""Contract and surface tests for the read-only target-architecture slice."""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from asxos.domain.decision_engine.demo import build_demo_brief, verify_content_hash
from asxos.domain.decision_engine.renderer import render_decision_brief
from asxos.domain.decision_engine.types import DecisionPacket, EvidencePacket, SizeRange
from asxos.prototype.app import app


def test_demo_builds_two_complete_identity_chains() -> None:
    brief = build_demo_brief()

    assert [case.case_id for case in brief.cases] == ["paper-ready", "blocked-abstain"]
    assert [case.decision.recommendation_state for case in brief.cases] == [
        "initiate",
        "abstain",
    ]
    assert all(verify_content_hash(case.evidence) for case in brief.cases)
    assert all(verify_content_hash(case.decision) for case in brief.cases)
    assert all(
        item.known_at <= case.evidence.knowledge_cutoff
        for case in brief.cases
        for item in case.evidence.items
    )


def test_demo_is_deterministic_and_model_a_never_enters_decision_basis() -> None:
    first = build_demo_brief()
    second = build_demo_brief()

    assert first == second
    for case in first.cases:
        assert case.decision.model_and_prompt_manifest["llm"] == "none"
        assert "model_a_quarantine" in case.decision.constraints_checked
        assert "model_a" not in case.thesis.model_dump_json().lower()


def test_point_in_time_boundary_rejects_late_evidence() -> None:
    packet = build_demo_brief().cases[0].evidence
    payload = packet.model_dump()
    item_payloads = [item.model_dump() for item in packet.items]
    item_payloads[0]["known_at"] = packet.knowledge_cutoff + timedelta(seconds=1)
    payload["items"] = item_payloads

    with pytest.raises(ValidationError, match="known after the packet cutoff"):
        EvidencePacket.model_validate(payload)


def test_contracts_reject_float_input() -> None:
    with pytest.raises(ValidationError, match="float input is forbidden"):
        SizeRange(minimum_pct=1.5, maximum_pct="4")


def test_missing_inputs_cannot_produce_capital_deployment_state() -> None:
    decision = build_demo_brief().cases[0].decision
    payload = decision.model_dump()
    payload["missing_or_uncertain_inputs"] = ("Unresolved source",)

    with pytest.raises(ValidationError, match="cannot produce a capital-deployment state"):
        DecisionPacket.model_validate(payload)


def test_renderer_contains_both_gate_outcomes_and_packet_identity() -> None:
    brief = build_demo_brief()
    html = render_decision_brief(brief)

    assert "GRID.AU" in html
    assert "LOCK.AU" in html
    assert "Synthetic architecture prototype only" in html
    assert brief.cases[0].decision.content_hash in html
    assert "/api/cases/paper-ready" in html


async def test_prototype_serves_same_typed_case_as_html_and_json() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        page = await client.get("/")
        case = await client.get("/api/cases/paper-ready")
        missing = await client.get("/api/cases/not-there")
        health = await client.get("/health")

    assert page.status_code == 200
    assert case.status_code == 200
    assert case.json()["decision"]["recommendation_state"] == "initiate"
    assert case.json()["decision"]["size_range"] == {
        "minimum_pct": "2",
        "maximum_pct": "4",
    }
    assert missing.status_code == 404
    assert health.json() == {"status": "ok", "mode": "synthetic_prototype"}
