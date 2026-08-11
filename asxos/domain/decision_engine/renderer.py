"""Pure Jinja renderer for an admitted decision brief."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, assert_never

import jinja2

from asxos.domain.decision_engine.types import (
    DecisionBrief,
    DecisionPacket,
    MemoVerdict,
    RecommendationState,
    require_utc,
)

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "brief" / "templates"
_TEMPLATE_NAME = "decision_engine_prototype.html.j2"

PresentationTone = Literal["positive", "caution", "review", "blocked", "expired"]


@dataclass(frozen=True)
class DecisionPresentation:
    """Exhaustive, non-financial presentation state derived from one packet."""

    recommendation_state: RecommendationState
    verdict: MemoVerdict
    tone: PresentationTone
    expired: bool
    actionable: bool
    status_label: str
    size_label: str
    decision_ask: str


def _tone_for(state: RecommendationState) -> PresentationTone:
    match state:
        case "initiate" | "add":
            return "positive"
        case "trim" | "exit_review":
            return "caution"
        case "watch":
            return "review"
        case "avoid" | "abstain":
            return "blocked"
        case _ as unreachable:
            assert_never(unreachable)


def presentation_for(
    packet: DecisionPacket, *, evaluated_at: datetime
) -> DecisionPresentation:
    """Derive the ruled memo state and expiry admission without finance logic."""
    evaluated_at = require_utc(evaluated_at, field_name="evaluated_at")
    expired = packet.is_expired_at(evaluated_at)
    actionable = packet.is_actionable_at(evaluated_at)
    verdict = packet.memo_verdict
    if expired:
        return DecisionPresentation(
            recommendation_state=packet.recommendation_state,
            verdict=verdict,
            tone="expired",
            expired=True,
            actionable=False,
            status_label=f"EXPIRED - {verdict}",
            size_label="non-actionable - refresh required",
            decision_ask="Packet expired. Generate a new governed packet before any action.",
        )
    size_label = (
        f"size {packet.size_range.minimum_pct}-{packet.size_range.maximum_pct}% - paper only"
        if actionable
        else "non-actionable - paper only"
    )
    return DecisionPresentation(
        recommendation_state=packet.recommendation_state,
        verdict=verdict,
        tone=_tone_for(packet.recommendation_state),
        expired=False,
        actionable=actionable,
        status_label=verdict,
        size_label=size_label,
        decision_ask=packet.decision_ask,
    )


def render_decision_brief(
    brief: DecisionBrief, *, evaluated_at: datetime | None = None
) -> str:
    """Render one revalidated truth without recalculating financial logic."""
    rendered_at = require_utc(
        evaluated_at or datetime.now(UTC), field_name="evaluated_at"
    )
    admitted = DecisionBrief.model_validate(brief.model_dump(mode="python"))
    case_views = tuple(
        (case, presentation_for(case.decision, evaluated_at=rendered_at))
        for case in admitted.cases
    )
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(
            enabled_extensions=("html", "html.j2", "xml"), default=True
        ),
        undefined=jinja2.StrictUndefined,
    )
    template = environment.get_template(_TEMPLATE_NAME)
    return template.render(brief=admitted, case_views=case_views, rendered_at=rendered_at)
