"""
After-tax dividend calculations (spec §4).

Two paths:
- Individual (§4.1): marginal + Medicare on grossed-up; franking offset is the
  full credit when refundable (default for individuals per s 67-25).
- SMSF (§4.2): proportionate method per s 295-390. ECPI component is exempt,
  taxable component at 15%, franking credit fully refundable under Div 207.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.franking import franking_credit, grossed_up
from asxos.domain.tax.types import (
    SMSF_TAX_RATE,
    Dividend,
    DividendOutcome,
    IndividualConfig,
    SMSFConfig,
)


def after_tax_dividend_individual(
    div: Dividend, cfg: IndividualConfig
) -> DividendOutcome:
    """spec §4.1 — marginal + Medicare on grossed-up; franking offset."""
    credit = franking_credit(div)
    gross = div.cash_dividend + credit
    tax_assessed = gross * (cfg.marginal_rate + cfg.medicare_levy_rate)
    offset = credit if cfg.franking_refundable else min(credit, tax_assessed)
    net_tax = tax_assessed - offset
    return DividendOutcome(
        cash_dividend=div.cash_dividend,
        franking_credit=credit,
        grossed_up=gross,
        tax_assessed=tax_assessed,
        franking_offset=offset,
        net_tax=net_tax,
        after_tax_cash=div.cash_dividend - net_tax,
    )


def after_tax_dividend_smsf(
    div: Dividend, cfg: SMSFConfig
) -> DividendOutcome:
    """spec §4.2 — proportionate method (s 295-390).

    The ECPI component is exempt. The taxable component is taxed at 15%. The
    full franking credit remains an offset/refund per s 67-25 + Div 207,
    regardless of how much of the dividend is ECPI.
    """
    credit = franking_credit(div)
    gross = div.cash_dividend + credit
    exempt = gross * cfg.fund_pension_proportion
    taxable = gross - exempt
    fund_tax = taxable * SMSF_TAX_RATE
    offset = credit  # spec §4.2: full credit retained
    net_tax = fund_tax - offset  # negative = refund
    return DividendOutcome(
        cash_dividend=div.cash_dividend,
        franking_credit=credit,
        grossed_up=gross,
        tax_assessed=fund_tax,
        franking_offset=offset,
        net_tax=net_tax,
        after_tax_cash=div.cash_dividend - net_tax,
    )


def grossed_up_amount(div: Dividend) -> Decimal:
    """Helper re-export — same as franking.grossed_up. Useful for tests."""
    return grossed_up(div)
