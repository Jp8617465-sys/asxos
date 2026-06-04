#!/usr/bin/env python
"""
Daily news ingest — M14a.

Fetches article-level news from EODHD /news for each current holding,
UPSERTs into holding_news.  One bad ticker does not abort the run
(return_exceptions=True gather pattern, same as sync_fundamentals.py).

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
from asxos.ingestion.news import parse_news_response, upsert_news
from asxos.jobs._helpers import assert_partial_success

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
) -> int:
    """Fetch news for one symbol and upsert to holding_news.

    Catches all exceptions and returns 0 on failure so one bad ticker
    cannot abort the gather across all holdings.
    """
    try:
        raw = await client.news_for_symbol(symbol, limit=10, from_date=from_date)
        items = parse_news_response(raw, holdings=holdings, as_of=date.today())
        return await upsert_news(conn, items)
    except Exception as exc:
        log.warning("ingest_news: %s failed: %s", symbol, exc)
        return 0


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
            n_ok = assert_partial_success(
                results,
                is_ok=lambda r: isinstance(r, int) and r >= 0,
                threshold=0.75,
                label="ingest_news",
                identifiers=symbols,
                allow_empty=False,
            )
            written = sum(r for r in results if isinstance(r, int))
            errors = sum(1 for r in results if isinstance(r, BaseException))
            monitor.rows_written = written
            log.info(
                "ingest_news done: %d rows written, %d/%d symbols healthy, %d errors",
                written, n_ok, len(symbols), errors,
            )
    finally:
        await _close_pool()


if __name__ == "__main__":
    asyncio.run(main())
