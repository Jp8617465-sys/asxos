"""
Tests for the API startup hard-fail sequence (CLAUDE.md non-negotiable #1).

Covers asxos/api/main.py: _check_migration_drift (drift / ok / skip) and the
FastAPI lifespan (success + each hard-fail branch), plus the /health route.
This establishes the FastAPI lifespan test harness the repo previously lacked.

The lifespan has two hard-fail gates: the DB ping and the migration-drift check.
The third (the Model A artefact warm) was removed with the Model A runtime
dependencies — see docs/product/model-a-reference-manifest.md R1. Removing it
must not soften the remaining two into warnings (CLAUDE.md #1 and #10).

NB: importing asxos.api.main instantiates BriefSettings() at import time. The
brief env vars it needs are seeded by tests/conftest.py before any asxos import,
so this module no longer carries its own os.environ preamble.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

import asxos.api.main as main
from asxos.api.routes import health as health_mod


def _acquire_yielding(conn: object):
    """A patch target for `acquire` that yields `conn` as an async context manager."""

    @asynccontextmanager
    async def _cm():
        yield conn

    return _cm


# ---------------------------------------------------------------------------
# _check_migration_drift — the migration-drift hard-fail guard
# ---------------------------------------------------------------------------


def _ledger(*names: str) -> MagicMock:
    """A conn whose fetch() returns ledger rows for the given asxos-era names."""
    conn = MagicMock()
    conn.fetch = AsyncMock(
        return_value=[{"version": "20260601000000", "name": n} for n in names]
    )
    return conn


async def test_migration_drift_raises_when_a_repo_file_is_unapplied(monkeypatch) -> None:
    """The startup guard still hard-fails (CLAUDE.md #1) — now on a name diff."""
    monkeypatch.setattr(main.settings, "skip_migration_drift_check", False)
    monkeypatch.setattr(main, "acquire", _acquire_yielding(_ledger("0001_initial")))
    with pytest.raises(RuntimeError, match="Migration drift"):
        await main._check_migration_drift()


async def test_migration_drift_raises_on_applied_but_untracked(monkeypatch) -> None:
    """The case the old count guard could not detect AT ALL.

    `count < REQUIRED_MIGRATIONS` passes when production carries a migration
    this repo has no file for: the count only rises. That is the state
    production was actually in — ledger row 20260602102212 / 0018_perf_indexes
    with no file — while the guard stayed green.

    The whole real ledger is passed so the only anomaly is the injected one.
    """
    from asxos.schema_drift import repo_migration_keys

    monkeypatch.setattr(main.settings, "skip_migration_drift_check", False)
    names = [*repo_migration_keys().keys(), "a_migration_with_no_file"]
    monkeypatch.setattr(main, "acquire", _acquire_yielding(_ledger(*names)))
    with pytest.raises(RuntimeError, match="APPLIED BUT NOT IN REPO"):
        await main._check_migration_drift()


async def test_migration_drift_passes_when_names_agree(monkeypatch) -> None:
    """Every repo file applied, plus the two allowlisted-unapplied ones absent."""
    from asxos.schema_drift import EXPECTED_UNAPPLIED, _key, repo_migration_keys

    monkeypatch.setattr(main.settings, "skip_migration_drift_check", False)
    unapplied = {_key(n) for n in EXPECTED_UNAPPLIED}
    names = [k for k in repo_migration_keys() if k not in unapplied]
    monkeypatch.setattr(main, "acquire", _acquire_yielding(_ledger(*names)))
    await main._check_migration_drift()  # must not raise


async def test_migration_drift_ignores_pre_asxos_ledger_rows(monkeypatch) -> None:
    """47 rows predate asxos on this shared Supabase instance.

    They are excluded by version epoch, not by an enumerated list, so they can
    never be mistaken for asxos migrations that lost their files.
    """
    from asxos.schema_drift import EXPECTED_UNAPPLIED, _key, repo_migration_keys

    monkeypatch.setattr(main.settings, "skip_migration_drift_check", False)
    unapplied = {_key(n) for n in EXPECTED_UNAPPLIED}
    conn = MagicMock()
    conn.fetch = AsyncMock(
        return_value=[
            {"version": "20260217004354", "name": "add_assistant_conversations"},
            {"version": "20260320045542", "name": "056_scenario_templates"},
            *(
                {"version": "20260601000000", "name": k}
                for k in repo_migration_keys()
                if k not in unapplied
            ),
        ]
    )
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


async def test_lifespan_success_pings_db_and_closes(monkeypatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    close = AsyncMock()
    drift = AsyncMock()
    monkeypatch.setattr(main, "init_pool", AsyncMock())
    monkeypatch.setattr(main, "close_pool", close)
    monkeypatch.setattr(main, "_check_migration_drift", drift)
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))

    async with main.lifespan(main.app):
        pass

    conn.fetchval.assert_awaited_once_with("SELECT 1")
    drift.assert_awaited_once()
    close.assert_awaited_once()


async def test_lifespan_hard_fails_on_db_ping(monkeypatch) -> None:
    """The DB-ping gate still hard-fails (CLAUDE.md non-negotiable #1)."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=RuntimeError("db unreachable"))
    monkeypatch.setattr(main, "init_pool", AsyncMock())
    monkeypatch.setattr(main, "close_pool", AsyncMock())
    monkeypatch.setattr(main, "_check_migration_drift", AsyncMock())
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))

    with pytest.raises(RuntimeError, match="db unreachable"):
        async with main.lifespan(main.app):
            pass


async def test_lifespan_hard_fails_on_migration_drift(monkeypatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    monkeypatch.setattr(main, "init_pool", AsyncMock())
    monkeypatch.setattr(main, "close_pool", AsyncMock())
    monkeypatch.setattr(main, "_check_migration_drift", AsyncMock(side_effect=RuntimeError("Migration drift")))
    monkeypatch.setattr(main, "acquire", _acquire_yielding(conn))

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
