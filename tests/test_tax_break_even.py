"""
CGT discount break-even heuristic — spec §5.4 (TC-22 individual, TC-23 SMSF).

`cgt_break_even_price` estimates the minimum sale price today that nets the same
after-tax proceeds as deferring until the s 115-100 discount lands. These tests
pin:
  - the two worked examples (TC-22, TC-23);
  - the generic round-trip invariant (sell-now after-tax == sell-later after-tax)
    that the old `d`-coefficient bug violated for SMSF;
  - the None (no-meaningful-answer) branches;
  - Decimal-exactness on the SMSF 1/3 path.

Pure Decimal, no I/O — collects in the bare sandbox.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.tax.cgt import cgt_break_even_price, cgt_discount_rate
from asxos.domain.tax.types import MEDICARE_LEVY_RATE, SMSF_TAX_RATE

# Acquired recently enough that the 12-month discount is NOT yet available as of
# AS_OF (earliest qualifying disposal would be 2027-01-02, §5.1).
_ACQUIRED = date(2026, 1, 1)
_AS_OF = date(2026, 6, 28)
# Already past the 1yr+1day mark relative to AS_OF → discount already eligible.
_ELIGIBLE_ACQUIRED = date(2024, 1, 1)


def _r_eff(account_type: str, marginal_rate: Decimal) -> Decimal:
    """The effective rate the formula applies (§5.4)."""
    if account_type == "smsf":
        return SMSF_TAX_RATE
    return marginal_rate + MEDICARE_LEVY_RATE


def _after_tax_sell_now(p_sell: Decimal, cost: Decimal, r_eff: Decimal) -> Decimal:
    return p_sell - (p_sell - cost) * r_eff


def _after_tax_sell_later(p: Decimal, cost: Decimal, d: Decimal, r_eff: Decimal) -> Decimal:
    return p - (p - cost) * d * r_eff


# ---------------------------------------------------------------------------
# Worked examples (§11 matrix)
# ---------------------------------------------------------------------------

def test_tc22_individual_break_even() -> None:
    # §5.4 TC-22: P=100, cost=40, marginal 0.45 → r_eff 0.47, d=0.5 → $126.60.
    be = cgt_break_even_price(
        Decimal("100"), Decimal("40"), "individual", _ACQUIRED, _AS_OF,
        marginal_rate=Decimal("0.45"),
    )
    assert be == Decimal("126.60")


def test_tc23_smsf_break_even_is_the_regression_lock() -> None:
    # §5.4 TC-23: SMSF r_eff 0.15, d=1/3 → $107.06. The pre-§5.4 code (cost*r*d,
    # plus the 0.45 default it never overrode for SMSF) returned $143.64 — this
    # assertion fails against that bug and passes only with the (1-d)+0.15 fix.
    be = cgt_break_even_price(
        Decimal("100"), Decimal("40"), "smsf", _ACQUIRED, _AS_OF,
    )
    assert be == Decimal("107.06")
    assert be != Decimal("143.64")  # the old buggy value, for documentation


# ---------------------------------------------------------------------------
# Generic round-trip invariant — the guard that would have caught the (1-d) bug
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("account_type", "price", "cost", "marginal"),
    [
        ("individual", Decimal("100"), Decimal("40"), Decimal("0.45")),
        ("individual", Decimal("250"), Decimal("180"), Decimal("0.37")),
        ("individual", Decimal("12.50"), Decimal("9.00"), Decimal("0.30")),
        ("smsf", Decimal("100"), Decimal("40"), Decimal("0.45")),
        ("smsf", Decimal("88.40"), Decimal("60.10"), Decimal("0.37")),
    ],
)
def test_break_even_round_trip_after_tax_equal(
    account_type: str, price: Decimal, cost: Decimal, marginal: Decimal
) -> None:
    # Selling NOW at the break-even price must net (to the cent) the same after-tax
    # proceeds as holding to the discount and selling LATER at the same price (§5.4).
    be = cgt_break_even_price(price, cost, account_type, _ACQUIRED, _AS_OF, marginal_rate=marginal)
    assert be is not None
    r_eff = _r_eff(account_type, marginal)
    d = cgt_discount_rate(account_type)  # type: ignore[arg-type]
    now = _after_tax_sell_now(be, cost, r_eff)
    later = _after_tax_sell_later(price, cost, d, r_eff)
    # `be` is quantized to cents, so allow up to a one-cent rounding gap.
    assert abs(now - later) <= Decimal("0.01")


# ---------------------------------------------------------------------------
# None branches (§5.4)
# ---------------------------------------------------------------------------

def test_none_when_already_discount_eligible() -> None:
    # days_to_eligibility == 0 → the discount is already available, no deferral hint.
    be = cgt_break_even_price(
        Decimal("100"), Decimal("40"), "individual", _ELIGIBLE_ACQUIRED, _AS_OF,
    )
    assert be is None


def test_none_when_no_unrealised_gain() -> None:
    be = cgt_break_even_price(
        Decimal("40"), Decimal("40"), "individual", _ACQUIRED, _AS_OF,
    )
    assert be is None
    below = cgt_break_even_price(
        Decimal("35"), Decimal("40"), "individual", _ACQUIRED, _AS_OF,
    )
    assert below is None


def test_none_when_r_eff_degenerate() -> None:
    # marginal 1.0 → r_eff 1.02 → denominator (1 - r_eff) <= 0 → None.
    be = cgt_break_even_price(
        Decimal("100"), Decimal("40"), "individual", _ACQUIRED, _AS_OF,
        marginal_rate=Decimal("1.0"),
    )
    assert be is None


def test_tiny_gain_returns_just_above_cost() -> None:
    # The `result > cost` guard is defensive: algebraically result <= cost iff
    # P <= cost (for 0 < r_eff < 1), which the no-gain branch already handles. So a
    # genuine (if tiny) unrealised gain always yields a break-even just above cost,
    # never None on this branch. P=40.50, cost=40, r_eff=0.47 → 40.72.
    be = cgt_break_even_price(
        Decimal("40.50"), Decimal("40"), "individual", _ACQUIRED, _AS_OF,
        marginal_rate=Decimal("0.45"),
    )
    assert be == Decimal("40.72")
    assert be > Decimal("40")


# ---------------------------------------------------------------------------
# Decimal-exactness on the SMSF 1/3 path (no float, exact literal)
# ---------------------------------------------------------------------------

def test_smsf_uses_exact_fraction_and_is_decimal() -> None:
    be = cgt_break_even_price(
        Decimal("100"), Decimal("40"), "smsf", _ACQUIRED, _AS_OF,
    )
    assert isinstance(be, Decimal)
    # Exact cents literal, not pytest.approx — the 1/3 discount is the exact
    # Decimal(Fraction(1, 3)) (spec §2), and the result quantizes deterministically.
    assert be == Decimal("107.06")
