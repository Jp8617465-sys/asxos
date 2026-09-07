"""Pure Jinja renderer for an admitted decision brief."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from pathlib import Path
from typing import Final, Literal, assert_never

import jinja2

from asxos.domain.decision_engine.types import (
    DecisionBrief,
    DecisionCase,
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


def _markdown(value: str) -> str:
    """Return untrusted contract text safe to embed in a Markdown/HTML render.

    A report contains issuer and provider text.  Escaping HTML here prevents a
    source string from becoming active markup in a Markdown viewer; it does not
    rewrite or interpret the financial content.
    """
    return escape(value, quote=True)


# Only these become clickable. `EvidenceItem.source_uri` is an unrestricted
# string (types.py), and HTML-escaping does not make `javascript:` or `data:`
# safe — escaping protects the surrounding markup, not the scheme a viewer
# will execute. Everything else is rendered inert, which is also more honest:
# `asxos://`, `db://`, `agent://` and `synthetic://` are identifiers, not
# addresses a reader can follow.
_LINKABLE_URI_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})

# A closing paren would terminate the Markdown link target early and let the
# remainder escape into document text; whitespace and angle brackets likewise
# break out of the target. Any of them disqualifies the URI from linking.
_URI_BREAKOUT_CHARS: Final[str] = "()<>\"'"


def _is_linkable(uri: str) -> bool:
    scheme, separator, _rest = uri.partition(":")
    if separator != ":" or scheme.lower() not in _LINKABLE_URI_SCHEMES:
        return False
    return not any(char.isspace() or char in _URI_BREAKOUT_CHARS for char in uri)


def _source(uri: str) -> str:
    """Render one evidence source, clickable only under an approved scheme."""
    if _is_linkable(uri):
        return f"[source]({_markdown(uri)})"
    return f"source `{_markdown(uri)}`"


def _pct(value: Decimal) -> str:
    """Render an exact Decimal percentage without passing through float."""
    return f"{value.normalize():f}%"


def render_broker_report(
    case: DecisionCase, *, evaluated_at: datetime | None = None
) -> str:
    """Render the canonical DecisionCase as a human broker-report view.

    This is deliberately a renderer, not a second recommendation schema.  It
    revalidates the complete content-addressed chain and derives its verdict,
    actionability, constraints and evidence solely from that chain.  A caller
    cannot supply a separate rating, price target, or size to the report.
    """
    rendered_at = require_utc(
        evaluated_at or datetime.now(UTC), field_name="evaluated_at"
    )
    admitted = DecisionCase.model_validate(case.model_dump(mode="python"))
    presentation = presentation_for(admitted.decision, evaluated_at=rendered_at)
    thesis = admitted.thesis
    challenge = admitted.challenge
    portfolio = admitted.portfolio
    decision = admitted.decision

    evidence_lines = "\n".join(
        "- "
        f"**{_markdown(item.evidence_tier)}** · {_markdown(item.title)} — "
        f"{_markdown(item.claim)} "
        f"({_source(item.source_uri)}; known {item.known_at.isoformat()})"
        for item in admitted.evidence.items
    )
    scenario_lines = "\n".join(
        "- "
        f"**{scenario.label.title()}**: {_pct(scenario.return_pct)} "
        f"at {_pct(scenario.probability_pct)} probability — {_markdown(scenario.rationale)}"
        for scenario in thesis.scenarios
    )
    constraint_lines = "\n".join(
        "- "
        f"**{_markdown(constraint.name)}**: {_markdown(constraint.status)} "
        f"({'blocking' if constraint.blocking else 'reporting'}) — "
        f"{_markdown(constraint.detail)}"
        for constraint in portfolio.constraints
    )
    finding_lines = "\n".join(
        "- "
        f"**{_markdown(finding.severity)}** — {_markdown(finding.finding)} "
        f"Required response: {_markdown(finding.required_response)}"
        for finding in challenge.findings
    ) or "- No challenger findings recorded."
    catalyst_lines = "\n".join(f"- {_markdown(item)}" for item in thesis.catalysts)
    falsifier_lines = "\n".join(f"- {_markdown(item)}" for item in thesis.falsifiers)
    missing_lines = "\n".join(
        f"- {_markdown(item)}" for item in decision.missing_or_uncertain_inputs
    ) or "- None declared."

    size = decision.size_range
    size_line = (
        f"{_pct(size.minimum_pct)}–{_pct(size.maximum_pct)} paper range"
        if presentation.actionable
        else "0% — non-actionable paper state"
    )
    return f"""# Broker research report: {_markdown(thesis.symbol)} ({_markdown(thesis.exchange)})

- **Decision packet:** `{_markdown(decision.decision_packet_id)}`
- **As-of / knowledge cutoff:** {decision.as_of.isoformat()} / {decision.knowledge_cutoff.isoformat()}
- **Verdict:** **{presentation.status_label}**
- **Recommendation state:** `{presentation.recommendation_state}`
- **Paper sizing:** {size_line}
- **Expiry:** {decision.expires_at.isoformat()} ({_markdown(decision.expiry_reason)})

> This is single-user decision-support, not licensed financial advice. It is not an order and no broker execution occurs. It uses no Model A output.

## Decision

{_markdown(presentation.decision_ask)}

## Investment case

**Question:** {_markdown(thesis.investment_question)}

**Variant view:** {_markdown(thesis.variant_view)}

{_markdown(thesis.thesis_summary)}

### Catalysts

{catalyst_lines}

### Falsifiers

{falsifier_lines}

### Scenarios

{scenario_lines}

## Independent challenge

**Outcome:** `{challenge.outcome}`
**Strongest bear case:** {_markdown(challenge.strongest_bear_case)}

{finding_lines}

## Portfolio and policy state

- **Marginal risk:** {_markdown(portfolio.marginal_risk)}
- **Opportunity cost:** {_markdown(portfolio.opportunity_cost)}
**Tax readiness:** `{decision.tax_assessment_reference.readiness}` / `{decision.tax_assessment_reference.applicability}`

{constraint_lines}

## Missing or uncertain inputs

{missing_lines}

## Evidence manifest

{evidence_lines}

## Integrity

`DecisionCase` and every upstream artifact were revalidated before rendering.
Decision content hash: `{decision.content_hash}`
"""
