"""Thesis domain types — stub for M-Thesis-0.

Full schema and business logic land in M-Thesis-1.
Column names mirror the `theses` table per V2 spec Part 6.1
(with D3 revision: status enum includes 'research').
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Thesis:
    """Placeholder — full schema in M-Thesis-1."""

    thesis_id: int
    symbol: str
    status: str  # 'research' | 'watching' | 'active' | 'exited' | 'expired'
    entry_price: Decimal | None
    stop_price: Decimal | None
    target_price: Decimal | None
    horizon_months: int | None
    created_at: datetime
    updated_at: datetime
    expires_at: date | None
