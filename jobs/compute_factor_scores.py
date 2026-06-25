#!/usr/bin/env python
"""
Compute sector-neutral factor scores (rs_factor_scores) from the research store.

Pure DB-to-DB: reads rs_fundamentals_pit (PIT, knowledge_date <= as_of) + prices +
rs_security_master.gics_sector and writes rs_factor_scores (the Layer-1 alpha input).
No EODHD. Run weekly, AFTER derive_fundamentals_pit.

Usage:
    python jobs/compute_factor_scores.py
    python jobs/compute_factor_scores.py --as-of 2026-06-24
    python jobs/compute_factor_scores.py --symbols CBA.AU,BHP.AU
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.prices.coverage import latest_complete_trading_day
from asxos.domain.research.factor_scores import FACTOR_SET_VERSION, refresh_factor_scores
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=str, default=None, help="YYYY-MM-DD (default today)")
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    parser.add_argument("--factor-set-version", type=str, default=FACTOR_SET_VERSION)
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

    await init_pool()

    # Anchor as_of on the latest COMPLETE trading day (a real prices.dt) so the
    # cross-section date aligns with a price bar. This cron fires Saturday UTC, so
    # date.today() would be a non-trading day: refresh_factor_scores would still write
    # rows (it reads prices dt<=as_of), but load_factor_panel() later joins
    # prices.dt = rs_factor_scores.as_of and would find NOTHING — an empty eval panel.
    # An explicit --as-of is an operator override and wins verbatim.
    if args.as_of:
        as_of = date.fromisoformat(args.as_of)
    else:
        async with acquire() as conn:
            anchor = await latest_complete_trading_day(conn)
        if anchor is None:
            raise RuntimeError(
                "no complete trading day in prices to anchor as_of — sync_prices has not "
                "produced a complete day. Pass --as-of to override."
            )
        as_of = anchor

    async with JobMonitor(
        job_name="compute_factor_scores",
        as_of=as_of,
        healthcheck_url=settings.healthcheck_url_compute_factor_scores,
    ) as monitor:
        async with acquire() as conn:
            counts = await refresh_factor_scores(
                conn, as_of=as_of, symbols=symbols,
                factor_set_version=args.factor_set_version,
            )
            if counts["rows"] == 0:
                raise RuntimeError(
                    "no factor scores computed — rs_fundamentals_pit is empty for the "
                    "given as_of/symbols. Run derive_fundamentals_pit first."
                )
        monitor.rows_written = counts["rows"]
        log.info(
            f"compute_factor_scores done — version={args.factor_set_version} "
            f"as_of={as_of} symbols={counts['symbols']} rows={counts['rows']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
