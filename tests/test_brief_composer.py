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
from datetime import date

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
