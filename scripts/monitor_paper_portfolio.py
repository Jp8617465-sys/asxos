#!/usr/bin/env python
"""
Paper-portfolio performance monitor — CLI (M13.8+).

Compares persisted build-portfolio runs against realised prices, benchmarks and
simple baselines, and records the result. This is the *scoreboard*: it measures
whether the model portfolio performs, NOT whether the pipeline ran. A single
run's realised P&L is one noisy data point and is never alpha proof.

Usage:
    python scripts/monitor_paper_portfolio.py --run-id 1
    python scripts/monitor_paper_portfolio.py --all
    python scripts/monitor_paper_portfolio.py --run-id 1 --as-of 2026-07-17
    python scripts/monitor_paper_portfolio.py --run-id 1 --no-persist --format json
    python scripts/monitor_paper_portfolio.py --all --commission-bps 10 --slippage-bps 7

Evidence labels in the report:
    [VERIFIED] computed from DB/prices   [INFERRED] assumption (e.g. cost bps)
    [MISSING]  not yet measurable / data absent

Persistence (UPSERT, idempotent) requires migration 0024_paper_portfolio_perf.
Existing runs and holdings are never modified.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.portfolio.monitor import CostModel, PerfReport, compute_report
from asxos.domain.portfolio.monitor_loader import (
    list_persisted_runs,
    load_run_inputs,
)
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persistence (idempotent UPSERT into migration 0024 tables)
# ---------------------------------------------------------------------------


async def persist_report(conn, rep: PerfReport) -> int:
    """UPSERT the report into the three scoreboard tables. Returns rows written."""
    written = 0
    await conn.execute(
        """
        INSERT INTO paper_portfolio_run_metrics (
            run_id, eval_as_of, run_as_of, signals_as_of, model_version, n_positions,
            measurable, n_forward_days, measurability_note, capital_aud, cash_aud,
            total_nav_aud, price_return_pct, total_return_pct, benchmark_available,
            benchmark_source, benchmark_return_pct, benchmark_relative_pct,
            equal_weight_return_pct, model_weight_return_pct, hit_rate_pct,
            avg_winner_pct, avg_loser_pct, payoff_ratio, max_drawdown_pct,
            realised_vol_pct, turnover_pct, est_cost_aud, est_cost_bps_of_capital,
            n_missing_events
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
            $21,$22,$23,$24,$25,$26,$27,$28,$29,$30
        )
        ON CONFLICT (run_id, eval_as_of) DO UPDATE SET
            run_as_of=EXCLUDED.run_as_of, signals_as_of=EXCLUDED.signals_as_of,
            model_version=EXCLUDED.model_version, n_positions=EXCLUDED.n_positions,
            measurable=EXCLUDED.measurable, n_forward_days=EXCLUDED.n_forward_days,
            measurability_note=EXCLUDED.measurability_note, capital_aud=EXCLUDED.capital_aud,
            cash_aud=EXCLUDED.cash_aud, total_nav_aud=EXCLUDED.total_nav_aud,
            price_return_pct=EXCLUDED.price_return_pct, total_return_pct=EXCLUDED.total_return_pct,
            benchmark_available=EXCLUDED.benchmark_available, benchmark_source=EXCLUDED.benchmark_source,
            benchmark_return_pct=EXCLUDED.benchmark_return_pct,
            benchmark_relative_pct=EXCLUDED.benchmark_relative_pct,
            equal_weight_return_pct=EXCLUDED.equal_weight_return_pct,
            model_weight_return_pct=EXCLUDED.model_weight_return_pct,
            hit_rate_pct=EXCLUDED.hit_rate_pct, avg_winner_pct=EXCLUDED.avg_winner_pct,
            avg_loser_pct=EXCLUDED.avg_loser_pct, payoff_ratio=EXCLUDED.payoff_ratio,
            max_drawdown_pct=EXCLUDED.max_drawdown_pct, realised_vol_pct=EXCLUDED.realised_vol_pct,
            turnover_pct=EXCLUDED.turnover_pct, est_cost_aud=EXCLUDED.est_cost_aud,
            est_cost_bps_of_capital=EXCLUDED.est_cost_bps_of_capital,
            n_missing_events=EXCLUDED.n_missing_events, computed_at=now()
        """,
        rep.run_id, rep.eval_as_of, rep.run_as_of, rep.signals_as_of, rep.model_version,
        rep.n_positions, rep.measurable, rep.n_forward_days, rep.measurability_note,
        rep.capital_aud, rep.cash_aud, rep.total_nav_aud, rep.price_return_pct,
        rep.total_return_pct, rep.benchmark_available, rep.benchmark_source,
        rep.benchmark_return_pct, rep.benchmark_relative_pct, rep.equal_weight_return_pct,
        rep.model_weight_return_pct, rep.hit_rate_pct, rep.avg_winner_pct, rep.avg_loser_pct,
        rep.payoff_ratio, rep.max_drawdown_pct, rep.realised_vol_pct, rep.turnover_pct,
        rep.cost.est_cost_aud, rep.cost.est_cost_bps_of_capital, len(rep.missing_events),
    )
    written += 1

    for pt in rep.nav_series:
        await conn.execute(
            """
            INSERT INTO paper_portfolio_nav (
                run_id, dt, invested_mv_aud, cash_aud, total_nav_aud, cum_return_pct,
                daily_return_pct, n_priced, n_missing, forward_filled, benchmark_level,
                benchmark_cum_return_pct
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ON CONFLICT (run_id, dt) DO UPDATE SET
                invested_mv_aud=EXCLUDED.invested_mv_aud, cash_aud=EXCLUDED.cash_aud,
                total_nav_aud=EXCLUDED.total_nav_aud, cum_return_pct=EXCLUDED.cum_return_pct,
                daily_return_pct=EXCLUDED.daily_return_pct, n_priced=EXCLUDED.n_priced,
                n_missing=EXCLUDED.n_missing, forward_filled=EXCLUDED.forward_filled,
                benchmark_level=EXCLUDED.benchmark_level,
                benchmark_cum_return_pct=EXCLUDED.benchmark_cum_return_pct, computed_at=now()
            """,
            rep.run_id, pt.dt, pt.invested_mv_aud, pt.cash_aud, pt.total_nav_aud,
            pt.cum_return_pct, pt.daily_return_pct, pt.n_priced, pt.n_missing,
            pt.forward_filled, pt.benchmark_level, pt.benchmark_cum_return_pct,
        )
        written += 1

    for p in rep.positions:
        await conn.execute(
            """
            INSERT INTO paper_portfolio_position_perf (
                run_id, eval_as_of, symbol, sector, weight, entry_close, last_close,
                last_dt, price_return_pct, total_return_pct, pnl_aud, contribution_pct,
                signal_label, prob_up, expected_return, used_adj_close, priced
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
            ON CONFLICT (run_id, eval_as_of, symbol) DO UPDATE SET
                sector=EXCLUDED.sector, weight=EXCLUDED.weight, entry_close=EXCLUDED.entry_close,
                last_close=EXCLUDED.last_close, last_dt=EXCLUDED.last_dt,
                price_return_pct=EXCLUDED.price_return_pct, total_return_pct=EXCLUDED.total_return_pct,
                pnl_aud=EXCLUDED.pnl_aud, contribution_pct=EXCLUDED.contribution_pct,
                signal_label=EXCLUDED.signal_label, prob_up=EXCLUDED.prob_up,
                expected_return=EXCLUDED.expected_return, used_adj_close=EXCLUDED.used_adj_close,
                priced=EXCLUDED.priced, computed_at=now()
            """,
            rep.run_id, rep.eval_as_of, p.symbol, p.sector, p.weight, p.entry_close,
            p.last_close, p.last_dt, p.price_return_pct, p.total_return_pct, p.pnl_aud,
            p.contribution_pct, p.signal_label, p.prob_up, p.expected_return,
            p.used_adj_close, p.priced,
        )
        written += 1
    return written


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _v(x: object, suffix: str = "", state: str = "VERIFIED") -> str:
    if x is None:
        return f"        n/a  [{'MISSING'}]"
    return f"{x}{suffix}  [{state}]"


def render_text(rep: PerfReport) -> str:
    L: list[str] = []
    L.append("=" * 78)
    L.append(f"PAPER-PORTFOLIO SCOREBOARD — run_id={rep.run_id}")
    L.append("=" * 78)
    L.append(
        f"entry(run) as_of : {rep.run_as_of}   signals as_of: {rep.signals_as_of}   "
        f"model: {rep.model_version}"
    )
    L.append(
        f"eval as_of       : {rep.eval_as_of}   capital: {rep.capital_aud}   "
        f"cash: {rep.cash_aud}   positions: {rep.n_positions}"
    )
    L.append("-" * 78)
    state = "VERIFIED" if rep.measurable else "MISSING"
    L.append(f"MEASURABLE       : {rep.measurable}  ({rep.n_forward_days} forward trading days)  [{state}]")
    L.append(f"  {rep.measurability_note}")
    L.append("-" * 78)
    L.append("HEADLINE PERFORMANCE")
    L.append(f"  price return (NAV)       : {_v(rep.price_return_pct, '%')}")
    L.append(f"  total return (adj_close) : {_v(rep.total_return_pct, '%')}")
    bstate = "VERIFIED" if rep.benchmark_available else "MISSING"
    L.append(f"  benchmark                : {rep.benchmark_source}  [{bstate}]")
    L.append(f"  benchmark return         : {_v(rep.benchmark_return_pct, '%', bstate)}")
    L.append(f"  benchmark-relative       : {_v(rep.benchmark_relative_pct, '%', bstate)}")
    L.append(f"  equal-weight baseline    : {_v(rep.equal_weight_return_pct, '%')}")
    L.append(f"  model-weight baseline    : {_v(rep.model_weight_return_pct, '%')}")
    L.append("-" * 78)
    L.append("RISK / QUALITY")
    L.append(f"  hit rate                 : {_v(rep.hit_rate_pct, '%')}")
    L.append(f"  avg winner / avg loser   : {_v(rep.avg_winner_pct, '%')} / {_v(rep.avg_loser_pct, '%')}")
    L.append(f"  payoff ratio             : {_v(rep.payoff_ratio)}")
    L.append(f"  max drawdown             : {_v(rep.max_drawdown_pct, '%')}")
    L.append(f"  realised vol (annualised): {_v(rep.realised_vol_pct, '%')}")
    L.append(f"  turnover (one-way)       : {rep.turnover_pct}%  [VERIFIED]")
    L.append("-" * 78)
    L.append("TRANSACTION COSTS  [INFERRED — configurable assumptions, not measured]")
    L.append(
        f"  traded notional: {rep.cost.traded_notional_aud}   "
        f"commission: {rep.cost.commission_bps}bps   slippage: {rep.cost.slippage_bps}bps"
    )
    L.append(
        f"  est cost: {rep.cost.est_cost_aud} AUD  "
        f"({rep.cost.est_cost_bps_of_capital} bps of capital)"
    )

    if rep.measurable:
        L.append("-" * 78)
        L.append("NAV PATH (last 10 points)")
        L.append(f"  {'dt':<12}{'nav_aud':>16}{'cum%':>9}{'daily%':>9}{'priced':>8}{'miss':>6}{'bench%':>9}")
        for pt in rep.nav_series[-10:]:
            L.append(
                f"  {pt.dt!s:<12}{pt.total_nav_aud:>16}{pt.cum_return_pct:>9}"
                f"{('' if pt.daily_return_pct is None else pt.daily_return_pct):>9}"
                f"{pt.n_priced:>8}{pt.n_missing:>6}"
                f"{('' if pt.benchmark_cum_return_pct is None else pt.benchmark_cum_return_pct):>9}"
            )

        L.append("-" * 78)
        L.append("POSITIONS (by weight)")
        L.append(
            f"  {'symbol':<10}{'sector':<22}{'label':<12}{'prob':>6}{'wt%':>7}"
            f"{'tot_ret%':>10}{'contrib%':>10}{'priced':>8}"
        )
        for p in sorted(rep.positions, key=lambda x: x.weight, reverse=True):
            L.append(
                f"  {p.symbol:<10}{(p.sector or '')[:21]:<22}{p.signal_label:<12}"
                f"{p.prob_up:>6}{p.weight * Decimal('100'):>7.2f}"
                f"{('' if p.total_return_pct is None else p.total_return_pct):>10}"
                f"{('' if p.contribution_pct is None else p.contribution_pct):>10}"
                f"{p.priced!s:>8}"
            )

        L.append("-" * 78)
        L.append("ATTRIBUTION BY SECTOR")
        for b in rep.sector_attribution:
            L.append(
                f"  {b.label:<24} n={b.n:<3} priced={b.n_priced:<3} "
                f"mean_ret={b.mean_total_return_pct} hit={b.hit_rate_pct} pnl={b.total_pnl_aud}"
            )
        L.append("PERFORMANCE BY SIGNAL LABEL")
        for b in rep.by_signal_label:
            L.append(
                f"  {b.label:<14} n={b.n:<3} priced={b.n_priced:<3} "
                f"mean_ret={b.mean_total_return_pct} hit={b.hit_rate_pct} pnl={b.total_pnl_aud}"
            )
        L.append("PERFORMANCE BY prob_up BUCKET")
        for b in rep.by_prob_up_bucket:
            L.append(
                f"  {b.label:<14} n={b.n:<3} priced={b.n_priced:<3} "
                f"mean_ret={b.mean_total_return_pct} hit={b.hit_rate_pct}"
            )
        L.append("PERFORMANCE BY expected_return BUCKET")
        for b in rep.by_expected_return_bucket:
            L.append(
                f"  {b.label:<14} n={b.n:<3} priced={b.n_priced:<3} "
                f"mean_ret={b.mean_total_return_pct} hit={b.hit_rate_pct}"
            )

        if rep.missing_events:
            L.append("-" * 78)
            L.append(f"MISSING-DATA EVENTS: {len(rep.missing_events)} (first 10)")
            for e in rep.missing_events[:10]:
                L.append(f"  {e.dt} {e.symbol} — {e.detail}")

    L.append("=" * 78)
    L.append(
        "DISCIPLINE: pipeline health != investment performance. Realised paper "
        "P&L is one noisy sample, not alpha proof. expected_return is uncalibrated; "
        "treat prob_up as the conviction signal."
    )
    L.append("=" * 78)
    return "\n".join(L)


def _json_default(o: object) -> object:
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(f"not serialisable: {type(o)}")


def render_json(rep: PerfReport) -> str:
    return json.dumps(asdict(rep), default=_json_default, indent=2)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


async def run_one(
    conn, run_id: int, eval_as_of: date, cost: CostModel, forward_fill: bool, persist: bool
) -> tuple[PerfReport | None, int]:
    inp = await load_run_inputs(
        conn, run_id, eval_as_of, cost_model=cost, forward_fill=forward_fill
    )
    if inp is None:
        return None, 0
    rep = compute_report(inp)
    written = 0
    if persist:
        try:
            written = await persist_report(conn, rep)
        except Exception as exc:
            if "paper_portfolio" in str(exc):
                log.error(
                    "Persistence failed — apply migration 0024_paper_portfolio_perf "
                    "via Supabase MCP first. (%s)", exc,
                )
            else:
                raise
    return rep, written


async def main(args: argparse.Namespace) -> None:
    eval_as_of: date = args.as_of or date.today()
    cost = CostModel(
        commission_bps=Decimal(str(args.commission_bps)),
        slippage_bps=Decimal(str(args.slippage_bps)),
    )
    await init_pool()
    try:
        async with acquire() as conn:
            if args.all:
                runs = await list_persisted_runs(conn)
                run_ids = [r["run_id"] for r in runs]
            else:
                run_ids = [args.run_id]
            if not run_ids:
                log.warning("no runs to evaluate")
                return

            async with JobMonitor(
                job_name="monitor_paper_portfolio",
                as_of=eval_as_of,
                healthcheck_url=getattr(
                    settings, "healthcheck_url_monitor_paper_portfolio", ""
                ),
            ) as monitor:
                total_written = 0
                reports: list[PerfReport] = []
                for rid in run_ids:
                    rep, written = await run_one(
                        conn, rid, eval_as_of, cost, args.forward_fill, args.persist
                    )
                    if rep is None:
                        log.warning("run_id %s not found — skipping", rid)
                        continue
                    reports.append(rep)
                    total_written += written
                monitor.rows_written = total_written

            for rep in reports:
                if args.format == "json":
                    print(render_json(rep))
                else:
                    print(render_text(rep))
    finally:
        await close_pool()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Paper-portfolio performance monitor.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-id", type=int, help="evaluate a single persisted run")
    g.add_argument("--all", action="store_true", help="evaluate all persisted runs")
    p.add_argument(
        "--as-of", type=date.fromisoformat, default=None,
        help="evaluation date YYYY-MM-DD (default: today). No price after this date is used.",
    )
    p.add_argument("--commission-bps", type=float, default=8.0)
    p.add_argument("--slippage-bps", type=float, default=5.0)
    p.add_argument(
        "--forward-fill", action="store_true",
        help="carry last price for names missing a bar (always flagged in diagnostics)",
    )
    persist = p.add_mutually_exclusive_group()
    persist.add_argument("--persist", dest="persist", action="store_true", default=True)
    persist.add_argument("--no-persist", dest="persist", action="store_false")
    p.add_argument("--format", choices=["table", "json"], default="table")
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(_parse_args())))  # type: ignore[func-returns-value]
