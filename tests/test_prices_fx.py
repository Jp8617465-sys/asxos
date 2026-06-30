"""Tests for the foreign-symbol FX helper (asxos/domain/prices/fx.py).

The single source of truth for "is this a USD US-exchange holding?". The bug this
guards against: matching only `.US` and silently mishandling `.NYSE/.NASDAQ/.AMEX`.
"""
from __future__ import annotations

import pytest

from asxos.domain.prices.fx import (
    FOREIGN_SUFFIXES,
    foreign_symbol_sql,
    is_foreign_symbol,
)


@pytest.mark.parametrize("symbol", ["AAPL.US", "HUBS.NYSE", "MSFT.NASDAQ", "X.AMEX"])
def test_is_foreign_true_for_every_us_exchange(symbol: str) -> None:
    assert is_foreign_symbol(symbol) is True


@pytest.mark.parametrize("symbol", ["BHP.AU", "CBA.AU", "AXJO.INDX", "AUDUSD.FOREX", "BARE"])
def test_is_foreign_false_for_au_and_other(symbol: str) -> None:
    assert is_foreign_symbol(symbol) is False


def test_foreign_suffixes_covers_all_us_exchanges() -> None:
    # Locks the set — if an exchange is added, this test and the SQL must update together.
    assert FOREIGN_SUFFIXES == (".US", ".NYSE", ".NASDAQ", ".AMEX")


def test_foreign_symbol_sql_default_column() -> None:
    clause = foreign_symbol_sql()
    assert clause == (
        "(symbol LIKE '%.US' OR symbol LIKE '%.NYSE' "
        "OR symbol LIKE '%.NASDAQ' OR symbol LIKE '%.AMEX')"
    )


def test_foreign_symbol_sql_aliased_column() -> None:
    clause = foreign_symbol_sql("hl.symbol")
    # Every suffix is matched against the aliased column.
    assert clause.startswith("(hl.symbol LIKE '%.US'")
    for sfx in FOREIGN_SUFFIXES:
        assert f"hl.symbol LIKE '%{sfx}'" in clause
    # Parenthesised so it drops into a WHERE … AND <clause> safely.
    assert clause.startswith("(") and clause.endswith(")")


@pytest.mark.parametrize("bad", ["symbol; DROP TABLE x", "a b", "1col", "", "x'"])
def test_foreign_symbol_sql_rejects_non_identifier_column(bad: str) -> None:
    # The column arg is interpolated into SQL, so a non-identifier is refused —
    # belt-and-suspenders against a future caller routing untrusted input here.
    with pytest.raises(ValueError, match="plain identifier"):
        foreign_symbol_sql(bad)


def test_sql_clause_and_python_test_stay_in_sync() -> None:
    # Both derive from FOREIGN_SUFFIXES, so the SQL names exactly the suffixes
    # is_foreign_symbol matches — the property that prevents the stale-copy bug.
    clause = foreign_symbol_sql()
    for sfx in FOREIGN_SUFFIXES:
        assert is_foreign_symbol(f"ZZZ{sfx}")
        assert f"%{sfx}'" in clause
