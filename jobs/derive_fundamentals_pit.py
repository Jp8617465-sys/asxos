#!/usr/bin/env python
"""
Derive point-in-time fundamentals (rs_fundamentals_pit) from the raw research store.

Pure DB-to-DB: reads rs_financial_statements (yearly) + rs_corporate_actions and writes
rs_fundamentals_pit, stamping each row with the guarded knowledge_date. No EODHD. Run
weekly, AFTER sync_financial_statements + sync_corporate_actions.

Usage:
    python jobs/derive_fundamentals_pit.py
    python jobs/derive_fundamentals_pit.py --symbols CBA.AU,BHP.AU
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.fundamentals_pit import refresh_fundamentals_pit
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

    today = date.today()
    await init_pool()

    async with JobMonitor(
        job_name="derive_fundamentals_pit",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_derive_fundamentals_pit,
    ) as monitor:
        async with acquire() as conn:
            counts = await refresh_fundamentals_pit(conn, as_of=today, symbols=symbols)
            if counts["rows"] == 0:
                raise RuntimeError(
                    "no PIT rows derived — rs_financial_statements is empty. "
                    "Run sync_financial_statements first."
                )
        monitor.rows_written = counts["rows"]
        log.info(
            f"derive_fundamentals_pit done — symbols={counts['symbols']} rows={counts['rows']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
