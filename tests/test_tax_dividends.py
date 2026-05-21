"""
Spec §4 dividend boundary tests — covers TC-01 through TC-09 and TC-19.

Each test cites the spec section and the TC ID from §11.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.tax.dividends import (
    after_tax_dividend_individual,
    after_tax_dividend_smsf,
)
from asxos.domain.tax.types import Dividend, IndividualConfig, SMSFConfig


def _div(cash: str, pct: str = "1.0", rate: str = "0.30") -> Dividend:
    return Dividend(
        symbol="X.AU",
        pay_date=date(2026, 5, 1),
        cash_dividend=Decimal(cash),
        franking_pct=Decimal(pct),
        corporate_tax_rate=Decimal(rate),
    )


# Decimal helper: approximate equality with a small tolerance for division by 7 / 3.
def _approx(actual: Decimal, expected_str: str, tol: str = "0.01") -> bool:
    return abs(actual - Decimal(expected_str)) <= Decimal(tol)


def test_tc01_individual_37_full_franking_30pct() -> None:
    # TC-01 / §4.1: $1000 ff @ 30% company, individual at 37%
    # spec §4.1 worked example: after-tax $728.57 at 47%. At 37%:
    #   credit = 428.57, gross = 1428.57, tax at 39% = 557.14,
    #   offset = 428.57, net_tax = 128.57, after_tax = 871.43.
    div = _div("1000")
    cfg = IndividualConfig(marginal_rate=Decimal("0.37"))
    out = after_tax_dividend_individual(div, cfg)
    assert _approx(out.after_tax_cash, "871.43")


def test_tc02_individual_37_full_franking_25pct_bre() -> None:
    # TC-02 / §3, §4.1: BRE rate 25%
    # credit = 1000 * 0.25/0.75 = 333.33; gross = 1333.33; tax at 39% = 520.00;
    # offset 333.33; net 186.67; after_tax = 813.33
    div = _div("1000", rate="0.25")
    cfg = IndividualConfig(marginal_rate=Decimal("0.37"))
    out = after_tax_dividend_individual(div, cfg)
    assert _approx(out.after_tax_cash, "813.33")


def test_tc03_individual_47_full_franking_30pct() -> None:
    # TC-03 / §4.1: $1000 ff @ 30% company, individual at 47%
    # gross = 1428.57; tax at 49% = 700.00; offset 428.57; net 271.43; after_tax = 728.57
    div = _div("1000")
    cfg = IndividualConfig(marginal_rate=Decimal("0.47"))
    out = after_tax_dividend_individual(div, cfg)
    assert _approx(out.after_tax_cash, "728.57")


def test_tc06_individual_37_partial_franking_50pct() -> None:
    # TC-06 / §3, §4.1: $1000, 50% franked at 30%
    # franked $500 → credit 214.29; gross 1214.29; tax 39% = 473.57;
    # offset 214.29; net 259.28; after_tax = 740.72
    div = _div("1000", "0.5")
    cfg = IndividualConfig(marginal_rate=Decimal("0.37"))
    out = after_tax_dividend_individual(div, cfg)
    assert _approx(out.after_tax_cash, "740.72")


def test_tc07_individual_37_fully_unfranked() -> None:
    # TC-07 / §4.1: $1000 unfranked
    # gross 1000; tax 39% = 390; after_tax = 610
    div = _div("1000", "0")
    cfg = IndividualConfig(marginal_rate=Decimal("0.37"))
    out = after_tax_dividend_individual(div, cfg)
    assert _approx(out.after_tax_cash, "610.00")


def test_tc08_position_1_cba_individual_37() -> None:
    # TC-08 / §4.1: $2,250 ff dividend, individual at 37% → after-tax $1,960.71
    div = _div("2250")
    cfg = IndividualConfig(marginal_rate=Decimal("0.37"))
    out = after_tax_dividend_individual(div, cfg)
    assert _approx(out.after_tax_cash, "1960.71")


def test_tc04_smsf_accumulation_full_franking() -> None:
    # TC-04 / §4.2: $1000 ff @ 30%, SMSF 0% pension
    # gross 1428.57; ECPI=0; taxable 1428.57; fund_tax at 15% = 214.29
    # offset 428.57; net_tax = -214.28 (refund); after_tax = 1214.28
    div = _div("1000")
    cfg = SMSFConfig(fund_pension_proportion=Decimal("0.0"))
    out = after_tax_dividend_smsf(div, cfg)
    assert _approx(out.after_tax_cash, "1214.29")


def test_tc05_smsf_pension_full_franking() -> None:
    # TC-05 / §4.2: $1000 ff @ 30%, SMSF 100% pension
    # gross 1428.57; ECPI 1428.57; taxable 0; fund_tax 0
    # offset 428.57 (full refund); after_tax = 1428.57
    div = _div("1000")
    cfg = SMSFConfig(fund_pension_proportion=Decimal("1.0"))
    out = after_tax_dividend_smsf(div, cfg)
    assert _approx(out.after_tax_cash, "1428.57")


def test_tc09_position_2_bhp_smsf_accumulation() -> None:
    # TC-09 / §4.2: BHP $2,000 ff @ 30%, SMSF 0% pension → after-tax $2,428.57
    div = _div("2000")
    cfg = SMSFConfig(fund_pension_proportion=Decimal("0.0"))
    out = after_tax_dividend_smsf(div, cfg)
    assert _approx(out.after_tax_cash, "2428.57")


def test_tc19_mixed_phase_smsf_60pct() -> None:
    # TC-19 / §4.2: $1000 ff @ 30%, SMSF 60% pension → after-tax $1,342.86
    div = _div("1000")
    cfg = SMSFConfig(fund_pension_proportion=Decimal("0.6"))
    out = after_tax_dividend_smsf(div, cfg)
    assert _approx(out.after_tax_cash, "1342.86")


def test_individual_marginal_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="marginal_rate"):
        IndividualConfig(marginal_rate=Decimal("0.6"))


def test_smsf_pension_prop_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="fund_pension_proportion"):
        SMSFConfig(fund_pension_proportion=Decimal("1.5"))
