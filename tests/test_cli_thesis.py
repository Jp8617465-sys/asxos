"""CLI tests for `asx thesis` — firewall gate + not-found + empty rendering.

Exercises the Typer wiring in ``asxos/cli/thesis.py`` without a real Postgres
connection. We patch the module-level pool functions (``init_pool`` /
``close_pool`` / ``acquire``) and the ``svc`` service object so the test drives
the command branches deterministically.

Covered:
  - ``_require_personal_use`` firewall: with ASXOS_PERSONAL_USE unset, a gated
    command exits non-zero before touching the DB.
  - ``thesis show`` for a symbol with no thesis → typer.Exit(1).
  - ``thesis list`` with an empty result set → friendly "No theses found."

Note: this collects cleanly in the bare sandbox — ``asxos.cli.thesis`` pulls
only typer/rich/Decimal, no numpy/lightgbm/fastapi.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import thesis as thesis_mod

runner = CliRunner()


def _make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


@asynccontextmanager
async def _acquire_ctx(conn: MagicMock) -> Any:
    yield conn


@pytest.fixture
def patched_pool() -> Any:
    """Patch pool + acquire on the thesis CLI module; yield the mock conn."""
    conn = _make_conn()
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(thesis_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        acquire_patch.side_effect = lambda: _acquire_ctx(conn)
        yield conn


# ---------------------------------------------------------------------------
# Firewall gate
# ---------------------------------------------------------------------------

def test_show_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    # Guard: the firewall must trip before any DB call. If init_pool ran the
    # AsyncMock would record a call; we assert it never does.
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_list_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    result = runner.invoke(cli_main.app, ["thesis", "list"])
    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output


# ---------------------------------------------------------------------------
# show — not found
# ---------------------------------------------------------------------------

def test_show_not_found_exits_1(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol", new=AsyncMock(return_value=None)
    ) as get_patch:
        result = runner.invoke(cli_main.app, ["thesis", "show", "ZZZ.AU"])

    assert result.exit_code == 1
    assert "No thesis found for ZZZ.AU" in result.output
    get_patch.assert_awaited_once()


# ---------------------------------------------------------------------------
# list — empty rendering
# ---------------------------------------------------------------------------

def test_list_empty_renders_friendly_message(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "list_theses", new=AsyncMock(return_value=[])
    ) as list_patch:
        result = runner.invoke(cli_main.app, ["thesis", "list"])

    assert result.exit_code == 0, result.output
    assert "No theses found." in result.output
    # No status filter was passed → status kwarg is None.
    list_patch.assert_awaited_once()
    assert list_patch.await_args.kwargs == {"status": None}


def test_list_with_status_filter_passes_through(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "list_theses", new=AsyncMock(return_value=[])
    ) as list_patch:
        result = runner.invoke(
            cli_main.app, ["thesis", "list", "--status", "active"]
        )

    assert result.exit_code == 0, result.output
    list_patch.assert_awaited_once()
    assert list_patch.await_args.kwargs == {"status": "active"}
