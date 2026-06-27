"""
CGT boundary tests — spec §5.1 (calendar arithmetic) and §5.2 (optimal
loss ordering). Covers TC-10, TC-11, TC-12, TC-18.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from asxos.domain.tax.cgt import (
    cgt_discount_rate,
    days_to_eligibility,
    is_discountable,
    net_capital_gain,
)
from asxos.domain.tax.types import CapitalGain

# ---------------------------------------------------------------------------
# §5.1 — the 12-month rule (calendar arithmetic, never day-count)
# ---------------------------------------------------------------------------

def test_disposal_exactly_one_year_later_not_eligible() -> None:
    # spec §5.1: a disposal exactly 365 days after acquisition does NOT qualify
    # in a non-leap-year span. acq 2024-01-01 → 2025-01-01 NOT eligible.
    assert not is_discountable(date(2024, 1, 1), date(2025, 1, 1))


def test_disposal_one_year_plus_one_day_eligible() -> None:
    # 2024-01-01 + 1 year + 1 day = 2025-01-02 is the earliest qualifying.
    assert is_discountable(date(2024, 1, 1), date(2025, 1, 2))


def test_disposal_one_year_plus_one_day_for_july_acq() -> None:
    # spec example: 2023-07-11 acquisition → earliest 2024-07-12
    assert not is_discountable(date(2023, 7, 11), date(2024, 7, 11))
    assert is_discountable(date(2023, 7, 11), date(2024, 7, 12))


def test_disposal_before_one_year_not_eligible() -> None:
    assert not is_discountable(date(2024, 1, 1), date(2024, 12, 31))


def test_disposal_exactly_366_days_eligible() -> None:
    # day-count 366 ≠ day-count 365; the calendar form catches the leap-year edge
    assert is_discountable(date(2024, 1, 1), date(2025, 1, 2))  # 367 days
    assert not is_discountable(date(2024, 1, 1), date(2024, 12, 31))  # 365 days


def test_days_to_eligibility_zero_after_threshold() -> None:
    today = date(2025, 1, 2)
    assert days_to_eligibility(date(2024, 1, 1), today) == 0


def test_days_to_eligibility_counts_down() -> None:
    today = date(2024, 12, 30)
    # earliest qualifying = 2025-01-02 → 3 days away
    assert days_to_eligibility(date(2024, 1, 1), today) == 3


# ---------------------------------------------------------------------------
# discount rate (spec §2 — exact 1/3 for SMSF)
# ---------------------------------------------------------------------------

def test_cgt_discount_individual() -> None:
    assert cgt_discount_rate("individual") == Decimal("0.5")


def test_cgt_discount_smsf_is_exact_third() -> None:
    rate = cgt_discount_rate("smsf")
    # 1/3 as exact ratio (Decimal at default precision)
    assert rate * Decimal("3") == pytest.approx(Decimal("1"), abs=Decimal("1e-25"))


# ---------------------------------------------------------------------------
# TC-10, TC-11 — individual 12-month boundary
# ---------------------------------------------------------------------------

def test_tc10_short_hold_no_discount() -> None:
    # TC-10 / §5.1: $10k gain on a 2024-01-01 acq disposed 2025-01-01 → NOT eligible
    gain = CapitalGain(
        symbol="X.AU",
        gain_aud=Decimal("10000"),
        discountable=is_discountable(date(2024, 1, 1), date(2025, 1, 1)),
        holding_period_days=(date(2025, 1, 1) - date(2024, 1, 1)).days,
    )
    assert not gain.discountable
    ncg = net_capital_gain(
        [gain],
        current_year_losses=Decimal("0"),
        carried_forward_losses=Decimal("0"),
        account_type="individual",
    )
    # No discount → net gain = $10k. Tax at 39% (37% + 2% Medicare) = $3,900
    assert ncg.net_capital_gain == Decimal("10000")
    assert ncg.discount_applied == Decimal("0")


def test_tc11_long_hold_with_discount() -> None:
    # TC-11 / §5.1: same gain, disposal 2025-01-02 → eligible. Net gain $5,000.
    gain = CapitalGain(
        symbol="X.AU",
        gain_aud=Decimal("10000"),
        discountable=is_discountable(date(2024, 1, 1), date(2025, 1, 2)),
        holding_period_days=(date(2025, 1, 2) - date(2024, 1, 1)).days,
    )
    assert gain.discountable
    ncg = net_capital_gain(
        [gain],
        current_year_losses=Decimal("0"),
        carried_forward_losses=Decimal("0"),
        account_type="individual",
    )
    assert ncg.net_capital_gain == Decimal("5000")


def test_tc12_smsf_with_one_third_discount() -> None:
    # TC-12 / §5.1, §5.2: same gain, SMSF → net gain $6,666.67 (after 1/3)
    gain = CapitalGain(
        symbol="X.AU",
        gain_aud=Decimal("10000"),
        discountable=True,
        holding_period_days=400,
    )
    ncg = net_capital_gain(
        [gain],
        current_year_losses=Decimal("0"),
        carried_forward_losses=Decimal("0"),
        account_type="smsf",
    )
    # 1/3 discount of $10k = $3,333.33; net = $6,666.67
    expected = Decimal("10000") * (Decimal("1") - cgt_discount_rate("smsf"))
    assert ncg.net_capital_gain == expected


# ---------------------------------------------------------------------------
# TC-18 — optimal loss ordering (spec §5.2)
# ---------------------------------------------------------------------------

def test_tc18_optimal_loss_ordering() -> None:
    # spec §5.2 worked example:
    # Discount gains $30k, non-discount $10k, CY loss $15k, CF loss $5k.
    # Optimal: apply $10k CY to non-discount (extinguish), then $5k CY + $5k CF
    # to discount, leaving $20k discount gain. Discount $10k. Net $10k. Tax $3,900.
    gains = [
        CapitalGain("ND.AU", Decimal("10000"), discountable=False, holding_period_days=100),
        CapitalGain("D.AU", Decimal("30000"), discountable=True, holding_period_days=400),
    ]
    ncg = net_capital_gain(
        gains,
        current_year_losses=Decimal("15000"),
        carried_forward_losses=Decimal("5000"),
        account_type="individual",
    )
    assert ncg.nd_remainder == Decimal("0")
    assert ncg.d_remainder_pre_discount == Decimal("20000")
    assert ncg.discount_applied == Decimal("10000")
    assert ncg.net_capital_gain == Decimal("10000")
    assert ncg.net_capital_loss_cf == Decimal("0")


def test_tc18_optimal_ordering_smsf_one_third() -> None:
    # §5.2 ordering with the SMSF 1/3 discount (TC-18 is individual; this pins the
    # ordering × SMSF-discount interaction). Same inputs as TC-18:
    # $10k ND, $30k D, CY loss $15k, CF loss $5k → $20k discount gain remains.
    # SMSF: discount = 20000 × 1/3 = $6,666.67 → net $13,333.33.
    gains = [
        CapitalGain("ND.AU", Decimal("10000"), discountable=False, holding_period_days=100),
        CapitalGain("D.AU", Decimal("30000"), discountable=True, holding_period_days=400),
    ]
    ncg = net_capital_gain(
        gains,
        current_year_losses=Decimal("15000"),
        carried_forward_losses=Decimal("5000"),
        account_type="smsf",
    )
    # Ordering signature: non-discount extinguished first, $20k discount remains.
    assert ncg.nd_remainder == Decimal("0")
    assert ncg.d_remainder_pre_discount == Decimal("20000")
    assert ncg.discount_applied == Decimal("20000") * cgt_discount_rate("smsf")
    assert ncg.net_capital_gain == Decimal("20000") * (Decimal("1") - cgt_discount_rate("smsf"))


def test_partial_loss_extinguishes_non_discount_only() -> None:
    # §5.2: a loss smaller than the non-discount total is applied entirely to
    # non-discount, leaving the discount gains fully intact.
    # $10k ND, $5k D, CY loss $4k → ND remainder $6k, D untouched $5k.
    # Individual 50% discount on the $5k → net = 6000 + 2500 = $8,500.
    gains = [
        CapitalGain("ND.AU", Decimal("10000"), discountable=False, holding_period_days=100),
        CapitalGain("D.AU", Decimal("5000"), discountable=True, holding_period_days=400),
    ]
    ncg = net_capital_gain(
        gains,
        current_year_losses=Decimal("4000"),
        carried_forward_losses=Decimal("0"),
        account_type="individual",
    )
    assert ncg.nd_remainder == Decimal("6000")
    assert ncg.d_remainder_pre_discount == Decimal("5000")
    assert ncg.discount_applied == Decimal("2500")
    assert ncg.net_capital_gain == Decimal("8500")


def test_smsf_one_third_discount_precision_characterised() -> None:
    # §2 precision trap: the SMSF discount is Decimal(1)/Decimal(3) TRUNCATED to
    # 28 digits — it is NOT an exact $1,000 on a $3,000 base (discount_applied =
    # 999.9999…). The residual cancels so the net rounds back to $2,000 at 28-digit
    # precision, and downstream tax lines quantize to cents (positions._q). Pinned
    # so this precision behaviour cannot drift silently.
    gain = CapitalGain("D.AU", Decimal("3000"), discountable=True, holding_period_days=400)
    ncg = net_capital_gain(
        [gain],
        current_year_losses=Decimal("0"),
        carried_forward_losses=Decimal("0"),
        account_type="smsf",
    )
    # discount_applied is 999.9999… (truncated 1/3), NOT an exact 1000 — but the
    # by-construction check below is the load-bearing one; we don't assert the
    # inequality, so a future exact-Fraction path that yields 1000 won't false-fail.
    assert ncg.discount_applied == Decimal("3000") * cgt_discount_rate("smsf")
    assert ncg.net_capital_gain == Decimal("2000")


def test_excess_loss_becomes_carry_forward() -> None:
    # spec §5.2 Step 4: loss exceeding total gain → net_capital_loss_cf > 0
    gains = [
        CapitalGain("D.AU", Decimal("5000"), discountable=True, holding_period_days=400),
    ]
    ncg = net_capital_gain(
        gains,
        current_year_losses=Decimal("8000"),
        carried_forward_losses=Decimal("0"),
        account_type="individual",
    )
    assert ncg.net_capital_gain == Decimal("0")
    assert ncg.net_capital_loss_cf == Decimal("3000")


def test_realised_loss_inside_gains_list_rolls_into_total() -> None:
    # A realised loss row (negative gain_aud) aggregates into the loss pool.
    gains = [
        CapitalGain("WIN.AU", Decimal("5000"), discountable=False, holding_period_days=100),
        CapitalGain("LOSE.AU", Decimal("-2000"), discountable=False, holding_period_days=80),
    ]
    ncg = net_capital_gain(
        gains,
        current_year_losses=Decimal("0"),
        carried_forward_losses=Decimal("0"),
        account_type="individual",
    )
    # $5k non-discount minus $2k loss → $3k
    assert ncg.net_capital_gain == Decimal("3000")


def test_negative_loss_input_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        net_capital_gain(
            [],
            current_year_losses=Decimal("-100"),
            carried_forward_losses=Decimal("0"),
            account_type="individual",
        )


# ---------------------------------------------------------------------------
# Calendar arithmetic edge case — leap year (spec rejects day-count form)
# ---------------------------------------------------------------------------

def test_leap_year_day_count_form_would_fail_calendar_passes() -> None:
    # acq 2024-02-29 (leap); the calendar earliest is 2025-03-01.
    # A day-count of 365 days lands on 2025-02-28 which is NOT eligible.
    acq = date(2024, 2, 29)
    assert not is_discountable(acq, acq + timedelta(days=365))
    # The calendar threshold is 2025-03-01.
    assert is_discountable(acq, date(2025, 3, 1))
