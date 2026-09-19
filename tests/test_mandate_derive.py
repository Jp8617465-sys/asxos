"""The v1 derivation reproduces P5-01 §3's recommended values from a stated
goals row, and says ETF-only where single names cannot honour the cap."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.mandate import Goals, LiquidityNeed, Mandate, derive
from asxos.domain.mandate.derive import SINGLE_NAME_SLEEVE_IDS


def _goals(**over: object) -> Goals:
    base: dict[str, object] = {
        "as_of": date(2026, 9, 19),
        "investable_assets_aud": Decimal("25000"),
        "income_aud_pa": Decimal("120000"),
        "savings_aud_pa": Decimal("30000"),
        "target_wealth_aud": Decimal("1000000"),
        "horizon_years": 10,
        "drawdown_tolerance_pct": Decimal("25"),
        "liquidity_needs": (),
        "emergency_months": 0,
        "account_type": "individual",
        "marginal_rate_pct": Decimal("37"),
        "brokerage_aud_per_side": Decimal("5"),
    }
    base.update(over)
    return Goals(**base)  # type: ignore[arg-type]


def test_c1_paper_book_reproduces_p5_01_recommended_values() -> None:
    """A$25k, A$5 brokerage → the numbers p5-01-risk-calibration §3 recommends."""
    m = derive(_goals())
    o = m.outputs
    assert o.deployable_capital_aud.value == Decimal("25000")
    assert o.cash_floor_pct.value == Decimal("7.5")            # C7 / D1
    assert o.min_position_aud.value == Decimal("1000")         # C1 arithmetic
    assert o.n_single_feasible.value == Decimal("20")          # balanced ≈ 20
    assert o.position_cap_pct.value == Decimal("10")           # C4
    assert o.equal_weight_pct.value == Decimal("4.625")        # 92.5 / 20
    assert o.stop_band_pct.value == Decimal("25")              # C3
    assert o.risk_per_position_pct.value == Decimal("2")       # C2
    assert o.portfolio_dd_review_pct.value == Decimal("25")    # C5, reporting-only
    assert o.structure == "etf_core_plus_sleeves"
    assert o.etf_core_pct.value == Decimal("30")               # contributions > 25 % of deployable
    assert tuple(a.sleeve_id for a in o.sleeve_allocations) == SINGLE_NAME_SLEEVE_IDS
    assert {a.weight_pct for a in o.sleeve_allocations} == {Decimal("17.5")}


def test_live_book_capital_is_etf_only() -> None:
    """A$7,749 at A$1,000 minimums holds 7 names; a 10 % cap needs 10 → ETF-only.

    This is capability-atlas D-6 (caps mutually unsatisfiable) stated as a
    mandate output instead of a hard-fail in the constraint waterfall.
    """
    o = derive(_goals(investable_assets_aud=Decimal("7749.54"))).outputs
    assert o.n_single_feasible.value == Decimal("0")
    assert "infeasible" in o.n_single_feasible.traced_to
    assert o.structure == "etf_only"
    assert o.etf_core_pct.value == Decimal("100")
    assert o.sleeve_allocations == ()
    assert o.equal_weight_pct.value == Decimal("0")


def test_retail_brokerage_raises_the_minimum_position_and_can_remove_single_names() -> None:
    """A$15 a side → A$3,000 minimum (round trip ≤ 1 %) → 7 names on A$25k → ETF-only."""
    o = derive(_goals(brokerage_aud_per_side=Decimal("15"))).outputs
    assert o.min_position_aud.value == Decimal("3000")
    assert o.structure == "etf_only"


def test_a_material_liquidity_call_raises_the_cash_floor_and_shrinks_the_book() -> None:
    need = LiquidityNeed(due=date(2027, 6, 30), amount_aud=Decimal("10000"), label="car")
    o = derive(_goals(liquidity_needs=(need,))).outputs
    assert o.liquidity_reserve_aud.value == Decimal("10000")
    assert o.deployable_capital_aud.value == Decimal("15000")
    assert o.cash_floor_pct.value == Decimal("10")             # D1 §1.1(b)
    assert o.n_single_feasible.value == Decimal("13")          # floor(13,500 / 1,000); ≥ ceil(90/10)=9
    assert o.etf_core_pct.value == Decimal("35")               # 100 × (1 − 13/20) beats the 30 floor
    assert o.structure == "etf_core_plus_sleeves"


def test_a_call_beyond_three_years_is_not_reserved() -> None:
    far = LiquidityNeed(due=date(2030, 1, 1), amount_aud=Decimal("50000"), label="later")
    o = derive(_goals(liquidity_needs=(far,))).outputs
    assert o.liquidity_reserve_aud.value == Decimal("0")


def test_low_drawdown_tolerance_elevates_the_floor() -> None:
    o = derive(_goals(drawdown_tolerance_pct=Decimal("15"))).outputs
    assert o.cash_floor_pct.value == Decimal("10")             # D1 §1.1(a)


def test_emergency_months_reserve_spending_not_income() -> None:
    o = derive(_goals(emergency_months=6)).outputs
    # (120,000 − 30,000) / 12 × 6 = 45,000 > investable → deployable 0, ETF-only, nothing to hold.
    assert o.liquidity_reserve_aud.value == Decimal("45000")
    assert o.deployable_capital_aud.value == Decimal("0")
    assert o.structure == "etf_only"


def test_allocations_always_sum_to_one_hundred_and_every_figure_is_traced() -> None:
    for investable in ("7749.54", "25000", "50000", "100000", "250000"):
        o = derive(_goals(investable_assets_aud=Decimal(investable))).outputs
        total = o.etf_core_pct.value + sum((a.weight_pct for a in o.sleeve_allocations), Decimal("0"))
        assert total == Decimal("100"), investable
        for name, value in o:
            if hasattr(value, "traced_to"):
                assert value.traced_to.strip(), name


def test_same_goals_same_hash_and_the_goals_hash_is_carried() -> None:
    g = _goals()
    a, b = derive(g), derive(g)
    assert a.content_hash == b.content_hash
    assert a.goals_content_hash == g.content_hash
    assert isinstance(a, Mandate) and a.derivation_version == "v1"


def test_float_input_is_refused_and_savings_cannot_exceed_income() -> None:
    with pytest.raises(ValueError, match="float"):
        Goals(**{**_goals().model_dump(exclude={"content_hash"}), "investable_assets_aud": 25000.0})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="savings"):
        _goals(savings_aud_pa=Decimal("130000"))
