"""
Division 296 boundary tests (spec §6). Covers TC-13, TC-14, TC-15, TC-16, TC-17.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.div_296 import div296_liability


def _approx(actual: Decimal, expected_str: str, tol: str = "1") -> bool:
    return abs(actual - Decimal(expected_str)) <= Decimal(tol)


def test_tc13_tsb_3_2m_earnings_160k() -> None:
    # TC-13: p1 = 0.0625, tier_1 = 1500
    out = div296_liability(tsb_ref=Decimal("3200000"), earnings=Decimal("160000"))
    assert _approx(out.tier_1, "1500")
    assert out.tier_2 == Decimal("0")
    assert _approx(out.total, "1500")


def test_tc14_tsb_10_5m_earnings_525k_stacked() -> None:
    # TC-14: tier_1 = 56250; tier_2 = 2500; total 58750
    out = div296_liability(tsb_ref=Decimal("10500000"), earnings=Decimal("525000"))
    assert _approx(out.tier_1, "56250")
    assert _approx(out.tier_2, "2500")
    assert _approx(out.total, "58750")


def test_tc15_under_threshold_zero() -> None:
    # TC-15: TSB just under $3M → 0 Div 296
    out = div296_liability(tsb_ref=Decimal("2999999"), earnings=Decimal("150000"))
    assert out.total == Decimal("0")


def test_tc16_exactly_at_threshold_zero() -> None:
    # TC-16: TSB == $3M → p1 = 0 → 0 Div 296
    out = div296_liability(tsb_ref=Decimal("3000000"), earnings=Decimal("150000"))
    assert out.total == Decimal("0")


def test_tc17_bills_digest_12m_example() -> None:
    # TC-17 / Bills Digest No. 48: TSB $12M, earnings $100k
    # p1 = 0.75 → tier_1 = 11250
    # p2 = 0.1667 → tier_2 = 1666.67
    # total ≈ 12916.67
    out = div296_liability(tsb_ref=Decimal("12000000"), earnings=Decimal("100000"))
    assert _approx(out.tier_1, "11250", tol="1")
    assert _approx(out.tier_2, "1667", tol="1")
    assert _approx(out.total, "12917", tol="1")


def test_zero_or_negative_earnings_short_circuits() -> None:
    # spec §6.3: tier_1 / tier_2 only fire when earnings > 0
    out = div296_liability(tsb_ref=Decimal("5000000"), earnings=Decimal("0"))
    assert out.total == Decimal("0")
    out = div296_liability(tsb_ref=Decimal("5000000"), earnings=Decimal("-10000"))
    assert out.total == Decimal("0")


def test_provisional_flag_propagates() -> None:
    out = div296_liability(
        tsb_ref=Decimal("3500000"),
        earnings=Decimal("100000"),
        is_provisional=True,
    )
    assert out.is_provisional is True


def test_proportions_use_full_tsb_denominator() -> None:
    # spec §6.3: both tiers use TSB_ref as denominator (not the slice above).
    out = div296_liability(tsb_ref=Decimal("4000000"), earnings=Decimal("100000"))
    p1 = (Decimal("4000000") - Decimal("3000000")) / Decimal("4000000")
    assert out.tier_1 == Decimal("100000") * p1 * Decimal("0.15")
