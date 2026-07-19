"""
Tests for M-Brief-Skeleton: safe_collect(), build_snapshot(), section states.

Covers:
  - safe_collect() timeout: mock coroutine that sleeps → SectionResult(status=timeout)
  - safe_collect() failure: mock coroutine that raises → SectionResult(status=failed)
  - safe_collect() success: normal coroutine → pass-through
  - build_snapshot() quiet: all green → time_estimate=1, affirmative health_line
  - build_snapshot() normal: yellow only → time_estimate ≥ 3
  - build_snapshot() stress: any red → time_estimate ≥ 8
  - build_snapshot() one_thing triage: overdue before regime warning
  - section_health footer: failed/timeout/no_data → appropriate SeverityItems
  - render_html: uses rendered_html if present; falls back to minimal HTML
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import asxos.domain.brief.composer as composer_mod
from asxos.domain.brief import composer
from asxos.domain.brief._runner import safe_collect
from asxos.domain.brief.collectors.section_health import collect_section_health
from asxos.domain.brief.renderer import render_html
from asxos.domain.brief.severity import (
    cgt_boundary_approaching,
    regime_warning,
    thesis_revisit_overdue,
)
from asxos.domain.brief.snapshot import build_snapshot
from asxos.domain.brief.types import (
    Brief,
    SectionResult,
    SectionStatus,
    SeverityItem,
    SeverityLevel,
    Snapshot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sr(name: str, status: SectionStatus, items=()) -> SectionResult:
    return SectionResult(name=name, status=status, items=items, elapsed_ms=0)


def _item(level: SeverityLevel, section: str, msg: str = "msg") -> SeverityItem:
    return SeverityItem(level=level, message=msg, section=section)


def _snapshot(**kw) -> Snapshot:
    defaults = {
        "red_count": 0, "yellow_count": 0, "green_count": 0,
        "one_thing": "ok", "health_line": "All green",
        "time_estimate_min": 1, "items": (),
    }
    return Snapshot(**{**defaults, **kw})


# ---------------------------------------------------------------------------
# safe_collect — timeout
# ---------------------------------------------------------------------------

def test_safe_collect_timeout() -> None:
    """A coroutine that sleeps longer than the timeout returns status=timeout."""
    async def _sleeping():
        await asyncio.sleep(60)
        return _sr("never", SectionStatus.ok)

    async def _run():
        result = await safe_collect(_sleeping(), "slow_section", timeout=0.05)
        return result

    result = asyncio.run(_run())
    assert result.status == SectionStatus.timeout
    assert result.name == "slow_section"
    assert result.error is not None
    assert "timeout" in result.error or "timed out" in result.error


def test_safe_collect_exception() -> None:
    """A coroutine that raises returns status=failed with error message."""
    async def _exploding():
        raise ValueError("something went wrong")

    async def _run():
        return await safe_collect(_exploding(), "bad_section", timeout=5.0)

    result = asyncio.run(_run())
    assert result.status == SectionStatus.failed
    assert result.name == "bad_section"
    assert "ValueError" in (result.error or "")
    assert "something went wrong" in (result.error or "")


def test_safe_collect_success() -> None:
    """A coroutine that succeeds returns its SectionResult unchanged."""
    expected = _sr("good_section", SectionStatus.ok)

    async def _fast() -> SectionResult:
        return expected

    async def _run():
        return await safe_collect(_fast(), "good_section", timeout=5.0)

    result = asyncio.run(_run())
    assert result.status == SectionStatus.ok
    assert result.name == "good_section"


def test_safe_collect_never_raises() -> None:
    """safe_collect must never propagate exceptions to the caller."""
    async def _bad():
        raise RuntimeError("DB is down")

    # Should not raise — just return a failed SectionResult
    result = asyncio.run(safe_collect(_bad(), "test", timeout=5.0))
    assert result.status == SectionStatus.failed


# ---------------------------------------------------------------------------
# build_snapshot — severity triage
# ---------------------------------------------------------------------------

def test_snapshot_quiet() -> None:
    """All sections green → time_estimate=1, affirmative health_line."""
    sections = [_sr("wealth_state", SectionStatus.ok)]
    snap = build_snapshot(sections)
    assert snap.red_count == 0
    assert snap.yellow_count == 0
    assert snap.time_estimate_min == 1
    assert "green" in snap.health_line.lower() or "clear" in snap.health_line.lower()


def test_snapshot_normal_yellow() -> None:
    """Yellow items → time_estimate ≥ 3, no 'action required'."""
    yellow = _item(SeverityLevel.yellow, "tax_operational", "CGT boundary in 15d")
    sections = [
        SectionResult("tax_operational", SectionStatus.ok, items=(yellow,), elapsed_ms=0)
    ]
    snap = build_snapshot(sections)
    assert snap.yellow_count == 1
    assert snap.red_count == 0
    assert snap.time_estimate_min >= 3
    assert "review" in snap.health_line.lower()


def test_snapshot_stress_red() -> None:
    """Red item → time_estimate ≥ 8, 'action required' in health_line."""
    red = _item(SeverityLevel.red, "active_theses", "MIN.AU review overdue by 3d")
    sections = [
        SectionResult("active_theses", SectionStatus.ok, items=(red,), elapsed_ms=0)
    ]
    snap = build_snapshot(sections)
    assert snap.red_count == 1
    assert snap.time_estimate_min >= 8
    assert "action" in snap.health_line.lower()


def test_snapshot_one_thing_triage() -> None:
    """Overdue thesis beats regime warning in one_thing triage."""
    overdue = SeverityItem(
        level=SeverityLevel.red,
        message="MIN.AU review overdue by 3d (due 2026-05-29)",
        section="active_theses",
    )
    regime = SeverityItem(
        level=SeverityLevel.yellow,
        message="Regime: risk_off_orderly — elevated risk",
        section="market_context",
    )
    sections = [
        SectionResult("active_theses", SectionStatus.ok, items=(overdue,), elapsed_ms=0),
        SectionResult("market_context", SectionStatus.ok, items=(regime,), elapsed_ms=0),
    ]
    snap = build_snapshot(sections)
    assert "overdue" in snap.one_thing.lower()


def test_snapshot_skips_failed_sections() -> None:
    """Items from failed sections are excluded from the snapshot."""
    red = _item(SeverityLevel.red, "wealth_state", "should not appear")
    sections = [
        SectionResult("wealth_state", SectionStatus.failed, items=(red,), elapsed_ms=0)
    ]
    snap = build_snapshot(sections)
    assert snap.red_count == 0


def test_snapshot_no_items_affirmative() -> None:
    """No items at all → one_thing is an affirmative message."""
    sections = [_sr("wealth_state", SectionStatus.no_data)]
    snap = build_snapshot(sections)
    assert snap.red_count == 0
    assert snap.yellow_count == 0
    assert "action" not in snap.one_thing.lower() or "no action" in snap.one_thing.lower()


# ---------------------------------------------------------------------------
# section_health footer
# ---------------------------------------------------------------------------

def test_section_health_failed_section() -> None:
    """Failed section → red item in footer."""
    sections = [
        SectionResult("wealth_state", SectionStatus.failed, items=(), elapsed_ms=0,
                      error="DB timeout"),
    ]
    footer = collect_section_health(sections)
    assert footer.status == SectionStatus.ok
    red_items = [i for i in footer.items if i.level == SeverityLevel.red]
    assert any("wealth_state" in i.message for i in red_items)


def test_section_health_timeout() -> None:
    """Timed-out section → yellow item in footer."""
    sections = [
        SectionResult("tax_operational", SectionStatus.timeout, items=(), elapsed_ms=60000),
    ]
    footer = collect_section_health(sections)
    yellow_items = [i for i in footer.items if i.level == SeverityLevel.yellow]
    assert any("tax_operational" in i.message for i in yellow_items)


def test_section_health_no_data() -> None:
    """no_data section → green item (informational, not alarming)."""
    sections = [
        SectionResult("wealth_state", SectionStatus.no_data, items=(), elapsed_ms=0),
    ]
    footer = collect_section_health(sections)
    green_items = [i for i in footer.items if i.level == SeverityLevel.green]
    assert any("wealth_state" in i.message for i in green_items)


def test_section_health_ok_sections_silent() -> None:
    """Ok sections produce no footer items (no noise)."""
    sections = [
        _sr("wealth_state", SectionStatus.ok),
        _sr("tax_operational", SectionStatus.ok),
    ]
    footer = collect_section_health(sections)
    assert len(footer.items) == 0


# ---------------------------------------------------------------------------
# Pure severity functions
# ---------------------------------------------------------------------------

def test_thesis_revisit_overdue() -> None:
    as_of = date(2026, 6, 1)
    item = thesis_revisit_overdue("MIN.AU", date(2026, 5, 28), as_of)
    assert item is not None
    assert item.level == SeverityLevel.red
    assert "MIN.AU" in item.message
    assert "4d" in item.message or "overdue" in item.message


def test_thesis_revisit_not_overdue() -> None:
    as_of = date(2026, 6, 1)
    item = thesis_revisit_overdue("MIN.AU", date(2026, 6, 5), as_of)
    assert item is None


def test_cgt_boundary_red() -> None:
    item = cgt_boundary_approaching("BHP.AU", 42, days_to_eligibility=3)
    assert item is not None
    assert item.level == SeverityLevel.red


def test_cgt_boundary_yellow() -> None:
    item = cgt_boundary_approaching("BHP.AU", 42, days_to_eligibility=15)
    assert item is not None
    assert item.level == SeverityLevel.yellow


def test_cgt_boundary_zero_already_eligible() -> None:
    item = cgt_boundary_approaching("BHP.AU", 42, days_to_eligibility=0)
    assert item is None


def test_regime_warning_disorderly() -> None:
    item = regime_warning("risk_off_disorderly")
    assert item is not None
    assert item.level == SeverityLevel.red


def test_regime_warning_orderly() -> None:
    item = regime_warning("risk_off_orderly")
    assert item is not None
    assert item.level == SeverityLevel.yellow


def test_regime_warning_neutral() -> None:
    item = regime_warning("neutral_mixed")
    assert item is None


# ---------------------------------------------------------------------------
# render_html
# ---------------------------------------------------------------------------

def test_render_html_uses_rendered_html_if_present() -> None:
    """If Brief has rendered_html, render_html returns it unchanged."""
    snap = _snapshot()
    brief = Brief(
        as_of=date(2026, 6, 1),
        sections=(),
        snapshot=snap,
        rendered_html="<html>already rendered</html>",
    )
    html = render_html(brief)
    assert html == "<html>already rendered</html>"


def test_render_html_fallback_when_no_rendered_html() -> None:
    """Without rendered_html, render_html produces minimal valid HTML."""
    snap = _snapshot(health_line="All systems green")
    brief = Brief(
        as_of=date(2026, 6, 1),
        sections=(),
        snapshot=snap,
        rendered_html=None,
    )
    html = render_html(brief)
    assert "asxos brief" in html.lower() or "2026-06-01" in html
    assert "All systems green" in html


# ---------------------------------------------------------------------------
# _gated_collect / _personal_use_enabled — risk-register R18 s766B gate
#
# jobs/compose_brief.py calls composer.compose(), which ran 8 personal-data
# collectors (theses/current_holdings/portfolio_daily_snapshots) with NO
# ASXOS_PERSONAL_USE check anywhere, masked only by render.yaml. These tests
# exercise the REAL compose()/_gated_collect()/_persist_brief_run() code, not
# a mock of compose() itself (test_brief_fallback.py's patch("jobs.
# compose_brief.v2_compose", ...) is the anti-pattern this deliberately
# avoids -- that proves nothing about compose()'s own internals). The 8
# leaf collector functions are mocked (patched at the names composer.py
# imports them under) so this doesn't need a full DB fixture per collector;
# the assertion that matters -- and the one that actually proves the fix --
# is that the mocked collector is never CALLED at all when gated off, which
# is exactly equivalent in strength to "the DB was never touched" since
# those collector functions are the sole gateway to that DB access.
# ---------------------------------------------------------------------------


def test_personal_use_enabled_exact_match_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    assert composer._personal_use_enabled() is False
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "0")
    assert composer._personal_use_enabled() is False
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    assert composer._personal_use_enabled() is True


def test_gated_collect_never_constructs_coroutine_when_gated_off() -> None:
    """The core safety property: coro_factory() itself must never be called."""
    called = {"n": 0}

    def factory():
        called["n"] += 1
        raise AssertionError("coro_factory must not be invoked when gated off")

    result = asyncio.run(
        composer._gated_collect(factory, "wealth_state", 60.0, personal_use_ok=False)
    )
    assert called["n"] == 0
    assert result.status == SectionStatus.suppressed
    assert result.name == "wealth_state"
    assert result.items == ()


def test_gated_collect_passes_through_when_gated_on() -> None:
    async def _inner() -> SectionResult:
        return _sr("wealth_state", SectionStatus.ok)

    result = asyncio.run(
        composer._gated_collect(_inner, "wealth_state", 60.0, personal_use_ok=True)
    )
    assert result.status == SectionStatus.ok


def _compose_mocks():
    """Patch composer.py's own bound names for all 10 collectors + acquire.

    Each personal-data collector mock raises if awaited, so a test only
    passes if the gate genuinely prevented the call -- not merely returned
    an unused value.
    """
    def _raising_mock(name):
        m = AsyncMock(side_effect=AssertionError(f"{name} must not run when gated off"))
        return m

    conn = MagicMock()

    @asynccontextmanager
    async def _acquire_ctx():
        yield conn

    patches = {
        "acquire": patch.object(composer_mod, "acquire", new=_acquire_ctx),
        # compose() falls back to V1's asxos.brief.compose.collect()/render_html()
        # when ASXOS_V2_BRIEF_ENABLED is unset (matching production, V2 is
        # KEEP-DARK) -- irrelevant to what these tests exercise (V2 collector
        # gating), so stubbed out rather than hitting a real, uninitialised
        # DB pool via V1's own (separately s766B-gated, but not personal-data-
        # free) collect().
        "v1_collect": patch("asxos.brief.compose.collect", new=AsyncMock(return_value=None)),
        "v1_render_html": patch("asxos.brief.compose.render_html", return_value="<html></html>"),
        "collect_wealth_state": patch.object(
            composer_mod, "collect_wealth_state", new=_raising_mock("wealth_state")
        ),
        "collect_tax_operational": patch.object(
            composer_mod, "collect_tax_operational", new=_raising_mock("tax_operational")
        ),
        "collect_active_theses": patch.object(
            composer_mod, "collect_active_theses", new=_raising_mock("active_theses")
        ),
        "collect_watchlist": patch.object(
            composer_mod, "collect_watchlist", new=_raising_mock("watchlist")
        ),
        "collect_underlying_drivers": patch.object(
            composer_mod, "collect_underlying_drivers", new=_raising_mock("underlying_drivers")
        ),
        "collect_new_ideas": patch.object(
            composer_mod, "collect_new_ideas", new=_raising_mock("new_ideas")
        ),
        "collect_theme_dashboard": patch.object(
            composer_mod, "collect_theme_dashboard", new=_raising_mock("theme_dashboard")
        ),
        "collect_opportunity_cost": patch.object(
            composer_mod, "collect_opportunity_cost", new=_raising_mock("opportunity_cost")
        ),
        "collect_market_context": patch.object(
            composer_mod,
            "collect_market_context",
            new=AsyncMock(
                return_value=SectionResult(
                    name="market_context", status=SectionStatus.ok, items=(),
                    elapsed_ms=0, metadata={"regime_label": "neutral_mixed"},
                )
            ),
        ),
        "_persist_brief_run": patch.object(
            composer_mod, "_persist_brief_run", new=AsyncMock(return_value=None)
        ),
    }
    return patches


_PERSONAL_COLLECTOR_SECTIONS = (
    "wealth_state", "tax_operational", "active_theses", "watchlist",
    "underlying_drivers", "new_ideas", "theme_dashboard", "opportunity_cost",
)


@pytest.mark.asyncio
async def test_compose_suppresses_all_personal_collectors_when_gate_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    patches = _compose_mocks()
    with patches["acquire"], patches["v1_collect"], patches["v1_render_html"], \
         patches["collect_wealth_state"], patches["collect_tax_operational"], \
         patches["collect_active_theses"], patches["collect_watchlist"], \
         patches["collect_underlying_drivers"], patches["collect_new_ideas"], \
         patches["collect_theme_dashboard"], patches["collect_opportunity_cost"], \
         patches["collect_market_context"], patches["_persist_brief_run"]:
        brief = await composer.compose(date(2026, 7, 19))

    by_name = {s.name: s for s in brief.sections}
    for name in _PERSONAL_COLLECTOR_SECTIONS:
        assert by_name[name].status == SectionStatus.suppressed, name
    # market_context carries no personal data and must NOT be suppressed.
    assert by_name["market_context"].status == SectionStatus.ok
    # section_health (footer) is pure/synchronous and always runs.
    assert "section_health" in by_name


@pytest.mark.asyncio
async def test_compose_runs_all_personal_collectors_when_gate_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    ok_result = {
        name: AsyncMock(
            return_value=SectionResult(name=name, status=SectionStatus.ok, items=(), elapsed_ms=0)
        )
        for name in _PERSONAL_COLLECTOR_SECTIONS
    }
    conn = MagicMock()

    @asynccontextmanager
    async def _acquire_ctx():
        yield conn

    with patch.object(composer_mod, "acquire", new=_acquire_ctx), \
         patch("asxos.brief.compose.collect", new=AsyncMock(return_value=None)), \
         patch("asxos.brief.compose.render_html", return_value="<html></html>"), \
         patch.object(composer_mod, "collect_wealth_state", new=ok_result["wealth_state"]), \
         patch.object(composer_mod, "collect_tax_operational", new=ok_result["tax_operational"]), \
         patch.object(composer_mod, "collect_active_theses", new=ok_result["active_theses"]), \
         patch.object(composer_mod, "collect_watchlist", new=ok_result["watchlist"]), \
         patch.object(
             composer_mod, "collect_underlying_drivers", new=ok_result["underlying_drivers"]
         ), \
         patch.object(composer_mod, "collect_new_ideas", new=ok_result["new_ideas"]), \
         patch.object(composer_mod, "collect_theme_dashboard", new=ok_result["theme_dashboard"]), \
         patch.object(
             composer_mod, "collect_opportunity_cost", new=ok_result["opportunity_cost"]
         ), \
         patch.object(
             composer_mod,
             "collect_market_context",
             new=AsyncMock(
                 return_value=SectionResult(
                     name="market_context", status=SectionStatus.ok, items=(),
                     elapsed_ms=0, metadata={"regime_label": "neutral_mixed"},
                 )
             ),
         ), \
         patch.object(composer_mod, "_persist_brief_run", new=AsyncMock(return_value=None)):
        brief = await composer.compose(date(2026, 7, 19))

    by_name = {s.name: s for s in brief.sections}
    for name in _PERSONAL_COLLECTOR_SECTIONS:
        assert by_name[name].status == SectionStatus.ok, name
        ok_result[name].assert_awaited()


# ---------------------------------------------------------------------------
# _persist_brief_run — defense-in-depth redaction
# ---------------------------------------------------------------------------


_SENSITIVE_HTML = "<html><body>BHP.AU: 50 shares, cost base $4,200</body></html>"


def _brief_with_sensitive_one_thing() -> Brief:
    snap = _snapshot(
        one_thing="BHP.AU: STOP BREACH at $41.20, lot 7",
        health_line="1 red item: BHP.AU stop violated",
    )
    return Brief(as_of=date(2026, 7, 19), sections=(), snapshot=snap, rendered_html=_SENSITIVE_HTML)


@pytest.mark.asyncio
async def test_persist_brief_run_redacts_when_gate_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=None)

    @asynccontextmanager
    async def _acquire_ctx():
        yield conn

    with patch.object(composer_mod, "acquire", new=_acquire_ctx):
        await composer._persist_brief_run(_brief_with_sensitive_one_thing())

    call_args = conn.execute.call_args[0]
    snapshot_json = json.loads(call_args[3])
    assert "BHP.AU" not in snapshot_json["one_thing"]
    assert "BHP.AU" not in snapshot_json["health_line"]
    assert snapshot_json["one_thing"] == composer._REDACTED
    assert snapshot_json["health_line"] == composer._REDACTED
    # rendered_html (security-engineer finding, 2026-07-19): the currently-
    # active V1-fallback branch's HTML must also be redacted, not just the
    # snapshot_json fields -- it's the 2nd positional arg (index 2) after sql.
    rendered_html_arg = call_args[2]
    assert "BHP.AU" not in rendered_html_arg
    assert rendered_html_arg == composer._REDACTED


@pytest.mark.asyncio
async def test_persist_brief_run_passes_through_when_gate_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=None)

    @asynccontextmanager
    async def _acquire_ctx():
        yield conn

    with patch.object(composer_mod, "acquire", new=_acquire_ctx):
        await composer._persist_brief_run(_brief_with_sensitive_one_thing())

    call_args = conn.execute.call_args[0]
    snapshot_json = json.loads(call_args[3])
    assert snapshot_json["one_thing"] == "BHP.AU: STOP BREACH at $41.20, lot 7"
    assert call_args[2] == _SENSITIVE_HTML
