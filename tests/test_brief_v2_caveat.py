"""V2 brief render — the evidence-only caveat (mission P1-04).

Replaces the "Signal caveat" tests (Brief QA Step 1). That caveat described the
brief's content as "experimental model-derived rankings"; with the ranking engine
retired, the honest statement is the opposite one, so the copy was replaced rather
than deleted — an unlabelled brief is worse than a wrongly-labelled one.

Imports only the renderer + types (no collectors), so this runs in the
sandbox without the heavy optional-ML dependency tree.
"""
from __future__ import annotations

from datetime import date

from asxos.domain.brief.renderer import render_v2_html
from asxos.domain.brief.types import Brief, Snapshot
from asxos.domain.review.status import ReviewStatus, directive_terms

_CAVEAT_MARKER = "Evidence only."


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


def test_v2_render_contains_evidence_only_caveat() -> None:
    html = render_v2_html(_brief())
    assert _CAVEAT_MARKER in html
    assert "model-independent" in html
    for state in ReviewStatus:
        assert state.value in html
    assert "no instruction to act" in html


def test_v2_caveat_after_snapshot_header() -> None:
    """Caveat renders after the snapshot health line (i.e. near the top, above
    the evidence sections), not buried at the bottom."""
    html = render_v2_html(_brief())
    assert html.index("All clear.") < html.index(_CAVEAT_MARKER)


def test_v2_caveat_makes_no_model_claim() -> None:
    """Adversarial: the retired copy must not survive anywhere on the page."""
    html = render_v2_html(_brief())
    for token in (
        "Signal caveat",
        "model-derived rankings",
        "Model A",
        "model_a",
        "STRONG_BUY",
    ):
        assert token not in html, f"{token!r} still rendered by brief_v2.html.j2"


def test_v2_caveat_issues_no_trade_direction() -> None:
    """The V2 shell's own copy carries no directive vocabulary.

    Narrow by construction: `sections=()`, so this renders the header, snapshot
    and caveat only. It is NOT a claim about the whole page — collector-authored
    section messages render verbatim through `render_section`, and some legitimately
    contain a banned word (`asxos/domain/brief/severity.py:67` emits "CGT boundary
    in 3d — do not sell", a prohibition rather than an instruction).
    """
    b = _brief()
    assert b.sections == ()
    assert directive_terms(render_v2_html(b)) == ()
