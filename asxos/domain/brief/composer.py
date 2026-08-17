"""
Brief composer — M-Brief-V2-Sections.

compose(as_of) → Brief

Phase-1 serial collectors (timeout=60s, run sequentially, share regime context):
  wealth_state, tax_operational, market_context, active_theses

Phase-2 parallel collectors (timeout=30s, asyncio.gather):
  watchlist, underlying_drivers, new_ideas, theme_dashboard, opportunity_cost

Footer: section_health (synchronous, pure)

V2 rendering gated behind ASXOS_V2_BRIEF_ENABLED=1. When 0 (default),
falls back to V1 collect() + render_html() for backward-compat email output.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import replace
from datetime import date

from asxos.db import acquire
from asxos.domain.brief._runner import safe_collect
from asxos.domain.brief.collectors.active_theses import collect_active_theses
from asxos.domain.brief.collectors.market_context import collect_market_context
from asxos.domain.brief.collectors.new_ideas import collect_new_ideas
from asxos.domain.brief.collectors.opportunity_cost import collect_opportunity_cost
from asxos.domain.brief.collectors.section_health import collect_section_health
from asxos.domain.brief.collectors.tax_operational import collect_tax_operational
from asxos.domain.brief.collectors.theme_dashboard import collect_theme_dashboard
from asxos.domain.brief.collectors.underlying_drivers import collect_underlying_drivers
from asxos.domain.brief.collectors.watchlist import collect_watchlist
from asxos.domain.brief.collectors.wealth_state import collect_wealth_state
from asxos.domain.brief.snapshot import build_snapshot
from asxos.domain.brief.types import Brief, SectionResult
from asxos.redaction import redact_secrets

log = logging.getLogger(__name__)


def _regime_from_section(market_ctx: SectionResult) -> str | None:
    """Extract regime label from market_context SectionResult metadata."""
    if market_ctx.metadata:
        return market_ctx.metadata.get("regime_label")
    return None


async def compose(as_of: date) -> Brief:
    """Run all collectors, build snapshot, persist to brief_runs, return Brief."""
    v2_sections: list[SectionResult] = []

    # Phase-1: serial collectors (60s each)
    async with acquire() as conn:
        ws = await safe_collect(collect_wealth_state(conn, as_of), "wealth_state", 60.0)
        to = await safe_collect(collect_tax_operational(conn, as_of), "tax_operational", 60.0)
    v2_sections.extend([ws, to])

    mc = await safe_collect(collect_market_context(as_of), "market_context", 60.0)
    v2_sections.append(mc)

    at = await safe_collect(collect_active_theses(as_of), "active_theses", 60.0)
    v2_sections.append(at)

    # Extract regime for downstream collectors that can skip their own DB fetch
    regime_label = _regime_from_section(mc)

    # Phase-2: parallel collectors (30s each)
    parallel_results = await asyncio.gather(
        safe_collect(collect_watchlist(as_of), "watchlist", 30.0),
        safe_collect(
            collect_underlying_drivers(as_of, regime_label=regime_label),
            "underlying_drivers", 30.0
        ),
        safe_collect(
            collect_new_ideas(as_of, regime_label=regime_label),
            "new_ideas", 30.0
        ),
        safe_collect(collect_theme_dashboard(as_of), "theme_dashboard", 30.0),
        safe_collect(collect_opportunity_cost(as_of), "opportunity_cost", 30.0),
    )
    v2_sections.extend(parallel_results)

    # Footer (synchronous, pure)
    footer = collect_section_health(v2_sections)
    v2_sections.append(footer)

    snapshot = build_snapshot(v2_sections)

    # Rendering: V2 template if gate is on, else V1 backward-compat path
    if os.environ.get("ASXOS_V2_BRIEF_ENABLED") == "1":
        from asxos.domain.brief.renderer import render_v2_html
        rendered_html = render_v2_html(
            Brief(as_of=as_of, sections=tuple(v2_sections), snapshot=snapshot)
        )
    else:
        from asxos.brief.compose import collect as v1_collect
        from asxos.brief.compose import render_html as v1_render_html
        v1_data = await v1_collect(as_of)
        rendered_html = v1_render_html(v1_data)

    brief = Brief(
        as_of=as_of,
        sections=tuple(v2_sections),
        snapshot=snapshot,
        rendered_html=rendered_html,
    )

    persistence_error = await _persist_brief_run(brief)
    return replace(brief, persistence_error=persistence_error)


async def _persist_brief_run(brief: Brief) -> str | None:
    """Insert ``brief_runs`` and return a redacted error for the delivery job.

    Persistence failure does not prevent the already-rendered primary brief from
    being sent. It is not treated as success either: ``jobs.compose_brief`` sends
    first, then raises the returned error inside ``JobMonitor`` so the run is
    durably failed and the failure healthcheck is pinged.
    """
    try:
        snapshot_json = {
            "red_count": brief.snapshot.red_count,
            "yellow_count": brief.snapshot.yellow_count,
            "green_count": brief.snapshot.green_count,
            "one_thing": brief.snapshot.one_thing,
            "health_line": brief.snapshot.health_line,
            "time_estimate_min": brief.snapshot.time_estimate_min,
        }
        section_runs = {
            s.name: {
                "status": s.status.value,
                "elapsed_ms": s.elapsed_ms,
                "item_count": len(s.items),
                "error": s.error,
            }
            for s in brief.sections
        }
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO brief_runs (as_of, rendered_html, snapshot_json, section_runs)
                VALUES ($1, $2, $3, $4)
                """,
                brief.as_of,
                brief.rendered_html,
                json.dumps(snapshot_json),
                json.dumps(section_runs),
            )
        return None
    # Some driver-originated persistence failures surface as CancelledError
    # without cancelling the current task. Preserve a real task.cancel():
    # shutdown and orchestration cancellation must retain asyncio semantics.
    except asyncio.CancelledError as exc:
        task = asyncio.current_task()
        if task is not None and task.cancelling():
            raise
        error = redact_secrets(f"{type(exc).__name__}: {exc}")
        log.error("brief_runs persistence failed; primary brief remains deliverable: %s", error)
        return error
    except Exception as exc:
        error = redact_secrets(f"{type(exc).__name__}: {exc}")
        log.error("brief_runs persistence failed; primary brief remains deliverable: %s", error)
        return error
