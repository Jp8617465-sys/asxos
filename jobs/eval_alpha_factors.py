#!/usr/bin/env python
"""
Evaluate the value×quality factor candidate on real ASX data (M14 research).

Read-only: loads the rs_factor_scores cross-section panel (factor scores joined
forward to prices), runs the alpha_eval engine, and prints rank-IC by horizon
(quoting the EFFECTIVE t — the non-overlapping-date t-stat), decile spreads, the
liquidity split, and the underpower warnings. Writes nothing; blesses nothing.

This is the engine the audit's step-8 names: the value×quality COMPOSITE is TESTED
here, never crowned. With ~18 months of prices the long horizons are underpowered —
the warnings say so, and the candidate stays a candidate until history deepens.

Usage:
    python jobs/eval_alpha_factors.py
    python jobs/eval_alpha_factors.py --factor-set-version fs_v1
"""
import argparse
import asyncio
import logging

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.research.alpha_eval import AlphaReport, evaluate
from asxos.domain.research.alpha_loader import (
    FACTOR_HORIZONS,
    _FACTOR_SCORE_COLS,
    load_factor_panel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _print_report(report: AlphaReport) -> None:
    print("\n=== Factor alpha evaluation (value×quality candidate) ===")
    print(f"dates: {report.n_dates}  range: {report.date_min} … {report.date_max}")
    if report.regimes:
        print(f"regimes (dates each): {report.regimes}")
    print("\n-- rank-IC by horizon (quote EFFECTIVE t) --")
    print(f"{'score':<18}{'h':>5}{'IC':>9}{'eff_n':>7}{'eff_t':>8}{'sig':>5}")
    for s in report.ic:
        print(
            f"{s.score:<18}{s.horizon:>5}{s.mean_ic:>9.4f}"
            f"{s.effective_n:>7}{s.effective_t:>8}{'  ✓' if s.significant else '   '}"
        )
    print("\n-- decile spread (composite buckets, low→high) --")
    for d in report.deciles:
        print(
            f"h={d.horizon:<4} spread={d.spread_pct}%  top={d.top_pct}%  "
            f"bottom={d.bottom_pct}%  top−uppermid={d.top_minus_upper_mid_pct}%"
        )
    if report.liquidity:
        print("\n-- liquidity split (tradable vs illiquid) --")
        for ls in report.liquidity:
            print(
                f"h={ls.horizon:<4} tradable IC={ls.tradable_ic} (t={ls.tradable_effective_t}, "
                f"n≈{ls.tradable_avg_names})  illiquid IC={ls.illiquid_ic} "
                f"(t={ls.illiquid_effective_t}, n≈{ls.illiquid_avg_names})"
            )
    if report.warnings:
        print("\n-- WARNINGS (read these before drawing any conclusion) --")
        for w in report.warnings:
            print(f"  ! {w}")
    print()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--factor-set-version", type=str, default="fs_v1")
    args = parser.parse_args()

    await init_pool()
    async with acquire() as conn:
        df = await load_factor_panel(conn, factor_set_version=args.factor_set_version)
    await close_pool()

    if df.empty:
        # Fail loudly (CLAUDE.md #10) — an empty panel is a real failure, not a no-op.
        # Most likely cause: rs_factor_scores.as_of is not a trading day present in
        # `prices` (load_factor_panel joins prices.dt = rs_factor_scores.as_of), or
        # compute_factor_scores has not run for this factor_set_version.
        raise RuntimeError(
            f"factor panel is EMPTY for factor_set_version={args.factor_set_version!r} — "
            "run compute_factor_scores first, and confirm its as_of is a trading day "
            "present in `prices`."
        )

    report = evaluate(
        df,
        horizons=FACTOR_HORIZONS,
        score_cols=_FACTOR_SCORE_COLS,
        prob_col="composite_score",  # the value×quality candidate drives the deciles
    )
    _print_report(report)


if __name__ == "__main__":
    asyncio.run(main())
