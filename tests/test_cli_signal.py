"""
CLI tests for `asx signal <symbol>`.

Patches the db pool (init_pool / close_pool / acquire) on the `signal` command
module so the test exercises Typer wiring, the row-None Exit(1) branch, the
str-vs-dict shap_factors handling, and the abs-sorted SHAP ordering/truncation
— without a real Postgres connection.

NOTE: this module imports `asxos.cli.main`, which transitively imports the
predict command's ML stack. In the bare sandbox without numpy/lightgbm/sklearn
this collection-errors; it collects and passes in CI / on Render where the ML
extras are installed (see CLAUDE.md "Known test environment gaps").
"""
from __future__ import annotations

import datetime as dt
import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import signal as signal_mod

runner = CliRunner()


def _row(shap_factors: Any) -> dict[str, Any]:
    return {
        "model": "model_a",
        "model_version": "v1_5",
        "as_of": dt.date(2026, 6, 1),
        "prob_up": 0.642,
        "expected_return": 0.0123,
        "signal_label": "BUY",
        "confidence": "high",
        "regime": "risk_on",
        "shap_factors": shap_factors,
    }


def _invoke(fetchrow_return: Any, extra_args: list[str] | None = None) -> Any:
    """Patch the pool + acquire on signal_mod and invoke the command."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)

    @asynccontextmanager
    async def _conn() -> Any:
        yield conn

    with (
        patch.object(signal_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(signal_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(signal_mod, "acquire") as acquire_patch,
    ):
        acquire_patch.side_effect = _conn
        result = runner.invoke(cli_main.app, ["signal", "BHP.AU", *(extra_args or [])])
    return result, conn


def test_signal_row_none_exits_nonzero() -> None:
    result, conn = _invoke(None)
    assert result.exit_code == 1, result.output
    assert "No signal found for BHP.AU" in result.output
    # The query was actually issued with the symbol arg.
    conn.fetchrow.assert_awaited_once()
    assert conn.fetchrow.await_args.args[-1] == "BHP.AU"


def test_signal_dict_shap_orders_by_abs_value() -> None:
    # rsi has the largest magnitude despite being negative; bias is excluded.
    shap = {"bias": 9.9, "rsi_14": -0.5, "momentum": 0.2, "volume": 0.05}
    result, _ = _invoke(_row(shap), ["--shap-n", "3"])
    assert result.exit_code == 0, result.output
    assert "BHP.AU" in result.output
    assert "BUY" in result.output
    assert "drivers:" in result.output

    drivers_line = next(
        line for line in result.output.splitlines() if "drivers:" in line
    )
    # bias must be filtered out.
    assert "bias" not in drivers_line
    # abs-sorted: rsi_14 (0.5) before momentum (0.2) before volume (0.05).
    assert drivers_line.index("rsi_14") < drivers_line.index("momentum")
    assert drivers_line.index("momentum") < drivers_line.index("volume")
    # signed formatting to 3dp.
    assert "rsi_14-0.500" in drivers_line
    assert "momentum+0.200" in drivers_line


def test_signal_str_shap_is_json_decoded() -> None:
    # shap_factors arriving as a JSON string (jsonb-as-text) must be parsed.
    shap_str = json.dumps({"rsi_14": 0.4, "macd": -0.1})
    result, _ = _invoke(_row(shap_str), ["--shap-n", "5"])
    assert result.exit_code == 0, result.output
    drivers_line = next(
        line for line in result.output.splitlines() if "drivers:" in line
    )
    assert "rsi_14+0.400" in drivers_line
    assert "macd-0.100" in drivers_line


def test_signal_shap_truncated_to_shap_n() -> None:
    shap = {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.6, "e": 0.5}
    result, _ = _invoke(_row(shap), ["--shap-n", "2"])
    assert result.exit_code == 0, result.output
    drivers_line = next(
        line for line in result.output.splitlines() if "drivers:" in line
    )
    # Only the top-2 by magnitude survive.
    assert "a+0.900" in drivers_line
    assert "b+0.800" in drivers_line
    assert "c+0.700" not in drivers_line
    assert "d" not in drivers_line.replace("drivers", "")
    assert "e+0.500" not in drivers_line


def test_signal_empty_shap_omits_drivers_line() -> None:
    # None shap_factors -> {} -> no drivers line, but still exits 0 with the header.
    result, _ = _invoke(_row(None))
    assert result.exit_code == 0, result.output
    assert "BHP.AU" in result.output
    assert "drivers:" not in result.output


def test_signal_none_valued_shap_factor_skipped() -> None:
    # A factor with a None value must be filtered (the `v is not None` guard).
    shap = {"rsi_14": None, "macd": 0.3}
    result, _ = _invoke(_row(shap))
    assert result.exit_code == 0, result.output
    drivers_line = next(
        line for line in result.output.splitlines() if "drivers:" in line
    )
    assert "macd+0.300" in drivers_line
    assert "rsi_14" not in drivers_line
