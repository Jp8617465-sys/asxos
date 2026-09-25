#!/usr/bin/env python
"""
Daily regulatory ingest.

Fetches one RSS source (RBA), parses, UPSERTs into regulatory_events.
Per-source failure is logged, then gated by assert_partial_success with
threshold=1.0: with N=1 source, only 1/1 (ratio 1.0) passes; 0/1 hard-fails
the run outright — at N=1 there is no partial-success ratio in between.
_degraded_note (see its docstring) exists for N>1, where some sources can
fail while the run still clears the threshold and is recorded success; it
attaches a one-line marker to that success run's job_runs.error_message so
check_cron_health surfaces the otherwise-hidden dead feed (fail-loud,
CLAUDE.md #10). It is presently dormant with SOURCES at N=1.

Sources:
  RBA — https://www.rba.gov.au/rss/rss-cb-media-releases.xml (RSS 1.0/RDF)

ATO was removed: the ATO site redesign killed the old Newsroom feed URL
(https://www.ato.gov.au/Newsroom/Newsroom-feeds/ is now a dead HTML index
page) and there is no stable public replacement — RSS only exists behind a
per-user subscription wizard. Re-add conditions are tracked in
docs/next-session-backlog.md.

Treasury was also removed (2026-07-18) — see the SOURCES comment below for
the full removal history.

Usage:
    python jobs/ingest_regulatory.py
"""
import argparse
import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from asxos import clock
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
#
# Treasury is deliberately absent: gov.au's WAF returns 403 to non-browser
# HTTP clients regardless of header content. A browser User-Agent + Accept
# header mitigation (added 2026-07-02, see _CLIENT_HEADERS below) ran in
# production for 13+ consecutive days (2026-07-04 to 2026-07-17) with zero
# Treasury rows ingested — the identical failure signature as before the
# mitigation. This is consistent with a TLS-fingerprint / IP-reputation
# block, which no HTTP-header change can defeat; the known workarounds
# (TLS-impersonating clients, headless-browser automation) are new external
# dependencies, out of scope for a pure-code fix. No stable alternate public
# Treasury RSS endpoint was found. Re-add conditions are tracked in
# docs/next-session-backlog.md.
SOURCES: list[SourceSpec] = [
    SourceSpec("RBA", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "monetary_policy"),
]

# Historical: added 2026-07-02 as a mitigation attempt for the (now-removed)
# Treasury feed's WAF block. Confirmed 2026-07-18 that header-only spoofing
# did not defeat it (13+ live Render days, zero effect) — see the SOURCES
# comment above. RBA, the sole remaining source, passes with or without
# these headers; they're kept as a harmless, generically well-behaved
# client identity, not because RBA requires them.
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
    """Returns NEW rows on success (0 for "nothing we had not already stored"),
    or None on hard failure (fetch / parse exception after retry).

    **New rows, not rows touched (E-20).** This used to return the number of
    events handed to the UPSERT, which for a feed re-serving the same item every
    night was 1 every night while `regulatory_events` did not grow — and that
    number is what `monitor.rows_written` carries into the digest. The re-touch
    count is still reported, at INFO, where a steady state belongs: it is a fact
    about the feed's cadence, not about this job's health, and `monitor.note` is
    an alerting channel (the #368 lesson).

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
        counts = await upsert_events(conn, events)
    log.info(
        f"{source.name}: {counts.inserted} new, {counts.updated} re-touched "
        f"({counts.presented} parsed)"
    )
    return counts.inserted


def _degraded_note(
    sources: Sequence[SourceSpec], totals: Sequence[int | None]
) -> str | None:
    """Return a one-line degraded note when a source hard-failed (returned
    ``None``) but the run still cleared the partial-success threshold — else
    ``None``.

    A ``None`` total means that source's fetch/parse failed after retry (see
    ``_fetch_and_upsert``). This only has an effect when the caller's
    threshold lets some sources fail without the run itself hard-failing —
    e.g. the pre-2026-07-18 N=2/threshold=0.5 config, where a lone Treasury
    WAF-403 would otherwise vanish behind a ``success`` job run. At the
    current SOURCES/threshold=1.0 (see the module docstring), a hard-failed
    source always breaches the threshold first, so this function is
    presently dormant in production — exercised directly by tests, not by
    ``main()`` — and reactivates if a second source is re-added at
    threshold < 1.0. When live, this note rides ``job_runs.error_message``
    on the success row and is surfaced daily by ``check_cron_health``
    (fail-loud, CLAUDE.md #10). ``0`` rows is a healthy slow-news-day
    outcome, not a dead feed — only ``None`` counts as dead.
    """
    dead = [s.name for s, t in zip(sources, totals, strict=True) if t is None]
    if not dead:
        return None
    return (
        f"degraded: {len(dead)}/{len(sources)} source(s) returned no data "
        f"after retry (dead feed): {dead}"
    )


async def main() -> None:
    today = clock.today()
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

            # Threshold 1.0 with N=1 source (RBA only — Treasury removed 2026-07-18,
            # see SOURCES comment above): the only two possible ratios at N=1 are 0/1
            # and 1/1, so 1.0 is the only threshold value that expresses "the single
            # remaining source is mandatory" rather than a stale carry-over from when
            # N=2 partial credit was legitimate. Any future re-add of a second source
            # (e.g. ATO, ASIC/ASX) MUST come with a deliberate re-review of this
            # constant — a stale <1.0 threshold silently tolerating 1 dead source out
            # of N is exactly how the Treasury feed stayed invisible for weeks.
            n_ok = assert_partial_success(
                totals,
                # Positive type test, not `r is not None`: extensionally
                # identical today (the worker returns only int | None), but it
                # stays correct if this gather ever adopts
                # return_exceptions=True — under which an exception object is
                # not None and would be scored as a success. Same predicate
                # class as the ingest_news false-green defect.
                is_ok=lambda r: isinstance(r, int),
                threshold=1.0,
                label="ingest_regulatory",
                identifiers=[s.name for s in SOURCES],
                allow_empty=False,  # SOURCES is hardcoded; empty == bug
            )
            # NEW rows only (E-20). A run that re-touches everything it already
            # had now reports 0 rather than the feed's item count, so a digest
            # cannot read a steady state as growth.
            written = sum(t for t in totals if t is not None)
            monitor.rows_written = written
            monitor.note = _degraded_note(SOURCES, totals)
            log.info(
                f"ingest_regulatory done: {written} new events "
                f"across {n_ok}/{len(SOURCES)} healthy sources"
            )
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()  # currently no args
    asyncio.run(main())
