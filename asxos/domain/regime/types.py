"""Regime domain types — stub for M-Thesis-0.

Full schema and business logic land in M-Market-Context.
Column names mirror the `regime_snapshots` table per V2 spec Part 6.4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class RegimeSnapshot:
    """Placeholder — full schema in M-Market-Context."""

    snapshot_id: int
    as_of: date
    label: str  # 'risk_on' | 'risk_off' | 'neutral'
    confidence: Decimal
    drivers: tuple[str, ...]
    created_at: datetime
