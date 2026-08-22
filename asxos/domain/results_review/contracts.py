"""Frozen results-review contracts — mission P2-02, the eight §8 freeze items.

Work order: `docs/product/finance-capability-matrix-2026-08-13.md` §8
(items 1-8). Every model and constant here is a FREEZE decision, each recorded
with its citation in `docs/product/results-review-contracts-2026-08-16.md`.

Relationship to the canonical decision contracts
(`asxos/domain/decision_engine/types.py`, executable canonical per
`target-architecture.md` B.2/B.4): this module builds BESIDE them and never
modifies them. Canonical objects are reused by projection (§3.1 path 1 of the
2026-08-12 execution plan): `Contract` / `ContentAddressedContract` bases,
`DataMode`, `EvidencePacket`/`EvidenceItem`, `TaxAssessmentReference`,
`verify_content_hash`. The new models here take §3.1 path 3 — the plan itself
authorizes them: *"The results path may introduce a `ResultsReviewArtifact`,
but it is an analysis input to a `ThesisVersion`; it is not a second decision
packet and does not mutate a thesis by itself"* (plan :180-181). Accordingly a
`ResultsReviewArtifact` has NO recommendation state, NO verdict, NO sizing,
NO rating and NO price target — its only outcome vocabulary is the plan's own
`complete | revise | abstain` (plan :303), which is neither the B.3 memo
vocabulary nor the P1-04 review-state vocabulary (different altitudes, B.6).

Recommendation generation is disabled pending Australian legal review. Nothing
in this package emits ratings, price targets, portfolio instructions, or
thesis mutations; `Contract`'s `extra="forbid"` makes smuggled fields fail
loudly. Abstention is a valid, successful outcome (matrix :366-368).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_EVEN, Decimal
from types import MappingProxyType
from typing import Annotated, Final, Literal, Self

from pydantic import AfterValidator, Field, model_validator

from asxos.domain.decision_engine.types import (
    ContentAddressedContract,
    Contract,
    DataMode,
    EvidencePacket,
    TaxAssessmentReference,
    verify_content_hash,
)
from asxos.ingestion.financial_statements import derive_knowledge_date

RESULTS_REVIEW_SCHEMA_VERSION: Final[str] = "results-review-contracts-1.0"

# ---------------------------------------------------------------------------
# §8 item 1 — the document-acquisition ruling (G2, matrix :427-430)
# ---------------------------------------------------------------------------
# RULED 2026-08-16: hashed fixture only. Widened 2026-08-22 (W1-1, James
# authorized the freeze exception by executing this chain after the 2026-08-22
# red-team). `asxos_pit_db` is a hashed research-store snapshot — not an ASX
# announcement feed. G2 stays closed. Never relabel a fixture as `asxos_pit_db`.
AcquisitionPath = Literal["hashed_fixture", "asxos_pit_db"]

# The frozen integrity algorithm for the document payload (matrix :429).
DOCUMENT_HASH_ALGORITHM: Final[Literal["sha256"]] = "sha256"

_HASH_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_CURRENCY_RE: Final[str] = r"^[A-Z]{3}$"

# ---------------------------------------------------------------------------
# §8 item 2 — the source hierarchy, verbatim and ranked (matrix :431-435;
# plan :290-292)
# ---------------------------------------------------------------------------
SourceClass = Literal[
    "asx_announcement",
    "audited_statements",
    "issuer_presentation",
    "results_transcript",
    "asxos_pit_record",
    "licensed_consensus",
    "news",
]

#: Plan :290-292 verbatim ranking: "ASX announcement and audited statements
#: first; issuer presentation second; complete transcript where lawfully
#: available; reconciled ASXOS PIT records; licensed consensus only when
#: provenance and rights are explicit; news is contextual and never
#: load-bearing."
SOURCE_RANK: Final[Mapping[SourceClass, int]] = MappingProxyType(
    {
        "asx_announcement": 1,
        "audited_statements": 1,
        "issuer_presentation": 2,
        "results_transcript": 3,
        "asxos_pit_record": 4,
        "licensed_consensus": 5,
        "news": 6,
    }
)

#: `licensed_consensus` is frozen OUT OF SCOPE for this slice — there is no
#: licensed consensus feed and `rs_estimates` is explicitly excluded
#: (matrix :434-435, B5.6). It stays in the ranked hierarchy verbatim but is
#: not admissible until a feed with explicit provenance and rights exists.
ADMISSIBLE_SOURCE_CLASSES: Final[frozenset[SourceClass]] = frozenset(
    {
        "asx_announcement",
        "audited_statements",
        "issuer_presentation",
        "results_transcript",
        "asxos_pit_record",
        "news",
    }
)

#: News is contextual and never load-bearing (plan :292): no numeric claim,
#: adjustment, delta, or guidance change may rest on it.
LOAD_BEARING_SOURCE_CLASSES: Final[frozenset[SourceClass]] = frozenset(
    {
        "asx_announcement",
        "audited_statements",
        "issuer_presentation",
        "results_transcript",
        "asxos_pit_record",
    }
)


def _require_load_bearing(value: SourceClass) -> SourceClass:
    if value not in LOAD_BEARING_SOURCE_CLASSES:
        raise ValueError(
            f"source class {value!r} is not load-bearing "
            "(news is contextual; licensed consensus is out of scope)"
        )
    return value


#: The source class of any numeric or guidance claim: must be load-bearing.
LoadBearingSourceClass = Annotated[SourceClass, AfterValidator(_require_load_bearing)]


def _require_sha256_hex(value: str) -> str:
    if not _HASH_RE.fullmatch(value):
        raise ValueError("document_sha256 must be a lowercase SHA-256 digest")
    return value


Sha256Hex = Annotated[str, AfterValidator(_require_sha256_hex)]

# Units/scale discipline (G4, matrix :348): every monetary figure carries an
# explicit currency AND an explicit presentation scale. The research store has
# no scale column today — the contract freezes the rule ahead of any schema.
UnitScale = Literal["ones", "thousands", "millions", "billions"]

PeriodType = Literal["yearly", "half_yearly", "quarterly"]
DocumentKind = Literal["full_year_results", "half_year_results", "quarterly_report"]

_KIND_TO_PERIOD: Final[Mapping[DocumentKind, PeriodType]] = MappingProxyType(
    {
        "full_year_results": "yearly",
        "half_year_results": "half_yearly",
        "quarterly_report": "quarterly",
    }
)

# ---------------------------------------------------------------------------
# §7 A3 discharge — the canonical security identity (matrix :407-414)
# ---------------------------------------------------------------------------
#: Verified against the actual DDL (`migrations/0027_research_store.sql:34-48`):
#: `rs_security_master.symbol` (`TEXT PRIMARY KEY`, vendor-namespaced, e.g.
#: `CBA.AU`) is the table's ONLY unique NOT NULL identity — `isin` is nullable
#: and carries no UNIQUE constraint, so it cannot serve as identity today.
#: `security_id` on every contract in this package and on the canonical
#: `ThesisVersion` binds to this column's value verbatim. `symbol`/`exchange`
#: fields remain display attributes only (target-architecture.md B.3
#: amendment 1). Moving identity to ISIN or a surrogate key requires both a
#: migration and a governor amendment — deferred by name
#: (`p2_deferred_security_id_column_migration`).
SECURITY_ID_BINDING: Final[str] = "rs_security_master.symbol"

# ---------------------------------------------------------------------------
# §8 item 6 — the trading-calendar source ruling (G6, matrix :446-448)
# ---------------------------------------------------------------------------
#: RULED: a real packet's `TradingSessionCalendar` derives from the repo's own
#: point-in-time price store — the distinct `prices.dt` values observed across
#: ASX-quoted symbols. A session is a day the ASX equity market demonstrably
#: traded, evidenced by the same store the review's evidence comes from. No
#: new dependency is introduced by this ruling (an `exchange_calendars`-style
#: library would need a `tech-stack-researcher` consult and is not required
#: for a historical review). NOT implemented here — implementation is P2-03+.
TRADING_CALENDAR_SOURCE: Final[Literal["asxos_prices_observed_sessions"]] = (
    "asxos_prices_observed_sessions"
)

#: Versioning convention (types.py:172-173 fields): `calendar_id` =
#: `TRADING_CALENDAR_ID_PREFIX`; `calendar_version` = the ISO date of the
#: latest session included plus the first 12 hex chars of the SHA-256 over the
#: ISO-8601 session list, e.g. `2026-08-14+3f9a0c1d2e4b`.
TRADING_CALENDAR_ID_PREFIX: Final[str] = "asx-observed-prices"

#: Each observed session date maps to the ASX cash-market close, 16:00
#: Australia/Sydney, expressed in UTC via zoneinfo (AEST/AEDT-aware).
TRADING_SESSION_CLOSE_LOCAL: Final[str] = "16:00 Australia/Sydney"

# Shortfall rule (frozen): when the calendar runs short of sessions after a
# historical cutoff, `TradingSessionCalendar.resolve_expiry` already raises
# (types.py:190-194) and that hard-fail STANDS — no weekday padding, no
# graceful fallback (CLAUDE.md non-negotiable #10). This source cannot see
# FUTURE sessions, so a live-cutoff packet needs a forward-looking calendar
# source — deferred by name (`p2_deferred_forward_trading_calendar_source`).

# ---------------------------------------------------------------------------
# §8 item 7 — the TaxAssessmentReference producer contract (G7 + G12,
# matrix :449-455)
# ---------------------------------------------------------------------------
#: The eventual producers of a `readiness="pass"` reference — B6.2's
#: `tax_view_*` aggregator is the only sane candidate (matrix :450-451).
TAX_ASSESSMENT_PRODUCERS: Final[tuple[str, str]] = (
    "asxos.domain.tax.positions.tax_view_individual",
    "asxos.domain.tax.positions.tax_view_smsf",
)

#: FROZEN DEFAULT: `unknown`, not `pass`. The tax aggregator has never been
#: fed real dividends or realised gains (`asxos/cli/tax.py:93,99` hardcodes
#: empty inputs — G12), so `pass` would be an unearned assertion. UNKNOWN is a
#: valid, successful outcome, not a failure (matrix :454-455); the canonical
#: contract makes non-pass readiness mechanically forbid every action state
#: (types.py:512-516).
DEFAULT_TAX_READINESS: Final[Literal["unknown"]] = "unknown"


def unresolved_tax_assessment_reference(
    *,
    tax_assessment_id: str,
    as_of: date,
    knowledge_cutoff: datetime,
    created_at: datetime,
) -> TaxAssessmentReference:
    """Build the only tax reference this package can produce: an unresolved one.

    Projection of the canonical `TaxAssessmentReference` (§3.1 path 1). This
    package deliberately offers NO constructor for `readiness="pass"` — a pass
    can only come from the named producers in `TAX_ASSESSMENT_PRODUCERS`, fed
    with real dividend and realised-gain inputs, in a later work order.
    """
    return TaxAssessmentReference(
        tax_assessment_id=tax_assessment_id,
        as_of=as_of,
        knowledge_cutoff=knowledge_cutoff,
        created_at=created_at,
        applicability="uncertain",
        readiness=DEFAULT_TAX_READINESS,
    )


# ---------------------------------------------------------------------------
# §8 item 4 — the `known_at` derivation rule (G8, matrix :440-442)
# ---------------------------------------------------------------------------
#: Conservative end-of-day convention: a vendor-dated statement becomes
#: known at 23:59:59 UTC on its guarded knowledge date, so it is only
#: admissible under `known_at <= knowledge_cutoff` (types.py:249-251) at a
#: cutoff at or after the end of that day. The convention errs toward
#: EXCLUDING same-day evidence rather than admitting it.
STATEMENT_KNOWN_AT_UTC_TIME: Final[time] = time(23, 59, 59)


def derive_statement_known_at(
    period_end: date,
    report_date: date | None,
    filing_date: date | None,
    as_of: date,
) -> datetime:
    """Derive `EvidenceItem.known_at` for a vendor-dated statement row.

    FROZEN two-branch rule (G8 — `filing_date` is not a release timestamp):

    1. Evidence sourced from the results DOCUMENT itself uses the document's
       verified `release_at` timestamp (`SourceDocumentRecord.release_at`) —
       never `filing_date`, never `report_date`.
    2. Evidence sourced from a vendor-dated statement row (`rs_*`) uses the
       probe-validated PIT guard `derive_knowledge_date()`
       (`asxos/ingestion/financial_statements.py:56-84`, reused here as the
       single source of truth, default lag 75 days) at the conservative
       end-of-day UTC instant above. The guard drops disclosure dates that
       defaulted to `period_end` and scheduled future dates, exactly as the
       research store's header rule requires (migration 0027 header).
    """
    knowledge_date = derive_knowledge_date(period_end, report_date, filing_date, as_of)
    return datetime.combine(knowledge_date, STATEMENT_KNOWN_AT_UTC_TIME, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Document payload hashing (§8 item 1)
# ---------------------------------------------------------------------------


def _reject_floats(value: object) -> None:
    if isinstance(value, float):
        raise ValueError(
            "float is forbidden in a document payload; encode figures as decimal strings"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_floats(key)
            _reject_floats(item)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            _reject_floats(item)


def hash_document_payload(payload: Mapping[str, object]) -> str:
    """SHA-256 over the canonical JSON form of a JSON-native document payload.

    The payload must be JSON-native (str/int/bool/None/mapping/sequence) with
    every numeric figure encoded as a decimal STRING — floats are rejected and
    non-JSON types (including Decimal objects) fail loudly. Canonical form:
    sorted keys, compact separators, ASCII-escaped — the same canonicalization
    the decision engine uses for content hashes.
    """
    _reject_floats(payload)
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise ValueError(
            "document payload must be JSON-native; encode figures as decimal strings"
        ) from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Deterministic delta arithmetic (plan required-work item 2)
# ---------------------------------------------------------------------------
DELTA_PCT_QUANT: Final[Decimal] = Decimal("0.000001")


def frozen_delta_pct(current: Decimal, prior: Decimal) -> Decimal:
    """The frozen period-on-period percentage-change rule.

    `((current - prior) / prior) * 100`, quantized to six decimal places with
    banker's rounding (ROUND_HALF_EVEN). Undefined for a zero prior — callers
    must carry `delta_pct=None` in that case rather than inventing a number.
    """
    if prior == 0:
        raise ValueError("delta_pct is undefined for a zero prior; carry None instead")
    return ((current - prior) / prior * Decimal("100")).quantize(
        DELTA_PCT_QUANT, rounding=ROUND_HALF_EVEN
    )


# ---------------------------------------------------------------------------
# §8 items 1 + 3 — the frozen document record and input tuple
# ---------------------------------------------------------------------------


class SourceDocumentRecord(ContentAddressedContract):
    """The frozen identity of the reviewed results document.

    Two hash layers, deliberately distinct: `document_sha256` pins the raw
    document PAYLOAD (via `hash_document_payload`); the inherited
    `content_hash` pins this RECORD. `release_at` is the verified (for a
    fixture: declared) release timestamp — it is never `filing_date` and never
    `report_date` (G8). A fixture never reproduces ASX-copyrighted
    announcement text: figures are synthetic or hand-transcribed, and
    `transcription_note` states which.
    """

    document_id: str = Field(min_length=1, max_length=200)
    acquisition: AcquisitionPath
    data_mode: DataMode
    security_id: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=100)
    exchange: str = Field(min_length=1, max_length=100)
    document_kind: DocumentKind
    period_end: date
    period_type: PeriodType
    currency: str = Field(pattern=_CURRENCY_RE)
    units_scale: UnitScale
    release_at: datetime
    document_sha256: Sha256Hex
    hash_algorithm: Literal["sha256"] = DOCUMENT_HASH_ALGORITHM
    transcription_note: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_fixture_never_real(self) -> Self:
        # §8 item 1: a fixture can NEVER be labelled data_mode="real".
        # `asxos_pit_db` is the authorized real path (W1-1); it is not G2.
        if self.acquisition == "hashed_fixture" and self.data_mode == "real":
            raise ValueError(
                "a hashed fixture can never carry data_mode='real'; "
                "real data requires a real acquisition path (G2)"
            )
        if _KIND_TO_PERIOD[self.document_kind] != self.period_type:
            raise ValueError(
                f"document_kind {self.document_kind!r} does not match "
                f"period_type {self.period_type!r}"
            )
        return self


class FrozenInputTuple(ContentAddressedContract):
    """§8 item 3 — the eight frozen input elements of one results review.

    Document identity + hash · `security_id` (§7 A3: the
    `rs_security_master.symbol` value) · reporting period · `period_type` ·
    currency · units/scale (G4) · `knowledge_cutoff` · the ASXOS evidence
    snapshot identity (matrix :436-439). Exactly these eight; nothing else.
    """

    document_id: str = Field(min_length=1, max_length=200)
    document_sha256: Sha256Hex
    security_id: str = Field(min_length=1, max_length=200)
    period_end: date
    period_type: PeriodType
    currency: str = Field(pattern=_CURRENCY_RE)
    units_scale: UnitScale
    knowledge_cutoff: datetime
    evidence_packet_id: str = Field(min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# §8 item 5 — statutory/underlying separation, in the schema (G3,
# matrix :443-445)
# ---------------------------------------------------------------------------


class MetricAdjustment(Contract):
    """One statutory→underlying adjustment.

    FROZEN RULE (G3): every adjustment carries an explanation AND an evidence
    citation — both are mandatory non-empty fields, so an unexplained or
    uncited adjustment is unrepresentable. Its source must be load-bearing
    (news never is; licensed consensus is out of scope)."""

    label: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(max_digits=18, decimal_places=6)
    explanation: str = Field(min_length=1, max_length=5_000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=100)
    source_class: LoadBearingSourceClass


class StatutoryUnderlyingBridge(Contract):
    """A statutory figure, its underlying counterpart, and the exact bridge.

    The separation is encoded in the schema, not just prose (§8 item 5): the
    two bases are distinct fields and the adjustments must reconcile them to
    the cent — `statutory + sum(adjustments) == underlying`, exact Decimal
    equality, no tolerance."""

    metric: str = Field(min_length=1, max_length=200)
    currency: str = Field(pattern=_CURRENCY_RE)
    scale: UnitScale
    statutory: Decimal = Field(max_digits=18, decimal_places=6)
    underlying: Decimal = Field(max_digits=18, decimal_places=6)
    adjustments: tuple[MetricAdjustment, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def validate_bridge_reconciles(self) -> Self:
        bridged = self.statutory + sum(
            (adjustment.amount for adjustment in self.adjustments), start=Decimal("0")
        )
        if bridged != self.underlying:
            raise ValueError(
                f"bridge does not reconcile: statutory {self.statutory} + adjustments "
                f"{bridged - self.statutory} != underlying {self.underlying}"
            )
        return self


class MetricDelta(Contract):
    """A period-on-period metric movement on one explicit basis.

    `basis` keeps the statutory/underlying separation at the delta level too;
    `currency` and `scale` apply to both values (G4 unit discipline — a delta
    across mixed currencies or scales is unrepresentable). `delta_pct` must
    equal `frozen_delta_pct(current_value, prior_value)` exactly, and must be
    None when there is no prior or the prior is zero."""

    metric: str = Field(min_length=1, max_length=200)
    basis: Literal["statutory", "underlying"]
    currency: str = Field(pattern=_CURRENCY_RE)
    scale: UnitScale
    current_value: Decimal = Field(max_digits=18, decimal_places=6)
    prior_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    delta_pct: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=100)
    source_class: LoadBearingSourceClass

    @model_validator(mode="after")
    def validate_delta_arithmetic(self) -> Self:
        if self.prior_value is None or self.prior_value == 0:
            if self.delta_pct is not None:
                raise ValueError("delta_pct must be None without a usable non-zero prior")
            return self
        expected = frozen_delta_pct(self.current_value, self.prior_value)
        if self.delta_pct != expected:
            raise ValueError(
                f"delta_pct {self.delta_pct} does not equal the frozen computation {expected}"
            )
        return self


class GuidanceChange(Contract):
    """A guidance statement and its change against any recorded prior.

    `prior` is None when no prior guidance is recorded — the repo has no
    guidance store (G5), so an absent prior is an explicit unknown, never an
    implied 'unchanged'."""

    metric: str = Field(min_length=1, max_length=200)
    prior: str | None = Field(default=None, max_length=2_000)
    current: str = Field(min_length=1, max_length=2_000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=100)
    source_class: LoadBearingSourceClass


class CitedStatement(Contract):
    """A qualitative claim that must cite frozen evidence (no unanchored prose)."""

    statement: str = Field(min_length=1, max_length=5_000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=100)


class EvidenceConflict(Contract):
    """An explicit conflict between at least two evidence sources.

    An unresolved conflict (resolution None) mechanically forbids a
    `complete` outcome on the artifact."""

    description: str = Field(min_length=1, max_length=5_000)
    evidence_ids: tuple[str, ...] = Field(min_length=2, max_length=100)
    resolution: str | None = Field(default=None, max_length=5_000)


# ---------------------------------------------------------------------------
# The review artifact and its case binder
# ---------------------------------------------------------------------------

#: Plan :303 verbatim: "Return `complete`, `revise`, or `abstain`; do not
#: return a rating, price target, trade, or position-size instruction."
ResultsReviewOutcome = Literal["complete", "revise", "abstain"]


class ResultsReviewArtifact(ContentAddressedContract):
    """The frozen shape of one results review — analysis, never a decision.

    Not a second decision packet (plan :180-181): no recommendation state, no
    verdict, no sizing, and no vocabulary shared with either the B.3 memo map
    or the P1-04 review states (B.6: different altitudes). Action gating stays
    where the canonical contract already enforces it — a non-pass tax
    readiness or unresolved inputs block action states in `DecisionPacket`
    (types.py:508-516), not here.

    Frozen outcome gates:
    - `missing_evidence` non-empty forces `abstain` — incomplete evidence
      must force abstention (plan :308; matrix :456-457).
    - any unresolved conflict forbids `complete`.
    """

    review_id: str = Field(min_length=1, max_length=200)
    schema_version: str = Field(min_length=1, max_length=100)
    frozen_input: FrozenInputTuple
    as_of: date
    created_at: datetime
    data_mode: DataMode
    metric_deltas: tuple[MetricDelta, ...] = Field(max_length=200)
    statutory_underlying_bridges: tuple[StatutoryUnderlyingBridge, ...] = Field(max_length=200)
    guidance_changes: tuple[GuidanceChange, ...] = Field(max_length=100)
    thesis_pillar_effects: tuple[CitedStatement, ...] = Field(max_length=100)
    catalysts: tuple[CitedStatement, ...] = Field(max_length=100)
    falsifiers: tuple[CitedStatement, ...] = Field(max_length=100)
    conflicts: tuple[EvidenceConflict, ...] = Field(max_length=100)
    missing_evidence: tuple[str, ...] = Field(max_length=200)
    outcome: ResultsReviewOutcome
    tax_assessment_reference: TaxAssessmentReference
    model_independence: Literal[True]

    @model_validator(mode="after")
    def validate_temporal_and_outcome_gates(self) -> Self:
        if self.as_of != self.frozen_input.knowledge_cutoff.date():
            raise ValueError("review as_of must equal the UTC knowledge_cutoff date")
        if self.created_at < self.frozen_input.knowledge_cutoff:
            raise ValueError("review cannot be created before its knowledge cutoff")
        if self.missing_evidence and self.outcome != "abstain":
            raise ValueError("missing evidence must force an abstain outcome")
        unresolved = [c.description for c in self.conflicts if c.resolution is None]
        if unresolved and self.outcome == "complete":
            raise ValueError(f"unresolved conflicts forbid a complete outcome: {unresolved}")
        return self

    def cited_evidence_ids(self) -> frozenset[str]:
        """Every evidence id any part of this artifact rests on."""
        ids: set[str] = set()
        for delta in self.metric_deltas:
            ids.update(delta.evidence_ids)
        for bridge in self.statutory_underlying_bridges:
            for adjustment in bridge.adjustments:
                ids.update(adjustment.evidence_ids)
        for guidance in self.guidance_changes:
            ids.update(guidance.evidence_ids)
        for group in (self.thesis_pillar_effects, self.catalysts, self.falsifiers):
            for statement in group:
                ids.update(statement.evidence_ids)
        for conflict in self.conflicts:
            ids.update(conflict.evidence_ids)
        return frozenset(ids)


class ResultsReviewCase(Contract):
    """Binds one document, one frozen evidence packet, and one review artifact.

    The results-review analogue of the decision engine's `DecisionCase`
    integrity chain: identities must resolve, hashes must verify, every
    citation must land inside the frozen packet, and the temporal boundary is
    the packet's."""

    case_id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=500)
    document: SourceDocumentRecord
    evidence: EvidencePacket
    review: ResultsReviewArtifact

    @model_validator(mode="after")
    def validate_integrity_chain(self) -> Self:
        frozen = self.review.frozen_input
        if frozen.evidence_packet_id != self.evidence.evidence_packet_id:
            raise ValueError("review does not reference this evidence packet")
        if frozen.document_id != self.document.document_id:
            raise ValueError("review does not reference this document")
        if frozen.document_sha256 != self.document.document_sha256:
            raise ValueError("frozen document hash does not match the document record")
        for field_name in ("security_id", "period_end", "period_type", "currency"):
            if getattr(frozen, field_name) != getattr(self.document, field_name):
                raise ValueError(f"frozen {field_name} does not match the document record")
        if frozen.units_scale != self.document.units_scale:
            raise ValueError("frozen units_scale does not match the document record")
        if frozen.knowledge_cutoff != self.evidence.knowledge_cutoff:
            raise ValueError("review and evidence packet must share one knowledge_cutoff")
        if self.review.as_of != self.evidence.as_of:
            raise ValueError("review and evidence packet must share one as_of")
        if self.document.release_at > self.evidence.knowledge_cutoff:
            raise ValueError("document released after the packet cutoff cannot be reviewed")
        if not (
            self.evidence.knowledge_cutoff
            <= self.review.created_at
            < self.evidence.expires_at
        ):
            raise ValueError("review created_at must be within packet cutoff and expiry")
        if self.review.data_mode != self.evidence.data_mode:
            raise ValueError("review data_mode must match the evidence packet")
        if self.document.data_mode != self.evidence.data_mode:
            raise ValueError("document data_mode must match the evidence packet")
        packet_ids = {item.evidence_id for item in self.evidence.items}
        outside = self.review.cited_evidence_ids() - packet_ids
        if outside:
            raise ValueError(f"case cites evidence outside the frozen packet: {sorted(outside)}")
        artifacts: tuple[ContentAddressedContract, ...] = (
            self.document,
            self.evidence,
            self.review.frozen_input,
            self.review.tax_assessment_reference,
            self.review,
        )
        if not all(verify_content_hash(artifact) for artifact in artifacts):
            raise ValueError("case contains an artifact with invalid content integrity")
        return self
