"""
Tests for jobs/derive_fundamentals_pit.py — upstream-gate behaviour.

2026-07-18 incident: this job fired at its scheduled 17:10 UTC while
sync_corporate_actions (started 16:30) was still running (didn't finish until
18:09) and hit a TimeoutError racing the concurrent write to rs_corporate_actions
-- with no upstream gate, the failure mode gave no hint the real cause was a
missing upstream. These tests pin the new `_missing_upstreams` gate and its
wiring into `main()`, mirroring the existing test_generate_signals_job.py
pattern for the same class of P0-2-style upstream check.
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.derive_fundamentals_pit as job_mod
from asxos.jobs._helpers import UpstreamBlocked


def _row_for(present: set[str]):
    async def _fetchrow(query, job_name, as_of):
        return {"1": 1} if job_name in present else None

    return _fetchrow


@pytest.mark.asyncio
async def test_missing_upstreams_empty_when_both_succeeded() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(
        side_effect=_row_for({"sync_financial_statements", "sync_corporate_actions"})
    )
    missing = await job_mod._missing_upstreams(conn, date(2026, 7, 19))
    assert missing == []


@pytest.mark.asyncio
async def test_missing_upstreams_reports_the_one_missing() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=_row_for({"sync_financial_statements"}))
    missing = await job_mod._missing_upstreams(conn, date(2026, 7, 19))
    assert missing == ["sync_corporate_actions"]


@pytest.mark.asyncio
async def test_missing_upstreams_reports_both_when_neither_succeeded() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=_row_for(set()))
    missing = await job_mod._missing_upstreams(conn, date(2026, 7, 19))
    assert missing == ["sync_financial_statements", "sync_corporate_actions"]


@asynccontextmanager
async def _ctx(conn):
    yield conn


class _FakeMonitor:
    def __init__(self, **kw):
        self.rows_written = 0
        self.override_reason = kw.get("override_reason")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


@pytest.mark.asyncio
async def test_main_raises_upstream_blocked_without_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["derive_fundamentals_pit.py"])
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=_row_for(set()))  # neither upstream ready

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=_FakeMonitor),
        patch.object(job_mod, "refresh_fundamentals_pit", new=AsyncMock()) as mock_refresh,
    ):
        with pytest.raises(UpstreamBlocked, match="--allow-stale-upstream"):
            await job_mod.main()
        mock_refresh.assert_not_called()  # gate fires BEFORE the derive query runs


@pytest.mark.asyncio
async def test_main_proceeds_with_override_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["derive_fundamentals_pit.py", "--allow-stale-upstream"])
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=_row_for(set()))

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=_FakeMonitor),
        patch.object(
            job_mod,
            "refresh_fundamentals_pit",
            new=AsyncMock(return_value={"symbols": 1, "rows": 1}),
        ) as mock_refresh,
    ):
        await job_mod.main()  # must not raise
    mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_main_records_override_reason_for_audit_trail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # generate_signals.py precedent: --allow-stale-upstream must be visible in
    # job_runs.override_reason, not just silently bypass the gate.
    monkeypatch.setattr(sys, "argv", ["derive_fundamentals_pit.py", "--allow-stale-upstream"])
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=_row_for(set()))
    captured: dict[str, _FakeMonitor] = {}

    class _CapturingMonitor(_FakeMonitor):
        def __init__(self, **kw):
            super().__init__(**kw)
            captured["m"] = self

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=_CapturingMonitor),
        patch.object(
            job_mod,
            "refresh_fundamentals_pit",
            new=AsyncMock(return_value={"symbols": 1, "rows": 1}),
        ),
    ):
        await job_mod.main()

    assert captured["m"].override_reason == "operator: --allow-stale-upstream"


@pytest.mark.asyncio
async def test_main_proceeds_silently_when_upstream_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["derive_fundamentals_pit.py"])
    conn = MagicMock()
    conn.fetchrow = AsyncMock(
        side_effect=_row_for({"sync_financial_statements", "sync_corporate_actions"})
    )

    with (
        patch.object(job_mod, "init_pool", new=AsyncMock()),
        patch.object(job_mod, "close_pool", new=AsyncMock()),
        patch.object(job_mod, "acquire", new=lambda: _ctx(conn)),
        patch.object(job_mod, "JobMonitor", new=_FakeMonitor),
        patch.object(
            job_mod,
            "refresh_fundamentals_pit",
            new=AsyncMock(return_value={"symbols": 3, "rows": 3}),
        ) as mock_refresh,
    ):
        await job_mod.main()  # no UpstreamBlocked, no warning needed
        mock_refresh.assert_called_once()
