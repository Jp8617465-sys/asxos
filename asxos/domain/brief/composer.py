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

s766B personal-use gate (risk-register R18, fixed 2026-07-19): 8 of the 10
collectors above read theses/current_holdings/portfolio_daily_snapshots
(personal-advice data) -- wealth_state, tax_operational, active_theses,
watchlist, underlying_drivers, new_ideas, theme_dashboard, opportunity_cost.
Before this fix they ran unconditionally, with no ASXOS_PERSONAL_USE check
anywhere in this file, masked only by render.yaml setting the flag on the
compose-brief cron -- the exact "render.yaml-only enforcement, no in-code
backstop" pattern this session already found and fixed for
jobs/compute_opportunity_cost.py. Worse: the leak into brief_runs was
unconditional regardless of ASXOS_V2_BRIEF_ENABLED too, since the snapshot
is built before the V1-vs-V2 render branch is chosen.

Fix, in one file, zero collector changes: `_gated_collect()` wraps the 8
personal collectors so their collect_*() coroutine is never even
constructed (so it never touches the DB) when the flag is unset -- reusing
the ALREADY-wired SectionStatus.suppressed (new_ideas.py already uses it
for risk-off regime suppression; build_snapshot/collect_section_health/
brief_v2.html.j2 already all handle it correctly). market_context and
section_health are NOT personal data and stay outside the gate, matching
portfolio-conventions.md's R9 precedent (best-effort degrade, not a
blackout of the whole brief). `_persist_brief_run()` separately redacts
one_thing/health_line as defense-in-depth, independent of the collector
gate, so a future ungated 9th collector still can't leak through this
specific write path.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any

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
from asxos.domain.brief.types import Brief, SectionResult, SectionStatus

_REDACTED = "(redacted — ASXOS_PERSONAL_USE not set)"


def _regime_from_section(market_ctx: SectionResult) -> str | None:
    """Extract regime label from market_context SectionResult metadata."""
    if market_ctx.metadata:
        return market_ctx.metadata.get("regime_label")
    return None


def _personal_use_enabled() -> bool:
    """True iff ASXOS_PERSONAL_USE=1 (s766B gate, risk-register R18)."""
    return os.environ.get("ASXOS_PERSONAL_USE") == "1"


def _suppressed_section(name: str) -> SectionResult:
    """Placeholder for a personal-data collector skipped by the s766B gate."""
    return SectionResult(
        name=name,
        status=SectionStatus.suppressed,
        items=(),
        elapsed_ms=0,
        error="ASXOS_PERSONAL_USE is not set to '1' — personal-data section suppressed.",
    )


async def _gated_collect(
    coro_factory: Callable[[], Coroutine[Any, Any, SectionResult]],
    section_name: str,
    timeout: float,
    *,
    personal_use_ok: bool,
) -> SectionResult:
    """Gate wrapper for the 8 personal-data collectors (risk-register R18).

    When personal_use_ok is False, coro_factory is never called -- the
    underlying collect_*() coroutine object is never constructed, so it
    never touches the DB. market_context and section_health are NOT routed
    through this wrapper (they carry no personal data); a future
    model-independent collector should follow their example, not this one's.
    """
    if not personal_use_ok:
        return _suppressed_section(section_name)
    return await safe_collect(coro_factory(), section_name, timeout)


async def compose(as_of: date) -> Brief:
    """Run all collectors, build snapshot, persist to brief_runs, return Brief."""
    v2_sections: list[SectionResult] = []
    personal_use_ok = _personal_use_enabled()

    # Phase-1: serial collectors (60s each). wealth_state/tax_operational/
    # active_theses are personal-data (gated); market_context is not.
    async with acquire() as conn:
        ws = await _gated_collect(
            lambda: collect_wealth_state(conn, as_of), "wealth_state", 60.0,
            personal_use_ok=personal_use_ok,
        )
        to = await _gated_collect(
            lambda: collect_tax_operational(conn, as_of), "tax_operational", 60.0,
            personal_use_ok=personal_use_ok,
        )
    v2_sections.extend([ws, to])

    mc = await safe_collect(collect_market_context(as_of), "market_context", 60.0)
    v2_sections.append(mc)

    at = await _gated_collect(
        lambda: collect_active_theses(as_of), "active_theses", 60.0,
        personal_use_ok=personal_use_ok,
    )
    v2_sections.append(at)

    # Extract regime for downstream collectors that can skip their own DB fetch
    regime_label = _regime_from_section(mc)

    # Phase-2: parallel collectors (30s each) -- all 5 are personal-data (gated).
    parallel_results = await asyncio.gather(
        _gated_collect(
            lambda: collect_watchlist(as_of), "watchlist", 30.0,
            personal_use_ok=personal_use_ok,
        ),
        _gated_collect(
            lambda: collect_underlying_drivers(as_of, regime_label=regime_label),
            "underlying_drivers", 30.0,
            personal_use_ok=personal_use_ok,
        ),
        _gated_collect(
            lambda: collect_new_ideas(as_of, regime_label=regime_label),
            "new_ideas", 30.0,
            personal_use_ok=personal_use_ok,
        ),
        _gated_collect(
            lambda: collect_theme_dashboard(as_of), "theme_dashboard", 30.0,
            personal_use_ok=personal_use_ok,
        ),
        _gated_collect(
            lambda: collect_opportunity_cost(as_of), "opportunity_cost", 30.0,
            personal_use_ok=personal_use_ok,
        ),
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

    await _persist_brief_run(brief)
    return brief


async def _persist_brief_run(brief: Brief) -> None:
    """Insert a row into brief_runs. Non-raising — failure never blocks email.

    one_thing/health_line/rendered_html are redacted when ASXOS_PERSONAL_USE
    is unset, independent of the _gated_collect check upstream and of V1's
    own per-collector gates in asxos/brief/compose.py (risk-register R18
    defense-in-depth, extended 2026-07-19 after a security-engineer review
    found V1's rendered_html -- the branch that actually runs today, since
    ASXOS_V2_BRIEF_ENABLED is unset in production -- was the one field this
    function wrote unredacted). A future collector or render path added
    without going through an upstream gate still cannot leak personal data
    through this specific write path.
    """
    try:
        personal_use_ok = _personal_use_enabled()
        snapshot_json = {
            "red_count": brief.snapshot.red_count,
            "yellow_count": brief.snapshot.yellow_count,
            "green_count": brief.snapshot.green_count,
            "one_thing": brief.snapshot.one_thing if personal_use_ok else _REDACTED,
            "health_line": brief.snapshot.health_line if personal_use_ok else _REDACTED,
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
        rendered_html = brief.rendered_html if personal_use_ok else _REDACTED
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO brief_runs (as_of, rendered_html, snapshot_json, section_runs)
                VALUES ($1, $2, $3, $4)
                """,
                brief.as_of,
                rendered_html,
                json.dumps(snapshot_json),
                json.dumps(section_runs),
            )
    except Exception:
        pass  # brief_runs is operational metadata — never block email delivery
