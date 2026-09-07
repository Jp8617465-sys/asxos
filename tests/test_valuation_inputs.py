"""The valuation's read surface: what it may touch, and what it must refuse."""
from __future__ import annotations

from decimal import Decimal

import pytest

from asxos.domain.valuation.inputs import (
    SQL_BALANCE,
    SQL_CLOSE,
    SQL_PIT,
    SQL_RISK_FREE,
    assert_valuation_sql_admissible,
    reconcile_roe_definition,
)

ALL_SQL = (SQL_PIT, SQL_BALANCE, SQL_RISK_FREE, SQL_CLOSE)


def test_shipped_sql_passes_its_own_screen() -> None:
    for sql in ALL_SQL:
        assert_valuation_sql_admissible(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT roe FROM fundamentals WHERE symbol = $1",
        "SELECT prob_up FROM signals WHERE symbol = $1",
        "SELECT x FROM signal_outcomes",
        "SELECT debt_to_equity FROM rs_fundamentals_pit WHERE symbol = $1",
        "SELECT net_debt FROM rs_fundamentals_pit",
        "SELECT gross_margin FROM rs_fundamentals_pit",
        "SELECT total_revenue FROM rs_financial_statements",
        "SELECT line_items->>'netInterestIncome' FROM rs_financial_statements",
        "SELECT * FROM holding_lots",
    ],
)
def test_the_screen_refuses_every_forbidden_read(sql: str) -> None:
    with pytest.raises(AssertionError):
        assert_valuation_sql_admissible(sql)


def test_the_all_null_fundamentals_table_is_unreadable_but_the_pit_table_is_not() -> None:
    """`fundamentals` has had no writer for five columns across 143,715 rows (C-18).

    The word boundary must block the legacy table without blocking
    rs_fundamentals_pit, which is where the real data lives.
    """
    with pytest.raises(AssertionError, match="fundamentals"):
        assert_valuation_sql_admissible("SELECT roe FROM fundamentals")
    assert_valuation_sql_admissible("SELECT roe FROM rs_fundamentals_pit WHERE symbol = $1")


def test_every_shipped_query_binds_its_parameters() -> None:
    for sql in ALL_SQL:
        assert "$1" in sql, sql


# --- the ROE definition reconciliation ---------------------------------------

def test_vendor_roe_on_period_end_equity_is_named_period_end() -> None:
    """Measured: all four majors match period-end, e.g. WBC 6910/72766 = 0.094962."""
    assert reconcile_roe_definition(
        Decimal("0.094962"), Decimal("6910"), Decimal("72766"), Decimal("61630")
    ) == "period_end"


def test_vendor_roe_on_average_equity_is_named_average() -> None:
    assert reconcile_roe_definition(
        Decimal("0.112121"), Decimal("6910"), Decimal("72766"), Decimal("61630")
    ) == "average"


def test_a_vendor_roe_matching_neither_definition_is_unknown_not_guessed() -> None:
    assert reconcile_roe_definition(
        Decimal("0.5"), Decimal("6910"), Decimal("72766"), Decimal("61630")
    ) == "unknown"


def test_an_absent_vendor_roe_is_named_absent() -> None:
    assert reconcile_roe_definition(
        None, Decimal("6910"), Decimal("72766"), Decimal("61630")
    ) == "vendor_roe_absent"
