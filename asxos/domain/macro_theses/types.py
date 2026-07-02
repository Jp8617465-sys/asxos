"""Macro-thesis domain types — Phase 2a.

All fields mirror the `macro_theses` table (migration 0035).

Design decisions:
  - governance_status DEFAULTs to 'draft' (not 'approved' like Thesis/Theme)
    — this table is net-new and zero-row; agent-drafted is the norm here,
    not a grandfathered exception. See migration 0035's inline comment.
  - retired_at is a DATE (not a status value), mirroring Theme's own
    retired_at. A CHECK constraint (migration 0035) prevents retiring a
    thesis that was never approved.
  - data_signals is a JSONB array of free-text signal descriptions the
    macro-economist agent cited — not a typed structure, since the set of
    signals an agent might reference is open-ended.

References:
  migrations/0035_macro_theses_and_governance_columns.sql
  docs/proposals/governance-first-architecture-2026-06-30.md Section 5.5
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class MacroThesis:
    """Mirrors the `macro_theses` table (migration 0035).

    regime_quadrant: one of the 4-value regime taxonomy shared with
      MacroThesisProposal (asxos/domain/theses/schemas.py).

    source_run_id: NULL = human-authored. Non-NULL references the
      agent_runs row that produced this thesis as a draft proposal.
    """

    macro_thesis_id: int
    title: str
    thesis_text: str
    regime_quadrant: str
    horizon_months: int | None
    catalyst: str
    falsifier: str
    data_signals: tuple[str, ...]
    source_run_id: int | None
    governance_status: str
    created_at: datetime
    retired_at: date | None
