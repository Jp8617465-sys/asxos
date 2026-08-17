"""Deterministic independent challenger — mission P2-04 (plan item 5, gap G9).

Produces the CANONICAL `ChallengeResult` (`asxos/domain/decision_engine/
types.py:317-338`, byte-unmodified) over one results-review artifact — the
first producer of that contract in the repo (matrix G9, :353). Every finding
is an EVIDENCE-STATE statement: uncited material claims, failed
reconciliations, post-cutoff evidence, conflicts, missing data, and
thesis-pillar effects. The challenger never emits a rating, price target,
trade, position-size instruction, portfolio instruction, or thesis mutation
(plan :303-304; s766B firewall) — its outcome vocabulary is the canonical
``pass | revise | abstain``, and per plan :302 a challenge can force revision
or abstention, never an action.

**Independence (`independent_of_author=True`) semantics in this increment:**
the challenger is a pure function of the frozen case. It holds no authorship
state, never reads the reviewer's verdict, and derives every statement
mechanically from the shared gate evaluation (`gates.evaluate_case`) — the
author of the artifact contributes nothing to the challenge but the frozen
case itself. The packet's reviewer/challenger *agents* with bounded
qualitative prompts (plan :271) are deferred by name
(``p2_deferred_bounded_prompt_shell``); this is the deterministic core.

**Injection defense (G10):** challenge prose is template-only. No finding,
required response, or bear-case sentence ever interpolates artifact free text
or document-payload text (the payload never reaches this module at all — the
artifact carries only its hash). Counts and code-generated coordinates are
the only variable content; evidence identifiers travel in the structured
``evidence_ids`` fields. An adversarial source document therefore cannot
place a single word into challenge output.

**Subject binding (recorded reading):** the canonical contract's subject slot
is named ``thesis_version_id``; no `ThesisVersion` exists on this path (the
artifact is "an analysis input to a ThesisVersion", plan :180-181), and
`types.py` is read-only to this mission. The slot therefore carries the
challenged `ResultsReviewArtifact.review_id` verbatim
(`CHALLENGED_ARTIFACT_BINDING`); renaming or widening the slot is a
`target-architecture.md` B.4 governor amendment, deferred by name
(``p2_deferred_challenge_subject_binding``).

Deterministic, pure, in-memory: no DB, no network, no persistence, no wall
clock (timestamps are the frozen packet's own). Decimal-only arithmetic.
"""

from __future__ import annotations

from typing import Final, Literal

from asxos.domain.decision_engine.types import ChallengeFinding, ChallengeResult
from asxos.domain.results_review.adapter import AdaptedResultsReview
from asxos.domain.results_review.contracts import ResultsReviewCase
from asxos.domain.results_review.gates import GateCheck, MechanicalGateReport, evaluate_case

#: Deterministic challenge identity: the prefix plus the challenged
#: artifact's ``review_id``.
CHALLENGE_RESULT_ID_PREFIX: Final[str] = "chg-"

#: The recorded subject-binding rule (see module docstring).
CHALLENGED_ARTIFACT_BINDING: Final[str] = (
    "ChallengeResult.thesis_version_id carries ResultsReviewArtifact.review_id verbatim"
)

#: Fixed required-response templates per mechanical gate. Every response is
#: addressed to the artifact and its analysis — never to any account,
#: instrument, or capital state.
_GATE_REQUIRED_RESPONSE: Final[dict[str, str]] = {
    "integrity_seal": (
        "Rebuild the artifact through contract validation so every content seal "
        "verifies."
    ),
    "citation_closure": (
        "Correct the artifact so every material claim cites evidence inside the "
        "frozen packet."
    ),
    "bridge_reconciliation": (
        "Correct the bridge figures or adjustments until the reconciliation is "
        "exact."
    ),
    "delta_arithmetic": (
        "Recompute each delta with the frozen computation, or carry an explicit "
        "absent value."
    ),
    "cutoff_admissibility": (
        "Remove every input that postdates the knowledge cutoff and re-freeze the "
        "packet."
    ),
    "tax_readiness_earned": (
        "Carry the honest readiness value; a pass must come from the named "
        "producers on real inputs."
    ),
    "outcome_gate_consistency": (
        "Set the artifact outcome that the frozen outcome gates force for this "
        "evidence state."
    ),
    "challenge_binding": (
        "Bind the challenge to the artifact and packet it examines before relying "
        "on it."
    ),
}


def _defect_findings(
    report: MechanicalGateReport,
) -> tuple[ChallengeFinding, ...]:
    findings: list[ChallengeFinding] = []
    for check in report.defects:
        findings.append(
            ChallengeFinding(
                severity="blocking",
                finding=f"Mechanical gate '{check.gate}' failed: {check.detail}.",
                required_response=_GATE_REQUIRED_RESPONSE[check.gate],
                evidence_ids=_finding_evidence_ids(check, report),
            )
        )
    return tuple(findings)


def _finding_evidence_ids(
    check: GateCheck, report: MechanicalGateReport
) -> tuple[str, ...]:
    """The structured citation base for one finding.

    A gate that identified specific evidence items cites them; otherwise the
    finding rests on the state of the whole frozen packet and cites it
    (sorted, capped at the contract's 100-item bound). The packet always
    carries at least one item (`EvidencePacket.items` min_length=1).
    """
    if check.evidence_ids:
        return check.evidence_ids[:100]
    return report.packet_evidence_ids[:100]


def _conflict_evidence_ids(case: ResultsReviewCase, *, resolved: bool) -> tuple[str, ...]:
    ids: set[str] = set()
    for conflict in case.review.conflicts:
        if (conflict.resolution is not None) == resolved:
            ids.update(conflict.evidence_ids)
    return tuple(sorted(ids))[:100]


def _pillar_evidence_ids(case: ResultsReviewCase) -> tuple[str, ...]:
    ids: set[str] = set()
    for statement in case.review.thesis_pillar_effects:
        ids.update(statement.evidence_ids)
    return tuple(sorted(ids))[:100]


def _strongest_bear_case(report: MechanicalGateReport) -> str:
    """The strongest standing challenge, from templates and counts only."""
    if report.falsifier_count:
        sentences = [
            f"The artifact records {report.falsifier_count} falsifier statement(s); "
            "read against their cited evidence, they are the strongest standing "
            "challenge to the analysis."
        ]
    else:
        sentences = [
            "The artifact records no falsifier statement; the absence of any "
            "recorded falsifier is itself the strongest standing challenge to the "
            "analysis."
        ]
    if report.unresolved_conflict_count:
        sentences.append(
            f"{report.unresolved_conflict_count} recorded evidence conflict(s) "
            "remain unresolved."
        )
    if report.missing_evidence_count:
        sentences.append(
            f"{report.missing_evidence_count} named evidence input(s) are absent "
            "from the frozen packet."
        )
    if report.has_defect:
        sentences.append(
            f"{len(report.defects)} mechanical gate(s) failed; the analysis cannot "
            "be relied on until the artifact is corrected."
        )
    return " ".join(sentences)


def challenge_case(case: ResultsReviewCase) -> ChallengeResult:
    """Challenge one results-review case, deterministically.

    Finding derivation (all evidence-state, all template-prose):

    - every failed mechanical gate -> one ``blocking`` finding;
    - recorded missing evidence -> one ``blocking`` finding (forces
      abstention, plan :308);
    - unresolved evidence conflicts -> one ``blocking`` finding (forces
      abstention behind the frozen complete-forbidding gate);
    - resolved conflicts -> one ``material`` finding (recorded, retained);
    - thesis-pillar effects -> one ``monitor`` finding (open to
      re-examination).

    Outcome rule (plan :302 — a challenge can force revision or abstention):
    any defect finding -> ``revise``; else any insufficiency finding ->
    ``abstain``; else ``pass``. A ``pass`` therefore never coexists with a
    blocking finding, which is also the canonical contract's own validator
    (types.py:331-333).
    """
    report = evaluate_case(case)
    review = case.review

    defect_findings = _defect_findings(report)
    insufficiency_findings: list[ChallengeFinding] = []
    context_findings: list[ChallengeFinding] = []

    if report.missing_evidence_count:
        insufficiency_findings.append(
            ChallengeFinding(
                severity="blocking",
                finding=(
                    f"The frozen packet lacks {report.missing_evidence_count} named "
                    "evidence input(s); no completed analysis can rest on it."
                ),
                required_response=(
                    "Abstention stands until the named evidence enters a frozen "
                    "packet and a new artifact is produced."
                ),
                evidence_ids=report.packet_evidence_ids[:100],
            )
        )
    if report.unresolved_conflict_count:
        insufficiency_findings.append(
            ChallengeFinding(
                severity="blocking",
                finding=(
                    f"{report.unresolved_conflict_count} recorded evidence "
                    "conflict(s) remain unresolved."
                ),
                required_response=(
                    "Resolve each recorded conflict under the frozen source-rank "
                    "rule, or abstention stands."
                ),
                evidence_ids=(
                    _conflict_evidence_ids(case, resolved=False)
                    or report.packet_evidence_ids[:100]
                ),
            )
        )
    if report.resolved_conflict_count:
        context_findings.append(
            ChallengeFinding(
                severity="material",
                finding=(
                    f"{report.resolved_conflict_count} recorded evidence "
                    "conflict(s) carry a recorded resolution."
                ),
                required_response=(
                    "Retain each recorded resolution and its citations for audit."
                ),
                evidence_ids=(
                    _conflict_evidence_ids(case, resolved=True)
                    or report.packet_evidence_ids[:100]
                ),
            )
        )
    if report.thesis_pillar_effect_count:
        context_findings.append(
            ChallengeFinding(
                severity="monitor",
                finding=(
                    f"{report.thesis_pillar_effect_count} thesis-pillar effect "
                    "statement(s) rest on cited evidence and remain open to "
                    "re-examination."
                ),
                required_response=(
                    "Re-examine each statement against its cited evidence at the "
                    "next results review."
                ),
                evidence_ids=(
                    _pillar_evidence_ids(case) or report.packet_evidence_ids[:100]
                ),
            )
        )

    outcome: Literal["pass", "revise", "abstain"]
    if defect_findings:
        outcome = "revise"
    elif insufficiency_findings:
        outcome = "abstain"
    else:
        outcome = "pass"

    return ChallengeResult(
        challenge_result_id=CHALLENGE_RESULT_ID_PREFIX + review.review_id,
        thesis_version_id=review.review_id,  # CHALLENGED_ARTIFACT_BINDING
        evidence_packet_id=case.evidence.evidence_packet_id,
        as_of=case.evidence.as_of,
        knowledge_cutoff=case.evidence.knowledge_cutoff,
        created_at=case.evidence.created_at,
        outcome=outcome,
        strongest_bear_case=_strongest_bear_case(report),
        findings=(*defect_findings, *insufficiency_findings, *context_findings),
        independent_of_author=True,
    )


def challenge_adapted(adapted: AdaptedResultsReview) -> ChallengeResult:
    """Challenge an adapter-produced review — the real ingestion path (P2-03)."""
    return challenge_case(adapted.case)
