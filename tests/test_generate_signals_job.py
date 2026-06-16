"""
Tests for jobs/generate_signals.py — P0-2 upstream hard-fail behaviour.

The job's full happy-path pipeline (load_panel → features → predict → persist)
has heavy dependencies that are tested elsewhere; these tests focus narrowly
on the upstream-gate behaviour added by P0-2.
"""
from __future__ import annotations

import logging
from contextlib import ExitStack, asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

import jobs.generate_signals as job_mod
from asxos.jobs._helpers import UpstreamBlocked


def _make_conn(upstream_ok_status: str | None, last_price_date: date | None = date(2026, 5, 28)) -> MagicMock:
    """Mock connection: fetchval returns last_price_date; fetchrow returns upstream_ok row."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=last_price_date)
    if upstream_ok_status is None:
        conn.fetchrow = AsyncMock(return_value=None)
    else:
        conn.fetchrow = AsyncMock(return_value={"status": upstream_ok_status})
    # fetch is used by _top_liquid_symbols and the symbol list query
    conn.fetch = AsyncMock(return_value=[{"symbol": "CBA.AU"}])
    return conn


@asynccontextmanager
async def _ctx(conn):
    yield conn


@pytest.mark.asyncio
async def test_upstream_stale_no_flag_raises_upstream_blocked() -> None:
    """No success row for sync_prices + no --allow-stale-upstream → UpstreamBlocked."""
    conn = _make_conn(upstream_ok_status=None)

    captured_monitor = {}

    class FakeMonitor:
        def __init__(self, **kw):
            self.rows_written = 0
            self.override_reason = kw.get("override_reason")
            captured_monitor["m"] = self
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=FakeMonitor),
    ):
        with pytest.raises(UpstreamBlocked, match="--allow-stale-upstream"):
            await job_mod.main(date(2026, 5, 28), allow_stale_upstream=False)

    # override_reason was NOT set (no override flag passed)
    assert captured_monitor["m"].override_reason is None


@pytest.mark.asyncio
async def test_upstream_stale_with_flag_proceeds_and_records_override() -> None:
    """--allow-stale-upstream → no raise on the upstream check; override_reason recorded.

    We patch the heavy downstream pipeline so the test focuses only on the
    upstream-gate behaviour.
    """
    conn = _make_conn(upstream_ok_status=None)
    # Stub the heavy bits so main() can complete past the upstream check
    fake_panel = MagicMock()
    fake_panel.empty = False
    fake_features = pd.DataFrame({"symbol": ["CBA.AU"]})

    captured_monitor = {}

    class FakeMonitor:
        def __init__(self, **kw):
            self.rows_written = 0
            self.override_reason = kw.get("override_reason")
            captured_monitor["m"] = self
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    fake_model = MagicMock()
    fake_model.version = "v1_5"
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(return_value=fake_model)

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=FakeMonitor),
        patch.object(job_mod, "load_panel", new=AsyncMock(return_value=fake_panel)),
        patch.object(job_mod, "classify_regime", return_value="bull"),
        patch.object(job_mod, "features_from_panel", return_value=fake_features),
        patch.object(job_mod, "get_cache", return_value=fake_cache),
        patch.object(
            job_mod, "predict_with_shap",
            new=AsyncMock(return_value=(MagicMock(), MagicMock())),
        ),
        patch.object(job_mod, "persist_signals", new=AsyncMock(return_value=42)),
    ):
        # Must NOT raise — override granted
        await job_mod.main(date(2026, 5, 28), allow_stale_upstream=True)

    assert captured_monitor["m"].override_reason == "operator: --allow-stale-upstream"
    assert captured_monitor["m"].rows_written == 42


@pytest.mark.asyncio
async def test_upstream_ok_proceeds_without_override_reason() -> None:
    """Normal happy path: sync_prices succeeded; no override needed."""
    conn = _make_conn(upstream_ok_status="success")
    fake_panel = MagicMock()
    fake_panel.empty = False
    fake_features = pd.DataFrame({"symbol": ["CBA.AU"]})

    captured_monitor = {}

    class FakeMonitor:
        def __init__(self, **kw):
            self.rows_written = 0
            self.override_reason = kw.get("override_reason")
            captured_monitor["m"] = self
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    fake_model = MagicMock()
    fake_model.version = "v1_5"
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(return_value=fake_model)

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=FakeMonitor),
        patch.object(job_mod, "load_panel", new=AsyncMock(return_value=fake_panel)),
        patch.object(job_mod, "classify_regime", return_value="bull"),
        patch.object(job_mod, "features_from_panel", return_value=fake_features),
        patch.object(job_mod, "get_cache", return_value=fake_cache),
        patch.object(
            job_mod, "predict_with_shap",
            new=AsyncMock(return_value=(MagicMock(), MagicMock())),
        ),
        patch.object(job_mod, "persist_signals", new=AsyncMock(return_value=10)),
    ):
        await job_mod.main(date(2026, 5, 28), allow_stale_upstream=False)

    assert captured_monitor["m"].override_reason is None
    assert captured_monitor["m"].rows_written == 10


# ---------------------------------------------------------------------------
# Complete-trading-day anchor (Batch 2 Stage 0): generate_signals anchors on
# latest_complete_trading_day, NOT raw MAX(prices.dt), when no --as-of is given.
# ---------------------------------------------------------------------------


class _FakeMonitor:
    """Minimal JobMonitor stand-in capturing as_of / override_reason / rows."""

    last: _FakeMonitor | None = None

    def __init__(self, **kw: object) -> None:
        self.job_name = kw.get("job_name")
        self.as_of = kw.get("as_of")
        self.override_reason = kw.get("override_reason")
        self.rows_written = 0
        _FakeMonitor.last = self

    async def __aenter__(self) -> _FakeMonitor:
        return self

    async def __aexit__(self, *a: object) -> bool:
        return False


def _nonempty_panel() -> MagicMock:
    p = MagicMock()
    p.empty = False
    return p


def _cache_returning(version: str) -> MagicMock:
    model = MagicMock()
    model.version = version
    cache = MagicMock()
    cache.get = AsyncMock(return_value=model)
    return cache


def _happy_pipeline_patches(
    *,
    conn: MagicMock,
    complete_dt: date | None,
    coverage_mock: AsyncMock,
    persist_mock: AsyncMock,
    load_panel_mock: AsyncMock,
) -> list:
    """Patch list for the heavy downstream pipeline + the coverage helper.

    `coverage_mock` stands in for ``latest_complete_trading_day``; the caller owns
    it so it can assert call/no-call. The pipeline stubs let ``main`` run past the
    upstream gate without touching the real model / DB.
    """
    coverage_mock.return_value = complete_dt
    load_panel_mock.return_value = _nonempty_panel()
    return [
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "JobMonitor", new=_FakeMonitor),
        patch.object(job_mod, "latest_complete_trading_day", new=coverage_mock),
        patch.object(job_mod, "load_panel", new=load_panel_mock),
        patch.object(job_mod, "classify_regime", return_value="bull"),
        patch.object(
            job_mod, "features_from_panel",
            return_value=pd.DataFrame({"symbol": ["CBA.AU"]}),
        ),
        patch.object(job_mod, "get_cache", return_value=_cache_returning("v1_5")),
        patch.object(
            job_mod, "predict_with_shap",
            new=AsyncMock(return_value=(MagicMock(), MagicMock())),
        ),
        patch.object(job_mod, "persist_signals", new=persist_mock),
    ]


@pytest.mark.asyncio
async def test_anchors_on_latest_complete_trading_day() -> None:
    """No --as-of: as_of comes from latest_complete_trading_day, not MAX(prices.dt).

    Observed price date and complete trading day coincide here (normal case) —
    no warning, signals persisted for the complete date. run_date is pinned one
    day after the complete day so the recency gate sees a fresh anchor.
    """
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 10))
    persist_mock = AsyncMock(return_value=7)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock()

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=date(2026, 6, 10),
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        await job_mod.main(None, allow_stale_upstream=False, run_date=date(2026, 6, 11))

    # Signals persisted under the complete trading day...
    assert persist_mock.call_args.kwargs["as_of"] == date(2026, 6, 10)
    # ...feature loading was anchored on the same date...
    assert load_panel_mock.await_args_list[0].args[1] == date(2026, 6, 10)
    # ...and the run is recorded under the same as_of (job_runs.as_of == signals.as_of).
    assert _FakeMonitor.last is not None
    assert _FakeMonitor.last.as_of == date(2026, 6, 10)
    coverage_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_residue_observed_date_anchors_on_complete_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Observed MAX(prices.dt) is a residue/non-trading date later than the last
    complete day: generation must anchor on the EARLIER complete day and warn."""
    # Observed freshest price date is a Sunday residue; last complete day is Wed.
    # run_date is the Monday run (06-15) — the complete day (06-10) is 5 calendar
    # days back, i.e. still fresh (the recency boundary is > 5), so generation
    # proceeds and the anchor-mismatch warning fires.
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 15))
    persist_mock = AsyncMock(return_value=5)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock()

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=date(2026, 6, 10),
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        with caplog.at_level(logging.WARNING, logger=job_mod.log.name):
            await job_mod.main(None, allow_stale_upstream=False, run_date=date(2026, 6, 15))

    # Anchored on the EARLIER complete date (06-10), NOT the residue date (06-15).
    assert persist_mock.call_args.kwargs["as_of"] == date(2026, 6, 10)
    assert load_panel_mock.await_args_list[0].args[1] == date(2026, 6, 10)
    assert "anchoring signal generation on latest complete trading day" in caplog.text
    assert "2026-06-15" in caplog.text  # observed residue date named in the warning
    assert "2026-06-10" in caplog.text  # complete date named in the warning


@pytest.mark.asyncio
async def test_no_complete_day_raises_upstream_blocked() -> None:
    """No complete trading day anywhere in the coverage window → UpstreamBlocked,
    no signals written, recorded as 'blocked' (via the existing pattern)."""
    # Prices exist (so the empty-DB hard-fail does not fire) but none are complete.
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 15))
    persist_mock = AsyncMock(return_value=0)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock()

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=None,
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        with pytest.raises(UpstreamBlocked, match="no complete trading day"):
            await job_mod.main(None, allow_stale_upstream=False)

    persist_mock.assert_not_called()


@pytest.mark.asyncio
async def test_explicit_as_of_bypasses_coverage_lookup() -> None:
    """Explicit --as-of wins verbatim and does NOT consult latest_complete_trading_day
    (even if no complete day exists), preserving the operator-override path."""
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 15))
    persist_mock = AsyncMock(return_value=3)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock(return_value=None)

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=None,
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        await job_mod.main(date(2026, 5, 20), allow_stale_upstream=False)

    # Operator-pinned date used verbatim; coverage helper never consulted.
    assert persist_mock.call_args.kwargs["as_of"] == date(2026, 5, 20)
    coverage_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Recency gate (Batch 2 Stage 0, follow-up): block when the latest COMPLETE
# trading day is too stale (calendar-day) relative to the run date, so a stalled
# price feed cannot keep producing "successful" signals on old complete data.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stale_complete_day_blocks_and_does_not_persist() -> None:
    """Complete day older than DEFAULT_MAX_STALE_DAYS (5) calendar days vs run date,
    no override → UpstreamBlocked, no signals persisted."""
    # complete day 06-10, run date 06-16 → 6 calendar days > 5 → stale.
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 10))
    persist_mock = AsyncMock(return_value=0)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock()

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=date(2026, 6, 10),
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        with pytest.raises(UpstreamBlocked, match="stale relative to run date"):
            await job_mod.main(None, allow_stale_upstream=False, run_date=date(2026, 6, 16))

    persist_mock.assert_not_called()
    # Recorded under the complete day (job_runs.as_of == the blocked anchor).
    assert _FakeMonitor.last is not None
    assert _FakeMonitor.last.as_of == date(2026, 6, 10)


@pytest.mark.asyncio
async def test_stale_complete_day_allow_stale_proceeds_and_records_override(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """--allow-stale-upstream bypasses the recency gate: generation proceeds on the
    stale complete day, warns, and records override_reason."""
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 10))
    persist_mock = AsyncMock(return_value=9)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock()

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=date(2026, 6, 10),
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        with caplog.at_level(logging.WARNING, logger=job_mod.log.name):
            await job_mod.main(None, allow_stale_upstream=True, run_date=date(2026, 6, 16))

    # Proceeded on the stale complete day; override recorded.
    assert persist_mock.call_args.kwargs["as_of"] == date(2026, 6, 10)
    assert _FakeMonitor.last is not None
    assert _FakeMonitor.last.override_reason == "operator: --allow-stale-upstream"
    assert "Proceeding on stale complete trading day" in caplog.text


@pytest.mark.asyncio
async def test_explicit_as_of_bypasses_recency_gate() -> None:
    """Explicit --as-of is an operator override: it skips the coverage lookup AND the
    recency gate, even for a date far older than the freshness window."""
    conn = _make_conn(upstream_ok_status="success", last_price_date=date(2026, 6, 15))
    persist_mock = AsyncMock(return_value=4)
    load_panel_mock = AsyncMock()
    coverage_mock = AsyncMock(return_value=None)

    with ExitStack() as stack:
        for p in _happy_pipeline_patches(
            conn=conn,
            complete_dt=None,
            coverage_mock=coverage_mock,
            persist_mock=persist_mock,
            load_panel_mock=load_panel_mock,
        ):
            stack.enter_context(p)
        # as_of pinned far in the past; run_date today → would be stale IF gated.
        await job_mod.main(date(2026, 1, 5), allow_stale_upstream=False, run_date=date(2026, 6, 16))

    # Pinned date used verbatim; gate never consulted (no raise, signals persisted).
    assert persist_mock.call_args.kwargs["as_of"] == date(2026, 1, 5)
    coverage_mock.assert_not_called()
