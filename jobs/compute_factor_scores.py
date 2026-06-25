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

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

    await init_pool()

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
