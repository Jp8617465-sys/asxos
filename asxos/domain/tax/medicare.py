"""
Medicare levy (spec §7).

Applies to taxable income for individuals only (s 251S(1)(a) ITAA 1936).
Taxable income includes the net capital gain (s 102-5, post-discount,
post-loss-offset) and grossed-up dividend income. The levy stacks on the
marginal rate at the same 2% on the same base.

The Medicare levy is already folded into the individual dividend path
(see after_tax_dividend_individual) by adding medicare_levy_rate to the
marginal rate. Here we expose a stand-alone helper for the net capital
gain branch of the tax-view aggregator.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.types import MEDICARE_LEVY_RATE, AccountType


def medicare_levy_on(
    base: Decimal, *, account_type: AccountType, rate: Decimal = MEDICARE_LEVY_RATE
) -> Decimal:
    """0 for super (spec §7); `base * rate` for individuals.

    `rate` defaults to the statutory 2% (MEDICARE_LEVY_RATE) but callers pass the
    taxpayer's configured `medicare_levy_rate` so a low-income individual (rate 0
    per the §7.1 ATO threshold) is honoured — consistently with the dividend path,
    which already folds `config.medicare_levy_rate` into the marginal rate. Passing
    the constant unconditionally was the Phase-1 regression this fixes.
    """
    if account_type == "smsf":
        return Decimal("0")
    return base * rate
