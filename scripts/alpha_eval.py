#!/usr/bin/env python
"""
Alpha-evaluation research command (M14).

Measures whether Model A's signal contains tradable short-horizon information.
Produces rank-IC by horizon (with an effective-sample-size guard), IC decay,
decile spreads, score-variant comparison (prob_up vs composite vs expected_return),
liquidity-bucket IC, and prob_up calibration.

This is a MEASUREMENT tool. It does not bless the model. A positive IC is not
"alpha" until it survives costs, liquidity, and out-of-sample replication on a
sufficient number of INDEPENDENT dates (see the effective_n column).

Usage:
    python scripts/alpha_eval.py
    python scripts/alpha_eval.py --format json
    python scripts/alpha_eval.py --horizons 5,10,21

Note: meaningful output requires a backfill of historical signals. With only a
handful of clustered signal dates the engine will (correctly) warn that results
are not decision-grade.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.research.alpha_eval import AlphaReport, evaluate
from asxos.domain.research.alpha_loader import load_panel


def render_text(rep: AlphaReport) -> str:
    L: list[str] = []
    L.append("=" * 80)
    L.append("ALPHA-EVALUATION REPORT  (measurement only — not an alpha claim)")
    L.append("=" * 80)
    L.append(f"signal dates: {rep.n_dates}  ({rep.date_min} -> {rep.date_max})  regimes: {rep.regimes}")
    if rep.warnings:
        L.append("-" * 80)
        L.append("WARNINGS:")
        for w in rep.warnings:
            L.append(f"  ! {w}")
    L.append("-" * 80)
    L.append("RANK-IC BY HORIZON  (quote effective_t, not naive_t)")
    L.append(f"  {'h':>4}{'score':>16}{'IC':>9}{'naive_t':>9}{'eff_t':>8}{'eff_n':>7}{'sig':>5}")
    for s in rep.ic:
        L.append(
            f"  {s.horizon:>4}{s.score:>16}{s.mean_ic:>9.4f}{s.naive_t:>9.2f}"
            f"{s.effective_t:>8.2f}{s.effective_n:>7}{('Y' if s.significant else '-'):>5}"
        )
    L.append("-" * 80)
    L.append("DECILE SPREAD (prob_up, % forward return, low->high)")
    for d in rep.deciles:
        L.append(
            f"  h={d.horizon:>3}  spread(top-bottom)={d.spread_pct}%  "
            f"top-uppermid={d.top_minus_upper_mid_pct}%  monotonic={d.monotonic_frac}"
        )
        L.append(f"        buckets: {d.bucket_means_pct}")
    if rep.liquidity:
        L.append("-" * 80)
        L.append("LIQUIDITY SPLIT (prob_up IC: tradable vs illiquid)")
        for q in rep.liquidity:
            L.append(
                f"  h={q.horizon:>3}  tradable IC={q.tradable_ic} (eff_t={q.tradable_effective_t}, "
                f"n~{q.tradable_avg_names})   illiquid IC={q.illiquid_ic} (eff_t={q.illiquid_effective_t}, "
                f"n~{q.illiquid_avg_names})"
            )
    if rep.calibration:
        c = rep.calibration
        L.append("-" * 80)
        L.append(f"CALIBRATION (prob_up vs realised 5d up-rate)  Brier={c.brier}  miscal={c.miscalibration}")
        for b in c.buckets:
            L.append(f"        pred={b['pred']:.3f}  realised_up={b['realised_up_rate']:.3f}  n={b['n']}")
    L.append("=" * 80)
    L.append(
        "DISCIPLINE: effective_n is the number of NON-OVERLAPPING dates at each "
        "horizon. With effective_n < 5, IC/t are indicative only. Backfill "
        "historical signals before drawing investability conclusions."
    )
    L.append("=" * 80)
    return "\n".join(L)


async def main(args: argparse.Namespace) -> None:
    horizons = tuple(int(x) for x in args.horizons.split(",")) if args.horizons else (5, 10, 21, 63)
    await init_pool()
    try:
        async with acquire() as conn:
            df = await load_panel(conn)
    finally:
        await close_pool()

    if df.empty:
        print("No signal panel data (signal_outcomes empty or no price join).")
        return
    rep = evaluate(df, horizons=horizons)
    if args.format == "json":
        print(json.dumps(asdict(rep), default=str, indent=2))
    else:
        print(render_text(rep))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Alpha-evaluation research command.")
    p.add_argument("--horizons", default="5,10,21,63", help="comma-separated trading-day horizons")
    p.add_argument("--format", choices=["table", "json"], default="table")
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(_parse_args())))  # type: ignore[func-returns-value]
