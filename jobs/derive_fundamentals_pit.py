#!/usr/bin/env python
"""
Derive point-in-time fundamentals (rs_fundamentals_pit) from the raw research store.

Pure DB-to-DB: reads rs_financial_statements (yearly) + rs_corporate_actions and writes
rs_fundamentals_pit, stamping each row with the guarded knowledge_date. No EODHD. Run
weekly, AFTER sync_financial_statements + sync_corporate_actions.

Usage:
    python jobs/derive_fundamentals_pit.py
    python jobs/derive_fundamentals_pit.py --symbols CBA.AU,BHP.AU
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.fundamentals_pit import refresh_fundamentals_pit
from asxos.jobs._helpers import UpstreamBlocked
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_UPSTREAM_JOBS = ("sync_financial_statements", "sync_corporate_actions")


async def _missing_upstreams(conn, as_of: date) -> list[str]:
    """Upstream job names among ``_UPSTREAM_JOBS`` with no 'success' row for
    this as_of (2-day lag tolerance for a late manual re-run). Empty = ready.

    2026-07-18 incident: this job fired at its scheduled 17:10 UTC while
    sync_corporate_actions (started 16:30, fixed-offset schedule with no
    dependency on how long its upstream actually takes) was still running —
    it didn't finish until 18:09. derive_fundamentals_pit proceeded straight
    into querying rs_corporate_actions concurrently with that write and hit a
    TimeoutError, a confusing failure mode that gave no hint the real cause
    was a missing upstream. This gate turns that into a clean, correctly-typed
    'blocked' (not 'failure' — job-conventions.md) before the query ever runs,
    for the same reason generate_signals.py gates on sync_prices.
    """
    missing = []
    for job_name in _UPSTREAM_JOBS:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM job_runs
            WHERE job_name = $1
              AND status    = 'success'
              AND as_of    >= $2::date - 2
            """,
            job_name,
            as_of,
        )
        if row is None:
            missing.append(job_name)
    return missing


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    parser.add_argument(
        "--allow-stale-upstream",
        action="store_true",
        help=(
            "Proceed even if sync_financial_statements/sync_corporate_actions "
            "have no recent success row (one-off manual override; the "
            "operator is presumed to know what they're doing)."
        ),
    )
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

    today = date.today()
    await init_pool()

    async with JobMonitor(
        job_name="derive_fundamentals_pit",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_derive_fundamentals_pit,
        override_reason=(
            "operator: --allow-stale-upstream" if args.allow_stale_upstream else None
        ),
    ) as monitor:
        async with acquire() as conn:
            # Upstream check INSIDE the JobMonitor block so an UpstreamBlocked
            # raise is recorded as status='blocked', not 'failure' (matches
            # generate_signals.py's identical placement/reasoning).
            missing = await _missing_upstreams(conn, today)
            if missing:
                if not args.allow_stale_upstream:
                    raise UpstreamBlocked(
                        f"upstream not ready: {', '.join(missing)} has no "
                        f"'success' row for {today} (or the 2 days prior) — "
                        "refusing to derive PIT fundamentals from a possibly-"
                        "incomplete or concurrently-written research store. "
                        "Use --allow-stale-upstream for a one-off manual "
                        "override."
                    )
                log.warning(
                    f"Proceeding despite missing upstream success ({', '.join(missing)}) "
                    "by explicit --allow-stale-upstream."
                )
            counts = await refresh_fundamentals_pit(conn, as_of=today, symbols=symbols)
            if counts["rows"] == 0:
                raise RuntimeError(
                    "no PIT rows derived — rs_financial_statements is empty. "
                    "Run sync_financial_statements first."
                )
        monitor.rows_written = counts["rows"]
        log.info(
            f"derive_fundamentals_pit done — symbols={counts['symbols']} rows={counts['rows']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
