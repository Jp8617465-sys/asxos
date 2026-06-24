"""Tests for research-store financial-statements ingestion.

The centerpiece is derive_knowledge_date — the point-in-time leak guard. The rest
covers the statement transform (promoted columns, report_date join, future skip) and
the orchestrator. No network, no DB.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from asxos.ingestion.financial_statements import (
    derive_knowledge_date,
    refresh_financial_statements,
    to_statement_rows,
)

D = date.fromisoformat

# ---------------------------------------------------------------------------
# derive_knowledge_date — the leak guard (the whole point of this job)
# ---------------------------------------------------------------------------


def test_future_report_date_is_dropped_for_past_filing():
    """The exact hazard: a FUTURE/scheduled reportDate must never become knowledge_date.
    Falls back to the real (past) filing_date."""
    kd = derive_knowledge_date(
        period_end=D("2026-03-31"),
        report_date=D("2026-08-11"),   # future / scheduled vs as_of
        filing_date=D("2026-05-07"),   # real past disclosure
        as_of=D("2026-06-24"),
    )
    assert kd == D("2026-05-07")


def test_both_future_falls_back_to_period_end_plus_lag():
    kd = derive_knowledge_date(
        period_end=D("2026-06-30"),
        report_date=D("2026-08-11"),
        filing_date=D("2026-06-30"),   # defaulted to period_end -> not > period_end
        as_of=D("2026-06-24"),
        lag_days=75,
    )
    assert kd == D("2026-09-13")   # 2026-06-30 + 75d (both disclosure dates unusable)


def test_defaulted_to_period_end_is_ignored():
    """filing_date == period_end (no real lag) must not be used; reportDate wins."""
    kd = derive_knowledge_date(
        period_end=D("2025-06-30"),
        report_date=D("2025-08-12"),
        filing_date=D("2025-06-30"),   # defaulted -> dropped (not > period_end)
        as_of=D("2026-06-24"),
    )
    assert kd == D("2025-08-12")


def test_returns_max_of_valid_candidates():
    kd = derive_knowledge_date(
        period_end=D("2025-12-31"),
        report_date=D("2026-02-11"),
        filing_date=D("2026-02-10"),
        as_of=D("2026-06-24"),
    )
    assert kd == D("2026-02-11")   # the later real disclosure


def test_both_none_uses_lag():
    kd = derive_knowledge_date(
        period_end=D("2024-06-30"), report_date=None, filing_date=None,
        as_of=D("2026-06-24"), lag_days=60,
    )
    assert kd == D("2024-08-29")   # +60d


def test_lag_days_parameter_respected():
    a = derive_knowledge_date(D("2024-06-30"), None, None, D("2026-06-24"), lag_days=75)
    b = derive_knowledge_date(D("2024-06-30"), None, None, D("2026-06-24"), lag_days=60)
    assert (a - b).days == 15


# ---------------------------------------------------------------------------
# to_statement_rows
# ---------------------------------------------------------------------------

_FUND = {
    "Earnings": {"History": {
        "2025-12-31": {"date": "2025-12-31", "reportDate": "2026-02-11"},
        "2026-06-30": {"date": "2026-06-30", "reportDate": "2026-08-05"},  # future, no stmt
    }},
    "Financials": {
        "Income_Statement": {"currency_symbol": "USD", "yearly": {
            "2025-12-31": {"date": "2025-12-31", "filing_date": "2026-02-11",
                            "currency_symbol": "USD", "totalRevenue": "3131244000.00",
                            "netIncome": "45911000.00"},
        }, "quarterly": {}},
        "Balance_Sheet": {"currency_symbol": "USD", "yearly": {
            "2025-12-31": {"date": "2025-12-31", "filing_date": "2026-02-11",
                            "totalAssets": "3854151000.00", "totalStockholderEquity": "2066244000.00",
                            "shortLongTermDebtTotal": "484907000.00",
                            "commonStockSharesOutstanding": "53194000.00"},
        }, "quarterly": {}},
        "Cash_Flow": {"yearly": {
            "2025-12-31": {"date": "2025-12-31", "filing_date": "2026-02-11",
                            "freeCashFlow": "900000000.00"},
        }, "quarterly": {}},
    },
}


def _by_type(rows):
    return {r[3]: r for r in rows}   # statement_type -> row


def test_to_statement_rows_three_statements():
    rows = to_statement_rows(_FUND, "HUBS.US", as_of=D("2026-06-24"))
    by = _by_type(rows)
    assert set(by) == {"income", "balance_sheet", "cash_flow"}


def test_income_promotes_revenue_and_net_income():
    r = _by_type(to_statement_rows(_FUND, "HUBS.US", as_of=D("2026-06-24")))["income"]
    # tuple: symbol,period_end,period_type,statement_type,filing,report,currency,
    #        total_revenue,net_income,total_assets,total_equity,total_debt,shares,line_items
    assert r[1] == D("2025-12-31")
    assert r[5] == D("2026-02-11")            # report_date joined from Earnings.History
    assert r[7] == Decimal("3131244000.00")   # total_revenue
    assert r[8] == Decimal("45911000.00")     # net_income
    assert r[9] is None                        # total_assets N/A on income row


def test_balance_sheet_promotes_assets_equity_debt_shares():
    r = _by_type(to_statement_rows(_FUND, "HUBS.US", as_of=D("2026-06-24")))["balance_sheet"]
    assert r[9] == Decimal("3854151000.00")    # total_assets
    assert r[10] == Decimal("2066244000.00")   # total_equity
    assert r[11] == Decimal("484907000.00")    # total_debt
    assert r[12] == Decimal("53194000.00")     # shares_diluted (period-end shares)
    assert r[7] is None                         # total_revenue N/A on balance row


def test_line_items_jsonb_is_full_statement():
    r = _by_type(to_statement_rows(_FUND, "HUBS.US", as_of=D("2026-06-24")))["cash_flow"]
    li = json.loads(r[13])
    assert li["freeCashFlow"] == "900000000.00"   # full raw statement preserved


def test_skips_future_period_end():
    """A statement dated after as_of (unreported) is never ingested."""
    fund = {"Financials": {"Income_Statement": {"yearly": {
        "2027-12-31": {"date": "2027-12-31", "totalRevenue": "1"},
    }}}}
    assert to_statement_rows(fund, "X.AU", as_of=D("2026-06-24")) == []


def test_nonlist_and_empty_safe():
    assert to_statement_rows(None, "X.AU", as_of=D("2026-06-24")) == []
    assert to_statement_rows({}, "X.AU", as_of=D("2026-06-24")) == []


# ---------------------------------------------------------------------------
# refresh_financial_statements — orchestrator
# ---------------------------------------------------------------------------


class FakeClient:
    def __init__(self, funds: dict, errors: set | None = None) -> None:
        self._funds = funds
        self._errors = errors or set()

    async def fundamentals(self, symbol: str):
        if symbol in self._errors:
            raise RuntimeError("boom")
        return self._funds.get(symbol, {})


class FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple]] = []

    async def execute(self, sql: str, *args):
        self.executed.append((sql, args))


@pytest.mark.asyncio
async def test_refresh_counts_and_idempotent_upsert():
    client = FakeClient({"HUBS.US": _FUND, "EMPTY.AU": {}})
    conn = FakeConn()
    counts = await refresh_financial_statements(
        client, conn, ["HUBS.US", "EMPTY.AU"], as_of=D("2026-06-24"), concurrency=2
    )
    assert counts["statements"] == 3
    assert counts["symbols_with_statements"] == 1
    assert counts["failed"] == 0
    assert all(
        "ON CONFLICT (symbol, period_end, period_type, statement_type) DO UPDATE" in s
        for s, _ in conn.executed
    )


@pytest.mark.asyncio
async def test_refresh_tolerates_errors_and_avoids_prod_tables():
    client = FakeClient({"OK.US": _FUND}, errors={"BAD.AU"})
    conn = FakeConn()
    counts = await refresh_financial_statements(
        client, conn, ["OK.US", "BAD.AU"], as_of=D("2026-06-24"), concurrency=2
    )
    assert counts["failed"] == 1
    assert counts["statements"] == 3
    for sql, _ in conn.executed:
        low = sql.lower()
        assert "universe" not in low
        assert " prices" not in low
        assert "rs_financial_statements" in low
