#!/usr/bin/env python
"""
Weekly fundamentals sync from EODHD.

Iterates every active universe symbol. Failure on one symbol is logged
and skipped — it does not abort the run. Run is still marked success
as long as at least one symbol writes.

Usage:
    python jobs/sync_fundamentals.py
    python jobs/sync_fundamentals.py --symbol BHP.AU   # single symbol
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.fundamentals import fetch_and_upsert_fundamentals
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

_CONCURRENCY = 5  # EODHD fundamentals endpoint is heavier than price endpoint


async def sync_symbol(symbol: str, as_of: date) -> bool:
    """Returns True on success, False on failure. Never raises."""
    client = get_client()
    try:
        async with acquire() as conn:
            await fetch_and_upsert_fundamentals(symbol, as_of, client, conn)
        return True
    except Exception as exc:
        log.warning(f"  {symbol}: failed — {exc}")
        return False


async def main(single_symbol: str | None) -> None:
    today = date.today()
    await init_pool()

    if single_symbol:
        symbols = [single_symbol]
    else:
        async with acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol FROM universe WHERE is_active ORDER BY symbol"
            )
        symbols = [r["symbol"] for r in rows]

    log.info(f"Syncing fundamentals for {len(symbols)} symbols...")

    async with JobMonitor(
        job_name="sync_fundamentals",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_fundamentals,
    ) as monitor:
        sem = asyncio.Semaphore(_CONCURRENCY)

        async def bounded(sym: str) -> bool:
            async with sem:
                return await sync_symbol(sym, today)

        results = await asyncio.gather(*[bounded(s) for s in symbols])
        successes = sum(results)
        failures = len(results) - successes

        monitor.rows_written = successes
        log.info(
            f"sync_fundamentals done — "
            f"ok={successes} failed={failures} total={len(symbols)}"
        )

    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=None, help="Single symbol to sync (e.g. BHP.AU)")
    asyncio.run(main(parser.parse_args().symbol))
