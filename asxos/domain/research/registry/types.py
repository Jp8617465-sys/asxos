"""Stage 2 contracts: ResearchHypothesis, StrategyVersion, ResearchRun.

All three subclass the decision engine's `ContentAddressedContract`, so they
are frozen, float-free, UTC-only, and self-verifying by SHA-256 — the same
properties migration 0048 relies on for round-trip fidelity. Nothing here
references a model version, an allocation flag, or a holding.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from asxos.domain.decision_engine.types import ContentAddressedContract
from asxos.domain.research.registry.promotion import PROMOTION_STATES, PromotionState

FactorName = Literal["momentum_12_1"]
Rebalance = Literal["monthly"]
RunOutcome = Literal["evaluated", "fail"]

_BENCHMARK_UNAVAILABLE = (
    "unavailable — AXJOA.INDX (accumulation index) is absent from prices; "
    "F1 benchmark work order not yet delivered. Never proxied."
)


class ResearchHypothesis(ContentAddressedContract):
    """A falsifiable statement: factor × universe × rebalance × horizon × cost."""

    hypothesis_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    statement: str = Field(min_length=1, max_length=4000)
    factor: FactorName
    universe_rule: str = Field(min_length=1, max_length=500)
    rebalance: Rebalance
    horizon_trading_days: int = Field(ge=1, le=252)
    cost_bps_per_side: Decimal = Field(ge=Decimal("0"), le=Decimal("500"))
    falsifier: str = Field(min_length=1, max_length=2000)
    registered_by: str = Field(min_length=1, max_length=100)
    created_at: datetime


class StrategyVersion(ContentAddressedContract):
    """One concrete parameterisation of a hypothesis, bound to its code."""

    strategy_version_id: str = Field(min_length=1, max_length=200)
    hypothesis_id: str = Field(min_length=1, max_length=200)
    parameters: dict[str, str]
    code_ref: str = Field(min_length=1, max_length=300)
    promotion_state: PromotionState = "research"
    created_at: datetime

    @field_validator("promotion_state")
    @classmethod
    def _state_is_known(cls, value: str) -> str:
        if value not in PROMOTION_STATES:
            raise ValueError(f"unknown promotion_state {value!r}")
        return value


class ResearchRun(ContentAddressedContract):
    """One evaluation of one StrategyVersion over one panel — pass or fail."""

    run_id: str = Field(min_length=1, max_length=200)
    hypothesis_id: str = Field(min_length=1, max_length=200)
    strategy_version_id: str = Field(min_length=1, max_length=200)
    as_of: date
    panel_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: RunOutcome
    failure_reason: str | None = None
    evaluation: dict[str, object]
    benchmark: str = _BENCHMARK_UNAVAILABLE
    alpha_claim: str = (
        "none — this run establishes process reproducibility, not edge. "
        "target-architecture.md Errata: a few decisions a year cannot prove alpha."
    )
    variants_tried: int = Field(ge=1)
    created_at: datetime

    @field_validator("evaluation")
    @classmethod
    def _evaluation_is_json_native(cls, value: dict[str, object]) -> dict[str, object]:
        def walk(v: object) -> None:
            if isinstance(v, float):
                raise ValueError("evaluation must not contain floats")
            if isinstance(v, Decimal):
                raise ValueError("evaluation must encode figures as decimal strings")
            if isinstance(v, dict):
                for item in v.values():
                    walk(item)
            elif isinstance(v, list | tuple):
                for item in v:
                    walk(item)
        walk(value)
        return value
