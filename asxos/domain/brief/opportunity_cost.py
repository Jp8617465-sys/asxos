"""
CGT-adjusted opportunity-cost ranking — M-Opportunity-Cost-v1.

rank_by_opportunity_cost() sorts redeployment candidates by net-of-CGT
expected return. CGT friction is computed per lot then aggregated to a
position-level fraction.

spec §5.1: CGT discount uses calendar arithmetic (relativedelta), not
day-count. spec §2: individual discount 0.5, SMSF 1/3 (exact fraction).

Caveat (documented in portfolio-conventions.md §loss-harvest tagging):
  - Flat marginal_rate approximation — actual liability depends on full-year
    taxable income, which this system does not model.
  - The ranking is an aid for review, not financial advice (ASXOS_PERSONAL_USE gate).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from asxos.domain.portfolio.types import AllocationCandidate, HoldingSnapshot
from asxos.domain.tax.cgt import cgt_discount_rate


@dataclass(frozen=True)
class CandidateWithCGT:
    """Candidate enriched with CGT friction and net expected return."""
    candidate: AllocationCandidate
    gross_expected_return: Decimal
    estimated_cgt_friction: Decimal  # fraction of position value [0, 1)
    net_expected_return: Decimal


def _position_cgt_friction(
    holding: HoldingSnapshot,
    marginal_rate: Decimal,
) -> Decimal:
    """Compute the CGT tax fraction of current position value.

    Returns a value in [0, 1) representing what fraction of the position's
    current market value would be consumed by CGT on full disposal.

    spec §5.1 calendar arithmetic is already encoded in HoldingSnapshot.days_to_cgt_discount.
    spec §2 discount rates: 0.5 individual, 1/3 SMSF.
    """
    current_value = holding.current_price_aud * holding.quantity
    if current_value <= Decimal("0"):
        return Decimal("0")

    unrealised_gain = current_value - holding.cost_base_normal
    if unrealised_gain <= Decimal("0"):
        return Decimal("0")  # no gain, no friction

    # CGT discount applies when days_to_cgt_discount == 0 (lot already eligible)
    discount = cgt_discount_rate(holding.account_type) if holding.days_to_cgt_discount == 0 else Decimal("0")
    taxable_gain = unrealised_gain * (Decimal("1") - discount)
    cgt_liability = taxable_gain * marginal_rate
    return cgt_liability / current_value


def rank_by_opportunity_cost(
    candidates: list[AllocationCandidate],
    holding: HoldingSnapshot,
    marginal_rate: Decimal = Decimal("0.45"),
) -> list[CandidateWithCGT]:
    """Rank redeployment candidates by net-of-CGT expected return.

    Each candidate's gross expected_return is reduced by the CGT friction of
    exiting the current holding. The friction is the same for all candidates
    (it depends on the holding, not the destination), so the ranking order
    differs from a raw expected_return sort only when the holding has a gain
    vs candidates with similar returns.

    Args:
        candidates:    potential redeployment targets (from watchlist + signals)
        holding:       the position being considered for exit
        marginal_rate: flat approximation; individual top rate 0.45

    Returns:
        candidates sorted by net_expected_return descending
    """
    cgt_friction = _position_cgt_friction(holding, marginal_rate)

    enriched: list[CandidateWithCGT] = []
    for c in candidates:
        gross = c.expected_return
        net = gross - cgt_friction
        # Only surface candidates where redeployment improves after-CGT outcome.
        # A negative net return means CGT cost exceeds expected upside — holding
        # the current position is preferred. Exclude rather than rank at bottom
        # to avoid misleading "best of bad" recommendations.
        if net > Decimal("0"):
            enriched.append(CandidateWithCGT(
                candidate=c,
                gross_expected_return=gross,
                estimated_cgt_friction=cgt_friction,
                net_expected_return=net,
            ))

    return sorted(enriched, key=lambda x: x.net_expected_return, reverse=True)
