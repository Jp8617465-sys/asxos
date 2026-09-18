#!/usr/bin/env python
"""
Value the active ASX equity universe on the residual-income model (F-E2E r2, S1).

Pure DB-to-DB: reads rs_fundamentals_pit, prices, universe, market_context_current and
fx_rates; writes one content-addressed `valuation_runs` row per active au_equity symbol
under the bundled scenario pre-registration — `valued` where the model has a basis,
`blocked` with named gaps where it does not (gaps are rows, never omissions). Runs
weekly in weekly-research.yml after derive_fundamentals_pit. Rule #11: nothing here
reads `signals` or `model_versions` (screened at import in the valuation package).

Idempotent by construction: the store is append-only and every INSERT is
ON CONFLICT (run_id) DO NOTHING, so a same-day re-run writes 0 rows rather than
duplicating or mutating. That no-op is recorded as rows_written=0 on a 'success'
job_runs row and logged at INFO — deliberately NOT in `monitor.note`, which is the
degraded-partial-success channel check_cron_health alerts on (see the comment at
the branch below). A no-op is not a degradation.

0 rows written AND 0 rows stored is a different thing entirely and still hard-fails:
that means the INSERTs did not land.

Usage:
    python jobs/run_valuation.py
    python jobs/run_valuation.py --write-batch-size 100
"""

import argparse
import asyncio
import logging
from collections import Counter
from datetime import UTC, datetime

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.valuation import repository
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.sweep import ke_band_for, value_row
from asxos.domain.valuation.universe import load_market_inputs, load_universe_rows
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME = "run_valuation"


def histogram(runs: list) -> Counter[str]:  # type: ignore[type-arg]
    """`valued` plus one bucket per FIRST gap name — the S1 close's blocked histogram."""
    counts: Counter[str] = Counter()
    for run in runs:
        counts[run.outcome if run.outcome == "valued" else run.gaps[0].name] += 1
    return counts


async def run(*, cutoff: datetime, monitor: JobMonitor, write_batch_size: int) -> Counter[str]:
    prereg = load_bundled_preregistration()
    async with acquire() as conn:
        inserted = await repository.ensure_preregistered(conn, prereg)
        log.info(
            "preregistration %s %s (hash %s…)",
            prereg.preregistration_id,
            "registered" if inserted else "already registered",
            prereg.content_hash[:12],
        )
        market = await load_market_inputs(conn, cutoff_date=cutoff.date())
        ke = ke_band_for(market, prereg)
        log.info(
            "ke band %s / %s / %s (rf %s as_of %s, AUDUSD %s as_of %s)",
            ke.ke_low, ke.ke_mid, ke.ke_high,
            market.risk_free, market.risk_free_as_of, market.audusd, market.audusd_as_of,
        )
        rows = await load_universe_rows(
            conn,
            cutoff_date=cutoff.date(),
            roe_average_periods=prereg.input_rules.roe_average_periods,
        )
        runs = [
            value_row(row, market=market, ke=ke, prereg=prereg, cutoff=cutoff, created_at=cutoff)
            for row in rows
        ]
        counts = histogram(runs)
        if counts["valued"] == 0:
            raise RuntimeError(
                f"the sweep valued 0 of {len(runs)} names — inputs are missing universe-wide; "
                f"histogram={dict(counts)}"
            )

        def record_progress(written: int) -> None:
            monitor.rows_written = written

        written = await repository.save_runs(
            conn, runs, batch_size=write_batch_size, on_rows_committed=record_progress
        )
        monitor.rows_written = written
        if written == 0:
            stored, stored_valued = await repository.count_runs_for(conn, cutoff.date())
            if stored == 0:
                raise RuntimeError(
                    f"0 rows written and 0 rows stored for {cutoff.date()} — the INSERTs "
                    "did not land; refusing to report success"
                )
            # NOT monitor.note. `note` is the DEGRADED partial-success channel
            # (job_monitor.py:56-62) and check_cron_health hard-fails on every
            # note it finds in a 36-hour window, so putting a benign idempotent
            # no-op there turns the nightly watchdog red for a run that did
            # exactly what it was designed to do — observed 2026-09-17, run
            # 35165551435. The no-op stays fully recoverable without it:
            # rows_written=0 on a 'success' row, plus the log line below, plus
            # the `stored` rows themselves in valuation_runs.
            log.info(
                "same-day re-run: 0 rows written; %d rows (%d valued) already stored for %s",
                stored, stored_valued, cutoff.date(),
            )
        log.info(
            "run_valuation done — symbols=%d written=%d histogram=%s",
            len(runs), written, dict(counts.most_common()),
        )
        return counts


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-batch-size",
        type=int,
        default=repository.DEFAULT_WRITE_BATCH_SIZE,
        help="valuation_runs rows per bounded INSERT transaction",
    )
    args = parser.parse_args()

    # UTC, like every decision-engine cutoff (builder.py: `as_of = cutoff.date()`),
    # because migration 0054 CHECKs `knowledge_cutoff::date = as_of` under the pool's
    # pinned UTC session — not the Sydney wall-clock date `asxos.clock` gives daily jobs.
    cutoff = datetime.now(UTC)
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=cutoff.date(),
        healthcheck_url=settings.healthcheck_url_run_valuation,
    ) as monitor:
        await run(cutoff=cutoff, monitor=monitor, write_batch_size=args.write_batch_size)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
