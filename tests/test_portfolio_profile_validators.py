"""
Pure-function unit tests for `asxos.domain.portfolio.types.Profile`.

No DB. Every validator boundary gets a green case and a red case. Tests
for the DB-touching profile.py (load/save/activate) live in
test_portfolio_profile.py — added after migration 0005 lands.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.types import (
    DEFAULT_SCORE_WEIGHTS,
    RISK_TOLERANCE_SCALARS,
    Profile,
)


def _valid_profile(**overrides) -> Profile:
    """Construct a valid Profile with overridable fields. Used to test
    one boundary at a time without rewriting the whole dataclass init."""
    defaults: dict = {
        "profile_id": None,
        "name": "test-baseline",
        "is_active": False,
        "account_type": "individual",
        "risk_tolerance": "balanced",
        "risk_tolerance_scalar": Decimal("0.50"),
        "capital_aud": Decimal("500000"),
        "cash_floor_pct": Decimal("0.05"),
        "leverage_cap": Decimal("1.0"),
        "per_name_cap_pct": Decimal("0.10"),
        "sector_cap_pct": Decimal("0.30"),
        "excluded_sectors": (),
        "excluded_symbols": (),
        "min_position_aud": Decimal("1000"),
        "horizon_years": 10,
        "defer_near_boundary_sells": True,
        "score_weights_json": {
            "prob_up": Decimal("0.6"),
            "expected_return": Decimal("0.4"),
        },
        "created_at": date(2026, 5, 22),
        "updated_at": date(2026, 5, 22),
    }
    defaults.update(overrides)
    return Profile(**defaults)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_profile_constructs():
    p = _valid_profile()
    assert p.name == "test-baseline"
    assert p.account_type == "individual"
    assert p.risk_tolerance == "balanced"
    assert p.risk_tolerance_scalar == Decimal("0.50")
    assert p.defer_near_boundary_sells is True


# ---------------------------------------------------------------------------
# name
# ---------------------------------------------------------------------------


def test_empty_name_raises():
    with pytest.raises(ValueError, match="name must be"):
        _valid_profile(name="")


def test_whitespace_only_name_raises():
    with pytest.raises(ValueError, match="name must be"):
        _valid_profile(name="   ")


# ---------------------------------------------------------------------------
# account_type
# ---------------------------------------------------------------------------


def test_unknown_account_type_raises():
    with pytest.raises(ValueError, match="account_type must be"):
        _valid_profile(account_type="trust")  # type: ignore[arg-type]


def test_smsf_account_type_ok():
    p = _valid_profile(account_type="smsf")
    assert p.account_type == "smsf"


# ---------------------------------------------------------------------------
# risk_tolerance label ↔ scalar consistency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label, expected", list(RISK_TOLERANCE_SCALARS.items()))
def test_each_label_has_canonical_scalar(label, expected):
    p = _valid_profile(risk_tolerance=label, risk_tolerance_scalar=expected)
    assert p.risk_tolerance == label
    assert p.risk_tolerance_scalar == expected


def test_label_scalar_mismatch_raises():
    # label says balanced (=0.5) but scalar says 0.75 — must raise
    with pytest.raises(ValueError, match="does not match label"):
        _valid_profile(
            risk_tolerance="balanced", risk_tolerance_scalar=Decimal("0.75")
        )


def test_unknown_risk_label_raises():
    with pytest.raises(ValueError, match="risk_tolerance must be one of"):
        _valid_profile(risk_tolerance="yolo")  # type: ignore[arg-type]


def test_scalar_outside_unit_interval_raises():
    # We can't reach this directly without also failing the label-mismatch
    # check, so use a fresh label that maps to 0 then push scalar out of bound:
    with pytest.raises(ValueError, match="does not match label"):
        _valid_profile(
            risk_tolerance="conservative",
            risk_tolerance_scalar=Decimal("-0.1"),
        )


# ---------------------------------------------------------------------------
# capital_aud
# ---------------------------------------------------------------------------


def test_negative_capital_raises():
    with pytest.raises(ValueError, match="capital_aud must be non-negative"):
        _valid_profile(capital_aud=Decimal("-1"))


def test_zero_capital_ok():
    # Edge case: zero capital is a valid input (allocator will hard-fail later
    # because nothing can be allocated, but the profile itself is valid).
    p = _valid_profile(capital_aud=Decimal("0"))
    assert p.capital_aud == Decimal("0")


# ---------------------------------------------------------------------------
# cash_floor_pct
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", [Decimal("-0.01"), Decimal("1.01")])
def test_cash_floor_out_of_unit_interval_raises(v):
    with pytest.raises(ValueError, match="cash_floor_pct"):
        _valid_profile(cash_floor_pct=v)


@pytest.mark.parametrize("v", [Decimal("0"), Decimal("0.5"), Decimal("1")])
def test_cash_floor_inclusive_unit_interval_ok(v):
    p = _valid_profile(cash_floor_pct=v)
    assert p.cash_floor_pct == v


# ---------------------------------------------------------------------------
# leverage_cap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", [Decimal("0.5"), Decimal("0.99"), Decimal("3.01"), Decimal("5")])
def test_leverage_outside_band_raises(v):
    with pytest.raises(ValueError, match="leverage_cap"):
        _valid_profile(leverage_cap=v)


@pytest.mark.parametrize("v", [Decimal("1"), Decimal("1.5"), Decimal("3")])
def test_leverage_inside_band_ok(v):
    p = _valid_profile(leverage_cap=v)
    assert p.leverage_cap == v


# ---------------------------------------------------------------------------
# per_name_cap_pct  (open at 0, inclusive at 0.5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", [Decimal("0"), Decimal("-0.05"), Decimal("0.51"), Decimal("1")])
def test_per_name_cap_outside_raises(v):
    with pytest.raises(ValueError, match="per_name_cap_pct"):
        _valid_profile(per_name_cap_pct=v)


@pytest.mark.parametrize("v", [Decimal("0.001"), Decimal("0.10"), Decimal("0.5")])
def test_per_name_cap_inside_ok(v):
    p = _valid_profile(per_name_cap_pct=v)
    assert p.per_name_cap_pct == v


# ---------------------------------------------------------------------------
# sector_cap_pct  (open at 0, inclusive at 1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", [Decimal("0"), Decimal("-0.1"), Decimal("1.01")])
def test_sector_cap_outside_raises(v):
    with pytest.raises(ValueError, match="sector_cap_pct"):
        _valid_profile(sector_cap_pct=v)


@pytest.mark.parametrize("v", [Decimal("0.001"), Decimal("0.30"), Decimal("1")])
def test_sector_cap_inside_ok(v):
    p = _valid_profile(sector_cap_pct=v)
    assert p.sector_cap_pct == v


# ---------------------------------------------------------------------------
# min_position_aud
# ---------------------------------------------------------------------------


def test_negative_min_position_raises():
    with pytest.raises(ValueError, match="min_position_aud must be non-negative"):
        _valid_profile(min_position_aud=Decimal("-1"))


def test_zero_min_position_ok():
    p = _valid_profile(min_position_aud=Decimal("0"))
    assert p.min_position_aud == Decimal("0")


# ---------------------------------------------------------------------------
# horizon_years
# ---------------------------------------------------------------------------


def test_negative_horizon_raises():
    with pytest.raises(ValueError, match="horizon_years must be non-negative"):
        _valid_profile(horizon_years=-1)


def test_zero_horizon_ok():
    p = _valid_profile(horizon_years=0)
    assert p.horizon_years == 0


# ---------------------------------------------------------------------------
# score_weights_json — keys, types, sum tolerance
# ---------------------------------------------------------------------------


def test_default_score_weights_matches_constant():
    p = _valid_profile()
    assert p.score_weights_json == DEFAULT_SCORE_WEIGHTS


def test_score_weights_missing_key_raises():
    with pytest.raises(ValueError, match="score_weights_json keys"):
        _valid_profile(score_weights_json={"prob_up": Decimal("1.0")})


def test_score_weights_extra_key_raises():
    with pytest.raises(ValueError, match="score_weights_json keys"):
        _valid_profile(
            score_weights_json={
                "prob_up": Decimal("0.5"),
                "expected_return": Decimal("0.3"),
                "bogus": Decimal("0.2"),
            }
        )


def test_score_weights_float_value_raises():
    with pytest.raises(TypeError, match="must be Decimal"):
        _valid_profile(
            score_weights_json={"prob_up": 0.6, "expected_return": Decimal("0.4")}  # type: ignore[dict-item]
        )


def test_score_weights_negative_value_raises():
    with pytest.raises(ValueError, match="outside \\[0, 1\\]"):
        _valid_profile(
            score_weights_json={
                "prob_up": Decimal("-0.1"),
                "expected_return": Decimal("1.1"),
            }
        )


@pytest.mark.parametrize(
    "p, r",
    [
        (Decimal("0.6"), Decimal("0.4")),       # exact 1.0
        (Decimal("0.333333"), Decimal("0.666667")),  # sums to 1.000000
        (Decimal("0.5"), Decimal("0.5")),       # exact 1.0
        (Decimal("0.999"), Decimal("0.001")),  # at lower tolerance edge of sum
    ],
)
def test_score_weights_inside_tolerance_band_ok(p, r):
    prof = _valid_profile(score_weights_json={"prob_up": p, "expected_return": r})
    assert prof.score_weights_json["prob_up"] == p


@pytest.mark.parametrize(
    "p, r",
    [
        (Decimal("0.5"), Decimal("0.4")),     # sum 0.9
        (Decimal("0.7"), Decimal("0.4")),     # sum 1.1
        (Decimal("0.99"), Decimal("0.001")),  # sum 0.991 — outside [0.999, 1.001]
    ],
)
def test_score_weights_outside_tolerance_raises(p, r):
    with pytest.raises(ValueError, match="outside tolerance band"):
        _valid_profile(score_weights_json={"prob_up": p, "expected_return": r})


# ---------------------------------------------------------------------------
# exclusions
# ---------------------------------------------------------------------------


def test_excluded_sectors_as_list_raises():
    with pytest.raises(TypeError, match="excluded_sectors must be a tuple"):
        _valid_profile(excluded_sectors=["Financials"])  # type: ignore[arg-type]


def test_excluded_sectors_empty_string_raises():
    with pytest.raises(ValueError, match="excluded_sectors must contain non-empty"):
        _valid_profile(excluded_sectors=("Financials", ""))


def test_excluded_symbols_whitespace_only_raises():
    with pytest.raises(ValueError, match="excluded_symbols must contain non-empty"):
        _valid_profile(excluded_symbols=("BHP.AU", "   "))


def test_excluded_tuples_ok():
    p = _valid_profile(
        excluded_sectors=("Tobacco", "Gambling"),
        excluded_symbols=("XYZ.AU",),
    )
    assert "Tobacco" in p.excluded_sectors
    assert p.excluded_symbols == ("XYZ.AU",)


# ---------------------------------------------------------------------------
# frozen dataclass
# ---------------------------------------------------------------------------


def test_profile_is_frozen():
    p = _valid_profile()
    with pytest.raises((AttributeError, Exception)):
        p.name = "mutated"  # type: ignore[misc]
