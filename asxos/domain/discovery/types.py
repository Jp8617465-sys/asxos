"""Discovery contracts — an opportunity and the thesis plan derived from it."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import Field, model_validator

from asxos.domain.decision_engine.types import Contract


class ThesisPlan(Contract):
    """The system's proposed price plan, by the baseline §5 conventions.

    target = the model's registered value (probability-weighted, Ke mid);
    entry band = 0.65-0.80 x target (a 20% margin of safety at the top);
    stop = 0.80 x entry upper (20% drawdown from entry); horizon 12 months.
    James can change the convention (sprint S4); the constants live in
    `ranker.py` so a change is one line and one test.
    """

    target_price: Decimal = Field(gt=0)
    entry_band_lower: Decimal = Field(gt=0)
    entry_band_upper: Decimal = Field(gt=0)
    stop_price: Decimal = Field(gt=0)
    timeline_days: int = Field(gt=0)
    close_inside_band: bool

    @model_validator(mode="after")
    def validate_ordering(self) -> Self:
        if not self.stop_price < self.entry_band_lower <= self.entry_band_upper < self.target_price:
            raise ValueError("plan must satisfy stop < entry lower <= entry upper < target")
        return self


class Opportunity(Contract):
    """One name the screen would propose, with every figure it was ranked on."""

    symbol: str = Field(min_length=1, max_length=40)
    run_id: str = Field(min_length=1, max_length=200)
    run_content_hash: str = Field(min_length=64, max_length=64)
    as_of: date
    last_close: Decimal = Field(gt=0)
    last_close_dt: date
    value_registered: Decimal = Field(gt=0)
    value_average_roe: Decimal = Field(gt=0)
    value_to_price_registered: Decimal = Field(gt=0)
    value_to_price_average_roe: Decimal = Field(gt=0)
    value_to_price_min: Decimal = Field(gt=0)
    roe_trailing: Decimal
    roe_average: Decimal
    roe_average_is_fallback: bool
    ke_mid: Decimal = Field(gt=0)
    adv_aud: Decimal = Field(ge=0)
    market_cap_aud: Decimal = Field(ge=0)
    liquidity_factor: Decimal = Field(ge=0, le=1)
    score: Decimal = Field(ge=0)
    flags: tuple[str, ...] = ()
    plan: ThesisPlan
    screening_run_id: int = Field(ge=1)
