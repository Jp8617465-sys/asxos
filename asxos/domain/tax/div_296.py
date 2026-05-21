"""
Division 296 — stacked tier 1 / tier 2 (spec §6).

Both tiers use TSB_ref as the denominator and are applied independently to
the same earnings figure. Tier 1 above $3M at 15%; Tier 2 above $10M at an
additional 10% (combined 25%). The 0.10 in tier 2 is the *additional* rate
above tier 1 — phrasing it as "25% of the slice above $10M" is the effective
rate description, not the legislated mechanism (spec §6.3).
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.types import Div296Outcome

DEFAULT_LSBT = Decimal("3000000")
DEFAULT_VLSBT = Decimal("10000000")
TIER_1_RATE = Decimal("0.15")
TIER_2_RATE = Decimal("0.10")  # additional, on top of tier 1


def div296_liability(
    *,
    tsb_ref: Decimal,
    earnings: Decimal,
    lsbt: Decimal = DEFAULT_LSBT,
    vlsbt: Decimal = DEFAULT_VLSBT,
    is_provisional: bool = False,
) -> Div296Outcome:
    """spec §6.3 — stacked-proportion methodology.

    `tsb_ref`: max(TSB at start of year, TSB at end of year) per s 296-40(2),
    or closing balance for FY 2026-27 under ITTPA s 296-1 (caller controls).
    `earnings`: realised fund taxable income (spec §6.2 — ECPI is ignored
    for Division 296 per Heffron technical note 23 March 2026).
    """
    if earnings <= 0:
        return Div296Outcome(tsb_ref, earnings, lsbt, vlsbt, Decimal("0"), Decimal("0"), Decimal("0"), is_provisional)

    if tsb_ref > lsbt:
        p1 = (tsb_ref - lsbt) / tsb_ref
        tier_1 = earnings * p1 * TIER_1_RATE
    else:
        tier_1 = Decimal("0")

    if tsb_ref > vlsbt:
        p2 = (tsb_ref - vlsbt) / tsb_ref
        tier_2 = earnings * p2 * TIER_2_RATE
    else:
        tier_2 = Decimal("0")

    return Div296Outcome(
        tsb_ref=tsb_ref,
        earnings=earnings,
        lsbt=lsbt,
        vlsbt=vlsbt,
        tier_1=tier_1,
        tier_2=tier_2,
        total=tier_1 + tier_2,
        is_provisional=is_provisional,
    )
