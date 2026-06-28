"""
CLI-layer tests for `asxos/cli/portfolio.py`.

These exercise the Typer wiring and the pre-`asyncio.run` validation
branches only:

  * the ASXOS_PERSONAL_USE firewall (set vs unset),
  * --as-of / --signals ISO date parsing,
  * --dry-run forcing --no-persist (plan H.1 CRITICAL-6),
  * the explicit --no-persist flag,
  * propose-trades --side validation.

The domain allocator (`PortfolioService.build`) is NOT re-tested here.
We patch the module-local `_run_build_portfolio` / `_run_propose_trades`
coroutines so the command body runs but no DB / allocator is touched, and
we assert on the arguments the CLI passes down (the real branch behaviour),
not on allocator output.

Collection note: `asxos.cli.portfolio` only imports typer/rich/db lazily;
the heavy domain imports live inside the `_run_*` coroutines, so this file
collects cleanly even in the bare sandbox.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import portfolio as portfolio_mod

runner = CliRunner()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _norm(output: str) -> str:
    """Strip ANSI colour codes and collapse all whitespace runs to single spaces.

    typer/rich renders a raised ``BadParameter`` inside a bordered, colour-styled
    panel and soft-wraps the message at the console width, so the raw error string
    is not a contiguous substring of ``result.output``. Normalising lets us assert
    the message text without coupling to rich's panel layout.
    """
    return " ".join(_ANSI.sub("", output).split())


@pytest.fixture
def personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


@pytest.fixture
def no_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)


# ---------------------------------------------------------------------------
# Firewall gate (_require_personal_use)
# ---------------------------------------------------------------------------

def test_build_portfolio_requires_personal_use(no_personal_use: None) -> None:
    # Patch the runner so that if the firewall *failed* to fire we'd still
    # not touch the DB; the assertion is that it never gets called.
    async def _should_not_run(**_: Any) -> None:  # pragma: no cover
        raise AssertionError("firewall must block before _run_build_portfolio")

    with patch.object(portfolio_mod, "_run_build_portfolio", new=_should_not_run):
        result = runner.invoke(cli_main.app, ["build-portfolio"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output


def test_propose_trades_requires_personal_use(no_personal_use: None) -> None:
    async def _should_not_run(**_: Any) -> None:  # pragma: no cover
        raise AssertionError("firewall must block before _run_propose_trades")

    with patch.object(portfolio_mod, "_run_propose_trades", new=_should_not_run):
        result = runner.invoke(cli_main.app, ["propose-trades"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output


# ---------------------------------------------------------------------------
# build-portfolio: date parsing
# ---------------------------------------------------------------------------

def test_build_portfolio_bad_as_of(personal_use: None) -> None:
    async def _should_not_run(**_: Any) -> None:  # pragma: no cover
        raise AssertionError("bad --as-of must be rejected before run")

    with patch.object(portfolio_mod, "_run_build_portfolio", new=_should_not_run):
        result = runner.invoke(cli_main.app, ["build-portfolio", "--as-of", "not-a-date"])

    assert result.exit_code != 0
    assert "--as-of must be YYYY-MM-DD" in _norm(result.output)


def test_build_portfolio_bad_signals(personal_use: None) -> None:
    async def _should_not_run(**_: Any) -> None:  # pragma: no cover
        raise AssertionError("bad --signals must be rejected before run")

    with patch.object(portfolio_mod, "_run_build_portfolio", new=_should_not_run):
        result = runner.invoke(cli_main.app, ["build-portfolio", "--signals", "2026-13-99"])

    assert result.exit_code != 0
    assert "--signals must be YYYY-MM-DD" in _norm(result.output)


def test_build_portfolio_parses_valid_dates(personal_use: None) -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> None:
        captured.update(kwargs)

    with patch.object(portfolio_mod, "_run_build_portfolio", new=_capture):
        result = runner.invoke(
            cli_main.app,
            ["build-portfolio", "--as-of", "2026-05-15", "--signals", "2026-05-14"],
        )

    assert result.exit_code == 0, result.output
    assert captured["as_of"] == date(2026, 5, 15)
    assert captured["signals_date"] == date(2026, 5, 14)


# ---------------------------------------------------------------------------
# build-portfolio: dry_run -> no_persist, and --no-persist flag
# ---------------------------------------------------------------------------

def test_build_portfolio_dry_run_forces_no_persist(personal_use: None) -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> None:
        captured.update(kwargs)

    # --dry-run alone, even though --persist defaults True, must yield do_persist=False.
    with patch.object(portfolio_mod, "_run_build_portfolio", new=_capture):
        result = runner.invoke(cli_main.app, ["build-portfolio", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert captured["do_persist"] is False


def test_build_portfolio_default_persists(personal_use: None) -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> None:
        captured.update(kwargs)

    with patch.object(portfolio_mod, "_run_build_portfolio", new=_capture):
        result = runner.invoke(cli_main.app, ["build-portfolio"])

    assert result.exit_code == 0, result.output
    assert captured["do_persist"] is True
    # default constraint/tax flags are inverted from the negative options
    assert captured["apply_constraints"] is True
    assert captured["apply_tax_overlay"] is True


def test_build_portfolio_no_persist_flag(personal_use: None) -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> None:
        captured.update(kwargs)

    with patch.object(portfolio_mod, "_run_build_portfolio", new=_capture):
        result = runner.invoke(
            cli_main.app,
            ["build-portfolio", "--no-persist", "--no-constraints", "--no-tax-overlay"],
        )

    assert result.exit_code == 0, result.output
    assert captured["do_persist"] is False
    assert captured["apply_constraints"] is False
    assert captured["apply_tax_overlay"] is False


# ---------------------------------------------------------------------------
# propose-trades: --side validation
# ---------------------------------------------------------------------------

def test_propose_trades_invalid_side(personal_use: None) -> None:
    async def _should_not_run(**_: Any) -> None:  # pragma: no cover
        raise AssertionError("invalid --side must be rejected before run")

    with patch.object(portfolio_mod, "_run_propose_trades", new=_should_not_run):
        result = runner.invoke(cli_main.app, ["propose-trades", "--side", "long"])

    assert result.exit_code != 0
    assert "--side must be buy, sell, or hold" in _norm(result.output)


@pytest.mark.parametrize("side", ["buy", "sell", "hold"])
def test_propose_trades_valid_side_passes_through(personal_use: None, side: str) -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> None:
        captured.update(kwargs)

    with patch.object(portfolio_mod, "_run_propose_trades", new=_capture):
        result = runner.invoke(cli_main.app, ["propose-trades", "--side", side])

    assert result.exit_code == 0, result.output
    assert captured["side"] == side
    assert captured["run_id"] is None
