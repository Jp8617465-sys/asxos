#!/usr/bin/env python
"""
Sync the research-store corporate-actions table (rs_corporate_actions) from EODHD —
dividends (+ AU franking) and splits for every security in rs_security_master.

Survivorship-free: iterates the full security master (active + delisted) by default.
SEPARATE from production tables — never touches `universe` or `prices`. Run weekly,
AFTER sync_security_master (it has no symbols to iterate until that has run).

Usage:
    python jobs/sync_corporate_actions.py                 # all of rs_security_master
    python jobs/sync_corporate_actions.py --active-only   # is_active = true only
    python jobs/sync_corporate_actions.py --limit 50      # first N symbols (smoke test)
    python jobs/sync_corporate_actions.py --symbols CBA.AU,BHP.AU
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.corporate_actions import refresh_corporate_actions
from asxos.ingestion.eodhd import get_client
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def _load_symbols(conn, *, active_only: bool, limit: int | None) -> list[str]:
    sql = "SELECT symbol FROM rs_security_master"
    if active_only:
        sql += " WHERE is_active"
    sql += " ORDER BY symbol"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = await conn.fetch(sql)
    return [r["symbol"] for r in rows]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    args = parser.parse_args()

    today = date.today()
    await init_pool()
    client = get_client()

    async with JobMonitor(
        job_name="sync_corporate_actions",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_corporate_actions,
    ) as monitor:
        async with acquire() as conn:
            if args.symbols:
                symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
            else:
                symbols = await _load_symbols(
                    conn, active_only=args.active_only, limit=args.limit
                )
            # Hard-fail loudly if the dependency hasn't run — no silent no-op.
            if not symbols:
                raise RuntimeError(
                    "no symbols to process — rs_security_master is empty. "
                    "Run sync_security_master first."
                )
            log.info(f"sync_corporate_actions start — {len(symbols)} symbols")
            counts = await refresh_corporate_actions(client, conn, symbols)

        monitor.rows_written = counts["dividends"] + counts["splits"]
        log.info(
            "sync_corporate_actions done — "
            f"symbols={counts['symbols']} with_actions={counts['symbols_with_actions']} "
            f"dividends={counts['dividends']} splits={counts['splits']} failed={counts['failed']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
