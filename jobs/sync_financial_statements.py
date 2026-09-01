#!/usr/bin/env python
"""
Sync the research-store financial statements (rs_financial_statements) from EODHD —
raw historical balance-sheet / income / cash-flow statements (yearly + quarterly) for
every security in rs_security_master. The source for point-in-time factor derivation.

Survivorship-free: iterates the full security master by default. SEPARATE from
production tables — never touches `universe` or `prices`. Run weekly, AFTER
sync_security_master (which populates the symbol list it iterates).

The leak-critical PIT guard (derive_knowledge_date) lives in
asxos/ingestion/financial_statements.py and is applied by the downstream
rs_fundamentals_pit derivation; this job stores filing_date and report_date raw.

Usage:
    python jobs/sync_financial_statements.py                 # all of rs_security_master
    python jobs/sync_financial_statements.py --active-only
    python jobs/sync_financial_statements.py --limit 50
    python jobs/sync_financial_statements.py --symbols CBA.AU,BHP.AU
"""
import argparse
import asyncio
import logging

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.financial_statements import refresh_financial_statements
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


# Hybrid/capital-note security_type values (matches asxos/ingestion/universe.py's
# _TYPE_TO_KIND "hybrid" mapping). These carry a parent company's income statement
# under the note's own symbol (e.g. CBAPI.AU reports CBA's group net income) --
# ingesting statements for them is what let bank hybrids materially inflate the
# Financials segment aggregate (2026-08-18 segment-valuation architecture doc, D2).
_HYBRID_SECURITY_TYPES = ("Preferred Stock", "Notes", "BOND")


async def _load_symbols(conn, *, active_only: bool, limit: int | None) -> list[str]:
    sql = (
        "SELECT symbol FROM rs_security_master "
        "WHERE (security_type IS NULL OR NOT (security_type = ANY($1::text[])))"
    )
    params: list[object] = [list(_HYBRID_SECURITY_TYPES)]
    if active_only:
        sql += " AND is_active"
    sql += " ORDER BY symbol"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = await conn.fetch(sql, *params)
    return [r["symbol"] for r in rows]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--symbols", type=str, default=None, help="comma-separated symbols")
    args = parser.parse_args()

    today = clock.today()
    await init_pool()
    client = get_client()

    async with JobMonitor(
        job_name="sync_financial_statements",
        as_of=today,
        healthcheck_url=settings.healthcheck_url_sync_financial_statements,
    ) as monitor:
        async with acquire() as conn:
            if args.symbols:
                symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
            else:
                symbols = await _load_symbols(
                    conn, active_only=args.active_only, limit=args.limit
                )
            if not symbols:
                raise RuntimeError(
                    "no symbols to process — rs_security_master is empty. "
                    "Run sync_security_master first."
                )
            log.info(f"sync_financial_statements start — {len(symbols)} symbols")
            counts = await refresh_financial_statements(client, conn, symbols, as_of=today)

        monitor.rows_written = counts["statements"]
        log.info(
            "sync_financial_statements done — "
            f"symbols={counts['symbols']} with_statements={counts['symbols_with_statements']} "
            f"statements={counts['statements']} sectors_enriched={counts['sectors_enriched']} "
            f"failed={counts['failed']}"
        )

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
