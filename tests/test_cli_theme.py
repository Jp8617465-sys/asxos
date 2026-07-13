"""CLI firewall-gate tests for `asx theme` (risk-register R12).

The 7 pre-existing theme commands (create / list / coverage / review,
adjacency add, stage, attach) were missing the `_require_personal_use()`
s766B firewall gate that the 4 governance verbs (approve / reject x
theme / holding) already carried — a firewall-integrity gap. This pins the
gate on all 7: with ASXOS_PERSONAL_USE unset each must exit non-zero with the
firewall message, before any pool init; with it set, the gate no longer blocks.

Imports `asxos.cli.theme` directly (not `asxos.cli.main`, which aggregates
sub-apps that pull joblib/lightgbm), so this file carries no ML dependency and
collects in the bare sandbox as well as on Render.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import theme as theme_mod

runner = CliRunner()

# The 7 previously-ungated commands. Args are the minimum that parse cleanly so
# control reaches the function body, where `_require_personal_use()` is the first
# statement.
_GATED_COMMANDS = [
    pytest.param(["create", "ai-infra", "--name", "AI", "--description", "d"], id="create"),
    pytest.param(["list"], id="list"),
    pytest.param(["coverage"], id="coverage"),
    pytest.param(["review", "ai-infra"], id="review"),
    pytest.param(["adjacency", "add", "a", "b"], id="adjacency-add"),
    pytest.param(["stage", "ai-infra", "early", "--note", "n"], id="stage"),
    pytest.param(["attach", "ai-infra", "CBA.AU", "--strength", "0.5"], id="attach"),
]


@pytest.mark.parametrize("argv", _GATED_COMMANDS)
def test_theme_command_requires_personal_use(
    argv: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every theme command hard-fails (non-zero exit) with the firewall message
    when ASXOS_PERSONAL_USE is unset, before any pool init."""
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with patch.object(theme_mod, "init_pool", new=AsyncMock()) as init_p:
        result = runner.invoke(theme_mod.theme_app, argv)
    assert result.exit_code != 0, result.output
    assert "ASXOS_PERSONAL_USE" in result.output
    # Gate fires before any pool init / DB work.
    init_p.assert_not_awaited()


def test_theme_command_gate_passes_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the flag set, the gate no longer blocks — control proceeds past it to
    the (stubbed) DB path, confirming the gate is the only thing the unset tests
    tripped on."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")

    @asynccontextmanager
    async def _fake_acquire() -> Any:
        yield MagicMock()

    with (
        patch.object(theme_mod, "init_pool", new=AsyncMock()),
        patch.object(theme_mod, "close_pool", new=AsyncMock()),
        patch.object(theme_mod, "acquire", new=_fake_acquire),
        patch.object(theme_mod.svc, "list_themes", new=AsyncMock(return_value=[])),
    ):
        result = runner.invoke(theme_mod.theme_app, ["list"])

    assert result.exit_code == 0, result.output
