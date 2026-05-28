"""Theme domain types — stub for M-Thesis-0.

Full schema and business logic land in M-Theme-1.
Column names mirror the `themes` table per V2 spec Part 6.2
(with D6 revision: adjacent_codes TEXT[] column).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Theme:
    """Placeholder — full schema in M-Theme-1."""

    theme_id: int
    name: str
    stage: str  # 'early' | 'emerging' | 'consensus' | 'mature'
    stage_suggested: str | None  # auto-detected, user-confirmed (D8)
    adjacent_codes: tuple[str, ...]  # GICS or custom codes (D6)
    created_at: datetime
    updated_at: datetime
