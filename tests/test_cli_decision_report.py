"""CLI tests for `asx decision report` — the broker report's only entry point.

The renderer landed in #226 with no caller outside its own tests. This file
pins the wiring: the command reads a PERSISTED case (never a rebuilt one),
writes the Markdown artifact, and refuses to run outside the personal-use
firewall.

Pool functions are patched at the `asxos.cli.decision` module level, following
the fixture pattern in `tests/test_cli_macro_thesis.py`.
"""
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from asxos.cli import decision as decision_mod
from asxos.domain.decision_engine.demo import build_demo_brief

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
        patch.object(decision_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(decision_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(decision_mod, "acquire") as acquire_patch,
    ):
        acquire_patch.side_effect = lambda: _acquire_ctx(conn)
        yield conn


def test_report_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    result = runner.invoke(
        decision_mod.decision_app,
        ["report", "--packet-id", "dpk-x-1", "--out", str(tmp_path / "r.md")],
    )
    assert result.exit_code != 0
    assert not (tmp_path / "r.md").exists()


def test_report_writes_the_markdown_artifact_from_the_persisted_case(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "reports" / "case.md"

    with patch.object(
        decision_mod.repository, "load_case", new=AsyncMock(return_value=case)
    ) as load_case:
        result = runner.invoke(
            decision_mod.decision_app,
            [
                "report",
                "--packet-id",
                case.decision.decision_packet_id,
                "--out",
                str(out),
            ],
        )

    assert result.exit_code == 0, result.output
    load_case.assert_awaited_once()
    assert load_case.await_args.args[0] == case.decision.decision_packet_id

    written = out.read_text(encoding="utf-8")
    assert written.startswith("# Broker research report: ")
    assert case.decision.decision_packet_id in written
    assert case.decision.content_hash in written
    assert "not licensed financial advice" in written


def test_report_creates_the_parent_directory(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "does" / "not" / "exist" / "case.md"

    with patch.object(
        decision_mod.repository, "load_case", new=AsyncMock(return_value=case)
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            ["report", "--packet-id", "p", "--out", str(out)],
        )

    assert result.exit_code == 0, result.output
    assert out.is_file()


def test_report_surfaces_a_missing_packet_rather_than_writing_an_empty_file(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    out = tmp_path / "case.md"

    with patch.object(
        decision_mod.repository,
        "load_case",
        new=AsyncMock(
            side_effect=decision_mod.repository.DecisionPacketNotFoundError("no row")
        ),
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            ["report", "--packet-id", "missing", "--out", str(out)],
        )

    assert result.exit_code != 0
    assert not out.exists()


# ---------------------------------------------------------------------------
# Delivery receipt
# ---------------------------------------------------------------------------

def test_report_dry_run_writes_no_receipt(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]

    with (
        patch.object(decision_mod.repository, "load_case", new=AsyncMock(return_value=case)),
        patch.object(decision_mod, "persist_receipt", new=AsyncMock()) as persist,
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            ["report", "--packet-id", "p", "--out", str(tmp_path / "r.md")],
        )

    assert result.exit_code == 0, result.output
    persist.assert_not_awaited()


def test_report_persist_records_a_receipt_over_the_exact_artifact_bytes(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "r.md"

    with (
        patch.object(decision_mod.repository, "load_case", new=AsyncMock(return_value=case)),
        patch.object(decision_mod, "persist_receipt", new=AsyncMock()) as persist,
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            ["report", "--packet-id", "p", "--out", str(out), "--persist"],
        )

    assert result.exit_code == 0, result.output
    persist.assert_awaited_once()
    _conn, receipt, html = persist.await_args.args

    written = out.read_text(encoding="utf-8")
    # The receipt must attest to the bytes that actually reached the artifact,
    # not to a second render.
    assert html == written
    assert receipt.render_sha256 == hashlib.sha256(written.encode("utf-8")).hexdigest()
    assert receipt.render_bytes == len(written.encode("utf-8"))
    assert receipt.decision_packet_id == case.decision.decision_packet_id
    assert receipt.decision_content_hash == case.decision.content_hash
    assert receipt.channel == "cli"
