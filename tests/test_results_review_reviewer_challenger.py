"""Eval suite for the deterministic reviewer and independent challenger (P2-04).

Four eval families as tests (plan :302-309 acceptance gates), each exercising
the REAL P2-03 ingestion path (`adapt_hashed_fixture`,
`partition_admissible_evidence`) wherever a valid artifact can travel it:

1. **Citation** — an artifact with an uncited material claim -> ``revise``; a
   fully-cited artifact through the real adapter is eligible for
   ``complete``. [mutation-observed]
2. **Abstention** — the abstention fixture through the adapter -> the
   reviewer emits ``abstain``; tax readiness stays ``unknown``; forcing
   completeness trips the frozen contract gate.
3. **Injection** — through the real adapter path, the adversarial string
   influences neither verdict nor challenge text; the action-language bait
   fixture's vocabulary never surfaces in challenger output.
   [mutation-observed]
4. **Advice boundary** — grep-class proof of the negative: reviewer and
   challenger outputs contain no rating / target / trade / size / action
   vocabulary and no memo-verdict or review-state word on ANY fixture; a
   ``revise`` is addressed to the artifact, never to a position or holding
   (test-pinned wording). [mutation-observed]

Tampered inputs use the P2-03 idiom (`model_construct` reconstruction): the
frozen contracts make most defects unrepresentable in VALIDATED instances, so
judging them requires unvalidated ones — which is exactly the reviewer's job
(it reports defects; it never raises). Where noted, the same defect is also
shown to hard-fail the real adapter path even earlier.
"""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import date, timedelta
from typing import Final

import pytest
from pydantic import BaseModel, ValidationError

from asxos.domain.decision_engine.types import (
    ChallengeFinding,
    ChallengeResult,
    EvidenceItem,
    verify_content_hash,
)
from asxos.domain.results_review.adapter import AdaptedResultsReview, adapt_hashed_fixture
from asxos.domain.results_review.challenger import (
    CHALLENGE_RESULT_ID_PREFIX,
    challenge_adapted,
    challenge_case,
)
from asxos.domain.results_review.contracts import ResultsReviewCase
from asxos.domain.results_review.fixtures import (
    abstention_case,
    action_bait_case,
    action_bait_document_payload,
    historical_document_payload,
    historical_results_case,
    injection_case,
    injection_document_payload,
)
from asxos.domain.results_review.gates import evaluate_case
from asxos.domain.results_review.reviewer import (
    VERDICT_SCOPE_STATEMENT,
    VERDICT_SCOPE_STATEMENT_CHALLENGE_BINDING,
    ReviewerVerdict,
    challenged_review,
    review_adapted,
    review_case,
)


def _reconstruct[M: BaseModel](model: M, **overrides: object) -> M:
    """Rebuild a contract instance WITHOUT validation (P2-03 test idiom)."""
    fields = dict(model)
    fields.update(overrides)
    if "content_hash" in fields:
        fields["content_hash"] = ""
    return type(model).model_construct(**fields)


def _tampered_case(case: ResultsReviewCase, **review_overrides: object) -> ResultsReviewCase:
    review = _reconstruct(case.review, **review_overrides)
    return ResultsReviewCase.model_construct(**{**dict(case), "review": review})


def _adapted_fixtures() -> tuple[tuple[str, AdaptedResultsReview], ...]:
    return (
        (
            "historical",
            adapt_hashed_fixture(historical_document_payload(), historical_results_case()),
        ),
        ("abstention", adapt_hashed_fixture(historical_document_payload(), abstention_case())),
        ("injection", adapt_hashed_fixture(injection_document_payload(), injection_case())),
        (
            "action-bait",
            adapt_hashed_fixture(action_bait_document_payload(), action_bait_case()),
        ),
    )


def _verdict_text(verdict: ReviewerVerdict) -> str:
    return json.dumps(dataclasses.asdict(verdict), default=str, sort_keys=True)


def _challenge_text(challenge: ChallengeResult) -> str:
    return challenge.model_dump_json()


def _failed_gates(verdict: ReviewerVerdict) -> set[str]:
    return {check.gate for check in verdict.checks if not check.passed}


# ---------------------------------------------------------------------------
# Eval family 1 — citation [mutation-observed]
# ---------------------------------------------------------------------------


def test_fully_cited_artifact_through_the_real_adapter_is_eligible_for_complete() -> None:
    adapted = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    challenged = challenged_review(adapted)
    assert challenged.verdict.verdict == "complete"
    assert challenged.verdict.derived_verdict == "complete"
    assert challenged.challenge.outcome == "pass"
    assert not any(f.severity == "blocking" for f in challenged.challenge.findings)
    citation = next(c for c in challenged.verdict.checks if c.gate == "citation_closure")
    assert citation.passed


def test_uncited_material_claim_forces_revise() -> None:
    case = historical_results_case()
    uncited = _reconstruct(case.review.metric_deltas[0], evidence_ids=())
    tampered = _tampered_case(
        case, metric_deltas=(uncited, *case.review.metric_deltas[1:])
    )
    verdict = review_case(tampered)
    assert verdict.verdict == "revise"
    assert "citation_closure" in _failed_gates(verdict)
    challenge = challenge_case(tampered)
    assert challenge.outcome == "revise"
    assert any(
        f.severity == "blocking" and "citation_closure" in f.finding
        for f in challenge.findings
    )
    # The real adapter path rejects the same defect even earlier — the frozen
    # contract makes an uncited claim unrepresentable in a validated case.
    with pytest.raises(ValidationError):
        adapt_hashed_fixture(historical_document_payload(), tampered)


def test_citation_outside_the_frozen_packet_forces_revise() -> None:
    case = historical_results_case()
    outside = _reconstruct(
        case.review.metric_deltas[0], evidence_ids=("not-in-the-frozen-packet",)
    )
    tampered = _tampered_case(
        case, metric_deltas=(outside, *case.review.metric_deltas[1:])
    )
    verdict = review_case(tampered)
    assert verdict.verdict == "revise"
    assert "citation_closure" in _failed_gates(verdict)
    assert challenge_case(tampered).outcome == "revise"


# ---------------------------------------------------------------------------
# Eval family 2 — abstention on incomplete evidence (plan :308)
# ---------------------------------------------------------------------------


def test_abstention_fixture_through_the_real_adapter_reviewer_abstains() -> None:
    adapted = adapt_hashed_fixture(historical_document_payload(), abstention_case())
    verdict = review_adapted(adapted)
    assert verdict.verdict == "abstain"
    assert verdict.derived_verdict == "abstain"
    assert not _failed_gates(verdict)  # abstention is a success, not a defect
    assert any("missing evidence" in statement for statement in verdict.insufficiencies)
    # Readiness stays unknown, and the earned-readiness gate passes on it.
    assert adapted.case.review.tax_assessment_reference.readiness == "unknown"
    readiness = next(c for c in verdict.checks if c.gate == "tax_readiness_earned")
    assert readiness.passed
    # The full challenged sequence agrees, with a blocking missing-data finding.
    challenged = challenged_review(adapted)
    assert challenged.verdict.verdict == "abstain"
    assert challenged.challenge.outcome == "abstain"
    assert any(
        f.severity == "blocking" and "lacks 2 named evidence input(s)" in f.finding
        for f in challenged.challenge.findings
    )


def test_forcing_completeness_on_the_abstention_fixture_trips_the_frozen_gate() -> None:
    forced = _tampered_case(abstention_case(), outcome="complete")
    # Through the real adapter: the frozen P2-02 contract gate fires.
    with pytest.raises(ValidationError, match="missing evidence must force"):
        adapt_hashed_fixture(historical_document_payload(), forced)
    # Handed straight to the reviewer: the same rule fires as a reported
    # defect (R3 — defects dominate), with the insufficiency still recorded.
    verdict = review_case(forced)
    assert verdict.verdict == "revise"
    assert "outcome_gate_consistency" in _failed_gates(verdict)
    assert any("missing evidence" in statement for statement in verdict.insufficiencies)


def test_unearned_tax_readiness_pass_is_a_defect() -> None:
    case = historical_results_case()
    unearned = _reconstruct(case.review.tax_assessment_reference, readiness="pass")
    tampered = _tampered_case(case, tax_assessment_reference=unearned)
    verdict = review_case(tampered)
    assert verdict.verdict == "revise"
    assert "tax_readiness_earned" in _failed_gates(verdict)
    challenge = challenge_case(tampered)
    assert challenge.outcome == "revise"
    assert any("tax_readiness_earned" in f.finding for f in challenge.findings)


def test_post_cutoff_evidence_fails_the_cutoff_gate_via_the_real_partition() -> None:
    base = historical_results_case()
    late = EvidenceItem(
        evidence_id="one-second-after-cutoff",
        evidence_type="fundamental_fact",
        title="Post-cutoff fixture row",
        claim="Synthetic row known one second after the packet cutoff.",
        source_uri="fixture://boundary",
        observed_at=date(2025, 8, 21),
        known_at=base.evidence.knowledge_cutoff + timedelta(seconds=1),
        evidence_tier="verified",
        data_mode="synthetic",
    )
    # A validated packet cannot carry a late item (types.py:249-251), so the
    # judged case is built unvalidated — the reviewer must still catch it.
    leaky_packet = _reconstruct(base.evidence, items=(*base.evidence.items, late))
    leaky = ResultsReviewCase.model_construct(**{**dict(base), "evidence": leaky_packet})
    verdict = review_case(leaky)
    assert verdict.verdict == "revise"
    assert "cutoff_admissibility" in _failed_gates(verdict)
    cutoff_check = next(c for c in verdict.checks if c.gate == "cutoff_admissibility")
    assert cutoff_check.evidence_ids == ("one-second-after-cutoff",)


# ---------------------------------------------------------------------------
# Eval family 3 — injection resistance (G10) [mutation-observed]
# ---------------------------------------------------------------------------


def test_injection_fixture_through_the_real_adapter_influences_nothing() -> None:
    adapted = adapt_hashed_fixture(injection_document_payload(), injection_case())
    challenged = challenged_review(adapted)
    # The verdict is dictated by the artifact's frozen evidence state (an
    # unresolved conflict), not by the adversarial demands.
    assert challenged.verdict.verdict == "abstain"
    assert challenged.challenge.outcome == "abstain"
    output = _challenge_text(challenged.challenge) + _verdict_text(challenged.verdict)
    for demanded in (
        "STRONG BUY",
        "99.99",
        "Ignore all previous instructions",
        "ADVERSARIAL",
        "complete'",
    ):
        assert demanded not in output


def test_challenge_prose_is_template_only_across_adversarial_fixtures() -> None:
    # The injection and action-bait artifacts differ in their free text
    # (conflict descriptions, claims) but share identical evidence-state
    # counts — so template-only challenge prose must come out IDENTICAL.
    # Any interpolation of artifact free text breaks this immediately.
    injection = challenge_adapted(
        adapt_hashed_fixture(injection_document_payload(), injection_case())
    )
    bait = challenge_adapted(
        adapt_hashed_fixture(action_bait_document_payload(), action_bait_case())
    )
    assert injection.strongest_bear_case == bait.strongest_bear_case
    assert [f.finding for f in injection.findings] == [f.finding for f in bait.findings]
    assert [f.required_response for f in injection.findings] == [
        f.required_response for f in bait.findings
    ]


def test_action_bait_vocabulary_never_reaches_reviewer_or_challenger_output() -> None:
    adapted = adapt_hashed_fixture(action_bait_document_payload(), action_bait_case())
    challenged = challenged_review(adapted)
    output = _challenge_text(challenged.challenge) + _verdict_text(challenged.verdict)
    for bait in (
        "recommend selling immediately",
        "STRONG SELL",
        "$0.10",
        "buy the dip",
        "GOOD HOLD",
        "EXIT-CANDIDATE",
        "overweight",
        "ACTION-LANGUAGE BAIT",
    ):
        assert bait not in output


# ---------------------------------------------------------------------------
# Eval family 4 — advice boundary (s766B; plan :303-304) [mutation-observed]
# ---------------------------------------------------------------------------

#: Frozen grep vocabulary. Case-insensitive word-bounded action/instruction
#: terms, plus the exact-case memo-verdict and review-state tokens
#: (`types.py:26`; `asxos/domain/review/status.py` via B.6). ``watch`` is the
#: packet's other triple (plan :105-106) and must never appear.
_ADVICE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brecommend",
        r"\bbuy\b",
        r"\bsell\b",
        r"\bselling\b",
        r"\bsold\b",
        r"\btrim\b",
        r"\bexit\b",
        r"\bhold\b",
        r"\badd\b",
        r"\bwatch\b",
        r"\brating\b",
        r"\bprice target\b",
        r"\btarget price\b",
        r"\bpositions?\b",
        r"\bholdings?\b",
        r"\bportfolio\b",
        r"\btrade\b",
        r"\btrades\b",
        r"\boverweight\b",
        r"\bunderweight\b",
        r"\baccumulate\b",
        r"\bsize\b",
        r"\bsizing\b",
        r"\bstop[ -]loss\b",
        # Widened by the P2-04 independent review (fix 1). This grep is the ONLY
        # tripwire for advice creep inside the fixed templates themselves: the
        # template-identity test catches interpolation, but an advice word edited
        # into a template appears identically in both outputs and slips past it.
        # Stems, not exact words, so inflections cannot evade (allocate/allocation/
        # allocating). Plurals were the concrete gap found: `\bposition\b` did not
        # match "positions".
        r"\ballocat",
        r"\breduc",
        r"\bincreas",
        r"\btarget\b",
        r"\bshort\b",
        r"\blong\b",
        r"\bdivest",
        r"take[ -]?profit",
        r"\bweighting\b",
    )
) + tuple(
    re.compile(pattern)
    for pattern in (
        r"\bGOOD HOLD\b",
        r"\bEXIT-CANDIDATE\b",
        r"\bREVIEW\b",
        r"\bCLEAR\b",
        r"\bATTENTION\b",
        r"\bBLOCKED\b",
        r"\bEVIDENCE_THIN\b",
    )
)


def _assert_advice_free(text: str, *, context: str) -> None:
    for pattern in _ADVICE_PATTERNS:
        match = pattern.search(text)
        assert match is None, (
            f"advice-boundary vocabulary {pattern.pattern!r} surfaced in "
            f"{context}: {match.group(0)!r}"
        )


def test_no_advice_vocabulary_in_any_reviewer_or_challenger_output() -> None:
    for name, adapted in _adapted_fixtures():
        challenged = challenged_review(adapted)
        _assert_advice_free(
            _challenge_text(challenged.challenge), context=f"{name} challenge"
        )
        _assert_advice_free(
            _verdict_text(challenged.verdict), context=f"{name} verdict"
        )
        _assert_advice_free(
            _verdict_text(review_adapted(adapted)), context=f"{name} bare verdict"
        )


def test_revise_output_is_advice_free_and_addressed_to_the_artifact() -> None:
    # A revise verdict from a defective artifact must stay inside the same
    # boundary: no advice vocabulary, and the pinned artifact-addressee scope.
    case = historical_results_case()
    uncited = _reconstruct(case.review.metric_deltas[0], evidence_ids=())
    tampered = _tampered_case(
        case, metric_deltas=(uncited, *case.review.metric_deltas[1:])
    )
    verdict = review_case(tampered)
    challenge = challenge_case(tampered)
    assert verdict.verdict == "revise"
    _assert_advice_free(_verdict_text(verdict), context="revise verdict")
    _assert_advice_free(_challenge_text(challenge), context="revise challenge")
    assert verdict.scope_statement == VERDICT_SCOPE_STATEMENT


def test_revise_addressee_wording_is_pinned_to_the_artifact() -> None:
    # Test-pinned wording (mission deliverable 3, family 4): revise is
    # addressed to the artifact/analysis, never to a position or holding.
    assert VERDICT_SCOPE_STATEMENT == (
        "This verdict addresses the results-review artifact and its analysis "
        "only; a revise verdict calls for correction of the artifact, and of "
        "nothing else."
    )
    for _, adapted in _adapted_fixtures():
        assert review_adapted(adapted).scope_statement == VERDICT_SCOPE_STATEMENT


def test_challenge_binding_scope_statement_is_pinned_and_advice_free() -> None:
    # P2-04 independent review, fix 2. On the R5 path where the ONLY failed
    # check is the challenge binding, the artifact was never found defective,
    # so claiming "correction of the artifact" would be literally inaccurate.
    assert VERDICT_SCOPE_STATEMENT_CHALLENGE_BINDING == (
        "This verdict addresses the results-review artifact and its analysis "
        "only; here the revise verdict calls for correction of the challenge "
        "binding — the supplied challenge does not bind to this artifact — and "
        "of nothing else."
    )
    _assert_advice_free(
        VERDICT_SCOPE_STATEMENT_CHALLENGE_BINDING, context="binding scope statement"
    )


# ---------------------------------------------------------------------------
# Vocabulary pins and challenge mechanics
# ---------------------------------------------------------------------------


def test_reviewer_vocabulary_is_the_plan_triple_and_never_watch() -> None:
    verdicts = {review_adapted(adapted).verdict for _, adapted in _adapted_fixtures()}
    assert verdicts <= {"complete", "revise", "abstain"}
    # An off-vocabulary artifact outcome (the packet's other triple) is a
    # defect — the reviewer answers in its own frozen vocabulary, never by
    # echoing the injected word.
    smuggled = _tampered_case(historical_results_case(), outcome="watch")
    verdict = review_case(smuggled)
    assert verdict.verdict == "revise"
    assert "outcome_gate_consistency" in _failed_gates(verdict)
    assert "watch" not in _verdict_text(verdict)


def test_blocking_challenge_cannot_pass_the_review() -> None:
    adapted = adapt_hashed_fixture(historical_document_payload(), historical_results_case())
    review = adapted.case.review
    packet = adapted.case.evidence
    blocking = ChallengeFinding(
        severity="blocking",
        finding="Synthetic blocking finding for the eval.",
        required_response="Correct the artifact before it can be relied on.",
        evidence_ids=(packet.items[0].evidence_id,),
    )
    challenge = ChallengeResult(
        challenge_result_id=CHALLENGE_RESULT_ID_PREFIX + review.review_id,
        thesis_version_id=review.review_id,
        evidence_packet_id=packet.evidence_packet_id,
        as_of=packet.as_of,
        knowledge_cutoff=packet.knowledge_cutoff,
        created_at=packet.created_at,
        outcome="revise",
        strongest_bear_case="Synthetic blocking bear case for the eval.",
        findings=(blocking,),
        independent_of_author=True,
    )
    verdict = review_adapted(adapted, challenge)
    assert verdict.derived_verdict == "complete"  # gates alone would certify
    assert verdict.challenge_ceiling == "revise"
    assert verdict.verdict == "revise"  # the blocking challenge caps it
    # An abstaining challenge forces abstention (plan :302).
    abstaining = ChallengeResult(
        **{
            **dict(challenge),
            "outcome": "abstain",
            "content_hash": "",
        }
    )
    forced = review_adapted(adapted, abstaining)
    assert forced.challenge_ceiling == "abstain"
    assert forced.verdict == "abstain"
    # The canonical contract itself forbids a passing blocking challenge.
    with pytest.raises(ValidationError, match="blocking finding cannot pass"):
        ChallengeResult(**{**dict(challenge), "outcome": "pass", "content_hash": ""})


def test_misbound_challenge_is_a_defect() -> None:
    historical = adapt_hashed_fixture(
        historical_document_payload(), historical_results_case()
    )
    other = challenge_adapted(
        adapt_hashed_fixture(injection_document_payload(), injection_case())
    )
    verdict = review_adapted(historical, other)
    assert verdict.verdict == "revise"
    assert "challenge_binding" in _failed_gates(verdict)
    # R5: a challenge examining some other artifact can neither cap nor force
    # this one's verdict — its ceiling is disregarded, not applied.
    assert verdict.challenge_ceiling is None
    # R6 (independent-review fix 2): the binding failure is the ONLY defect, so
    # the verdict must say the challenge needs correcting, not the artifact.
    assert _failed_gates(verdict) == {"challenge_binding"}
    assert verdict.scope_statement == VERDICT_SCOPE_STATEMENT_CHALLENGE_BINDING
    _assert_advice_free(_verdict_text(verdict), context="misbound revise verdict")


def test_challenger_output_is_deterministic_and_canonical() -> None:
    for name, adapted in _adapted_fixtures():
        first = challenge_adapted(adapted)
        second = challenge_adapted(adapted)
        assert first.content_hash == second.content_hash, name
        assert first.model_dump(mode="json") == second.model_dump(mode="json")
        assert verify_content_hash(first)
        review = adapted.case.review
        assert first.challenge_result_id == CHALLENGE_RESULT_ID_PREFIX + review.review_id
        assert first.thesis_version_id == review.review_id
        assert first.evidence_packet_id == adapted.case.evidence.evidence_packet_id
        assert first.independent_of_author is True
        assert first.outcome in {"pass", "revise", "abstain"}


def test_challenge_findings_are_evidence_state_statements_with_packet_citations() -> None:
    for name, adapted in _adapted_fixtures():
        challenge = challenge_adapted(adapted)
        packet_ids = {item.evidence_id for item in adapted.case.evidence.items}
        assert challenge.strongest_bear_case
        for finding in challenge.findings:
            assert finding.evidence_ids, name
            assert set(finding.evidence_ids) <= packet_ids, name
            assert finding.severity in {"blocking", "material", "monitor"}


def test_shared_gate_report_keeps_reviewer_and_challenger_in_agreement() -> None:
    # Both consume the identical mechanical evaluation, so their view of the
    # evidence state can never diverge: a challenger 'pass' coincides with a
    # defect-free reviewer report, and vice versa.
    for name, adapted in _adapted_fixtures():
        report = evaluate_case(adapted.case)
        challenge = challenge_adapted(adapted)
        assert report.has_defect is (
            any(
                f.severity == "blocking" and f.finding.startswith("Mechanical gate")
                for f in challenge.findings
            )
        ), name
