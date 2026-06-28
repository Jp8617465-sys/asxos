"""
CLI tests for `asx model activate` and `asx model list`.

Patches the command module's init_pool/close_pool/acquire so the Typer
wiring, the activate transaction flip, the not-found exit path, and the
empty-list path run without a real Postgres connection.

This module imports cleanly in the bare sandbox — asxos.cli.model pulls
no numpy/lightgbm/fastapi, only typer + rich + asxos.db.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import model as model_mod

runner = CliRunner()


def _make_conn() -> MagicMock:
    """A mock asyncpg conn whose fetch/fetchrow/execute are AsyncMocks and
    whose .transaction() is an async context manager."""
    conn = MagicMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def _txn() -> Any:
        yield None

    conn.transaction = _txn
    return conn


def _patch_pool(conn: MagicMock) -> Any:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    return patch.multiple(
        model_mod,
        init_pool=AsyncMock(return_value=None),
        close_pool=AsyncMock(return_value=None),
        acquire=_acquire,
    )


def test_model_activate_not_found_exits_1() -> None:
    conn = _make_conn()
    # target lookup returns None -> not-found branch
    conn.fetchrow.return_value = None

    with _patch_pool(conn):
        result = runner.invoke(cli_main.app, ["model", "activate", "v9_9"])

    assert result.exit_code == 1, result.output
    assert "no row found for model_a v9_9" in result.output
    # The transaction flip must NOT have run.
    conn.execute.assert_not_awaited()


def test_model_activate_flips_active_row() -> None:
    conn = _make_conn()
    # First fetchrow = target exists; second = previous active row.
    conn.fetchrow.side_effect = [
        {"version": "v1_6"},  # target
        {"version": "v1_5"},  # previous active
    ]

    with _patch_pool(conn):
        result = runner.invoke(cli_main.app, ["model", "activate", "v1_6"])

    assert result.exit_code == 0, result.output
    assert "Activated model_a v1_6" in result.output
    assert "was v1_5" in result.output

    # The flip is two UPDATEs inside the transaction: clear all then set one.
    assert conn.execute.await_count == 2
    clear_call, set_call = conn.execute.await_args_list
    assert "is_active = FALSE" in clear_call.args[0]
    assert clear_call.args[1] == "model_a"
    assert "is_active = TRUE" in set_call.args[0]
    assert set_call.args[1] == "model_a"
    assert set_call.args[2] == "v1_6"


def test_model_activate_no_previous_active() -> None:
    conn = _make_conn()
    conn.fetchrow.side_effect = [
        {"version": "v1_6"},  # target
        None,  # no previously active row
    ]

    with _patch_pool(conn):
        result = runner.invoke(cli_main.app, ["model", "activate", "v1_6"])

    assert result.exit_code == 0, result.output
    assert "was (none)" in result.output


def test_model_list_empty_rows() -> None:
    conn = _make_conn()
    conn.fetch.return_value = []

    with _patch_pool(conn):
        result = runner.invoke(cli_main.app, ["model", "list"])

    assert result.exit_code == 0, result.output
    assert "no versions found for model_a" in result.output


def test_model_list_renders_rows() -> None:
    conn = _make_conn()
    from datetime import datetime

    conn.fetch.return_value = [
        {
            "version": "v1_6",
            "roc_auc": 0.5432,
            "is_active": True,
            "trained_at": datetime(2026, 5, 1, tzinfo=UTC),
            "notes": "best so far",
        },
        {
            "version": "v1_5",
            "roc_auc": None,
            "is_active": False,
            "trained_at": None,
            "notes": None,
        },
    ]

    with _patch_pool(conn):
        result = runner.invoke(cli_main.app, ["model", "list"])

    assert result.exit_code == 0, result.output
    assert "v1_6" in result.output
    assert "0.5432" in result.output
    assert "best so far" in result.output
