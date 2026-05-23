"""
Tests for asxos/domain/portfolio/rebalance.py (M13.6).

Coverage targets (plan I.10 — ≥85% on pure modules):
  - current_qty_by_symbol: aggregation, multi-lot, empty
  - compute_deltas: new buy, exited-universe sell, reduction sell,
    drift threshold hold, concentration alarm, §5.1 boundary defer,
    universe-inactive forced sell, missing price, zero price
  - assemble_result: summary counts, deferral classification, AUD totals
  - Integration: full pipeline (allocate → constraints → compute_deltas)
    with the pathological ultra-low-vol convergence case (plan H.1 R3)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.rebalance import (
    assemble_result,
    compute_deltas,
    current_qty_by_symbol,
)
from asxos.domain.portfolio.types import (
    AllocationTarget,
    HoldingSnapshot,
    Profile,
    ProposedTrade,
    RISK_TOLERANCE_SCALARS,
    DEFAULT_SCORE_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date(2026, 5, 23)
_PRICES = {"BHP": Decimal("40"), "CBA": Decimal("100"), "RIO": Decimal("80")}


def make_profile(**kwargs) -> Profile:
    defaults = dict(
        profile_id=1,
        name="test",
        is_active=True,
        account_type="individual",
        risk_tolerance="balanced",
        risk_tolerance_scalar=RISK_TOLERANCE_SCALARS["balanced"],
        capital_aud=Decimal("100000"),
        cash_floor_pct=Decimal("0.05"),
        leverage_cap=Decimal("1"),
        per_name_cap_pct=Decimal("0.10"),
        sector_cap_pct=Decimal("0.30"),
        excluded_sectors=(),
        excluded_symbols=(),
        min_position_aud=Decimal("1000"),
        horizon_years=10,
        defer_near_boundary_sells=True,
        score_weights_json=DEFAULT_SCORE_WEIGHTS,
        created_at=_TODAY,
        updated_at=_TODAY,
    )
    defaults.update(kwargs)
    return Profile(**defaults)


def make_target(
    *,
    symbol: str = "BHP",
    sector: str | None = "Materials",
    target_weight: Decimal = Decimal("0.10"),
    inv_vol_score: Decimal = Decimal("5"),
    signal_label: str = "BUY",
) -> AllocationTarget:
    return AllocationTarget(
        symbol=symbol,
        sector=sector,
        target_weight=target_weight,
        inv_vol_score=inv_vol_score,
        signal_label=signal_label,
        prob_up=Decimal("0.60"),
        expected_return=Decimal("0.05"),
        constraint_log={},
    )


def make_snapshot(
    *,
    lot_id: int = 1,
    symbol: str = "BHP",
    acquired_at: date = date(2024, 1, 1),
    quantity: Decimal = Decimal("100"),
    cost_base_normal: Decimal = Decimal("5000"),
    cost_base_div296: Decimal = Decimal("5000"),
    account_type: str = "individual",
    current_price_aud: Decimal = Decimal("40"),
    days_to_cgt_discount: int = 15,
) -> HoldingSnapshot:
    return HoldingSnapshot(
        lot_id=lot_id,
        symbol=symbol,
        acquired_at=acquired_at,
        quantity=quantity,
        cost_base_normal=cost_base_normal,
        cost_base_div296=cost_base_div296,
        account_type=account_type,
        current_price_aud=current_price_aud,
        days_to_cgt_discount=days_to_cgt_discount,
    )


# ---------------------------------------------------------------------------
# current_qty_by_symbol
# ---------------------------------------------------------------------------


def test_current_qty_by_symbol_empty() -> None:
    assert current_qty_by_symbol([]) == {}


def test_current_qty_by_symbol_single_lot() -> None:
    h = make_snapshot(symbol="BHP", quantity=Decimal("250"))
    result = current_qty_by_symbol([h])
    assert result == {"BHP": Decimal("250")}


def test_current_qty_by_symbol_multi_lot_same_symbol() -> None:
    """Two lots of same symbol → quantities summed."""
    h1 = make_snapshot(lot_id=1, symbol="BHP", quantity=Decimal("100"))
    h2 = make_snapshot(lot_id=2, symbol="BHP", quantity=Decimal("50"))
    result = current_qty_by_symbol([h1, h2])
    assert result == {"BHP": Decimal("150")}


def test_current_qty_by_symbol_multi_symbol() -> None:
    """Each symbol gets its own total."""
    h1 = make_snapshot(lot_id=1, symbol="BHP", quantity=Decimal("100"))
    h2 = make_snapshot(lot_id=2, symbol="CBA", quantity=Decimal("20"))
    result = current_qty_by_symbol([h1, h2])
    assert result["BHP"] == Decimal("100")
    assert result["CBA"] == Decimal("20")


# ---------------------------------------------------------------------------
# compute_deltas — basic trade classification
# ---------------------------------------------------------------------------


def test_compute_deltas_new_buy() -> None:
    """Symbol in targets, not held → buy trade."""
    # target_weight=0.10 × 100000 / 40 = 250 shares
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    result = compute_deltas(
        targets=[target],
        current_qty={},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    assert len(result) == 1
    t = result[0]
    assert t.symbol == "BHP"
    assert t.side == "buy"
    assert t.delta_qty == Decimal("250")
    assert t.current_qty == Decimal("0")
    assert t.target_qty == Decimal("250")


def test_compute_deltas_full_sell_exited_universe() -> None:
    """Held but not in targets → full sell with exited_universe tag."""
    result = compute_deltas(
        targets=[],
        current_qty={"BHP": Decimal("250")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    assert len(result) == 1
    t = result[0]
    assert t.side == "sell"
    assert t.delta_qty == Decimal("-250")
    assert t.rationale_tags.get("reason") == "exited_universe"


def test_compute_deltas_reduction_sell() -> None:
    """Held > target → sell the difference (above drift threshold)."""
    # current: 300 shares @ 40 = 12000; target: 250 @ 40 = 10000; delta=-2000 >> 500 threshold
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("300")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    t = result[0]
    assert t.side == "sell"
    assert t.delta_qty == Decimal("-50")


def test_compute_deltas_increase_buy() -> None:
    """Held < target → buy the difference."""
    # current: 200 @ 40 = 8000; target: 250 @ 40 = 10000; delta=+2000 >> threshold
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("200")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    t = result[0]
    assert t.side == "buy"
    assert t.delta_qty == Decimal("50")


# ---------------------------------------------------------------------------
# compute_deltas — drift threshold
# ---------------------------------------------------------------------------


def test_compute_deltas_drift_threshold_hold() -> None:
    """delta_aud below 0.5% of capital → side='hold'."""
    # capital=100000, threshold=500 AUD
    # current: 250 shares @ 40 = 10000 AUD
    # target: 0.1001 × 100000 = 10010 AUD → delta_aud = +10 < 500 → hold
    target = make_target(symbol="BHP", target_weight=Decimal("0.1001"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("250")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    assert result[0].side == "hold"


def test_compute_deltas_drift_threshold_buy_above() -> None:
    """delta_aud just above drift threshold → side='buy'."""
    # drift = 0.005 × 100000 = 500 AUD
    # target: 0.106 × 100000 = 10600; current: 250 × 40 = 10000; delta=+600 > 500
    target = make_target(symbol="BHP", target_weight=Decimal("0.106"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("250")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    assert result[0].side == "buy"


def test_compute_deltas_drift_custom_threshold() -> None:
    """Custom drift_threshold_pct is respected."""
    # With threshold=0.02 (2%), drift_aud = 2000.
    # delta_aud = +600 < 2000 → hold.
    target = make_target(symbol="BHP", target_weight=Decimal("0.106"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("250")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        drift_threshold_pct=Decimal("0.02"),
    )
    assert result[0].side == "hold"


# ---------------------------------------------------------------------------
# compute_deltas — concentration alarm
# ---------------------------------------------------------------------------


def test_compute_deltas_concentration_alarm_flagged() -> None:
    """target_aud > 10% of capital → concentration_alarm tag on buy."""
    # target_weight=0.15 → 15000 AUD > 10000 (10%)
    target = make_target(symbol="BHP", target_weight=Decimal("0.15"))
    result = compute_deltas(
        targets=[target],
        current_qty={},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    t = result[0]
    assert t.side == "buy"
    assert t.rationale_tags.get("concentration_alarm") is True


def test_compute_deltas_concentration_alarm_not_flagged() -> None:
    """target_aud at exactly 10% → alarm not raised (boundary excluded)."""
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    result = compute_deltas(
        targets=[target],
        current_qty={},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    assert "concentration_alarm" not in result[0].rationale_tags


def test_compute_deltas_concentration_alarm_only_on_buy() -> None:
    """Concentration check applies to buy trades only, not holds."""
    # current = target → hold; no alarm even if > 10%
    target = make_target(symbol="BHP", target_weight=Decimal("0.15"))
    result = compute_deltas(
        targets=[target],
        # current: 375 @ 40 = 15000 = target → delta=0 → hold
        current_qty={"BHP": Decimal("375")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    # delta_aud = 0 < 500 threshold → hold
    assert result[0].side == "hold"
    assert "concentration_alarm" not in result[0].rationale_tags


# ---------------------------------------------------------------------------
# compute_deltas — §5.1 boundary defer
# ---------------------------------------------------------------------------


def test_compute_deltas_boundary_defer_forces_hold() -> None:
    """Sell with near-boundary lot + defer=True → forced hold."""
    # 300 @ 40 = 12000, target 250 @ 40 = 10000, delta=-2000 → sell without defer
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    near_lot = make_snapshot(symbol="BHP", lot_id=7, days_to_cgt_discount=15)
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("300")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        holdings=[near_lot],
        defer_near_boundary_sells=True,
    )
    t = result[0]
    assert t.side == "hold"
    assert 7 in t.rationale_tags["near_boundary_lot_ids"]


def test_compute_deltas_boundary_annotates_when_no_defer() -> None:
    """Sell with near-boundary lot + defer=False → annotated but still sell."""
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    near_lot = make_snapshot(symbol="BHP", lot_id=7, days_to_cgt_discount=15)
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("300")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        holdings=[near_lot],
        defer_near_boundary_sells=False,
    )
    t = result[0]
    assert t.side == "sell"
    assert 7 in t.rationale_tags["near_boundary_lot_ids"]


def test_compute_deltas_already_eligible_lot_no_defer() -> None:
    """Lot with days_to_cgt_discount=0 (already eligible) → no deferral."""
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    eligible_lot = make_snapshot(symbol="BHP", lot_id=3, days_to_cgt_discount=0)
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("300")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        holdings=[eligible_lot],
        defer_near_boundary_sells=True,
    )
    t = result[0]
    assert t.side == "sell"
    assert "near_boundary_lot_ids" not in t.rationale_tags


def test_compute_deltas_no_holdings_no_boundary_check() -> None:
    """With holdings=None, §5.1 check is skipped; sell remains sell."""
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("300")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        holdings=None,
        defer_near_boundary_sells=True,
    )
    assert result[0].side == "sell"
    assert "near_boundary_lot_ids" not in result[0].rationale_tags


# ---------------------------------------------------------------------------
# compute_deltas — universe_inactive forced sell
# ---------------------------------------------------------------------------


def test_compute_deltas_universe_inactive_forced_sell() -> None:
    """Held symbol in universe_inactive → full sell with universe_inactive tag."""
    result = compute_deltas(
        targets=[],
        current_qty={"BHP": Decimal("250")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        universe_inactive_symbols=frozenset({"BHP"}),
    )
    t = result[0]
    assert t.side == "sell"
    assert t.rationale_tags.get("reason") == "universe_inactive"
    assert t.delta_qty == Decimal("-250")  # full liquidation


def test_compute_deltas_universe_inactive_ignores_drift() -> None:
    """Universe-inactive forced-sell ignores the drift threshold."""
    # current ≈ target (drift < threshold normally), but still forced sell
    target = make_target(symbol="BHP", target_weight=Decimal("0.10"))
    result = compute_deltas(
        targets=[target],
        current_qty={"BHP": Decimal("250")},
        prices={"BHP": Decimal("40")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
        universe_inactive_symbols=frozenset({"BHP"}),
    )
    t = result[0]
    assert t.side == "sell"
    assert t.rationale_tags.get("reason") == "universe_inactive"
    assert t.delta_qty == Decimal("-250")


# ---------------------------------------------------------------------------
# compute_deltas — hard-fail cases
# ---------------------------------------------------------------------------


def test_compute_deltas_missing_price_raises() -> None:
    """Missing price for a target symbol → RuntimeError."""
    target = make_target(symbol="BHP")
    with pytest.raises(RuntimeError, match="no reference price for 'BHP'"):
        compute_deltas(
            targets=[target],
            current_qty={},
            prices={},
            capital_aud=Decimal("100000"),
            leverage_cap=Decimal("1"),
        )


def test_compute_deltas_zero_price_raises() -> None:
    """Zero price → RuntimeError."""
    target = make_target(symbol="BHP")
    with pytest.raises(RuntimeError, match="non-positive reference price"):
        compute_deltas(
            targets=[target],
            current_qty={},
            prices={"BHP": Decimal("0")},
            capital_aud=Decimal("100000"),
            leverage_cap=Decimal("1"),
        )


def test_compute_deltas_missing_price_for_held_symbol_raises() -> None:
    """Missing price for a held symbol → RuntimeError."""
    with pytest.raises(RuntimeError, match="no reference price for 'BHP'"):
        compute_deltas(
            targets=[],
            current_qty={"BHP": Decimal("100")},
            prices={},
            capital_aud=Decimal("100000"),
            leverage_cap=Decimal("1"),
        )


# ---------------------------------------------------------------------------
# compute_deltas — deterministic ordering
# ---------------------------------------------------------------------------


def test_compute_deltas_output_is_alphabetical() -> None:
    """Output is sorted alphabetically by symbol."""
    result = compute_deltas(
        targets=[
            make_target(symbol="RIO", target_weight=Decimal("0.05")),
            make_target(symbol="BHP", target_weight=Decimal("0.05")),
            make_target(symbol="CBA", target_weight=Decimal("0.05")),
        ],
        current_qty={},
        prices={"BHP": Decimal("40"), "CBA": Decimal("100"), "RIO": Decimal("80")},
        capital_aud=Decimal("100000"),
        leverage_cap=Decimal("1"),
    )
    assert [t.symbol for t in result] == ["BHP", "CBA", "RIO"]


# ---------------------------------------------------------------------------
# assemble_result
# ---------------------------------------------------------------------------


def _make_trade(symbol: str, side: str, delta_aud: Decimal, tags: dict | None = None) -> ProposedTrade:
    return ProposedTrade(
        symbol=symbol,
        side=side,
        delta_qty=Decimal("10") if side == "buy" else Decimal("-10"),
        delta_aud=delta_aud,
        target_qty=Decimal("10"),
        current_qty=Decimal("0"),
        reference_price=Decimal("100"),
        rationale_tags=tags or {},
        lot_hints={},
    )


def test_assemble_result_summary_counts() -> None:
    """n_buys / n_sells / n_holds counted correctly."""
    profile = make_profile()
    trades = [
        _make_trade("BHP", "buy", Decimal("5000")),
        _make_trade("CBA", "sell", Decimal("-3000")),
        _make_trade("RIO", "hold", Decimal("0")),
    ]
    result = assemble_result(
        profile=profile,
        targets=[make_target()],
        trades=trades,
        as_of=_TODAY,
        signals_as_of=_TODAY,
    )
    s = result.summary
    assert s["n_buys"] == 1
    assert s["n_sells"] == 1
    assert s["n_holds"] == 1
    assert s["n_deferrals"] == 0


def test_assemble_result_deferral_classified() -> None:
    """Hold trades with near_boundary_lot_ids → counted as deferral, not hold."""
    profile = make_profile()
    deferred = _make_trade("BHP", "hold", Decimal("0"), tags={"near_boundary_lot_ids": [1, 2]})
    plain_hold = _make_trade("CBA", "hold", Decimal("0"))
    result = assemble_result(
        profile=profile,
        targets=[],
        trades=[deferred, plain_hold],
        as_of=_TODAY,
        signals_as_of=_TODAY,
    )
    s = result.summary
    assert s["n_deferrals"] == 1
    assert s["n_holds"] == 1


def test_assemble_result_aud_totals() -> None:
    """total_buy_aud and total_sell_aud sum correctly."""
    profile = make_profile()
    trades = [
        _make_trade("BHP", "buy", Decimal("5000")),
        _make_trade("CBA", "buy", Decimal("3000")),
        _make_trade("RIO", "sell", Decimal("-2000")),
    ]
    result = assemble_result(
        profile=profile,
        targets=[],
        trades=trades,
        as_of=_TODAY,
        signals_as_of=_TODAY,
    )
    s = result.summary
    assert s["total_buy_aud"] == Decimal("8000")
    assert s["total_sell_aud"] == Decimal("2000")


def test_assemble_result_run_id_is_none() -> None:
    """run_id is None before persisting."""
    profile = make_profile()
    result = assemble_result(
        profile=profile, targets=[], trades=[],
        as_of=_TODAY, signals_as_of=_TODAY,
    )
    assert result.run_id is None


def test_assemble_result_empty_trades() -> None:
    """All-zero summary for empty trade list."""
    profile = make_profile()
    result = assemble_result(
        profile=profile, targets=[], trades=[],
        as_of=_TODAY, signals_as_of=_TODAY,
    )
    s = result.summary
    assert s["n_buys"] == s["n_sells"] == s["n_holds"] == s["n_deferrals"] == 0
    assert s["total_buy_aud"] == Decimal("0")
    assert s["total_sell_aud"] == Decimal("0")


# ---------------------------------------------------------------------------
# Integration test — full pipeline with pathological convergence (plan H.1 R3)
# ---------------------------------------------------------------------------


def test_end_to_end_pipeline_pathological_convergence() -> None:
    """Full pipeline: allocate → apply_constraints → compute_deltas.

    Uses the ultra-low-vol scenario (plan H.1 R3): one name with an
    inverse-vol score ~20× the others. The constraint waterfall must take
    3+ iterations to settle; this test confirms the pipeline converges and
    produces valid ProposedTrade output.

    This is the integration-level guard against iteration-count regressions
    referenced in the M13.6 plan.
    """
    from asxos.domain.portfolio import allocator as alloc
    from asxos.domain.portfolio import constraints as cons
    from asxos.domain.portfolio.types import AllocationCandidate, DEFAULT_SCORE_WEIGHTS

    # Build 5 candidates: one ultra-low-vol (A, inv_vol=100), rest normal.
    def make_candidate(symbol: str, vol: str, rank: float) -> AllocationCandidate:
        return AllocationCandidate(
            symbol=symbol,
            sector="Materials",
            market_cap_aud=Decimal("500000000"),
            signal_label="STRONG_BUY",
            prob_up=Decimal(str(rank)),
            expected_return=Decimal("0.05"),
            daily_vol=Decimal(vol),
            confidence=2,
        )

    candidates = [
        make_candidate("A", "0.01", 0.90),   # ultra-low vol → inv_vol=100
        make_candidate("B", "0.02", 0.80),   # inv_vol=50
        make_candidate("C", "0.033", 0.70),  # inv_vol≈30
        make_candidate("D", "0.10", 0.60),   # inv_vol=10
        make_candidate("E", "0.20", 0.50),   # inv_vol=5
    ]

    profile = make_profile(
        risk_tolerance="aggressive",
        risk_tolerance_scalar=RISK_TOLERANCE_SCALARS["aggressive"],
        capital_aud=Decimal("100000"),
        cash_floor_pct=Decimal("0.70"),  # target_sum = 0.30
        per_name_cap_pct=Decimal("0.08"),  # cap at 8%; total headroom = 5×0.08=0.40 > 0.30 ✓
        sector_cap_pct=Decimal("1.0"),  # no sector cap — isolate name-cap pathology
    )

    # allocate: filter → rank → top-10 (aggressive but only 5 candidates) → inv-vol weights
    targets = alloc.allocate(candidates=candidates, profile=profile)
    assert len(targets) == 5  # universe smaller than position_count=10

    # apply_constraints: per-name cap of 8% triggers multi-iteration convergence
    constrained = cons.apply_constraints(targets, profile)
    assert len(constrained) == 5

    # All weights must respect per_name_cap.
    per_name_cap = profile.per_name_cap_pct
    for t in constrained:
        assert t.target_weight <= per_name_cap + Decimal("1e-9"), (
            f"{t.symbol} weight {t.target_weight} > cap {per_name_cap}"
        )

    # Weights must sum to roughly target_sum (≤ tolerance for rounding).
    target_sum = profile.leverage_cap - profile.cash_floor_pct
    total = sum(t.target_weight for t in constrained)
    assert abs(total - target_sum) < Decimal("1e-8"), (
        f"total weight {total} != target_sum {target_sum}"
    )

    # compute_deltas: from scratch (no existing holdings).
    prices = {t.symbol: Decimal("40") for t in constrained}
    trades = compute_deltas(
        targets=constrained,
        current_qty={},
        prices=prices,
        capital_aud=profile.capital_aud,
        leverage_cap=profile.leverage_cap,
    )
    assert len(trades) == 5
    assert all(t.side == "buy" for t in trades)
    assert all(t.delta_qty > 0 for t in trades)

    # assemble.
    result = assemble_result(
        profile=profile,
        targets=constrained,
        trades=trades,
        as_of=_TODAY,
        signals_as_of=_TODAY,
    )
    assert result.summary["n_buys"] == 5
    assert result.summary["n_sells"] == 0
    assert result.summary["total_buy_aud"] > Decimal("0")
