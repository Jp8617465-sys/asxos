"""Empty ``financial_goals`` must leave packets abstaining exactly as they do now.

James, 2026-09-21: after 0062 is applied, the mandate derives from nothing
until he enters goals. Do not seed, default, or infer any goal value. A
mandate derived from placeholder numbers is worse than no mandate, because
the sizer would act on it.

This PR stores the layer and does not wire it into the packet builder
(that is M-e, later). The contract this file pins is: an empty goals table
cannot invent a mandate, and the builder still passes ``calibration=None``,
so every reachable recommendation state stays a non-action state.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from click import unstyle
from pydantic import ValidationError
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.domain.decision_engine.builder import derive_state
from asxos.domain.decision_engine.types import ACTION_STATES, NON_ACTION_STATES
from asxos.domain.mandate import Goals
from asxos.domain.mandate import repository as repo

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = _ROOT / "migrations" / "0062_mandate.sql"
_BUILDER = _ROOT / "asxos" / "domain" / "decision_engine" / "builder.py"
_PACKET_JOB = _ROOT / "jobs" / "build_decision_packets.py"
_MANDATE_DIR = _ROOT / "asxos" / "domain" / "mandate"
_RUNNER = CliRunner()
_SCALAR_GOAL_VALUES = {
    "as-of": "2026-09-22",
    "investable": "25000",
    "income": "100000",
    "savings": "20000",
    "target-wealth": "1000000",
    "horizon-years": "15",
    "drawdown-tolerance": "20",
    "emergency-months": "3",
    "account": "individual",
    "marginal-rate": "37",
    "brokerage": "5",
}


def _mandate_init_args(
    *,
    missing: str | None = None,
    declare_no_liquidity_needs: bool = True,
) -> list[str]:
    args = ["mandate", "init"]
    for option, value in _SCALAR_GOAL_VALUES.items():
        if option != missing:
            args.extend((f"--{option}", value))
    if declare_no_liquidity_needs:
        args.append("--no-liquidity-needs")
    return args


def test_0062_does_not_seed_or_default_any_goal_or_mandate_row() -> None:
    """The migration creates empty tables. An INSERT here would be a placeholder mandate."""
    sql = _MIGRATION.read_text()
    assert "CREATE TABLE financial_goals" in sql
    assert "CREATE TABLE mandates" in sql
    # Column DEFAULTs on append-only metadata (stated_by, created_at, empty
    # liquidity_needs JSON) are not a goals statement. A row INSERT is.
    for table in ("financial_goals", "mandates"):
        assert f"INSERT INTO {table}" not in sql
        assert f"INSERT INTO {table.upper()}" not in sql
    assert "COPY financial_goals" not in sql
    assert "COPY mandates" not in sql


def test_goals_cannot_be_constructed_from_nothing() -> None:
    """derive() has no zero-arg path. Missing any required field is a hard fail."""
    with pytest.raises(ValidationError):
        Goals()  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "missing",
    _SCALAR_GOAL_VALUES,
)
def test_mandate_init_requires_every_scalar_goal_value(missing: str) -> None:
    """The CLI cannot silently fill a goal value James did not state."""
    result = _RUNNER.invoke(cli_main.app, _mandate_init_args(missing=missing), env={"ASXOS_PERSONAL_USE": "1"})

    assert result.exit_code == 2
    assert f"--{missing}" in unstyle(result.output)


def test_mandate_init_requires_an_explicit_liquidity_statement() -> None:
    result = _RUNNER.invoke(
        cli_main.app,
        _mandate_init_args(declare_no_liquidity_needs=False),
        env={"ASXOS_PERSONAL_USE": "1"},
    )

    assert result.exit_code == 2
    assert "--no-liquidity-needs" in unstyle(result.output)


def test_mandate_init_accepts_explicit_no_liquidity_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[Goals] = []

    async def record(goals: Goals) -> None:
        recorded.append(goals)

    monkeypatch.setattr("asxos.cli.mandate._run_init", record)

    result = _RUNNER.invoke(cli_main.app, _mandate_init_args(), env={"ASXOS_PERSONAL_USE": "1"})

    assert result.exit_code == 0
    assert len(recorded) == 1
    assert recorded[0].liquidity_needs == ()


def test_domain_mandate_has_no_placeholder_goals_factory() -> None:
    """A helper that invents A$25k / 25 % drawdown would be the failure mode James named."""
    for path in _MANDATE_DIR.glob("*.py"):
        src = path.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                name = node.name.lower()
                assert "placeholder" not in name
                assert "default_goals" not in name
                assert not name.startswith("seed")
        if path.name == "derive.py":
            # derive() reads Goals; it must not construct one.
            assert "Goals(" not in src
        lower = src.lower()
        for token in ("placeholder", "default_goals", "example_goals"):
            assert token not in lower, f"{path.name} names a {token}"


class _EmptyConn:
    """A store with no financial_goals and no mandates rows."""

    async def execute(self, query: str, *args: object) -> str:
        raise AssertionError(f"empty store must not write: {query!r}")

    async def fetchrow(self, query: str, *args: object) -> None:
        return None

    async def fetch(self, query: str, *args: object) -> list[object]:
        return []

    async def fetchval(self, query: str, *args: object) -> None:
        return None


async def test_latest_approved_mandate_is_none_when_the_table_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    assert await repo.latest_approved_mandate(_EmptyConn()) is None


def test_packet_builder_does_not_import_mandate_and_still_passes_calibration_none() -> None:
    """M-e has not landed. Wiring derive() here with an inferred Goals is the bug."""
    for path in (_BUILDER, _PACKET_JOB):
        tree = ast.parse(path.read_text())
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any("mandate" in name for name in imported), (path.name, imported)

    builder_src = _BUILDER.read_text()
    assert "calibration=None" in builder_src
    # Mutation: a call that passed latest_approved_mandate() into derive_state
    # would drop this literal and unstick packets on an empty table.
    assert "latest_approved_mandate" not in builder_src
    assert "sizing_policy_from" not in builder_src


def test_empty_goals_leave_every_reachable_packet_state_non_action() -> None:
    """The same matrix as today: no calibration, so no action state.

    ``watch`` when the challenge passed and ``abstain`` when it did not —
    both NON_ACTION_STATES, both size zero. That is what 'packets still
    abstain' means in this codebase (C-13 / P5-01 / H-32).
    """
    for challenge_outcome in ("pass", "revise", "abstain"):
        for tax_readiness in ("pass", "fail", "unknown"):
            result = derive_state(
                challenge_outcome=challenge_outcome,  # type: ignore[arg-type]
                tax_readiness=tax_readiness,  # type: ignore[arg-type]
                calibration=None,
            )
            assert result in NON_ACTION_STATES
            assert result not in ACTION_STATES
    assert derive_state(challenge_outcome="pass", tax_readiness="pass", calibration=None) == "watch"
    assert derive_state(challenge_outcome="abstain", tax_readiness="pass", calibration=None) == "abstain"
