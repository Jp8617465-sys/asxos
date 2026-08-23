"""
Brief renderer — M-Brief-V2-Sections.

render_html(brief) → str      (backward-compat alias, used by jobs/compose_brief.py)
render_v2_html(brief) → str   (new V2 Jinja path, used when ASXOS_V2_BRIEF_ENABLED=1)

Phase 3: delegates to the stored Brief.rendered_html (populated by V1 path).
Phase 4: render_v2_html() drives the new 10-section template.
"""

from __future__ import annotations

from pathlib import Path

import jinja2

from asxos.domain.brief.types import Brief

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "brief" / "templates"
_V2_TEMPLATE = "_archive/brief_v2.html.j2"  # frozen; canonical live template is brief.html.j2

_env: jinja2.Environment | None = None


def _get_env() -> jinja2.Environment:
    global _env
    if _env is None:
        _env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )
    return _env


def render_v2_html(brief: Brief) -> str:
    """Render a Brief using the V2 Jinja2 template (10 sections + snapshot)."""
    tpl = _get_env().get_template(_V2_TEMPLATE)
    return tpl.render(brief=brief)


def render_html(brief: Brief) -> str:
    """Backward-compat alias.

    Returns the pre-rendered HTML stored in Brief.rendered_html.
    If not set (e.g. in tests that build Brief directly), falls back to a
    minimal template so tests don't need a full Jinja environment.
    """
    if brief.rendered_html is not None:
        return brief.rendered_html

    return (
        f"<html><body><h1>asxos brief — {brief.as_of}</h1>"
        f"<p>{brief.snapshot.health_line}</p></body></html>"
    )
