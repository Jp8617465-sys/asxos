#!/usr/bin/env python
"""
Daily sentiment ingest — M14b.

Fetches daily aggregated sentiment from EODHD /sentiments for each
current holding, UPSERTs into signal_sentiment.  7-day lookback window
ensures rows are refreshed as EODHD updates its daily aggregation.

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/ingest_sentiment.py

Regulatory firewall: raises RuntimeError if ASXOS_PERSONAL_USE != "1"
(Part 0 Q1 / s766B Corporations Act 2001).
"""
import asyncio
import logging
import os
from datetime import date, timedelta

# asxos.ingestion.sentiment is stdlib + asyncpg only — safe at module level.
from asxos.ingestion.sentiment import parse_sentiment_response, upsert_sentiment

# ---------------------------------------------------------------------------
# Module-level stubs — tests patch these at the jobs.ingest_sentiment namespace.
# Pattern mirrors jobs/ingest_news.py exactly.
# ---------------------------------------------------------------------------

# DB + monitoring: None stubs; production main() lazy-imports from asxos.db
acquire = None  # type: ignore[assignment]
init_pool = None  # type: ignore[assignment]
close_pool = None  # type: ignore[assignment]
JobMonitor = None  # type: ignore[assignment]

# get_client: try real import at module load; fall back to a no-op stub if
# asxos.ingestion.eodhd cannot be imported (test envs without tenacity).
try:
    from asxos.ingestion.eodhd import get_client  # type: ignore[assignment]
except (ImportError, ModuleNotFoundError):  # test env missing tenacity / httpx
    def get_client():  # type: ignore[assignment]  # noqa: E301
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
    to_date: str,
    holdings: set[str],
    conn,
) -> int:
    """Fetch sentiment for one symbol and upsert to signal_sentiment.

    Catches all exceptions and returns 0 on failure so one bad ticker
    cannot abort the gather across all holdings.
    """
    try:
        raw = await client.sentiments_for_symbol(symbol, from_date=from_date, to_date=to_date)
        entries = parse_sentiment_response(raw, symbol=symbol, holdings=holdings)
        return await upsert_sentiment(conn, entries)
    except Exception as exc:
        log.warning("ingest_sentiment: %s failed: %s", symbol, exc)
        return 0


async def main() -> None:
    # Regulatory firewall — MUST be the very first check, before any imports
    # that might fail in restricted environments.
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise RuntimeError(
            "ASXOS_PERSONAL_USE not set — refusing to ingest sentiment. "
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
            close_pool as _close_pool,
            init_pool as _init_pool,
        )

    today = date.today()
    await _init_pool()
    try:
        async with _acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT symbol FROM current_holdings")
        symbols = [r["symbol"] for r in rows]

        if not symbols:
            log.info("No holdings — skipping sentiment ingest")
            return

        # Resolve JobMonitor only when we know we need it (symbols > 0).
        _JobMonitor = globals()["JobMonitor"]
        if _JobMonitor is None:
            from asxos.jobs.utils.job_monitor import JobMonitor as _JobMonitor  # type: ignore[assignment]

        client = _get_client()
        # 7-day lookback: idempotent upsert handles overlaps if re-run.
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        holdings = set(symbols)

        log.info(
            "ingest_sentiment: fetching for %d holdings, from=%s to=%s",
            len(symbols),
            from_date,
            to_date,
        )

        async with _JobMonitor(
            job_name="ingest_sentiment",
            as_of=today,
            healthcheck_url=os.environ.get("HEALTHCHECK_URL_INGEST_SENTIMENT", ""),
        ) as monitor:
            async with _acquire() as conn:
                results = await asyncio.gather(
                    *[_fetch_and_upsert(client, s, from_date, to_date, holdings, conn)
                      for s in symbols],
                    return_exceptions=True,
                )

            written = sum(r for r in results if isinstance(r, int))
            errors = sum(1 for r in results if isinstance(r, BaseException))
            monitor.rows_written = written
            log.info(
                "ingest_sentiment done: %d rows written, %d symbol errors",
                written,
                errors,
            )
    finally:
        await _close_pool()


if __name__ == "__main__":
    asyncio.run(main())
