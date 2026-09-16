#!/usr/bin/env python
"""Run the sealed value-to-price predictive test and record it (S3).

This is the first real `research_run` in the system: the table was empty while
the residual-income model was already emitting target prices for 23 named
securities. Migration 0050's trigger makes the result undeletable, which is the
point — a failed variant that can be dropped is not evidence of anything.

WHAT IT DOES, IN ORDER.
  1. Refuses unless the hypothesis is already sealed (`asx research vp-register`).
     A test that registers its own pre-registration on the way past has not
     pre-registered anything.
  2. Replays the residual-income model at each quarterly cutoff using the REAL
     `sweep.value_row` against point-in-time inputs (`knowledge_date <= cutoff`),
     over a survivorship-correct membership set that is NOT `universe.is_active`.
  3. Loads the forward price panel and evaluates the quintile ladder.
  4. Writes ONE ResearchRun carrying the verdict, the ladder, the survivorship
     accounting and the declared multiple-testing surface.

WHAT IT DOES NOT DO. It writes no `valuation_runs` rows — the replay is
in-process and `panel_hash` is the record, so `valuation_runs` keeps meaning
"live sweep". It changes nothing about what the product emits: the verdict's
consequence is the pre-committed RESPONSE_RULE, applied as a separate,
human-visible step (S4). And `alpha_claim` on the run stays "none" regardless
of the verdict, because a four-cutoff, heavily-overlapping cross-section cannot license a size.

Usage:
    python jobs/run_vp_test.py --cutoffs 2025-03-31,2025-06-30,2025-09-30,2025-12-31
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from asxos import clock
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.research.registry.harness import HarnessError, panel_hash
from asxos.domain.research.registry.repository import (
    list_runs,
    save_run,
)
from asxos.domain.research.registry.types import ResearchRun
from asxos.domain.research.registry.vp import (
    HYPOTHESIS_ID,
    PRIMARY_HORIZON_SESSIONS,
    RESPONSE_RULE,
    STRATEGY_ID,
    TOTAL_SURFACE_EXAMINED,
)
from asxos.domain.research.registry.vp_harness import evaluate_value_to_price
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.sweep import ke_band_for, value_row
from asxos.domain.valuation.universe import load_market_inputs, load_replay_rows

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME = "run_vp_test"

SQL_HYPOTHESIS_EXISTS = "SELECT 1 FROM research_hypotheses WHERE hypothesis_id = $1"
#: Closes only; the evaluator derives its calendar from the union of panel dates.
SQL_PANEL = (
    "SELECT symbol, dt, close FROM prices "
    "WHERE symbol LIKE '%.AU' AND dt >= $1 AND dt <= $2 ORDER BY symbol, dt"
)
#: Instruments whose accounting makes the model mis-specified — an LIC's "ROE"
#: is its portfolio return, an A-REIT's contains the IAS 40 revaluation mark.
#: FLAGGED in the result, never excluded: dropping them after seeing a candidate
#: set would be a choice made on the data.
SQL_MARKED_BOOK = (
    "SELECT symbol, gics_industry FROM rs_security_master "
    "WHERE gics_industry ILIKE ANY (ARRAY['%REIT%','%Capital Markets%','%Asset Management%'])"
)


async def scores_for_cutoff(conn, cutoff: date, prereg) -> dict[str, Decimal]:  # type: ignore[no-untyped-def]
    """Replay the model at `cutoff` and return symbol -> value_to_price."""
    market = await load_market_inputs(conn, cutoff_date=cutoff)
    ke = ke_band_for(market, prereg)
    at = datetime(cutoff.year, cutoff.month, cutoff.day, tzinfo=UTC)
    rows = await load_replay_rows(
        conn, cutoff_date=cutoff, roe_average_periods=prereg.input_rules.roe_average_periods
    )
    out: dict[str, Decimal] = {}
    for row in rows:
        run = value_row(row, market=market, ke=ke, prereg=prereg, cutoff=at, created_at=at)
        if run.outcome != "valued" or run.value_per_share is None:
            continue
        price = row.last_close
        if price is None or price <= 0:
            continue
        out[row.symbol] = run.value_per_share / price
    log.info("cutoff %s: %s of %s names valued", cutoff, len(out), len(rows))
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoffs", required=True, help="Comma-separated YYYY-MM-DD quarterly cutoffs")
    ap.add_argument("--horizon", type=int, default=PRIMARY_HORIZON_SESSIONS)
    ap.add_argument("--persist", action="store_true", help="Write the ResearchRun")
    args = ap.parse_args()

    cutoffs = [date.fromisoformat(c.strip()) for c in args.cutoffs.split(",") if c.strip()]
    now = datetime.now(UTC).replace(microsecond=0)
    prereg = load_bundled_preregistration()

    await init_pool()
    try:
        async with acquire() as conn:
            sealed = await conn.fetchval(SQL_HYPOTHESIS_EXISTS, HYPOTHESIS_ID)
            if not sealed:
                raise RuntimeError(
                    f"{HYPOTHESIS_ID} is not registered. Run `asx research vp-register` "
                    "FIRST — a test that seals its own pre-registration on the way past "
                    "has pre-registered nothing."
                )

            scores = {c: await scores_for_cutoff(conn, c, prereg) for c in cutoffs}
            # clock.today() — a bare date.today() is the UTC runner's day, which is
            # the previous Sydney day for the whole evening pipeline.
            first, last = min(cutoffs), clock.today()
            rows = await conn.fetch(SQL_PANEL, first, last)
            panel: dict[str, list[tuple[date, Decimal]]] = {}
            for r in rows:
                panel.setdefault(str(r["symbol"]), []).append((r["dt"], Decimal(str(r["close"]))))
            marked = {
                str(r["symbol"]): str(r["gics_industry"])
                for r in await conn.fetch(SQL_MARKED_BOOK)
            }
            log.info(
                "panel %s symbols, marked-book %s names, cutoffs %s",
                len(panel), len(marked), len(cutoffs),
            )

            outcome, reason, evaluation = "evaluated", None, {}
            try:
                evaluation = evaluate_value_to_price(
                    scores, panel, horizon_trading_days=args.horizon, marked_book=marked
                )
            except HarnessError as exc:
                outcome, reason = "fail", str(exc)

            run = ResearchRun(
                run_id=f"run-{HYPOTHESIS_ID}-{now.strftime('%Y%m%dT%H%M%SZ')}",
                hypothesis_id=HYPOTHESIS_ID,
                strategy_version_id=STRATEGY_ID,
                as_of=max(cutoffs),
                panel_hash=panel_hash(panel),
                outcome=outcome,  # type: ignore[arg-type]
                failure_reason=reason,
                evaluation=evaluation,
                # The whole declared surface, not the one combination run here:
                # the count exists to price multiple testing, and pricing it at 1
                # when nine were available would be the error it guards against.
                variants_tried=TOTAL_SURFACE_EXAMINED,
                created_at=now,
            )
            if args.persist:
                await save_run(conn, run)
            history = await list_runs(conn, hypothesis_id=HYPOTHESIS_ID)
    finally:
        await close_pool()

    print(json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True))
    print(f"\nVERDICT: {evaluation.get('verdict', 'n/a')}")
    print(f"PRE-COMMITTED RESPONSE: {RESPONSE_RULE}")
    print(
        f"[run={run.run_id} outcome={run.outcome} persisted={args.persist} "
        f"runs_on_record={len(history)}]"
    )


if __name__ == "__main__":
    asyncio.run(main())
