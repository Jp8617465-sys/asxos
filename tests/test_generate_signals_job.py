"""
Tests for jobs/generate_signals.py — P0-2 upstream hard-fail behaviour.

The job's full happy-path pipeline (load_panel → features → predict → persist)
has heavy dependencies that are tested elsewhere; these tests focus narrowly
on the upstream-gate behaviour added by P0-2.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.generate_signals as job_mod
from asxos.jobs._helpers import UpstreamBlocked


def _make_conn(upstream_ok_status: str | None) -> MagicMock:
    """conn.fetchrow returns the row that _upstream_ok would read."""
    conn = MagicMock()
    if upstream_ok_status is None:
        conn.fetchrow = AsyncMock(return_value=None)
    else:
        conn.fetchrow = AsyncMock(return_value={"status": upstream_ok_status})
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
    fake_features = MagicMock()
    fake_features.empty = False

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
    fake_features = MagicMock()
    fake_features.empty = False

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
