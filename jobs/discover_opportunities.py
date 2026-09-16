#!/usr/bin/env python
"""
Record the value screen over the valuation sweep. Opens no theses (#306).

Weekly, after run_valuation in weekly-research.yml:

  1. Pre-filter through the screening evaluator (liquidity ADV >= A$250k, market
     cap >= A$100m) and log the run to screening_runs — the audit row; the rule
     row is owned by this job and created on first use.
  2. Read the latest valuation_runs row per name (S1) and compute the passing set
     (asxos/domain/discovery/ranker.py): quality on the 3-period-AVERAGE ROE,
     value >= price under both the registered convention and the average-ROE
     sensitivity. Log it. Write nothing else.

Demoted 2026-09-16 (#306). This job used to rank the passing set by value/price
x liquidity and open the top-K as `system_screen` theses at pending_review with
a target, an entry band and a stop derived from the model value by three
constants. The sealed value-to-price test returned `null` (#304), and the
pre-committed response (`asxos/domain/research/registry/vp.py::RESPONSE_RULE`)
demotes the model to a discipline device that "stops emitting target prices,
entry bands and ranked 'opportunities'". So: no rank, no proposal, no plan.
The falsifiable number per thesis is stated where the challenge reads it —
`valuation_fact` evidence and the `valuation_gap` rule in
`decision_engine/builder.py` — for theses a human has written and approved.

Deterministic Python only — no LLM (sprint §6). Rule #11: no signals /
model_versions. ASXOS_PERSONAL_USE=1 is still required: the job no longer opens
theses, but removing the gate is a change to the personal-use firewall
(AGENTS.md §2 item 1), which is James's, not this job's.

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/discover_opportunities.py
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Any, Final

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.discovery import ranker
from asxos.domain.screening.evaluator import decode_rule_json, evaluate_rule, log_run
from asxos.domain.screening.types import ScreeningRule
from asxos.domain.valuation import repository as valuation_repository
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "discover_opportunities"
#: The liquidity pre-filter, as a curated_composite screening rule this job owns.
SCREEN_RULE_NAME: Final[str] = "discovery-liquidity-v1"
SCREEN_RULE_JSON: Final[dict[str, Any]] = {
    "version": 1,
    "conditions": {
        "logic": "AND",
        "items": [
            {"field": "avg_daily_value_aud_90d", "op": "gte", "value": int(ranker.MIN_ADV_AUD)},
            {"field": "market_cap", "op": "gte", "value": int(ranker.MIN_MARKET_CAP_AUD)},
        ],
    },
}
SCREEN_RULE_DESCRIPTION: Final[str] = (
    "F-E2E r2 S4 discovery pre-filter: 90-day ADV >= A$250k and market cap >= A$100m "
    "(baseline-inquiry-2026-09-16 section 4). Owned by jobs/discover_opportunities.py."
)
#: Large enough that every match carries its values (the screen needs ADV and cap).
SCREEN_LIMIT: Final[int] = 5000
DEMOTION_NOTE: Final[str] = (
    "demoted (#306): the value screen is recorded, no thesis is opened, no target or rank is emitted"
)


async def ensure_screen_rule(conn: Any) -> ScreeningRule:
    """Create the job's rule row on first use; load it by name thereafter."""
    await conn.execute(
        """
        INSERT INTO screening_rules (name, source_method, rule_json, is_active, description)
        VALUES ($1, 'curated_composite', $2::jsonb, TRUE, $3)
        ON CONFLICT (name) DO NOTHING
        """,
        SCREEN_RULE_NAME,
        json.dumps(SCREEN_RULE_JSON),
        SCREEN_RULE_DESCRIPTION,
    )
    row = await conn.fetchrow(
        "SELECT id, name, source_method, rule_json::text AS rule_json_raw, is_active "
        "FROM screening_rules WHERE name = $1",
        SCREEN_RULE_NAME,
    )
    if row is None:
        raise RuntimeError(f"screening rule {SCREEN_RULE_NAME!r} absent after ensure — refusing to screen")
    return ScreeningRule(
        id=int(row["id"]),
        name=str(row["name"]),
        source_method=str(row["source_method"]),
        rule_json=decode_rule_json(str(row["rule_json_raw"])),
        is_active=bool(row["is_active"]),
    )


def _dec(value: object) -> Decimal:
    if isinstance(value, float):
        raise TypeError("float reached the discovery job")
    return Decimal(str(value))


async def run(*, monitor: JobMonitor) -> dict[str, Any]:
    as_of = clock.today()
    async with acquire() as conn:
        rule = await ensure_screen_rule(conn)
        result = await evaluate_rule(conn, rule, limit=SCREEN_LIMIT)
        screening_run_id = await log_run(conn, result, rule.rule_json)
        screened: dict[str, ranker.Screened] = {}
        for m in result.matches:
            adv = m.values.get("avg_daily_value_aud_90d")
            cap = m.values.get("market_cap")
            if adv is None or cap is None or isinstance(adv, str) or isinstance(cap, str):
                continue
            screened[m.symbol] = ranker.Screened(m.symbol, adv_aud=_dec(adv), market_cap_aud=_dec(cap))
        log.info(
            "screen %s: %d of %d pass liquidity (screening_runs #%d)",
            rule.name, result.match_count, result.universe_size, screening_run_id,
        )

        runs = await valuation_repository.latest_runs(conn, as_of=as_of)
        if not runs:
            raise RuntimeError(
                f"no valuation_runs at or before {as_of} — run_valuation must precede discovery"
            )
        passing = ranker.passing(runs, screened, screening_run_id=screening_run_id)
    # The screening_runs row is the audit log's, not this job's product; the job's
    # own product — theses — no longer exists (#306), so rows_written stays 0 and
    # the note says why, so a digest cannot read the zero as a silent failure.
    monitor.rows_written = 0
    monitor.note = f"{DEMOTION_NOTE}; {len(passing)} names pass the value screen"
    summary = {
        "as_of": as_of.isoformat(),
        "screening_run_id": screening_run_id,
        "screened": len(screened),
        "valued_runs": sum(1 for r in runs if r.outcome == "valued"),
        "passing": [o.symbol for o in passing],
        "opened": [],
    }
    log.info("discover_opportunities done — %s", json.dumps(summary, default=str))
    return summary


async def main() -> None:
    require_personal_use_job()
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=clock.today(),
        healthcheck_url=settings.healthcheck_url_discover_opportunities,
    ) as monitor:
        await run(monitor=monitor)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
