#!/usr/bin/env python
"""
Discover opportunities from the valuation sweep and propose theses (F-E2E r2, S4).

Weekly, after run_valuation in weekly-research.yml:

  1. Pre-filter through the screening evaluator (liquidity ADV >= A$250k, market
     cap >= A$100m) and log the run to screening_runs — the audit row the DoD
     names; the rule row is owned by this job and created on first use.
  2. Read the latest valuation_runs row per name (S1) and rank with the
     deterministic ranker (asxos/domain/discovery/ranker.py): quality on the
     3-period-AVERAGE ROE, value >= price under both the registered convention and
     the average-ROE sensitivity, score = min(value/price) x liquidity factor.
  3. Open the top-K names that have no open thesis as status='research' at
     governance_status='pending_review' with source='system_screen' (migration
     0057), the baseline §5 price plan, measurable invalidation conditions, and
     thesis_evidence rows citing the valuation run, its point-in-time inputs and
     the screening run. A human approval (S8: `APPROVE thesis <id>`) is the only
     path to 'approved'.

Deterministic Python only — no LLM (sprint §6). Rule #11: no signals /
model_versions. Personal-advice firewall: the theses are investment content, so
ASXOS_PERSONAL_USE=1 is required. Idempotent: a symbol with an open thesis is never
proposed again, so a re-run proposes only new names.

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/discover_opportunities.py [--top-k 10]
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any, Final

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.discovery import ranker
from asxos.domain.discovery.types import Opportunity
from asxos.domain.screening.evaluator import decode_rule_json, evaluate_rule, log_run
from asxos.domain.screening.types import ScreeningRule
from asxos.domain.theses.service import add_thesis_evidence, open_thesis
from asxos.domain.valuation import repository as valuation_repository
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "discover_opportunities"
SOURCE_AGENT: Final[str] = "system_screen"
DEFAULT_TOP_K: Final[int] = 10
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
#: Large enough that every match carries its values (the ranker needs ADV and cap).
SCREEN_LIMIT: Final[int] = 5000


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


async def open_symbols(conn: Any) -> set[str]:
    rows = await conn.fetch("SELECT symbol FROM theses WHERE closed_at IS NULL")
    return {str(r["symbol"]) for r in rows}


async def propose(conn: Any, o: Opportunity) -> int:
    """Open one system_screen thesis with its three evidence citations; returns thesis_id."""
    citations = [
        f"asxos://valuation_runs/{o.run_id}",
        f"asxos://screening_runs/{o.screening_run_id}",
    ]
    thesis = await open_thesis(
        conn,
        o.symbol,
        status="research",
        thesis_text=ranker.thesis_text_for(o),
        entry_band_lower=o.plan.entry_band_lower,
        entry_band_upper=o.plan.entry_band_upper,
        stop_price=o.plan.stop_price,
        target_price=o.plan.target_price,
        timeline_days=o.plan.timeline_days,
        invalidation_conditions=ranker.invalidation_conditions_for(o),
        reasoning=(
            f"Proposed by the deterministic valuation screen: score {o.score} "
            f"(value/price min {o.value_to_price_min}, liquidity factor {o.liquidity_factor})."
        ),
        governance_status="pending_review",
        source=SOURCE_AGENT,
        evidence_confidence="verified",
        evidence_citations=citations,
    )
    as_of_ts = datetime.combine(o.as_of, time(0), tzinfo=UTC)
    await add_thesis_evidence(
        conn,
        thesis_id=thesis.thesis_id,
        source_agent=SOURCE_AGENT,
        tier="verified",
        claim_text=(
            f"valuation_runs {o.run_id}: value {o.value_registered} (registered), "
            f"{o.value_average_roe} (average ROE) against close {o.last_close} on "
            f"{o.last_close_dt.isoformat()}; content_hash {o.run_content_hash}"
        ),
        source_table="valuation_runs",
        source_as_of=as_of_ts,
        snapshot_data={
            "run_id": o.run_id,
            "content_hash": o.run_content_hash,
            "value_registered": o.value_registered,
            "value_average_roe": o.value_average_roe,
            "last_close": o.last_close,
            "last_close_dt": o.last_close_dt.isoformat(),
            "ke_mid": o.ke_mid,
            "roe_trailing": o.roe_trailing,
            "roe_average": o.roe_average,
            "flags": list(o.flags),
        },
    )
    await add_thesis_evidence(
        conn,
        thesis_id=thesis.thesis_id,
        source_agent=SOURCE_AGENT,
        tier="verified",
        claim_text=(
            f"screening_runs {o.screening_run_id} ({SCREEN_RULE_NAME}): {o.symbol} passed "
            f"ADV A${o.adv_aud:.0f} >= {ranker.MIN_ADV_AUD:.0f} and market cap "
            f"A${o.market_cap_aud:.0f} >= {ranker.MIN_MARKET_CAP_AUD:.0f}"
        ),
        source_table="screening_runs",
        source_as_of=as_of_ts,
        snapshot_data={
            "screening_run_id": o.screening_run_id,
            "rule": SCREEN_RULE_NAME,
            "adv_aud": o.adv_aud,
            "market_cap_aud": o.market_cap_aud,
            "liquidity_factor": o.liquidity_factor,
        },
    )
    return thesis.thesis_id


async def run(*, monitor: JobMonitor, top_k: int) -> dict[str, Any]:
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
        ranked = ranker.rank(runs, screened, screening_run_id=screening_run_id)
        already = await open_symbols(conn)
        opened: list[tuple[int, str]] = []
        for o in ranked:
            if len(opened) >= top_k:
                break
            if o.symbol in already:
                continue
            thesis_id = await propose(conn, o)
            opened.append((thesis_id, o.symbol))
            monitor.rows_written = len(opened)
    summary = {
        "as_of": as_of.isoformat(),
        "screening_run_id": screening_run_id,
        "screened": len(screened),
        "valued_runs": sum(1 for r in runs if r.outcome == "valued"),
        "opportunities": len(ranked),
        "top": [(o.symbol, str(o.score)) for o in ranked[:top_k]],
        "opened": opened,
        "skipped_open_thesis": [o.symbol for o in ranked[: top_k + len(already)] if o.symbol in already],
    }
    if not opened:
        monitor.note = (
            f"0 theses opened: {len(ranked)} opportunities, "
            f"{len([o for o in ranked if o.symbol in already])} already have an open thesis"
        )
    log.info("discover_opportunities done — %s", json.dumps(summary, default=str))
    return summary


async def main() -> None:
    require_personal_use_job()
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="max theses to open per run")
    args = parser.parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be >= 1")
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=clock.today(),
        healthcheck_url=settings.healthcheck_url_discover_opportunities,
    ) as monitor:
        await run(monitor=monitor, top_k=args.top_k)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
