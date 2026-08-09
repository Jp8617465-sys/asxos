"""CLI tests for `asx thesis` — firewall gate + not-found + empty rendering.

Exercises the Typer wiring in ``asxos/cli/thesis.py`` without a real Postgres
connection. We patch the module-level pool functions (``init_pool`` /
``close_pool`` / ``acquire``) and the ``svc`` service object so the test drives
the command branches deterministically.

Covered:
  - ``_require_personal_use`` firewall: with ASXOS_PERSONAL_USE unset, a gated
    command exits non-zero before touching the DB.
  - ``thesis show`` for a symbol with no thesis → typer.Exit(1).
  - ``thesis list`` with an empty result set → friendly "No theses found."

Note: ``asxos.cli.thesis`` itself pulls only typer/rich/Decimal, but this file
imports ``from asxos.cli import main as cli_main`` for ``runner.invoke()``,
and ``cli/main.py`` wires in ``cli/predict.py`` -> ``domain/models/model_a.py``
-> ``domain/models/cache.py`` -> ``joblib``. This file is therefore in the
same joblib-collection-error sandbox gap as the four files CLAUDE.md
documents explicitly (test_cli_predict.py, test_generate_signals_job.py,
test_model_a_predict.py, test_model_cache.py) — it passes on Render where
``pip install -e ".[ml]"`` is run, same as those four.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import thesis as thesis_mod
from asxos.domain.theses.schemas import ReportSection
from asxos.domain.theses.types import Thesis

runner = CliRunner()


def _thesis(report_sections: tuple[ReportSection, ...] = ()) -> Thesis:
    """Minimal, fully-real Thesis for render tests — every other field is a
    plain placeholder; only report_sections varies per test."""
    now = datetime(2026, 7, 13, tzinfo=UTC)
    return Thesis(
        thesis_id=1, symbol="CBA.AU", status="watching",
        thesis_text="Rate cycle play — NIM expansion when RBA cuts",
        entry_band_lower=None, entry_band_upper=None,
        stop_price=None, target_price=None, timeline_days=None,
        themes=(),
        actual_entry_price=None, actual_entry_at=None,
        actual_exit_price=None, actual_exit_at=None,
        last_revisited_at=now, revisit_due_at=now, opened_at=now, closed_at=None,
        report_sections=report_sections,
    )


def _make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


@asynccontextmanager
async def _acquire_ctx(conn: MagicMock) -> Any:
    yield conn


@pytest.fixture
def patched_pool() -> Any:
    """Patch pool + acquire on the thesis CLI module; yield the mock conn."""
    conn = _make_conn()
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(thesis_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        acquire_patch.side_effect = lambda: _acquire_ctx(conn)
        yield conn


# ---------------------------------------------------------------------------
# Firewall gate
# ---------------------------------------------------------------------------

def test_show_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    # Guard: the firewall must trip before any DB call. If init_pool ran the
    # AsyncMock would record a call; we assert it never does.
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_list_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    result = runner.invoke(cli_main.app, ["thesis", "list"])
    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output


# ---------------------------------------------------------------------------
# show — not found
# ---------------------------------------------------------------------------

def test_show_not_found_exits_1(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol", new=AsyncMock(return_value=None)
    ) as get_patch:
        result = runner.invoke(cli_main.app, ["thesis", "show", "ZZZ.AU"])

    assert result.exit_code == 1
    assert "No thesis found for ZZZ.AU" in result.output
    get_patch.assert_awaited_once()


# ---------------------------------------------------------------------------
# list — empty rendering
# ---------------------------------------------------------------------------

def test_list_empty_renders_friendly_message(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "list_theses", new=AsyncMock(return_value=[])
    ) as list_patch:
        result = runner.invoke(cli_main.app, ["thesis", "list"])

    assert result.exit_code == 0, result.output
    assert "No theses found." in result.output
    # No status filter was passed → status kwarg is None.
    list_patch.assert_awaited_once()
    assert list_patch.await_args.kwargs == {"status": None}


def test_list_with_status_filter_passes_through(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "list_theses", new=AsyncMock(return_value=[])
    ) as list_patch:
        result = runner.invoke(
            cli_main.app, ["thesis", "list", "--status", "active"]
        )

    assert result.exit_code == 0, result.output
    list_patch.assert_awaited_once()
    assert list_patch.await_args.kwargs == {"status": "active"}


# ---------------------------------------------------------------------------
# approve / reject — firewall gate
# ---------------------------------------------------------------------------

def test_approve_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(cli_main.app, ["thesis", "approve", "1", "--reason", "test"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_reject_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(cli_main.app, ["thesis", "reject", "1", "--reason", "test"])

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


# ---------------------------------------------------------------------------
# approve — service wiring
# ---------------------------------------------------------------------------

def test_approve_invokes_service_with_correct_args(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake_thesis = MagicMock(thesis_id=42, symbol="CBA.AU", governance_status="approved")
    with (
        patch.object(
            thesis_mod.svc, "approve_object", new=AsyncMock(return_value=fake_thesis)
        ) as approve_patch,
        # _approve_thesis() also calls _print_thesis_detail(t), which does
        # arithmetic on several Thesis attributes (e.g. timedelta(days=
        # t.timeline_days)) — a bare MagicMock auto-generates a truthy mock
        # for any unset attribute, which crashes that arithmetic. No-op it;
        # this test only cares about the approve_object() call, not rendering.
        patch.object(thesis_mod, "_print_thesis_detail"),
    ):
        result = runner.invoke(
            cli_main.app,
            ["thesis", "approve", "42", "--reason", "Evidence checks out"],
        )

    assert result.exit_code == 0, result.output
    approve_patch.assert_awaited_once()
    call_args = approve_patch.await_args
    assert call_args.args[1] == 42  # thesis_id positional
    assert call_args.kwargs["reasoning"] == "Evidence checks out"


def test_approve_missing_reason_exits_nonzero() -> None:
    result = runner.invoke(cli_main.app, ["thesis", "approve", "42"])
    assert result.exit_code != 0


def test_approve_passes_accept_stale_evidence_when_given(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake_thesis = MagicMock(thesis_id=42, symbol="CBA.AU", governance_status="approved")
    with (
        patch.object(
            thesis_mod.svc, "approve_object", new=AsyncMock(return_value=fake_thesis)
        ) as approve_patch,
        patch.object(thesis_mod, "_print_thesis_detail"),  # see comment above
    ):
        result = runner.invoke(
            cli_main.app,
            [
                "thesis", "approve", "42", "--reason", "test",
                "--accept-stale-evidence", "Still valid despite age",
            ],
        )

    assert result.exit_code == 0, result.output
    call_kwargs = approve_patch.await_args.kwargs
    assert call_kwargs["accept_stale_evidence"] == "Still valid despite age"


# ---------------------------------------------------------------------------
# reject — service wiring
# ---------------------------------------------------------------------------

def test_reject_invokes_service_with_correct_args(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake_thesis = MagicMock(thesis_id=42, symbol="CBA.AU", governance_status="rejected")
    with patch.object(
        thesis_mod.svc, "reject_object", new=AsyncMock(return_value=fake_thesis)
    ) as reject_patch:
        result = runner.invoke(
            cli_main.app,
            ["thesis", "reject", "42", "--reason", "Catalyst didn't materialise"],
        )

    assert result.exit_code == 0, result.output
    reject_patch.assert_awaited_once()
    call_args = reject_patch.await_args
    assert call_args.args[1] == 42
    assert call_args.kwargs["reasoning"] == "Catalyst didn't materialise"


def test_reject_missing_reason_exits_nonzero() -> None:
    result = runner.invoke(cli_main.app, ["thesis", "reject", "42"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# open --from-agent-run — routing
# ---------------------------------------------------------------------------

def test_open_from_agent_run_invokes_correct_service_function(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake_thesis = MagicMock(thesis_id=99, symbol="CBA.AU", governance_status="draft")
    with (
        patch.object(
            thesis_mod.svc, "create_thesis_from_agent_run",
            new=AsyncMock(return_value=fake_thesis),
        ) as agent_run_patch,
        patch.object(
            thesis_mod.svc, "open_thesis", new=AsyncMock()
        ) as normal_open_patch,
        patch.object(thesis_mod, "_print_thesis_detail"),  # see comment above
    ):
        result = runner.invoke(
            cli_main.app,
            ["thesis", "open", "CBA.AU", "--from-agent-run", "7"],
        )

    assert result.exit_code == 0, result.output
    agent_run_patch.assert_awaited_once()
    normal_open_patch.assert_not_awaited()


def test_open_without_from_agent_run_uses_normal_path(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake_thesis = MagicMock(thesis_id=1, symbol="CBA.AU", governance_status="approved")
    with (
        patch.object(
            thesis_mod.svc, "open_thesis", new=AsyncMock(return_value=fake_thesis)
        ) as normal_open_patch,
        patch.object(
            thesis_mod.svc, "create_thesis_from_agent_run", new=AsyncMock()
        ) as agent_run_patch,
        patch.object(thesis_mod, "_print_thesis_detail"),  # see comment above
        # _print_ladder_lint (0042) compares ladder Decimals — same
        # MagicMock-arithmetic hazard as _print_thesis_detail; no-op it too.
        patch.object(thesis_mod, "_print_ladder_lint"),
    ):
        result = runner.invoke(cli_main.app, ["thesis", "open", "CBA.AU"])

    assert result.exit_code == 0, result.output
    normal_open_patch.assert_awaited_once()
    agent_run_patch.assert_not_awaited()


# ---------------------------------------------------------------------------
# add-section — Phase C broker-report thesis (migration 0040)
# ---------------------------------------------------------------------------

def test_add_section_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(
            cli_main.app,
            ["thesis", "add-section", "CBA.AU", "--kind", "moat", "--body", "Text."],
        )

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_add_section_invalid_kind_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch:
        result = runner.invoke(
            cli_main.app,
            ["thesis", "add-section", "CBA.AU", "--kind", "not_a_real_kind", "--body", "Text."],
        )

    assert result.exit_code != 0
    init_patch.assert_not_awaited()  # BadParameter fires before touching the DB


def test_add_section_requires_exactly_one_of_body_or_body_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch:
        result = runner.invoke(
            cli_main.app, ["thesis", "add-section", "CBA.AU", "--kind", "moat"],
        )

    assert result.exit_code != 0
    assert "exactly one" in result.output
    init_patch.assert_not_awaited()


# ---------------------------------------------------------------------------
# attest / condition — 0042 wiring
# ---------------------------------------------------------------------------

def test_attest_without_personal_use_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with (
        patch.object(thesis_mod, "init_pool", new=AsyncMock()) as init_patch,
        patch.object(thesis_mod, "acquire") as acquire_patch,
    ):
        result = runner.invoke(
            cli_main.app, ["thesis", "attest", "1", "--basis", "Q3 numbers hold"]
        )

    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE=1" in result.output
    init_patch.assert_not_awaited()
    acquire_patch.assert_not_called()


def test_attest_invokes_service_with_basis(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake = MagicMock(thesis_id=1, symbol="CBA.AU", attestation="underwritten")
    with (
        patch.object(
            thesis_mod.svc, "attest_thesis", new=AsyncMock(return_value=fake)
        ) as attest_patch,
        patch.object(thesis_mod, "_print_thesis_detail"),
    ):
        result = runner.invoke(
            cli_main.app, ["thesis", "attest", "1", "--basis", "Q3 numbers hold"]
        )

    assert result.exit_code == 0, result.output
    kwargs = attest_patch.await_args.kwargs
    assert kwargs["to"] == "underwritten"
    assert kwargs["basis"] == "Q3 numbers hold"


def test_attest_demotion_requires_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    result = runner.invoke(
        cli_main.app, ["thesis", "attest", "1", "--to", "placeholder"]
    )
    assert result.exit_code != 0


def test_parse_condition_option_defaults_alert_review() -> None:
    out = thesis_mod._parse_condition_option("Price falls below $150")
    assert out == {"text": "Price falls below $150", "trigger_semantics": "alert_review"}


def test_parse_condition_option_hard_exit_prefix() -> None:
    out = thesis_mod._parse_condition_option("hard_exit::Price falls below $150")
    assert out == {"text": "Price falls below $150", "trigger_semantics": "hard_exit"}


def test_parse_condition_option_bad_prefix_rejected() -> None:
    with pytest.raises(typer.BadParameter):
        thesis_mod._parse_condition_option("soft_exit::Price falls below $150")


def test_condition_add_invokes_service(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    fake_cond = MagicMock(
        thesis_id=1, ordinal=1, trigger_semantics="hard_exit",
        enforcement_note="will enforce: close < 150.000000.",
    )
    with (
        patch.object(
            thesis_mod.svc, "get_thesis_by_symbol",
            new=AsyncMock(return_value=_thesis()),
        ),
        patch.object(
            thesis_mod.conditions_svc, "add_condition",
            new=AsyncMock(return_value=fake_cond),
        ) as add_patch,
    ):
        result = runner.invoke(
            cli_main.app,
            ["thesis", "condition", "add", "CBA.AU",
             "--text", "Price falls below $150",
             "--semantics", "hard_exit", "--reason", "stop discipline"],
        )

    assert result.exit_code == 0, result.output
    kwargs = add_patch.await_args.kwargs
    assert kwargs["trigger_semantics"] == "hard_exit"
    assert kwargs["text"] == "Price falls below $150"
    # The parser echo is printed — the narrowing/enforcement is never silent.
    assert "will enforce" in result.output


# ---------------------------------------------------------------------------
# _parse_figure — pure function
# ---------------------------------------------------------------------------

def test_parse_figure_valid() -> None:
    fig = thesis_mod._parse_figure("Fair value=130.50")
    assert fig.label == "Fair value"
    assert fig.value == Decimal("130.50")
    assert fig.provenance == "james_input"


def test_parse_figure_missing_equals() -> None:
    with pytest.raises(typer.BadParameter):
        thesis_mod._parse_figure("no equals sign here")


def test_parse_figure_bad_decimal() -> None:
    with pytest.raises(typer.BadParameter):
        thesis_mod._parse_figure("Label=not_a_number")


def test_parse_figure_empty_label() -> None:
    with pytest.raises(typer.BadParameter):
        thesis_mod._parse_figure("=130.50")


# ---------------------------------------------------------------------------
# show --full-report — section rendering
# ---------------------------------------------------------------------------

def test_show_full_report_renders_sections_in_fixed_kind_order(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    # Deliberately out of REPORT_SECTION_KINDS order: valuation before moat.
    sections = (
        ReportSection(kind="valuation", body="Valuation text."),
        ReportSection(kind="moat", body="Moat text."),
    )
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol",
        new=AsyncMock(return_value=_thesis(report_sections=sections)),
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU", "--full-report"])

    assert result.exit_code == 0, result.output
    assert result.output.index("Moat") < result.output.index("Valuation")


def test_show_full_report_skips_absent_kinds(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    sections = (ReportSection(kind="moat", body="Moat text."),)
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol",
        new=AsyncMock(return_value=_thesis(report_sections=sections)),
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU", "--full-report"])

    assert result.exit_code == 0, result.output
    assert "Moat" in result.output
    for title in ("Business", "Valuation", "Risks / Bear Case"):
        assert title not in result.output


def test_show_without_full_report_flag_unchanged_for_empty_sections(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    """Backward compatibility: a thesis with no sections renders byte-
    identical to pre-Phase-C output — no hint, no section block."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol",
        new=AsyncMock(return_value=_thesis(report_sections=())),
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU"])

    assert result.exit_code == 0, result.output
    assert "Full report" not in result.output


def test_show_hint_appears_when_sections_present_but_flag_omitted(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    sections = (ReportSection(kind="moat", body="Moat text."),)
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol",
        new=AsyncMock(return_value=_thesis(report_sections=sections)),
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU"])

    assert result.exit_code == 0, result.output
    assert "Full report:" in result.output  # the hint
    assert "Moat text." not in result.output  # section body itself not rendered without the flag


def test_show_full_report_with_no_sections_shows_hint(
    monkeypatch: pytest.MonkeyPatch, patched_pool: MagicMock
) -> None:
    """--full-report on a thesis with zero sections shows the
    add-section-to-get-started hint, not an empty/blank render."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    with patch.object(
        thesis_mod.svc, "get_thesis_by_symbol",
        new=AsyncMock(return_value=_thesis(report_sections=())),
    ):
        result = runner.invoke(cli_main.app, ["thesis", "show", "CBA.AU", "--full-report"])

    assert result.exit_code == 0, result.output
    assert "No report sections yet" in result.output
    assert "add-section" in result.output
