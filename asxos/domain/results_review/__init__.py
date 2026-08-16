"""Frozen results-review contracts (P2-02), adapter (P2-03), reviewer (P2-04).

One package per major entity (house convention). `contracts.py` and
`fixtures.py` freeze the contracts the ASX Results-to-Thesis Review slice
(`P2`) builds on; the freeze decisions and their citations are recorded in
`docs/product/results-review-contracts-2026-08-16.md`. `adapter.py` (P2-03)
mechanically surfaces those frozen artifacts from a hashed fixture — pure
in-memory, read-only, no DB access, and no persistence of its output.
`gates.py` / `reviewer.py` / `challenger.py` (P2-04) are the deterministic
review core: the frozen mechanical acceptance gates, the
``complete | revise | abstain`` reviewer, and the first producer of the
canonical `ChallengeResult` (gap G9). There is still no recommendation
surface — recommendation generation stays disabled pending Australian legal
review, and abstention is a valid, successful outcome.
"""

from asxos.domain.results_review.adapter import (
    SCALE_EXPONENT,
    AdaptedResultsReview,
    ResultsReviewAdapterError,
    adapt_hashed_fixture,
    artifact_output_sha256,
    map_statement_period_type,
    normalize_scale,
    partition_admissible_evidence,
    render_artifact_json,
    render_artifact_markdown,
    verify_hashed_fixture_payload,
)
from asxos.domain.results_review.challenger import (
    CHALLENGE_RESULT_ID_PREFIX,
    CHALLENGED_ARTIFACT_BINDING,
    challenge_adapted,
    challenge_case,
)
from asxos.domain.results_review.contracts import (
    ADMISSIBLE_SOURCE_CLASSES,
    DEFAULT_TAX_READINESS,
    DELTA_PCT_QUANT,
    DOCUMENT_HASH_ALGORITHM,
    LOAD_BEARING_SOURCE_CLASSES,
    RESULTS_REVIEW_SCHEMA_VERSION,
    SECURITY_ID_BINDING,
    SOURCE_RANK,
    STATEMENT_KNOWN_AT_UTC_TIME,
    TAX_ASSESSMENT_PRODUCERS,
    TRADING_CALENDAR_ID_PREFIX,
    TRADING_CALENDAR_SOURCE,
    TRADING_SESSION_CLOSE_LOCAL,
    AcquisitionPath,
    CitedStatement,
    DocumentKind,
    EvidenceConflict,
    FrozenInputTuple,
    GuidanceChange,
    MetricAdjustment,
    MetricDelta,
    PeriodType,
    ResultsReviewArtifact,
    ResultsReviewCase,
    ResultsReviewOutcome,
    SourceClass,
    SourceDocumentRecord,
    StatutoryUnderlyingBridge,
    UnitScale,
    derive_statement_known_at,
    frozen_delta_pct,
    hash_document_payload,
    unresolved_tax_assessment_reference,
)
from asxos.domain.results_review.gates import (
    FROZEN_OUTCOME_TRIPLE,
    GateCheck,
    GateName,
    MechanicalGateReport,
    evaluate_case,
)
from asxos.domain.results_review.reviewer import (
    VERDICT_SCOPE_STATEMENT,
    ChallengedReview,
    ReviewerVerdict,
    challenged_review,
    review_adapted,
    review_case,
)

__all__ = [
    "ADMISSIBLE_SOURCE_CLASSES",
    "CHALLENGED_ARTIFACT_BINDING",
    "CHALLENGE_RESULT_ID_PREFIX",
    "DEFAULT_TAX_READINESS",
    "DELTA_PCT_QUANT",
    "DOCUMENT_HASH_ALGORITHM",
    "FROZEN_OUTCOME_TRIPLE",
    "LOAD_BEARING_SOURCE_CLASSES",
    "RESULTS_REVIEW_SCHEMA_VERSION",
    "SCALE_EXPONENT",
    "SECURITY_ID_BINDING",
    "SOURCE_RANK",
    "STATEMENT_KNOWN_AT_UTC_TIME",
    "TAX_ASSESSMENT_PRODUCERS",
    "TRADING_CALENDAR_ID_PREFIX",
    "TRADING_CALENDAR_SOURCE",
    "TRADING_SESSION_CLOSE_LOCAL",
    "VERDICT_SCOPE_STATEMENT",
    "AcquisitionPath",
    "AdaptedResultsReview",
    "ChallengedReview",
    "CitedStatement",
    "DocumentKind",
    "EvidenceConflict",
    "FrozenInputTuple",
    "GateCheck",
    "GateName",
    "GuidanceChange",
    "MechanicalGateReport",
    "MetricAdjustment",
    "MetricDelta",
    "PeriodType",
    "ResultsReviewAdapterError",
    "ReviewerVerdict",
    "ResultsReviewArtifact",
    "ResultsReviewCase",
    "ResultsReviewOutcome",
    "SourceClass",
    "SourceDocumentRecord",
    "StatutoryUnderlyingBridge",
    "UnitScale",
    "adapt_hashed_fixture",
    "artifact_output_sha256",
    "challenge_adapted",
    "challenge_case",
    "challenged_review",
    "derive_statement_known_at",
    "evaluate_case",
    "frozen_delta_pct",
    "hash_document_payload",
    "map_statement_period_type",
    "normalize_scale",
    "partition_admissible_evidence",
    "render_artifact_json",
    "render_artifact_markdown",
    "review_adapted",
    "review_case",
    "unresolved_tax_assessment_reference",
    "verify_hashed_fixture_payload",
]
