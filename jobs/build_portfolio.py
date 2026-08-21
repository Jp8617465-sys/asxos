#!/usr/bin/env python
"""
Weekly portfolio construction job (M13.7).

Runs the full build-portfolio pipeline — load profile, signals, universe,
vol, allocate, constrain, rebalance, persist — and writes the result to
``rebalance_runs`` / ``target_allocations`` / ``proposed_trades``.

The brief's portfolio section (section 6) reads from the latest persisted
run; this job must succeed before the Monday brief runs.

GATE: refuses to run if ASXOS_PERSONAL_USE != "1" (Part 0 Q1 regulatory
firewall; plan Part B M13.6 — every portfolio entry point checks this).

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/build_portfolio.py
    ASXOS_PERSONAL_USE=1 python jobs/build_portfolio.py --as-of 2026-05-22
    ASXOS_PERSONAL_USE=1 python jobs/build_portfolio.py --dry-run

Schedule: not currently scheduled. build_portfolio was deleted from the live
scheduler per a 2026-08-19 governor ruling, as part of the Model A retirement
lane — see docs/product/roadmap-state.md for the current queue and its
proposed replacement direction.
"""
import argparse
import asyncio
import logging
import os
import sys
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main(as_of: date, dry_run: bool) -> None:
    # Personal-use gate (plan Part 0 Q1 / CLAUDE.md regulatory firewall).
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        log.error(
            "ASXOS_PERSONAL_USE is not set to '1'. "
            "This job generates personal-advice outputs under s766B "
            "(Corporations Act 2001) and must only run in single-user mode. "
            "Set ASXOS_PERSONAL_USE=1 in your environment."
        )
        sys.exit(1)

    await init_pool()
    try:
        async with JobMonitor(
            job_name="build_portfolio",
            as_of=as_of,
            healthcheck_url=settings.healthcheck_url_build_portfolio,
        ) as monitor:
            from asxos.domain.portfolio.build import PortfolioService

            svc = PortfolioService()
            async with acquire() as conn:
                result = await svc.build(conn, as_of=as_of)

                if dry_run:
                    log.info(
                        f"--dry-run: built run for {as_of} "
                        f"({len(result.targets)} targets, {len(result.trades)} trades) — not persisted"
                    )
                    monitor.rows_written = 0
                else:
                    run_id = await svc.persist(conn, result)
                    log.info(
                        f"persisted run_id={run_id} for {as_of}: "
                        f"{len(result.targets)} targets, {len(result.trades)} trades"
                    )
                    s = result.summary
                    log.info(
                        f"summary: {s['n_buys']} buys +${s['total_buy_aud']:,.0f} · "
                        f"{s['n_sells']} sells ${s['total_sell_aud']:,.0f} · "
                        f"{s['n_holds']} holds · {s['n_deferrals']} deferred"
                    )
                    monitor.rows_written = len(result.trades)
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly portfolio construction job.")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Build date YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and log the result without writing to the DB.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.as_of or date.today(), dry_run=args.dry_run))
