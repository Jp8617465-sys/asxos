#!/usr/bin/env python
"""
Daily regulatory ingest.

Fetches two RSS sources, parses each, UPSERTs into regulatory_events.
Per-source failure is logged, then gated by assert_partial_success with
threshold=0.5: with N=2 sources, 2/2 or 1/2 healthy passes (ratio >= 0.5);
0/2 hard-fails the run. When a source hard-fails but the run still clears the
threshold, _degraded_note attaches a one-line marker to the success run's
job_runs.error_message so check_cron_health surfaces the otherwise-hidden dead
feed (fail-loud, CLAUDE.md #10).

Sources:
  RBA      — https://www.rba.gov.au/rss/rss-cb-media-releases.xml (RSS 1.0/RDF)
  Treasury — https://treasury.gov.au/news/rss (RSS 2.0)

ATO was removed: the ATO site redesign killed the old Newsroom feed URL
(https://www.ato.gov.au/Newsroom/Newsroom-feeds/ is now a dead HTML index
page) and there is no stable public replacement — RSS only exists behind a
per-user subscription wizard. Re-add conditions are tracked in
docs/next-session-backlog.md.

Usage:
    python jobs/ingest_regulatory.py
"""
import argparse
import asyncio
import logging
from collections.abc import Sequence
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


# ATO is deliberately absent: its old Newsroom feed URL is a dead HTML index
# page after the ATO site redesign, and there is no stable public replacement
# (RSS only exists behind a per-user subscription wizard). Re-add conditions
# are tracked in docs/next-session-backlog.md.
SOURCES: list[SourceSpec] = [
    SourceSpec("RBA", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "monetary_policy"),
    SourceSpec("Treasury", "https://treasury.gov.au/news/rss", "other"),
]

# gov.au WAFs 403 default python User-Agents: from Render, Treasury was
# blocked on every run while RBA happened to pass without a UA. A mainstream
# desktop-browser UA plus an explicit feed Accept header is the cheap,
# portable mitigation — final confirmation is only possible from Render
# egress, since the WAF behaviour differs by client IP reputation.
_CLIENT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/rdf+xml, application/atom+xml, "
        "application/xml;q=0.9, */*;q=0.8"
    ),
}


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


def _degraded_note(
    sources: Sequence[SourceSpec], totals: Sequence[int | None]
) -> str | None:
    """Return a one-line degraded note when a source hard-failed (returned
    ``None``) but the run still cleared the partial-success threshold — else
    ``None``.

    A ``None`` total means that source's fetch/parse failed after retry (see
    ``_fetch_and_upsert``); because RBA alone clears the 0.5 threshold the run
    is still recorded ``success``, so a dead source (e.g. Treasury WAF-403 from
    Render egress) would otherwise vanish. This note rides
    ``job_runs.error_message`` on the success row and is surfaced daily by
    ``check_cron_health`` (fail-loud, CLAUDE.md #10). ``0`` rows is a healthy
    slow-news-day outcome, not a dead feed — only ``None`` counts as dead.
    """
    dead = [s.name for s, t in zip(sources, totals, strict=True) if t is None]
    if not dead:
        return None
    return (
        f"degraded: {len(dead)}/{len(sources)} source(s) returned no data "
        f"after retry (dead feed): {dead}"
    )


async def main() -> None:
    today = date.today()
    await init_pool()
    try:
        async with JobMonitor(
            job_name="ingest_regulatory",
            as_of=today,
            healthcheck_url=settings.healthcheck_url_ingest_regulatory,
        ) as monitor:
            async with httpx.AsyncClient(headers=_CLIENT_HEADERS) as client:
                totals = await asyncio.gather(
                    *[_fetch_and_upsert(client, s) for s in SOURCES]
                )

            # Threshold 0.5 with N=2 sources: 2/2 (1.0) and 1/2 (0.5) pass
            # the >= comparison; 0/2 hard-fails. One feed may be down without
            # aborting the run, but both failing means nothing ingested and
            # the job must fail loudly. Per-source SLA tracking is a separate
            # (deferred) improvement.
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
            monitor.note = _degraded_note(SOURCES, totals)
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
