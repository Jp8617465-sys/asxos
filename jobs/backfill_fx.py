#!/usr/bin/env python
"""Load AUD-base FX history for the currencies the valuation sweep cannot convert.

THE FINDING THIS CLOSES. Measured 2026-09-20, 75 symbols are blocked on
`currency_unconvertible` — they report in a currency the sweep has no rate for.
It was scoped as "a missing conversion step", but `fx_rates` holds **AUDUSD
only** (one pair, 108 rows), and `asxos/domain/prices/fx.py` says so in its own
docstring: "fx_rates carries only AUDUSD, so 'foreign' == 'USD' in v1". So the
conversion had no rates to convert with, and this fetches them.

    NZD 43 · CAD 15 · EUR 4 · GBP 4 · PGK 4 · SGD 2 · MYR 1 · IDR 1 · HKD 1

NZD and CAD alone are 58 of the 75.

WHY A BACKFILL AND NOT JUST THE DAILY PHASE. `sync_prices` now fetches these
pairs forward, but a valuation reads the rate AT ITS CUTOFF, and the sweep
replays historical cutoffs (the sealed V/P test runs at 2025 dates). Without
history, a 2025 cutoff finds no rate and the cohort stays blocked at exactly the
dates the predictive test measures. This loads the history once.

POINT-IN-TIME IS THE WHOLE POINT. The sweep reads
`fx_rates WHERE dt <= cutoff ORDER BY dt DESC LIMIT 1`. Converting a 2025 book
value at today's rate would be a look-ahead leak: the valuation would know an
exchange rate that did not exist when its fundamentals were published. Loading
daily history is what makes that read honest rather than merely well-named.

BEST-EFFORT PER PAIR, AND THAT IS DELIBERATE. A pair EODHD does not serve is
reported and skipped, not raised. PGK and IDR are the doubtful ones; failing to
source either should cost five symbols, not the other 70.

`--dry-run` is the DEFAULT: it fetches nothing and prints the plan. Pass
`--persist` to fetch and write.

Usage:
    python jobs/backfill_fx.py
    python jobs/backfill_fx.py --persist --from 2022-01-01
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import UTC, date, datetime
from typing import Any, Final

from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.prices import VALUATION_FX_PAIRS, to_fx_rows, upsert_fx_rates
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "backfill_fx"

#: Far enough back to cover every `rs_fundamentals_pit` knowledge_date the
#: replay harness reaches. Cheap: one request per pair regardless of span.
DEFAULT_FROM: Final[date] = date(2022, 1, 1)


async def run(
    conn: Any, client: Any, *, from_date: date, persist: bool, monitor: JobMonitor | None = None
) -> dict[str, Any]:
    written: dict[str, int] = {}
    failed: dict[str, str] = {}

    if not persist:
        log.info(
            "DRY RUN — would fetch %d pairs from %s: %s",
            len(VALUATION_FX_PAIRS), from_date, ", ".join(VALUATION_FX_PAIRS),
        )
        return {
            "persist": False,
            "from_date": from_date.isoformat(),
            "planned_pairs": list(VALUATION_FX_PAIRS),
            "written": {},
            "failed": {},
        }

    for pair in VALUATION_FX_PAIRS:
        try:
            raw = await client.daily_prices(f"{pair}.FOREX", from_date=from_date.isoformat())
        except Exception as exc:
            # Reported, not raised. A pair EODHD does not serve costs its own
            # cohort and nothing else; raising here would forfeit the pairs
            # already written and the ones not yet tried.
            failed[pair] = f"{type(exc).__name__}: {exc}"
            log.warning("fx backfill: %s unavailable — %s: %s", pair, type(exc).__name__, exc)
            continue
        rows = to_fx_rows(raw, pair=pair)
        if not rows:
            failed[pair] = "no rows returned"
            log.warning("fx backfill: %s returned no usable rows", pair)
            continue
        written[pair] = await upsert_fx_rates(conn, rows)
        log.info("fx backfill: %s wrote %d rows", pair, written[pair])

    if monitor is not None:
        monitor.rows_written = sum(written.values())
    summary = {
        "persist": True,
        "from_date": from_date.isoformat(),
        "written": written,
        "failed": failed,
        "pairs_ok": len(written),
        "pairs_failed": len(failed),
    }
    log.info("%s done — %s", JOB_NAME, json.dumps(summary, default=str))
    return summary


async def main() -> None:
    require_personal_use_job()
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", action="store_true", help="Fetch and write (default: dry-run)")
    ap.add_argument("--from", dest="from_date", default=DEFAULT_FROM.isoformat())
    args = ap.parse_args()
    from_date = date.fromisoformat(args.from_date)

    await init_pool()
    try:
        if not args.persist:
            async with acquire() as conn:
                await run(conn, None, from_date=from_date, persist=False)
            return
        client = get_client()
        try:
            async with JobMonitor(job_name=JOB_NAME, as_of=datetime.now(UTC).date()) as monitor:
                async with acquire() as conn:
                    await run(conn, client, from_date=from_date, persist=True, monitor=monitor)
        finally:
            await client.close()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
