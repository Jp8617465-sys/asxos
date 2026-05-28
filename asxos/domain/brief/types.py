"""V2 brief domain types — stub for M-Thesis-0.

Full schema and business logic land in M-Brief-Skeleton.
Types here mirror the `brief_runs` table and section data model
per V2 spec Part 5 and V2_ARCHITECTURE_AUDIT_AND_DESIGN.md Part B.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class BriefRun:
    """Placeholder — full schema in M-Brief-Skeleton."""

    run_id: int
    brief_date: date
    sections_enabled: tuple[str, ...]
    status: str  # 'success' | 'partial' | 'failed'
    sent_at: datetime | None
    created_at: datetime
