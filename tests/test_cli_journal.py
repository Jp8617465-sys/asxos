"""
CLI tests for `asx journal add|list|review`.

Patches the journal command module's db pool (init_pool/close_pool/acquire)
so the tests exercise the Typer wiring, the symbol='-' -> NULL sentinel,
the action-validation BadParameter path, and the empty-list/empty-review
rendering — without touching Postgres.

This module imports only typer/rich/asxos.db, so it collects cleanly even
in the bare sandbox.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import journal as journal_mod

runner = CliRunner()


@pytest.fixture(autouse=True)
def _enable_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    """journal commands are firewall-gated (ASXOS_PERSONAL_USE=1) as of the
    2026-07-18 R14 audit fix. Set it for every test here so the commands exercise
    their logic, not the gate — the gate itself is covered by
    tests/test_cli_journal_firewall.py."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


def _make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_db(conn: MagicMock) -> list[Any]:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    return [
        patch.object(journal_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(journal_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(journal_mod, "acquire", new=_acquire),
    ]


def _invoke(args: list[str], conn: MagicMock) -> Any:
    patches = _patch_db(conn)
    for p in patches:
        p.start()
    try:
        return runner.invoke(journal_mod.journal_app, args)
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# journal add
# ---------------------------------------------------------------------------


def test_journal_add_symbol_records_decision() -> None:
    """signal_ref enrichment was retired with Model A and always inserts NULL now.

    The `signals`-table lookup is gone (that table has had no writer since
    P1-02), so only one fetchrow call (the INSERT) fires.
    """
    conn = _make_conn()
    conn.fetchrow = AsyncMock(return_value={"id": 42, "decision_date": date(2026, 6, 28)})

    result = _invoke(
        ["add", "BHP.AU", "buy", "--rationale", "cheap"],
        conn,
    )

    assert result.exit_code == 0, result.output
    assert "Recorded decision" in result.output
    assert "#42" in result.output
    assert "BHP.AU" in result.output

    assert conn.fetchrow.await_count == 1
    insert_args = conn.fetchrow.await_args.args
    assert insert_args[1] == "BHP.AU"  # symbol param
    assert insert_args[3] == "BUY"  # action upper-cased
    assert insert_args[4] == "cheap"  # rationale
    assert insert_args[5] is None  # signal_ref always None post-Model-A


def test_journal_add_dash_sentinel_inserts_null_symbol() -> None:
    conn = _make_conn()
    conn.fetchrow = AsyncMock(
        return_value={"id": 7, "decision_date": date(2026, 6, 28)}
    )

    result = _invoke(
        ["add", "-", "note", "--rationale", "rebalanced"],
        conn,
    )

    assert result.exit_code == 0, result.output
    assert "portfolio" in result.output
    assert conn.fetchrow.await_count == 1
    insert_args = conn.fetchrow.await_args.args
    assert insert_args[1] is None  # symbol -> NULL
    assert insert_args[3] == "NOTE"
    assert insert_args[5] is None  # signal_ref is None for portfolio-level


def test_journal_add_rejects_invalid_action() -> None:
    conn = _make_conn()
    result = _invoke(
        ["add", "BHP.AU", "frobnicate", "--rationale", "x"],
        conn,
    )
    assert result.exit_code != 0
    assert "action must be one of" in result.output
    # No DB write attempted on the bad-action path.
    assert conn.fetchrow.await_count == 0


# ---------------------------------------------------------------------------
# journal list
# ---------------------------------------------------------------------------


def test_journal_list_empty_renders_yellow_message() -> None:
    conn = _make_conn()
    conn.fetch = AsyncMock(return_value=[])

    result = _invoke(["list", "--days", "14"], conn)

    assert result.exit_code == 0, result.output
    assert "No decisions in the last 14 days." in result.output
    # No --symbol -> the un-filtered query path; one fetch call.
    assert conn.fetch.await_count == 1


def test_journal_list_with_symbol_filters_and_renders_rows() -> None:
    conn = _make_conn()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "id": 3,
                "symbol": "CBA.AU",
                "decision_date": date(2026, 6, 20),
                "action": "BUY",
                "rationale": "yield",
                "signal_ref": "model_a@v1_5@2026-06-19",
                "tax_note": "",
                "created_at": date(2026, 6, 20),
            },
            {
                "id": 4,
                "symbol": "CBA.AU",
                "decision_date": date(2026, 6, 21),
                "action": "HOLD",
                "rationale": None,
                "signal_ref": None,
                "tax_note": "",
                "created_at": date(2026, 6, 21),
            },
        ]
    )

    result = _invoke(["list", "--symbol", "CBA.AU"], conn)

    assert result.exit_code == 0, result.output
    assert "CBA.AU" in result.output
    assert "BUY" in result.output
    # The symbol filter is passed as the second query param.
    fetch_args = conn.fetch.await_args.args
    assert fetch_args[2] == "CBA.AU"


# ---------------------------------------------------------------------------
# journal review
# ---------------------------------------------------------------------------


def test_journal_review_empty_renders_green_message() -> None:
    conn = _make_conn()
    conn.fetch = AsyncMock(return_value=[])

    result = _invoke(["review", "--stale-days", "90"], conn)

    assert result.exit_code == 0, result.output
    assert "No actionable decisions older than 90 days." in result.output


def test_journal_review_lists_stale_decisions() -> None:
    conn = _make_conn()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "id": 11,
                "symbol": None,
                "decision_date": date(2026, 1, 5),
                "action": "REVIEW",
                "rationale": "check thesis",
                "signal_ref": None,
            },
        ]
    )

    result = _invoke(["review"], conn)

    assert result.exit_code == 0, result.output
    assert "REVIEW" in result.output
    assert "portfolio" in result.output  # symbol None -> 'portfolio'
    assert "check thesis" in result.output
