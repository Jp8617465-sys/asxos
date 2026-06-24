"""Tests for research-store corporate-actions ingestion.

No network, no DB. Heavy on the pure parse/transform helpers (where the real risk
lives — the "<float>%" franking format and "new/old" splits that the 2026-06-24 probe
surfaced), plus a light orchestrator test with faked client/conn.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.ingestion.corporate_actions import (
    parse_franking,
    parse_split_ratio,
    refresh_corporate_actions,
    to_dividend_rows,
    to_split_rows,
)

# ---------------------------------------------------------------------------
# parse_franking — the format the probe forced us to get right
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("100%", Decimal("100")),
    ("0%", Decimal("0")),
    ("25.03%", Decimal("25.03")),   # decimals are real (QBE)
    ("90.47%", Decimal("90.47")),   # (TLS)
    ("49%", Decimal("49")),
    (None, None),                   # undeclared -> NULL, NOT 0
    ("", None),
    ("   ", None),
    ("150%", None),                 # out of range -> NULL
    ("-5%", None),
    ("abc", None),
    ("100", Decimal("100")),        # tolerate a bare number
])
def test_parse_franking(raw, expected):
    assert parse_franking(raw) == expected


def test_parse_franking_null_is_not_zero():
    """The tax-material distinction: undeclared (None) must not collapse to 0%."""
    assert parse_franking(None) is None
    assert parse_franking("0%") == Decimal("0")


# ---------------------------------------------------------------------------
# parse_split_ratio
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("2.000000/1.000000", Decimal("2")),
    ("7.000000/1.000000", Decimal("7")),
    ("0.993600/1.000000", Decimal("0.9936")),   # consolidation (CBA 1996)
    ("4.000000/1.000000", Decimal("4")),
    (None, None),
    ("", None),
    ("x/y", None),
    ("1.0/0.0", None),                           # zero divisor -> NULL
])
def test_parse_split_ratio(raw, expected):
    assert parse_split_ratio(raw) == expected


# ---------------------------------------------------------------------------
# to_dividend_rows / to_split_rows
# ---------------------------------------------------------------------------

_CBA_DIV = [{
    "date": "2026-02-18", "paymentDate": "2026-03-30", "recordDate": None,
    "period": "Final", "franking": "100%", "value": 2.35, "unadjustedValue": 2.35,
    "currency": "AUD",
}]
_AAPL_DIV = [{
    "date": "2026-05-11", "paymentDate": "2026-05-14", "recordDate": "2026-05-11",
    "period": "Quarterly", "value": 0.27, "unadjustedValue": 0.27, "currency": "USD",
}]


def test_to_dividend_rows_au_with_franking():
    (row,) = to_dividend_rows(_CBA_DIV, "CBA.AU")
    assert row[0] == "CBA.AU"
    assert row[1] == date(2026, 2, 18)        # ex_date
    assert row[2] == "dividend"
    assert row[3] is None                      # split_ratio
    assert row[4] == Decimal("2.35")           # dividend_amount (unadjustedValue)
    assert row[5] == Decimal("100")            # franking_pct
    assert row[6] == date(2026, 3, 30)         # pay_date
    assert row[7] is None                      # record_date (null in source)


def test_to_dividend_rows_us_has_no_franking():
    (row,) = to_dividend_rows(_AAPL_DIV, "AAPL.US")
    assert row[5] is None                      # no franking key on US names


def test_to_dividend_rows_prefers_unadjusted_over_value():
    raw = [{"date": "2020-01-01", "value": 1.0, "unadjustedValue": 4.0}]
    assert to_dividend_rows(raw, "X.AU")[0][4] == Decimal("4.0")


def test_to_dividend_rows_falls_back_to_value():
    raw = [{"date": "2020-01-01", "value": 1.5}]   # no unadjustedValue
    assert to_dividend_rows(raw, "X.AU")[0][4] == Decimal("1.5")


def test_to_dividend_rows_skips_missing_ex_date():
    raw = [{"value": 1.0}, {"date": "2026-01-01", "value": 2.0}]
    rows = to_dividend_rows(raw, "X.AU")
    assert len(rows) == 1
    assert rows[0][1] == date(2026, 1, 1)


def test_to_dividend_rows_empty_and_nonlist():
    assert to_dividend_rows([], "X.AU") == []
    assert to_dividend_rows(None, "X.AU") == []
    assert to_dividend_rows({"error": "x"}, "X.AU") == []


def test_to_split_rows():
    raw = [{"date": "2020-08-31", "split": "4.000000/1.000000"}]
    (row,) = to_split_rows(raw, "AAPL.US")
    assert row == ("AAPL.US", date(2020, 8, 31), "split", Decimal("4"), None, None, None, None)


def test_to_split_rows_empty_and_nonlist():
    assert to_split_rows([], "X.AU") == []
    assert to_split_rows(None, "X.AU") == []


# ---------------------------------------------------------------------------
# refresh_corporate_actions — orchestrator
# ---------------------------------------------------------------------------


class FakeClient:
    def __init__(self, divs: dict, splits: dict, errors: set | None = None) -> None:
        self._divs = divs
        self._splits = splits
        self._errors = errors or set()

    async def dividends(self, symbol: str):
        if symbol in self._errors:
            raise RuntimeError("boom")
        return self._divs.get(symbol, [])

    async def splits(self, symbol: str):
        if symbol in self._errors:
            raise RuntimeError("boom")
        return self._splits.get(symbol, [])


class FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple]] = []

    async def execute(self, sql: str, *args):
        self.executed.append((sql, args))


@pytest.mark.asyncio
async def test_refresh_counts_and_upsert_shape():
    client = FakeClient(
        divs={"CBA.AU": _CBA_DIV, "BHP.AU": []},
        splits={"AAPL.US": [{"date": "2020-08-31", "split": "4.000000/1.000000"}]},
    )
    conn = FakeConn()
    counts = await refresh_corporate_actions(
        client, conn, ["CBA.AU", "BHP.AU", "AAPL.US"], concurrency=2
    )
    assert counts["dividends"] == 1
    assert counts["splits"] == 1
    assert counts["symbols_with_actions"] == 2     # CBA (div) + AAPL (split)
    assert counts["failed"] == 0
    # every write is an idempotent UPSERT on the composite PK
    assert all("ON CONFLICT (symbol, ex_date, action_type) DO UPDATE" in s for s, _ in conn.executed)


@pytest.mark.asyncio
async def test_refresh_does_not_touch_universe_or_prices():
    client = FakeClient(divs={"CBA.AU": _CBA_DIV}, splits={})
    conn = FakeConn()
    await refresh_corporate_actions(client, conn, ["CBA.AU"], concurrency=1)
    for sql, _ in conn.executed:
        low = sql.lower()
        assert "universe" not in low
        assert " prices" not in low
        assert "rs_corporate_actions" in low


@pytest.mark.asyncio
async def test_refresh_tolerates_per_symbol_errors():
    client = FakeClient(divs={"OK.AU": _CBA_DIV}, splits={}, errors={"BAD.AU"})
    conn = FakeConn()
    counts = await refresh_corporate_actions(client, conn, ["OK.AU", "BAD.AU"], concurrency=2)
    assert counts["failed"] == 1
    assert counts["dividends"] == 1   # the good symbol still processed


@pytest.mark.asyncio
async def test_refresh_action_type_recorded_in_args():
    client = FakeClient(divs={"CBA.AU": _CBA_DIV}, splits={"CBA.AU": [{"date": "1996-05-27", "split": "0.993600/1.000000"}]})
    conn = FakeConn()
    await refresh_corporate_actions(client, conn, ["CBA.AU"], concurrency=1)
    action_types = {args[2] for _s, args in conn.executed}
    assert action_types == {"dividend", "split"}
