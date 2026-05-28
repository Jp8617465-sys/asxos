"""Underlyings domain types — stub for M-Thesis-0.

Full schema and business logic land in M-Thesis-2.
Column names mirror the `thesis_underlyings` table per V2 spec Part 6.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ThesisUnderlying:
    """Placeholder — full schema in M-Thesis-2."""

    underlying_id: int
    thesis_id: int
    symbol: str
    weight: Decimal  # proportion of thesis exposure
    rationale: str
    created_at: datetime
