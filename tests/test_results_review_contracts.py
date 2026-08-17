"""Contract tests for the frozen results-review contracts (mission P2-02).

Pins the eight §8 freeze items of
`docs/product/finance-capability-matrix-2026-08-13.md`: schema shape, hash
stability, the fixture-never-real invariant, the `known_at` derivation, the
statutory/underlying bridge, the tax-readiness default, and the
abstention/injection negative controls.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.results_review.contracts import (
    ADMISSIBLE_SOURCE_CLASSES,
    DEFAULT_TAX_READINESS,
    DOCUMENT_HASH_ALGORITHM,
    LOAD_BEARING_SOURCE_CLASSES,
    SECURITY_ID_BINDING,
    SOURCE_RANK,
    TAX_ASSESSMENT_PRODUCERS,
    TRADING_CALENDAR_SOURCE,
    FrozenInputTuple,
    MetricAdjustment,
    MetricDelta,
    ResultsReviewArtifact,
    ResultsReviewCase,
    SourceDocumentRecord,
    StatutoryUnderlyingBridge,
    derive_statement_known_at,
    frozen_delta_pct,
    hash_document_payload,
    unresolved_tax_assessment_reference,
)
from asxos.domain.results_review.fixtures import (
    abstention_case,
    historical_document_payload,
    historical_results_case,
    injection_case,
    injection_document_payload,
)

_AS_OF = date(2025, 8, 21)
_CUTOFF = datetime(2025, 8, 21, 23, 59, 59, tzinfo=UTC)

# Pinned once at freeze time; any drift in payload or canonicalization fails.
_PINNED_CLEAN_SHA256 = "cc8914940979501ef288d6a60158ffa41567413dbdd627ce6f4567ed3a8ec8e6"


def _without_hashes(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_hashes(item) for key, item in value.items() if key != "content_hash"
        }
    if isinstance(value, list | tuple):
        return type(value)(_without_hashes(item) for item in value)
    return value


def _mutated_artifact(review: ResultsReviewArtifact, **overrides: Any) -> ResultsReviewArtifact:
    payload = _without_hashes(review.model_dump(mode="json"))
    payload.update(overrides)
    return ResultsReviewArtifact.model_validate(payload)


# ---------------------------------------------------------------------------
# Frozen constants (§8 items 1, 2, 6, 7 + §7 A3)
# ---------------------------------------------------------------------------


def test_frozen_ruling_constants() -> None:
    assert DOCUMENT_HASH_ALGORITHM == "sha256"
    assert SECURITY_ID_BINDING == "rs_security_master.symbol"
    assert TRADING_CALENDAR_SOURCE == "asxos_prices_observed_sessions"
    assert DEFAULT_TAX_READINESS == "unknown"
    assert TAX_ASSESSMENT_PRODUCERS == (
        "asxos.domain.tax.positions.tax_view_individual",
        "asxos.domain.tax.positions.tax_view_smsf",
    )


def test_source_hierarchy_is_ranked_and_news_is_never_load_bearing() -> None:
    assert SOURCE_RANK["asx_announcement"] == 1
    assert SOURCE_RANK["audited_statements"] == 1
    assert SOURCE_RANK["issuer_presentation"] == 2
    assert SOURCE_RANK["results_transcript"] == 3
    assert SOURCE_RANK["asxos_pit_record"] == 4
    assert SOURCE_RANK["licensed_consensus"] == 5
    assert SOURCE_RANK["news"] == 6
    assert "licensed_consensus" not in ADMISSIBLE_SOURCE_CLASSES
    assert "news" in ADMISSIBLE_SOURCE_CLASSES
    assert "news" not in LOAD_BEARING_SOURCE_CLASSES
    assert LOAD_BEARING_SOURCE_CLASSES < ADMISSIBLE_SOURCE_CLASSES


# ---------------------------------------------------------------------------
# §8 item 1 — hashed fixture: hash stability and the never-real invariant
# ---------------------------------------------------------------------------


def test_document_hash_is_stable_and_pins_content() -> None:
    payload = historical_document_payload()
    assert hash_document_payload(payload) == _PINNED_CLEAN_SHA256
    assert hash_document_payload(payload) == hash_document_payload(payload)
    assert hash_document_payload(injection_document_payload()) != _PINNED_CLEAN_SHA256


def test_document_hash_rejects_floats_and_non_json_figures() -> None:
    with pytest.raises(ValueError, match="float is forbidden"):
        hash_document_payload({"figure": 1284.6})
    with pytest.raises(ValueError, match="JSON-native"):
        hash_document_payload({"figure": Decimal("1284.6")})


def test_a_fixture_can_never_carry_data_mode_real() -> None:
    document = historical_results_case().document
    payload = _without_hashes(document.model_dump(mode="json"))
    payload["data_mode"] = "real"
    with pytest.raises(ValidationError, match="never carry data_mode='real'"):
        SourceDocumentRecord.model_validate(payload)


def test_document_kind_must_match_period_type() -> None:
    document = historical_results_case().document
    payload = _without_hashes(document.model_dump(mode="json"))
    payload["period_type"] = "quarterly"
    with pytest.raises(ValidationError, match="does not match"):
        SourceDocumentRecord.model_validate(payload)


# ---------------------------------------------------------------------------
# §8 item 3 — the frozen input tuple: exactly eight elements, content-hashed
# ---------------------------------------------------------------------------


def test_frozen_input_tuple_carries_exactly_the_eight_elements() -> None:
    expected = {
        "document_id",
        "document_sha256",
        "security_id",
        "period_end",
        "period_type",
        "currency",
        "units_scale",
        "knowledge_cutoff",
        "evidence_packet_id",
        "content_hash",  # the seal, not a ninth element
    }
    assert set(FrozenInputTuple.model_fields) == expected


def test_frozen_input_tuple_hash_is_stable_and_verifiable() -> None:
    first = historical_results_case().review.frozen_input
    second = historical_results_case().review.frozen_input
    assert first.content_hash == second.content_hash
    assert verify_content_hash(first)


# ---------------------------------------------------------------------------
# §8 item 4 — the known_at derivation rule (G8)
# ---------------------------------------------------------------------------


def test_known_at_drops_disclosure_dates_that_defaulted_to_period_end() -> None:
    known_at = derive_statement_known_at(
        date(2025, 6, 30), date(2025, 8, 21), date(2025, 6, 30), date(2025, 8, 21)
    )
    assert known_at == datetime(2025, 8, 21, 23, 59, 59, tzinfo=UTC)


def test_known_at_drops_scheduled_future_dates_and_falls_back_to_lag() -> None:
    # report_date is a scheduled FUTURE date relative to as_of and filing_date
    # defaulted to period_end: both are dropped, so the 75-day conservative
    # lag applies (asxos/ingestion/financial_statements.py:53).
    known_at = derive_statement_known_at(
        date(2025, 6, 30), date(2025, 9, 30), date(2025, 6, 30), date(2025, 8, 1)
    )
    assert known_at == datetime(2025, 9, 13, 23, 59, 59, tzinfo=UTC)
    assert known_at.date() == date(2025, 6, 30) + timedelta(days=75)


def test_known_at_end_of_day_is_conservative_against_intraday_cutoffs() -> None:
    # A vendor-dated row whose knowledge date IS the cutoff day is not
    # admissible at an intraday cutoff — the packet must reject it as known
    # after the cutoff. Only an end-of-day cutoff admits it.
    case = historical_results_case()
    packet_payload = _without_hashes(case.evidence.model_dump(mode="json"))
    intraday = datetime(2025, 8, 21, 6, 0, tzinfo=UTC)
    packet_payload["knowledge_cutoff"] = intraday.isoformat()
    packet_payload["created_at"] = intraday.isoformat()
    from asxos.domain.decision_engine.types import EvidencePacket

    with pytest.raises(ValidationError, match="known after the packet cutoff"):
        EvidencePacket.model_validate(packet_payload)


# ---------------------------------------------------------------------------
# §8 item 5 — statutory/underlying separation in the schema (G3)
# ---------------------------------------------------------------------------


def test_bridge_must_reconcile_exactly() -> None:
    bridge = historical_results_case().review.statutory_underlying_bridges[0]
    payload = bridge.model_dump(mode="json")
    payload["underlying"] = "201.8"  # off by 0.1
    with pytest.raises(ValidationError, match="does not reconcile"):
        StatutoryUnderlyingBridge.model_validate(payload)


def test_every_adjustment_requires_explanation_and_citation() -> None:
    base = {
        "label": "Restructuring costs",
        "amount": "12.8",
        "explanation": "One-off program.",
        "evidence_ids": ["resl-fy25-announcement"],
        "source_class": "asx_announcement",
    }
    with pytest.raises(ValidationError):
        MetricAdjustment.model_validate({**base, "explanation": ""})
    with pytest.raises(ValidationError):
        MetricAdjustment.model_validate({**base, "evidence_ids": []})


@pytest.mark.parametrize("source_class", ["news", "licensed_consensus"])
def test_non_load_bearing_sources_cannot_carry_an_adjustment(source_class: str) -> None:
    with pytest.raises(ValidationError, match="not load-bearing"):
        MetricAdjustment(
            label="Restructuring costs",
            amount=Decimal("12.8"),
            explanation="One-off program.",
            evidence_ids=("resl-fy25-announcement",),
            source_class=source_class,  # type: ignore[arg-type]
        )


def test_delta_pct_must_equal_the_frozen_computation() -> None:
    delta = historical_results_case().review.metric_deltas[0]
    payload = delta.model_dump(mode="json")
    payload["delta_pct"] = "7.840834"  # one ulp off the frozen value
    with pytest.raises(ValidationError, match="frozen computation"):
        MetricDelta.model_validate(payload)
    assert delta.delta_pct == Decimal("7.840833")


def test_delta_pct_is_none_without_a_usable_prior() -> None:
    delta = abstention_case().review.metric_deltas[0]
    assert delta.prior_value is None
    assert delta.delta_pct is None
    payload = delta.model_dump(mode="json")
    payload["delta_pct"] = "1.000000"
    with pytest.raises(ValidationError, match="without a usable non-zero prior"):
        MetricDelta.model_validate(payload)
    with pytest.raises(ValueError, match="undefined for a zero prior"):
        frozen_delta_pct(Decimal("1"), Decimal("0"))


# ---------------------------------------------------------------------------
# §8 item 7 — tax readiness defaults to unknown, and unknown is success
# ---------------------------------------------------------------------------


def test_unresolved_tax_reference_defaults_to_unknown() -> None:
    reference = unresolved_tax_assessment_reference(
        tax_assessment_id="taxref-test",
        as_of=_AS_OF,
        knowledge_cutoff=_CUTOFF,
        created_at=_CUTOFF,
    )
    assert reference.readiness == "unknown"
    assert reference.applicability == "uncertain"
    assert verify_content_hash(reference)


def test_every_fixture_carries_unknown_tax_readiness() -> None:
    for case in (historical_results_case(), abstention_case(), injection_case()):
        assert case.review.tax_assessment_reference.readiness == "unknown"


# ---------------------------------------------------------------------------
# The artifact is analysis, never a recommendation
# ---------------------------------------------------------------------------


def test_artifact_rejects_recommendation_shaped_fields() -> None:
    review = historical_results_case().review
    for forbidden in ("price_target", "rating", "recommendation_state", "size_range"):
        payload = _without_hashes(review.model_dump(mode="json"))
        payload[forbidden] = "anything"
        with pytest.raises(ValidationError):
            ResultsReviewArtifact.model_validate(payload)


def test_outcome_vocabulary_is_the_plan_triple_only() -> None:
    review = historical_results_case().review
    for invalid in ("BUY", "GOOD HOLD", "CLEAR", "pass"):
        payload = _without_hashes(review.model_dump(mode="json"))
        payload["outcome"] = invalid
        with pytest.raises(ValidationError):
            ResultsReviewArtifact.model_validate(payload)


# ---------------------------------------------------------------------------
# §8 item 8 — the negative controls
# ---------------------------------------------------------------------------


def test_missing_evidence_forces_abstention() -> None:
    case = abstention_case()
    assert case.review.missing_evidence
    assert case.review.outcome == "abstain"
    for outcome in ("complete", "revise"):
        with pytest.raises(ValidationError, match="missing evidence must force"):
            _mutated_artifact(case.review, outcome=outcome)


def test_unresolved_conflict_forbids_a_complete_outcome() -> None:
    case = injection_case()
    assert any(conflict.resolution is None for conflict in case.review.conflicts)
    with pytest.raises(ValidationError, match="unresolved conflicts forbid"):
        _mutated_artifact(case.review, outcome="complete")


def test_adversarial_document_moves_no_number_and_no_citation() -> None:
    clean = historical_results_case()
    adversarial = injection_case()
    # The document differs — same claimed identity, different content hash.
    assert adversarial.document.document_id == clean.document.document_id
    assert adversarial.document.document_sha256 != clean.document.document_sha256
    # Nothing load-bearing moved.
    assert adversarial.review.statutory_underlying_bridges == (
        clean.review.statutory_underlying_bridges
    )
    assert adversarial.review.metric_deltas == clean.review.metric_deltas
    assert adversarial.review.guidance_changes == clean.review.guidance_changes
    assert adversarial.review.cited_evidence_ids() == clean.review.cited_evidence_ids()
    # The injected demands appear nowhere in the review artifact.
    rendered = adversarial.review.model_dump_json()
    assert "STRONG BUY" not in rendered
    assert "99.99" not in rendered
    assert adversarial.review.tax_assessment_reference.readiness == "unknown"
    assert adversarial.review.outcome == "abstain"


# ---------------------------------------------------------------------------
# Case integrity chain
# ---------------------------------------------------------------------------


def test_case_rejects_citations_outside_the_frozen_packet() -> None:
    case = historical_results_case()
    payload = _without_hashes(case.model_dump(mode="json"))
    payload["review"]["catalysts"][0]["evidence_ids"] = ["not-in-the-packet"]
    with pytest.raises(ValidationError, match="outside the frozen packet"):
        ResultsReviewCase.model_validate(payload)


def test_case_rejects_a_document_hash_mismatch() -> None:
    case = historical_results_case()
    payload = _without_hashes(case.model_dump(mode="json"))
    payload["review"]["frozen_input"]["document_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="document hash does not match"):
        ResultsReviewCase.model_validate(payload)


def test_case_rejects_a_data_mode_mismatch() -> None:
    case = historical_results_case()
    payload = _without_hashes(case.model_dump(mode="json"))
    payload["review"]["data_mode"] = "real"
    with pytest.raises(ValidationError, match="data_mode must match"):
        ResultsReviewCase.model_validate(payload)


def test_fixtures_are_deterministic() -> None:
    assert (
        historical_results_case().review.content_hash
        == historical_results_case().review.content_hash
    )
    assert historical_results_case().evidence.content_hash == (
        historical_results_case().evidence.content_hash
    )
    for case in (historical_results_case(), abstention_case(), injection_case()):
        assert verify_content_hash(case.review)
        assert verify_content_hash(case.document)
        assert verify_content_hash(case.evidence)
