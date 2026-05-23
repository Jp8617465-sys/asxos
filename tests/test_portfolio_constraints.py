"""
Tests for M13.4: constraint waterfall.

Coverage targets (plan I.10): ≥85% on constraints.py.

Covers per the plan:
(a) convergence in 2 iterations on realistic input
(b) hard-fail at 5 iterations (cycling sector cap with nowhere to go)
(c) cash floor + leverage respected (target_sum = leverage_cap - cash_floor_pct)
(d) min-position drop (trim_min_position)
(e) pre-flight infeasibility: over-allocation and under-allocation
(f) PATHOLOGICAL (R3): one ultra-high inv_vol name forces 3+ waterfall iterations
    due to cascading per-name cap freezes, but still converges.

Unit tests for apply_per_name_cap, apply_sector_cap, redistribute_residual,
apply_constraints, and trim_min_position are grouped separately.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.constraints import (
    apply_constraints,
    apply_per_name_cap,
    apply_sector_cap,
    redistribute_residual,
    trim_min_position,
)
from asxos.domain.portfolio.types import (
    DEFAULT_SCORE_WEIGHTS,
    RISK_TOLERANCE_SCALARS,
    AllocationTarget,
    Profile,
)

_TODAY = date(2026, 5, 23)
_EPS = Decimal("1e-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_target(
    symbol: str,
    weight: str | Decimal,
    inv_vol: str | Decimal,
    sector: str | None = "Financials",
    constraint_log: dict | None = None,
) -> AllocationTarget:
    return AllocationTarget(
        symbol=symbol,
        sector=sector,
        target_weight=Decimal(str(weight)),
        inv_vol_score=Decimal(str(inv_vol)),
        signal_label="BUY",
        prob_up=Decimal("0.70"),
        expected_return=Decimal("0.05"),
        constraint_log=constraint_log or {},
    )


def _make_profile(
    risk_tolerance: str = "balanced",
    capital_aud: Decimal = Decimal("500000"),
    cash_floor_pct: Decimal = Decimal("0.05"),
    leverage_cap: Decimal = Decimal("1.0"),
    per_name_cap_pct: Decimal = Decimal("0.10"),
    sector_cap_pct: Decimal = Decimal("0.30"),
    min_position_aud: Decimal = Decimal("1000"),
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
        per_name_cap_pct=per_name_cap_pct,
        sector_cap_pct=sector_cap_pct,
        excluded_sectors=(),
        excluded_symbols=(),
        min_position_aud=min_position_aud,
        horizon_years=10,
        defer_near_boundary_sells=True,
        score_weights_json=dict(DEFAULT_SCORE_WEIGHTS),
        created_at=_TODAY,
        updated_at=_TODAY,
    )


# ---------------------------------------------------------------------------
# apply_per_name_cap — unit tests
# ---------------------------------------------------------------------------


def test_per_name_cap_clips_overweight():
    t = _make_target("AAA", "0.25", "5")
    result, frozen = apply_per_name_cap([t], Decimal("0.10"))
    assert result[0].target_weight == Decimal("0.10")
    assert "AAA" in frozen


def test_per_name_cap_leaves_under_cap_unchanged():
    t = _make_target("AAA", "0.08", "5")
    result, frozen = apply_per_name_cap([t], Decimal("0.10"))
    assert result[0].target_weight == Decimal("0.08")
    assert frozen == set()


def test_per_name_cap_marks_constraint_log():
    t = _make_target("AAA", "0.25", "5")
    result, _ = apply_per_name_cap([t], Decimal("0.10"))
    assert result[0].constraint_log.get("capped_by_per_name") is True


def test_per_name_cap_exact_cap_not_frozen():
    # weight == cap: should NOT be frozen (not strictly greater).
    t = _make_target("AAA", "0.10", "5")
    result, frozen = apply_per_name_cap([t], Decimal("0.10"))
    assert frozen == set()
    assert result[0].target_weight == Decimal("0.10")


def test_per_name_cap_mixed_batch():
    targets = [
        _make_target("A", "0.20", "5"),   # over → freeze
        _make_target("B", "0.08", "5"),   # under → unchanged
        _make_target("C", "0.15", "5"),   # over → freeze
    ]
    result, frozen = apply_per_name_cap(targets, Decimal("0.10"))
    assert result[0].target_weight == Decimal("0.10")
    assert result[1].target_weight == Decimal("0.08")
    assert result[2].target_weight == Decimal("0.10")
    assert frozen == {"A", "C"}


# ---------------------------------------------------------------------------
# apply_sector_cap — unit tests
# ---------------------------------------------------------------------------


def test_sector_cap_scales_down_unfrozen():
    targets = [
        _make_target("A", "0.20", "5", sector="Energy"),
        _make_target("B", "0.20", "5", sector="Energy"),
    ]
    result = apply_sector_cap(targets, Decimal("0.30"), frozen=set())
    total = sum(t.target_weight for t in result)
    assert abs(total - Decimal("0.30")) < _EPS


def test_sector_cap_leaves_frozen_untouched():
    targets = [
        _make_target("A", "0.10", "5", sector="Energy"),  # frozen
        _make_target("B", "0.20", "5", sector="Energy"),  # unfrozen, over with A
    ]
    # A frozen → sector total = 0.30 = sector_cap; no violation (<=); no change needed.
    result = apply_sector_cap(targets, Decimal("0.30"), frozen={"A"})
    assert result[0].target_weight == Decimal("0.10")
    assert result[1].target_weight == Decimal("0.20")


def test_sector_cap_marks_constraint_log():
    targets = [
        _make_target("A", "0.20", "5", sector="Energy"),
        _make_target("B", "0.20", "5", sector="Energy"),
    ]
    result = apply_sector_cap(targets, Decimal("0.30"), frozen=set())
    for t in result:
        assert t.constraint_log.get("capped_by_sector") is True


def test_sector_cap_different_sectors_independent():
    targets = [
        _make_target("A", "0.25", "5", sector="Energy"),
        _make_target("B", "0.25", "5", sector="Energy"),
        _make_target("C", "0.10", "5", sector="Materials"),  # separate sector, not over
    ]
    result = apply_sector_cap(targets, Decimal("0.30"), frozen=set())
    energy_total = sum(t.target_weight for t in result if t.sector == "Energy")
    materials_total = sum(t.target_weight for t in result if t.sector == "Materials")
    assert abs(energy_total - Decimal("0.30")) < _EPS
    assert materials_total == Decimal("0.10")  # unchanged


def test_sector_cap_no_violation_no_change():
    targets = [
        _make_target("A", "0.10", "5", sector="Energy"),
        _make_target("B", "0.10", "5", sector="Energy"),
    ]
    result = apply_sector_cap(targets, Decimal("0.30"), frozen=set())
    assert result == targets


# ---------------------------------------------------------------------------
# redistribute_residual — unit tests
# ---------------------------------------------------------------------------


def test_redistribute_by_inv_vol():
    # A has inv_vol=10 (low vol), B has inv_vol=5 (higher vol).
    # A should receive more residual.
    targets = [
        _make_target("A", "0.10", "10"),
        _make_target("B", "0.10", "5"),
    ]
    result = redistribute_residual(targets, Decimal("0.30"), frozen=set())
    total = sum(t.target_weight for t in result)
    assert abs(total - Decimal("0.30")) < _EPS
    a_new = next(t for t in result if t.symbol == "A")
    b_new = next(t for t in result if t.symbol == "B")
    assert a_new.target_weight > b_new.target_weight


def test_redistribute_skips_frozen():
    targets = [
        _make_target("A", "0.10", "10"),  # frozen
        _make_target("B", "0.05", "5"),   # unfrozen
    ]
    result = redistribute_residual(targets, Decimal("0.30"), frozen={"A"})
    a_new = next(t for t in result if t.symbol == "A")
    assert a_new.target_weight == Decimal("0.10")  # frozen, unchanged


def test_redistribute_zero_residual_no_change():
    targets = [
        _make_target("A", "0.15", "5"),
        _make_target("B", "0.15", "5"),
    ]
    # target_sum == sum already
    result = redistribute_residual(targets, Decimal("0.30"), frozen=set())
    assert result[0].target_weight == Decimal("0.15")
    assert result[1].target_weight == Decimal("0.15")


def test_redistribute_all_frozen_is_noop():
    targets = [
        _make_target("A", "0.10", "5"),
        _make_target("B", "0.10", "5"),
    ]
    result = redistribute_residual(targets, Decimal("0.50"), frozen={"A", "B"})
    # Residual stays as cash; frozen weights unchanged.
    assert result[0].target_weight == Decimal("0.10")
    assert result[1].target_weight == Decimal("0.10")


# ---------------------------------------------------------------------------
# apply_constraints — convergence in 2 iterations (realistic)
# ---------------------------------------------------------------------------


def test_constraints_converge_two_iterations():
    """Realistic 12-name input that takes exactly two waterfall iterations.

    Iteration 1: A (0.30, inv_vol=5) is capped at 0.12; residual redistributed.
                 B (inv_vol=100) absorbs a large share → 0.1883 > cap 0.12.
    Iteration 2: B capped at 0.12; residual redistributed to C-L (all < 0.12). Done.

    N(12) × per_name_cap(0.12) = 1.44 >> target_sum(0.95) ✓ pre-flight passes.
    Sector_cap=1.0 (no sector constraint fires).
    """
    # 12 names summing to exactly 0.95.
    # A: 0.30 (over cap 0.12)
    # B: 0.065 (inv_vol=100 → absorbs most residual in iter 1; pushed over cap)
    # C-L: 0.058 each × 10 = 0.580
    # Sum = 0.30 + 0.065 + 0.580 = 0.945... need 0.95 exactly. Adjust:
    # A:0.30, B:0.07, C-L:0.058 × 10 = 0.58. Sum=0.95 ✓
    targets = [
        _make_target("A", "0.30",  "5",   sector="Mixed"),
        _make_target("B", "0.07",  "100", sector="Mixed"),
        *[_make_target(f"N{i:02d}", "0.058", "5", sector="Mixed") for i in range(10)],
    ]
    total = sum(t.target_weight for t in targets)
    assert abs(total - Decimal("0.95")) < _EPS

    profile = _make_profile(
        per_name_cap_pct=Decimal("0.12"),
        sector_cap_pct=Decimal("1.0"),   # no sector constraint
        capital_aud=Decimal("500000"),
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile)

    # All weights ≤ per_name_cap.
    for t in result:
        assert t.target_weight <= Decimal("0.12") + Decimal("1e-8"), \
            f"{t.symbol} weight {t.target_weight} > per_name_cap 0.12"

    # Weight sum preserved at target_sum.
    assert abs(sum(t.target_weight for t in result) - Decimal("0.95")) < _EPS


# ---------------------------------------------------------------------------
# (c) Cash floor + leverage respected
# ---------------------------------------------------------------------------


def test_constraints_target_sum_equals_leverage_minus_cash():
    """After waterfall, sum(target_weights) should equal target_sum."""
    targets = [_make_target(f"S{i:02d}", "0.095", "5", sector="Financials") for i in range(10)]
    profile = _make_profile(
        leverage_cap=Decimal("1.0"),
        cash_floor_pct=Decimal("0.05"),
        per_name_cap_pct=Decimal("0.20"),
        sector_cap_pct=Decimal("1.0"),  # no sector constraint
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile)
    total = sum(t.target_weight for t in result)
    expected = Decimal("1.0") - Decimal("0.05")  # = 0.95
    assert abs(total - expected) < _EPS


def test_constraints_leverage_increases_target_sum():
    # target_sum = 2.0 - 0.05 = 1.95 with leverage_cap=2.0.
    # 2 heavy names at 0.40 (over per_name_cap=0.25) + 8 lighter names.
    # Each name in a unique sector so no sector cap fires.
    # Sum = 2*0.40 + 8*0.14375 = 0.80 + 1.15 = 1.95 ✓
    targets = [
        _make_target("H1", "0.40", "5", sector="S00"),
        _make_target("H2", "0.40", "5", sector="S01"),
        *[
            _make_target(f"L{i:02d}", "0.14375", "5", sector=f"S{i+2:02d}")
            for i in range(8)
        ],
    ]
    assert abs(sum(t.target_weight for t in targets) - Decimal("1.95")) < _EPS

    profile = _make_profile(
        leverage_cap=Decimal("2.0"),
        cash_floor_pct=Decimal("0.05"),
        per_name_cap_pct=Decimal("0.25"),
        sector_cap_pct=Decimal("1.0"),   # no sector constraint (each in own sector)
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile)
    total = sum(t.target_weight for t in result)
    expected = Decimal("2.0") - Decimal("0.05")  # = 1.95
    assert abs(total - expected) < _EPS


# ---------------------------------------------------------------------------
# (d) trim_min_position
# ---------------------------------------------------------------------------


def test_trim_drops_below_min():
    targets = [
        _make_target("A", "0.001", "5"),   # $500k * 0.001 = $500 < $1000 min
        _make_target("B", "0.002", "5"),   # $500k * 0.002 = $1000 >= $1000 min
    ]
    result = trim_min_position(targets, Decimal("500000"), Decimal("1000"))
    assert len(result) == 1
    assert result[0].symbol == "B"


def test_trim_keeps_at_exact_minimum():
    t = _make_target("A", "0.002", "5")  # $500k * 0.002 = $1000 exactly
    result = trim_min_position([t], Decimal("500000"), Decimal("1000"))
    assert len(result) == 1


def test_trim_dropped_weight_not_redistributed():
    # The sum of remaining weights < original sum (dropped weight becomes cash).
    targets = [
        _make_target("A", "0.001", "5"),  # dropped
        _make_target("B", "0.094", "5"),  # kept
    ]
    result = trim_min_position(targets, Decimal("500000"), Decimal("1000"))
    assert len(result) == 1
    assert result[0].target_weight == Decimal("0.094")  # unchanged


def test_trim_empty_result_when_all_below_min():
    targets = [_make_target("A", "0.001", "5"), _make_target("B", "0.001", "5")]
    result = trim_min_position(targets, Decimal("500000"), Decimal("1000"))
    assert result == []


def test_trim_all_kept_when_all_above_min():
    targets = [_make_target(f"S{i}", "0.05", "5") for i in range(10)]
    result = trim_min_position(targets, Decimal("500000"), Decimal("1000"))
    assert len(result) == 10


# ---------------------------------------------------------------------------
# (e) pre-flight infeasibility
# ---------------------------------------------------------------------------


def test_preflight_over_allocation_raises():
    """target_sum (0.95) > N(5) × per_name_cap(0.10) = 0.50 → RuntimeError."""
    targets = [_make_target(f"S{i}", "0.19", "5") for i in range(5)]
    profile = _make_profile(per_name_cap_pct=Decimal("0.10"))
    with pytest.raises(RuntimeError, match="pre-flight"):
        apply_constraints(targets, profile)


def test_preflight_under_allocation_raises():
    """target_sum extremely small relative to min_position_aud / capital_aud."""
    targets = [_make_target("A", "0.000001", "5")]
    profile = _make_profile(
        leverage_cap=Decimal("1.0"),
        cash_floor_pct=Decimal("0.999999"),  # target_sum ≈ 0.000001
        per_name_cap_pct=Decimal("0.50"),
        capital_aud=Decimal("500000"),
        min_position_aud=Decimal("1000"),
        # min_weight = 1000/500000 = 0.002; target_sum=0.000001 < 0.002 → fail
    )
    with pytest.raises(RuntimeError, match="pre-flight"):
        apply_constraints(targets, profile)


# ---------------------------------------------------------------------------
# (b) Hard-fail at 5 iterations (cycling sector constraint)
# ---------------------------------------------------------------------------


def test_hard_fail_five_iterations_sector_cycle():
    """All names in one sector; sector_cap << target_sum.

    The sector cap scales them down each iteration; residual redistribution
    brings them back up.  After 5 iterations: RuntimeError.

    N(5) × per_name_cap(0.30) = 1.50 > target_sum(0.95) → pre-flight passes.
    sector_cap(0.15) < target_sum(0.95) → infeasible; waterfall cycles.
    """
    targets = [_make_target(f"S{i}", "0.19", "5", sector="Energy") for i in range(5)]
    profile = _make_profile(
        per_name_cap_pct=Decimal("0.30"),
        sector_cap_pct=Decimal("0.15"),
        min_position_aud=Decimal("1"),
    )
    with pytest.raises(RuntimeError, match="did not converge"):
        apply_constraints(targets, profile)


# ---------------------------------------------------------------------------
# (f) PATHOLOGICAL (plan H.1 R3 + Part E item 4)
#     One ultra-high inv_vol name cascades per-name cap freezes across 3+
#     iterations but still converges before hitting the 5-iter limit.
# ---------------------------------------------------------------------------


def test_pathological_ultra_low_vol_forces_3_iterations():
    """Constructed scenario that requires exactly 3 waterfall iterations.

    Five names with cascading inv_vol scores (100, 50, 30, 10, 5).
    Name A starts far above per_name_cap=0.08:

    Iter 1: A (0.20) capped → residual redistributed → B (0.10316) > 0.08.
    Iter 2: B capped → residual redistributed → C (0.08333) > 0.08.
    Iter 3: C capped → residual redistributed → D,E settle below 0.08. DONE.

    Verified by hand-trace in the session that produced this test.
    """
    targets = [
        _make_target("A", "0.20", "100", sector="Misc"),  # ultra-high inv_vol
        _make_target("B", "0.04", "50",  sector="Misc"),
        _make_target("C", "0.03", "30",  sector="Misc"),
        _make_target("D", "0.02", "10",  sector="Misc"),
        _make_target("E", "0.01", "5",   sector="Misc"),
    ]
    # sum = 0.30 = target_sum; per_name_cap=0.08; max_deployable=5*0.08=0.40>0.30
    profile = _make_profile(
        leverage_cap=Decimal("1.00"),
        cash_floor_pct=Decimal("0.70"),   # target_sum = 1.00 - 0.70 = 0.30
        per_name_cap_pct=Decimal("0.08"),
        sector_cap_pct=Decimal("1.00"),   # no sector constraint
        capital_aud=Decimal("500000"),
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile, max_iterations=5)

    # Converged: all weights ≤ per_name_cap.
    for t in result:
        assert t.target_weight <= Decimal("0.08") + Decimal("1e-8"), \
            f"{t.symbol}: weight={t.target_weight} > per_name_cap=0.08"

    # Total weight preserved at target_sum = 0.30.
    total = sum(t.target_weight for t in result)
    assert abs(total - Decimal("0.30")) < _EPS

    # All 5 names retained (none dropped by per_name cap — just capped).
    assert {t.symbol for t in result} == {"A", "B", "C", "D", "E"}

    # constraint_log confirms A, B, C were capped by per-name.
    by_sym = {t.symbol: t for t in result}
    assert by_sym["A"].constraint_log.get("capped_by_per_name") is True
    assert by_sym["B"].constraint_log.get("capped_by_per_name") is True
    assert by_sym["C"].constraint_log.get("capped_by_per_name") is True

    # D and E were NOT frozen (they settled below cap).
    assert not by_sym["D"].constraint_log.get("capped_by_per_name")
    assert not by_sym["E"].constraint_log.get("capped_by_per_name")


def test_pathological_converges_before_limit():
    """Same scenario as above but with max_iterations=3 (still converges at iter 3)."""
    targets = [
        _make_target("A", "0.20", "100", sector="Misc"),
        _make_target("B", "0.04", "50",  sector="Misc"),
        _make_target("C", "0.03", "30",  sector="Misc"),
        _make_target("D", "0.02", "10",  sector="Misc"),
        _make_target("E", "0.01", "5",   sector="Misc"),
    ]
    profile = _make_profile(
        leverage_cap=Decimal("1.00"),
        cash_floor_pct=Decimal("0.70"),
        per_name_cap_pct=Decimal("0.08"),
        sector_cap_pct=Decimal("1.00"),
        capital_aud=Decimal("500000"),
        min_position_aud=Decimal("1"),
    )
    # With max_iterations=3, should still converge (exactly at iter 3).
    result = apply_constraints(targets, profile, max_iterations=3)
    for t in result:
        assert t.target_weight <= Decimal("0.08") + Decimal("1e-8")


def test_pathological_fails_if_limit_too_low():
    """Same scenario with max_iterations=2 should NOT converge (needs 3)."""
    targets = [
        _make_target("A", "0.20", "100", sector="Misc"),
        _make_target("B", "0.04", "50",  sector="Misc"),
        _make_target("C", "0.03", "30",  sector="Misc"),
        _make_target("D", "0.02", "10",  sector="Misc"),
        _make_target("E", "0.01", "5",   sector="Misc"),
    ]
    profile = _make_profile(
        leverage_cap=Decimal("1.00"),
        cash_floor_pct=Decimal("0.70"),
        per_name_cap_pct=Decimal("0.08"),
        sector_cap_pct=Decimal("1.00"),
        capital_aud=Decimal("500000"),
        min_position_aud=Decimal("1"),
    )
    with pytest.raises(RuntimeError, match="did not converge"):
        apply_constraints(targets, profile, max_iterations=2)


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_constraints_no_violations_passthrough():
    """No cap fires; weights returned unchanged (sum preserved)."""
    targets = [_make_target(f"S{i}", "0.095", "5", sector="Financials") for i in range(10)]
    profile = _make_profile(
        per_name_cap_pct=Decimal("0.10"),
        sector_cap_pct=Decimal("1.00"),
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile)
    total = sum(t.target_weight for t in result)
    assert abs(total - Decimal("0.95")) < _EPS
    # No names frozen.
    for t in result:
        assert t.constraint_log.get("capped_by_per_name") is None


def test_constraints_preserves_symbol_set():
    """Waterfall must not add or remove names."""
    targets = [
        _make_target("A", "0.25", "10", sector="Energy"),
        _make_target("B", "0.25", "10", sector="Materials"),
        _make_target("C", "0.25", "5",  sector="Industrials"),
        _make_target("D", "0.10", "5",  sector="Industrials"),
        _make_target("E", "0.10", "5",  sector="Financials"),
    ]
    profile = _make_profile(
        per_name_cap_pct=Decimal("0.20"),
        sector_cap_pct=Decimal("1.00"),
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile)
    assert {t.symbol for t in result} == {"A", "B", "C", "D", "E"}


def test_constraints_single_name_at_cap():
    """One name, weight == per_name_cap already; no trimming, no iteration needed."""
    t = _make_target("A", "0.10", "5")
    profile = _make_profile(
        per_name_cap_pct=Decimal("0.10"),
        sector_cap_pct=Decimal("1.00"),
        leverage_cap=Decimal("1.0"),
        cash_floor_pct=Decimal("0.90"),   # target_sum = 0.10
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints([t], profile)
    assert len(result) == 1
    assert result[0].target_weight == Decimal("0.10")


def test_constraints_multiple_sectors_all_respect_per_name_cap():
    """Per-name cap fires across names spread over multiple sectors.

    10 names in 5 sectors (2 per sector).  Two names start overweight;
    after the waterfall every name ≤ per_name_cap and every sector ≤ sector_cap.
    Each sector has at most 2 names × per_name_cap = 2 × 0.12 = 0.24 < 0.30,
    so no sector cap fires (this tests the per-name path in a multi-sector setup).
    """
    # 8 names at 0.09375 each + 2 heavy names at 0.25.
    # Sum = 8*0.09375 + 2*0.25 = 0.75 + 0.50 = 1.25... too high.
    # Recalculate: target_sum = 0.95. Heavy=2*0.20, rest=(0.95-0.40)/8=0.06875 each.
    targets = [
        _make_target("H1", "0.20", "8", sector="Energy"),
        _make_target("H2", "0.20", "8", sector="Materials"),
        _make_target("L1", "0.06875", "5", sector="Energy"),
        _make_target("L2", "0.06875", "5", sector="Materials"),
        _make_target("L3", "0.06875", "5", sector="Industrials"),
        _make_target("L4", "0.06875", "5", sector="Industrials"),
        _make_target("L5", "0.06875", "5", sector="Financials"),
        _make_target("L6", "0.06875", "5", sector="Financials"),
        _make_target("L7", "0.06875", "5", sector="Healthcare"),
        _make_target("L8", "0.06875", "5", sector="Healthcare"),
    ]
    assert abs(sum(t.target_weight for t in targets) - Decimal("0.95")) < _EPS

    profile = _make_profile(
        per_name_cap_pct=Decimal("0.12"),
        sector_cap_pct=Decimal("0.30"),
        min_position_aud=Decimal("1"),
    )
    result = apply_constraints(targets, profile)

    # No per-name violation.
    for t in result:
        assert t.target_weight <= Decimal("0.12") + Decimal("1e-8"), \
            f"{t.symbol}: {t.target_weight} > 0.12"

    # No sector violation.
    sector_sums: dict[str | None, Decimal] = {}
    for t in result:
        sector_sums[t.sector] = sector_sums.get(t.sector, Decimal("0")) + t.target_weight
    for sector, total in sector_sums.items():
        assert total <= Decimal("0.30") + Decimal("1e-8"), \
            f"Sector {sector!r}: {total} > 0.30"
