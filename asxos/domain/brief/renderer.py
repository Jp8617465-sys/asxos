"""
Brief renderer — M-Brief-V2-Sections.

render_html(brief) → str      returns the pre-rendered HTML stored on the Brief

**The V2 rendering path was DELETED under A-35** (dark-launch verdict #3, issued
2026-09-14). `render_v2_html()` loaded a frozen template that only ever rendered
when `ASXOS_V2_BRIEF_ENABLED=1`, and that variable was set in no workflow,
Makefile, `.toml` or env example — so it never rendered once. The template and
its `_archive/` README went with it, because that README said in as many words
that the copy existed only to serve this renderer. The ten collectors in
`composer.py` are untouched and remain in production.

One correction this deletion surfaced, worth keeping rather than silently
fixing: the docstring here used to say `render_html` was "used by
jobs/compose_brief.py". It is not — that job imports `render_html` from
`asxos.brief.compose`, a different function in a different module with the same
name. The one below has no production caller at all; it exists so a test can
build a `Brief` directly without a Jinja environment. Said plainly rather than
left to mislead the next reader.
"""

from __future__ import annotations

from asxos.domain.brief.types import Brief


def render_html(brief: Brief) -> str:
    """Return the HTML already rendered onto the Brief.

    No production caller: `jobs/compose_brief.py` uses the identically-named
    function in `asxos.brief.compose`. This one serves tests that construct a
    `Brief` directly, which is why the fallback below exists — a Brief built
    without going through `compose()` has no `rendered_html`.
    """
    if brief.rendered_html is not None:
        return brief.rendered_html

    return (
        f"<html><body><h1>asxos brief — {brief.as_of}</h1>"
        f"<p>{brief.snapshot.health_line}</p></body></html>"
    )
