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


def _only_artifact(root: Path) -> Path:
    """The single Markdown artifact written under a content-addressed store."""
    found = sorted(root.rglob("*.md"))
    assert len(found) == 1, f"expected exactly one artifact, got {found}"
    return found[0]


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
        ["report", "--packet-id", "dpk-x-1", "--out", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert list(tmp_path.rglob("*.md")) == []


def test_report_writes_the_markdown_artifact_from_the_persisted_case(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "reports"

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

    written = _only_artifact(out).read_text(encoding="utf-8")
    assert written.startswith("# Broker research report: ")
    assert case.decision.decision_packet_id in written
    assert case.decision.content_hash in written
    assert "not licensed financial advice" in written


def test_report_creates_the_parent_directory(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "does" / "not" / "exist"

    with patch.object(
        decision_mod.repository, "load_case", new=AsyncMock(return_value=case)
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            ["report", "--packet-id", "p", "--out", str(out)],
        )

    assert result.exit_code == 0, result.output
    assert _only_artifact(out).is_file()


def test_report_surfaces_a_missing_packet_rather_than_writing_an_empty_file(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    out = tmp_path

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
    assert list(out.rglob("*.md")) == []


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
            ["report", "--packet-id", "p", "--out", str(tmp_path)],
        )

    assert result.exit_code == 0, result.output
    persist.assert_not_awaited()


def test_report_persist_records_a_receipt_over_the_exact_artifact_bytes(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "store"

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

    written = _only_artifact(out).read_text(encoding="utf-8")
    # The receipt must attest to the bytes that actually reached the artifact,
    # not to a second render.
    assert html == written
    assert receipt.render_sha256 == hashlib.sha256(written.encode("utf-8")).hexdigest()
    assert receipt.render_bytes == len(written.encode("utf-8"))
    assert receipt.decision_packet_id == case.decision.decision_packet_id
    assert receipt.decision_content_hash == case.decision.content_hash
    assert receipt.channel == "cli"


# ---------------------------------------------------------------------------
# Content addressing
# ---------------------------------------------------------------------------

def test_artifact_is_named_by_its_digest_under_the_packet_id(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    out = tmp_path / "store"

    with (
        patch.object(decision_mod.repository, "load_case", new=AsyncMock(return_value=case)),
        patch.object(decision_mod, "persist_receipt", new=AsyncMock()) as persist,
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            ["report", "--packet-id", "p", "--out", str(out), "--persist"],
        )

    assert result.exit_code == 0, result.output
    artifact = _only_artifact(out)
    _conn, receipt, _html = persist.await_args.args

    assert artifact.parent.name == case.decision.decision_packet_id
    assert artifact.name == f"{receipt.render_sha256}.md"
    # The name is derivable from the bytes alone.
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert artifact.stem == digest


def test_artifact_path_is_a_pure_function_of_packet_and_digest(tmp_path: Path) -> None:
    digest = "a" * 64
    first = decision_mod._artifact_path(tmp_path, "dpk-1", digest)
    second = decision_mod._artifact_path(tmp_path, "dpk-1", digest)
    assert first == second

    # Bytes that differ by one character cannot land on the same path.
    other = decision_mod._artifact_path(tmp_path, "dpk-1", "b" + "a" * 63)
    assert other != first


# ---------------------------------------------------------------------------
# Deterministic re-render
# ---------------------------------------------------------------------------

def _render_once(case: Any, out: Path, evaluated_at: str) -> Path:
    with (
        patch.object(decision_mod.repository, "load_case", new=AsyncMock(return_value=case)),
        patch.object(decision_mod, "persist_receipt", new=AsyncMock()),
    ):
        result = runner.invoke(
            decision_mod.decision_app,
            [
                "report",
                "--packet-id",
                "p",
                "--out",
                str(out),
                "--evaluated-at",
                evaluated_at,
            ],
        )
    assert result.exit_code == 0, result.output
    return _only_artifact(out)


def test_same_packet_and_instant_render_byte_identical_artifacts(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    instant = case.decision.knowledge_cutoff.isoformat()

    first = _render_once(case, tmp_path / "a", instant).read_bytes()
    second = _render_once(case, tmp_path / "b", instant).read_bytes()

    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_repeat_render_into_one_store_stays_a_single_artifact(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]
    instant = case.decision.knowledge_cutoff.isoformat()
    store = tmp_path / "store"

    _render_once(case, store, instant)
    _render_once(case, store, instant)

    # Content addressing means the second render reoccupies the same path.
    assert len(list(store.rglob("*.md"))) == 1


def test_evaluated_at_must_be_explicit_utc(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    case = build_demo_brief().cases[1]

    for bad in ("2026-09-07T00:00:00", "2026-09-07T00:00:00+10:00"):
        with patch.object(
            decision_mod.repository, "load_case", new=AsyncMock(return_value=case)
        ):
            result = runner.invoke(
                decision_mod.decision_app,
                ["report", "--packet-id", "p", "--out", str(tmp_path), "--evaluated-at", bad],
            )
        assert result.exit_code != 0, bad
    assert list(tmp_path.rglob("*.md")) == []
