"""
Brief renderer — M-Brief-Skeleton.

render_html(brief) → str

Phase 3 transition: delegates to the V1 brief/compose.render_html path.
Phase 4 introduces brief_v2.html.j2 behind the ASXOS_V2_BRIEF_ENABLED gate.
"""
from __future__ import annotations

from asxos.domain.brief.types import Brief


def render_html(brief: Brief) -> str:
    """Render a Brief to HTML.

    Phase 3: uses the pre-rendered HTML stored in Brief.rendered_html
    (populated by composer.compose() via the V1 rendering path).

    If rendered_html is not set (e.g. in tests that build Brief directly),
    falls back to a minimal template.
    """
    if brief.rendered_html is not None:
        return brief.rendered_html

    # Minimal fallback for test environments / direct Brief construction
    return (
        f"<html><body><h1>asxos brief — {brief.as_of}</h1>"
        f"<p>{brief.snapshot.health_line}</p></body></html>"
    )
