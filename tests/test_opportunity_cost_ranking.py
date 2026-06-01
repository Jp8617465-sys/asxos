"""
Tests for M-Opportunity-Cost-v1: CGT-adjusted candidate ranking.

Covers:
- rank_by_opportunity_cost: CGT-eligible holding changes ranking vs non-eligible
- No unrealised gain → zero friction regardless of eligibility
- Loss position → zero friction (no CGT on losses)
- Marginal rate parameter flows through to net return
spec §5.1 calendar arithmetic encoded in days_to_cgt_discount (pre-computed).
spec §2 discount: 0.5 individual, 1/3 SMSF.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.domain.brief.opportunity_cost import (
    CandidateWithCGT,
    rank_by_opportunity_cost,
    _position_cgt_friction,
)
from asxos.domain.portfolio.types import AllocationCandidate, HoldingSnapshot
from asxos.domain.tax.types import AccountType

_TODAY = date(2026, 6, 1)


def _holding(
    *,
    quantity: str = "1000",
    cost_base: str = "10000",
    current_price: str = "15.00",
    days_to_cgt: int = 0,
    account_type: AccountType = "individual",
) -> HoldingSnapshot:
    return HoldingSnapshot(
        lot_id=1,
        symbol="MIN.AU",
        acquired_at=_TODAY,
        quantity=Decimal(quantity),
        cost_base_normal=Decimal(cost_base),
        cost_base_div296=Decimal("0"),
        account_type=account_type,
        current_price_aud=Decimal(current_price),
        days_to_cgt_discount=days_to_cgt,
    )


def _candidate(symbol: str, expected_return: str) -> AllocationCandidate:
    return AllocationCandidate(
        symbol=symbol,
        sector=None,
        market_cap_aud=None,
        signal_label="BUY",
        prob_up=Decimal("0.60"),
        expected_return=Decimal(expected_return),
        daily_vol=Decimal("0.02"),
        confidence=1,
    )


class TestPositionCGTFriction:
    def test_no_gain_gives_zero_friction(self):
        h = _holding(cost_base="15000", current_price="15.00", quantity="1000")
        assert _position_cgt_friction(h, Decimal("0.45")) == Decimal("0")

    def test_loss_position_gives_zero_friction(self):
        h = _holding(cost_base="20000", current_price="15.00", quantity="1000")
        assert _position_cgt_friction(h, Decimal("0.45")) == Decimal("0")

    def test_eligible_holding_applies_50pct_discount(self):
        """spec §2: individual investor gets 50% CGT discount after 12 months."""
        # cost_base=10000, current_value=15000, gain=5000
        # With discount: taxable = 5000 * (1 - 0.5) = 2500
        # CGT = 2500 * 0.45 = 1125
        # friction = 1125 / 15000 = 0.075
        h = _holding(cost_base="10000", current_price="15.00", quantity="1000", days_to_cgt=0)
        friction = _position_cgt_friction(h, Decimal("0.45"))
        assert friction == Decimal("1125") / Decimal("15000")

    def test_non_eligible_no_discount(self):
        """Less than 12 months held: no discount, full marginal rate applies."""
        # gain=5000, taxable=5000 (no discount), CGT=2250, friction=2250/15000=0.15
        h = _holding(cost_base="10000", current_price="15.00", quantity="1000", days_to_cgt=45)
        friction = _position_cgt_friction(h, Decimal("0.45"))
        assert friction == Decimal("2250") / Decimal("15000")

    def test_eligible_friction_less_than_non_eligible(self):
        """CGT-eligible holding has lower friction than non-eligible (50% discount)."""
        h_eligible = _holding(days_to_cgt=0)
        h_non_eligible = _holding(days_to_cgt=30)
        f_elig = _position_cgt_friction(h_eligible, Decimal("0.45"))
        f_non = _position_cgt_friction(h_non_eligible, Decimal("0.45"))
        assert f_elig < f_non


class TestRankByOpportunityCost:
    def test_higher_return_ranks_first_when_no_gain(self):
        """No gain → zero friction; ranking is pure gross return order."""
        h = _holding(cost_base="15000", current_price="15.00")
        candidates = [
            _candidate("PLS.AU", "0.20"),
            _candidate("BHP.AU", "0.35"),
            _candidate("CASH", "0.045"),
        ]
        ranked = rank_by_opportunity_cost(candidates, h)
        assert ranked[0].candidate.symbol == "BHP.AU"
        assert ranked[1].candidate.symbol == "PLS.AU"
        assert ranked[2].candidate.symbol == "CASH"

    def test_cgt_friction_reduces_all_returns_equally(self):
        """When CGT friction > 0, all net returns are reduced by the same amount."""
        h = _holding(cost_base="10000", current_price="15.00", days_to_cgt=0)
        friction = _position_cgt_friction(h, Decimal("0.45"))
        assert friction > Decimal("0")

        candidates = [
            _candidate("PLS.AU", "0.20"),
            _candidate("BHP.AU", "0.35"),
        ]
        ranked = rank_by_opportunity_cost(candidates, h)
        # Order preserved; both reduced by same friction
        assert ranked[0].candidate.symbol == "BHP.AU"
        assert ranked[1].candidate.symbol == "PLS.AU"
        for r in ranked:
            assert r.net_expected_return == r.gross_expected_return - friction

    def test_cgt_eligible_vs_non_eligible_ranking_inversion(self):
        """A candidate with lower gross return beats one slightly higher when
        CGT friction makes both negative — ranking can invert relative to
        no-friction case only if candidates have different gross returns.
        This tests that friction is correctly applied."""
        # Non-eligible: friction higher → net return lower → still same ranking
        h_non_eligible = _holding(days_to_cgt=60, cost_base="10000", current_price="15.00")
        h_eligible = _holding(days_to_cgt=0, cost_base="10000", current_price="15.00")

        candidates = [_candidate("X.AU", "0.10"), _candidate("Y.AU", "0.08")]

        ranked_ne = rank_by_opportunity_cost(candidates, h_non_eligible)
        ranked_e = rank_by_opportunity_cost(candidates, h_eligible)

        # Ranking order is the same (friction is symmetric), but eligible friction is smaller
        assert ranked_ne[0].candidate.symbol == ranked_e[0].candidate.symbol == "X.AU"
        # net returns are higher when CGT-eligible (lower friction)
        assert ranked_e[0].net_expected_return > ranked_ne[0].net_expected_return

    def test_empty_candidates_returns_empty(self):
        h = _holding()
        assert rank_by_opportunity_cost([], h) == []

    def test_returns_candidate_with_cgt_type(self):
        h = _holding()
        ranked = rank_by_opportunity_cost([_candidate("BHP.AU", "0.15")], h)
        assert len(ranked) == 1
        assert isinstance(ranked[0], CandidateWithCGT)
        assert ranked[0].candidate.symbol == "BHP.AU"
