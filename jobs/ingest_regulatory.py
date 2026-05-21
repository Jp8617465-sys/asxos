#!/usr/bin/env python
"""
Daily regulatory ingest.

Fetches three RSS-ish sources, parses each, UPSERTs into regulatory_events.
Failure of any single source is logged but does not abort the run — we
record success as long as one source ingests.

Sources (all RSS):
  ATO      — https://www.ato.gov.au/Newsroom/Newsroom-feeds/
  RBA      — https://www.rba.gov.au/rss/rss-cb-media-releases.xml
  Treasury — https://treasury.gov.au/news/rss

Usage:
    python jobs/ingest_regulatory.py
"""
import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import date

import httpx

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.regulatory import parse_rss, upsert_events
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceSpec:
    name: str
    url: str
    default_kind: str


SOURCES: list[SourceSpec] = [
    SourceSpec("ATO", "https://www.ato.gov.au/Newsroom/Newsroom-feeds/", "tax"),
    SourceSpec("RBA", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "monetary_policy"),
    SourceSpec("Treasury", "https://treasury.gov.au/news/rss", "other"),
]


async def _fetch_and_upsert(client: httpx.AsyncClient, source: SourceSpec) -> int:
    try:
        r = await client.get(source.url, timeout=30.0, follow_redirects=True)
        r.raise_for_status()
    except Exception as exc:
        log.warning(f"{source.name} fetch failed: {exc}")
        return 0
    try:
        events = parse_rss(r.content, source=source.name, default_kind=source.default_kind)
    except Exception as exc:
        log.warning(f"{source.name} parse failed: {exc}")
        return 0
    if not events:
        log.info(f"{source.name}: 0 events")
        return 0
    async with acquire() as conn:
        n = await upsert_events(conn, events)
    log.info(f"{source.name}: {n} events upserted")
    return n


async def main() -> None:
    today = date.today()
    await init_pool()
    try:
        async with JobMonitor(
            job_name="ingest_regulatory",
            as_of=today,
            healthcheck_url=settings.healthcheck_url_ingest_regulatory,
        ) as monitor:
            async with httpx.AsyncClient() as client:
                totals = await asyncio.gather(
                    *[_fetch_and_upsert(client, s) for s in SOURCES]
                )
            monitor.rows_written = sum(totals)
            log.info(f"ingest_regulatory done: {sum(totals)} total events across {len(SOURCES)} sources")
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()  # currently no args
    asyncio.run(main())
