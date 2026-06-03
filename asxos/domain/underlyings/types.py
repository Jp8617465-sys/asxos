"""Underlyings domain types — M-Underlyings."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class UnderlyingCategory(StrEnum):
    commodity_resources = "commodity_resources"
    commodity_energy = "commodity_energy"
    commodity_agriculture = "commodity_agriculture"
    currency = "currency"
    rate = "rate"
    index = "index"  # type: ignore[assignment]


class UnderlyingDirection(StrEnum):
    positive = "positive"
    negative = "negative"


@dataclass(frozen=True)
class Underlying:
    underlying_id: int
    code: str
    name: str
    category: UnderlyingCategory
    unit: str | None
    data_source: str | None
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class UnderlyingPrice:
    underlying_id: int
    as_of: date
    spot: Decimal


@dataclass(frozen=True)
class ThesisUnderlying:
    thesis_id: int
    underlying_id: int
    code: str          # denormalised for caller convenience
    exposure: Decimal  # [0, 1]
    direction: UnderlyingDirection
    last_validated_at: date | None


@dataclass(frozen=True)
class UnderlyingScore:
    """Attribution score for a single thesis's underlying basket."""
    label: str              # 'confirming' | 'mixed' | 'diverging'
    weighted_movement: Decimal   # exposure-weighted, direction-signed 5d move
    component_moves: tuple[dict[str, Any], ...]  # per-underlying breakdown for display
