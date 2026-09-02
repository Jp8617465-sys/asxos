"""Slice 2.5 — the thin challenge layer (ADR §6, D12/D13/D14).

`challenge_thesis()` is the only producer: it runs the Layer-1 rules
(`rules.py`, deterministic code), the Layer-2 template shell (`steelman.py`),
consults the disposition log (`log.py`) and returns the canonical, frozen
`ChallengeResult` — never a rating, size, target, trade or advice.

Outcome ladder (ADR :302 — a challenge can force revision or abstention,
never an action):

    any blocking finding ................................. "abstain"
    any material finding without an accepted disposition . "revise"
    otherwise ............................................ "pass"

The contract itself refuses `pass` alongside a blocking finding
(`types.py` ChallengeResult validator), so the first rung is doubly held.
An overridden blocking finding is still blocking: James's override is
RECORDED (the §1.6 health metric) but does not change the outcome — only a
revised proposal that no longer breaches the register can pass.

Rule #11: this package imports nothing under `asxos.domain.models`, reads no
`signals`, and its inputs are typed measurements the caller made. It
imports nothing under `asxos.domain.portfolio` either — sizing lives
downstream in `decision_engine/sizer.py`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from asxos.domain.decision_engine.challenge.log import DispositionLog
from asxos.domain.decision_engine.challenge.rules import (
    RULE_NAMES,
    ChallengeInput,
    PortfolioState,
    RuleOutcome,
    findings_of,
    run_layer1,
)
from asxos.domain.decision_engine.challenge.steelman import (
    BoundaryError,
    admit_llm_finding,
    falsifiability,
    outside_view,
    readmit,
    strongest_bear_case,
)
from asxos.domain.decision_engine.types import ChallengeFinding, ChallengeResult

__all__ = [
    "RULE_NAMES",
    "BoundaryError",
    "ChallengeInput",
    "DispositionLog",
    "PortfolioState",
    "RuleOutcome",
    "admit_llm_finding",
    "challenge_thesis",
    "outcome_for",
    "run_layer1",
]


def outcome_for(
    findings: tuple[ChallengeFinding, ...], log: DispositionLog
) -> Literal["pass", "revise", "abstain"]:
    if any(f.severity == "blocking" for f in findings):
        return "abstain"
    if any(f.severity == "material" and not log.accepted(f) for f in findings):
        return "revise"
    return "pass"


def challenge_thesis(
    x: ChallengeInput,
    *,
    thesis_version_id: str,
    evidence_packet_id: str,
    knowledge_cutoff: datetime,
    created_at: datetime | None = None,
    log: DispositionLog | None = None,
    llm_findings: tuple[ChallengeFinding, ...] = (),
    known_evidence_ids: frozenset[str] | None = None,
) -> ChallengeResult:
    """Challenge one proposal. Every entry of `llm_findings` is re-admitted
    through `admit_llm_finding` here, so constructing a `ChallengeFinding`
    directly cannot bypass the door; with `known_evidence_ids` the citations
    must also resolve inside the packet."""
    if knowledge_cutoff.date() != x.as_of:
        raise ValueError("ChallengeInput.as_of must equal the UTC knowledge_cutoff date")
    admitted = tuple(readmit(f, known_evidence_ids=known_evidence_ids) for f in llm_findings)
    log = log or DispositionLog()
    outcomes = run_layer1(x)
    findings = (*findings_of(outcomes), *outside_view(x), *falsifiability(x), *admitted)
    return ChallengeResult(
        challenge_result_id=f"chr-{thesis_version_id}",
        thesis_version_id=thesis_version_id,
        evidence_packet_id=evidence_packet_id,
        as_of=x.as_of,
        knowledge_cutoff=knowledge_cutoff,
        created_at=created_at or knowledge_cutoff,
        outcome=outcome_for(findings, log),
        strongest_bear_case=strongest_bear_case(x, outcomes),
        findings=findings,
        independent_of_author=True,
    )
