"""
Tests for the API startup hard-fail sequence (CLAUDE.md non-negotiable #1).

Covers asxos/api/main.py: _check_migration_drift (drift / ok / skip) and the
FastAPI lifespan (success + each hard-fail branch), plus the /health route.
This establishes the FastAPI lifespan test harness the repo previously lacked.

NB: importing asxos.api.main instantiates BriefSettings() at import time and warms
the model cache import, so the brief env vars must be present before the import
below, and the module may collection-error in the bare sandbox (no ML deps) — it
runs on CI where `.[ml]` is installed, like the other documented ML-import tests.
"""
from __future__ import annotations

import os

# BriefSettings() (asxos/api/main.py import) requires these — set before import.
for _k, _v in {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon",
    "RESEND_API_KEY": "test-resend",
    "BRIEF_FROM_EMAIL": "from@example.com",
    "BRIEF_TO_EMAIL": "to@example.com",
}.items():
    os.environ.setdefault(_k, _v)
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")

from contextlib import asynccontextmanager  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

import asxos.api.main as main  # noqa: E402
from asxos.api.routes import health as health_mod  # noqa: E402


def _acquire_yielding(conn: object):
    """A patch target for `acquire` that yields `conn` as an async context manager."""

    @asynccontextmanager
    async def _cm():
        yield conn

    return _cm


# ---------------------------------------------------------------------------
# _check_migration_drift — the migration-drift hard-fail guard
# ---------------------------------------------------------------------------


async def test_migration_drift_raises_below_required(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "skip_migration_drift_check", False)
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=main.REQUIRED_MIGRATIONS - 1)
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))
    with pytest.raises(RuntimeError, match="Migration drift"):
        await main._check_migration_drift()


async def test_migration_drift_passes_at_required(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "skip_migration_drift_check", False)
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=main.REQUIRED_MIGRATIONS)
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))
    await main._check_migration_drift()  # must not raise


async def test_migration_drift_skipped_by_config(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "skip_migration_drift_check", True)
    called = MagicMock()
    monkeypatch.setattr(main, "acquire", called)
    await main._check_migration_drift()
    called.assert_not_called()  # short-circuits before touching the DB


# ---------------------------------------------------------------------------
# lifespan — the startup hard-fail sequence
# ---------------------------------------------------------------------------


async def test_lifespan_success_warms_and_closes(monkeypatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    close = AsyncMock()
    cache = MagicMock()
    cache.get = AsyncMock(return_value=object())
    monkeypatch.setattr(main, "init_pool", AsyncMock())
    monkeypatch.setattr(main, "close_pool", close)
    monkeypatch.setattr(main, "_check_migration_drift", AsyncMock())
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))
    monkeypatch.setattr(main, "get_cache", lambda: cache)

    async with main.lifespan(main.app):
        pass

    cache.get.assert_awaited_once_with("model_a")
    close.assert_awaited_once()


async def test_lifespan_hard_fails_on_missing_model_artefact(monkeypatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    cache = MagicMock()
    cache.get = AsyncMock(side_effect=RuntimeError("model_a artefact missing"))
    monkeypatch.setattr(main, "init_pool", AsyncMock())
    monkeypatch.setattr(main, "close_pool", AsyncMock())
    monkeypatch.setattr(main, "_check_migration_drift", AsyncMock())
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))
    monkeypatch.setattr(main, "get_cache", lambda: cache)

    with pytest.raises(RuntimeError, match="artefact missing"):
        async with main.lifespan(main.app):
            pass


async def test_lifespan_hard_fails_on_migration_drift(monkeypatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    monkeypatch.setattr(main, "init_pool", AsyncMock())
    monkeypatch.setattr(main, "close_pool", AsyncMock())
    monkeypatch.setattr(main, "_check_migration_drift", AsyncMock(side_effect=RuntimeError("Migration drift")))
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))
    monkeypatch.setattr(main, "get_cache", lambda: MagicMock(get=AsyncMock()))

    with pytest.raises(RuntimeError, match="Migration drift"):
        async with main.lifespan(main.app):
            pass


# ---------------------------------------------------------------------------
# /health route
# ---------------------------------------------------------------------------


async def test_health_ok_when_db_reachable(monkeypatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    monkeypatch.setattr(health_mod, "acquire", _acquire_yielding(conn))
    resp = await health_mod.health()
    assert resp.status_code == 200


async def test_health_503_when_db_unreachable(monkeypatch) -> None:
    @asynccontextmanager
    async def _boom():
        raise RuntimeError("db down")
        yield  # pragma: no cover

    monkeypatch.setattr(health_mod, "acquire", _boom)
    resp = await health_mod.health()
    assert resp.status_code == 503
