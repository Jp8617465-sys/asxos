#!/usr/bin/env python
"""
Daily sentiment aggregation — M14b REV-K.

REV-K pivot (2026-05-24): EODHD /sentiments has no ASX coverage on the
Fundamentals Data Feed plan tier. Aggregates daily mean polarity from
holding_news.sentiment_polarity → signal_sentiment.  7-day rolling window;
idempotent on re-run (UPSERT ON CONFLICT).

Architecture:
    ingest_news (20:57 UTC) → holding_news.sentiment_polarity
    ingest_sentiment (21:02 UTC) → signal_sentiment (SQL aggregation)

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/ingest_sentiment.py

Regulatory firewall: raises RuntimeError if ASXOS_PERSONAL_USE != "1"
(Part 0 Q1 / s766B Corporations Act 2001).
"""
import argparse
import asyncio
import logging
import os
from datetime import date

from asxos.jobs._helpers import UpstreamBlocked

# ---------------------------------------------------------------------------
# Module-level stubs — tests patch these at the jobs.ingest_sentiment namespace.
# Pattern mirrors jobs/ingest_news.py exactly.
# ---------------------------------------------------------------------------

# DB + monitoring: None stubs; production main() lazy-imports from asxos.db
acquire = None  # type: ignore[assignment]
init_pool = None  # type: ignore[assignment]
close_pool = None  # type: ignore[assignment]
JobMonitor = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def _upstream_ok(conn, today: date) -> bool:
    """Return True if ingest_news had a successful run within the last 24 hours.

    Used as a soft pipeline guard: missing ingest_news run doesn't abort this job
    (the 7-day rolling window still covers prior days), but it is logged as a WARNING.
    """
    row = await conn.fetchrow(
        """
        SELECT 1 FROM job_runs
        WHERE job_name = 'ingest_news'
          AND status = 'success'
          AND as_of >= $1 - INTERVAL '1 day'
        """,
        today,
    )
    return row is not None


async def _aggregate_from_news(conn) -> int:
    """Aggregate daily mean polarity from holding_news → signal_sentiment.

    Uses a 7-day lookback window; UPSERT is idempotent on re-run.
    CROSS JOIN LATERAL unnests the JSONB symbols array so each symbol in a
    cross-holding article gets its own row in signal_sentiment.

    source_layer = 'news_polarity' (not 'direct') to distinguish from any
    future EODHD /sentiments coverage if the plan tier changes.

    Returns the number of rows written (inserted + updated).
    """
    rows = await conn.fetch(
        """
        INSERT INTO signal_sentiment
            (symbol, as_of, mention_count, sentiment_normalised,
             source_layer, source_metadata)
        SELECT
            sym.value                        AS symbol,
            hn.published_at                  AS as_of,
            COUNT(*)::INTEGER                AS mention_count,
            AVG(hn.sentiment_polarity)::NUMERIC(8,6) AS sentiment_normalised,
            'news_polarity'                  AS source_layer,
            jsonb_build_object(
                'source',                  'news_polarity',
                'ingestion_window_days',   7,
                'article_count_per_symbol', true
            )                                AS source_metadata
        FROM holding_news hn
        CROSS JOIN LATERAL jsonb_array_elements_text(hn.symbols) AS sym(value)
        WHERE hn.sentiment_polarity IS NOT NULL
          AND hn.published_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY sym.value, hn.published_at
        ON CONFLICT (symbol, as_of) DO UPDATE SET
            mention_count        = EXCLUDED.mention_count,
            sentiment_normalised = EXCLUDED.sentiment_normalised,
            source_metadata      = EXCLUDED.source_metadata,
            ingested_at          = NOW()
        RETURNING symbol
        """,
    )
    return len(rows)


async def main(allow_stale_upstream: bool = False) -> None:
    # Regulatory firewall — MUST be the very first check.
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise RuntimeError(
            "ASXOS_PERSONAL_USE not set — refusing to ingest sentiment. "
            "This job is for personal use only (s766B Corporations Act 2001)."
        )

    # Resolve module-level stubs: tests inject mocks (non-None); production
    # lazy-imports from asxos.db on first use.  _JobMonitor is resolved AFTER
    # the empty-holdings guard so a test that patches acquire/init_pool but
    # not JobMonitor still exits cleanly when there are no holdings.
    _acquire = globals()["acquire"]
    _init_pool = globals()["init_pool"]
    _close_pool = globals()["close_pool"]

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
            log.info("No holdings — skipping sentiment aggregation")
            return

        # Resolve JobMonitor only when we know we need it (symbols > 0).
        _JobMonitor = globals()["JobMonitor"]
        if _JobMonitor is None:
            from asxos.jobs.utils.job_monitor import (
                JobMonitor as _JobMonitor,  # type: ignore[assignment]
            )

        async with _JobMonitor(
            job_name="ingest_sentiment",
            as_of=today,
            healthcheck_url=os.environ.get("HEALTHCHECK_URL_INGEST_SENTIMENT", ""),
            override_reason=(
                "operator: --allow-stale-upstream" if allow_stale_upstream else None
            ),
        ) as monitor:
            # Upstream check is inside JobMonitor so UpstreamBlocked records
            # status='blocked' (P0-2). Split into two acquires — the previous
            # code held one connection across the entire aggregation runtime.
            async with _acquire() as conn:
                upstream_ok = await _upstream_ok(conn, today)

            if not upstream_ok:
                if not allow_stale_upstream:
                    raise UpstreamBlocked(
                        "ingest_news has no success run in last 24h; refusing "
                        "to aggregate sentiment on stale upstream. Use "
                        "--allow-stale-upstream for a one-off manual override."
                    )
                log.warning(
                    "Proceeding on stale upstream by explicit --allow-stale-upstream "
                    "(recorded in job_runs.override_reason)."
                )

            async with _acquire() as conn:
                written = await _aggregate_from_news(conn)
            monitor.rows_written = written
            log.info("ingest_sentiment done: %d rows written", written)
    finally:
        await _close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-stale-upstream",
        action="store_true",
        help=(
            "Proceed even if ingest_news has no success run in last 24h. "
            "Manual operator override only — recorded in job_runs.override_reason. "
            "Cron services must NEVER pass this flag."
        ),
    )
    args = parser.parse_args()
    asyncio.run(main(allow_stale_upstream=args.allow_stale_upstream))
