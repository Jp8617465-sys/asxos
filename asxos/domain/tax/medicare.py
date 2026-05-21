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


def medicare_levy_on(base: Decimal, *, account_type: AccountType) -> Decimal:
    """0 for super (spec §7); base * 0.02 for individuals (no low-income
    floor implemented in v1 — the user sets `medicare_levy_rate` to 0 in
    their config if they fall under the threshold per ATO publication)."""
    if account_type == "smsf":
        return Decimal("0")
    return base * MEDICARE_LEVY_RATE
