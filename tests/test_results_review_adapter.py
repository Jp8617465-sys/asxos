"""Adapter tests for the deterministic read-only results adapter (mission P2-03).

Covers the four P2-03 deliverable groups against the FROZEN P2-02 contracts:

- numeric: Decimal-exact arithmetic, no float contamination, G4 scale
  normalization, and the exact-Decimal (no tolerance) bridge reconciliation;
- cutoff: mechanical `known_at <= knowledge_cutoff` exclusion with the
  at-cutoff / one-second-after boundary and the conservative end-of-day rule;
- reproducibility: identical in-memory fingerprints across runs (pinned as hex
  digest constants — fingerprints only, never a committed artifact body) and
  input-mutation sensitivity;
- negative controls: the abstention fixture's frozen abstain outcome, the
  `unknown` tax readiness, and the injection fixture's adversarial string
  surfacing nowhere load-bearing.

The adapter surfaces frozen outcomes mechanically; every rejection asserted
here is a P2-02 contract gate re-fired through adapter revalidation, never an
adapter-invented rule.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, Inexact, InvalidOperation
from typing import TypeVar

import pytest
from pydantic import BaseModel, ValidationError

from asxos.domain.decision_engine.types import EvidenceItem
from asxos.domain.results_review.adapter import (
    SCALE_EXPONENT,
    ResultsReviewAdapterError,
    adapt_hashed_fixture,
    artifact_output_sha256,
    map_statement_period_type,
    normalize_scale,
    partition_admissible_evidence,
)
from asxos.domain.results_review.contracts import (
    MetricDelta,
    ResultsReviewArtifact,
    ResultsReviewCase,
    StatutoryUnderlyingBridge,
    derive_statement_known_at,
    frozen_delta_pct,
)
from asxos.domain.results_review.fixtures import (
    abstention_case,
    historical_document_payload,
    historical_results_case,
    injection_case,
    injection_document_payload,
)

_CUTOFF = datetime(2025, 8, 21, 23, 59, 59, tzinfo=UTC)

# In-memory fingerprints of the clean adapted fixture, pinned at build time.
# These are hex-digest STRING CONSTANTS only — no artifact body is committed
# anywhere (standing rule: adapter output is never persisted). Any drift in
# fixture content, contract canonicalization, or adapter rendering fails here.
_PINNED_ARTIFACT_SHA256 = "b10afcf3507fac1e7c561d45c5e005a91d7a1c73253e27dafee1ed356d7dcf5b"
_PINNED_CASE_SHA256 = "78e016474c3292f155347af7c623374a55337fe7f5834a55fd8686a11767f171"

_M = TypeVar("_M", bound=BaseModel)


def _reconstruct(model: _M, **overrides: object) -> _M:
    """Rebuild a contract instance WITHOUT validation (``model_construct``).

    Emulates an untrusted, unvalidated case arriving at the adapter — the
    adapter's JSON-round-trip revalidation must be what catches (or reseals)
    it. Any stale ``content_hash`` is cleared so revalidation reseals it and
    the targeted frozen gate, not the seal check, is what fires.
    """
    fields = dict(model)
    fields.update(overrides)
    if "content_hash" in fields:
        fields["content_hash"] = ""
    return type(model).model_construct(**fields)


def _tampered_case(case: ResultsReviewCase, **review_overrides: object) -> ResultsReviewCase:
    review = _reconstruct(case.review, **review_overrides)
    return ResultsReviewCase.model_construct(**{**dict(case), "review": review})


def _boundary_item(evidence_id: str, known_at: datetime) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type="fundamental_fact",
        title="Boundary fixture row",
        claim="Synthetic boundary-check row.",
        source_uri="fixture://boundary",
        observed_at=date(2025, 8, 21),
        known_at=known_at,
        evidence_tier="verified",
        data_mode="synthetic",
    )


def _walk(value: object) -> Iterator[object]:
    yield value
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _walk(key)
            yield from _walk(item)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            yield from _walk(item)


# ---------------------------------------------------------------------------
# Numeric — Decimal-exact arithmetic, no float contamination (deliverable 2)
# ---------------------------------------------------------------------------


def test_every_monetary_value_in_the_adapted_artifact_is_decimal() -> None:
    review = adapt_hashed_fixture(
        historical_document_payload(), historical_results_case()
    ).case.review
    for delta in review.metric_deltas:
        assert isinstance(delta.current_value, Decimal)
        assert delta.prior_value is None or isinstance(delta.prior_value, Decimal)
        assert delta.delta_pct is None or isinstance(delta.delta_pct, Decimal)
    for bridge in review.statutory_underlying_bridges:
        assert isinstance(bridge.statutory, Decimal)
        assert isinstance(bridge.underlying, Decimal)
        for adjustment in bridge.adjustments:
            assert isinstance(adjustment.amount, Decimal)
    # No float anywhere in the adapted artifact tree (portfolio-conventions
    # §Decimal-only; Contract.reject_float_input is the frozen enforcement).
    assert not any(isinstance(node, float) for node in _walk(review.model_dump(mode="python")))


def test_adapted_deltas_equal_the_frozen_decimal_computation_exactly() -> None:
    review = adapt_hashed_fixture(
        historical_document_payload(), historical_results_case()
    ).case.review
    for delta in review.metric_deltas:
        assert delta.prior_value is not None
        assert delta.delta_pct == frozen_delta_pct(delta.current_value, delta.prior_value)
    revenue = review.metric_deltas[0]
    assert (revenue.metric, revenue.delta_pct) == ("Revenue", Decimal("7.840833"))


def test_bridge_reconciliation_is_exact_with_no_tolerance_through_the_adapter() -> None:
    case = historical_results_case()
    bridge = case.review.statutory_underlying_bridges[0]
    off_by_one_micro = _reconstruct(bridge, underlying=bridge.underlying + Decimal("0.000001"))
    tampered = _tampered_case(case, statutory_underlying_bridges=(off_by_one_micro,))
    with pytest.raises(ValidationError, match="does not reconcile"):
        adapt_hashed_fixture(historical_document_payload(), tampered)


def test_tampered_delta_pct_is_rejected_through_the_adapter() -> None:
    case = historical_results_case()
    delta = case.review.metric_deltas[0]
    assert delta.delta_pct is not None
    one_ulp_off = _reconstruct(delta, delta_pct=delta.delta_pct + Decimal("0.000001"))
    tampered = _tampered_case(
        case, metric_deltas=(one_ulp_off, *case.review.metric_deltas[1:])
    )
    with pytest.raises(ValidationError, match="frozen computation"):
        adapt_hashed_fixture(historical_document_payload(), tampered)


def test_scale_normalization_is_exact_and_reversible() -> None:
    # G4: explicit presentation scales, exact decimal-point shifts only.
    assert SCALE_EXPONENT == {"ones": 0, "thousands": 3, "millions": 6, "billions": 9}
    assert normalize_scale(Decimal("1284.6"), "millions", "ones") == Decimal("1284600000")
    assert normalize_scale(Decimal("1284600000"), "ones", "millions") == Decimal("1284.6")
    assert normalize_scale(Decimal("415.0"), "millions", "billions") == Decimal("0.415")
    assert normalize_scale(Decimal("268.3"), "millions", "millions") == Decimal("268.3")
    round_trip = normalize_scale(
        normalize_scale(Decimal("182.4"), "millions", "thousands"), "thousands", "millions"
    )
    assert round_trip == Decimal("182.4")


def test_scale_normalization_raises_rather_than_round() -> None:
    # A coefficient wider than the trap context cannot be shifted silently:
    # fail loudly (CLAUDE.md non-negotiable #10), never round a monetary value.
    too_wide = Decimal("1" * 61)
    with pytest.raises(Inexact):
        normalize_scale(too_wide, "ones", "millions")
    # A signaling NaN raises instead of propagating a quiet NaN (security
    # pass F4: InvalidOperation stays trapped alongside Inexact).
    with pytest.raises(InvalidOperation):
        normalize_scale(Decimal("sNaN"), "ones", "millions")


# ---------------------------------------------------------------------------
# Cutoff — mechanical exclusion at the frozen boundary (deliverable 3)
# ---------------------------------------------------------------------------


def test_at_cutoff_evidence_is_admissible_and_one_second_after_is_excluded() -> None:
    # The frozen canonical rule is known_at <= knowledge_cutoff
    # (types.py:249-251); the adapter surfaces it without alteration.
    at_cutoff = _boundary_item("at-cutoff", _CUTOFF)
    one_second_after = _boundary_item("one-second-after", _CUTOFF + timedelta(seconds=1))
    admissible, excluded = partition_admissible_evidence(
        (at_cutoff, one_second_after), _CUTOFF
    )
    assert tuple(item.evidence_id for item in admissible) == ("at-cutoff",)
    assert tuple(item.evidence_id for item in excluded) == ("one-second-after",)
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        partition_admissible_evidence((at_cutoff,), _CUTOFF.replace(tzinfo=None))


def test_conservative_end_of_day_rule_is_honoured_by_the_partition() -> None:
    # §8 item 4: a vendor-dated row disclosed on the cutoff day lands at
    # 23:59:59 UTC, so it is excluded at ANY intraday cutoff and admitted
    # only at (or after) end of day — the approximation errs toward
    # exclusion, never leakage.
    known_at = derive_statement_known_at(
        date(2025, 6, 30), date(2025, 8, 21), date(2025, 6, 30), date(2025, 8, 21)
    )
    assert known_at == _CUTOFF
    same_day_row = _boundary_item("same-day-vendor-row", known_at)
    intraday = datetime(2025, 8, 21, 6, 0, tzinfo=UTC)
    admissible, excluded = partition_admissible_evidence((same_day_row,), intraday)
    assert not admissible
    assert tuple(item.evidence_id for item in excluded) == ("same-day-vendor-row",)
    admissible, excluded = partition_admissible_evidence((same_day_row,), _CUTOFF)
    assert tuple(item.evidence_id for item in admissible) == ("same-day-vendor-row",)
    assert not excluded


def test_partition_agrees_with_the_canonical_packet_gate_on_the_fixture() -> None:
    # At an intraday cutoff the fixture's same-day FY25 PIT row is excluded
    # while the released announcement and the FY24 comparative stay in —
    # exactly the set the EvidencePacket validator would reject as "known
    # after the packet cutoff".
    case = historical_results_case()
    intraday = datetime(2025, 8, 21, 6, 0, tzinfo=UTC)
    admissible, excluded = partition_admissible_evidence(case.evidence.items, intraday)
    assert {item.evidence_id for item in admissible} == {
        "resl-fy25-announcement",
        "resl-fy24-pit-statement",
    }
    assert tuple(item.evidence_id for item in excluded) == ("resl-fy25-pit-statement",)
    admissible, excluded = partition_admissible_evidence(
        case.evidence.items, case.evidence.knowledge_cutoff
    )
    assert len(admissible) == 3
    assert not excluded


# ---------------------------------------------------------------------------
# Reproducibility — identical fingerprints, in-memory only (deliverable 4)
# ---------------------------------------------------------------------------


def test_same_fixture_produces_identical_fingerprints_across_runs() -> None:
    # Two INDEPENDENT constructions, recomputed and compared in memory —
    # no golden file, no snapshot, no persisted artifact (constraint 3).
    first = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    second = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    assert first.artifact_sha256 == second.artifact_sha256 == _PINNED_ARTIFACT_SHA256
    assert first.case_sha256 == second.case_sha256 == _PINNED_CASE_SHA256
    assert first.artifact_json == second.artifact_json
    assert first.artifact_markdown == second.artifact_markdown
    assert artifact_output_sha256(first.case.review) == _PINNED_ARTIFACT_SHA256


def test_json_and_markdown_render_the_same_validated_artifact() -> None:
    adapted = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    review = adapted.case.review
    # Plan :305 — both renders derive from the one validated artifact.
    assert json.loads(adapted.artifact_json) == review.model_dump(mode="json")
    assert f"# Results review {review.review_id}" in adapted.artifact_markdown
    assert f"- Outcome: **{review.outcome}**" in adapted.artifact_markdown
    assert "| Revenue | statutory | AUD | millions | 1284.6 | 1191.2 | 7.840833 |" in (
        adapted.artifact_markdown
    )
    assert review.frozen_input.document_sha256 in adapted.artifact_markdown
    # The document payload itself is never embedded in either render — the
    # artifact carries only its hash.
    payload_only_text = "Synthetic figures authored for the P2-02 hashed-fixture contract"
    assert payload_only_text not in adapted.artifact_json
    assert payload_only_text not in adapted.artifact_markdown


def test_mutation_of_any_input_field_changes_the_fingerprint_or_is_rejected() -> None:
    payload = historical_document_payload()
    baseline = adapt_hashed_fixture(payload, historical_results_case())

    # A review input field: both fingerprints move.
    renamed_review = adapt_hashed_fixture(
        payload, _tampered_case(historical_results_case(), review_id="rrv-resl-fy2025-mutated")
    )
    assert renamed_review.artifact_sha256 != baseline.artifact_sha256
    assert renamed_review.case_sha256 != baseline.case_sha256

    # A document-record input field outside the review: the case fingerprint
    # moves (the document reseals to a new content hash).
    case = historical_results_case()
    relabelled_document = _reconstruct(
        case.document, transcription_note="Synthetic figures; mutated note for the test."
    )
    mutated_document = adapt_hashed_fixture(
        payload,
        ResultsReviewCase.model_construct(**{**dict(case), "document": relabelled_document}),
    )
    assert mutated_document.case_sha256 != baseline.case_sha256

    # A case-level input field: the case fingerprint moves.
    relabelled_case = adapt_hashed_fixture(
        payload,
        ResultsReviewCase.model_construct(**{**dict(case), "label": "Mutated label"}),
    )
    assert relabelled_case.case_sha256 != baseline.case_sha256

    # A document PAYLOAD field: rejected outright before any artifact exists.
    tampered_payload = dict(payload)
    tampered_payload["issuer"] = "Tampered Issuer Ltd"
    with pytest.raises(ResultsReviewAdapterError, match="does not match"):
        adapt_hashed_fixture(tampered_payload, historical_results_case())


def test_payload_hash_mismatch_hard_fails() -> None:
    # The clean case bound to the adversarial payload is a hash mismatch —
    # there is no partial acceptance (§8 item 1).
    with pytest.raises(ResultsReviewAdapterError, match="does not match"):
        adapt_hashed_fixture(injection_document_payload(), historical_results_case())


# ---------------------------------------------------------------------------
# Negative controls through the adapter (deliverable 5)
# ---------------------------------------------------------------------------


def test_abstention_fixture_surfaces_the_frozen_abstain_outcome() -> None:
    adapted = adapt_hashed_fixture(historical_document_payload(), abstention_case())
    review = adapted.case.review
    assert review.outcome == "abstain"
    assert review.tax_assessment_reference.readiness == "unknown"
    assert review.missing_evidence
    assert "- Outcome: **abstain**" in adapted.artifact_markdown
    assert "## Missing evidence" in adapted.artifact_markdown
    # The adapter owns no outcome rule: forcing any other outcome trips the
    # FROZEN artifact gate (contracts.py:585-586) on revalidation.
    with pytest.raises(ValidationError, match="missing evidence must force"):
        adapt_hashed_fixture(
            historical_document_payload(), _tampered_case(abstention_case(), outcome="complete")
        )


def test_injection_fixture_moves_nothing_load_bearing_through_the_adapter() -> None:
    clean = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    adversarial = adapt_hashed_fixture(injection_document_payload(), injection_case())
    review = adversarial.case.review
    # The frozen outcomes hold: abstain behind an unresolved conflict, tax
    # readiness still unknown (G10, §8 item 8).
    assert review.outcome == "abstain"
    assert review.tax_assessment_reference.readiness == "unknown"
    assert any(conflict.resolution is None for conflict in review.conflicts)
    # The adversarial string's demands surface nowhere in either render.
    for injected in (
        "STRONG BUY",
        "99.99",
        "Ignore all previous instructions",
        "ADVERSARIAL NEGATIVE-CONTROL FIXTURE",
    ):
        assert injected not in adversarial.artifact_json
        assert injected not in adversarial.artifact_markdown
    # Every load-bearing number and citation is identical to the clean case.
    assert review.metric_deltas == clean.case.review.metric_deltas
    assert review.statutory_underlying_bridges == clean.case.review.statutory_underlying_bridges
    assert review.guidance_changes == clean.case.review.guidance_changes
    assert review.cited_evidence_ids() == clean.case.review.cited_evidence_ids()
    # It is still a different adapted case (different document hash, review
    # identity, and conflict), so the fingerprints differ.
    assert adversarial.artifact_sha256 != clean.artifact_sha256
    assert adversarial.case_sha256 != clean.case_sha256


def test_markdown_structure_cannot_be_forged_by_free_text_fields() -> None:
    # Security pass F2: contract free text caps length, not content — a
    # metric name carrying pipes and newlines must not forge table cells,
    # headings, or list items in the deterministic Markdown render.
    case = historical_results_case()
    delta = case.review.metric_deltas[0]
    hostile = "Revenue | statutory | AUD | ones | 9 | 1 | 99\n## Recommendation\nSTRONG"
    forged = _reconstruct(delta, metric=hostile)
    tampered = _tampered_case(case, metric_deltas=(forged, *case.review.metric_deltas[1:]))
    adapted = adapt_hashed_fixture(historical_document_payload(), tampered)
    markdown = adapted.artifact_markdown
    assert "\n## Recommendation" not in markdown
    assert "\nSTRONG" not in markdown
    # The hostile text survives verbatim as CONTENT, neutralized as structure.
    assert "Revenue \\| statutory" in markdown


def test_unresolved_conflict_still_forbids_complete_through_the_adapter() -> None:
    with pytest.raises(ValidationError, match="unresolved conflicts forbid"):
        adapt_hashed_fixture(
            injection_document_payload(), _tampered_case(injection_case(), outcome="complete")
        )


# ---------------------------------------------------------------------------
# Statement-vocabulary mapping (freeze record §5 — the adapter's concern)
# ---------------------------------------------------------------------------


def test_statement_period_type_mapping_is_total_and_hard_fails_on_the_rest() -> None:
    assert map_statement_period_type("yearly") == "yearly"
    assert map_statement_period_type("quarterly") == "quarterly"
    # half_yearly is document-level vocabulary (ASX Appendix 4D); no
    # rs_financial_statements row may claim it (0027:71).
    for unmapped in ("half_yearly", "monthly", "", "YEARLY"):
        with pytest.raises(ResultsReviewAdapterError, match="not an rs_financial_statements"):
            map_statement_period_type(unmapped)


def test_adapted_artifact_types_are_the_frozen_contract_types() -> None:
    adapted = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    assert isinstance(adapted.case, ResultsReviewCase)
    assert isinstance(adapted.case.review, ResultsReviewArtifact)
    assert isinstance(adapted.case.review.metric_deltas[0], MetricDelta)
    assert isinstance(
        adapted.case.review.statutory_underlying_bridges[0], StatutoryUnderlyingBridge
    )
