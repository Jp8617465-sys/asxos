"""CLI tests for `asx macro-thesis` — firewall gate + service wiring.

Exercises the Typer wiring in ``asxos/cli/macro_thesis.py`` without a real
Postgres connection, following the exact fixture pattern established in
``tests/test_cli_thesis.py`` (patch module-level pool functions + ``svc``).

Note: same joblib-collection-error sandbox gap as ``test_cli_thesis.py`` —
this file imports ``from asxos.cli import main as cli_main`` for
``runner.invoke()``, and ``cli/main.py`` wires in ``cli/predict.py`` ->
``domain/models/model_a.py`` -> ``domain/models/cache.py`` -> ``joblib``,
not installed in the sandbox venv. Passes on Render where
``pip install -e ".[ml]"`` is run — verified manually via direct script
invocation of ``macro_thesis_app`` (bypassing ``cli_main``) before writing
this file, per the same verification approach used for
``test_cli_thesis.py``'s new commands in Phase 1.
"""
from __future__ import annotations

import dataclasses
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import macro_thesis as mt_mod
from asxos.cli import main as cli_main
from asxos.domain.macro_theses.types import MacroThesis

runner = CliRunner()

_FAKE_MT = MacroThesis(
    macro_thesis_id=7,
    title="Risk-off regime persists",
    thesis_text="Elevated vol and soft iron ore point to a defensive tilt.",
    regime_quadrant="falling_growth_falling_inflation",
    horizon_months=6,
    catalyst="RBA pause",
    falsifier="AVIX below 15 for 5 sessions",
    data_signals=("avix", "iron_ore_62fe"),
    source_run_id=42,
    governance_status="pending_review",
    created_at=datetime.now(tz=UTC),
    retired_at=None,
)


def _make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


@asynccontextmanager
async def _acquire_ctx(conn: MagicMock) -> Any:
    yield conn


@pytest.fixture
def patched_pool() -> Any:
    conn = _make_conn()
    with (
        patch.object(mt_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(mt_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(mt_mod, "acquire") as acquire_patch,
    ):
        acquire_patch.side_effect = lambda: _acquire_ctx(conn)
        yield conn


# ---------------------------------------------------------------------------
# Firewall gate
# ---------------------------------------------------------------------------

def test_approve_without_personal_use_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(mt_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(mt_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(cli_main.app, ["macro-thesis", "approve", "7", "--reason", "test"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_reject_without_personal_use_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(mt_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(mt_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(cli_main.app, ["macro-thesis", "reject", "7", "--reason", "test"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_open_without_personal_use_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with patch.object(mt_mod, "init_pool", new=AsyncMock()) as init_patch:
        result = runner.invoke(cli_main.app, ["macro-thesis", "open", "--from-agent-run", "42"])

    assert result.exit_code != 0
    init_patch.assert_not_awaited()


# ---------------------------------------------------------------------------
# approve — service wiring
# ---------------------------------------------------------------------------

def test_approve_invokes_service_with_correct_args(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        mt_mod.svc, "approve_object", new=AsyncMock(return_value=_FAKE_MT)
    ) as approve_patch:
        result = runner.invoke(
            cli_main.app,
            ["macro-thesis", "approve", "7", "--reason", "Evidence checks out"],
        )

    assert result.exit_code == 0, result.output
    approve_patch.assert_awaited_once()
    call_args = approve_patch.await_args
    assert call_args.args[1] == 7
    assert call_args.kwargs["reasoning"] == "Evidence checks out"


def test_approve_missing_reason_exits_nonzero() -> None:
    result = runner.invoke(cli_main.app, ["macro-thesis", "approve", "7"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# reject — service wiring
# ---------------------------------------------------------------------------

def test_reject_invokes_service_with_correct_args(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    rejected = dataclasses.replace(_FAKE_MT, governance_status="rejected")
    with patch.object(
        mt_mod.svc, "reject_object", new=AsyncMock(return_value=rejected)
    ) as reject_patch:
        result = runner.invoke(
            cli_main.app,
            ["macro-thesis", "reject", "7", "--reason", "Catalyst didn't materialise"],
        )

    assert result.exit_code == 0, result.output
    reject_patch.assert_awaited_once()
    call_args = reject_patch.await_args
    assert call_args.args[1] == 7
    assert call_args.kwargs["reasoning"] == "Catalyst didn't materialise"


def test_reject_missing_reason_exits_nonzero() -> None:
    result = runner.invoke(cli_main.app, ["macro-thesis", "reject", "7"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# open --from-agent-run — routing + not-given guard
# ---------------------------------------------------------------------------

def test_open_from_agent_run_invokes_correct_service_function(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        mt_mod.svc, "create_macro_thesis_from_agent_run", new=AsyncMock(return_value=_FAKE_MT)
    ) as create_patch:
        result = runner.invoke(cli_main.app, ["macro-thesis", "open", "--from-agent-run", "42"])

    assert result.exit_code == 0, result.output
    create_patch.assert_awaited_once()
    assert create_patch.await_args.args[1] == 42


def test_open_without_from_agent_run_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    result = runner.invoke(cli_main.app, ["macro-thesis", "open"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# list / show
# ---------------------------------------------------------------------------

def test_list_empty_shows_friendly_message(patched_pool: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(mt_mod.svc, "list_macro_theses", new=AsyncMock(return_value=[])):
        result = runner.invoke(cli_main.app, ["macro-thesis", "list"])
    assert result.exit_code == 0
    assert "No macro theses yet" in result.output


def test_show_not_found_exits_nonzero(patched_pool: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(mt_mod.svc, "get_macro_thesis", new=AsyncMock(return_value=None)):
        result = runner.invoke(cli_main.app, ["macro-thesis", "show", "999"])
    assert result.exit_code != 0
