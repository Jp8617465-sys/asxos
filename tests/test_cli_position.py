"""
CLI tests for `asx position` (monitor + history).

Covers the audit P1 coverage gap on asxos/cli/position.py:
  - the `_require_personal_use()` firewall gate on both `monitor` and `history`
    (ASXOS_PERSONAL_USE unset -> non-zero exit; set -> gate passes)
  - the `--as-of` date parse inside `_monitor_async`:
      * a valid ISO date is accepted and flows through to MonitorInput.as_of
      * an invalid ISO date raises (ValueError) -> non-zero exit, no DB touched

These tests patch the db pool (init_pool/close_pool/acquire) and the network
fetchers so no live Postgres / EODHD / FRED connection is made.

Note: this module imports cleanly in CI. The `asxos.cli.main` app aggregates
other sub-apps (predict etc.) that pull joblib/lightgbm; in the bare sandbox
those are absent and collection of the whole suite may error there — but this
file's own imports do not require them, and the tests pass on Render.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import position as position_mod

runner = CliRunner()


@asynccontextmanager
async def _fake_acquire() -> Any:
    """Yield a MagicMock conn with async DB methods."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    yield conn


# ---------------------------------------------------------------------------
# firewall gate — unset path (non-zero exit, no fetch/DB work)
# ---------------------------------------------------------------------------

def test_monitor_firewall_unset_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(position_mod, "init_pool", new=AsyncMock()) as init_p,
        patch.object(position_mod, "fetch_price_data", new=AsyncMock()) as fetch_p,
    ):
        result = runner.invoke(cli_main.app, ["position", "monitor", "BHP.AU"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE" in result.output
    # Gate fires before any pool init or network fetch.
    init_p.assert_not_awaited()
    fetch_p.assert_not_awaited()


def test_history_firewall_unset_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with patch.object(position_mod, "init_pool", new=AsyncMock()) as init_p:
        result = runner.invoke(cli_main.app, ["position", "history", "BHP.AU"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE" in result.output
    init_p.assert_not_awaited()


# ---------------------------------------------------------------------------
# firewall gate — set path lets history through to list_runs
# ---------------------------------------------------------------------------

def test_history_firewall_set_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with (
        patch.object(position_mod, "init_pool", new=AsyncMock()),
        patch.object(position_mod, "close_pool", new=AsyncMock()) as close_p,
        patch.object(position_mod, "acquire", side_effect=_fake_acquire),
        patch.object(position_mod, "list_runs", new=AsyncMock(return_value=[])) as list_runs_p,
        patch.object(position_mod, "format_history", return_value="HISTORY-TABLE"),
    ):
        result = runner.invoke(
            cli_main.app, ["position", "history", "BHP.AU", "-n", "3"]
        )

    assert result.exit_code == 0, result.output
    assert "HISTORY-TABLE" in result.output
    list_runs_p.assert_awaited_once()
    # limit option threaded through as keyword.
    assert list_runs_p.await_args.kwargs["limit"] == 3
    # symbol is the positional arg after conn.
    assert list_runs_p.await_args.args[1] == "BHP.AU"
    close_p.assert_awaited_once()


# ---------------------------------------------------------------------------
# --as-of parse: valid date flows to MonitorInput.as_of
# ---------------------------------------------------------------------------

def _price_stub() -> MagicMock:
    pd = MagicMock()
    pd.current_price = Decimal("100.00")
    pd.ma_50d = Decimal("95.00")
    pd.ma_200d = Decimal("90.00")
    pd.avg_weekly_move = Decimal("2.00")
    return pd


def _macro_stub() -> MagicMock:
    md = MagicMock()
    md.vix_5d_move = Decimal("1.00")
    md.hy_oas_5d_move = Decimal("0.10")
    return md


def test_monitor_valid_as_of_flows_to_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    captured: dict[str, Any] = {}

    def _capture_build(inputs: Any, thesis_underlyings: Any = None) -> str:
        captured["inputs"] = inputs
        return "MONITOR-RESULT"

    with (
        patch.object(position_mod, "init_pool", new=AsyncMock()),
        patch.object(position_mod, "close_pool", new=AsyncMock()),
        patch.object(position_mod, "acquire", side_effect=_fake_acquire),
        patch.object(position_mod, "fetch_price_data", new=AsyncMock(return_value=_price_stub())),
        patch.object(position_mod, "fetch_macro_data", new=AsyncMock(return_value=_macro_stub())),
        patch.object(position_mod, "get_last_sentiment_inputs", new=AsyncMock(return_value=None)),
        patch.object(position_mod, "load_position_context", new=AsyncMock(return_value={})),
        patch.object(position_mod, "list_thesis_underlyings", new=AsyncMock(return_value=None)),
        patch.object(position_mod, "build_monitor_result", side_effect=_capture_build),
        patch.object(position_mod, "format_monitor", return_value="FMT"),
    ):
        # --no-save avoids the save_run/acquire round-trip; manual prompts get
        # defaults supplied on stdin (retail, sentiment, vol-skip, si-skip).
        result = runner.invoke(
            cli_main.app,
            ["position", "monitor", "BHP.AU", "--as-of", "2026-03-01", "--no-save"],
            input="\n\n\n\n",
        )

    assert result.exit_code == 0, result.output
    assert "FMT" in result.output
    assert captured["inputs"].as_of == date(2026, 3, 1)
    assert captured["inputs"].symbol == "BHP.AU"


# ---------------------------------------------------------------------------
# --as-of parse: invalid date -> non-zero exit, no fetch/DB work
# ---------------------------------------------------------------------------

def test_monitor_invalid_as_of_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with (
        patch.object(position_mod, "init_pool", new=AsyncMock()) as init_p,
        patch.object(position_mod, "fetch_price_data", new=AsyncMock()) as fetch_p,
    ):
        result = runner.invoke(
            cli_main.app,
            ["position", "monitor", "BHP.AU", "--as-of", "not-a-date"],
        )

    # date.fromisoformat raises ValueError before any fetch/pool work.
    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    init_p.assert_not_awaited()
    fetch_p.assert_not_awaited()
