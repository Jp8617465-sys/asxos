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


def earnings_risk(
    symbol: str,
    next_earnings_date: date | None,
    cgt_date: date | None,
    as_of: date,
    section: str = "active_theses",
) -> SeverityItem | None:
    """
    Red: earnings within 14d of CGT discount date (double-risk window).
    Yellow: earnings within 30d of as_of.
    None: no earnings date, earnings already passed, or > 30d away.
    """
    if next_earnings_date is None:
        return None
    days_to_earnings = (next_earnings_date - as_of).days
    if days_to_earnings < 0:
        return None
    if cgt_date is not None and abs((next_earnings_date - cgt_date).days) <= 14:
        return SeverityItem(
            level=SeverityLevel.red,
            message=(
                f"{symbol}: earnings {next_earnings_date} within 14d of CGT discount"
                f" date {cgt_date} — double-risk window"
            ),
            section=section,
        )
    if days_to_earnings <= 30:
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=f"{symbol}: earnings in {days_to_earnings}d ({next_earnings_date})",
            section=section,
        )
    return None


def thesis_timeline_expired(
    symbol: str,
    opened_at: date,
    timeline_days: int | None,
    as_of: date,
    section: str = "active_theses",
) -> SeverityItem | None:
    """Red if timeline has elapsed; yellow if within 14 days of expiry."""
    from datetime import timedelta
    if timeline_days is None:
        return None
    deadline = opened_at + timedelta(days=timeline_days)
    days_remaining = (deadline - as_of).days
    if days_remaining < 0:
        return SeverityItem(
            level=SeverityLevel.red,
            message=(
                f"{symbol}: thesis expired {-days_remaining}d ago"
                f" (deadline {deadline}) — review or close"
            ),
            section=section,
        )
    if days_remaining <= 14:
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=f"{symbol}: thesis expires in {days_remaining}d ({deadline})",
            section=section,
        )
    return None


def portfolio_drawdown(
    capital: Decimal,
    peak_capital: Decimal,
    section: str = "wealth_state",
) -> SeverityItem | None:
    """Yellow if drawdown from high-water mark > 3%; red if > 5%."""
    if peak_capital <= 0 or capital >= peak_capital:
        return None
    drawdown_pct = (peak_capital - capital) / peak_capital * 100
    if drawdown_pct >= Decimal("5"):
        return SeverityItem(
            level=SeverityLevel.red,
            message=(
                f"Portfolio down {drawdown_pct:.1f}% from peak"
                f" (A${peak_capital:,.0f} → A${capital:,.0f})"
            ),
            section=section,
        )
    if drawdown_pct >= Decimal("3"):
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=f"Portfolio drawdown {drawdown_pct:.1f}% from high-water mark",
            section=section,
        )
    return None


def position_concentration(
    symbol: str,
    holding_mv_aud: Decimal,
    total_mv_aud: Decimal,
    section: str = "wealth_state",
) -> SeverityItem | None:
    """Red if a single holding is ≥ 20% of total holdings MV; yellow if ≥ 10%."""
    if total_mv_aud <= 0:
        return None
    pct = holding_mv_aud / total_mv_aud * 100
    if pct >= Decimal("20"):
        return SeverityItem(
            level=SeverityLevel.red,
            message=f"{symbol}: {pct:.1f}% of portfolio — concentrated position",
            section=section,
        )
    if pct >= Decimal("10"):
        return SeverityItem(
            level=SeverityLevel.yellow,
            message=f"{symbol}: {pct:.1f}% of portfolio",
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
