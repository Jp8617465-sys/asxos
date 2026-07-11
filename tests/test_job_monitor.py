"""
Tests for asxos/jobs/utils/job_monitor.py — P0-2 additions.

Covers:
  - UpstreamBlocked exception is mapped to status='blocked'
  - ModelGateDormant exception is mapped to status='blocked' (rule #11)
  - override_reason kwarg persists through INSERT and UPDATE
  - 'blocked' runs do NOT ping the healthcheck (so the deadman misses)
  - Normal failure maps to status='failure' AND pings healthcheck_url + '/fail'
  - A ping exception on the '/fail' ping never masks the job's own exception
  - Happy path still maps to status='success' AND pings healthcheck
  - Stale-row heal is cross-as_of (no as_of bind — a crashed prior-day row heals)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asxos.domain.models.production_gate import ModelGateDormant
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

    # RESET (stale) + INSERT (running) + UPDATE (success) = 3 calls
    assert conn.execute.await_count == 3
    update_call = conn.execute.await_args_list[2]
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

    update_call = conn.execute.await_args_list[2]
    assert update_call.args[1] == "blocked"
    # Error message captured
    assert "sync_prices stale" in update_call.args[4]


@pytest.mark.asyncio
async def test_model_gate_dormant_records_blocked_status() -> None:
    """ModelGateDormant (rule #11, 0 approved models) → status='blocked', not
    'failure' — build_portfolio hitting the standing quarantine every week is
    an expected policy state, not a new crash each time. Exception propagates
    (JobMonitor never suppresses)."""
    conn = MagicMock()
    conn.execute = AsyncMock()

    with _patch_pool(conn):
        with pytest.raises(ModelGateDormant, match="approved_for_allocation"):
            async with JobMonitor(
                job_name="build_portfolio",
                as_of=date(2026, 7, 11),
                healthcheck_url="http://hc/ping",
            ):
                raise ModelGateDormant(
                    "no model_version is both active and approved_for_allocation"
                )

    update_call = conn.execute.await_args_list[2]
    assert update_call.args[1] == "blocked"
    assert "approved_for_allocation" in update_call.args[4]


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
async def test_real_failure_records_failure_status_and_pings_fail_url() -> None:
    """Any non-UpstreamBlocked exception → status='failure', pings url + '/fail'."""
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

    update_call = conn.execute.await_args_list[2]
    assert update_call.args[1] == "failure"
    # Explicit-failure signal: the exact URL requested ends with /fail
    fake_get.assert_awaited_once_with("http://hc/ping/fail")
    assert fake_get.await_args.args[0].endswith("/fail")


@pytest.mark.asyncio
async def test_fail_ping_exception_does_not_mask_job_exception() -> None:
    """A flaky '/fail' ping must never swallow or replace the job's exception."""
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
        # The ORIGINAL ValueError propagates, not the ping's RuntimeError
        with pytest.raises(ValueError, match="Postgres unreachable"):
            async with JobMonitor(
                job_name="t",
                as_of=date(2026, 5, 28),
                healthcheck_url="http://hc/ping",
            ):
                raise ValueError("Postgres unreachable")

    # The /fail ping was attempted; failure status was still recorded
    fake_get.assert_awaited_once_with("http://hc/ping/fail")
    update_call = conn.execute.await_args_list[2]
    assert update_call.args[1] == "failure"


@pytest.mark.asyncio
async def test_stale_row_heal_is_not_scoped_to_as_of() -> None:
    """The __aenter__ heal must match ANY stale running row for this job_name,
    regardless of its as_of — a sync_financial_statements run that crashed on
    2026-06-27 stayed 'running' forever because the heal was scoped to each
    later run's own as_of (date.today()) and never saw the prior-day row."""
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

    # Call 0 is the stale-row heal UPDATE
    heal_call = conn.execute.await_args_list[0]
    heal_sql = heal_call.args[0]
    assert "status   = 'running'" in heal_sql
    assert "INTERVAL '2 hours'" in heal_sql
    # No as_of filter in the WHERE clause, and no as_of bind arg —
    # only (sql, job_name) is passed.
    assert "as_of" not in heal_sql
    assert heal_call.args[1:] == ("t",)


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

    insert_call = conn.execute.await_args_list[1]
    update_call = conn.execute.await_args_list[2]
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

    insert_call = conn.execute.await_args_list[1]
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
    update_call = conn.execute.await_args_list[2]
    assert update_call.args[1] == "success"
