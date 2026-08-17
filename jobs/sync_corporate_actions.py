#!/usr/bin/env python
"""
Sync the research-store corporate-actions table (rs_corporate_actions) from EODHD —
dividends (+ AU franking) and splits for every security in rs_security_master.

Survivorship-free: iterates the full security master (active + delisted) by default.
SEPARATE from production tables — never touches `universe` or `prices`. Run weekly,
AFTER sync_security_master (it has no symbols to iterate until that has run).

Usage:
    python jobs/sync_corporate_actions.py                 # all of rs_security_master
    python jobs/sync_corporate_actions.py --active-only   # is_active = true only
    python jobs/sync_corporate_actions.py --limit 50      # first N symbols (smoke test)
    python jobs/sync_corporate_actions.py --symbols CBA.AU,BHP.AU
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.corporate_actions import refresh_corporate_actions
from asxos.ingestion.eodhd import get_client
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def _load_symbols(conn, *, active_only: bool, limit: int | None) -> list[str]:
    sql = "SELECT symbol FROM rs_security_master"
    if active_only:
        sql += " WHERE is_active"
    sql += " ORDER BY symbol"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = await conn.fetch(sql)
    return [r["symbol"] for r in rows]


# Minimum share of symbols that must succeed before the run is called a success.
# Matches the 0.75 the other partial-success jobs use (ingest_news, sync_fundamentals).
MIN_OK_RATIO = 0.75


def assert_symbol_success_ratio(counts: dict[str, int], *, threshold: float = MIN_OK_RATIO) -> int:
    """Hard-fail when too large a share of symbols failed. Returns the OK count.

    Bounded tolerance, not unbounded. `refresh_corporate_actions` isolates a per-symbol
    write failure (counting it and continuing) so one poison row cannot wedge the whole
    weekly run. That is right for the ISOLATED failure class and wrong for the SYSTEMIC
    one: a dead connection, a revoked grant or a wrong-schema deploy fails EVERY symbol,
    and without this gate the run still returns normally — JobMonitor writes
    status='success' and pings the Healthchecks deadman GREEN with rows_written near 0.
    The deadman cannot catch that, because it is being fed. That inverts CLAUDE.md #10
    and is strictly worse than the pre-batching behaviour, where an unguarded
    conn.execute aborted the run loudly.

    Not hypothetical: ingest_news recorded 22 consecutive status='success' runs with
    rows_written=0 against an empty table for exactly this shape — see the predicate
    lesson in `asxos/jobs/_helpers.py::assert_partial_success`. That helper takes a
    per-unit result sequence; this job carries only aggregate counters, so the same
    threshold semantics are applied here directly rather than fabricating a synthetic
    results list (fabricating one is how that no-op predicate happened).
    """
    total = counts["symbols"]
    n_ok = total - counts["failed"]
    if total and (n_ok / total) < threshold:
        raise RuntimeError(
            f"sync_corporate_actions: only {n_ok}/{total} symbols succeeded "
            f"({n_ok / total:.1%} < {threshold:.0%}) — failing loudly rather than "
            "reporting a green run. A failure rate this high is systemic "
            "(connection, grant, schema), not per-symbol data."
        )
    return n_ok


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    args = parser.parse_args()

    today = date.today()
    await init_pool()
    client = get_client()

    async with JobMonitor(
        job_name="sync_corporate_actions",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_corporate_actions,
    ) as monitor:
        async with acquire() as conn:
            if args.symbols:
                symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
            else:
                symbols = await _load_symbols(
                    conn, active_only=args.active_only, limit=args.limit
                )
            # Hard-fail loudly if the dependency hasn't run — no silent no-op.
            if not symbols:
                raise RuntimeError(
                    "no symbols to process — rs_security_master is empty. "
                    "Run sync_security_master first."
                )
            log.info(f"sync_corporate_actions start — {len(symbols)} symbols")

            # Track rows as they land, not just on the happy path. The in-process
            # wall-clock deadline (corporate_actions._RUN_DEADLINE_S) makes "aborted
            # after substantial partial progress" an expected recurring outcome, and
            # JobMonitor.__aexit__ persists self.rows_written on the failure path too —
            # so assigning only after the call returned reported rows_written = 0 for a
            # run that had in fact written tens of thousands of rows.
            def _track(total: int) -> None:
                monitor.rows_written = total

            counts = await refresh_corporate_actions(
                client, conn, symbols, on_rows_written=_track
            )

        monitor.rows_written = counts["dividends"] + counts["splits"]
        log.info(
            "sync_corporate_actions done — "
            f"symbols={counts['symbols']} with_actions={counts['symbols_with_actions']} "
            f"dividends={counts['dividends']} splits={counts['splits']} failed={counts['failed']}"
        )

        # Gate the run AFTER logging the counts, so the numbers are on the record even
        # when this raises. See the function's docstring for why unbounded per-symbol
        # tolerance would turn a systemic failure into a green deadman ping.
        assert_symbol_success_ratio(counts)

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
