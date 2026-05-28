"""
Tests for jobs/snapshot_portfolio.py.

Exercises all hard-fail and soft-degrade paths without a real DB.
Uses asyncpg Record-shaped dicts via unittest.mock.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.snapshot_portfolio as job_mod
from asxos.jobs._helpers import UpstreamBlocked


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(fetchrow_map: dict | None = None, fetch_map: dict | None = None) -> Any:
    """Return a mock asyncpg connection stub."""
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=None)

    _fr = fetchrow_map or {}
    _fc = fetch_map or {}

    async def _fetchrow(query, *args):
        # Simple dispatch by first arg keyword in the query
        for key, val in _fr.items():
            if key in query:
                return val
        return None

    async def _fetch(query, *args):
        for key, val in _fc.items():
            if key in query:
                return val
        return []

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    return conn


@asynccontextmanager
async def _pool_ctx(conn):
    yield conn


def _patch_acquire(conn):
    """Context manager that patches asxos.db.acquire and job_mod.acquire."""
    cm = asynccontextmanager(lambda: (x for x in [conn]))
    return patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AS_OF = date(2026, 5, 26)

_PROFILE_ROW = {"capital_aud": "100000.000000", "cash_floor_pct": "0.050000"}
_PRICES_ROWS = [
    {"symbol": "BHP.AU", "quantity": "100.000000", "close": "45.200000"},
    {"symbol": "CRM.US", "quantity": "10.000000", "close": "200.000000"},
]
_FX_ROW = {"rate": "0.625100"}  # AUDUSD: 1 AUD = 0.6251 USD


# ---------------------------------------------------------------------------
# 1. Happy path — holdings + prices + FX, no XJO yet (soft degrade)
# ---------------------------------------------------------------------------

def test_happy_path_writes_row(monkeypatch):
    """Holdings MV computed; XJO NULL (not in prices); row UPSERTed."""
    fetchrow_map = {
        "job_runs": {"status": "success"},
        "profiles WHERE is_active": _PROFILE_ROW,
        "AXJO.INDX": None,  # XJO not yet ingested
        "fx_rates": _FX_ROW,
    }
    fetch_map = {
        "current_holdings": _PRICES_ROWS,
    }
    conn = _make_conn(fetchrow_map, fetch_map)

    inserted_rows: list = []

    async def _execute(query, *args):
        if "INSERT INTO portfolio_daily_snapshots" in query:
            inserted_rows.append(args)

    conn.execute = _execute

    monitor = MagicMock()
    monitor.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    assert monitor.rows_written == 1
    assert len(inserted_rows) == 1
    args = inserted_rows[0]
    as_of_arg, capital_aud, holdings_mv_aud, cash_aud = args[0], args[1], args[2], args[3]
    benchmark_xjo_close = args[4]
    holdings_count = args[7]

    assert as_of_arg == AS_OF
    assert benchmark_xjo_close is None  # XJO soft-degrade
    assert holdings_count == 2

    # BHP: 100 * 45.20 = 4520 AUD
    # CRM: 10 * 200 / 0.6251 = 3199.something AUD
    expected_mv = Decimal("100") * Decimal("45.2") + Decimal("10") * Decimal("200") / Decimal("0.6251")
    assert abs(holdings_mv_aud - expected_mv.quantize(Decimal("0.000001"))) < Decimal("0.01")

    # cash = 0.05 * 100000 = 5000 AUD
    assert cash_aud == Decimal("5000.000000")
    assert capital_aud == (holdings_mv_aud + cash_aud).quantize(Decimal("0.000001"))


# ---------------------------------------------------------------------------
# 2. Upstream blocked — sync_prices not success
# ---------------------------------------------------------------------------

def test_upstream_blocked_raises():
    """UpstreamBlocked when sync_prices has no success row for as_of."""
    fetchrow_map = {
        "job_runs": None,  # no success row
    }
    conn = _make_conn(fetchrow_map)
    monitor = MagicMock()
    monitor.rows_written = 0  # pre-initialize so we can assert it wasn't set

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        with pytest.raises(UpstreamBlocked):
            asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    assert monitor.rows_written == 0  # never incremented before the exception


# ---------------------------------------------------------------------------
# 3. No active profile — hard-fail
# ---------------------------------------------------------------------------

def test_no_active_profile_raises():
    """RuntimeError when no active profile exists."""
    fetchrow_map = {
        "job_runs": {"status": "success"},
        "profiles WHERE is_active": None,  # no active profile
    }
    conn = _make_conn(fetchrow_map)
    monitor = MagicMock()

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        with pytest.raises(RuntimeError, match="No active profile"):
            asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))


# ---------------------------------------------------------------------------
# 4. Missing trailing yield — benchmark_tr_level stays NULL, row still written
# ---------------------------------------------------------------------------

def test_missing_trailing_yield_writes_null_benchmark(monkeypatch):
    """benchmark_tr_level=NULL when trailing yield is None; row written."""
    fetchrow_map = {
        "job_runs": {"status": "success"},
        "profiles WHERE is_active": _PROFILE_ROW,
        "AXJO.INDX": None,
        "fx_rates": _FX_ROW,
    }
    fetch_map = {"current_holdings": []}  # empty holdings
    conn = _make_conn(fetchrow_map, fetch_map)

    inserted_rows: list = []

    async def _execute(query, *args):
        if "INSERT INTO portfolio_daily_snapshots" in query:
            inserted_rows.append(args)

    conn.execute = _execute
    monitor = MagicMock()
    monitor.rows_written = 0

    monkeypatch.setattr(job_mod, "_fetch_trailing_div_yield", lambda: None)

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    assert monitor.rows_written == 1
    args = inserted_rows[0]
    benchmark_tr_level = args[5]
    trailing_div = args[6]
    holdings_count = args[7]
    assert benchmark_tr_level is None
    assert trailing_div is None
    assert holdings_count == 0  # empty holdings
    assert args[2] == Decimal("0")  # holdings_mv_aud = 0


# ---------------------------------------------------------------------------
# 5. Idempotency — second run for same as_of overwrites via UPSERT
# ---------------------------------------------------------------------------

def test_upsert_on_conflict(monkeypatch):
    """Running twice for same as_of executes ON CONFLICT DO UPDATE."""
    fetchrow_map = {
        "job_runs": {"status": "success"},
        "profiles WHERE is_active": _PROFILE_ROW,
        "AXJO.INDX": None,
        "fx_rates": _FX_ROW,
    }
    fetch_map = {"current_holdings": []}
    conn = _make_conn(fetchrow_map, fetch_map)

    execute_calls: list = []

    async def _execute(query, *args):
        if "INSERT INTO portfolio_daily_snapshots" in query:
            execute_calls.append(query)

    conn.execute = _execute

    monitor1 = MagicMock()
    monitor1.rows_written = 0
    monitor2 = MagicMock()
    monitor2.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor1))
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor2))

    assert len(execute_calls) == 2
    assert all("ON CONFLICT" in q for q in execute_calls)
    assert monitor1.rows_written == 1
    assert monitor2.rows_written == 1
