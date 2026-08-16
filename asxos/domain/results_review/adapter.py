"""Deterministic read-only results-review adapter — mission P2-03.

Consumes a hashed fixture — the ONLY admissible acquisition path
(`contracts.AcquisitionPath`, §8 item 1 / G2) — verifies the document payload
hash, revalidates every frozen P2-02 contract gate, and renders JSON and
Markdown from the same validated artifact (plan required-work items 1-4 and 7;
`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md:296-305`).

The adapter NEVER evaluates quality. Every outcome it surfaces — including
`abstain` — is the frozen artifact's own outcome, enforced by the P2-02
validators on revalidation (`contracts.ResultsReviewArtifact`,
`contracts.ResultsReviewCase`). The independent finance challenge and the
complete/revise/abstain verdict logic are P2-04 (plan items 5-6) and do not
exist here. Recommendation generation is disabled pending Australian legal
review: nothing in this module emits ratings, price targets, portfolio
instructions, or thesis mutations, and abstention is a valid, successful
outcome (matrix :366-368).

Pure in-memory transformation: no network, no DB, no file writes. Its output
is never persisted by this module — do not add persistence without explicit
authorization. Decimal-only arithmetic per
`.claude/rules/portfolio-conventions.md` §Decimal-only; the frozen contracts
reject float input and this module never introduces one.

A real (non-fixture) acquisition path is unrepresentable today: widening
`AcquisitionPath` beyond ``"hashed_fixture"`` is a separately authorized work
order (freeze record §2), at which point this adapter must gain an explicit
dispatch on the acquisition path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Context, Decimal, Inexact, InvalidOperation, Overflow
from types import MappingProxyType
from typing import Final

from asxos.domain.decision_engine.types import EvidenceItem, require_utc
from asxos.domain.results_review.contracts import (
    PeriodType,
    ResultsReviewArtifact,
    ResultsReviewCase,
    SourceDocumentRecord,
    UnitScale,
    hash_document_payload,
)


class ResultsReviewAdapterError(ValueError):
    """Hard failure of a mechanical adapter step (CLAUDE.md non-negotiable #10).

    No graceful warnings: a payload that does not hash to its document record,
    or a statement vocabulary this adapter cannot map, stops the review.
    """


# ---------------------------------------------------------------------------
# Document payload verification (§8 item 1 — the hashed-fixture ruling, G2)
# ---------------------------------------------------------------------------


def verify_hashed_fixture_payload(
    payload: Mapping[str, object], document: SourceDocumentRecord
) -> None:
    """Verify a fixture payload against its frozen document record.

    The frozen rule (§8 item 1, `contracts.DOCUMENT_HASH_ALGORITHM`):
    ``hash_document_payload(payload)`` must equal the record's
    ``document_sha256`` exactly. Any divergence — a tampered figure, an
    injected key, a reordered-but-different value — hard-fails; there is no
    partial acceptance. Comparison uses ``hmac.compare_digest``, matching the
    canonical `verify_content_hash` idiom (`types.py:207-211`).
    """
    digest = hash_document_payload(payload)
    if not hmac.compare_digest(digest, document.document_sha256):
        raise ResultsReviewAdapterError(
            f"document payload hash {digest} does not match the frozen record "
            f"{document.document_sha256} for document {document.document_id!r}"
        )


# ---------------------------------------------------------------------------
# Mechanical evidence-cutoff partition (§8 item 4 context; types.py:249-251)
# ---------------------------------------------------------------------------


def partition_admissible_evidence(
    items: Iterable[EvidenceItem], knowledge_cutoff: datetime
) -> tuple[tuple[EvidenceItem, ...], tuple[EvidenceItem, ...]]:
    """Split evidence at the frozen cutoff rule; return (admissible, excluded).

    This surfaces the canonical packet gate — evidence is admissible iff
    ``known_at <= knowledge_cutoff`` (`types.py:249-251`) — as a total
    function, adding no rule of its own. At-cutoff evidence is admissible;
    evidence known strictly after the cutoff is mechanically excluded. Under
    the conservative end-of-day `known_at` convention (§8 item 4,
    `contracts.derive_statement_known_at`), a vendor-dated row disclosed on
    the cutoff day therefore stays excluded at any intraday cutoff — the
    approximation can only err toward exclusion, never leakage.
    """
    cutoff = require_utc(knowledge_cutoff, field_name="knowledge_cutoff")
    admissible: list[EvidenceItem] = []
    excluded: list[EvidenceItem] = []
    for item in items:
        if item.known_at <= cutoff:
            admissible.append(item)
        else:
            excluded.append(item)
    return tuple(admissible), tuple(excluded)


# ---------------------------------------------------------------------------
# Statement-vocabulary mapping (freeze record §5 — assigned to this adapter)
# ---------------------------------------------------------------------------

#: `rs_financial_statements.period_type` admits only these two values
#: (`migrations/0027_research_store.sql:71`). `half_yearly` is a
#: document-level reality (ASX Appendix 4D) with no `rs_*` row shape — the
#: freeze record (§5) assigns this mapping to the P2-03 adapter and rules
#: that it involves no `rs_*` schema change.
_STATEMENT_PERIOD_TYPES: Final[Mapping[str, PeriodType]] = MappingProxyType(
    {"yearly": "yearly", "quarterly": "quarterly"}
)


def map_statement_period_type(value: str) -> PeriodType:
    """Map an `rs_financial_statements.period_type` value into the frozen vocabulary.

    Total over the store's DDL vocabulary (`yearly | quarterly`, 0027:71) and
    a hard failure on everything else — including ``half_yearly``, which only
    a document (`contracts.DocumentKind` ``half_year_results``) may claim, and
    which no vendor statement row can carry today.
    """
    try:
        return _STATEMENT_PERIOD_TYPES[value]
    except KeyError:
        raise ResultsReviewAdapterError(
            f"period_type {value!r} is not an rs_financial_statements vocabulary "
            "member (migrations/0027_research_store.sql:71 admits yearly|quarterly); "
            "half_yearly exists only at document level (ASX Appendix 4D)"
        ) from None


# ---------------------------------------------------------------------------
# Units/scale normalization (G4 — explicit scale on every monetary figure)
# ---------------------------------------------------------------------------

#: Powers of ten for the frozen presentation scales (`contracts.UnitScale`).
SCALE_EXPONENT: Final[Mapping[UnitScale, int]] = MappingProxyType(
    {"ones": 0, "thousands": 3, "millions": 6, "billions": 9}
)


def normalize_scale(value: Decimal, from_scale: UnitScale, to_scale: UnitScale) -> Decimal:
    """Re-express a monetary figure at another presentation scale, exactly (G4).

    A pure decimal-point shift (``scaleb``) under a context that traps
    ``Inexact``: a scale normalization can never round — if it ever would,
    it raises instead of silently losing precision. ``InvalidOperation`` and
    ``Overflow`` stay trapped too, so a signaling NaN or out-of-range shift
    fails loudly instead of propagating a quiet NaN (CLAUDE.md #10). Currency
    is deliberately NOT a parameter: a cross-currency figure is not a scale
    change, and mixed currencies stay unrepresentable at the contract level
    (`contracts.MetricDelta`, `contracts.StatutoryUnderlyingBridge`).
    """
    context = Context(prec=60, traps=[Inexact, InvalidOperation, Overflow])
    return value.scaleb(SCALE_EXPONENT[from_scale] - SCALE_EXPONENT[to_scale], context=context)


# ---------------------------------------------------------------------------
# Rendering — JSON and Markdown from the same validated artifact (plan :305)
# ---------------------------------------------------------------------------


def _canonical_json(payload: object) -> str:
    """The decision engine's canonical JSON form (`types.py:_canonical_digest`)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(text: str) -> str:
    """The one definition of the output fingerprint: SHA-256 over UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _md_text(value: str) -> str:
    """Neutralize Markdown structure in interpolated free text (security hardening).

    Contract free-text fields cap length, not content: an embedded ``|``
    could forge table cells and an embedded newline could forge headings or
    list items in the deterministic render. Newlines collapse to single
    spaces and pipes are escaped; content is otherwise verbatim. This is
    presentation-only — no artifact field is altered, and the JSON render is
    already injection-safe via ``json.dumps`` escaping.
    """
    return " ".join(value.splitlines()).replace("|", "\\|")


def render_artifact_json(review: ResultsReviewArtifact) -> str:
    """Render the validated artifact as canonical JSON.

    Same canonicalization as the content-hash seal (sorted keys, compact
    separators, ASCII) so the render is deterministic by construction, and
    every string is escaped by ``json.dumps``. Like the Markdown renderer,
    a bare artifact (outside `adapt_hashed_fixture`'s case closure) is
    trusted input.
    """
    return _canonical_json(review.model_dump(mode="json"))


def artifact_output_sha256(review: ResultsReviewArtifact) -> str:
    """SHA-256 fingerprint of the canonical JSON render (the P2-05 hash input)."""
    return _sha256_hex(render_artifact_json(review))


def render_artifact_markdown(review: ResultsReviewArtifact) -> str:
    """Render the SAME validated artifact as deterministic Markdown (plan :305).

    Every line derives from artifact fields; nothing is fetched, timestamped
    at render time, or invented. The document payload is never embedded — the
    artifact carries only its hash — so non-evidence document text (including
    an adversarial fixture's injected string, G10) cannot surface here. Free
    text is structurally neutralized (`_md_text`) so a field cannot forge
    table cells or headings. Renderers accept a bare artifact: outside
    `adapt_hashed_fixture` (which enforces the case-level citation closure
    and hash chain), treat input as trusted — element strings inside tuple
    fields carry no per-element length cap in the frozen contracts (tracked
    for a contract amendment).
    """
    frozen = review.frozen_input
    lines: list[str] = [
        f"# Results review {_md_text(review.review_id)}",
        "",
        "Analysis only: no recommendation, no rating, no price target, no trade",
        "or position-size instruction (plan :303). Abstention is a valid,",
        "successful outcome.",
        "",
        f"- Outcome: **{review.outcome}**",
        f"- Security: {_md_text(frozen.security_id)}",
        f"- Period: {frozen.period_end.isoformat()} ({frozen.period_type})",
        f"- Currency / scale: {frozen.currency} / {frozen.units_scale}",
        f"- Knowledge cutoff: {frozen.knowledge_cutoff.isoformat()}",
        f"- As of: {review.as_of.isoformat()}",
        f"- Document: {_md_text(frozen.document_id)} (sha256 {frozen.document_sha256})",
        f"- Evidence packet: {_md_text(frozen.evidence_packet_id)}",
        f"- Tax readiness: {review.tax_assessment_reference.readiness}",
        f"- Model-independent: {review.model_independence}",
        f"- Artifact content hash: {review.content_hash}",
    ]
    if review.metric_deltas:
        lines += [
            "",
            "## Metric deltas",
            "",
            "| Metric | Basis | Currency | Scale | Current | Prior | Delta % |",
            "|---|---|---|---|---|---|---|",
        ]
        for delta in review.metric_deltas:
            prior = "-" if delta.prior_value is None else str(delta.prior_value)
            pct = "-" if delta.delta_pct is None else str(delta.delta_pct)
            lines.append(
                f"| {_md_text(delta.metric)} | {delta.basis} | {delta.currency} | {delta.scale} "
                f"| {delta.current_value} | {prior} | {pct} |"
            )
    for bridge in review.statutory_underlying_bridges:
        lines += [
            "",
            f"## Bridge: {_md_text(bridge.metric)} ({bridge.currency}, {bridge.scale})",
            "",
            f"Statutory {bridge.statutory} + adjustments = underlying {bridge.underlying}",
        ]
        for adjustment in bridge.adjustments:
            cited = _md_text(", ".join(adjustment.evidence_ids))
            lines.append(
                f"- {adjustment.amount}: {_md_text(adjustment.label)} — "
                f"{_md_text(adjustment.explanation)} [{cited}] ({adjustment.source_class})"
            )
    if review.guidance_changes:
        lines += ["", "## Guidance changes", ""]
        for guidance in review.guidance_changes:
            prior_text = guidance.prior if guidance.prior is not None else "no recorded prior"
            cited = _md_text(", ".join(guidance.evidence_ids))
            lines.append(
                f"- {_md_text(guidance.metric)}: {_md_text(prior_text)} -> "
                f"{_md_text(guidance.current)} [{cited}] ({guidance.source_class})"
            )
    for heading, statements in (
        ("Thesis-pillar effects", review.thesis_pillar_effects),
        ("Catalysts", review.catalysts),
        ("Falsifiers", review.falsifiers),
    ):
        if statements:
            lines += ["", f"## {heading}", ""]
            for statement in statements:
                cited = _md_text(", ".join(statement.evidence_ids))
                lines.append(f"- {_md_text(statement.statement)} [{cited}]")
    if review.conflicts:
        lines += ["", "## Evidence conflicts", ""]
        for conflict in review.conflicts:
            resolution = (
                conflict.resolution if conflict.resolution is not None else "UNRESOLVED"
            )
            cited = _md_text(", ".join(conflict.evidence_ids))
            lines.append(
                f"- {_md_text(conflict.description)} [{cited}] — "
                f"resolution: {_md_text(resolution)}"
            )
    if review.missing_evidence:
        lines += ["", "## Missing evidence", ""]
        lines += [f"- {_md_text(item)}" for item in review.missing_evidence]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The adapter entry point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdaptedResultsReview:
    """The adapter's complete in-memory output. Never persisted by this module.

    ``artifact_sha256`` fingerprints the canonical JSON render of the review
    artifact (the plan :305 / P2-05 hash input). ``case_sha256`` fingerprints
    the full revalidated case — document record, evidence packet, and review,
    each sealed by its own content hash — so every input field either changes
    ``case_sha256`` or is rejected outright before adaptation completes.
    """

    case: ResultsReviewCase
    artifact_json: str
    artifact_markdown: str
    artifact_sha256: str
    case_sha256: str


def adapt_hashed_fixture(
    payload: Mapping[str, object], case: ResultsReviewCase
) -> AdaptedResultsReview:
    """Adapt one hashed fixture into the frozen artifact types, mechanically.

    Steps, all deterministic and in-memory:

    1. Verify the document payload hash against the frozen record
       (`verify_hashed_fixture_payload`, §8 item 1).
    2. Revalidate the ENTIRE case through a JSON round-trip — this re-runs
       every frozen P2-02 gate: exact-Decimal bridge reconciliation (§8 item
       5, no tolerance), the frozen delta arithmetic (`frozen_delta_pct`),
       the outcome gates (missing evidence forces ``abstain``; an unresolved
       conflict forbids ``complete``), the citation closure, the temporal
       boundary, and the full content-hash chain
       (`ResultsReviewCase.validate_integrity_chain`). An unvalidated or
       tampered instance (e.g. built via ``model_construct``) fails here.
    3. Render JSON and Markdown from the same revalidated artifact and
       fingerprint both the artifact render and the full case.

    The adapter surfaces the artifact's frozen outcome verbatim — it never
    decides one. No network, no DB, no file writes, no persistence.
    """
    verify_hashed_fixture_payload(payload, case.document)
    admitted = ResultsReviewCase.model_validate(case.model_dump(mode="json"))
    artifact_json = render_artifact_json(admitted.review)
    case_json = _canonical_json(admitted.model_dump(mode="json"))
    return AdaptedResultsReview(
        case=admitted,
        artifact_json=artifact_json,
        artifact_markdown=render_artifact_markdown(admitted.review),
        artifact_sha256=_sha256_hex(artifact_json),
        case_sha256=_sha256_hex(case_json),
    )
