"""asx research — Stage 2 registry: run one hypothesis reproducibly and record it.

Read-only against prices/universe; writes only the append-only registry
tables (migration 0050). Not personal-use gated: no holdings, no tax, no
theses, never `signals`. Output is a research record, not a recommendation.
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime
from decimal import Decimal

import typer

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.research.registry import (
    ResearchHypothesis,
    ResearchRun,
    StrategyVersion,
    evaluate_momentum_12_1,
)
from asxos.domain.research.registry.harness import HarnessError, panel_hash
from asxos.domain.research.registry.loader import load_panel
from asxos.domain.research.registry.repository import (
    list_runs,
    save_hypothesis,
    save_run,
    save_strategy_version,
)

research_app = typer.Typer(
    help="Research registry — reproducible hypothesis evaluation (Stage 2).",
    no_args_is_help=True,
    add_completion=False,
)

HYPOTHESIS_ID = "hyp-momentum-12-1-asx-monthly-v1"
STRATEGY_ID = "sv-momentum-12-1-top-decile-25bp-v1"


def momentum_hypothesis(now: datetime) -> ResearchHypothesis:
    return ResearchHypothesis(
        hypothesis_id=HYPOTHESIS_ID,
        title="12-1 cross-sectional momentum on active ASX equities",
        statement=(
            "Ranking active .AU symbols by 12-month return excluding the most recent "
            "month, holding the top decile equal-weight and rebalancing monthly, "
            "produces a positive net-of-cost return per period."
        ),
        factor="momentum_12_1",
        universe_rule="universe.is_active AND symbol LIKE '%.AU' AND adj_close IS NOT NULL",
        rebalance="monthly",
        horizon_trading_days=21,
        cost_bps_per_side=Decimal("25"),
        falsifier=(
            "Holdout mean net return per period <= 0 over a sample large enough to "
            "matter — which this data does not yet provide (prices begin 2025-01-02)."
        ),
        registered_by="arbi (Amendment H, campaign node H3-A)",
        created_at=now,
    )


def momentum_strategy(now: datetime) -> StrategyVersion:
    return StrategyVersion(
        strategy_version_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        parameters={"top_fraction": "0.1", "cost_bps_per_side": "25", "horizon_trading_days": "21"},
        code_ref="asxos.domain.research.registry.harness:evaluate_momentum_12_1",
        created_at=now,
    )


@research_app.command("run")
def research_run(
    as_of: str = typer.Option(..., "--as-of", help="Panel cutoff YYYY-MM-DD"),
    twice: bool = typer.Option(True, "--twice/--once", help="Evaluate twice; refuse if hashes differ."),
    persist: bool = typer.Option(True, "--persist/--dry-run", help="Write the run to the registry."),
) -> None:
    """Evaluate the momentum hypothesis over the live price panel and record the run."""
    asyncio.run(_run(date.fromisoformat(as_of), twice, persist))


async def _run(as_of: date, twice: bool, persist: bool) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    hypothesis = momentum_hypothesis(now)
    strategy = momentum_strategy(now)

    await init_pool()
    try:
        async with acquire() as conn:
            panel = await load_panel(conn, as_of=as_of)
            p_hash = panel_hash(panel)
            outcome, reason, evaluation = "evaluated", None, {}
            try:
                first = evaluate_momentum_12_1(panel)
                if twice:
                    second = evaluate_momentum_12_1(panel)
                    if second.hash != first.hash:
                        raise typer.Exit(code=2)
                evaluation = first.payload
            except HarnessError as exc:
                outcome, reason = "fail", str(exc)

            run = ResearchRun(
                run_id=f"run-{HYPOTHESIS_ID}-{as_of.isoformat()}-{now.strftime('%Y%m%dT%H%M%SZ')}",
                hypothesis_id=HYPOTHESIS_ID,
                strategy_version_id=STRATEGY_ID,
                as_of=as_of,
                panel_hash=p_hash,
                outcome=outcome,  # type: ignore[arg-type]
                failure_reason=reason,
                evaluation=evaluation,
                variants_tried=1,
                created_at=now,
            )
            if persist:
                await save_hypothesis(conn, hypothesis)
                await save_strategy_version(conn, strategy)
                await save_run(conn, run)
                history = await list_runs(conn, hypothesis_id=HYPOTHESIS_ID)
            else:
                history = [run]
    finally:
        await close_pool()

    console.print(json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True))
    console.print(
        f"[dim]run={run.run_id} outcome={run.outcome} content_hash={run.content_hash} "
        f"panel_hash={p_hash} reproducible={'yes' if twice and outcome == 'evaluated' else 'n/a'} "
        f"runs_on_record={len(history)} failed_on_record={sum(1 for r in history if r.outcome == 'fail')}[/dim]"
    )
