"""Position monitor domain types — M-Position-Monitor."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal


@dataclass(frozen=True)
class LotCgt:
    """One open lot's CGT ladder rung, scoped to the active profile's account_type.

    Lots are never pooled across account types: an individual and their SMSF are
    separate CGT taxpayers (ITAA 1997 s 115-100; cost bases do not combine), so a
    ladder only ever contains lots of one account_type.
    """

    quantity: Decimal
    acquired_at: date
    cost_base_normal: Decimal      # AUD, s 110-25
    cgt_eligible_date: date        # acquired + 1yr + 1day (spec §5.1)
    is_eligible: bool              # as_of >= cgt_eligible_date


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

    # Optional position context (loaded from thesis + holding_lots if available).
    # cost_native is the weighted-average cost per share in the SYMBOL'S NATIVE
    # currency (cost_base_usd for foreign lots, cost_base_normal for .AU lots) —
    # renamed from `cost_usd`, which despite its name carried the AUD CGT base and
    # produced cross-currency P&L/break-even errors on foreign symbols (R10;
    # 2026-08-09 red-team register #11). fx_rate_audusd (latest available) is set
    # for foreign symbols only, for the §5.4 break-even's AUD price leg.
    stop_price: Decimal | None = None
    cost_native: Decimal | None = None
    fx_rate_audusd: Decimal | None = None
    shares: Decimal | None = None
    acquired: date | None = None
    cgt_date: date | None = None
    regime_label: str | None = None

    # Account type (from the ACTIVE PROFILE; scopes the lot ladder + CGT break-even
    # to one taxpayer — individual and SMSF lots are never pooled).
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

    # Per-lot CGT ladder (scoped to the active account_type; empty when no open
    # lots). `cost_native`/`shares`/`cgt_date` are the position-level headline scalars
    # derived from these. `all_eligible` is True iff `lots` is non-empty AND every
    # lot is already CGT-discount-eligible — distinct from the empty-ladder case
    # where `cgt_date` is also None.
    lots: tuple[LotCgt, ...] = field(default_factory=tuple)
    all_eligible: bool = False


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
