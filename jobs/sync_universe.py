#!/usr/bin/env python
"""
Sync ASX universe from EODHD exchange symbol list.

Writes Common Stock entries to the universe table (UPSERT).
Run daily — idempotent.

Usage:
    python jobs/sync_universe.py
"""
import asyncio
import logging
from datetime import date

import httpx

from asxos.config import settings
from asxos.db import close_pool, init_pool, acquire
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

EODHD_BASE = "https://eodhd.com/api"


async def fetch_exchange_symbols() -> list[dict]:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{EODHD_BASE}/exchange-symbol-list/AU",
            params={"api_token": settings.eodhd_api_key, "fmt": "json"},
        )
        r.raise_for_status()
        return r.json()


def to_symbol(code: str) -> str:
    return code if "." in code else f"{code}.AU"


async def main() -> None:
    today = date.today()
    await init_pool()

    async with JobMonitor(
        job_name="sync_universe",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_universe,
    ) as monitor:
        log.info("Fetching exchange symbol list from EODHD...")
        raw = await fetch_exchange_symbols()

        rows = [
            (
                to_symbol(s["Code"]),
                s.get("Name") or "",
                s.get("Sector") or "",
                s.get("Currency") or "AUD",
            )
            for s in raw
            if s.get("Type") == "Common Stock"
        ]

        log.info(f"Upserting {len(rows)} symbols into universe...")
        async with acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO universe (symbol, name, sector, currency)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (symbol) DO UPDATE SET
                    name       = EXCLUDED.name,
                    sector     = EXCLUDED.sector,
                    updated_at = NOW()
                """,
                rows,
            )

        monitor.rows_written = len(rows)
        log.info(f"sync_universe done: {len(rows)} rows, as_of={today}")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
