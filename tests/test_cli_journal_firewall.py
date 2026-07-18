"""Firewall-gate regression: journal CLI commands require ASXOS_PERSONAL_USE=1.

Closes an R14-class hole surfaced by the 2026-07-18 security audit: the
decisions journal (``asx journal add/list/review``) reads and writes
BUY/SELL/HOLD/REVIEW/NOTE decisions with free-text rationale and tax_note --
personal investment-decision data under s766B that must not surface outside the
single-user context. Enforces the firewall convention that every CLI entry
point touching portfolio data MUST call _require_personal_use(), documented in
.claude/rules/portfolio-conventions.md ("Regulatory firewall (Part 0 Q1)").

Imports asxos.cli.journal directly (not asxos.cli.main) to avoid the joblib
import chain that collection-errors the other test_cli_* files in the sandbox.
"""
import pytest
import typer

from asxos.cli.journal import journal_add, journal_list, journal_review


def test_journal_add_requires_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter, match="ASXOS_PERSONAL_USE"):
        journal_add()


def test_journal_list_requires_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter, match="ASXOS_PERSONAL_USE"):
        journal_list()


def test_journal_review_requires_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter, match="ASXOS_PERSONAL_USE"):
        journal_review()


def test_journal_add_gate_fires_before_arg_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    # The firewall must be the first thing checked: an invalid action with the
    # flag unset should surface the firewall error, not an action BadParameter.
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter, match="ASXOS_PERSONAL_USE"):
        journal_add(symbol="BHP.AU", action="bogus", rationale="x")
