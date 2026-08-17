"""Canonical contracts for the research-to-decision target architecture.

The contracts are deliberately independent of databases, agents, and renderers.
They fail closed at the aggregate boundary: capital-action states require a
passed challenge, resolved blocking constraints, an admissible tax assessment,
Model A independence, one point-in-time cutoff, and verified content hashes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Literal, Self, assert_never, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

RecommendationState = Literal[
    "initiate", "watch", "avoid", "add", "trim", "exit_review", "abstain"
]
MemoVerdict = Literal["ADD", "TRIM", "EXIT-CANDIDATE", "REVIEW", "GOOD HOLD"]
EvidenceTier = Literal["verified", "inferred", "speculative"]
DataMode = Literal["real", "synthetic"]
ConstraintStatus = Literal["pass", "fail", "unknown"]
ExpiryReason = Literal[
    "default",
    "material_event",
    "stale_evidence",
    "constraint_change",
    "portfolio_snapshot_change",
]

ACTION_STATES: frozenset[RecommendationState] = frozenset(
    {"initiate", "add", "trim", "exit_review"}
)
NON_ACTION_STATES: frozenset[RecommendationState] = frozenset(
    {"watch", "avoid", "abstain"}
)
OUTCOME_WINDOWS_TRADING_DAYS: tuple[int, int, int] = (21, 63, 126)
UNIVERSAL_CONSTRAINTS: frozenset[str] = frozenset(
    {
        "no_leverage",
        "model_a_quarantine",
        "tradeability_and_ownership",
        "decision_evidence_freshness",
        "no_broker_execution",
    }
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_MODEL_A_RE = re.compile(
    r"(?:"
    r"(?<![A-Za-z0-9])model[ _-]?a(?=$|[^A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])v1[_.-]?5(?=$|[^A-Za-z0-9])"
    r")",
    re.IGNORECASE,
)
_DATETIME_ADAPTER = TypeAdapter(datetime)


def _contains_float(value: object) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, Mapping):
        return any(_contains_float(key) or _contains_float(item) for key, item in value.items())
    if isinstance(value, list | tuple | set | frozenset):
        return any(_contains_float(item) for item in value)
    return False


def require_utc(value: datetime, *, field_name: str = "datetime") -> datetime:
    """Return ``value`` only when it is timezone-aware and exactly UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must use UTC")
    return value.astimezone(UTC)


def memo_verdict_for(state: RecommendationState | None) -> MemoVerdict:
    """Map the canonical state to the sole permitted human-memo vocabulary."""
    match state:
        case None:
            return "GOOD HOLD"
        case "initiate" | "add":
            return "ADD"
        case "trim":
            return "TRIM"
        case "exit_review":
            return "EXIT-CANDIDATE"
        case "watch" | "avoid" | "abstain":
            return "REVIEW"
        case _ as unreachable:
            assert_never(unreachable)


def expiry_trading_days_for(state: RecommendationState) -> Literal[5, 21]:
    """Return the ratified F3 default horizon for a recommendation state."""
    match state:
        case "initiate" | "add" | "trim" | "exit_review":
            return 5
        case "watch" | "avoid" | "abstain":
            return 21
        case _ as unreachable:
            assert_never(unreachable)


def _canonical_digest(model: BaseModel) -> str:
    payload = model.model_dump(mode="json", exclude={"content_hash"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Contract(BaseModel):
    """Strict, deeply immutable boundary object with Decimal-only input."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
        revalidate_instances="always",
    )

    @model_validator(mode="before")
    @classmethod
    def reject_float_input(cls, value: object) -> object:
        if _contains_float(value):
            raise ValueError("float input is forbidden; use Decimal or a decimal string")
        return value

    @model_validator(mode="after")
    def validate_direct_datetimes_are_utc(self) -> Self:
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            if isinstance(value, datetime):
                require_utc(value, field_name=field_name)
        return self


class ContentAddressedContract(Contract):
    """A contract whose digest is computed when absent and verified when supplied."""

    content_hash: str = ""

    @model_validator(mode="after")
    def seal_or_verify_content_hash(self) -> Self:
        expected = _canonical_digest(self)
        if self.content_hash == "":
            object.__setattr__(self, "content_hash", expected)
            return self
        if not _HASH_RE.fullmatch(self.content_hash):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        if not hmac.compare_digest(self.content_hash, expected):
            raise ValueError("content_hash does not match canonical artifact content")
        return self


class TradingSessionCalendar(Contract):
    """Deterministic session input used to resolve F3 horizons.

    The horizon policy remains state-based, while an exchange-calendar adapter is
    responsible for supplying exact UTC session deadlines. Keeping those concerns
    separate prevents weekday arithmetic from being mislabeled as trading days and
    lets real calendars represent exchange holidays and daylight-saving changes.
    """

    calendar_id: str = Field(min_length=1, max_length=200)
    calendar_version: str = Field(min_length=1, max_length=200)
    sessions: tuple[datetime, ...] = Field(min_length=1, max_length=512)

    @field_validator("sessions")
    @classmethod
    def validate_sessions(cls, value: tuple[datetime, ...]) -> tuple[datetime, ...]:
        sessions = tuple(
            require_utc(session, field_name="trading session") for session in value
        )
        if any(current >= following for current, following in pairwise(sessions)):
            raise ValueError("trading sessions must be unique and strictly increasing")
        return sessions

    def resolve_expiry(self, cutoff: datetime, trading_sessions: int) -> datetime:
        cutoff = require_utc(cutoff, field_name="knowledge_cutoff")
        if trading_sessions <= 0:
            raise ValueError("trading_sessions must be positive")
        future_sessions = tuple(session for session in self.sessions if session > cutoff)
        if len(future_sessions) < trading_sessions:
            raise ValueError(
                f"trading calendar does not contain {trading_sessions} sessions after cutoff"
            )
        return future_sessions[trading_sessions - 1]


def default_packet_expiry(
    cutoff: datetime,
    state: RecommendationState,
    trading_calendar: TradingSessionCalendar,
) -> datetime:
    """Resolve the F3 horizon through an explicit deterministic session calendar."""
    return trading_calendar.resolve_expiry(cutoff, expiry_trading_days_for(state))


def verify_content_hash(model: ContentAddressedContract) -> bool:
    """Return whether an artifact still matches its canonical payload."""
    return bool(_HASH_RE.fullmatch(model.content_hash)) and hmac.compare_digest(
        model.content_hash, _canonical_digest(model)
    )


class EvidenceItem(Contract):
    evidence_id: str = Field(min_length=1, max_length=200)
    evidence_type: Literal[
        "market_fact", "fundamental_fact", "source_document", "theme_fact", "portfolio_fact"
    ]
    title: str = Field(min_length=1, max_length=500)
    claim: str = Field(min_length=1, max_length=10_000)
    source_uri: str = Field(min_length=1, max_length=2_000)
    observed_at: date
    known_at: datetime
    evidence_tier: EvidenceTier
    data_mode: DataMode

    @model_validator(mode="after")
    def validate_observation_precedes_knowledge(self) -> Self:
        if self.observed_at > self.known_at.date():
            raise ValueError("observed_at cannot be later than known_at")
        return self


class EvidencePacket(ContentAddressedContract):
    evidence_packet_id: str = Field(min_length=1, max_length=200)
    as_of: date
    knowledge_cutoff: datetime
    expires_at: datetime
    data_mode: DataMode
    created_at: datetime
    items: tuple[EvidenceItem, ...] = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def validate_temporal_and_provenance_boundary(self) -> Self:
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("evidence as_of must equal the UTC knowledge_cutoff date")
        if not self.knowledge_cutoff <= self.created_at < self.expires_at:
            raise ValueError("evidence created_at must be within cutoff and expiry")
        late = [item.evidence_id for item in self.items if item.known_at > self.knowledge_cutoff]
        if late:
            raise ValueError(f"evidence known after the packet cutoff: {late}")
        future = [item.evidence_id for item in self.items if item.observed_at > self.as_of]
        if future:
            raise ValueError(f"evidence observed after packet as_of: {future}")
        wrong_mode = [item.evidence_id for item in self.items if item.data_mode != self.data_mode]
        if wrong_mode:
            raise ValueError(f"evidence data_mode differs from packet: {wrong_mode}")
        if len({item.evidence_id for item in self.items}) != len(self.items):
            raise ValueError("evidence_id values must be unique within a packet")
        return self


class Scenario(Contract):
    label: Literal["bull", "base", "bear"]
    return_pct: Decimal = Field(max_digits=18, decimal_places=6)
    probability_pct: Decimal = Field(
        ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6
    )
    rationale: str = Field(min_length=1, max_length=5_000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=100)


class ThesisVersion(ContentAddressedContract):
    thesis_version_id: str = Field(min_length=1, max_length=200)
    security_id: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=100)
    exchange: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    evidence_packet_id: str = Field(min_length=1, max_length=200)
    as_of: date
    knowledge_cutoff: datetime
    created_at: datetime
    theme: str = Field(min_length=1, max_length=500)
    investment_question: str = Field(min_length=1, max_length=5_000)
    variant_view: str = Field(min_length=1, max_length=10_000)
    thesis_summary: str = Field(min_length=1, max_length=20_000)
    catalysts: tuple[str, ...] = Field(min_length=1, max_length=100)
    falsifiers: tuple[str, ...] = Field(min_length=1, max_length=100)
    horizon_months: int = Field(gt=0, le=120)
    scenarios: tuple[Scenario, Scenario, Scenario]
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def validate_scenarios_and_time(self) -> Self:
        labels = {scenario.label for scenario in self.scenarios}
        if labels != {"bull", "base", "bear"}:
            raise ValueError("scenarios must contain exactly one bull, base, and bear case")
        probability = sum(
            (scenario.probability_pct for scenario in self.scenarios), start=Decimal("0")
        )
        if probability != Decimal("100"):
            raise ValueError("scenario probability_pct values must sum to exactly 100")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("thesis as_of must equal the UTC knowledge_cutoff date")
        if self.created_at < self.knowledge_cutoff:
            raise ValueError("thesis cannot be created before its knowledge cutoff")
        return self


class ChallengeFinding(Contract):
    severity: Literal["blocking", "material", "monitor"]
    finding: str = Field(min_length=1, max_length=10_000)
    required_response: str = Field(min_length=1, max_length=10_000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=100)


class ChallengeResult(ContentAddressedContract):
    challenge_result_id: str = Field(min_length=1, max_length=200)
    thesis_version_id: str = Field(min_length=1, max_length=200)
    evidence_packet_id: str = Field(min_length=1, max_length=200)
    as_of: date
    knowledge_cutoff: datetime
    created_at: datetime
    outcome: Literal["pass", "revise", "abstain"]
    strongest_bear_case: str = Field(min_length=1, max_length=20_000)
    findings: tuple[ChallengeFinding, ...] = Field(max_length=100)
    independent_of_author: Literal[True]

    @model_validator(mode="after")
    def validate_independence_outcome_and_time(self) -> Self:
        has_blocker = any(finding.severity == "blocking" for finding in self.findings)
        if has_blocker and self.outcome == "pass":
            raise ValueError("a challenge with a blocking finding cannot pass")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("challenge as_of must equal the UTC knowledge_cutoff date")
        if self.created_at < self.knowledge_cutoff:
            raise ValueError("challenge cannot be created before its knowledge cutoff")
        return self


class ConstraintResult(Contract):
    name: str = Field(min_length=1, max_length=200)
    status: ConstraintStatus
    blocking: bool
    detail: str = Field(min_length=1, max_length=10_000)


class SizeRange(Contract):
    minimum_pct: Decimal = Field(
        ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6
    )
    maximum_pct: Decimal = Field(
        ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6
    )

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.minimum_pct > self.maximum_pct:
            raise ValueError("minimum_pct cannot exceed maximum_pct")
        return self


class PortfolioAssessment(ContentAddressedContract):
    portfolio_assessment_id: str = Field(min_length=1, max_length=200)
    portfolio_snapshot_id: str = Field(min_length=1, max_length=200)
    thesis_version_id: str = Field(min_length=1, max_length=200)
    as_of: date
    knowledge_cutoff: datetime
    created_at: datetime
    assessment_state: RecommendationState
    size_range: SizeRange
    loss_budget_aud: Decimal = Field(
        ge=Decimal("0"), max_digits=18, decimal_places=6
    )
    marginal_risk: str = Field(min_length=1, max_length=10_000)
    opportunity_cost: str = Field(min_length=1, max_length=10_000)
    constraints: tuple[ConstraintResult, ...] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_constraints_state_and_time(self) -> Self:
        names = tuple(constraint.name for constraint in self.constraints)
        if len(set(names)) != len(names):
            raise ValueError("portfolio constraint names must be unique")
        unresolved_blocking = any(
            constraint.blocking and constraint.status != "pass"
            for constraint in self.constraints
        )
        if unresolved_blocking and self.assessment_state in ACTION_STATES:
            raise ValueError("a failed or unknown blocking constraint must block action states")
        if self.assessment_state in NON_ACTION_STATES:
            if self.size_range.maximum_pct != 0:
                raise ValueError("non-action states must carry a zero size range")
            if self.loss_budget_aud != 0:
                raise ValueError("non-action states must carry a zero loss budget")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("portfolio as_of must equal the UTC knowledge_cutoff date")
        if self.created_at < self.knowledge_cutoff:
            raise ValueError("portfolio assessment cannot predate its knowledge cutoff")
        return self


class TaxAssessmentReference(ContentAddressedContract):
    """Typed identity and readiness state for a separately governed tax artifact."""

    tax_assessment_id: str = Field(min_length=1, max_length=200)
    as_of: date
    knowledge_cutoff: datetime
    created_at: datetime
    applicability: Literal["applicable", "not_applicable", "uncertain"]
    readiness: Literal["pass", "fail", "unknown"]

    @model_validator(mode="after")
    def validate_tax_reference(self) -> Self:
        if self.applicability == "uncertain" and self.readiness == "pass":
            raise ValueError("uncertain tax applicability cannot pass readiness")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("tax as_of must equal the UTC knowledge_cutoff date")
        if self.created_at < self.knowledge_cutoff:
            raise ValueError("tax assessment reference cannot predate its knowledge cutoff")
        return self


class ManifestEntry(Contract):
    component: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=500)


class UpstreamArtifactHashes(Contract):
    evidence_packet: str
    thesis_version: str
    challenge_result: str
    portfolio_assessment: str
    tax_assessment_reference: str

    @field_validator("*")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _HASH_RE.fullmatch(value):
            raise ValueError("upstream hash must be a lowercase SHA-256 digest")
        return value


class DecisionPacket(ContentAddressedContract):
    decision_packet_id: str = Field(min_length=1, max_length=200)
    schema_version: str = Field(min_length=1, max_length=100)
    as_of: date
    knowledge_cutoff: datetime
    recommendation_state: RecommendationState
    trading_calendar: TradingSessionCalendar
    expires_at: datetime
    expiry_reason: ExpiryReason = "default"
    portfolio_snapshot_id: str = Field(min_length=1, max_length=200)
    evidence_packet_id: str = Field(min_length=1, max_length=200)
    thesis_version_id: str = Field(min_length=1, max_length=200)
    challenge_result_id: str = Field(min_length=1, max_length=200)
    portfolio_assessment_id: str = Field(min_length=1, max_length=200)
    upstream_hashes: UpstreamArtifactHashes
    benchmark_id: str = Field(min_length=1, max_length=200)
    size_range: SizeRange
    staging_framework: str = Field(min_length=1, max_length=10_000)
    scenario_summary: str = Field(min_length=1, max_length=10_000)
    risk_summary: str = Field(min_length=1, max_length=10_000)
    constraints_checked: tuple[str, ...] = Field(min_length=1, max_length=200)
    missing_or_uncertain_inputs: tuple[str, ...] = Field(max_length=200)
    decision_ask: str = Field(min_length=1, max_length=10_000)
    model_independence: Literal[True]
    model_and_prompt_manifest: tuple[ManifestEntry, ...] = Field(min_length=1, max_length=100)
    tax_assessment_reference: TaxAssessmentReference
    created_at: datetime
    supersedes_packet_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="before")
    @classmethod
    def apply_f3_default_expiry(cls, value: object) -> object:
        if not isinstance(value, Mapping) or value.get("expires_at") is not None:
            return value
        cutoff_raw = value.get("knowledge_cutoff")
        state = value.get("recommendation_state")
        calendar_raw = value.get("trading_calendar")
        if (
            cutoff_raw is None
            or calendar_raw is None
            or not isinstance(state, str)
            or state not in ACTION_STATES | NON_ACTION_STATES
        ):
            return value
        cutoff = _DATETIME_ADAPTER.validate_python(cutoff_raw)
        calendar = TradingSessionCalendar.model_validate(calendar_raw)
        updated = dict(value)
        updated["expires_at"] = default_packet_expiry(
            cutoff, cast(RecommendationState, state), calendar
        )
        return updated

    @model_validator(mode="after")
    def validate_decision_gate(self) -> Self:
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("decision as_of must equal the UTC knowledge_cutoff date")
        if not self.knowledge_cutoff <= self.created_at < self.expires_at:
            raise ValueError("decision created_at must be within cutoff and expiry")
        default_expiry = default_packet_expiry(
            self.knowledge_cutoff, self.recommendation_state, self.trading_calendar
        )
        if self.expiry_reason == "default" and self.expires_at != default_expiry:
            raise ValueError("default expires_at must equal the F3 trading-day expiry")
        if self.expiry_reason != "default" and self.expires_at >= default_expiry:
            raise ValueError("event-driven expiry must be strictly earlier than the F3 default")
        if self.missing_or_uncertain_inputs and self.recommendation_state in ACTION_STATES:
            raise ValueError("unresolved inputs cannot produce an action state")
        if self.recommendation_state in NON_ACTION_STATES and self.size_range.maximum_pct != 0:
            raise ValueError("non-action states must carry a zero size range")
        if (
            self.tax_assessment_reference.readiness != "pass"
            and self.recommendation_state in ACTION_STATES
        ):
            raise ValueError("unresolved tax readiness cannot produce an action state")

        components = tuple(entry.component for entry in self.model_and_prompt_manifest)
        if len(set(components)) != len(components):
            raise ValueError("model and prompt manifest components must be unique")
        required = {"composition", "llm", "market_data", "code_contract"}
        if not required.issubset(components):
            raise ValueError(f"model and prompt manifest is missing: {sorted(required-set(components))}")
        manifest_text = " ".join(
            f"{entry.component} {entry.version}" for entry in self.model_and_prompt_manifest
        )
        if _MODEL_A_RE.search(manifest_text):
            raise ValueError("Model A and v1_5 are quarantined from the decision basis")
        return self

    @property
    def memo_verdict(self) -> MemoVerdict:
        return memo_verdict_for(self.recommendation_state)

    def is_expired_at(self, evaluated_at: datetime) -> bool:
        evaluated_at = require_utc(evaluated_at, field_name="evaluated_at")
        return evaluated_at >= self.expires_at

    def is_actionable_at(self, evaluated_at: datetime) -> bool:
        return (
            self.recommendation_state in ACTION_STATES
            and not self.is_expired_at(evaluated_at)
        )


class DecisionCase(Contract):
    case_id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=500)
    changed_since_prior: str = Field(min_length=1, max_length=10_000)
    evidence: EvidencePacket
    thesis: ThesisVersion
    challenge: ChallengeResult
    portfolio: PortfolioAssessment
    decision: DecisionPacket

    @model_validator(mode="after")
    def validate_identity_integrity_and_gate_chain(self) -> Self:
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

        expected_hashes = UpstreamArtifactHashes(
            evidence_packet=self.evidence.content_hash,
            thesis_version=self.thesis.content_hash,
            challenge_result=self.challenge.content_hash,
            portfolio_assessment=self.portfolio.content_hash,
            tax_assessment_reference=self.decision.tax_assessment_reference.content_hash,
        )
        if self.decision.upstream_hashes != expected_hashes:
            raise ValueError("decision upstream hashes do not match canonical artifact contents")
        artifacts: tuple[ContentAddressedContract, ...] = (
            self.evidence,
            self.thesis,
            self.challenge,
            self.portfolio,
            self.decision.tax_assessment_reference,
            self.decision,
        )
        if not all(verify_content_hash(artifact) for artifact in artifacts):
            raise ValueError("case contains an artifact with invalid content integrity")

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

        has_blocker = any(finding.severity == "blocking" for finding in self.challenge.findings)
        if has_blocker and self.decision.recommendation_state != "abstain":
            raise ValueError("a blocking challenge finding must force an abstain decision")
        if self.challenge.outcome == "abstain" and self.decision.recommendation_state != "abstain":
            raise ValueError("an abstain challenge must force an abstain decision")
        if self.challenge.outcome == "revise" and self.decision.recommendation_state in ACTION_STATES:
            raise ValueError("a revise challenge cannot accompany an action state")
        if self.portfolio.assessment_state != self.decision.recommendation_state:
            raise ValueError("portfolio and decision recommendation states must agree")
        if self.portfolio.size_range != self.decision.size_range:
            raise ValueError("portfolio and decision size ranges must agree")

        portfolio_constraints = tuple(item.name for item in self.portfolio.constraints)
        if self.decision.constraints_checked != portfolio_constraints:
            raise ValueError("decision constraints_checked must exactly match portfolio constraints")
        model_a_gate = [
            item for item in self.portfolio.constraints if item.name == "model_a_quarantine"
        ]
        if len(model_a_gate) != 1 or not model_a_gate[0].blocking or model_a_gate[0].status != "pass":
            raise ValueError("the blocking Model A quarantine constraint must pass exactly once")
        constraint_by_name = {item.name: item for item in self.portfolio.constraints}
        missing_universal = UNIVERSAL_CONSTRAINTS - constraint_by_name.keys()
        if missing_universal:
            raise ValueError(f"case is missing universal constraints: {sorted(missing_universal)}")
        nonblocking_universal = [
            name for name in UNIVERSAL_CONSTRAINTS if not constraint_by_name[name].blocking
        ]
        if nonblocking_universal:
            raise ValueError(
                f"universal constraints must be blocking: {sorted(nonblocking_universal)}"
            )

        temporal_artifacts = (
            self.thesis,
            self.challenge,
            self.portfolio,
            self.decision.tax_assessment_reference,
            self.decision,
        )
        for artifact in temporal_artifacts:
            if artifact.as_of != self.evidence.as_of:
                raise ValueError("all case artifacts must share the evidence as_of")
            if artifact.knowledge_cutoff != self.evidence.knowledge_cutoff:
                raise ValueError("all case artifacts must share the evidence knowledge_cutoff")
            if not self.evidence.knowledge_cutoff <= artifact.created_at < self.evidence.expires_at:
                raise ValueError("artifact created_at must be within evidence cutoff and expiry")
        created_chain = (
            self.evidence.created_at,
            self.thesis.created_at,
            self.challenge.created_at,
            self.portfolio.created_at,
            self.decision.tax_assessment_reference.created_at,
            self.decision.created_at,
        )
        if created_chain != tuple(sorted(created_chain)):
            raise ValueError("case artifacts must be created in decision-chain order")
        if self.decision.expires_at > self.evidence.expires_at:
            raise ValueError("decision cannot outlive its frozen evidence packet")
        return self


class ArchitectureStage(Contract):
    name: str = Field(min_length=1, max_length=200)
    status: Literal["reused", "demonstrated", "adapter_needed", "future"]
    detail: str = Field(min_length=1, max_length=2_000)


class DecisionBrief(Contract):
    title: str = Field(min_length=1, max_length=500)
    as_of: date
    mode: Literal["synthetic_prototype"] = "synthetic_prototype"
    disclaimer: str = Field(min_length=1, max_length=5_000)
    one_thing: str = Field(min_length=1, max_length=5_000)
    architecture_stages: tuple[ArchitectureStage, ...] = Field(max_length=50)
    cases: tuple[DecisionCase, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_synthetic_cases(self) -> Self:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("case_id values must be unique")
        if len({case.decision.decision_packet_id for case in self.cases}) != len(self.cases):
            raise ValueError("decision_packet_id values must be unique")
        if len({case.decision.content_hash for case in self.cases}) != len(self.cases):
            raise ValueError("decision packet hashes must be unique")
        if any(case.evidence.data_mode != "synthetic" for case in self.cases):
            raise ValueError("a synthetic prototype brief may contain only synthetic evidence")
        if any(case.evidence.as_of != self.as_of for case in self.cases):
            raise ValueError("every case must share the brief as_of")
        return self
