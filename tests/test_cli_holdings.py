"""
CLI tests for `asx import-holdings` (asxos/cli/holdings.py).

Covers:
- _infer_currency pure mapping (.US -> USD, else AUD)
- the _require_personal_use firewall gate (ASXOS_PERSONAL_USE set vs unset)
- the --dry-run path: parses + prints, writes nothing (no DB hand-off)

The CLI wiring is exercised via Typer's CliRunner. parse_csv is patched at its
definition module (the command imports it lazily inside the function body), so
no real CSV file or DB connection is touched.

Collection note: this module imports only the thin CLI layer + rich/typer.
It has no numpy/lightgbm/fastapi dependency, so it collects in the bare sandbox.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli.holdings import _infer_currency
from asxos.domain.tax.import_csv import LotRow

runner = CliRunner()


def _lot(symbol: str = "BHP.AU") -> LotRow:
    return LotRow(
        symbol=symbol,
        acquired_at=date(2024, 1, 15),
        quantity=Decimal("100"),
        cost_base_normal=Decimal("4500.00"),
        cost_base_div296=Decimal("4500.00"),
        account_type="individual",
        broker_ref="ABC123",
        notes="seed lot",
    )


# --- _infer_currency (pure) -------------------------------------------------


def test_infer_currency_us_suffix_returns_usd() -> None:
    assert _infer_currency("AAPL.US") == "USD"


def test_infer_currency_asx_returns_aud() -> None:
    assert _infer_currency("BHP.AU") == "AUD"
    assert _infer_currency("CBA") == "AUD"


# --- firewall gate ----------------------------------------------------------


def test_import_holdings_blocks_without_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)

    with patch("asxos.domain.tax.import_csv.parse_csv") as parse_patch:
        result = runner.invoke(cli_main.app, ["import-holdings", "lots.csv", "--dry-run"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    # Gate fires before any parsing happens.
    parse_patch.assert_not_called()


# --- dry-run path -----------------------------------------------------------


def test_import_holdings_dry_run_prints_and_does_not_write(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    rows = [_lot("BHP.AU"), _lot("AAPL.US")]

    with (
        patch("asxos.domain.tax.import_csv.parse_csv", return_value=rows) as parse_patch,
        patch("asxos.cli.holdings._run_import_holdings") as run_patch,
    ):
        result = runner.invoke(cli_main.app, ["import-holdings", "lots.csv", "--dry-run"])

    assert result.exit_code == 0, result.output
    parse_patch.assert_called_once()
    assert "Parsed 2 rows from lots.csv" in result.output
    assert "--dry-run: no rows written." in result.output
    # Dry-run must NOT hand off to the async DB writer.
    run_patch.assert_not_called()
    # No "Inserted" success line on the dry-run branch.
    assert "Inserted" not in result.output
