"""Structured agent-proposal schemas — Phase 1 governance layer.

Pydantic v2 models validated against agent_runs.proposed_object before any
write. Agents produce these typed objects, never SQL (doc Section 4.2).

Every evidence_citation_ids entry must reference an agent_evidence /
thesis_evidence row with tier != 'speculative' -- validated by the service
function (create_thesis_from_agent_run), not by the schema itself, since
that check requires a DB round-trip the schema layer doesn't have.

No ThesisProposal type -- no Phase 1/2 agent produces a full instrument
thesis (entry band/stop/target/timeline). MacroThesisProposal/ThemeProposal/
ThemeHoldingProposal are landed now (Phase 1) as pure schema even though the
agents that would produce them (macro-economist, theme-researcher,
instrument-selector) are Phase 2 -- the schemas have no DB dependency and
Phase 1's `--from-agent-run` CLI flag needs at least one to validate against
end-to-end in the Phase 1 done-criteria synthetic test.

ThesisProposal itself is deliberately NOT defined here -- see
asxos/domain/theses/service.py::create_thesis_from_agent_run() for the
documented Phase 1/2 gap this creates (m14_candidate_agentic_thesis_drafter).

Deserialisation hazard for the implementer of whichever code first turns
agent_runs.proposed_object (raw JSONB) into one of these models: use
json.loads(raw, parse_float=Decimal), never a bare json.loads(). A bare
json.loads() turns a JSON number literal into a float before Pydantic ever
sees it -- Pydantic will coerce that float into Decimal, but precision is
already lost by then, silently violating CLAUDE.md non-negotiable #5. Not
exercised by any Phase 1 code path (no Phase 1 function constructs a
ThemeHoldingProposal from live JSONB), but load-bearing for whoever in
Phase 2 writes the first such deserialisation call.

References:
  docs/proposals/governance-first-architecture-2026-06-30.md Section 4.2
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class MacroThesisProposal(BaseModel):
    """Proposal shape for macro-economist agent output (Phase 2 producer;
    schema landed in Phase 1 so the validation/CLI plumbing exists ahead of
    the agent). evidence_citation_ids reference agent_evidence.evidence_id
    rows (pre-thesis evidence — no thesis exists yet at this stage)."""

    title: str = Field(min_length=1)
    thesis_text: str = Field(min_length=1)
    regime_quadrant: Literal[
        "rising_growth_rising_inflation",
        "rising_growth_falling_inflation",
        "falling_growth_rising_inflation",
        "falling_growth_falling_inflation",
    ]
    horizon_months: int = Field(gt=0, le=36)
    catalyst: str = Field(min_length=1)
    falsifier: str = Field(min_length=1)
    data_signals: list[str] = Field(default_factory=list)
    evidence_citation_ids: list[int] = Field(min_length=1)  # agent_evidence.evidence_id FKs


class ThemeProposal(BaseModel):
    """Proposal shape for theme-researcher agent output (Phase 2 producer).
    macro_thesis_id is optional -- a theme need not trace to a specific
    macro thesis (e.g. a bottom-up theme identified independently)."""

    theme_code: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    conviction_band: Literal["low", "medium", "high"]
    stage: Literal[
        "early", "early-institutional", "broad-institutional",
        "mainstream", "late-retail", "mature",
    ]
    macro_thesis_id: int | None = None
    evidence_citation_ids: list[int] = Field(min_length=1)


class ThemeHoldingProposal(BaseModel):
    """Proposal shape for instrument-selector agent output (Phase 2
    producer). Maps to a theme_holdings row with source='llm_inferred'
    once written -- the first real use of that existing-but-unused enum
    value (migration 0012)."""

    theme_code: str = Field(pattern=r"^[a-z0-9-]+$")
    symbol: str = Field(pattern=r"^[A-Z0-9]+\.(AU|US)$")
    exposure_strength: Decimal = Field(ge=0, le=1)
    direction: Literal["positive", "negative"]
    mechanism_text: str = Field(min_length=1)
    evidence_citation_ids: list[int] = Field(min_length=1)
