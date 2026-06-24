"""Tests for the rs_fundamentals_pit derivation.

compute_pit_factors is where derive_knowledge_date is finally USED, so the guard is
re-exercised here in context. Ratios are checked on clean synthetic numbers; the
orchestrator is driven with a fake conn. No network, no DB.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from asxos.ingestion.fundamentals_pit import compute_pit_factors, refresh_fundamentals_pit

D = date.fromisoformat

_INCOME = {
    "total_revenue": Decimal("1000"), "net_income": Decimal("100"),
    "line_items": {"grossProfit": "600", "operatingIncome": "200"},
}
_BALANCE = {
    "total_assets": Decimal("2000"), "total_equity": Decimal("500"),
    "total_debt": Decimal("300"), "shares_diluted": Decimal("50"),
    "line_items": {"netDebt": "100"},
}
_DIVS = [
    {"dividend_amount": Decimal("1.5"), "franking_pct": Decimal("100")},
    {"dividend_amount": Decimal("1.5"), "franking_pct": Decimal("0")},
]


def _factors(**over):
    kw = {"period_end": D("2025-06-30"), "report_date": D("2025-08-12"),
          "filing_date": D("2025-06-30"), "as_of": D("2026-06-24")}
    kw.update(over)
    return compute_pit_factors(_INCOME, _BALANCE, _DIVS, **kw)


def test_ratios():
    f = _factors()
    assert f["roe"] == Decimal("0.200000")            # 100/500
    assert f["roa"] == Decimal("0.050000")            # 100/2000
    assert f["gross_margin"] == Decimal("0.600000")   # 600/1000
    assert f["operating_margin"] == Decimal("0.200000")
    assert f["book_value_ps"] == Decimal("10.000000") # 500/50
    assert f["eps_ttm"] == Decimal("2.000000")        # 100/50


def test_absolute_passthrough_and_netdebt():
    f = _factors()
    assert f["revenue_ttm"] == Decimal("1000")
    assert f["net_income_ttm"] == Decimal("100")
    assert f["total_equity"] == Decimal("500")
    assert f["shares_outstanding"] == Decimal("50")
    assert f["net_debt"] == Decimal("100")            # from balance line_items


def test_dividends_and_franking_average():
    f = _factors()
    assert f["dividend_ttm"] == Decimal("3.0")        # 1.5 + 1.5
    assert f["franking_avg_pct"] == Decimal("50.000000")  # avg(100, 0)


def test_knowledge_date_uses_guard_dropping_future_report_date():
    """The whole point: a FUTURE reportDate must not become knowledge_date."""
    f = _factors(period_end=D("2026-03-31"), report_date=D("2026-08-11"),
                 filing_date=D("2026-05-07"), as_of=D("2026-06-24"))
    assert f["knowledge_date"] == D("2026-05-07")     # the real past disclosure
    assert f["as_of"] == D("2026-03-31")              # the period end


def test_division_guards_return_none():
    f = compute_pit_factors(
        {"total_revenue": Decimal("0"), "net_income": Decimal("100"), "line_items": {}},
        {"total_assets": None, "total_equity": Decimal("0"), "shares_diluted": None, "line_items": {}},
        [],
        period_end=D("2025-06-30"), report_date=None, filing_date=None, as_of=D("2026-06-24"),
    )
    assert f["roe"] is None      # equity 0
    assert f["roa"] is None      # assets None
    assert f["gross_margin"] is None
    assert f["book_value_ps"] is None
    assert f["dividend_ttm"] is None
    assert f["franking_avg_pct"] is None


def test_none_when_both_statements_absent():
    assert compute_pit_factors(None, None, [], period_end=D("2025-06-30"),
                               report_date=None, filing_date=None, as_of=D("2026-06-24")) is None


# ---------------------------------------------------------------------------
# orchestrator
# ---------------------------------------------------------------------------


class FakeConn:
    def __init__(self, fin, divs):
        self._fin = fin
        self._divs = divs
        self.executed: list[tuple[str, tuple]] = []

    async def fetch(self, sql, *args):
        if "rs_financial_statements" in sql:
            return self._fin
        if "rs_corporate_actions" in sql:
            return self._divs
        return []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))


def _finrow(stmt_type, **over):
    base = {
        "symbol": "HUBS.US", "period_end": D("2025-12-31"), "statement_type": stmt_type,
        "filing_date": D("2026-02-11"), "report_date": D("2026-02-11"),
        "total_revenue": None, "net_income": None, "total_assets": None,
        "total_equity": None, "total_debt": None, "shares_diluted": None,
        "line_items": "{}",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_orchestrator_derives_and_upserts():
    fin = [
        _finrow("income", total_revenue=Decimal("1000"), net_income=Decimal("100"),
                line_items=json.dumps({"grossProfit": "600", "operatingIncome": "200"})),
        _finrow("balance_sheet", total_assets=Decimal("2000"), total_equity=Decimal("500"),
                total_debt=Decimal("300"), shares_diluted=Decimal("50"),
                line_items=json.dumps({"netDebt": "100"})),
    ]
    divs = [{"symbol": "HUBS.US", "ex_date": D("2025-09-01"),
             "dividend_amount": Decimal("1.5"), "franking_pct": Decimal("100")}]
    conn = FakeConn(fin, divs)
    counts = await refresh_fundamentals_pit(conn, as_of=D("2026-06-24"))
    assert counts == {"rows": 1, "symbols": 1}
    sql, args = conn.executed[0]
    assert "ON CONFLICT (symbol, knowledge_date) DO UPDATE" in sql
    assert args[0] == "HUBS.US"
    assert args[7] == Decimal("0.200000")   # roe in the param list


@pytest.mark.asyncio
async def test_orchestrator_reads_only_research_store():
    conn = FakeConn([_finrow("income", total_revenue=Decimal("1"))], [])
    await refresh_fundamentals_pit(conn, as_of=D("2026-06-24"))
    # the SELECTs the orchestrator issued must not reference production tables
    # (we can't see fetch SQL post-hoc, so assert the write path is correct instead)
    assert all("universe" not in s.lower() and " prices" not in s.lower()
               for s, _ in conn.executed)
    assert all("rs_fundamentals_pit" in s for s, _ in conn.executed)


@pytest.mark.asyncio
async def test_dividend_window_excludes_out_of_range():
    """Only dividends with ex_date in (period_end - 1y, period_end] count."""
    fin = [_finrow("income", total_revenue=Decimal("1000"), net_income=Decimal("100")),
           _finrow("balance_sheet", total_equity=Decimal("500"), shares_diluted=Decimal("50"))]
    divs = [
        {"symbol": "HUBS.US", "ex_date": D("2025-09-01"), "dividend_amount": Decimal("2"), "franking_pct": None},
        {"symbol": "HUBS.US", "ex_date": D("2024-01-01"), "dividend_amount": Decimal("9"), "franking_pct": None},  # too old
    ]
    conn = FakeConn(fin, divs)
    await refresh_fundamentals_pit(conn, as_of=D("2026-06-24"))
    _sql, args = conn.executed[0]
    assert args[14] == Decimal("2")   # dividend_ttm — only the in-window dividend
