"""Typed contracts for the research-to-decision target architecture.

These are logical contracts, not one-table-per-model migration instructions.
They deliberately have no database, agent, or renderer dependency. Every
numeric value rejects float input so capital-relevant values remain Decimal
exact throughout the prototype.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RecommendationState = Literal["initiate", "watch", "avoid", "add", "trim", "exit_review", "abstain"]

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _contains_float(value: object) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_contains_float(k) or _contains_float(v) for k, v in value.items())
    if isinstance(value, list | tuple | set | frozenset):
        return any(_contains_float(item) for item in value)
    return False


class Contract(BaseModel):
    """Strict, immutable base for all decision-engine boundary objects."""

    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    @model_validator(mode="before")
    @classmethod
    def reject_float_input(cls, value: object) -> object:
        if _contains_float(value):
            raise ValueError("float input is forbidden; use Decimal or a decimal string")
        return value


class EvidenceItem(Contract):
    evidence_id: str = Field(min_length=1)
    evidence_type: Literal[
        "market_fact", "fundamental_fact", "source_document", "theme_fact", "portfolio_fact"
    ]
    title: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    observed_at: date
    known_at: datetime
    quality: Literal["verified", "inferred", "synthetic"]


class EvidencePacket(Contract):
    evidence_packet_id: str = Field(min_length=1)
    as_of: date
    knowledge_cutoff: datetime
    expires_at: datetime
    items: tuple[EvidenceItem, ...] = Field(min_length=1)
    content_hash: str

    @field_validator("content_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _HASH_RE.fullmatch(value):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def validate_temporal_boundary(self) -> Self:
        if self.expires_at <= self.knowledge_cutoff:
            raise ValueError("expires_at must be later than knowledge_cutoff")
        late = [item.evidence_id for item in self.items if item.known_at > self.knowledge_cutoff]
        if late:
            raise ValueError(f"evidence known after the packet cutoff: {late}")
        if len({item.evidence_id for item in self.items}) != len(self.items):
            raise ValueError("evidence_id values must be unique within a packet")
        return self


class Scenario(Contract):
    label: Literal["bull", "base", "bear"]
    return_pct: Decimal
    probability_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    rationale: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ThesisVersion(Contract):
    thesis_version_id: str = Field(min_length=1)
    symbol: str = Field(pattern=r"^[A-Z0-9]+\.(AU|US)$")
    version: int = Field(ge=1)
    evidence_packet_id: str
    theme: str = Field(min_length=1)
    investment_question: str = Field(min_length=1)
    variant_view: str = Field(min_length=1)
    thesis_summary: str = Field(min_length=1)
    catalysts: tuple[str, ...] = Field(min_length=1)
    falsifiers: tuple[str, ...] = Field(min_length=1)
    horizon_months: int = Field(gt=0)
    scenarios: tuple[Scenario, Scenario, Scenario]
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenarios(self) -> Self:
        labels = {scenario.label for scenario in self.scenarios}
        if labels != {"bull", "base", "bear"}:
            raise ValueError("scenarios must contain exactly one bull, base, and bear case")
        probability = sum(
            (scenario.probability_pct for scenario in self.scenarios), start=Decimal("0")
        )
        if probability != Decimal("100"):
            raise ValueError("scenario probability_pct values must sum to exactly 100")
        return self


class ChallengeFinding(Contract):
    severity: Literal["blocking", "material", "monitor"]
    finding: str = Field(min_length=1)
    required_response: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()


class ChallengeResult(Contract):
    challenge_result_id: str = Field(min_length=1)
    thesis_version_id: str
    evidence_packet_id: str
    outcome: Literal["pass", "revise", "abstain"]
    strongest_bear_case: str = Field(min_length=1)
    findings: tuple[ChallengeFinding, ...]
    independent_of_author: bool

    @model_validator(mode="after")
    def validate_independence_and_outcome(self) -> Self:
        if not self.independent_of_author:
            raise ValueError("challenge must be independent of the thesis author")
        has_blocker = any(finding.severity == "blocking" for finding in self.findings)
        if has_blocker and self.outcome == "pass":
            raise ValueError("a challenge with a blocking finding cannot pass")
        return self


class ConstraintResult(Contract):
    name: str = Field(min_length=1)
    status: Literal["pass", "fail", "unknown"]
    detail: str = Field(min_length=1)


class SizeRange(Contract):
    minimum_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    maximum_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.minimum_pct > self.maximum_pct:
            raise ValueError("minimum_pct cannot exceed maximum_pct")
        return self


class PortfolioAssessment(Contract):
    portfolio_assessment_id: str = Field(min_length=1)
    portfolio_snapshot_id: str = Field(min_length=1)
    thesis_version_id: str
    assessment_state: RecommendationState
    size_range: SizeRange
    loss_budget_aud: Decimal = Field(ge=Decimal("0"))
    marginal_risk: str = Field(min_length=1)
    opportunity_cost: str = Field(min_length=1)
    constraints: tuple[ConstraintResult, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_failed_constraints(self) -> Self:
        has_failure = any(constraint.status == "fail" for constraint in self.constraints)
        if has_failure and self.assessment_state not in {"avoid", "abstain", "exit_review"}:
            raise ValueError("a failed portfolio constraint must block capital deployment")
        if self.assessment_state in {"avoid", "abstain"} and self.size_range.maximum_pct != 0:
            raise ValueError("avoid or abstain must carry a zero size range")
        return self


class DecisionPacket(Contract):
    decision_packet_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    as_of: date
    knowledge_cutoff: datetime
    expires_at: datetime
    portfolio_snapshot_id: str
    evidence_packet_id: str
    thesis_version_id: str
    challenge_result_id: str
    portfolio_assessment_id: str
    benchmark_id: str
    recommendation_state: RecommendationState
    size_range: SizeRange
    staging_framework: str = Field(min_length=1)
    scenario_summary: str = Field(min_length=1)
    risk_summary: str = Field(min_length=1)
    constraints_checked: tuple[str, ...] = Field(min_length=1)
    missing_or_uncertain_inputs: tuple[str, ...]
    decision_ask: str = Field(min_length=1)
    model_and_prompt_manifest: dict[str, str]
    content_hash: str
    created_at: datetime
    supersedes_packet_id: str | None = None

    @field_validator("content_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _HASH_RE.fullmatch(value):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def validate_decision_gate(self) -> Self:
        if self.expires_at <= self.knowledge_cutoff:
            raise ValueError("expires_at must be later than knowledge_cutoff")
        if self.missing_or_uncertain_inputs and self.recommendation_state not in {
            "watch",
            "avoid",
            "abstain",
            "exit_review",
        }:
            raise ValueError("unresolved inputs cannot produce a capital-deployment state")
        if self.recommendation_state in {"avoid", "abstain"} and self.size_range.maximum_pct != 0:
            raise ValueError("avoid or abstain must carry a zero size range")
        return self


class DecisionCase(Contract):
    case_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    changed_since_prior: str = Field(min_length=1)
    evidence: EvidencePacket
    thesis: ThesisVersion
    challenge: ChallengeResult
    portfolio: PortfolioAssessment
    decision: DecisionPacket

    @model_validator(mode="after")
    def validate_identity_chain(self) -> Self:
        if self.thesis.evidence_packet_id != self.evidence.evidence_packet_id:
            raise ValueError("thesis does not reference this evidence packet")
        if self.challenge.thesis_version_id != self.thesis.thesis_version_id:
            raise ValueError("challenge does not reference this thesis version")
        if self.challenge.evidence_packet_id != self.evidence.evidence_packet_id:
            raise ValueError("challenge does not use the frozen evidence packet")
        if self.portfolio.thesis_version_id != self.thesis.thesis_version_id:
            raise ValueError("portfolio assessment does not reference this thesis version")

        expected_links = {
            "portfolio_snapshot_id": self.portfolio.portfolio_snapshot_id,
            "evidence_packet_id": self.evidence.evidence_packet_id,
            "thesis_version_id": self.thesis.thesis_version_id,
            "challenge_result_id": self.challenge.challenge_result_id,
            "portfolio_assessment_id": self.portfolio.portfolio_assessment_id,
        }
        for field_name, expected in expected_links.items():
            if getattr(self.decision, field_name) != expected:
                raise ValueError(f"decision {field_name} does not resolve to its artifact")

        evidence_ids = {item.evidence_id for item in self.evidence.items}
        cited_ids = set(self.thesis.evidence_ids)
        cited_ids.update(
            evidence_id
            for scenario in self.thesis.scenarios
            for evidence_id in scenario.evidence_ids
        )
        cited_ids.update(
            evidence_id
            for finding in self.challenge.findings
            for evidence_id in finding.evidence_ids
        )
        missing_ids = cited_ids - evidence_ids
        if missing_ids:
            raise ValueError(
                f"case cites evidence outside the frozen packet: {sorted(missing_ids)}"
            )

        if self.challenge.outcome == "abstain" and self.decision.recommendation_state != "abstain":
            raise ValueError("an abstain challenge must force an abstain decision")
        if self.portfolio.assessment_state != self.decision.recommendation_state:
            raise ValueError("portfolio and decision recommendation states must agree")
        if self.portfolio.size_range != self.decision.size_range:
            raise ValueError("portfolio and decision size ranges must agree")
        return self


class ArchitectureStage(Contract):
    name: str
    status: Literal["reused", "demonstrated", "adapter_needed", "future"]
    detail: str


class DecisionBrief(Contract):
    title: str
    as_of: date
    mode: Literal["synthetic_prototype"] = "synthetic_prototype"
    disclaimer: str
    one_thing: str
    architecture_stages: tuple[ArchitectureStage, ...]
    cases: tuple[DecisionCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cases(self) -> Self:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("case_id values must be unique")
        if len({case.decision.content_hash for case in self.cases}) != len(self.cases):
            raise ValueError("decision packet hashes must be unique")
        return self


JsonObject = dict[str, Any]
