"""
Tests for asxos/jobs/utils/job_monitor.py — P0-2 additions.

Covers:
  - UpstreamBlocked exception is mapped to status='blocked'
  - override_reason kwarg persists through INSERT and UPDATE
  - 'blocked' runs do NOT ping the healthcheck (so the deadman misses)
  - Normal failure path still maps to status='failure'
  - Happy path still maps to status='success' AND pings healthcheck
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asxos.jobs._helpers import UpstreamBlocked
from asxos.jobs.utils.job_monitor import JobMonitor


@asynccontextmanager
async def _fake_acquire(conn):
    yield conn


def _patch_pool(conn):
    return patch(
        "asxos.jobs.utils.job_monitor.acquire", new=lambda: _fake_acquire(conn)
    )


@pytest.mark.asyncio
async def test_happy_path_records_success_and_pings_healthcheck() -> None:
    conn = MagicMock()
    conn.execute = AsyncMock()

    fake_get = AsyncMock()
    fake_client = MagicMock()
    fake_client.get = fake_get

    @asynccontextmanager
    async def fake_async_client(*a, **kw):
        yield fake_client

    with _patch_pool(conn), patch(
        "asxos.jobs.utils.job_monitor.httpx.AsyncClient", new=fake_async_client
    ):
        async with JobMonitor(
            job_name="t", as_of=date(2026, 5, 28), healthcheck_url="http://hc/ping"
        ) as monitor:
            monitor.rows_written = 5

    # INSERT (running) + UPDATE (success) = 2 calls
    assert conn.execute.await_count == 2
    update_call = conn.execute.await_args_list[1]
    assert update_call.args[1] == "success"  # status
    assert update_call.args[3] == 5  # rows_written

    # Healthcheck was pinged
    fake_get.assert_awaited_once_with("http://hc/ping")


@pytest.mark.asyncio
async def test_upstream_blocked_records_blocked_status() -> None:
    """UpstreamBlocked → status='blocked' (not 'failure'). Exception propagates."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    with _patch_pool(conn):
        with pytest.raises(UpstreamBlocked, match="sync_prices stale"):
            async with JobMonitor(
                job_name="t",
                as_of=date(2026, 5, 28),
                healthcheck_url="http://hc/ping",
            ):
                raise UpstreamBlocked("sync_prices stale")

    update_call = conn.execute.await_args_list[1]
    assert update_call.args[1] == "blocked"
    # Error message captured
    assert "sync_prices stale" in update_call.args[4]


@pytest.mark.asyncio
async def test_blocked_does_not_ping_success_url() -> None:
    """Blocked runs must NOT ping the success URL — the deadman should miss."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    fake_get = AsyncMock()
    fake_client = MagicMock()
    fake_client.get = fake_get

    @asynccontextmanager
    async def fake_async_client(*a, **kw):
        yield fake_client

    with _patch_pool(conn), patch(
        "asxos.jobs.utils.job_monitor.httpx.AsyncClient", new=fake_async_client
    ):
        with pytest.raises(UpstreamBlocked):
            async with JobMonitor(
                job_name="t",
                as_of=date(2026, 5, 28),
                healthcheck_url="http://hc/ping",
            ):
                raise UpstreamBlocked("x")

    fake_get.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_failure_records_failure_status_and_no_ping() -> None:
    """Any non-UpstreamBlocked exception → status='failure', no ping."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    fake_get = AsyncMock()
    fake_client = MagicMock()
    fake_client.get = fake_get

    @asynccontextmanager
    async def fake_async_client(*a, **kw):
        yield fake_client

    with _patch_pool(conn), patch(
        "asxos.jobs.utils.job_monitor.httpx.AsyncClient", new=fake_async_client
    ):
        with pytest.raises(ValueError):
            async with JobMonitor(
                job_name="t",
                as_of=date(2026, 5, 28),
                healthcheck_url="http://hc/ping",
            ):
                raise ValueError("Postgres unreachable")

    update_call = conn.execute.await_args_list[1]
    assert update_call.args[1] == "failure"
    fake_get.assert_not_awaited()


@pytest.mark.asyncio
async def test_override_reason_persisted_in_insert_and_update() -> None:
    """override_reason flows to INSERT (running) AND UPDATE (final status)."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    fake_get = AsyncMock()
    fake_client = MagicMock()
    fake_client.get = fake_get

    @asynccontextmanager
    async def fake_async_client(*a, **kw):
        yield fake_client

    with _patch_pool(conn), patch(
        "asxos.jobs.utils.job_monitor.httpx.AsyncClient", new=fake_async_client
    ):
        async with JobMonitor(
            job_name="t",
            as_of=date(2026, 5, 28),
            healthcheck_url="http://hc/ping",
            override_reason="operator: --allow-stale-upstream",
        ):
            pass

    insert_call = conn.execute.await_args_list[0]
    update_call = conn.execute.await_args_list[1]
    # INSERT: $4 (4th arg) is override_reason
    assert insert_call.args[4] == "operator: --allow-stale-upstream"
    # UPDATE: $6 (6th arg) is override_reason
    assert update_call.args[6] == "operator: --allow-stale-upstream"


@pytest.mark.asyncio
async def test_override_reason_defaults_to_none() -> None:
    """When omitted, override_reason persists as NULL."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    fake_get = AsyncMock()
    fake_client = MagicMock()
    fake_client.get = fake_get

    @asynccontextmanager
    async def fake_async_client(*a, **kw):
        yield fake_client

    with _patch_pool(conn), patch(
        "asxos.jobs.utils.job_monitor.httpx.AsyncClient", new=fake_async_client
    ):
        async with JobMonitor(
            job_name="t", as_of=date(2026, 5, 28), healthcheck_url="http://hc/ping"
        ):
            pass

    insert_call = conn.execute.await_args_list[0]
    assert insert_call.args[4] is None


@pytest.mark.asyncio
async def test_healthcheck_ping_failure_does_not_break_success() -> None:
    """A flaky healthcheck endpoint must not turn success into failure."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    fake_get = AsyncMock(side_effect=RuntimeError("healthcheck.io down"))
    fake_client = MagicMock()
    fake_client.get = fake_get

    @asynccontextmanager
    async def fake_async_client(*a, **kw):
        yield fake_client

    with _patch_pool(conn), patch(
        "asxos.jobs.utils.job_monitor.httpx.AsyncClient", new=fake_async_client
    ):
        # Must not raise despite the ping failure
        async with JobMonitor(
            job_name="t", as_of=date(2026, 5, 28), healthcheck_url="http://hc/ping"
        ):
            pass

    # Status was still recorded as success
    update_call = conn.execute.await_args_list[1]
    assert update_call.args[1] == "success"
