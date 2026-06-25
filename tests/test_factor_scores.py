"""Tests for sector-neutral factor scores (rs_factor_scores).

Pure-stdlib (no pandas/asyncpg needed): the factor math is checked on clean synthetic
numbers, sector-neutrality and degenerate-group handling are checked directly, and the
orchestrator is driven with a FakeConn that records the SQL it issues — so the
leak-safety filters (knowledge_date <= as_of, dt <= as_of) and the idempotent UPSERT
target are asserted without a DB. No network, no DB.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.research.factor_scores import (
    SymbolScore,
    _zscores,
    gross_franked_yield,
    momentum_12_1,
    neg_realised_vol,
    raw_factors,
    refresh_factor_scores,
    sector_neutral_scores,
)

D = date.fromisoformat


# ---------------------------------------------------------------------------
# Pure raw-factor functions
# ---------------------------------------------------------------------------


def test_momentum_12_1_skips_recent_month():
    # 253 points: index 0 = oldest (used as the 252-back price), index 231 = 21-back.
    series = [110.0] * 253
    series[0] = 100.0
    series[231] = 120.0
    assert momentum_12_1(series) == pytest.approx(0.20)  # 120/100 - 1


def test_momentum_none_when_too_short():
    assert momentum_12_1([100.0] * 252) is None
    assert momentum_12_1([]) is None


def test_neg_vol_lower_is_higher():
    flat = [100.0] * 130
    choppy = [100.0 + (5.0 if i % 2 else -5.0) for i in range(130)]
    assert neg_realised_vol(flat) == pytest.approx(0.0)
    assert neg_realised_vol(choppy) < neg_realised_vol(flat)  # more vol → more negative


def test_neg_vol_none_when_too_few():
    assert neg_realised_vol([100.0] * 10) is None


def test_gross_franked_yield_grosses_up_franking():
    # cash yield 0.05; 100% franked → credit = div * 1.0 * (0.3/0.7).
    y = gross_franked_yield(5.0, 100.0, 100.0)
    assert y == pytest.approx((5.0 + 5.0 * (0.30 / 0.70)) / 100.0)


def test_gross_franked_yield_unfranked_and_missing():
    assert gross_franked_yield(5.0, 0.0, 100.0) == pytest.approx(0.05)   # no credit
    assert gross_franked_yield(5.0, None, 100.0) == pytest.approx(0.05)  # NULL → 0 credit
    assert gross_franked_yield(None, 100.0, 100.0) is None               # no dividend
    assert gross_franked_yield(5.0, 100.0, 0.0) is None                  # no price


def test_raw_factors_value_is_a_yield():
    raw = raw_factors(
        eps_ttm=Decimal("5"), book_value_ps=Decimal("50"), roe=Decimal("0.2"),
        roa=Decimal("0.1"), gross_margin=Decimal("0.6"), operating_margin=Decimal("0.3"),
        dividend_ttm=Decimal("2"), franking_avg_pct=Decimal("100"),
        close=100.0, adj_closes=[100.0] * 5,
    )
    assert raw["earnings_yield"] == pytest.approx(0.05)  # 5/100 (higher = cheaper)
    assert raw["book_yield"] == pytest.approx(0.50)      # 50/100
    assert raw["roe"] == pytest.approx(0.2)
    assert raw["mom_12_1"] is None                       # series too short
    assert raw["gross_yield"] is not None


# ---------------------------------------------------------------------------
# Sector-neutral z-scoring
# ---------------------------------------------------------------------------


def test_zscores_basic_and_degenerate():
    z = _zscores({"a": 1.0, "b": 2.0, "c": 3.0})
    assert z["a"] == pytest.approx(-1.224745, abs=1e-5)
    assert z["b"] == pytest.approx(0.0, abs=1e-9)
    assert z["c"] == pytest.approx(1.224745, abs=1e-5)
    assert _zscores({"a": 5.0, "b": 5.0}) == {"a": 0.0, "b": 0.0}  # zero dispersion
    assert _zscores({"a": 5.0}) == {"a": 0.0}                      # single member
    assert "b" not in _zscores({"a": 1.0, "b": None, "c": 3.0})    # None omitted


def test_sector_neutrality_and_composite():
    tech1 = SymbolScore("T1.AU", "Tech", 1.0, raw={"earnings_yield": 0.05})
    tech2 = SymbolScore("T2.AU", "Tech", 1.0, raw={"earnings_yield": 0.10})
    # Different sector, different raw — must be scored INDEPENDENTLY (z=0, alone).
    mine1 = SymbolScore("M1.AU", "Mining", 1.0, raw={"earnings_yield": 0.99})
    sector_neutral_scores([tech1, tech2, mine1])

    assert tech1.value_score == pytest.approx(-1.0)   # cheaper-than-peer within Tech
    assert tech2.value_score == pytest.approx(1.0)
    assert mine1.value_score == pytest.approx(0.0)     # alone in its sector → no signal
    # quality absent → category None; composite = mean of present (value only).
    assert tech1.quality_score is None
    assert tech1.composite_score == pytest.approx(-1.0)
    assert tech1.n_factors_present == 1                 # only value present


def test_null_sector_bucketed_together_not_dropped():
    a = SymbolScore("A.AU", None, 1.0, raw={"roe": 0.1})
    b = SymbolScore("B.AU", "", 1.0, raw={"roe": 0.3})
    sector_neutral_scores([a, b])
    # both fall in the "__none__" bucket and are scored relative to each other.
    assert a.quality_score == pytest.approx(-1.0)
    assert b.quality_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Orchestrator — leak-safety + idempotent UPSERT (FakeConn)
# ---------------------------------------------------------------------------


class FakeConn:
    def __init__(self, pit, prices):
        self._pit = pit
        self._prices = prices
        self.fetched: list[str] = []
        self.executed: list[tuple[str, tuple]] = []

    async def fetch(self, sql, *args):
        self.fetched.append(sql)
        if "rs_fundamentals_pit" in sql:
            return self._pit
        if "FROM prices" in sql:
            return self._prices
        return []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))


def _pit_row(sym="CBA.AU", **over):
    base = {
        "symbol": sym, "eps_ttm": Decimal("6"), "book_value_ps": Decimal("40"),
        "roe": Decimal("0.13"), "roa": Decimal("0.01"), "gross_margin": None,
        "operating_margin": None, "dividend_ttm": Decimal("4"),
        "franking_avg_pct": Decimal("100"), "shares_outstanding": Decimal("1000"),
        "knowledge_date": D("2025-08-12"), "sector": "Financials",
    }
    base.update(over)
    return base


def _price_row(sym, dt, close, adj):
    return {"symbol": sym, "dt": D(dt), "close": Decimal(str(close)), "adj_close": Decimal(str(adj))}


@pytest.mark.asyncio
async def test_orchestrator_writes_factor_scores_and_market_cap():
    pit = [_pit_row(shares_outstanding=Decimal("1000"))]
    prices = [_price_row("CBA.AU", "2026-06-23", 100, 100), _price_row("CBA.AU", "2026-06-24", 110, 110)]
    conn = FakeConn(pit, prices)
    counts = await refresh_factor_scores(conn, as_of=D("2026-06-24"))
    assert counts == {"symbols": 1, "rows": 1}

    sql, args = conn.executed[0]
    assert "ON CONFLICT (symbol, as_of, factor_set_version) DO UPDATE" in sql
    assert "rs_factor_scores" in sql
    assert args[0] == "CBA.AU"
    assert args[2] == "fs_v1"
    assert args[4] == Decimal("110000.000000")  # market_cap = 1000 shares * last close 110
    # value, quality AND yield present; momentum/low_vol need long price history → absent.
    assert args[11] == 3


@pytest.mark.asyncio
async def test_orchestrator_is_leak_safe():
    conn = FakeConn([_pit_row()], [_price_row("CBA.AU", "2026-06-24", 100, 100)])
    await refresh_factor_scores(conn, as_of=D("2026-06-24"))
    # PIT load filters on the guarded knowledge_date; price load on dt — never as_of of
    # the underlying fact. No production `universe` is read or written.
    assert any("knowledge_date <= $1" in s for s in conn.fetched)
    assert any("dt <= $1" in s for s in conn.fetched)
    assert all("universe" not in s.lower() for s in conn.fetched)
    assert all("rs_factor_scores" in s for s, _ in conn.executed)


@pytest.mark.asyncio
async def test_orchestrator_skips_symbol_with_no_usable_data():
    # No price → no market cap; single-name sector → all z=0 but categories present.
    # A row with neither fundamentals-derived factors NOR market cap is skipped.
    pit = [_pit_row(eps_ttm=None, book_value_ps=None, roe=None, roa=None,
                    gross_margin=None, operating_margin=None, dividend_ttm=None,
                    franking_avg_pct=None, shares_outstanding=None)]
    conn = FakeConn(pit, [])  # no prices at all
    counts = await refresh_factor_scores(conn, as_of=D("2026-06-24"))
    assert counts == {"symbols": 1, "rows": 0}
    assert conn.executed == []
