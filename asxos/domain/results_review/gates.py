"""Frozen mechanical acceptance gates for the results review — mission P2-04.

One shared, deterministic evaluation of the P2 acceptance gates (plan
:307-309: 100% deterministic numeric checks, 100% material-claim citations,
no post-cutoff evidence) over a `ResultsReviewCase`. The reviewer
(`reviewer.py`) turns this report into a `complete | revise | abstain`
verdict; the independent challenger (`challenger.py`) turns the same report
into canonical `ChallengeFinding`s. Neither re-implements a gate.

Design invariants:

- **Report, never raise.** Unlike the frozen contract validators (which make
  a defective artifact unrepresentable at construction), these gates JUDGE an
  artifact that may have been built unvalidated (``model_construct``) — a
  failed gate is a reported defect, not an exception, so the reviewer can
  always emit a verdict. Total over field-complete instances whose field
  values carry the contract's declared types.
- **Template-only prose (G10 injection defense).** No gate detail ever
  interpolates artifact free text or document-payload text. Details are built
  from fixed templates, code-generated field coordinates
  (``metric_deltas[0]``), and counts. Evidence identifiers travel in the
  structured ``evidence_ids`` field, never in prose. This is the structural
  reason an adversarial source document cannot steer reviewer or challenger
  output.
- **The cutoff gate goes through the real adapter path.** Admissibility is
  computed by `adapter.partition_admissible_evidence` — the same frozen
  ``known_at <= knowledge_cutoff`` surface P2-03 ships — not a re-derivation.
- **Decimal-only arithmetic** (`.claude/rules/portfolio-conventions.md`
  §Decimal-only); the reconciliation and delta gates re-run the frozen exact
  rules (`contracts.StatutoryUnderlyingBridge`, `contracts.frozen_delta_pct`)
  with no tolerance.

No DB, no network, no persistence. Nothing here emits a recommendation state,
rating, price target, or sizing — gate output describes the state of the
EVIDENCE and the artifact, only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal

from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.results_review.adapter import partition_admissible_evidence
from asxos.domain.results_review.contracts import (
    ResultsReviewArtifact,
    ResultsReviewCase,
    frozen_delta_pct,
)

#: The frozen gate names. ``challenge_binding`` is evaluated by the reviewer
#: (it needs the supplied ChallengeResult); every other gate is evaluated
#: here. All are defect-class: any failure means the artifact must be
#: corrected before it can be certified.
GateName = Literal[
    "integrity_seal",
    "citation_closure",
    "bridge_reconciliation",
    "delta_arithmetic",
    "cutoff_admissibility",
    "tax_readiness_earned",
    "outcome_gate_consistency",
    "challenge_binding",
]

#: The plan-:303 outcome triple, restated for gate logic. The authoritative
#: type is `contracts.ResultsReviewOutcome`; this frozenset exists so the
#: consistency gate can judge an UNVALIDATED artifact whose outcome may lie
#: outside the triple (e.g. a vocabulary-injection attempt).
FROZEN_OUTCOME_TRIPLE: Final[frozenset[str]] = frozenset({"complete", "revise", "abstain"})


@dataclass(frozen=True)
class GateCheck:
    """One mechanical gate evaluation: name, result, template detail."""

    gate: GateName
    passed: bool
    detail: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MechanicalGateReport:
    """The complete deterministic gate evaluation of one case."""

    checks: tuple[GateCheck, ...]
    missing_evidence_count: int
    unresolved_conflict_count: int
    resolved_conflict_count: int
    thesis_pillar_effect_count: int
    falsifier_count: int
    #: The artifact's own outcome claim, unvalidated (may be off-vocabulary
    #: on tampered input — the consistency gate reports that as a defect).
    artifact_outcome: str
    packet_evidence_ids: tuple[str, ...]

    @property
    def defects(self) -> tuple[GateCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)

    @property
    def has_defect(self) -> bool:
        return any(not check.passed for check in self.checks)


def _material_claim_coordinates(
    review: ResultsReviewArtifact,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Every material claim as (code-generated coordinate, cited evidence ids).

    Material claims (plan :307 "100% material-claim citations"): metric
    deltas, bridge adjustments, guidance changes, thesis-pillar effects,
    catalysts, falsifiers, and evidence conflicts. Coordinates are built from
    field names and indices only — never from artifact free text.
    """
    coordinates: list[tuple[str, tuple[str, ...]]] = []
    for i, delta in enumerate(review.metric_deltas):
        coordinates.append((f"metric_deltas[{i}]", tuple(delta.evidence_ids)))
    for i, bridge in enumerate(review.statutory_underlying_bridges):
        for j, adjustment in enumerate(bridge.adjustments):
            coordinates.append(
                (
                    f"statutory_underlying_bridges[{i}].adjustments[{j}]",
                    tuple(adjustment.evidence_ids),
                )
            )
    for i, guidance in enumerate(review.guidance_changes):
        coordinates.append((f"guidance_changes[{i}]", tuple(guidance.evidence_ids)))
    for field_name, statements in (
        ("thesis_pillar_effects", review.thesis_pillar_effects),
        ("catalysts", review.catalysts),
        ("falsifiers", review.falsifiers),
    ):
        for i, statement in enumerate(statements):
            coordinates.append((f"{field_name}[{i}]", tuple(statement.evidence_ids)))
    for i, conflict in enumerate(review.conflicts):
        coordinates.append((f"conflicts[{i}]", tuple(conflict.evidence_ids)))
    return tuple(coordinates)


def _integrity_seal_check(case: ResultsReviewCase) -> GateCheck:
    roles = (
        ("document", case.document),
        ("evidence", case.evidence),
        ("frozen_input", case.review.frozen_input),
        ("tax_assessment_reference", case.review.tax_assessment_reference),
        ("artifact", case.review),
    )
    failed = tuple(name for name, artifact in roles if not verify_content_hash(artifact))
    if failed:
        return GateCheck(
            gate="integrity_seal",
            passed=False,
            detail=(
                "content seal absent or diverging from canonical content for: "
                + ", ".join(failed)
            ),
        )
    return GateCheck(
        gate="integrity_seal",
        passed=True,
        detail="every content seal verifies against canonical artifact content",
    )


def _citation_closure_check(
    review: ResultsReviewArtifact, packet_ids: frozenset[str]
) -> GateCheck:
    offending = tuple(
        coordinate
        for coordinate, cited in _material_claim_coordinates(review)
        if not cited or any(evidence_id not in packet_ids for evidence_id in cited)
    )
    if offending:
        return GateCheck(
            gate="citation_closure",
            passed=False,
            detail=(
                f"{len(offending)} material claim(s) cite nothing, or cite outside "
                "the frozen packet: " + ", ".join(offending)
            ),
        )
    return GateCheck(
        gate="citation_closure",
        passed=True,
        detail="every material claim cites at least one item inside the frozen packet",
    )


def _bridge_reconciliation_check(review: ResultsReviewArtifact) -> GateCheck:
    offending: list[str] = []
    for i, bridge in enumerate(review.statutory_underlying_bridges):
        bridged = bridge.statutory + sum(
            (adjustment.amount for adjustment in bridge.adjustments), start=Decimal("0")
        )
        if bridged != bridge.underlying:
            offending.append(f"statutory_underlying_bridges[{i}]")
    if offending:
        return GateCheck(
            gate="bridge_reconciliation",
            passed=False,
            detail=(
                f"{len(offending)} bridge(s) fail exact statutory-plus-adjustments "
                "reconciliation: " + ", ".join(offending)
            ),
        )
    return GateCheck(
        gate="bridge_reconciliation",
        passed=True,
        detail="every bridge reconciles exactly, with no tolerance",
    )


def _delta_arithmetic_check(review: ResultsReviewArtifact) -> GateCheck:
    offending: list[str] = []
    for i, delta in enumerate(review.metric_deltas):
        if delta.prior_value is None or delta.prior_value == 0:
            if delta.delta_pct is not None:
                offending.append(f"metric_deltas[{i}]")
        elif delta.delta_pct != frozen_delta_pct(delta.current_value, delta.prior_value):
            offending.append(f"metric_deltas[{i}]")
    if offending:
        return GateCheck(
            gate="delta_arithmetic",
            passed=False,
            detail=(
                f"{len(offending)} metric delta(s) diverge from the frozen "
                "computation: " + ", ".join(offending)
            ),
        )
    return GateCheck(
        gate="delta_arithmetic",
        passed=True,
        detail="every metric delta equals the frozen computation exactly",
    )


def _cutoff_admissibility_check(case: ResultsReviewCase) -> GateCheck:
    try:
        _, excluded = partition_admissible_evidence(
            case.evidence.items, case.evidence.knowledge_cutoff
        )
    except ValueError:
        return GateCheck(
            gate="cutoff_admissibility",
            passed=False,
            detail="the knowledge cutoff is not a timezone-aware UTC instant",
        )
    problems: list[str] = []
    if excluded:
        problems.append(f"{len(excluded)} evidence item(s) known after the knowledge cutoff")
    if case.document.release_at > case.evidence.knowledge_cutoff:
        problems.append("the reviewed document was released after the knowledge cutoff")
    if problems:
        return GateCheck(
            gate="cutoff_admissibility",
            passed=False,
            detail="; ".join(problems),
            evidence_ids=tuple(item.evidence_id for item in excluded),
        )
    return GateCheck(
        gate="cutoff_admissibility",
        passed=True,
        detail="no evidence, and no document, postdates the knowledge cutoff",
    )


def _tax_readiness_earned_check(review: ResultsReviewArtifact) -> GateCheck:
    # str() + vocabulary check before any interpolation: on an unvalidated
    # instance the field may carry arbitrary text, and gate prose must stay
    # template-only (G10).
    readiness = str(review.tax_assessment_reference.readiness)
    if readiness not in {"pass", "fail", "unknown"}:
        return GateCheck(
            gate="tax_readiness_earned",
            passed=False,
            detail="tax readiness lies outside the frozen vocabulary (types.py:410)",
        )
    if readiness == "pass" and review.data_mode != "real":
        return GateCheck(
            gate="tax_readiness_earned",
            passed=False,
            detail=(
                "tax readiness claims 'pass' on non-real input; no producer is "
                "wired (G12, freeze record §9), so the claim is unearned"
            ),
        )
    return GateCheck(
        gate="tax_readiness_earned",
        passed=True,
        detail=(
            f"tax readiness is '{readiness}'; a non-pass readiness keeps every "
            "downstream state gate closed at the canonical boundary "
            "(types.py:512-516), and unknown is a valid, successful outcome"
        ),
    )


def _outcome_gate_consistency_check(review: ResultsReviewArtifact) -> GateCheck:
    problems: list[str] = []
    outcome = str(review.outcome)
    if outcome not in FROZEN_OUTCOME_TRIPLE:
        problems.append("the artifact outcome lies outside the frozen triple (plan :303)")
    if review.missing_evidence and outcome != "abstain":
        problems.append(
            "recorded missing evidence must force an abstaining artifact outcome"
        )
    if any(conflict.resolution is None for conflict in review.conflicts) and (
        outcome == "complete"
    ):
        problems.append("an unresolved evidence conflict forbids a completed artifact outcome")
    if problems:
        return GateCheck(
            gate="outcome_gate_consistency",
            passed=False,
            detail="; ".join(problems),
        )
    return GateCheck(
        gate="outcome_gate_consistency",
        passed=True,
        detail="the artifact outcome respects the frozen outcome gates",
    )


def evaluate_case(case: ResultsReviewCase) -> MechanicalGateReport:
    """Run every frozen mechanical gate over one case, deterministically.

    Pure and in-memory. The same report feeds both the reviewer's verdict and
    the challenger's findings, so the two can never disagree about what the
    evidence state IS — only their outputs differ in shape (a verdict versus
    canonical findings).
    """
    review = case.review
    packet_ids = tuple(sorted({item.evidence_id for item in case.evidence.items}))
    checks = (
        _integrity_seal_check(case),
        _citation_closure_check(review, frozenset(packet_ids)),
        _bridge_reconciliation_check(review),
        _delta_arithmetic_check(review),
        _cutoff_admissibility_check(case),
        _tax_readiness_earned_check(review),
        _outcome_gate_consistency_check(review),
    )
    return MechanicalGateReport(
        checks=checks,
        missing_evidence_count=len(review.missing_evidence),
        unresolved_conflict_count=sum(
            1 for conflict in review.conflicts if conflict.resolution is None
        ),
        resolved_conflict_count=sum(
            1 for conflict in review.conflicts if conflict.resolution is not None
        ),
        thesis_pillar_effect_count=len(review.thesis_pillar_effects),
        falsifier_count=len(review.falsifiers),
        artifact_outcome=str(review.outcome),
        packet_evidence_ids=packet_ids,
    )
