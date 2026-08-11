#!/usr/bin/env python
"""
Derive point-in-time fundamentals (rs_fundamentals_pit) from the raw research store.

Pure DB-to-DB: reads rs_financial_statements (yearly) + rs_corporate_actions and writes
rs_fundamentals_pit, stamping each row with the guarded knowledge_date. No EODHD. Run
weekly, AFTER sync_financial_statements + sync_corporate_actions.

Usage:
    python jobs/derive_fundamentals_pit.py
    python jobs/derive_fundamentals_pit.py --symbols CBA.AU,BHP.AU
    python jobs/derive_fundamentals_pit.py --batch-size 50
    python jobs/derive_fundamentals_pit.py --write-batch-size 250
"""

import argparse
import asyncio
import logging
from datetime import date

import asyncpg

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.fundamentals_pit import (
    DEFAULT_PIT_BATCH_SIZE,
    DEFAULT_PIT_WRITE_BATCH_SIZE,
    MAX_PIT_BATCH_SIZE,
    MAX_PIT_WRITE_BATCH_SIZE,
    FundamentalsPitCounts,
    refresh_fundamentals_pit,
)
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def _refresh_with_monitor(
    conn: asyncpg.Connection,
    *,
    monitor: JobMonitor,
    as_of: date,
    symbols: list[str] | None,
    batch_size: int,
    write_batch_size: int,
) -> FundamentalsPitCounts:
    """Keep the durable job record aligned with each committed write chunk."""

    def record_progress(rows: int) -> None:
        monitor.rows_written = rows

    return await refresh_fundamentals_pit(
        conn,
        as_of=as_of,
        symbols=symbols,
        batch_size=batch_size,
        write_batch_size=write_batch_size,
        on_rows_committed=record_progress,
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_PIT_BATCH_SIZE,
        help=f"symbols per bounded DB batch (1-{MAX_PIT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--write-batch-size",
        type=int,
        default=DEFAULT_PIT_WRITE_BATCH_SIZE,
        help=f"PIT rows per bounded UPSERT command (1-{MAX_PIT_WRITE_BATCH_SIZE})",
    )
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
            counts = await _refresh_with_monitor(
                conn,
                monitor=monitor,
                as_of=today,
                symbols=symbols,
                batch_size=args.batch_size,
                write_batch_size=args.write_batch_size,
            )
            if counts["rows"] == 0:
                raise RuntimeError(
                    "no PIT rows derived — "
                    f"scanned={counts['symbols_scanned']} "
                    f"source={counts['source_symbols']} "
                    f"no_pit={counts['symbols_without_pit']} "
                    f"no_source={counts['symbols_without_source']}. "
                    "Confirm yearly income/balance source coverage and run "
                    "sync_financial_statements if it is absent."
                )
        log.info(
            "derive_fundamentals_pit done — "
            f"batches={counts['batches']} scanned={counts['symbols_scanned']} "
            f"source={counts['source_symbols']} symbols={counts['symbols']} "
            f"no_pit={counts['symbols_without_pit']} "
            f"no_source={counts['symbols_without_source']} rows={counts['rows']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
