"""Firewall-gate regression: tax CLI commands require ASXOS_PERSONAL_USE=1.

Closes the ungated tax-lot surface a staged order draws from (an R14-class
hole): tax-view / tax-action render per-lot CGT eligibility, cost bases, and
Div 296 tiers -- personal-advice outputs under s766B that must not surface
outside the single-user context. Enforces the firewall convention that
every CLI entry point MUST call _require_personal_use(), documented in
.claude/rules/portfolio-conventions.md ("Regulatory firewall (Part 0 Q1)").

Imports asxos.cli.tax directly (not asxos.cli.main) to avoid the joblib import
chain that collection-errors the other test_cli_* files in the sandbox.
"""
import pytest
import typer

from asxos.cli.tax import tax_action, tax_view


def test_tax_view_requires_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter, match="ASXOS_PERSONAL_USE"):
        tax_view()


def test_tax_action_requires_personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter):
        tax_action()


def test_tax_view_gate_fires_before_arg_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    # The firewall must be the first thing checked: an invalid account with the
    # flag unset should surface the firewall error, not an account BadParameter.
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(typer.BadParameter, match="ASXOS_PERSONAL_USE"):
        tax_view(account_type="bogus")
