"""V2 brief render — signal caveat presence (Brief QA Step 1).

Imports only the renderer + types (no collectors), so this runs in the
sandbox without the heavy optional-ML dependency tree.
"""
from __future__ import annotations

from datetime import date

from asxos.domain.brief.renderer import render_v2_html
from asxos.domain.brief.types import Brief, Snapshot

_CAVEAT_MARKER = "Signal caveat:"


def _brief() -> Brief:
    snapshot = Snapshot(
        red_count=0,
        yellow_count=0,
        green_count=1,
        one_thing="",
        health_line="All clear.",
        time_estimate_min=3,
        items=(),
    )
    return Brief(as_of=date(2026, 6, 16), sections=(), snapshot=snapshot)


def test_v2_render_contains_signal_caveat() -> None:
    html = render_v2_html(_brief())
    assert _CAVEAT_MARKER in html
    assert "experimental model-derived rankings" in html
    assert "decision-support context only" in html
    assert "not trade instructions" in html


def test_v2_caveat_after_snapshot_header() -> None:
    """Caveat renders after the snapshot health line (i.e. near the top, above
    the signal-bearing sections), not buried at the bottom."""
    html = render_v2_html(_brief())
    assert html.index("All clear.") < html.index(_CAVEAT_MARKER)
