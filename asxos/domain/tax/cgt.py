"""
CGT discount eligibility + s 102-5 net capital gain.

Strict spec compliance:
- §5.1 the 12-month rule uses calendar arithmetic, never day-count.
- §5.2 optimal loss ordering — non-discount gains first, then discount.
- §2 individual discount 0.5, SMSF discount 1/3 (exact fraction).

All Decimal in/out. No I/O.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from dateutil.relativedelta import relativedelta

from asxos.domain.tax.types import (
    AccountType,
    CapitalGain,
    NetCapitalGain,
)


def is_discountable(acquisition_date: date, disposal_date: date) -> bool:
    """
    spec §5.1: A CGT event must occur on or after the day one year and one
    day after acquisition. Calendar arithmetic — `(disposal - acquisition).days
    >= 365` is forbidden by the spec.
    """
    earliest_qualifying = acquisition_date + relativedelta(years=1) + timedelta(days=1)
    return disposal_date >= earliest_qualifying


def days_to_eligibility(acquisition_date: date, today: date | None = None) -> int:
    """Returns 0 once eligible, otherwise the days until the earliest qualifying disposal."""
    today = today or date.today()
    earliest_qualifying = acquisition_date + relativedelta(years=1) + timedelta(days=1)
    return max(0, (earliest_qualifying - today).days)


def cgt_discount_rate(account_type: AccountType) -> Decimal:
    """spec §2 — 0.5 individual, 1/3 SMSF (exact)."""
    if account_type == "smsf":
        f = Fraction(1, 3)
        return Decimal(f.numerator) / Decimal(f.denominator)
    return Decimal("0.5")


def net_capital_gain(
    gains: list[CapitalGain],
    *,
    current_year_losses: Decimal,
    carried_forward_losses: Decimal,
    account_type: AccountType,
) -> NetCapitalGain:
    """
    Implements the s 102-5 optimal ordering (spec §5.2):
      Step 1: apply losses against non-discount gains first.
      Step 2: apply remainder against discount gains.
      Step 3: apply the s 115-100 discount to the post-loss discount remainder.
      Step 4: any remaining loss is carried forward (spec §5.2 Step 4).

    `current_year_losses` and `carried_forward_losses` are positive numbers
    (magnitudes), per the spec's input convention.
    """
    if current_year_losses < 0 or carried_forward_losses < 0:
        raise ValueError("loss inputs must be non-negative magnitudes")

    nd_gains = [g for g in gains if not g.discountable and g.gain_aud > 0]
    d_gains = [g for g in gains if g.discountable and g.gain_aud > 0]

    nd_total = sum((g.gain_aud for g in nd_gains), Decimal("0"))
    d_total = sum((g.gain_aud for g in d_gains), Decimal("0"))

    # Realised losses inside the gains list aggregate into current_year_losses.
    in_period_losses = sum(
        (-g.gain_aud for g in gains if g.gain_aud < 0), Decimal("0")
    )
    remaining_loss = current_year_losses + carried_forward_losses + in_period_losses

    # Step 1: apply to non-discount first (the optimal ordering).
    applied_nd = min(nd_total, remaining_loss)
    nd_remainder = nd_total - applied_nd
    remaining_loss -= applied_nd

    # Step 2: apply remainder to discount gains.
    applied_d = min(d_total, remaining_loss)
    d_remainder = d_total - applied_d
    remaining_loss -= applied_d

    # Step 3: apply discount.
    discount_rate = cgt_discount_rate(account_type)
    discount_applied = d_remainder * discount_rate
    post_discount_d = d_remainder - discount_applied

    net_gain = nd_remainder + post_discount_d
    net_loss_cf = remaining_loss

    return NetCapitalGain(
        nd_remainder=nd_remainder,
        d_remainder_pre_discount=d_remainder,
        discount_applied=discount_applied,
        net_capital_gain=net_gain,
        net_capital_loss_cf=net_loss_cf,
    )


def cgt_break_even_price(
    current_price: Decimal,
    cost_usd: Decimal,
    account_type: str,
    acquired: date,
    as_of: date,
    marginal_rate: Decimal = Decimal("0.45"),
) -> Decimal | None:
    """
    Minimum sale price to break even after CGT vs waiting for the 50% discount.

    Formula (spec §2 + §5.1):
        P_sell = [P * (1 - r*d) - cost * r*d] / (1 - r)

    where d = CGT discount fraction (0.5 individual, 1/3 SMSF), r = marginal rate.

    Returns None if: already CGT-eligible, no unrealised gain, or formula
    produces a result below cost (degenerate: tiny gain, very high rate).
    spec §5.1 calendar arithmetic via days_to_eligibility().
    """
    if days_to_eligibility(acquired, as_of) == 0:
        return None
    if current_price <= cost_usd:
        return None
    discount = cgt_discount_rate(account_type)  # type: ignore[arg-type]  # str narrows to AccountType at runtime
    denominator = Decimal("1") - marginal_rate
    if denominator <= 0:
        return None
    numerator = current_price * (Decimal("1") - marginal_rate * discount) - cost_usd * marginal_rate * discount
    result = (numerator / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return result if result > cost_usd else None
