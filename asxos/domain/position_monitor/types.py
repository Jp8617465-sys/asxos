"""Position monitor domain types — M-Position-Monitor."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal


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

    # Account type (from holding_lots; used for CGT break-even calc)
    account_type: str = "individual"

    # Price type flag — intraday vs confirmed close
    price_type: Literal["intraday", "close"] = "close"

    # Optional context: volume + short interest (manual prompts)
    volume_vs_avg_pct: Decimal | None = None    # today's vol / 30d avg × 100
    short_interest_pct: Decimal | None = None   # % of float sold short

    # Analyst consensus (loaded from thesis DB row if populated)
    analyst_buy_count: int | None = None
    analyst_neutral_count: int | None = None
    analyst_sell_count: int | None = None
    analyst_consensus_target: Decimal | None = None


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
    component_moves: tuple[dict[str, Any], ...]
    cross_layer_obs: tuple[str, ...]
    scenarios: tuple[ScenarioState, ...] = field(default_factory=tuple)
