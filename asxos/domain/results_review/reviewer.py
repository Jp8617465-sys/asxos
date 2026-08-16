"""Deterministic results reviewer — mission P2-04 (plan required-work item 6).

Consumes an adapter-produced results review (P2-03, the only real ingestion
path), applies the frozen mechanical acceptance gates (`gates.py`), and emits
exactly ``complete | revise | abstain`` — the plan's own ruled triple, quoted:
*"Return `complete`, `revise`, or `abstain`; do not return a rating, price
target, trade, or position-size instruction"* (plan :303). The vocabulary is
`contracts.ResultsReviewOutcome`, verbatim. It is not a decision state, not a
memo verdict, and not a review state; no conversion between those
vocabularies exists here in either direction (`target-architecture.md` B.6).
``watch`` — a member of the packet's other triple (plan :105-106) — is
unrepresentable in this reviewer's output.

Review-procedure record (freeze-record changelog style; each rule is
test-pinned in ``tests/test_results_review_reviewer_challenger.py``):

- **R1 — Gate set.** The defect gates are `gates.py`'s seven mechanical
  checks (integrity seal, citation closure, bridge reconciliation, delta
  arithmetic, cutoff admissibility, earned tax readiness, outcome-gate
  consistency) plus ``challenge_binding`` when a challenge is supplied. All
  are deterministic re-runs of frozen P2-02 rules — no reviewer-invented
  rule, no qualitative judgement.
- **R2 — Verdict derivation.** Any failed defect gate -> ``revise`` (the
  artifact must be corrected). Otherwise any insufficiency condition
  (recorded missing evidence; an unresolved evidence conflict; the
  artifact's own abstaining outcome) -> ``abstain`` (the evidence cannot
  support a completed review — the SUCCESS case on incomplete evidence,
  plan :308, matrix :366-368). Otherwise the artifact's own frozen outcome
  stands (``complete`` or ``revise``): the reviewer confirms or demotes,
  never upgrades.
- **R3 — Precedence.** Defects dominate insufficiency: a defective
  artifact's own insufficiency claims cannot be relied on, so correction
  (``revise``) is the verdict even when missing evidence is also recorded.
  The insufficiency conditions remain reported alongside.
- **R4 — Challenge ceiling.** Per plan :302 an independent challenge "can
  force revision or abstention": a supplied `ChallengeResult` with outcome
  ``revise`` caps the verdict at ``revise``; outcome ``abstain`` forces
  ``abstain``; outcome ``pass`` imposes no cap. Any blocking finding caps
  the verdict at ``revise`` regardless of the stated outcome — **a blocking
  challenge can never yield ``complete``** (mirrors types.py:331-333). The
  final verdict is the more conservative of the derived verdict and the cap
  (``complete`` > ``revise`` > ``abstain``).
- **R5 — Challenge binding.** A supplied challenge must bind to THIS
  artifact: subject identity (``thesis_version_id`` carries the artifact's
  ``review_id`` — `challenger.CHALLENGED_ARTIFACT_BINDING`), packet
  identity, knowledge cutoff, verified content seal. A mis-bound challenge
  is a defect (``revise``) — an unverifiable challenge can never certify —
  and its R4 ceiling is DISREGARDED: a challenge that examines some other
  artifact can neither cap nor force this one's verdict.
- **R6 — Addressee.** Every verdict carries `VERDICT_SCOPE_STATEMENT`,
  verbatim: a ``revise`` is addressed to the artifact and its analysis,
  never to a position, holding, or any capital state. No rating, price
  target, trade, size, portfolio instruction, or thesis mutation exists in
  this output (plan :303-304; s766B firewall; matrix :485).

Anything that would REDEFINE what the three words mean is a JAMES_NEEDED
governor question, not a reviewer change. Deterministic, pure, in-memory: no
DB, no network, no persistence, no wall clock. Decimal-only arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from asxos.domain.decision_engine.types import ChallengeResult, verify_content_hash
from asxos.domain.results_review.adapter import AdaptedResultsReview
from asxos.domain.results_review.challenger import challenge_case
from asxos.domain.results_review.contracts import ResultsReviewCase, ResultsReviewOutcome
from asxos.domain.results_review.gates import GateCheck, evaluate_case

#: R6 — pinned verbatim by the advice-boundary eval family.
VERDICT_SCOPE_STATEMENT: Final[str] = (
    "This verdict addresses the results-review artifact and its analysis only; "
    "a revise verdict calls for correction of the artifact, and of nothing else."
)

#: R2/R4 — conservatism order for the ceiling rule.
_VERDICT_RANK: Final = MappingProxyType({"abstain": 0, "revise": 1, "complete": 2})

#: R2 — fixed insufficiency statements (template-only prose, G10).
_MISSING_EVIDENCE_STATEMENT: Final[str] = (
    "missing evidence is recorded; the frozen gate forces abstention"
)
_UNRESOLVED_CONFLICT_STATEMENT: Final[str] = (
    "an unresolved evidence conflict is recorded; a completed review is forbidden"
)
_ARTIFACT_ABSTAINS_STATEMENT: Final[str] = (
    "the artifact abstains on its own frozen outcome; an abstention is never upgraded"
)


@dataclass(frozen=True)
class ReviewerVerdict:
    """The reviewer's complete deterministic output. Never persisted."""

    review_id: str
    verdict: ResultsReviewOutcome
    derived_verdict: ResultsReviewOutcome
    challenge_ceiling: ResultsReviewOutcome | None
    checks: tuple[GateCheck, ...]
    insufficiencies: tuple[str, ...]
    scope_statement: str = VERDICT_SCOPE_STATEMENT


@dataclass(frozen=True)
class ChallengedReview:
    """One challenged review: the canonical challenge plus the verdict it capped."""

    challenge: ChallengeResult
    verdict: ReviewerVerdict


def _challenge_binding_check(
    case: ResultsReviewCase, challenge: ChallengeResult
) -> GateCheck:
    """R5 — the supplied challenge must bind to this artifact and packet."""
    problems: list[str] = []
    if challenge.thesis_version_id != case.review.review_id:
        problems.append("subject identity")
    if challenge.evidence_packet_id != case.evidence.evidence_packet_id:
        problems.append("packet identity")
    if challenge.knowledge_cutoff != case.evidence.knowledge_cutoff:
        problems.append("knowledge cutoff")
    if challenge.independent_of_author is not True:
        # Unrepresentable in a validated ChallengeResult (Literal[True],
        # types.py:327); guarded anyway for unvalidated constructs.
        problems.append("independence")
    if not verify_content_hash(challenge):
        problems.append("content seal")
    if problems:
        return GateCheck(
            gate="challenge_binding",
            passed=False,
            detail=(
                "the supplied challenge does not bind to this artifact: "
                + ", ".join(problems)
            ),
        )
    return GateCheck(
        gate="challenge_binding",
        passed=True,
        detail="the supplied challenge binds to this artifact and its frozen packet",
    )


def _challenge_ceiling(challenge: ChallengeResult) -> ResultsReviewOutcome | None:
    """R4 — the cap a challenge imposes on the verdict (plan :302)."""
    ceiling: ResultsReviewOutcome | None
    if challenge.outcome == "revise":
        ceiling = "revise"
    elif challenge.outcome == "abstain":
        ceiling = "abstain"
    else:  # a passed challenge imposes no cap
        ceiling = None
    if any(finding.severity == "blocking" for finding in challenge.findings):
        # A blocking challenge can never yield complete, whatever its stated
        # outcome claims (belt-and-braces over types.py:331-333).
        ceiling = "abstain" if ceiling == "abstain" else "revise"
    return ceiling


def review_case(
    case: ResultsReviewCase, challenge: ChallengeResult | None = None
) -> ReviewerVerdict:
    """Apply the frozen gates to one case and emit the verdict (R1-R6).

    Total over field-complete cases: a defective artifact yields ``revise``
    with the failed checks reported — the reviewer judges, it does not raise.
    """
    report = evaluate_case(case)
    checks: tuple[GateCheck, ...] = report.checks
    challenge_bound = False
    if challenge is not None:
        binding = _challenge_binding_check(case, challenge)
        checks = (*checks, binding)
        challenge_bound = binding.passed

    insufficiencies: list[str] = []
    if report.missing_evidence_count:
        insufficiencies.append(_MISSING_EVIDENCE_STATEMENT)
    if report.unresolved_conflict_count:
        insufficiencies.append(_UNRESOLVED_CONFLICT_STATEMENT)
    if report.artifact_outcome == "abstain":
        insufficiencies.append(_ARTIFACT_ABSTAINS_STATEMENT)

    derived: ResultsReviewOutcome
    if any(not check.passed for check in checks):
        derived = "revise"  # R2/R3: defects dominate
    elif insufficiencies:
        derived = "abstain"
    elif report.artifact_outcome == "revise":
        derived = "revise"  # R2: the artifact's own outcome is never upgraded
    else:
        # Gate-consistent, sufficient, and in-vocabulary (the consistency
        # gate passed), so the only remaining artifact outcome is complete.
        derived = "complete"

    # R5: only a challenge that binds to THIS artifact can cap its verdict.
    ceiling = (
        _challenge_ceiling(challenge)
        if challenge is not None and challenge_bound
        else None
    )
    verdict = (
        derived
        if ceiling is None
        else min(derived, ceiling, key=lambda outcome: _VERDICT_RANK[outcome])
    )
    return ReviewerVerdict(
        review_id=str(case.review.review_id),
        verdict=verdict,
        derived_verdict=derived,
        challenge_ceiling=ceiling,
        checks=checks,
        insufficiencies=tuple(insufficiencies),
    )


def review_adapted(
    adapted: AdaptedResultsReview, challenge: ChallengeResult | None = None
) -> ReviewerVerdict:
    """Review an adapter-produced case — the real ingestion path (P2-03)."""
    return review_case(adapted.case, challenge)


def challenged_review(adapted: AdaptedResultsReview) -> ChallengedReview:
    """The plan-:302/:303 sequence: independent challenge, then the verdict.

    Runs the deterministic challenger over the adapted case and reviews the
    same case with that challenge applied as the R4 ceiling. The challenger
    never sees reviewer state (independence), and both consume the identical
    frozen case.
    """
    challenge = challenge_case(adapted.case)
    return ChallengedReview(
        challenge=challenge,
        verdict=review_adapted(adapted, challenge),
    )
