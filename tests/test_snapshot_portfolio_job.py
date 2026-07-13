"""
Tests for jobs/snapshot_portfolio.py.

Exercises all hard-fail and soft-degrade paths without a real DB.
Uses asyncpg Record-shaped dicts via unittest.mock.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
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


def test_nyse_holding_is_fx_converted(monkeypatch):
    """A .NYSE holding (USD close) must be FX-converted like .US — the bug being
    fixed booked it 1:1 into holdings_mv_aud. Regression guard for task #7."""
    holdings = [
        {"symbol": "BHP.AU", "quantity": "100.000000", "close": "45.200000"},
        {"symbol": "HUBS.NYSE", "quantity": "5.000000", "close": "150.000000"},
    ]
    fetchrow_map = {
        "job_runs": {"status": "success"},
        "profiles WHERE is_active": _PROFILE_ROW,
        "fx_rates": _FX_ROW,  # AUDUSD 0.6251
    }
    fetch_map = {
        "current_holdings": holdings,
        # the us_cost query now matches all foreign suffixes
        "SUM(hl.cost_base_normal)": [{"total_cost_aud": Decimal("7000.000000")}],
    }
    conn = _make_conn(fetchrow_map, fetch_map)

    inserted: list = []

    async def _execute(query, *args):
        if "INSERT INTO portfolio_daily_snapshots" in query:
            inserted.append(args)

    conn.execute = _execute
    monitor = MagicMock()
    monitor.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    args = inserted[0]
    holdings_mv_aud = args[2]
    us_mv_aud = args[8]
    us_cost_aud = args[9]

    # BHP 100*45.2 = 4520 AUD; HUBS.NYSE 5*150/0.6251 = 1199.808... AUD (NOT 750)
    hubs_aud = Decimal("5") * Decimal("150") / Decimal("0.6251")
    expected_total = (Decimal("4520") + hubs_aud).quantize(Decimal("0.000001"))
    assert abs(holdings_mv_aud - expected_total) < Decimal("0.01")
    # us_mv_aud is the .NYSE leg only (FX-converted) — proves it wasn't booked 1:1
    assert abs(us_mv_aud - hubs_aud.quantize(Decimal("0.000001"))) < Decimal("0.01")
    assert holdings_mv_aud > Decimal("5000")  # the buggy 1:1 path would give 5270
    # cost query now matches .NYSE → us_cost_aud populated (was NULL under '%.US')
    assert us_cost_aud == Decimal("7000.000000")


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
# 4. No benchmark index in prices — both benchmark columns stay NULL, row written
# ---------------------------------------------------------------------------

def test_no_index_writes_null_benchmark():
    """benchmark_xjo_close + benchmark_tr_level NULL when neither index is in
    prices (default-None dispatch); row still written."""
    fetchrow_map = {
        "job_runs": {"status": "success"},
        "profiles WHERE is_active": _PROFILE_ROW,
        "fx_rates": _FX_ROW,
        # the prices query (symbol param) falls through to the None default for
        # both AXJO.INDX and the accumulation symbol.
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

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    assert monitor.rows_written == 1
    args = inserted_rows[0]
    benchmark_xjo_close = args[4]
    benchmark_tr_level = args[5]
    trailing_div = args[6]
    holdings_count = args[7]
    assert benchmark_xjo_close is None
    assert benchmark_tr_level is None
    assert trailing_div is None
    assert holdings_count == 0  # empty holdings
    assert args[2] == Decimal("0")  # holdings_mv_aud = 0


# ---------------------------------------------------------------------------
# 4b. benchmark_tr_level — accumulation index path + approximation path
# ---------------------------------------------------------------------------

def test_accumulation_tr_level_epoch_is_identity():
    # At the epoch the overlay factor is 1 → tr level == price close.
    assert job_mod._accumulation_tr_level(
        Decimal("8000"), job_mod._TR_EPOCH
    ) == Decimal("8000.000000")


def test_accumulation_tr_level_overlay_is_positive_after_epoch():
    assert job_mod._accumulation_tr_level(Decimal("8000"), date(2021, 6, 1)) > Decimal("8000")


def test_accumulation_tr_level_ratio_cancels_epoch():
    # The brief uses tr(t1)/tr(t0); the epoch cancels, leaving (1+yield)^Δyears.
    # 2022-01-01 → 2023-01-01 is exactly 365 days → ratio == 1 + _ASX200_TR_YIELD.
    c = Decimal("8000")
    t0 = job_mod._accumulation_tr_level(c, date(2022, 1, 1))
    t1 = job_mod._accumulation_tr_level(c, date(2023, 1, 1))
    expected = Decimal("1") + job_mod._ASX200_TR_YIELD
    assert abs(t1 / t0 - expected) < Decimal("0.0001")


def _index_conn(xjo_close: str | None, accum_close: str | None):
    """A conn whose prices fetchrow routes by the symbol arg, so the price index
    and the accumulation index can return different values (the substring-based
    _make_conn cannot, since both issue the same query string)."""
    conn = MagicMock()

    async def _fetchrow(query, *args):
        if "job_runs" in query:
            return {"status": "success"}
        if "profiles WHERE is_active" in query:
            return _PROFILE_ROW
        if "FROM prices WHERE symbol" in query:
            sym = args[0]
            if sym == job_mod._XJO_SYMBOL and xjo_close is not None:
                return {"close": xjo_close}
            if sym == job_mod._XJO_TR_SYMBOL and accum_close is not None:
                return {"close": accum_close}
            return None
        if "fx_rates" in query:
            return _FX_ROW
        return None

    async def _fetch(query, *args):
        return []

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    return conn


def test_benchmark_tr_level_approximation_when_only_price_index():
    """AXJO.INDX present, accumulation absent → tr is the documented overlay and
    trailing_div_yield_pct records the assumed yield."""
    conn = _index_conn(xjo_close="8000.000000", accum_close=None)
    inserted: list = []

    async def _execute(query, *args):
        if "INSERT INTO portfolio_daily_snapshots" in query:
            inserted.append(args)

    conn.execute = _execute
    monitor = MagicMock()
    monitor.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    args = inserted[0]
    assert args[4] == Decimal("8000.000000")          # benchmark_xjo_close
    assert args[5] > Decimal("8000")                  # benchmark_tr_level (overlay)
    assert args[6] == job_mod._ASX200_TR_YIELD * Decimal("100")  # trailing_div_yield_pct


def test_benchmark_tr_level_prefers_real_accumulation_index():
    """Accumulation index present → tr uses it verbatim, trailing yield NULL."""
    conn = _index_conn(xjo_close="8000.000000", accum_close="9999.000000")
    inserted: list = []

    async def _execute(query, *args):
        if "INSERT INTO portfolio_daily_snapshots" in query:
            inserted.append(args)

    conn.execute = _execute
    monitor = MagicMock()
    monitor.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    args = inserted[0]
    assert args[5] == Decimal("9999.000000")  # benchmark_tr_level = real index
    assert args[6] is None                    # trailing_div_yield_pct (index embeds divs)


# ---------------------------------------------------------------------------
# 5. --from backfill gate-skip (M2 must-fix)
# ---------------------------------------------------------------------------

class _FixedDate(_dt.date):
    """Subclass of date that overrides today() for test isolation."""

    _today: _dt.date = _dt.date(2026, 5, 30)  # Saturday — loop covers Wed/Thu/Fri

    @classmethod
    def today(cls) -> _dt.date:  # type: ignore[override]
        return cls._today


class _FakeJobMonitor:
    """Minimal async context manager standing in for JobMonitor."""

    def __init__(self, **kwargs: object) -> None:
        self.rows_written = 0

    async def __aenter__(self) -> _FakeJobMonitor:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


def test_backfill_from_skips_blocked_day():
    """--from backfill warns and skips days with no sync_prices success row
    instead of raising UpstreamBlocked, then continues to OK days.

    Range: 2026-05-27 (Wed, ok) / 2026-05-28 (Thu, ok) / 2026-05-29 (Fri, BLOCKED).
    Today capped at 2026-05-30 (Sat) so the loop ends after Friday.
    Assert: only Wed + Thu are snapshotted; Fri is silently skipped, no exception.
    """
    from_date = _dt.date(2026, 5, 27)
    ok_dates = {_dt.date(2026, 5, 27), _dt.date(2026, 5, 28)}

    synced_days: list[_dt.date] = []

    async def fake_snapshot_one_day(as_of: _dt.date, monitor: object) -> None:
        synced_days.append(as_of)

    gate_conn = MagicMock()

    async def _gate_fetchrow(query: str, *args: object) -> dict | None:
        if "job_runs" in query:
            return {"status": "success"} if args[0] in ok_dates else None
        return None

    gate_conn.fetchrow = _gate_fetchrow

    async def run() -> None:
        with (
            patch.object(job_mod, "init_pool", AsyncMock()),
            patch.object(job_mod, "close_pool", AsyncMock()),
            patch.object(job_mod, "_snapshot_one_day", fake_snapshot_one_day),
            patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(gate_conn)),
            patch.object(job_mod, "JobMonitor", _FakeJobMonitor),
            patch("jobs.snapshot_portfolio.date", _FixedDate),
        ):
            await job_mod.main(None, from_date)

    asyncio.run(run())

    assert synced_days == [_dt.date(2026, 5, 27), _dt.date(2026, 5, 28)]
    assert _dt.date(2026, 5, 29) not in synced_days  # Fri blocked → skip, not abort


def test_as_of_blocked_still_raises():
    """Daily --as-of path (non-backfill) still hard-fails with UpstreamBlocked
    when sync_prices has no success row. CLAUDE.md #10 intact."""
    fetchrow_map = {"job_runs": None}
    conn = _make_conn(fetchrow_map)
    monitor = MagicMock()
    monitor.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        with pytest.raises(UpstreamBlocked):
            asyncio.run(job_mod._snapshot_one_day(AS_OF, monitor))

    assert monitor.rows_written == 0


# ---------------------------------------------------------------------------
# 6. Idempotency — second run for same as_of overwrites via UPSERT
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


# ---------------------------------------------------------------------------
# 7. Auto daily path — trading-day anchor + latest-run gate (weekend false-block fix)
# ---------------------------------------------------------------------------

def test_latest_sync_ok_true_when_latest_success():
    """_latest_sync_ok reads the most-recent sync_prices run (not an exact date)."""
    conn = MagicMock()

    async def _fetchrow(query, *args):
        assert "ORDER BY as_of DESC" in query  # latest-run form...
        assert "as_of = $1" not in query       # ...not the exact-date form
        return {"status": "success"}

    conn.fetchrow = _fetchrow
    assert asyncio.run(job_mod._latest_sync_ok(conn)) is True


def test_latest_sync_ok_false_when_latest_failed_or_absent():
    """False when the latest sync failed, and when there is no sync row at all."""
    conn_fail = MagicMock()

    async def _fail(query, *args):
        return {"status": "failure"}

    conn_fail.fetchrow = _fail
    assert asyncio.run(job_mod._latest_sync_ok(conn_fail)) is False

    conn_none = MagicMock()

    async def _none(query, *args):
        return None

    conn_none.fetchrow = _none
    assert asyncio.run(job_mod._latest_sync_ok(conn_none)) is False


def test_snapshot_one_day_latest_run_gate_blocks_on_failed_sync():
    """gate_exact_date=False routes through _latest_sync_ok; a failed latest sync
    raises UpstreamBlocked (still fail-loud, CLAUDE.md #10)."""
    conn = MagicMock()

    async def _fetchrow(query, *args):
        return {"status": "failure"}

    conn.fetchrow = _fetchrow
    monitor = MagicMock()
    monitor.rows_written = 0

    with patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)):
        with pytest.raises(UpstreamBlocked):
            asyncio.run(
                job_mod._snapshot_one_day(AS_OF, monitor, gate_exact_date=False)
            )


def test_auto_daily_path_anchors_to_latest_complete_trading_day():
    """main() with no --as-of/--from anchors as_of to latest_complete_trading_day
    and uses the latest-run gate (gate_exact_date=False), not naive today-1."""
    anchor = _dt.date(2026, 5, 22)  # a Friday
    captured: dict = {}

    async def _fake_snapshot_one_day(as_of, monitor, *, gate_exact_date=True):
        captured["as_of"] = as_of
        captured["gate_exact_date"] = gate_exact_date

    async def _fake_latest(conn):
        return anchor

    conn = _make_conn()
    with (
        patch.object(job_mod, "init_pool", AsyncMock()),
        patch.object(job_mod, "close_pool", AsyncMock()),
        patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)),
        patch.object(job_mod, "latest_complete_trading_day", _fake_latest),
        patch.object(job_mod, "_snapshot_one_day", _fake_snapshot_one_day),
        patch.object(job_mod, "JobMonitor", _FakeJobMonitor),
    ):
        asyncio.run(job_mod.main(None, None))

    assert captured["as_of"] == anchor           # trading-date anchor, not Sat/Sun
    assert captured["gate_exact_date"] is False   # auto path uses the latest-run gate


def test_auto_daily_path_raises_when_no_complete_trading_day():
    """main() hard-fails (RuntimeError) rather than snapshotting off missing prices
    when latest_complete_trading_day returns None (CLAUDE.md #10)."""
    async def _fake_latest(conn):
        return None

    conn = _make_conn()
    with (
        patch.object(job_mod, "init_pool", AsyncMock()),
        patch.object(job_mod, "close_pool", AsyncMock()),
        patch.object(job_mod, "acquire", side_effect=lambda: _pool_ctx(conn)),
        patch.object(job_mod, "latest_complete_trading_day", _fake_latest),
    ):
        with pytest.raises(RuntimeError, match="complete trading day"):
            asyncio.run(job_mod.main(None, None))
