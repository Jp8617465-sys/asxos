#!/usr/bin/env python
"""perf_report.py — duration-trend report over job_runs (READ-ONLY).

The thin consumer of ``asxos.domain.opsmetrics``. Reads ``job_runs``, computes a
robust trend per job, and prints a markdown report. SELECTs only — no INSERT,
UPDATE or DDL, and no capital-impacting output of any kind.

This exists to give the standing perf lane an evidence base. Until it has run for
a few weeks, that lane stays gated: ``security-perf-mission-loop.md`` §4 forbids
speculative perf findings, and a lane with no measurements can only speculate.

Usage:
    python scripts/perf_report.py                 # all jobs, default windows
    python scripts/perf_report.py --job sync_prices
    python scripts/perf_report.py --days 90 --recent 5

Read the honest limits in ``asxos/domain/opsmetrics/trend.py`` before acting on
anything here. In short: this detects sustained shifts, not spikes; for ingestion
jobs it largely measures upstream APIs rather than our code; and a REGRESSED
verdict is a prompt to investigate, never a mandate to optimise.
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.opsmetrics import (
    DEFAULT_MIN_BASELINE,
    DEFAULT_RECENT_WINDOW,
    Sample,
    TrendResult,
    Verdict,
    duration_trend,
)

_SQL = """
SELECT job_name, as_of, duration_ms, status
FROM job_runs
WHERE as_of >= CURRENT_DATE - $1::int
ORDER BY job_name, as_of
"""

_ORDER = {
    Verdict.REGRESSED: 0,
    Verdict.IMPROVED: 1,
    Verdict.OK: 2,
    Verdict.INSUFFICIENT_DATA: 3,
}


async def collect(days: int, recent: int, min_baseline: int) -> list[TrendResult]:
    await init_pool()
    try:
        async with acquire() as conn:
            rows = await conn.fetch(_SQL, days)
    finally:
        await close_pool()

    by_job: dict[str, list[Sample]] = {}
    for row in rows:
        by_job.setdefault(row["job_name"], []).append(
            Sample(
                as_of=row["as_of"],
                duration_ms=row["duration_ms"],
                status=row["status"],
            )
        )

    results = [
        duration_trend(job, samples, recent_window=recent, min_baseline=min_baseline)
        for job, samples in by_job.items()
    ]
    return sorted(results, key=lambda r: (_ORDER[r.verdict], r.job_name))


def _ms(value: Decimal | None) -> str:
    return "—" if value is None else f"{value:,.0f}"


def render(results: list[TrendResult], days: int) -> str:
    lines = [
        f"# Job duration trend — last {days} days",
        "",
        "Robust trend (trailing median + MAD) over `job_runs.duration_ms`, successful",
        "runs only. A REGRESSED verdict needs both a median ratio past 1.5x and a shift",
        "past 3 MAD — see `asxos/domain/opsmetrics/trend.py` for why both gates.",
        "",
        "| Job | Verdict | Baseline | Recent | Ratio | n | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ratio = "—" if r.ratio is None else f"{r.ratio:.2f}x"
        lines.append(
            f"| `{r.job_name}` | {r.verdict.value} | {_ms(r.baseline_median_ms)} ms "
            f"| {_ms(r.recent_median_ms)} ms | {ratio} | {r.n_usable} | {r.note} |"
        )

    regressed = [r for r in results if r.is_actionable]
    lines += ["", f"**{len(regressed)} regressed / {len(results)} jobs.**"]
    if not regressed:
        lines.append("")
        lines.append(
            "No sustained regression. This is a normal and useful result — the repo's "
            "last measured hot paths were all judged not worth optimising "
            "(`docs/model-a-audit-and-extension-plan-2026-07-04.md:119-124`)."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=120, help="lookback window (default 120)")
    parser.add_argument("--recent", type=int, default=DEFAULT_RECENT_WINDOW)
    parser.add_argument("--min-baseline", type=int, default=DEFAULT_MIN_BASELINE)
    parser.add_argument("--job", type=str, default=None, help="restrict to one job name")
    args = parser.parse_args()

    results = asyncio.run(collect(args.days, args.recent, args.min_baseline))
    if args.job:
        results = [r for r in results if r.job_name == args.job]
    print(render(results, args.days))


if __name__ == "__main__":
    main()
