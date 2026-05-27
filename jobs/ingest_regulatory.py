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
from asxos.jobs._helpers import assert_partial_success
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


async def _fetch_and_upsert(client: httpx.AsyncClient, source: SourceSpec) -> int | None:
    """Returns rows ingested on success (including 0 for "no new events"),
    or None on hard failure (fetch / parse exception after retry).

    The distinction matters: 0 is a healthy outcome on a slow news day; None
    is a real upstream problem that should count against the success
    threshold via assert_partial_success(is_ok=lambda r: r is not None).

    One retry with 2s backoff before returning None — converts most transient
    503s/timeouts into successes so the threshold guard only fires on real
    outages.
    """
    for attempt in (1, 2):
        try:
            r = await client.get(source.url, timeout=30.0, follow_redirects=True)
            r.raise_for_status()
            break
        except Exception as exc:
            if attempt == 2:
                log.warning(f"{source.name} fetch failed after 2 attempts: {exc}")
                return None
            log.info(f"{source.name} fetch attempt {attempt} failed: {exc} — retrying")
            await asyncio.sleep(2)
    try:
        events = parse_rss(r.content, source=source.name, default_kind=source.default_kind)
    except Exception as exc:
        log.warning(f"{source.name} parse failed: {exc}")
        return None
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

            # Threshold 0.5 (not 0.75) because N=3 sources: at 0.75 even
            # 2/3 (0.667) would hard-fail, which is too brittle for RSS feeds.
            # 0.5 allows one source to die without aborting; 2-of-3 failures
            # is treated as a real outage. Per-source SLA tracking is a
            # separate (deferred) improvement.
            n_ok = assert_partial_success(
                totals,
                is_ok=lambda r: r is not None,
                threshold=0.5,
                label="ingest_regulatory",
                identifiers=[s.name for s in SOURCES],
                allow_empty=False,  # SOURCES is hardcoded; empty == bug
            )
            written = sum(t for t in totals if t is not None)
            monitor.rows_written = written
            log.info(
                f"ingest_regulatory done: {written} total events "
                f"across {n_ok}/{len(SOURCES)} healthy sources"
            )
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()  # currently no args
    asyncio.run(main())
