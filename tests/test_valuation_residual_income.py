"""Residual income: the maths, with no DB and no Ke machinery.

The method is deliberately the conservative one — terminal value equals book,
no perpetual excess return — and these tests pin that shape so it cannot drift.
"""
from __future__ import annotations

import decimal
from decimal import Decimal
from pathlib import Path

import pytest

from asxos.domain.valuation import capm
from asxos.domain.valuation import residual_income as ri
from asxos.domain.valuation.numeric import compound, q6, valuation_context

PKG = Path(__file__).resolve().parent.parent / "asxos" / "domain" / "valuation"


# --- determinism substrate ---------------------------------------------------

def test_q6_refuses_float_outright() -> None:
    with pytest.raises(TypeError, match="float reached"):
        q6(1.5)  # type: ignore[arg-type]


def test_compound_is_exact_for_an_integer_exponent() -> None:
    with valuation_context():
        assert compound(Decimal("1.1"), 3) == Decimal("1.331")
        assert compound(Decimal("1.1"), 0) == Decimal("1")


def test_value_is_identical_under_a_mutated_global_decimal_context() -> None:
    """The whole point of the local context: another module cannot move our answer."""
    kwargs = {
        "book_start": Decimal("16.883740"),
        "roe_start": Decimal("0.110913"),
        "ke": Decimal("0.103310"),
        "payout_ratio": Decimal("0.811696"),
    }
    first, _, _ = ri.value_per_share(**kwargs)  # type: ignore[arg-type]
    original = decimal.getcontext().prec
    try:
        decimal.getcontext().prec = 6  # hostile: far below what the model needs
        second, _, _ = ri.value_per_share(**kwargs)  # type: ignore[arg-type]
    finally:
        decimal.getcontext().prec = original
    assert first == second


# --- the fade ----------------------------------------------------------------

def test_fade_path_reaches_ke_exactly_at_the_stated_horizon() -> None:
    path = ri.fade_path(Decimal("0.15"), Decimal("0.10"), 10)
    assert len(path) == 10
    assert path[-1] == Decimal("0.10"), "terminal ROE must BE Ke, not approach it"


def test_default_horizon_is_ten_years() -> None:
    assert ri.DEFAULT_HORIZON_YEARS == 10


def test_book_rolls_forward_on_retained_earnings_only() -> None:
    roe = (Decimal("0.10"), Decimal("0.10"))
    # Full payout retains nothing, so book cannot grow.
    assert ri.book_path(Decimal("100"), roe, Decimal("1")) == (Decimal("100"), Decimal("100"))
    grown = ri.book_path(Decimal("100"), roe, Decimal("0"))
    assert grown[0] == Decimal("110.00")
    assert grown[1] == Decimal("121.0000")


# --- the value ---------------------------------------------------------------

def test_two_year_hand_worked_example() -> None:
    """B0=100, ROE 15% fading to Ke 10% over 2y, full payout.

    ROE = (0.125, 0.10); book stays 100; RI = (2.5, 0); V = 100 + 2.5/1.1.
    """
    value, roe_by_year, book_by_year = ri.value_per_share(
        book_start=Decimal("100"),
        roe_start=Decimal("0.15"),
        ke=Decimal("0.10"),
        payout_ratio=Decimal("1"),
        horizon_years=2,
    )
    assert roe_by_year == (Decimal("0.125"), Decimal("0.10"))
    assert book_by_year == (Decimal("100"), Decimal("100"))
    assert value == Decimal("102.272727")


def test_zero_excess_return_values_exactly_at_book() -> None:
    """ROE == Ke at every step means the security is worth its book, to the cent."""
    value, _, _ = ri.value_per_share(
        book_start=Decimal("16.883740"),
        roe_start=Decimal("0.10"),
        ke=Decimal("0.10"),
        payout_ratio=Decimal("0.80"),
    )
    assert value == Decimal("16.883740")


def test_roe_below_ke_values_below_book() -> None:
    value, _, _ = ri.value_per_share(
        book_start=Decimal("20.555000"),
        roe_start=Decimal("0.090127"),
        ke=Decimal("0.103310"),
        payout_ratio=Decimal("0.80"),
    )
    assert value < Decimal("20.555000")


def test_terminal_value_is_book_and_no_perpetuity_term_exists() -> None:
    """Grep-level guarantee: the module carries no continuing-value machinery."""
    source = "\n".join(p.read_text() for p in PKG.glob("*.py"))
    for banned in ("terminal_growth", "perpetuity", "gordon", "/ (ke -", "/(ke -"):
        assert banned not in source.lower(), banned


def test_a_longer_horizon_cannot_be_used_to_raise_the_value_to_market() -> None:
    """Pre-commitment, made executable: extending the fade adds little, by design.

    Because ROE fades to Ke, extra years contribute a vanishing excess. This test
    exists so that a future attempt to close a value/price gap by lengthening the
    horizon is visibly futile rather than quietly attempted.
    """
    common = {
        "book_start": Decimal("16.883740"),
        "roe_start": Decimal("0.110913"),
        "ke": Decimal("0.103310"),
        "payout_ratio": Decimal("0.811696"),
    }
    ten, _, _ = ri.value_per_share(**common, horizon_years=10)  # type: ignore[arg-type]
    thirty, _, _ = ri.value_per_share(**common, horizon_years=30)  # type: ignore[arg-type]
    assert thirty > ten
    # Tripling the horizon moves the value by well under half of book.
    assert (thirty - ten) < Decimal("16.883740") / Decimal("2")


# --- franking ----------------------------------------------------------------

def test_franking_gross_up_matches_the_repo_wide_constant() -> None:
    """Tc/(1-Tc) — the same derivation as research/factor_scores.py."""
    assert ri.FRANKING_GROSS_UP == Decimal("0.30") / Decimal("0.70")


def test_franking_adjustment_raises_value_and_zero_franking_is_a_no_op() -> None:
    common = {
        "book_start": Decimal("16.883740"),
        "roe_start": Decimal("0.110913"),
        "ke": Decimal("0.103310"),
        "payout_ratio": Decimal("0.811696"),
    }
    unadjusted, _, _ = ri.value_per_share(**common)  # type: ignore[arg-type]
    zero, _, _ = ri.value_per_share(**common, franking_pct=Decimal("0"))  # type: ignore[arg-type]
    full, _, _ = ri.value_per_share(**common, franking_pct=Decimal("100"))  # type: ignore[arg-type]
    assert zero == unadjusted, "0% franking must be identical to not adjusting"
    assert full > unadjusted


# --- Ke ----------------------------------------------------------------------

def test_ke_is_risk_free_plus_beta_times_erp() -> None:
    ke = capm.cost_of_equity(
        risk_free=Decimal("0.04831"), beta=Decimal("1.00"), erp=Decimal("0.055")
    )
    assert ke == Decimal("0.103310")


def test_erp_outside_the_ruled_five_to_six_percent_is_refused() -> None:
    for bad in (Decimal("0.04"), Decimal("0.07")):
        with pytest.raises(ValueError, match="outside the ruled range"):
            capm.cost_of_equity(risk_free=Decimal("0.04831"), beta=Decimal("1"), erp=bad)


def test_ke_band_spans_the_stated_beta_range_and_is_ordered() -> None:
    low, mid, high = capm.ke_band(risk_free=Decimal("0.04831"), erp=Decimal("0.055"))
    assert low < mid < high
    assert low == Decimal("0.097810")   # beta 0.90
    assert high == Decimal("0.114310")  # beta 1.20


def test_ke_sensitivity_is_exactly_minus_one_zero_plus_one_percent() -> None:
    lo, mid, hi = capm.ke_sensitivity(Decimal("0.103310"))
    assert (mid - lo, hi - mid) == (Decimal("0.01"), Decimal("0.01"))


def test_the_risk_free_label_never_claims_to_be_an_acgb_quote() -> None:
    assert "IRLTLT01AUM156N" in capm.RISK_FREE_LABEL
    assert "MONTHLY" in capm.RISK_FREE_LABEL.upper()
    assert "not a daily" in capm.RISK_FREE_LABEL


def test_beta_floor_is_one_trading_year() -> None:
    assert capm.MIN_BETA_SESSIONS == 250
