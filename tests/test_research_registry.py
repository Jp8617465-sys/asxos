"""Stage 2 research registry — campaign node H3-A.

Exit-gate tests: (1) one hypothesis reproduced from raw prices through
evaluation with an identical hash on two runs; (2) failed variants are stored
and listed, never dropped; (3) no research can self-promote into capital —
by type, by transition table, and by grep over the package.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from asxos.domain.research.registry import (
    PROMOTION_STATES,
    ResearchHypothesis,
    ResearchRun,
    StrategyVersion,
    advance,
    evaluate_momentum_12_1,
)
from asxos.domain.research.registry.harness import HarnessError, panel_hash
from asxos.domain.research.registry.loader import SQL_PANEL, assert_panel_sql_admissible
from asxos.domain.research.registry.promotion import PromotionError
from asxos.domain.research.registry.repository import (
    list_runs,
    record_promotion,
    save_hypothesis,
    save_run,
    save_strategy_version,
)

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


# --- synthetic panel: deterministic, no randomness ------------------------------------


def _sessions(n: int, start: date = date(2025, 1, 2)) -> list[date]:
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _panel(n_symbols: int = 30, n_sessions: int = 320) -> dict[str, list[tuple[date, Decimal]]]:
    """Symbol k drifts at (k - n/2) bp per session, so momentum ranks are well defined."""
    cal = _sessions(n_sessions)
    panel: dict[str, list[tuple[date, Decimal]]] = {}
    for k in range(n_symbols):
        drift = Decimal(k - n_symbols // 2) / Decimal(10000)
        px = Decimal("10")
        series: list[tuple[date, Decimal]] = []
        for d in cal:
            series.append((d, px.quantize(Decimal("0.000001"))))
            px = px * (Decimal(1) + drift)
        panel[f"S{k:02d}.AU"] = series
    return panel


# --- (1) reproducibility --------------------------------------------------------------


def test_two_evaluations_of_the_same_panel_hash_identically() -> None:
    panel = _panel()
    a = evaluate_momentum_12_1(panel)
    b = evaluate_momentum_12_1(panel)
    assert a.hash == b.hash and len(a.hash) == 64
    assert a.payload["n_evaluated"] >= 1


def test_evaluation_is_json_native_and_decimal_strings() -> None:
    result = evaluate_momentum_12_1(_panel())
    text = json.dumps(result.payload)
    assert "." in str(result.payload["mean_net_return_per_period"])
    assert "float" not in text
    period = next(p for p in result.payload["periods"] if p["status"] == "evaluated")  # type: ignore[index]
    assert isinstance(period["net_return"], str)


def test_ranking_picks_the_highest_drift_symbols() -> None:
    result = evaluate_momentum_12_1(_panel(n_symbols=30))
    period = next(p for p in result.payload["periods"] if p["status"] == "evaluated")  # type: ignore[index]
    assert period["top"][0] == "S29.AU"


def test_costs_reduce_net_below_gross_on_the_first_rebalance() -> None:
    result = evaluate_momentum_12_1(_panel(), cost_bps_per_side=Decimal("25"))
    period = next(p for p in result.payload["periods"] if p["status"] == "evaluated")  # type: ignore[index]
    assert Decimal(period["net_return"]) < Decimal(period["gross_return"])  # type: ignore[arg-type]
    assert Decimal(period["turnover_one_way"]) > 0  # type: ignore[arg-type]


def test_panel_hash_changes_when_one_price_changes() -> None:
    panel = _panel(n_symbols=5, n_sessions=10)
    before = panel_hash(panel)
    d, px = panel["S00.AU"][3]
    panel["S00.AU"][3] = (d, px + Decimal("0.000001"))
    assert panel_hash(panel) != before


def test_float_prices_are_refused() -> None:
    with pytest.raises(HarnessError, match="float"):
        evaluate_momentum_12_1({"X.AU": [(date(2025, 1, 2), 1.0)]})  # type: ignore[list-item]


# --- (2) failed variants remain visible ---------------------------------------------------


def test_a_too_short_panel_is_a_reported_failure_not_a_crash_or_a_silent_empty() -> None:
    with pytest.raises(HarnessError, match="panel too short"):
        evaluate_momentum_12_1(_panel(n_sessions=100))


class FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.runs: list[dict[str, object]] = []

    async def execute(self, sql: str, *args: Any) -> str:
        self.executed.append((sql, args))
        if "INSERT INTO research_runs" in sql:
            self.runs.append(json.loads(args[8]))
        return "INSERT 0 1"

    async def fetch(self, sql: str, *args: Any) -> list[Any]:
        assert "FROM research_runs" in sql
        return [{"payload": r} for r in self.runs if r["hypothesis_id"] == args[0]]

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        return None


def _hypothesis() -> ResearchHypothesis:
    return ResearchHypothesis(
        hypothesis_id="hyp-test", title="t", statement="s", factor="momentum_12_1",
        universe_rule="u", rebalance="monthly", horizon_trading_days=21,
        cost_bps_per_side=Decimal("25"), falsifier="f", registered_by="test", created_at=NOW,
    )


def _strategy() -> StrategyVersion:
    return StrategyVersion(
        strategy_version_id="sv-test", hypothesis_id="hyp-test", parameters={"k": "v"},
        code_ref="asxos.domain.research.registry.harness:evaluate_momentum_12_1", created_at=NOW,
    )


def _run(run_id: str, *, outcome: str, reason: str | None = None) -> ResearchRun:
    return ResearchRun(
        run_id=run_id, hypothesis_id="hyp-test", strategy_version_id="sv-test",
        as_of=date(2026, 9, 1), panel_hash="a" * 64, outcome=outcome,  # type: ignore[arg-type]
        failure_reason=reason, evaluation={} if outcome == "fail" else {"n_evaluated": 3},
        variants_tried=1, created_at=NOW,
    )


@pytest.mark.asyncio
async def test_failed_and_successful_runs_are_both_stored_and_listed() -> None:
    conn = FakeConn()
    await save_hypothesis(conn, _hypothesis())
    await save_strategy_version(conn, _strategy())
    await save_run(conn, _run("run-1", outcome="fail", reason="panel too short"))
    await save_run(conn, _run("run-2", outcome="evaluated"))
    history = await list_runs(conn, hypothesis_id="hyp-test")
    assert [r.run_id for r in history] == ["run-1", "run-2"]
    assert history[0].outcome == "fail" and history[0].failure_reason == "panel too short"
    assert history[1].outcome == "evaluated"


@pytest.mark.asyncio
async def test_runs_are_never_upserted_over() -> None:
    """A run row has no ON CONFLICT — a second identical id must be a DB error, not a silent replace."""
    conn = FakeConn()
    await save_run(conn, _run("run-1", outcome="evaluated"))
    sql, _ = conn.executed[-1]
    assert "ON CONFLICT" not in sql


# --- (3) no self-promotion into capital ------------------------------------------------------


def test_promotion_states_contain_no_capital_state() -> None:
    joined = " ".join(PROMOTION_STATES).lower()
    for word in ("capital", "live", "allocat", "approved", "production", "deploy"):
        assert word not in joined


def test_legal_promotion_requires_evidence_and_illegal_edges_are_refused() -> None:
    assert advance("research", "paper_candidate", evidence_run_id="run-2", reason="holdout > 0") == "paper_candidate"
    with pytest.raises(PromotionError, match="requires an evidence run id"):
        advance("research", "paper_candidate", evidence_run_id=None, reason="x")
    with pytest.raises(PromotionError, match="illegal transition"):
        advance("research", "paper", evidence_run_id="run-2", reason="skip a step")
    with pytest.raises(PromotionError, match="illegal transition"):
        advance("retired", "paper", evidence_run_id="run-2", reason="resurrect")
    with pytest.raises(PromotionError):
        advance("paper", "capital", evidence_run_id="run-2", reason="nope")  # type: ignore[arg-type]
    assert advance("paper", "retired", evidence_run_id=None, reason="diverged") == "retired"


@pytest.mark.asyncio
async def test_record_promotion_writes_the_log_row_with_the_validated_edge() -> None:
    conn = FakeConn()
    state = await record_promotion(
        conn, strategy_version_id="sv-test", current="research", to="paper_candidate",
        evidence_run_id="run-2", reason="holdout positive", decided_by="james",
    )
    assert state == "paper_candidate"
    sql, args = conn.executed[-1]
    assert "INSERT INTO research_promotions" in sql
    assert args[1:3] == ("research", "paper_candidate")


def test_strategy_version_refuses_an_unknown_state() -> None:
    with pytest.raises(ValueError):
        StrategyVersion(
            strategy_version_id="sv", hypothesis_id="h", parameters={}, code_ref="c",
            promotion_state="capital", created_at=NOW,  # type: ignore[arg-type]
        )


def test_registry_package_imports_no_capital_module_and_names_no_allocation_flag() -> None:
    pkg = Path(__file__).parent.parent / "asxos" / "domain" / "research" / "registry"
    text = "\n".join(p.read_text(encoding="utf-8") for p in pkg.glob("*.py"))
    assert not re.search(r"^\s*(from|import)\s+asxos\.domain\.(portfolio|models)\b", text, re.M)
    for forbidden in ("approved_for_allocation", "model_versions", "holding_lots"):
        assert forbidden not in text, forbidden
    # `signals` may appear only as a refused token in the loader's guard — never as a source.
    assert re.search(r"\b(from|join)\s+signals\b", text, re.I) is None
    ddl_lines = (Path(__file__).parent.parent / "migrations" / "0050_research_registry.sql").read_text().splitlines()
    ddl = "\n".join(line for line in ddl_lines if not line.lstrip().startswith("--"))
    # The header comment NAMES these to say they are absent; the DDL itself must not touch them.
    for forbidden in ("approved_for_allocation", "model_versions", "holding_lots"):
        assert forbidden not in ddl, forbidden


# --- contracts + loader ----------------------------------------------------------------------


def test_contracts_are_content_addressed_and_reject_floats() -> None:
    h = _hypothesis()
    assert len(h.content_hash) == 64
    assert ResearchHypothesis.model_validate(h.model_dump(mode="json")).content_hash == h.content_hash
    with pytest.raises(ValueError):
        _run("r", outcome="evaluated").model_copy(update={"evaluation": {"x": 1.5}}).model_validate(
            {**_run("r", outcome="evaluated").model_dump(mode="json"), "evaluation": {"x": 1.5}, "content_hash": ""}
        )


def test_run_carries_no_alpha_claim_and_an_unavailable_benchmark() -> None:
    r = _run("r", outcome="evaluated")
    assert r.alpha_claim.startswith("none")
    assert r.benchmark.startswith("unavailable")


def test_panel_sql_is_bound_and_admissible() -> None:
    assert "$1" in SQL_PANEL and "is_active" in SQL_PANEL
    assert_panel_sql_admissible(SQL_PANEL)
    with pytest.raises(ValueError):
        assert_panel_sql_admissible("SELECT prob_up FROM signals")
