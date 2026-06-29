"""
Spec §7 Medicare levy tests.

`medicare_levy_on()` is the stand-alone helper for the net-capital-gain branch
of the tax-view aggregator (s 251S(1)(a) ITAA 1936): 2% on the base for
individuals, 0 for SMSF. Previously untested.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.medicare import medicare_levy_on


def test_individual_levy_is_two_percent() -> None:
    # spec §7: levy = base * 0.02 for individuals
    assert medicare_levy_on(Decimal("10000"), account_type="individual") == Decimal("200")


def test_smsf_levy_is_zero() -> None:
    # spec §7: super funds pay no Medicare levy
    assert medicare_levy_on(Decimal("10000"), account_type="smsf") == Decimal("0")


def test_zero_base_individual_is_zero() -> None:
    assert medicare_levy_on(Decimal("0"), account_type="individual") == Decimal("0")


def test_levy_stacks_on_grossed_up_dividend_plus_net_gain() -> None:
    # spec §7: taxable income includes the grossed-up dividend AND the net
    # capital gain. The levy applies to the combined base at the same 2%.
    # grossed-up dividend 1428.57 (TC-01) + net capital gain 5000 = 6428.57.
    # grossed-up dividend 1428.57 (TC-01) + net capital gain 5000 = 6428.57;
    # levy at 2% = 128.5714 (independent oracle, not a restatement of the rate).
    base = Decimal("1428.57") + Decimal("5000")
    assert medicare_levy_on(base, account_type="individual") == Decimal("128.5714")


def test_individual_levy_honours_configured_rate() -> None:
    # §7.1: a low-income individual sets medicare_levy_rate=0 → no levy; a custom
    # rate is applied. (Default stays the statutory 2%.)
    assert medicare_levy_on(Decimal("10000"), account_type="individual", rate=Decimal("0")) == Decimal("0")
    assert medicare_levy_on(Decimal("10000"), account_type="individual", rate=Decimal("0.015")) == Decimal("150")
    assert medicare_levy_on(Decimal("10000"), account_type="individual") == Decimal("200")
