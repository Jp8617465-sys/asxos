"""
Tests for M13.3: allocator core and volatility.

Coverage targets (plan I.10): ≥85% on allocator.py and volatility.py.

Covers:
- position_count_for: anchor values, linear interpolation, clamping
- filter_buy_universe: signal label, sector exclusion, symbol exclusion,
  market-cap filter, None market-cap, zero-vol exclusion
- rank_candidates: composite z-score ordering, tiebreak by confidence,
  tiebreak by symbol, custom score weights, single-candidate edge case
- inverse_vol_weights: sum-to-one, lower-vol → higher-weight, empty list,
  zero-vol hard-fail
- allocate: weight sum equals target_sum, position count, empty-universe hard-fail
- annualised_vol_from_prices: known input (constant prices → 0 vol),
  positive vol, window_days cap, short-history hard-fail, non-positive close
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.allocator import (
    allocate,
    filter_buy_universe,
    inverse_vol_weights,
    position_count_for,
    rank_candidates,
)
from asxos.domain.portfolio.types import (
    DEFAULT_SCORE_WEIGHTS,
    RISK_TOLERANCE_SCALARS,
    AllocationCandidate,
    Profile,
)
from asxos.domain.portfolio.volatility import annualised_vol_from_prices

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TODAY = date(2026, 5, 23)


def _make_profile(
    risk_tolerance: str = "balanced",
    capital_aud: Decimal = Decimal("500000"),
    cash_floor_pct: Decimal = Decimal("0.05"),
    leverage_cap: Decimal = Decimal("1.0"),
    excluded_sectors: tuple[str, ...] = (),
    excluded_symbols: tuple[str, ...] = (),
    score_weights: dict[str, Decimal] | None = None,
) -> Profile:
    scalar = RISK_TOLERANCE_SCALARS[risk_tolerance]
    return Profile(
        profile_id=1,
        name="test",
        is_active=True,
        account_type="individual",
        risk_tolerance=risk_tolerance,  # type: ignore[arg-type]
        risk_tolerance_scalar=scalar,
        capital_aud=capital_aud,
        cash_floor_pct=cash_floor_pct,
        leverage_cap=leverage_cap,
        per_name_cap_pct=Decimal("0.10"),
        sector_cap_pct=Decimal("0.30"),
        excluded_sectors=excluded_sectors,
        excluded_symbols=excluded_symbols,
        min_position_aud=Decimal("1000"),
        horizon_years=10,
        defer_near_boundary_sells=True,
        score_weights_json=score_weights if score_weights is not None else dict(DEFAULT_SCORE_WEIGHTS),
        created_at=_TODAY,
        updated_at=_TODAY,
    )


def _make_candidate(
    symbol: str,
    sector: str | None = "Financials",
    signal_label: str = "BUY",
    prob_up: Decimal = Decimal("0.70"),
    expected_return: Decimal = Decimal("0.05"),
    daily_vol: Decimal = Decimal("0.20"),
    market_cap_aud: Decimal | None = Decimal("100000000"),
    confidence: int = 2,
) -> AllocationCandidate:
    return AllocationCandidate(
        symbol=symbol,
        sector=sector,
        market_cap_aud=market_cap_aud,
        signal_label=signal_label,
        prob_up=prob_up,
        expected_return=expected_return,
        daily_vol=daily_vol,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# position_count_for — anchor values
# ---------------------------------------------------------------------------


def test_position_count_conservative():
    assert position_count_for(Decimal("0.25")) == 30


def test_position_count_balanced():
    assert position_count_for(Decimal("0.50")) == 20


def test_position_count_growth():
    assert position_count_for(Decimal("0.75")) == 15


def test_position_count_aggressive():
    assert position_count_for(Decimal("1.00")) == 10


# ---------------------------------------------------------------------------
# position_count_for — linear interpolation between anchors
# ---------------------------------------------------------------------------


def test_position_count_interpolation_mid_conservative_balanced():
    # Midpoint of [0.25, 0.50]: expected = round(30 + 0.5*(20-30)) = 25
    assert position_count_for(Decimal("0.375")) == 25


def test_position_count_interpolation_mid_balanced_growth():
    # Midpoint of [0.50, 0.75]: expected = round(20 + 0.5*(15-20)) = round(17.5) = 18
    assert position_count_for(Decimal("0.625")) == 18


def test_position_count_interpolation_mid_growth_aggressive():
    # Midpoint of [0.75, 1.00]: expected = round(15 + 0.5*(10-15)) = round(12.5) = 12 or 13
    n = position_count_for(Decimal("0.875"))
    assert 12 <= n <= 13


# ---------------------------------------------------------------------------
# position_count_for — clamping at edges
# ---------------------------------------------------------------------------


def test_position_count_clamp_below_min():
    assert position_count_for(Decimal("0.10")) == 30


def test_position_count_clamp_above_max():
    assert position_count_for(Decimal("1.50")) == 10


def test_position_count_always_at_least_one():
    # Clamping must never produce < 1.
    for s in ["0.00", "0.25", "0.50", "0.75", "1.00", "2.00"]:
        assert position_count_for(Decimal(s)) >= 1


# ---------------------------------------------------------------------------
# filter_buy_universe — signal label filter
# ---------------------------------------------------------------------------


def test_filter_keeps_strong_buy():
    c = _make_candidate("AAA", signal_label="STRONG_BUY")
    assert filter_buy_universe([c], (), ()) == [c]


def test_filter_keeps_buy():
    c = _make_candidate("AAA", signal_label="BUY")
    assert filter_buy_universe([c], (), ()) == [c]


def test_filter_drops_hold():
    c = _make_candidate("AAA", signal_label="HOLD")
    assert filter_buy_universe([c], (), ()) == []


def test_filter_drops_sell():
    c = _make_candidate("AAA", signal_label="SELL")
    assert filter_buy_universe([c], (), ()) == []


def test_filter_drops_strong_sell():
    c = _make_candidate("AAA", signal_label="STRONG_SELL")
    assert filter_buy_universe([c], (), ()) == []


def test_filter_mixed_signals():
    candidates = [
        _make_candidate("AAA", signal_label="STRONG_BUY"),
        _make_candidate("BBB", signal_label="BUY"),
        _make_candidate("CCC", signal_label="HOLD"),
        _make_candidate("DDD", signal_label="SELL"),
    ]
    result = filter_buy_universe(candidates, (), ())
    assert [c.symbol for c in result] == ["AAA", "BBB"]


# ---------------------------------------------------------------------------
# filter_buy_universe — sector exclusion
# ---------------------------------------------------------------------------


def test_filter_excludes_named_sector():
    candidates = [
        _make_candidate("AAA", sector="Materials"),
        _make_candidate("BBB", sector="Financials"),
    ]
    result = filter_buy_universe(candidates, ("Materials",), ())
    assert [c.symbol for c in result] == ["BBB"]


def test_filter_none_sector_passes_through():
    # A None sector is NOT excluded by the sector filter.
    c = _make_candidate("AAA", sector=None)
    result = filter_buy_universe([c], ("Materials",), ())
    assert result == [c]


# ---------------------------------------------------------------------------
# filter_buy_universe — symbol exclusion
# ---------------------------------------------------------------------------


def test_filter_excludes_named_symbol():
    candidates = [_make_candidate("AAA"), _make_candidate("BBB")]
    result = filter_buy_universe(candidates, (), ("AAA",))
    assert [c.symbol for c in result] == ["BBB"]


# ---------------------------------------------------------------------------
# filter_buy_universe — market-cap filter
# ---------------------------------------------------------------------------


def test_filter_excludes_small_cap():
    candidates = [
        _make_candidate("AAA", market_cap_aud=Decimal("1000000")),   # 1M < 50M
        _make_candidate("BBB", market_cap_aud=Decimal("100000000")), # 100M ≥ 50M
    ]
    result = filter_buy_universe(candidates, (), ())
    assert [c.symbol for c in result] == ["BBB"]


def test_filter_excludes_none_market_cap():
    candidates = [
        _make_candidate("AAA", market_cap_aud=None),
        _make_candidate("BBB"),
    ]
    result = filter_buy_universe(candidates, (), ())
    assert [c.symbol for c in result] == ["BBB"]


def test_filter_custom_min_market_cap():
    candidates = [
        _make_candidate("AAA", market_cap_aud=Decimal("200000000")),
        _make_candidate("BBB", market_cap_aud=Decimal("50000000")),
    ]
    result = filter_buy_universe(candidates, (), (), min_market_cap_aud=Decimal("100000000"))
    assert [c.symbol for c in result] == ["AAA"]


# ---------------------------------------------------------------------------
# filter_buy_universe — zero vol excluded
# ---------------------------------------------------------------------------


def test_filter_excludes_zero_vol():
    c = _make_candidate("AAA", daily_vol=Decimal("0"))
    assert filter_buy_universe([c], (), ()) == []


# ---------------------------------------------------------------------------
# rank_candidates — composite z-score ordering
# ---------------------------------------------------------------------------


def test_rank_orders_by_prob_up():
    # Higher prob_up → higher z_p → higher composite.
    a = _make_candidate("AAA", prob_up=Decimal("0.90"), expected_return=Decimal("0.05"))
    b = _make_candidate("BBB", prob_up=Decimal("0.60"), expected_return=Decimal("0.05"))
    ranked = rank_candidates([b, a])
    assert ranked[0].symbol == "AAA"


def test_rank_orders_by_expected_return_when_prob_equal():
    a = _make_candidate("AAA", prob_up=Decimal("0.70"), expected_return=Decimal("0.10"))
    b = _make_candidate("BBB", prob_up=Decimal("0.70"), expected_return=Decimal("0.02"))
    ranked = rank_candidates([b, a])
    assert ranked[0].symbol == "AAA"


# ---------------------------------------------------------------------------
# rank_candidates — tiebreakers
# ---------------------------------------------------------------------------


def test_rank_tiebreak_confidence_desc():
    # Same prob_up and expected_return → composite = 0 for all → tiebreak by confidence.
    a = _make_candidate("AAA", prob_up=Decimal("0.70"), expected_return=Decimal("0.05"), confidence=3)
    b = _make_candidate("BBB", prob_up=Decimal("0.70"), expected_return=Decimal("0.05"), confidence=1)
    ranked = rank_candidates([b, a])
    assert ranked[0].symbol == "AAA"  # higher confidence first


def test_rank_tiebreak_symbol_asc():
    # Equal composite and confidence → alphabetical symbol order.
    a = _make_candidate("AAA", prob_up=Decimal("0.70"), expected_return=Decimal("0.05"), confidence=2)
    b = _make_candidate("BBB", prob_up=Decimal("0.70"), expected_return=Decimal("0.05"), confidence=2)
    ranked = rank_candidates([b, a])
    assert ranked[0].symbol == "AAA"


# ---------------------------------------------------------------------------
# rank_candidates — edge cases
# ---------------------------------------------------------------------------


def test_rank_single_candidate():
    c = _make_candidate("AAA")
    ranked = rank_candidates([c])
    assert ranked == [c]


def test_rank_empty_list():
    assert rank_candidates([]) == []


def test_rank_custom_score_weights():
    # With weight 1.0 on expected_return, higher expected_return wins even if prob_up is lower.
    a = _make_candidate("AAA", prob_up=Decimal("0.60"), expected_return=Decimal("0.20"))
    b = _make_candidate("BBB", prob_up=Decimal("0.90"), expected_return=Decimal("0.01"))
    weights = {"prob_up": Decimal("0.0"), "expected_return": Decimal("1.0")}
    ranked = rank_candidates([b, a], score_weights=weights)
    assert ranked[0].symbol == "AAA"


# ---------------------------------------------------------------------------
# inverse_vol_weights — sum and ordering
# ---------------------------------------------------------------------------


def test_inv_vol_weights_sum_to_one():
    candidates = [
        _make_candidate("AAA", daily_vol=Decimal("0.20")),
        _make_candidate("BBB", daily_vol=Decimal("0.30")),
        _make_candidate("CCC", daily_vol=Decimal("0.25")),
    ]
    weights = inverse_vol_weights(candidates)
    total = sum(weights, Decimal("0"))
    assert abs(total - Decimal("1")) < Decimal("1e-10")


def test_inv_vol_weights_lower_vol_gets_higher_weight():
    a = _make_candidate("AAA", daily_vol=Decimal("0.10"))
    b = _make_candidate("BBB", daily_vol=Decimal("0.50"))
    weights = inverse_vol_weights([a, b])
    assert weights[0] > weights[1]


def test_inv_vol_weights_equal_vol_equal_weight():
    candidates = [
        _make_candidate("AAA", daily_vol=Decimal("0.20")),
        _make_candidate("BBB", daily_vol=Decimal("0.20")),
    ]
    weights = inverse_vol_weights(candidates)
    assert weights[0] == weights[1]


def test_inv_vol_weights_empty_list():
    assert inverse_vol_weights([]) == []


def test_inv_vol_weights_zero_vol_raises():
    c = _make_candidate("AAA", daily_vol=Decimal("0"))
    with pytest.raises(ValueError, match="vol > 0"):
        inverse_vol_weights([c])


def test_inv_vol_weights_preserves_order():
    candidates = [
        _make_candidate("AAA", daily_vol=Decimal("0.10")),
        _make_candidate("BBB", daily_vol=Decimal("0.50")),
        _make_candidate("CCC", daily_vol=Decimal("0.25")),
    ]
    weights = inverse_vol_weights(candidates)
    # AAA (lowest vol) should have highest weight; BBB (highest vol) lowest.
    assert weights[0] > weights[2] > weights[1]


# ---------------------------------------------------------------------------
# allocate — end-to-end
# ---------------------------------------------------------------------------


def test_allocate_weights_sum_to_target_sum():
    # balanced (20 positions), cash_floor=0.05, leverage=1.0 → target_sum=0.95
    profile = _make_profile(cash_floor_pct=Decimal("0.05"), leverage_cap=Decimal("1.0"))
    candidates = [
        _make_candidate(f"S{i:02d}", daily_vol=Decimal(str(0.20 + i * 0.01)))
        for i in range(25)
    ]
    targets = allocate(candidates=candidates, profile=profile)
    total = sum(t.target_weight for t in targets)
    expected = Decimal("1.0") - Decimal("0.05")
    assert abs(total - expected) < Decimal("1e-8")


def test_allocate_respects_position_count_aggressive():
    profile = _make_profile(risk_tolerance="aggressive")  # 10 positions
    candidates = [_make_candidate(f"S{i:02d}") for i in range(25)]
    targets = allocate(candidates=candidates, profile=profile)
    assert len(targets) == 10


def test_allocate_respects_position_count_conservative():
    profile = _make_profile(risk_tolerance="conservative")  # 30 positions
    candidates = [_make_candidate(f"S{i:02d}") for i in range(35)]
    targets = allocate(candidates=candidates, profile=profile)
    assert len(targets) == 30


def test_allocate_capped_by_universe_size():
    # Fewer candidates than position count → return all.
    profile = _make_profile(risk_tolerance="aggressive")  # 10 positions
    candidates = [_make_candidate(f"S{i:02d}") for i in range(5)]
    targets = allocate(candidates=candidates, profile=profile)
    assert len(targets) == 5


def test_allocate_empty_universe_raises():
    profile = _make_profile()
    candidates = [_make_candidate("AAA", signal_label="HOLD")]
    with pytest.raises(RuntimeError, match="no investable universe"):
        allocate(candidates=candidates, profile=profile)


def test_allocate_respects_sector_exclusion():
    profile = _make_profile(excluded_sectors=("Energy",))
    candidates = [
        _make_candidate("BHP", sector="Materials"),
        _make_candidate("WPL", sector="Energy"),
    ]
    targets = allocate(candidates=candidates, profile=profile)
    symbols = {t.symbol for t in targets}
    assert "WPL" not in symbols
    assert "BHP" in symbols


def test_allocate_inv_vol_score_stored():
    profile = _make_profile()
    c = _make_candidate("AAA", daily_vol=Decimal("0.25"))
    targets = allocate(candidates=[c], profile=profile)
    assert len(targets) == 1
    expected_score = Decimal("1") / Decimal("0.25")
    assert targets[0].inv_vol_score == expected_score


def test_allocate_leverage_increases_target_sum():
    # leverage_cap=2.0, cash_floor=0.05 → target_sum=1.95
    profile = _make_profile(leverage_cap=Decimal("2.0"), cash_floor_pct=Decimal("0.05"))
    candidates = [_make_candidate(f"S{i:02d}") for i in range(5)]
    targets = allocate(candidates=candidates, profile=profile)
    total = sum(t.target_weight for t in targets)
    expected = Decimal("2.0") - Decimal("0.05")
    assert abs(total - expected) < Decimal("1e-8")


def test_allocate_constraint_log_empty():
    profile = _make_profile()
    candidates = [_make_candidate("AAA")]
    targets = allocate(candidates=candidates, profile=profile)
    assert targets[0].constraint_log == {}


# ---------------------------------------------------------------------------
# annualised_vol_from_prices — known inputs
# ---------------------------------------------------------------------------


def test_annualised_vol_constant_prices_returns_zero():
    # All log returns = 0 → std_dev = 0 → vol = 0.
    closes = [Decimal("100")] * 61
    vol = annualised_vol_from_prices(closes)
    assert vol == Decimal("0")


def test_annualised_vol_positive_for_varying_prices():
    # Alternating 100/110 gives non-zero log returns.
    closes = [Decimal("100") if i % 2 == 0 else Decimal("110") for i in range(61)]
    vol = annualised_vol_from_prices(closes)
    assert vol > Decimal("0")


def test_annualised_vol_uses_only_last_window_closes():
    # A long history with a constant prefix + varying suffix should only
    # compute vol on the last (window_days + 1) closes.
    constant = [Decimal("100")] * 200
    varying = [Decimal("100") if i % 2 == 0 else Decimal("110") for i in range(61)]
    closes = constant + varying
    vol_full = annualised_vol_from_prices(closes)
    vol_only_tail = annualised_vol_from_prices(varying)
    # Both computed from the same last 61 closes.
    assert abs(vol_full - vol_only_tail) < Decimal("1e-10")


def test_annualised_vol_exact_minimum_history():
    # Exactly window_days + 1 closes is the minimum; must not raise.
    closes = [Decimal("100")] * 61
    annualised_vol_from_prices(closes, window_days=60)  # no exception


def test_annualised_vol_custom_window():
    closes = [Decimal("100")] * 11
    vol = annualised_vol_from_prices(closes, window_days=10)
    assert vol == Decimal("0")  # constant prices


# ---------------------------------------------------------------------------
# annualised_vol_from_prices — hard-fail conditions
# ---------------------------------------------------------------------------


def test_annualised_vol_short_history_raises():
    closes = [Decimal("100")] * 59  # < 61 required for window_days=60
    with pytest.raises(ValueError, match="insufficient"):
        annualised_vol_from_prices(closes, window_days=60)


def test_annualised_vol_nonpositive_close_raises():
    closes = [Decimal("100")] * 60 + [Decimal("0")]
    with pytest.raises(ValueError, match="> 0"):
        annualised_vol_from_prices(closes)


def test_annualised_vol_negative_close_raises():
    closes = [Decimal("100")] * 60 + [Decimal("-1")]
    with pytest.raises(ValueError, match="> 0"):
        annualised_vol_from_prices(closes)


def test_annualised_vol_window_cap_raises():
    closes = [Decimal("100")] * 300
    with pytest.raises(ValueError, match="252"):
        annualised_vol_from_prices(closes, window_days=253)


def test_annualised_vol_window_at_cap_does_not_raise():
    closes = [Decimal("100")] * 253
    annualised_vol_from_prices(closes, window_days=252)  # 252 is the cap, not exceeded
