#!/usr/bin/env python
"""
Daily news ingest — M14a.

Fetches article-level news from EODHD /news for each current holding,
UPSERTs into holding_news.  One bad ticker does not abort the run
(return_exceptions=True gather pattern; note sync_fundamentals.py gathers
WITHOUT return_exceptions, so its `r is True` predicate is safe there and
would NOT be safe here — see the predicate comment in main()).

The run as a whole still hard-fails when fewer than 75% of symbols succeed
(``assert_partial_success`` in ``main()``); "one bad ticker" is the tolerated
case, not "most tickers".

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/ingest_news.py

Regulatory firewall: raises RuntimeError if ASXOS_PERSONAL_USE != "1"
(Part 0 Q1 / s766B Corporations Act 2001).
"""
import asyncio
import logging
import os
from datetime import date, timedelta

# asxos.ingestion.news is stdlib + asyncpg only — safe at module level.
from asxos.ingestion.news import ParseStats, parse_news_response_with_stats, upsert_news
from asxos.ingestion.symbols import eodhd_symbol
from asxos.jobs._helpers import assert_partial_success
from asxos.redaction import redact_secrets

# ---------------------------------------------------------------------------
# Module-level stubs — tests patch these at the jobs.ingest_news namespace.
# Pattern mirrors asxos/brief/compose.py (acquire = None + globals() lazy).
# ---------------------------------------------------------------------------

# DB + monitoring: None stubs; production main() lazy-imports from asxos.db
acquire = None  # type: ignore[assignment]
init_pool = None  # type: ignore[assignment]
close_pool = None  # type: ignore[assignment]
JobMonitor = None  # type: ignore[assignment]

# get_client: try real import at module load; fall back to a no-op stub if
# asxos.ingestion.eodhd cannot be imported (test envs without `tenacity`).
# Tests that care about get_client always patch it explicitly.
try:
    from asxos.ingestion.eodhd import get_client  # type: ignore[assignment]
except (ImportError, ModuleNotFoundError):  # test env missing tenacity / httpx
    def get_client():  # type: ignore[assignment]
        """No-op stub used only when eodhd dependencies are unavailable."""
        return None

# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def _fetch_and_upsert(
    client,
    symbol: str,
    from_date: str,
    holdings: set[str],
    conn,
) -> tuple[int, ParseStats] | None:
    """Fetch news for one symbol and upsert to holding_news.

    Returns ``(rows_written, stats)`` on success — including a legitimate
    ``(0, stats)`` when the symbol genuinely had no articles in the window —
    and ``None`` on failure.

    The stats ride along because ``main()`` is the only place that can decide
    whether the RUN was degraded: a single symbol's malformed envelope is a
    per-symbol log line, but the job-level note (persisted to
    ``job_runs.error_message``, read by the brief's freshness gate and by
    check_cron_health) must aggregate across symbols. Returning a bare int
    meant the counters existed but died inside this function — counted in
    memory, invisible to every consumer that matters.

    The failure sentinel MUST NOT be ``0`` or ``(0, ...)`` for a failed fetch.
    Returning a zero for failure makes "every symbol errored" indistinguishable
    from "a quiet news day", and the aggregate guard in ``main()`` keys off
    exactly that distinction. Catching here (rather than raising) is still
    deliberate: one bad ticker must not abort the gather across all holdings.

    Scope limit — a returned ``0`` is still not proof of a quiet day, but both
    silent paths that used to produce one are now counted rather than invisible.
    ``news_for_symbol`` no longer coerces a non-list payload to ``[]``: the
    parser classifies it as one malformed unit, so an error envelope is no longer
    arithmetically identical to a quiet response. Articles whose tags resolve to
    no held symbol are counted in ``dropped_no_match``, and every remaining drop
    path (stale, malformed, duplicate) now has its own counter.

    The sentinel itself still cannot distinguish them — a row count never could.
    What changed is that the counters are now READ: the warning below fires on
    ANY drop, not only ``dropped_no_match``, so a malformed-only or
    duplicate-only batch is visible instead of passing as a quiet day.

    The 2026-08 zero-row incident had two candidate causes, and this job now
    closes both: the request asked for a namespace EODHD does not serve
    (``HUBS.NYSE`` rather than ``HUBS.US``), and the parser's ``.AU`` guess could
    not match a US listing. Which one actually fired was never established —
    both yield a green run with zero rows — and only a live probe would settle
    it (``docs/market-trends-report-2026-08-05.md`` §11 fix #4).
    """
    try:
        # Translate to the vendor namespace on the way out, store under the
        # project symbol on the way back — the same shape as
        # asxos/ingestion/prices.py::fetch_and_upsert_us_symbol. This job was the
        # one per-symbol EODHD path that skipped the remap, so every US holding
        # was requested as e.g. HUBS.NYSE, which EODHD does not address (.US).
        raw = await client.news_for_symbol(
            eodhd_symbol(symbol), limit=10, from_date=from_date
        )
        items, stats = parse_news_response_with_stats(
            raw, holdings=holdings, as_of=date.today(), requested_symbol=symbol
        )
        dropped_total = (
            stats.dropped_no_match
            + stats.dropped_stale
            + stats.dropped_malformed
            + stats.dropped_duplicate
        )
        if dropped_total:
            # Gate on ANY drop, not just no-match. Gating on `dropped_no_match`
            # alone meant a malformed-only or duplicate-only batch logged
            # nothing, persisted nothing, and still reported success — the
            # counters existed with no consumer, so a loss that WAS counted in
            # memory stayed invisible in operation.
            #
            # Everything interpolated is bounded: counts are ints, and tags are
            # already stripped of non-printables and capped at 32 chars each,
            # first 10 (asxos/ingestion/news.py). No unbounded vendor string
            # reaches this line.
            log.warning(
                "ingest_news: %s — %d/%d articles dropped "
                "(no_match=%d stale=%d malformed=%d duplicate=%d); tags seen: %s",
                symbol, dropped_total, stats.fetched,
                stats.dropped_no_match, stats.dropped_stale,
                stats.dropped_malformed, stats.dropped_duplicate,
                ", ".join(stats.unmatched_tags) or "(none)",
            )
        return await upsert_news(conn, items), stats
    except Exception as exc:
        # redact_secrets at the sink, matching jobs/sync_prices.py:198. The
        # EODHD client already sanitises HTTPStatusError at source, so this is
        # defence in depth against that single point of failure (CWE-532).
        log.warning("ingest_news: %s failed: %s", symbol, redact_secrets(str(exc)))
        return None


async def main() -> None:
    # Regulatory firewall — MUST be the very first check, before any imports
    # that might fail in restricted environments.
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise RuntimeError(
            "ASXOS_PERSONAL_USE not set — refusing to ingest news. "
            "This job is for personal use only (s766B Corporations Act 2001)."
        )

    # Resolve module-level stubs: tests inject mocks (non-None); production
    # lazy-imports from asxos.db on first use.  _JobMonitor is resolved AFTER
    # the empty-holdings guard so the test that patches acquire/init_pool but
    # not JobMonitor still exits cleanly when there are no holdings.
    _acquire = globals()["acquire"]
    _init_pool = globals()["init_pool"]
    _close_pool = globals()["close_pool"]
    _get_client = globals()["get_client"]

    if _acquire is None:
        from asxos.db import (  # type: ignore[assignment]
            acquire as _acquire,
        )
        from asxos.db import (
            close_pool as _close_pool,
        )
        from asxos.db import (
            init_pool as _init_pool,
        )

    today = date.today()
    await _init_pool()
    try:
        async with _acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT symbol FROM current_holdings")
        symbols = [r["symbol"] for r in rows]

        if not symbols:
            log.info("No holdings — skipping news ingest")
            return

        # Resolve JobMonitor only when we know we need it (symbols > 0).
        _JobMonitor = globals()["JobMonitor"]
        if _JobMonitor is None:
            from asxos.jobs.utils.job_monitor import (
                JobMonitor as _JobMonitor,  # type: ignore[assignment]
            )

        client = _get_client()
        from_date = (today - timedelta(days=1)).isoformat()
        holdings = set(symbols)

        log.info("ingest_news: fetching for %d holdings, from_date=%s", len(symbols), from_date)

        async with _JobMonitor(
            job_name="ingest_news",
            as_of=today,
            healthcheck_url=os.environ.get("HEALTHCHECK_URL_INGEST_NEWS", ""),
        ) as monitor:
            # Prune stale rows before the ingest
            async with _acquire() as conn:
                deleted = await conn.fetchval(
                    "WITH deleted AS ("
                    "  DELETE FROM holding_news"
                    "  WHERE published_at < (NOW() - INTERVAL '7 days')::DATE"
                    "  RETURNING id"
                    ") SELECT COUNT(*) FROM deleted"
                )
                if deleted:
                    log.info("ingest_news: pruned %d stale rows", deleted)

            async with _acquire() as conn:
                results = await asyncio.gather(
                    *[_fetch_and_upsert(client, s, from_date, holdings, conn)
                      for s in symbols],
                    return_exceptions=True,
                )

            # Threshold 0.75 — each holding matters (N is small, typically
            # 5-20). 25% symbol failure rate is a real outage worth a
            # hard-fail rather than silently writing stale-for-most-symbols
            # sentiment that feeds tomorrow's build_portfolio.
            # Do NOT re-add a `and r >= 0` clause — every int satisfies it, so
            # the guard became a no-op that scored fully-failing runs as 100%
            # healthy (docs/market-trends-report-2026-08-05.md §1). The predicate
            # must also be a positive TYPE test rather than `r is not None`:
            # under return_exceptions=True, an exception object is not None and
            # would pass. See asxos/jobs/_helpers.py for the general rule.
            n_ok = assert_partial_success(
                results,
                is_ok=lambda r: isinstance(r, tuple),
                threshold=0.75,
                label="ingest_news",
                identifiers=symbols,
                allow_empty=False,
            )
            oks = [r for r in results if isinstance(r, tuple)]
            written = sum(w for w, _ in oks)
            # Count everything the predicate rejected — None (caught failure) and
            # BaseException (escaped) alike. Counting only BaseException reports
            # "0 errors" for every real failure, since the worker never raises.
            errors = len(results) - len(oks)
            agg_malformed = sum(st.dropped_malformed for _, st in oks)
            agg_no_match = sum(st.dropped_no_match for _, st in oks)
            monitor.rows_written = written
            log.info(
                "ingest_news done: %d rows written, %d/%d symbols healthy, %d errors",
                written, n_ok, len(symbols), errors,
            )

            # Surface the states that clear the threshold but still mean "no news
            # reached the table". JobMonitor persists `note` into
            # job_runs.error_message on a SUCCESS row, which is the field
            # check_cron_health's degraded-run check reads — the only way a
            # green-but-empty run becomes visible without inspecting the table.
            #
            # This is the load-bearing half for the incident that motivated it.
            # A zero-row run needs NO exception to occur: either the vendor
            # returns nothing for the symbol we asked about, or every article it
            # does return resolves to no held symbol. Both were possible before
            # this change — a wrong request namespace and a ".AU"-guessing
            # symbol filter — both are fixed, and neither was ever proven to be
            # the one that fired, because they produce the identical artefact.
            # The predicate above legitimately passes a 0 in every case, so the
            # sentinel fix alone cannot catch it; this note does.
            # error_message is LOAD-BEARING IN BOTH DIRECTIONS, and this is
            # the only site that writes it for this job:
            #   - check_cron_health's degraded check alerts on it being NON-NULL;
            #   - asxos/brief/compose.py::_news_ingest_fresh requires it to be
            #     NULL on the LATEST run before the brief renders news.
            # So a note attached for a benign reason does not merely add noise —
            # it silently suppresses a brief section AND pages.
            #
            # That is why the old `if written == 0` branch is GONE: it fired on
            # every genuinely quiet news day, which is the same
            # row-count-as-health confusion that produced the incident (rule 2
            # of docs/market-trends-report-2026-08-05.md §1). A quiet day is a
            # healthy run. Only real degradation may write here:
            #   - a symbol's fetch failed outright (errors);
            #   - the vendor sent something we could not parse (malformed —
            #     includes a non-list error envelope, counted as one unit);
            #   - articles arrived and resolved to no held symbol (no_match —
            #     the namespace-fault signature of the incident itself).
            # Stale and duplicate drops are the time window and dedup working
            # as designed; they are logged per-symbol above, never noted here.
            # Counts only — no vendor string reaches this persisted field.
            notes = []
            if errors:
                notes.append(f"{errors}/{len(symbols)} symbols failed")
            if agg_malformed:
                notes.append(f"malformed={agg_malformed}")
            if agg_no_match:
                notes.append(f"no_match={agg_no_match}")
            if notes:
                monitor.note = "ingest_news degraded: " + "; ".join(notes)
    finally:
        await _close_pool()


if __name__ == "__main__":
    asyncio.run(main())
