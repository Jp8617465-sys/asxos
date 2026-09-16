#!/usr/bin/env python
"""Backfill the point-in-time risk-free series from FRED (issue #301).

WHY THIS EXISTS. `ke = risk_free + beta * erp`, and `ke` is the discount rate in
a residual-income model. The only source for it was `market_context_current`, a
daily-forward ingest with nothing before 2026-07-03 and 3 distinct values across
55 rows — so the valuation model could not be replayed at any historical cutoff,
and therefore could not be validated against a realised return at all. The
sealed value-to-price test hard-failed on exactly that (run 35135765565).

WHAT IT DOES. Reads FRED `IRLTLT01AUM156N` (Australia 10-year government bond
yield, monthly) from `--start` forward and upserts one `risk_free_rates` row per
published observation.

WHY UPSERT AND NOT INSERT. FRED revises published values. A series that cannot
take a revision keeps a stale print forever, so a re-run overwrites `yield_pct`
and moves `ingested_at`; the pair is how a revision is visible afterwards. This
is the one table in the recent set that is deliberately NOT append-only, and
migration 0058's header says why: it holds a third-party observation, not
evidence of a decision.

WHAT IT DOES NOT DO. It does not touch `market_context`, `market_context_current`
or any valuation output, and it writes no `valuation_runs` or `research_runs`
row. Moving the valuation read path onto this table is a separate PR, made only
once this job has run and its rows are verified — so the live sweep never reads
an empty table.

Usage:
    python jobs/backfill_risk_free.py --start 2024-01-01
    python jobs/backfill_risk_free.py --start 2024-01-01 --dry-run
"""

import argparse
import asyncio
import logging
from datetime import date
from decimal import Decimal

from asxos.clients.fred import get_client as get_fred_client
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.valuation import capm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME = "backfill_risk_free"

#: The bare FRED id, derived once in capm and shared with the valuation read
#: path — a second hardcoded copy is how the writer and the reader come to
#: disagree about which series `risk_free_rates` holds.
FRED_SERIES_ID = capm.RISK_FREE_SERIES_ID

#: FRED's monthly series returns ~12 observations a year; this bounds a decade
#: without paging. A truncated fetch is detected rather than assumed away.
OBSERVATION_LIMIT = 200

SQL_UPSERT = """
    INSERT INTO risk_free_rates (series, as_of, yield_pct, source)
    VALUES ($1, $2, $3, 'fred')
    ON CONFLICT (series, as_of) DO UPDATE
       SET yield_pct = EXCLUDED.yield_pct,
           ingested_at = NOW()
     WHERE risk_free_rates.yield_pct IS DISTINCT FROM EXCLUDED.yield_pct
"""

SQL_SUMMARY = """
    SELECT count(*) AS rows, min(as_of) AS earliest, max(as_of) AS latest,
           count(DISTINCT yield_pct) AS distinct_yields
      FROM risk_free_rates
     WHERE series = $1
"""


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01", help="FRED observation_start (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="Fetch and report; write nothing")
    args = ap.parse_args()

    start = date.fromisoformat(args.start)

    client = get_fred_client()
    try:
        observations = await client.get_series(
            FRED_SERIES_ID,
            observation_start=start.isoformat(),
            limit=OBSERVATION_LIMIT,
            sort_order="asc",
        )
    finally:
        await client.close()

    usable = [o for o in observations if o.value is not None]
    missing = len(observations) - len(usable)
    if not usable:
        raise RuntimeError(
            f"FRED returned no usable observations for {FRED_SERIES_ID} since {start} "
            f"({len(observations)} rows, all missing) — refusing to report a backfill "
            "that wrote nothing as success"
        )
    if len(observations) == OBSERVATION_LIMIT:
        # Silently keeping a truncated series would leave a gap at the far end
        # that looks exactly like "the publisher had no data".
        raise RuntimeError(
            f"FRED returned exactly the {OBSERVATION_LIMIT}-row limit — the series is "
            "truncated and the tail is missing. Raise OBSERVATION_LIMIT or page."
        )

    log.info(
        "%s: %s observations since %s (%s usable, %s missing), %s..%s",
        FRED_SERIES_ID, len(observations), start, len(usable), missing,
        usable[0].date, usable[-1].date,
    )

    if args.dry_run:
        for obs in usable[:5]:
            log.info("  DRY RUN %s %s", obs.date, obs.value)
        log.info("DRY RUN — wrote nothing. %s rows would be upserted.", len(usable))
        return

    await init_pool()
    try:
        async with acquire() as conn:
            written = 0
            for obs in usable:
                assert obs.value is not None  # narrowed by the `usable` filter
                status = await conn.execute(
                    SQL_UPSERT, FRED_SERIES_ID, obs.date, Decimal(str(obs.value))
                )
                # "INSERT 0 1" on a write, "INSERT 0 0" when the WHERE suppressed
                # a no-op update — so this counts real changes, not attempts.
                written += int(status.rsplit(" ", 1)[-1])
            summary = await conn.fetchrow(SQL_SUMMARY, FRED_SERIES_ID)
    finally:
        await close_pool()

    log.info(
        "%s: %s rows changed. Series now %s rows, %s..%s, %s distinct yields.",
        JOB_NAME, written, summary["rows"], summary["earliest"], summary["latest"],
        summary["distinct_yields"],
    )


if __name__ == "__main__":
    asyncio.run(main())
