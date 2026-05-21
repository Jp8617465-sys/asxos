"""
Franking-credit gross-up math (spec §3).

The system trusts the credit amount on the registry statement when one is
supplied (`franking_credit_override`). The formula here is the fallback /
validation path: not the production calculation. Per spec audit Issue 7.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.types import Dividend


def franking_credit(div: Dividend) -> Decimal:
    """
    spec §3: franking_credit = cash * franking_pct * rate / (1 - rate).

    Returns the registry-statement override if supplied; otherwise computes
    from cash, franking_pct, and corporate_tax_rate.
    """
    if div.franking_credit_override is not None:
        return div.franking_credit_override

    rate = div.corporate_tax_rate
    if rate >= Decimal("1") or rate < Decimal("0"):
        raise ValueError(f"corporate_tax_rate {rate} must be in [0, 1)")
    franked_portion = div.cash_dividend * div.franking_pct
    return franked_portion * rate / (Decimal("1") - rate)


def grossed_up(div: Dividend) -> Decimal:
    """Cash + franking credit (the amount included in assessable income)."""
    return div.cash_dividend + franking_credit(div)
