"""Thesis domain types — M-Thesis-1.

Supersedes the M-Thesis-0 stub. All fields mirror the `theses` and
`thesis_revisions` tables in migration 0012_theses_and_themes.sql.

Design decisions:
  - BIGSERIAL int PKs throughout (not SERIAL).
  - `timeline_days` is the single source of truth; no `expires_at` column.
    Deadline = opened_at.date() + timedelta(days=timeline_days).
  - `thesis_text` is nullable in DB; enter_thesis() hard-fails if missing.
  - `invalidation_conditions` serialised as JSONB array; each element maps to
    InvalidationCondition. Status is manual in v1.
  - `themes` is a denormalised TEXT[] of theme_codes on the theses table.
    Kept in sync with theme_holdings at write time by ThesisService.
  - Decimal serialisation contract in thesis_revisions.diff JSONB:
    Decimal values → str(value), e.g. Decimal("55.123456") → "55.123456".
    Parse back with Decimal(str_value). Never float().

References:
  spec Part 6.1 (theses schema)
  spec Part 6.4 (thesis_revisions schema)
  M-THESIS-1_IMPLEMENTATION_PLAN_V2.md §3, §4 Phase 2
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class InvalidationCondition:
    """One invalidation condition on a thesis.

    status is manual in v1:
      'active'    — condition is live and being monitored
      'triggered' — condition has been met (thesis should be reviewed/exited)
      'resolved'  — condition no longer applies (thesis can continue)
    """

    condition: str
    status: str  # 'active' | 'triggered' | 'resolved'
    note: str | None


@dataclass(frozen=True)
class Thesis:
    """Mirrors the `theses` table (migration 0012).

    thesis_text is None for research/watching status without articulated thesis.
    enter_thesis() hard-fails (raises ValueError) if thesis_text is None or ''.

    entry_band_lower <= entry_band_upper is enforced by DB CHECK.
    Both may be None for research status (no price plan yet).

    stop_price / target_price are None for research status;
    enter_thesis() hard-fails if either is None.

    timeline_days: days from opened_at to expected exit.
    Compute day-N-of-M: (date.today() - opened_at.date()).days
    Compute deadline:    opened_at.date() + timedelta(days=timeline_days)
    None for research status.

    themes: denormalised tuple of theme_codes attached to this thesis.
    Do not modify directly — use ThesisService.attach_theme().
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
    invalidation_conditions: tuple[InvalidationCondition, ...]
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


@dataclass(frozen=True)
class ThesisRevision:
    """One row in thesis_revisions — the append-only discipline event log.

    diff format: {"field": {"old": "serialised_value", "new": "serialised_value"}}
    Decimal values are serialised as str(Decimal_value). Parse back with
    Decimal(str_value). Never float(). Empty dict ({}) for reviewed_no_change.

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
    "invalidation_conditions": "invalidation_conditions",
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
    "invalidation_conditions": "assumption_change",
}
