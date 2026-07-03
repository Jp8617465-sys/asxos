"""CLI tests for `asx agent-run log` — firewall gate + service wiring.

Exercises the Typer wiring in ``asxos/cli/agent_run.py`` without a real
Postgres connection, following the exact fixture pattern established in
``tests/test_cli_thesis.py``.

Note: same joblib-collection-error sandbox gap as ``test_cli_thesis.py`` (see
that file's docstring for the full import chain) — passes on Render.

Also note: ``agent_run_app`` registers exactly one command ("log"). Typer
collapses a single-command sub-Typer into direct invocation when tested in
isolation (``runner.invoke(agent_run_app, [...])`` would need to omit "log"
entirely) — but once nested under the real ``cli_main.app`` (as
``asxos/cli/main.py`` actually does via
``app.add_typer(agent_run_app, name="agent-run")``), group semantics apply
normally and "log" IS required, exactly as used below. Verified this
distinction manually (both the bare-app collapse and the nested-parent
behavior) before writing this file.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import agent_run as ar_mod
from asxos.cli import main as cli_main

runner = CliRunner()


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
        patch.object(ar_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(ar_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(ar_mod, "acquire") as acquire_patch,
    ):
        acquire_patch.side_effect = lambda: _acquire_ctx(conn)
        yield conn


def test_log_without_personal_use_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(ar_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(ar_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(
            cli_main.app,
            ["agent-run", "log", "macro-economist", "--summary", "x"],
        )

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_log_invokes_service_with_correct_args(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        ar_mod.svc, "log_agent_run", new=AsyncMock(return_value=99)
    ) as log_patch:
        result = runner.invoke(
            cli_main.app,
            [
                "agent-run", "log", "macro-economist",
                "--object-type", "macro_thesis",
                "--summary", "Proposed 1 macro thesis",
                "--proposal-json", "{}",
                "--evidence-json", "[]",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "#99" in result.output
    log_patch.assert_awaited_once()
    call_args = log_patch.await_args
    assert call_args.args[1] == "macro-economist"
    assert call_args.kwargs["object_type"] == "macro_thesis"
    assert call_args.kwargs["summary"] == "Proposed 1 macro thesis"
    assert call_args.kwargs["proposal_raw"] == "{}"
    assert call_args.kwargs["evidence_raw"] == "[]"


def test_log_omits_optional_args_as_none(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    """An evidence-only run (no --object-type/--proposal-json) passes None
    for both, not empty strings — log_agent_run()'s
    (object_type is None) == (proposal_raw is None) check depends on this."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        ar_mod.svc, "log_agent_run", new=AsyncMock(return_value=100)
    ) as log_patch:
        result = runner.invoke(
            cli_main.app,
            ["agent-run", "log", "macro-economist", "--summary", "Evidence-only run"],
        )

    assert result.exit_code == 0, result.output
    call_kwargs = log_patch.await_args.kwargs
    assert call_kwargs["object_type"] is None
    assert call_kwargs["proposal_raw"] is None
    assert call_kwargs["evidence_raw"] is None
    assert call_kwargs["subject"] is None


def test_log_missing_summary_exits_nonzero() -> None:
    result = runner.invoke(cli_main.app, ["agent-run", "log", "macro-economist"])
    assert result.exit_code != 0


def test_log_service_valueerror_exits_nonzero_with_message(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        ar_mod.svc, "log_agent_run",
        new=AsyncMock(side_effect=ValueError("evidence_citation_ids references evidence_id=5, which has tier='speculative'")),
    ):
        result = runner.invoke(
            cli_main.app,
            [
                "agent-run", "log", "macro-economist",
                "--object-type", "macro_thesis",
                "--summary", "x", "--proposal-json", "{}",
            ],
        )

    assert result.exit_code != 0
    assert "speculative" in result.output
