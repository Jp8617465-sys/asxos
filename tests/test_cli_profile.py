"""
CLI tests for `asx profile {init,show,activate,list}` (asxos/cli/profile.py).

Patches the db pool (init_pool/close_pool/acquire) and the lazily-imported
domain functions in `asxos.domain.portfolio.profile`, so the tests exercise
the Typer wiring, the personal-use firewall, comma-split exclusion parsing,
and the p-is-None exit-1 path — without a real Postgres connection.

Collects cleanly in the bare sandbox (no numpy/lightgbm/fastapi imports).
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, asynccontextmanager, contextmanager
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import profile as profile_mod
from asxos.domain.portfolio import profile as domain_profile

runner = CliRunner()


@asynccontextmanager
async def _conn_ctx(conn: Any) -> Any:
    yield conn


def _patch_pool(conn: Any):
    """Patch init_pool/close_pool/acquire on the cli.profile module."""
    return [
        patch.object(profile_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(profile_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(profile_mod, "acquire", side_effect=lambda: _conn_ctx(conn)),
    ]


@contextmanager
def _patched(conn: Any, **domain_mocks: Any) -> Iterator[None]:
    """Enter the pool patches plus any `asxos.domain.portfolio.profile` attribute
    mocks (passed by name). Replaces the old `with (*_patch_pool(conn), ...)` form,
    which Python parses as a single tuple display — not a parenthesized with-items
    list — and so fails with 'tuple object does not support the context manager
    protocol'.
    """
    with ExitStack() as stack:
        for cm in _patch_pool(conn):
            stack.enter_context(cm)
        for name, mock in domain_mocks.items():
            stack.enter_context(patch.object(domain_profile, name, mock))
        yield


def _fake_profile(**over: Any) -> SimpleNamespace:
    base = {
        "profile_id": 7,
        "name": "baseline",
        "is_active": True,
        "account_type": "individual",
        "risk_tolerance": "balanced",
        "risk_tolerance_scalar": Decimal("1.0"),
        "capital_aud": Decimal("100000.00"),
        "cash_floor_pct": Decimal("0.05"),
        "leverage_cap": Decimal("1.0"),
        "per_name_cap_pct": Decimal("0.10"),
        "sector_cap_pct": Decimal("0.30"),
        "excluded_sectors": ("Energy",),
        "excluded_symbols": ("BHP.AU",),
        "min_position_aud": Decimal("1000.00"),
        "horizon_years": 10,
        "defer_near_boundary_sells": True,
        "score_weights_json": {"prob_up": Decimal("0.6"), "expected_return": Decimal("0.4")},
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 6, 1),
    }
    base.update(over)
    return SimpleNamespace(**base)


# --------------------------------------------------------------------------
# Firewall: ASXOS_PERSONAL_USE unset → non-zero exit on every command.
# --------------------------------------------------------------------------

def test_firewall_blocks_when_flag_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    result = runner.invoke(cli_main.app, ["profile", "list"])
    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output


# --------------------------------------------------------------------------
# init: comma-split exclusion parsing → passed to domain save().
# --------------------------------------------------------------------------

def test_init_parses_comma_split_exclusions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    save = AsyncMock(return_value=42)
    activate = AsyncMock(return_value=42)

    with _patched(conn, save=save, activate=activate):
        result = runner.invoke(
            cli_main.app,
            [
                "profile", "init",
                "--name", "growth1",
                "--capital", "50000",
                "--exclude-sectors", " Energy , Materials ,",
                "--exclude-symbols", "BHP.AU,, RIO.AU ",
                "--activate",
            ],
        )

    assert result.exit_code == 0, result.output
    assert save.await_count == 1
    kwargs = save.await_args.kwargs
    # whitespace stripped, empty tokens dropped
    assert kwargs["excluded_sectors"] == ("Energy", "Materials")
    assert kwargs["excluded_symbols"] == ("BHP.AU", "RIO.AU")
    assert kwargs["capital_aud"] == Decimal("50000.0")
    # --activate flows to domain activate()
    assert activate.await_count == 1
    assert activate.await_args.args[1] == "growth1"
    assert "Created profile" in result.output
    assert "Activated" in result.output


def test_init_value_error_becomes_bad_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    save = AsyncMock(side_effect=ValueError("cash_floor out of range"))

    with _patched(conn, save=save):
        result = runner.invoke(
            cli_main.app,
            ["profile", "init", "--capital", "1000"],
        )

    assert result.exit_code != 0
    assert "cash_floor out of range" in result.output


# --------------------------------------------------------------------------
# show: present vs p-is-None (exit 1).
# --------------------------------------------------------------------------

def test_show_renders_active_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    load_active = AsyncMock(return_value=_fake_profile())

    with _patched(conn, load_active=load_active):
        result = runner.invoke(cli_main.app, ["profile", "show"])

    assert result.exit_code == 0, result.output
    assert load_active.await_count == 1
    assert "baseline" in result.output
    assert "individual" in result.output


def test_show_by_name_uses_load_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    load_by_name = AsyncMock(return_value=_fake_profile(name="other"))

    with _patched(conn, load_by_name=load_by_name):
        result = runner.invoke(cli_main.app, ["profile", "show", "--name", "other"])

    assert result.exit_code == 0, result.output
    assert load_by_name.await_args.args[1] == "other"
    assert "other" in result.output


def test_show_none_named_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    load_by_name = AsyncMock(return_value=None)

    with _patched(conn, load_by_name=load_by_name):
        result = runner.invoke(cli_main.app, ["profile", "show", "--name", "ghost"])

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_show_none_active_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    load_active = AsyncMock(return_value=None)

    with _patched(conn, load_active=load_active):
        result = runner.invoke(cli_main.app, ["profile", "show"])

    assert result.exit_code == 1
    assert "No active profile" in result.output


# --------------------------------------------------------------------------
# activate: success + domain error → BadParameter.
# --------------------------------------------------------------------------

def test_activate_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    activate = AsyncMock(return_value=9)

    with _patched(conn, activate=activate):
        result = runner.invoke(cli_main.app, ["profile", "activate", "growth1"])

    assert result.exit_code == 0, result.output
    assert activate.await_args.args[1] == "growth1"
    assert "Activated" in result.output
    assert "9" in result.output


def test_activate_error_becomes_bad_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    activate = AsyncMock(side_effect=Exception("no such profile"))

    with _patched(conn, activate=activate):
        result = runner.invoke(cli_main.app, ["profile", "activate", "ghost"])

    assert result.exit_code != 0
    assert "no such profile" in result.output


# --------------------------------------------------------------------------
# list: empty vs populated.
# --------------------------------------------------------------------------

def test_list_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    list_profiles = AsyncMock(return_value=[])

    with _patched(conn, list_profiles=list_profiles):
        result = runner.invoke(cli_main.app, ["profile", "list"])

    assert result.exit_code == 0, result.output
    assert "No profiles yet" in result.output


def test_list_populated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    rows = [_fake_profile(profile_id=1, name="baseline"),
            _fake_profile(profile_id=2, name="growth1", is_active=False)]
    list_profiles = AsyncMock(return_value=rows)

    with _patched(conn, list_profiles=list_profiles):
        result = runner.invoke(cli_main.app, ["profile", "list"])

    assert result.exit_code == 0, result.output
    assert "baseline" in result.output
    assert "growth1" in result.output
    assert "Profiles (2)" in result.output
