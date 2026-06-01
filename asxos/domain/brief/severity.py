"""
Pure severity classification functions — M-Brief-Skeleton.

Each function inspects domain data and returns a SeverityItem or None.
These are called by collectors to produce the items list in SectionResult.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.domain.brief.types import SeverityItem, SeverityLevel


def thesis_revisit_overdue(
    symbol: str,
    revisit_due_at: date,
    as_of: date,
    section: str = "active_theses",
) -> SeverityItem | None:
    """Red if the review deadline has passed."""
    days_overdue = (as_of - revisit_due_at).days
    if days_overdue > 0:
        return SeverityItem(
            level=SeverityLevel.red,
            message=f"{symbol}: review overdue by {days_overdue}d (due {revisit_due_at})",
            section=section,
        )
    return None


def thesis_approaching_target(
    symbol: str,
    current_price: Decimal,
    target_price: Decimal,
    threshold_pct: Decimal = Decimal("5"),
    section: str = "active_theses",
) -> SeverityItem | None:
    """Yellow when current price is within threshold_pct of target."""
    if target_price <= Decimal("0"):
        return None
    gap_pct = (target_price - current_price) / target_price * 100
    if Decimal("0") <= gap_pct <= threshold_pct:
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=(
                f"{symbol}: approaching target {target_price} "
                f"({gap_pct:.1f}% away)"
            ),
            section=section,
        )
    return None


def cgt_boundary_approaching(
    symbol: str,
    lot_id: int,
    days_to_eligibility: int,
    section: str = "tax_operational",
) -> SeverityItem | None:
    """Red if < 7 days to CGT boundary, yellow if 7–30 days, None otherwise."""
    if days_to_eligibility <= 0:
        return None
    if days_to_eligibility <= 7:
        return SeverityItem(
            level=SeverityLevel.red,
            message=f"{symbol} lot #{lot_id}: CGT boundary in {days_to_eligibility}d — do not sell",
            section=section,
        )
    if days_to_eligibility <= 30:
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=f"{symbol} lot #{lot_id}: CGT boundary in {days_to_eligibility}d",
            section=section,
        )
    return None


def regime_warning(
    label: str,
    section: str = "market_context",
) -> SeverityItem | None:
    """Yellow on risk_off_orderly, red on risk_off_disorderly, None otherwise."""
    if label == "risk_off_disorderly":
        return SeverityItem(
            level=SeverityLevel.red,
            message=f"Regime: {label} — high volatility, credit stress",
            section=section,
        )
    if label == "risk_off_orderly":
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=f"Regime: {label} — elevated risk, review positions",
            section=section,
        )
    return None
