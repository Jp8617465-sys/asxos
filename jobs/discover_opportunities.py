#!/usr/bin/env python
"""
Record the value screen, and propose each survivor for review.

Weekly, after run_valuation in weekly-research.yml:

  1. Pre-filter through the screening evaluator (liquidity ADV >= A$250k, market
     cap >= A$100m) and log the run to screening_runs — the audit row; the rule
     row is owned by this job and created on first use.
  2. Read the latest valuation_runs row per name (S1) and compute the passing set
     (asxos/domain/discovery/ranker.py): quality on the 3-period-AVERAGE ROE,
     value >= price under both the registered convention and the average-ROE
     sensitivity.
  3. Open each fresh survivor as a `system_screen` thesis at `pending_review`
     with two thesis_evidence rows — a governance-queue entry, nothing more.
     It renders in the brief's candidates card; James approves or rejects.

WHAT IS PROPOSED AND WHAT IS NOT. #306 demoted this job after the sealed
value-to-price test returned `null` (#304): it had been ranking the passing set
by value/price x liquidity and opening the top-K with a target, an entry band
and a stop derived from the model value by three constants. The pre-committed
response (`asxos/domain/research/registry/vp.py::RESPONSE_RULE`) demotes the
model to a discipline device that "stops emitting target prices, entry bands and
ranked 'opportunities'".

Those three things stay deleted. What #306 also removed, and what James restored
on 2026-09-17, is the proposal itself — a reviewable queue is not a target and
not a rank. So a proposed row carries NO target, NO stop, NO entry band, and the
set is ordered by symbol and never truncated (`asxos/domain/discovery/proposals.py`
explains why both circuit breakers refuse the whole run rather than pick).

The falsifiable number per thesis is still stated where the challenge reads it —
`valuation_fact` evidence and the `valuation_gap` rule in
`decision_engine/builder.py` — once a human has written a plan and approved it.

Deterministic Python only — no LLM (sprint §6). Rule #11: no signals /
model_versions. ASXOS_PERSONAL_USE=1 required (AGENTS.md §2 item 1).

Note on first fire: `weekly-research.yml` is reserved to James and is never
dispatched from an agent session (.claude/rules/job-conventions.md), so this
lands on his Saturday 16:00 UTC schedule, not on demand.

Usage:
    ASXOS_PERSONAL_USE=1 python jobs/discover_opportunities.py
"""
import asyncio
import json
import logging
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any, Final

from asxos import clock
from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.discovery import proposals, ranker
from asxos.domain.discovery.types import Opportunity
from asxos.domain.screening.evaluator import decode_rule_json, evaluate_rule, log_run
from asxos.domain.screening.types import ScreeningRule
from asxos.domain.theses import service as theses_service
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


async def propose(
    conn: Any, passing: list[Opportunity], *, as_of: date
) -> tuple[list[str], list[str], str | None]:
    """Open each fresh survivor at `pending_review`. Returns (opened, suppressed, breaker).

    One transaction per symbol, never one around the loop: a run that fails on
    symbol 9 of 16 should leave the first 8 committed and be resumable, which
    the suppression predicate makes safe.

    Both circuit breakers open NOTHING rather than truncate — see
    `proposals.py`'s module docstring for why a truncated set is a rank. Only
    `QueueFull` is caught here: it is James's state, reported in the summary.
    `RunawayScreen` propagates and fails the run — a gate is broken and the
    run must be loud.
    """
    if not passing:
        return [], [], None
    symbols = [o.symbol for o in passing]
    rows = await conn.fetch(
        proposals.SQL_SUPPRESSED_SYMBOLS, symbols, proposals.REPROPOSE_COOLDOWN_DAYS
    )
    suppressed = {r["symbol"] for r in rows}
    depth_row = await conn.fetchrow(proposals.SQL_OPEN_QUEUE_DEPTH)
    depth = int(depth_row["n"]) if depth_row else 0
    try:
        fresh = proposals.selectable(
            passing, suppressed=suppressed, open_queue_depth=depth
        )
    except proposals.QueueFull as exc:
        log.info("queue-depth breaker: %s", exc)
        return [], sorted(suppressed), str(exc)

    opened: list[str] = []
    for o in fresh:
        async with conn.transaction():
            thesis = await theses_service.open_thesis(
                conn,
                o.symbol,
                status="research",
                thesis_text=proposals.thesis_text_for(o),
                governance_status="pending_review",
                source="system_screen",
                evidence_confidence=proposals.evidence_tier_for(o),
                evidence_citations=proposals.evidence_citations_for(o),
                reasoning=proposals.opening_reason_for(o, as_of=as_of),
            )
            for row in proposals.evidence_rows_for(o):
                await theses_service.add_thesis_evidence(
                    conn,
                    thesis_id=thesis.thesis_id,
                    source_agent="system_screen",
                    source_as_of=datetime.combine(o.as_of, time(0, 0), tzinfo=UTC),
                    **row,
                )
        opened.append(f"{o.symbol}#{thesis.thesis_id}")
        log.info("proposed %s as thesis %d (pending_review)", o.symbol, thesis.thesis_id)
    return opened, sorted(suppressed), None


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
        opened, suppressed, breaker = await propose(conn, passing, as_of=as_of)
    monitor.rows_written = len(opened)
    # Deliberately NO monitor.note on any of these paths. `note` is the degraded
    # partial-success channel (job_monitor.py) and check_cron_health raises on
    # every note it finds inside 36 hours, so a routine weekly outcome written
    # there pages every Saturday for the rest of time. A quiet run, a suppressed
    # name and a tripped breaker are all ordinary states of this job; they are
    # reported in the summary and the log, and the queue itself renders in the
    # brief's candidates card.
    summary = {
        "as_of": as_of.isoformat(),
        "screening_run_id": screening_run_id,
        "screened": len(screened),
        "valued_runs": sum(1 for r in runs if r.outcome == "valued"),
        "passing": [o.symbol for o in passing],
        "opened": opened,
        "suppressed_existing": suppressed,
        "breaker": breaker,
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
