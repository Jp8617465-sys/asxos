"""Thesis domain types — M-Thesis-1 (+ 0042 rules-integrity).

Supersedes the M-Thesis-0 stub. All fields mirror the `theses`,
`thesis_revisions`, `thesis_conditions` and `thesis_condition_events` tables
(migrations 0012 and 0042).

Design decisions:
  - BIGSERIAL int PKs throughout (not SERIAL).
  - `timeline_days` is the single source of truth; no `expires_at` column.
    Deadline = opened_at.date() + timedelta(days=timeline_days).
  - `thesis_text` is nullable in DB; enter_thesis() hard-fails if missing.
  - Invalidation conditions are NORMALISED rows (migration 0042, D1/R2):
    `ThesisCondition` mirrors `thesis_conditions` (current state + the
    authoring-time parse baseline), `ConditionEvent` mirrors
    `thesis_condition_events` (append-only episode log with price-date
    provenance). The pre-0042 write-once `theses.invalidation_conditions`
    JSONB column — and its `InvalidationCondition` dataclass — are gone
    (dropped in 0042; leaving them would recreate the register #1 stale-read
    split-brain).
  - `themes` is a denormalised TEXT[] of theme_codes on the theses table.
    Kept in sync with theme_holdings at write time by ThesisService.
  - Decimal serialisation contract in thesis_revisions.diff JSONB:
    Decimal values → str(value), e.g. Decimal("55.123456") → "55.123456".
    Parse back with Decimal(str_value). Never float().

References:
  spec Part 6.1 (theses schema)
  spec Part 6.4 (thesis_revisions schema)
  migrations/0042_rules_integrity.sql (thesis_conditions / events / attestation)
  M-THESIS-1_IMPLEMENTATION_PLAN_V2.md §3, §4 Phase 2
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from asxos.domain.theses.schemas import ReportSection


@dataclass(frozen=True)
class ThesisCondition:
    """One row in thesis_conditions (migration 0042) — current per-condition
    state plus the authoring-time machine-enforcement baseline.

    trigger_semantics is the authored INTENT ('hard_exit' | 'alert_review').
    The EFFECTIVE semantics are computed at read time: alert_review whenever
    the instrument is disposal-locked (KD-2/KD-3) — the lock never mutates
    authored intent.

    status: 'active' | 'triggered' | 're_armed' | 'resolved' (terminal).
    're_armed' is deliberately distinct from 'active' — it asserts "breached
    at least once, currently recaptured", which surfaces must render with the
    episode history.

    enforcement_kind/enforcement_threshold is what the daily job evaluates —
    the STORED baseline echoed to James at authoring, never a runtime
    re-parse. enforcement_note is the parser echo, verbatim; for unparseable
    conditions it is the LOUD 'NOT MACHINE-CHECKED' marking every consumer
    must render (register #5).
    """

    condition_id: int
    thesis_id: int
    ordinal: int
    condition_text: str
    trigger_semantics: str  # 'hard_exit' | 'alert_review' — authored intent
    status: str  # 'active' | 'triggered' | 're_armed' | 'resolved'
    enforcement_kind: str  # 'price_below' | 'price_above' | 'not_machine_checkable'
    enforcement_threshold: Decimal | None  # None iff not_machine_checkable
    enforcement_note: str
    parser_version: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConditionEvent:
    """One row in thesis_condition_events (migration 0042) — append-only.

    price_date is the CLOSE's dt, never the run date (register #21);
    detected_at carries the run/detection time separately. observed_close is
    None only for human 'resolved' events. Episodes are derived (consecutive
    triggered→re_armed pairs) — there is no episode table and no duration
    counter (the "day 36" class is unproducible by construction).
    """

    event_id: int
    condition_id: int
    thesis_id: int
    event_type: str  # 'triggered' | 're_armed' | 'resolved'
    price_date: date
    observed_close: Decimal | None
    threshold: Decimal | None
    detected_at: datetime
    source: str  # 'job' | 'human' | 'sweep' | 'migration'
    note: str | None


@dataclass(frozen=True)
class Thesis:
    """Mirrors the `theses` table (migration 0012, + 0042 attestation).

    thesis_text is None for research/watching status without articulated thesis.
    enter_thesis() hard-fails (raises ValueError) if thesis_text is None or ''.

    entry_band_lower <= entry_band_upper is enforced by DB CHECK; for
    UNDERWRITTEN rows the strict attestation-gated ladder CHECK
    (theses_ladder_coherent_long_v1, migration 0042) additionally requires
    stop < lower < upper < target pairwise where present.

    stop_price / target_price are None for research status;
    enter_thesis() hard-fails if either is None.

    timeline_days: days from opened_at to expected exit.
    Compute day-N-of-M: (date.today() - opened_at.date()).days
    Compute deadline:    opened_at.date() + timedelta(days=timeline_days)
    None for research status.

    themes: denormalised tuple of theme_codes attached to this thesis.
    Do not modify directly — use ThesisService.attach_theme().

    governance_status (migration 0033): provenance/approval state, ORTHOGONAL
    to status. status answers "is capital deployed"; governance_status
    answers "is this content trustworthy enough to exist/be acted on".
    DEFAULT 'approved' — matches the DB column default, grandfathering every
    pre-0033 row. enter_thesis() hard-fails unless this is 'approved'. See
    docs/proposals/governance-first-architecture-2026-06-30.md Section 4.1.

    attestation (migration 0042, D4/R9): ORTHOGONAL to both of the above —
    it answers "has James underwritten these numbers". DEFAULT 'placeholder'
    (new rules are BORN placeholder — the inverse of the born-approved
    governance default, register #2). enter_thesis() hard-fails unless
    'underwritten'; alert action-verbs are gated on it too. Transition ONLY
    via service.attest_thesis().

    Invalidation conditions live in thesis_conditions (ThesisCondition above),
    not on this dataclass — fetch via conditions.list_conditions().
    """

    thesis_id: int
    symbol: str
    status: str  # 'research' | 'watching' | 'active' | 'exited' | 'expired'
    thesis_text: str | None
    entry_band_lower: Decimal | None
    entry_band_upper: Decimal | None
    stop_price: Decimal | None
    target_price: Decimal | None
    timeline_days: int | None
    themes: tuple[str, ...]  # theme_codes (denormalised fast-lookup)
    actual_entry_price: Decimal | None
    actual_entry_at: datetime | None
    actual_exit_price: Decimal | None
    actual_exit_at: datetime | None
    last_revisited_at: datetime
    revisit_due_at: datetime
    opened_at: datetime
    closed_at: datetime | None
    # Analyst consensus fields (migration 0021)
    analyst_buy_count: int | None = None
    analyst_neutral_count: int | None = None
    analyst_sell_count: int | None = None
    analyst_consensus_target: Decimal | None = None
    analyst_updated_at: datetime | None = None
    # Earnings fields (migration 0021)
    next_earnings_date: datetime | None = None
    earnings_notes: str = ""
    # PM conviction + tax fields (migration 0026)
    conviction_level: int | None = None  # 1..5 PM conviction scale; None = unset
    tax_notes: str = ""                  # CGT / franking / holding-period notes
    # Governance provenance/approval field (migration 0033)
    governance_status: str = "approved"  # 'draft'|'evidence_complete'|'pending_review'|
                                          # 'approved'|'rejected'|'retired'; matches DB DEFAULT
    # Broker-report sections (migration 0040, Phase C). Each element is a
    # ReportSection (asxos/domain/theses/schemas.py) — kind + prose body +
    # figures, each figure provenance-tagged. Populated only via
    # service.add_report_section(), which re-validates through
    # ReportSection/ReportFigure on every write (see that function's
    # docstring). Empty for every pre-migration-0040 thesis.
    report_sections: tuple[ReportSection, ...] = ()
    # Attestation (migration 0042, D4/R9) — matches DB DEFAULT 'placeholder'.
    attestation: str = "placeholder"  # 'placeholder' | 'underwritten'
    attestation_basis: str | None = None  # required non-empty iff underwritten


@dataclass(frozen=True)
class ThesisRevision:
    """One row in thesis_revisions — the append-only discipline event log.

    diff format: {"field": {"old": "serialised_value", "new": "serialised_value"}}
    Decimal values are serialised as str(Decimal_value). Parse back with
    Decimal(str_value). Never float(). Empty dict ({}) for reviewed_no_change.

    0042 extension: R8 sweep findings use revision_type='integrity_flag' with
    diff = {"flag": {"code": ..., "detail": {...}, "fingerprint": ...}} — a
    documented extension of the diff contract for non-field-change rows.

    reasoning is always non-empty. For reviewed_no_change it must state
    why the position is still being held — this is the discipline event.
    """

    revision_id: int
    thesis_id: int
    revised_at: datetime
    revision_type: str  # see CHECK constraint in migration for valid values
    diff: dict[str, Any]  # {field: {"old": str, "new": str}}
    reasoning: str


# ---------------------------------------------------------------------------
# Revision control — Item 4 (SQL injection prevention) from plan review.
# ---------------------------------------------------------------------------

# Maps Python attribute name → SQL column name for revise_thesis().
# Only fields in this allowlist may be updated via revise_thesis().
# Never interpolate raw field names into SQL — always look up here first.
REVISABLE_FIELDS: dict[str, str] = {
    "thesis_text": "thesis_text",
    "entry_band_lower": "entry_band_lower",
    "entry_band_upper": "entry_band_upper",
    "stop_price": "stop_price",
    "target_price": "target_price",
    "timeline_days": "timeline_days",
    "status": "status",
    "conviction_level": "conviction_level",
    "tax_notes": "tax_notes",
    # governance_status (migration 0033) is DELIBERATELY NOT in this
    # allowlist. It has its own dedicated transition functions
    # (approve_object()/reject_object() in service.py) that write a matching
    # governance_events row in the same transaction — a requirement the
    # migration 0034 theses_governance_audit trigger enforces at the DB
    # level. revise_thesis()'s generic path has no governance_events-writing
    # logic, so adding "governance_status" here would either be rejected
    # (current, correct behaviour — it's simply not in this dict) or, if
    # wired up carelessly, fail with an opaque trigger exception on the
    # UPDATE. Do not add "governance_status" to this dict.
    #
    # attestation (migration 0042) is likewise NOT revisable here — it has
    # its own dedicated transition function (attest_thesis() in service.py)
    # that runs the underwriting gates and writes the attestation_change
    # revision, exactly like governance_status. Do not add it.
    #
    # invalidation_conditions was removed in 0042 — conditions live in
    # thesis_conditions with their own service (conditions.py), not a
    # revisable JSONB blob.
}

# Maps Python attribute name → revision_type to record in thesis_revisions.
# Used by revise_thesis() to auto-classify the revision event.
_REVISION_TYPE_FOR_FIELD: dict[str, str] = {
    "thesis_text": "assumption_change",
    "entry_band_lower": "assumption_change",
    "entry_band_upper": "assumption_change",
    "stop_price": "stop_adjusted",
    "target_price": "target_adjusted",
    "timeline_days": "timeline_extended",
    "status": "status_change",
    "conviction_level": "assumption_change",
    "tax_notes": "assumption_change",
}
