"""Position monitor domain types — M-Position-Monitor."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class MonitorInput:
    """All inputs for a single monitor run."""

    symbol: str
    as_of: date

    # Price levels (auto-fetched from EODHD)
    current_price: Decimal
    ma_50d: Decimal
    ma_200d: Decimal
    avg_weekly_move: Decimal    # mean |weekly return| over last 4 weeks

    # Macro drivers (auto-fetched from FRED; negative = favourable)
    vix_5d_move: Decimal        # % change; falling = good for growth stocks
    hy_oas_5d_move: Decimal     # % change; tightening = good

    # Sentiment (manual prompts — no free Stocktwits API)
    retail_ratio: Decimal       # current mentions / 90d avg; 1.0 = normal
    news_sentiment: Decimal     # normalised [0, 1]; Stocktwits bullish ratio

    # Optional position context (loaded from thesis + holding_lots if available)
    stop_price: Decimal | None = None
    cost_usd: Decimal | None = None
    shares: Decimal | None = None
    acquired: date | None = None
    cgt_date: date | None = None
    regime_label: str | None = None


@dataclass(frozen=True)
class ScenarioState:
    code: str
    name: str
    status: str         # confirmed | ON TRACK | active | pending | TRIGGERED | risky
    confirmation: str
    invalidation: str


@dataclass(frozen=True)
class MonitorResult:
    """Full output from a single monitor run."""

    inputs: MonitorInput
    stage_label: str
    conditions_fired: list[str]
    underlying_label: str
    weighted_movement: Decimal
    component_moves: tuple[dict, ...]
    cross_layer_obs: tuple[str, ...]
    scenarios: tuple[ScenarioState, ...] = field(default_factory=tuple)
