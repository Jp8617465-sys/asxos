"""The two live decision chains still validate and hash after any types.py change.

`tests/fixtures/live_decision_chain_2026-09.json` holds the ten payloads persisted
to production (migration 0048) for `dpk-cba-1-2026-09-01` and
`dpk-cba-1-2026-09-04`, read verbatim on 2026-09-16. `ContentAddressedContract`
verifies a supplied `content_hash` against the canonical dump, so a contract
change that reshaped a stored payload — a renamed field, a default that now
serialises, a narrowed Literal — fails here rather than on the next `load()`.
S2 widened `EvidenceItem.evidence_type`; this is the proof it changed nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from asxos.domain.decision_engine.types import (
    ChallengeResult,
    DecisionCase,
    DecisionPacket,
    EvidencePacket,
    PortfolioAssessment,
    ThesisVersion,
    verify_content_hash,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "live_decision_chain_2026-09.json"
MODELS = {
    "evidence_packets": EvidencePacket,
    "thesis_versions": ThesisVersion,
    "challenge_results": ChallengeResult,
    "portfolio_assessments": PortfolioAssessment,
    "decision_packets": DecisionPacket,
}
LIVE_PACKET_HASHES = {
    "dpk-cba-1-2026-09-01": "0a051f6d0e470301b52a78bc1e23db197e7a5335373c6e18d4fb8e467302d67d",
    "dpk-cba-1-2026-09-04": "98134494b8fa8af787ab7a200cc180db5c7eda67d436b342e2ec5b97b1ffec5b",
}


def _rows() -> list[dict[str, object]]:
    return list(json.loads(FIXTURE.read_text(encoding="utf-8"))["rows"])


@pytest.mark.parametrize("row", _rows(), ids=lambda r: str(r["id"]))
def test_every_live_payload_validates_and_hashes_to_its_stored_hash(row: dict[str, object]) -> None:
    model = MODELS[str(row["table"])]
    payload = dict(row["payload"])  # type: ignore[call-overload]
    artifact = model.model_validate(payload)
    assert artifact.content_hash == payload["content_hash"]
    assert verify_content_hash(artifact)


@pytest.mark.parametrize("packet_id", sorted(LIVE_PACKET_HASHES))
def test_both_live_decision_cases_still_assemble(packet_id: str) -> None:
    """`DecisionCase` runs the identity-linkage, hash-chain and citation-closure checks."""
    by_id = {str(r["id"]): dict(r["payload"]) for r in _rows()}  # type: ignore[call-overload]
    suffix = packet_id.removeprefix("dpk-")
    decision = DecisionPacket.model_validate(by_id[packet_id])
    assert decision.content_hash == LIVE_PACKET_HASHES[packet_id]
    case = DecisionCase(
        case_id=suffix,
        label=f"live {packet_id}",
        changed_since_prior="fixture replay",
        evidence=EvidencePacket.model_validate(by_id[f"evp-{suffix}"]),
        thesis=ThesisVersion.model_validate(by_id[f"thv-{suffix}"]),
        challenge=ChallengeResult.model_validate(by_id[f"chr-{suffix}"]),
        portfolio=PortfolioAssessment.model_validate(by_id[f"pra-{suffix}"]),
        decision=decision,
    )
    assert case.decision.recommendation_state == "abstain"
    assert verify_content_hash(case.decision)
