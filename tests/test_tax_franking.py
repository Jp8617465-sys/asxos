"""
Franking-credit boundary tests (spec §3).

Covers BRE (25%) vs default (30%) corporate rates, partial franking,
fully unfranked, and the registry-statement override path.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.tax.franking import franking_credit, grossed_up
from asxos.domain.tax.types import Dividend


def _div(
    cash: str,
    pct: str,
    rate: str = "0.30",
    override: str | None = None,
) -> Dividend:
    return Dividend(
        symbol="X.AU",
        pay_date=date(2026, 5, 1),
        cash_dividend=Decimal(cash),
        franking_pct=Decimal(pct),
        corporate_tax_rate=Decimal(rate),
        franking_credit_override=Decimal(override) if override else None,
    )


def test_full_franking_30pct_credit_per_spec_worked_example() -> None:
    # spec §3 worked example: $1000 cash, full franking, 30% → credit 428.57
    div = _div("1000", "1.0", "0.30")
    credit = franking_credit(div)
    assert credit == Decimal("1000") * Decimal("0.30") / Decimal("0.70")
    assert grossed_up(div) == Decimal("1000") + credit


def test_full_franking_25pct_base_rate_entity_credit() -> None:
    # spec §3 BRE worked example: same $1000, 25% rate → credit 333.33
    div = _div("1000", "1.0", "0.25")
    credit = franking_credit(div)
    assert credit == Decimal("1000") * Decimal("0.25") / Decimal("0.75")


def test_partial_franking_50pct() -> None:
    # 50% of $1000 is franked at 30% → only $500 carries credit
    div = _div("1000", "0.5", "0.30")
    credit = franking_credit(div)
    expected = Decimal("500") * Decimal("0.30") / Decimal("0.70")
    assert credit == expected


def test_unfranked_zero_credit() -> None:
    # spec §10: missing franking_pct treated as unfranked (0 credit)
    div = _div("1000", "0", "0.30")
    assert franking_credit(div) == Decimal("0")
    assert grossed_up(div) == Decimal("1000")


def test_registry_override_wins_over_formula() -> None:
    # spec §3 audit Issue 7: trust the credit on the statement
    div = _div("1000", "1.0", "0.30", override="500.00")
    assert franking_credit(div) == Decimal("500.00")


def test_zero_cash_with_credit_rejected() -> None:
    # spec §10: zero cash dividend with non-zero franking credit is malformed
    with pytest.raises(ValueError, match="malformed"):
        Dividend(
            symbol="X.AU",
            pay_date=date(2026, 5, 1),
            cash_dividend=Decimal("0"),
            franking_pct=Decimal("1.0"),
            franking_credit_override=Decimal("100"),
        )


def test_franking_pct_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="franking_pct"):
        Dividend(
            symbol="X.AU",
            pay_date=date(2026, 5, 1),
            cash_dividend=Decimal("100"),
            franking_pct=Decimal("1.5"),
        )


def test_corporate_tax_rate_must_be_below_one() -> None:
    div = _div("1000", "1.0", rate="1.0")
    with pytest.raises(ValueError, match="corporate_tax_rate"):
        franking_credit(div)
