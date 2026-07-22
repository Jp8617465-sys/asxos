"""Structured agent-proposal schemas -- Phase 1 governance layer.

Pydantic v2 models validated against agent_runs.proposed_object before any
write. Agents produce these typed objects, never SQL (doc Section 4.2).

Every evidence_citation_ids entry must reference an agent_evidence /
thesis_evidence row with tier != 'speculative' -- validated by the service
function (create_thesis_from_agent_run), not by the schema itself, since
that check requires a DB round-trip the schema layer doesn't have.

MacroThesisProposal/ThemeProposal/ThemeHoldingProposal were landed in Phase 1
as pure schema even though the agents that would produce them (macro-economist,
theme-researcher, instrument-selector) are Phase 2 -- the schemas have no DB
dependency and Phase 1's `--from-agent-run` CLI flag needs at least one to
validate against end-to-end in the Phase 1 done-criteria synthetic test.

ThesisProposal (the full instrument thesis -- entry band/stop/target/timeline)
lands in Phase B below, closing the gap that still stubs
asxos/domain/theses/service.py::create_thesis_from_agent_run()
(m14_candidate_agentic_thesis_drafter); wiring that consumer is Phase E.

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

import re
from decimal import Decimal
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Machine-checkable macro-thesis conditions — the macro-thesis learning loop
# (docs/proposals/macro-thesis-learning-loop-2026-07-21.md §3 Layer A).
#
# Optional structured predicates the macro-economist can emit ALONGSIDE its
# free-text catalyst/falsifier so jobs/score_macro_theses.py can evaluate them
# against accumulating market_context_current history by construction, rather
# than parsing prose. Free-text catalyst/falsifier stay authoritative for a
# human; machine_conditions is the machine-evaluable subset (may be omitted, or
# carry only the flat half of a claim — nested A AND (B OR C) trees and
# crosses_* are deferred, backend-architect §6).
#
# MacroSignal values are the market_context_current column names verbatim
# (migration 0013) — the evaluator resolves signal->column by identity and
# hard-fails on any name outside this set (a raw-SQL / stale-annotation guard).
# ---------------------------------------------------------------------------

MacroSignal = Literal[
    "asx200_close", "asx200_daily_change_pct",
    "pct_above_50d_ma", "pct_above_200d_ma", "net_new_highs_lows_10d",
    "avix", "avix_5d_change_pct", "avix_30d_band_pos",
    "rba_cash_rate", "aud_usd", "aus_10y_yield", "iron_ore_62fe",
    "us_hy_oas", "us_10y_2y_spread", "vix",
]
Comparator = Literal["gt", "gte", "lt", "lte"]        # crosses_* deferred
WindowAgg = Literal["consecutive", "any", "majority"]  # over the last `window` rows


class MachineCondition(BaseModel):
    """One comparison of a named market_context signal against a threshold over
    a trailing window. Semantics of ``aggregation`` (over the last ``window``
    daily rows, a NULL value counting as not-satisfied — never confirm/falsify
    on missing data): ``consecutive`` = every one of the last ``window`` rows
    satisfies; ``any`` = >=1 of them; ``majority`` = >50% of them. If fewer than
    ``window`` rows of history exist, the condition cannot be met (not-satisfied).
    """

    signal: MacroSignal
    op: Comparator
    threshold: Decimal
    window: int = Field(default=1, ge=1, le=60)
    aggregation: WindowAgg = "consecutive"

    @field_validator("threshold", mode="before")
    @classmethod
    def _reject_float_threshold(cls, v: object) -> object:
        # A JSON number literal deserialises to float and loses precision before
        # Decimal sees it (CLAUDE.md #5) — reject it so a lossy threshold fails
        # loud; a decimal string ("0.50") or a real Decimal/int stays exact.
        if isinstance(v, float):
            raise ValueError("threshold must be a Decimal or decimal string, not float")
        return v


class MachinePredicate(BaseModel):
    """A boolean combination of conditions. ``combine='all'`` = AND across every
    condition; ``combine='any'`` = OR. Flat only — a nested predicate tree is
    deferred (backend-architect §6)."""

    combine: Literal["all", "any"] = "all"
    conditions: list[MachineCondition] = Field(min_length=1)


class MachineConditions(BaseModel):
    """The machine-evaluable half of a macro thesis: a catalyst predicate (what
    would confirm it) and/or a falsifier predicate (what would break it). At
    least one must be present — omit the whole field otherwise."""

    catalyst: MachinePredicate | None = None
    falsifier: MachinePredicate | None = None

    @model_validator(mode="after")
    def _require_one(self) -> "MachineConditions":
        if self.catalyst is None and self.falsifier is None:
            raise ValueError(
                "machine_conditions needs a catalyst or falsifier; else omit the field"
            )
        return self


class MacroThesisProposal(BaseModel):
    """Proposal shape for macro-economist agent output (Phase 2 producer;
    schema landed in Phase 1 so the validation/CLI plumbing exists ahead of
    the agent). evidence_citation_ids reference agent_evidence.evidence_id
    rows (pre-thesis evidence — no thesis exists yet at this stage).

    machine_conditions is optional (default None) and backward-compatible: an
    existing proposal with only free-text catalyst/falsifier still validates.
    When present it is the structured, evaluable form scored by
    jobs/score_macro_theses.py (the learning loop, Layer A)."""

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
    machine_conditions: MachineConditions | None = None
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


# ---------------------------------------------------------------------------
# Phase B -- the ThesisProposal keystone (m14_candidate_agentic_thesis_drafter)
#
# The individual-investment broker-report thesis. Closes the deliberately-absent
# ThesisProposal gap named in this module's docstring and in
# theses/service.py::create_thesis_from_agent_run() (a stub until Phase E wires
# it). Design refs: the Phase A spec + architecture and the 2026-07-18
# design-hardening workflow.
#
# This validates SHAPE, not advice -- a data structure + provenance guard -- so
# it ships regardless of the personal-advice firewall register. Its load-bearing
# job: make an LLM-invented or uncited capital-relevant number structurally
# unrepresentable as trustworthy. Every number is a ReportFigure with explicit
# provenance, and prose bodies cannot carry inline capital-relevant literals.
# (north-star.md: every capital-relevant number is Decimal-exact and traces to a
# cited source, never a model guess; CLAUDE.md #5.)
# ---------------------------------------------------------------------------

ReportSectionKind = Literal[
    "identity_classification",
    "business",
    "moat",
    "capital_allocation",
    "strategy_catalysts",
    "risks_bear",
    "valuation",
    "position_plan",
    "verdict_conviction",
    "evidence_ledger",
]

# The full ordered set of section kinds, derived from the Literal so the two can
# never drift. Public for Phase C (renderer) + the rubric + tests to reuse.
REPORT_SECTION_KINDS: tuple[str, ...] = get_args(ReportSectionKind)

# Basis sections state the thesis's point of view; a rule #11 Model A datapoint
# (a monitor_only figure) may never appear in one. The schema enforces exactly
# that -- "not in a basis section" -- not "evidence_ledger only": a monitor
# figure is still accepted in the non-basis narrative sections, so confining it
# to the ledger (its intended home) is a render/review bar.
_BASIS_SECTION_KINDS = frozenset(
    {"moat", "capital_allocation", "strategy_catalysts", "valuation", "verdict_conviction"}
)

# A semantic subset, not derivable from the Literal -- so a rename in
# ReportSectionKind could silently drop a kind from the basis set and let a
# monitor_only (rule #11 Model A) figure leak into a basis section. Fail at
# import (a raise, not an assert -- assert is stripped under `python -O`).
if not _BASIS_SECTION_KINDS.issubset(REPORT_SECTION_KINDS):
    raise RuntimeError("_BASIS_SECTION_KINDS drifted from ReportSectionKind")

# Capital-relevant numeric literals that must NOT appear inline in a prose body --
# they belong in a ReportFigure so provenance is explicit. Catches leading
# currency ($/EUR/GBP/JPY), percentages, thousands-separated numbers, and
# multiples. This is a PARTIAL guard, honestly: bare digits with a word/symbol
# unit ("130 dollars", "4.64 EPS", "trades at 28 times"), spelled-out numbers,
# and trailing-cent forms ("130c") still slip -- too ambiguous to catch without
# false positives (years like FY26 / 2050, "20-year moat", "13 theses"). That
# residual is the Phase C render + review backstop, not a schema guarantee.
# The leading `\b` on the %, thousands, and multiple branches is load-bearing
# for ReDoS resistance (bounds backtracking on long digit runs) -- do not remove.
_CAPITAL_NUMBER_RE = re.compile(
    r"(?x)"
    r"(?: [$€£¥] \s? \d )"  # $130, EUR/GBP/JPY 130
    r"| (?: \b \d+ (?:\.\d+)? \s? % )"     # 12%, 12.5 %
    r"| (?: \b \d{1,3} (?:,\d{3})+ \b )"   # 1,234 (thousands separator)
    r"| (?: \b \d+ (?:\.\d+)? x \b )"      # 28x, 3.5x (multiple)
)


class ReportFigure(BaseModel):
    """A single capital-relevant number in a broker-report thesis.

    A number enters a report ONLY as one of these, never as a bare literal in a
    section body -- so provenance is always explicit and an LLM-invented or
    uncited number is structurally unrepresentable as trustworthy:

    - ``cited``       -- read directly from a source; requires >=1 evidence ref.
    - ``derived``     -- computed by a shown ``formula`` over cited inputs;
                         requires the formula AND >=1 evidence ref (the inputs).
    - ``james_input`` -- James's own stated number (his target/band); no ref needed.

    ``monitor_only`` flags a rule #11 Model A datapoint. The schema bars such a
    figure from every basis section (see ``ReportSection``); its intended home is
    the evidence_ledger, as a labelled, non-load-bearing monitor line. The
    guarantee is "not in a basis section," not "evidence_ledger only" -- a
    monitor figure is not rejected in the non-basis narrative sections.
    """

    label: str = Field(min_length=1)
    value: Decimal
    provenance: Literal["cited", "derived", "james_input"]
    evidence_citation_ids: list[int] = Field(default_factory=list)
    formula: str | None = None
    monitor_only: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def _reject_float_value(cls, v: object) -> object:
        # A JSON number deserialised via model_validate_json() arrives as a float
        # and loses precision before Decimal ever sees it (CLAUDE.md #5). Reject
        # float outright so a lossy value fails loud; a decimal string ("130.15")
        # or a real Decimal/int stays exact. Matches service.py's Decimals-as-str
        # JSONB contract, and makes model_validate_json() safe by construction.
        if isinstance(v, float):
            raise ValueError(
                "value must be a Decimal or a decimal string, not float "
                "(float loses precision; serialise numbers as strings)"
            )
        return v

    @model_validator(mode="after")
    def _check_provenance(self) -> ReportFigure:
        if self.provenance == "derived":
            if not (self.formula and self.formula.strip()):
                raise ValueError("provenance='derived' requires a non-empty formula")
            if not self.evidence_citation_ids:
                raise ValueError(
                    "provenance='derived' requires >=1 evidence_citation_ids "
                    "(the cited inputs the formula computes over)"
                )
        elif self.formula is not None:
            raise ValueError(
                f"formula is only valid for provenance='derived', not '{self.provenance}'"
            )
        if self.provenance == "cited" and not self.evidence_citation_ids:
            raise ValueError("provenance='cited' requires >=1 evidence_citation_ids")
        return self


class ReportSection(BaseModel):
    """One section of a broker-report thesis. ``body`` is PROSE ONLY --
    capital-relevant numbers live in ``figures`` (each a ReportFigure), never
    inline, so every number's provenance is explicit and checkable."""

    kind: ReportSectionKind
    body: str = Field(min_length=1)
    figures: list[ReportFigure] = Field(default_factory=list)
    evidence_citation_ids: list[int] = Field(default_factory=list)

    @field_validator("body")
    @classmethod
    def _body_prose_only(cls, v: str) -> str:
        m = _CAPITAL_NUMBER_RE.search(v)
        if m:
            raise ValueError(
                "section body is prose-only; capital-relevant number "
                f"{m.group(0)!r} must be a ReportFigure, not inline prose"
            )
        return v

    @model_validator(mode="after")
    def _check_monitor_placement(self) -> ReportSection:
        if self.kind in _BASIS_SECTION_KINDS:
            for fig in self.figures:
                if fig.monitor_only:
                    raise ValueError(
                        f"monitor_only (rule #11 Model A) figure {fig.label!r} may not "
                        f"appear in basis section '{self.kind}'; only in evidence_ledger"
                    )
        return self


class ThesisProposal(BaseModel):
    """Individual-investment broker-report thesis -- the keystone whose absence
    stubbed ``create_thesis_from_agent_run()`` and blocked coverage-framework
    Tier 3 (``m14_candidate_agentic_thesis_drafter``).

    Mirrors ``MacroThesisProposal``'s citation contract and adds the
    ReportFigure/ReportSection depth + capital-relevant Decimals no prior
    proposal type carried. Discipline-wrapper prices are ReportFigures so an
    agent can never propose an unprovenanced price. ``evidence_citation_ids``
    reference ``agent_evidence.evidence_id`` rows (tier != 'speculative',
    enforced by the service layer, not here -- needs a DB round-trip, per the
    module docstring). Deserialise with ``json.loads(raw, parse_float=Decimal)``.
    """

    symbol: str = Field(pattern=r"^[A-Z0-9]+\.(AU|US)$")
    flavour: Literal["individual_equity", "etf_fund"] = "individual_equity"
    thesis_text: str = Field(min_length=1)
    conviction_level: int | None = Field(default=None, ge=1, le=5)
    themes: list[str] = Field(default_factory=list)
    entry_band_lower: ReportFigure | None = None
    entry_band_upper: ReportFigure | None = None
    stop_price: ReportFigure | None = None
    target_price: ReportFigure | None = None
    timeline_days: int | None = Field(default=None, gt=0)
    invalidation_conditions: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)
    evidence_citation_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_shape(self) -> ThesisProposal:
        if (
            self.entry_band_lower is not None
            and self.entry_band_upper is not None
            and self.entry_band_lower.value > self.entry_band_upper.value
        ):
            raise ValueError("entry_band_lower must be <= entry_band_upper")
        # A rule #11 Model A datapoint (monitor_only) may never BE a capital lever
        # -- the entry band, stop, or target that drives enter_thesis() / the
        # position monitor. _check_monitor_placement guards sections; these four
        # top-level discipline-wrapper figures need the same guard, more sharply.
        for _name in ("entry_band_lower", "entry_band_upper", "stop_price", "target_price"):
            _fig = getattr(self, _name)
            if _fig is not None and _fig.monitor_only:
                raise ValueError(
                    f"{_name} may not be a monitor_only (rule #11 Model A) figure -- "
                    "a stop/target/entry level must be a real, non-monitor number"
                )
        kinds = [s.kind for s in self.sections]
        if len(kinds) != len(set(kinds)):
            raise ValueError("duplicate section kinds are not allowed")
        return self
