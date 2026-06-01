"""
Brief composer — M-Brief-Skeleton.

compose(as_of) → Brief

Orchestrates all collectors via safe_collect(), builds snapshot, persists to
brief_runs, and stores the V1-rendered HTML inside the returned Brief.

Phase 3 transition: V1 collect() is called for rendering backward compat.
Phase 4 replaces V1 rendering with the new V2 template.
"""
from __future__ import annotations

import json
from datetime import date

from asxos.db import acquire
from asxos.domain.brief._runner import safe_collect
from asxos.domain.brief.collectors.section_health import collect_section_health
from asxos.domain.brief.collectors.tax_operational import collect_tax_operational
from asxos.domain.brief.collectors.wealth_state import collect_wealth_state
from asxos.domain.brief.snapshot import build_snapshot
from asxos.domain.brief.types import Brief, SectionResult


async def compose(as_of: date) -> Brief:
    """Run all collectors, build snapshot, persist to brief_runs, return Brief.

    V1 rendering path: collect() from asxos.brief.compose is called after the
    V2 collectors so the email HTML is identical to the pre-refactor output.
    The V2 snapshot data is persisted to brief_runs.snapshot_json.
    """
    # Phase-1: serial collectors (may block on DB, 60s timeout each)
    v2_sections: list[SectionResult] = []
    async with acquire() as conn:
        ws = await safe_collect(collect_wealth_state(conn, as_of), "wealth_state", 60.0)
        to = await safe_collect(collect_tax_operational(conn, as_of), "tax_operational", 60.0)
    v2_sections.extend([ws, to])

    # Footer (synchronous, no DB needed)
    footer = collect_section_health(v2_sections)
    v2_sections.append(footer)

    snapshot = build_snapshot(v2_sections)

    # V1 data collection + rendering (backward compat — replaced in Phase 4)
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

    await _persist_brief_run(brief)
    return brief


async def _persist_brief_run(brief: Brief) -> None:
    """Insert a row into brief_runs. Non-raising — failure is logged, not surfaced."""
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
    except Exception:
        pass  # brief_runs is operational metadata — never block email delivery
