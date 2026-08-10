"""Pure Jinja renderer for an admitted decision brief."""

from __future__ import annotations

from pathlib import Path

import jinja2

from asxos.domain.decision_engine.types import DecisionBrief

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "brief" / "templates"
_TEMPLATE_NAME = "decision_engine_prototype.html.j2"


def render_decision_brief(brief: DecisionBrief) -> str:
    """Render without recalculating any finance, challenge, or constraint logic."""
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = environment.get_template(_TEMPLATE_NAME)
    return template.render(brief=brief)
