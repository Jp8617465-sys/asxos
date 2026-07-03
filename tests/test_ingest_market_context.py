"""Tests for jobs/ingest_market_context.py breadth computation.

Written alongside the first-live-run fixes (2026-07-03): the breadth SQL had
two bugs never caught because the job had never executed — a CTE alias
mismatch (m50/m200 vs ma50/ma200, an immediate UndefinedTableError) and a
highs10 CTE grouped by (symbol, close) whose join fan-out inflated every
denominator (total=9058 against a 1,874-symbol universe). The SQL semantics
were verified live against prod (the corrected query returns total exactly
equal to the active-universe count); these tests pin the Python-side ratio
math and the empty-universe path, which mocks CAN legitimately cover.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from jobs.ingest_market_context import _compute_breadth, _to_dec


class _FakeConn:
    def __init__(self, row):
        self._row = row
        self.queries: list[str] = []

    async def fetchrow(self, query, *args):
        self.queries.append(query)
        return self._row


@pytest.mark.asyncio
async def test_breadth_ratios_quantized_from_row():
    conn = _FakeConn(
        {"total": 1874, "above_50": 569, "above_200": 485, "new_highs": 299, "new_lows": 309}
    )
    out = await _compute_breadth(conn, date(2026, 7, 3))
    assert out["pct_above_50d_ma"] == Decimal("0.303629")
    assert out["pct_above_200d_ma"] == Decimal("0.258805")
    assert out["net_new_highs_lows_10d"] == Decimal("-0.005336")


@pytest.mark.asyncio
async def test_breadth_empty_universe_returns_nones():
    conn = _FakeConn({"total": 0, "above_50": 0, "above_200": 0, "new_highs": 0, "new_lows": 0})
    out = await _compute_breadth(conn, date(2026, 7, 3))
    assert out == {
        "pct_above_50d_ma": None,
        "pct_above_200d_ma": None,
        "net_new_highs_lows_10d": None,
    }


@pytest.mark.asyncio
async def test_breadth_sql_groups_highs_by_symbol_only():
    # Pin the fan-out fix: highs10 must group by symbol alone and the outer
    # SELECT must compare against window extremes, not per-close booleans.
    conn = _FakeConn({"total": 1, "above_50": 0, "above_200": 0, "new_highs": 0, "new_lows": 0})
    await _compute_breadth(conn, date(2026, 7, 3))
    sql = conn.queries[0]
    assert "GROUP  BY p.symbol, p.close" not in sql
    assert "win_high" in sql and "win_low" in sql
    assert "ma50.avg_close" in sql and "ma200.avg_close" in sql


def test_to_dec_edges():
    assert _to_dec(None) is None
    assert _to_dec("12.5") == Decimal("12.5")
    assert _to_dec(7) == Decimal("7")
    assert _to_dec("not-a-number") is None
