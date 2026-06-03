"""Regime domain types — M-Market-Context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any


class RegimeLabel(StrEnum):
    risk_on_broadening = "risk_on_broadening"
    risk_on_narrowing = "risk_on_narrowing"
    neutral_mixed = "neutral_mixed"
    risk_off_orderly = "risk_off_orderly"
    risk_off_disorderly = "risk_off_disorderly"


@dataclass(frozen=True)
class Condition:
    """One predicate evaluated during regime classification."""
    name: str
    fired: bool
    value: Decimal | None   # actual observed value
    threshold: Decimal | None  # threshold that was tested


@dataclass(frozen=True)
class RegimeSnapshot:
    """Classified regime snapshot for a single as_of date."""
    as_of: date
    label: RegimeLabel
    rationale: tuple[Condition, ...]       # which conditions fired
    ingestion_warnings: tuple[dict[str, Any], ...]   # partial-data flags from ingest
