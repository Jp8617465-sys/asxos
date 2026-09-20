"""Mandate contracts — `Goals` in, `Mandate` out. Content-addressed, Decimal-only.

`governance_status` is deliberately NOT a field of `Mandate`: it is a column
on `mandates` (0062) audited by `governance_events`, so ratifying a mandate
cannot change the hash of what was derived.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from asxos.domain.decision_engine.types import ContentAddressedContract, Contract

AccountType = Literal["individual", "smsf"]
MandateStatus = Literal["pending_review", "approved", "rejected", "retired"]
Structure = Literal["etf_only", "etf_core_plus_sleeves"]

class LiquidityNeed(Contract):
    """A dated, non-portfolio call on capital — ADR D1 §1.1 input (b)."""

    due: date
    amount_aud: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    label: str = Field(min_length=1, max_length=200)


class Goals(ContentAddressedContract):
    """What James states. Stored once per statement; never edited (0062)."""

    as_of: date
    investable_assets_aud: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    income_aud_pa: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    savings_aud_pa: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    target_wealth_aud: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    horizon_years: int = Field(ge=1, le=50)
    #: ADR D1 §1.1 input (a) — the one that was never supplied.
    drawdown_tolerance_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    #: ADR D1 §1.1 input (b) — the other one.
    liquidity_needs: tuple[LiquidityNeed, ...] = ()
    emergency_months: int = Field(ge=0, le=24)
    account_type: AccountType
    marginal_rate_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("60"), max_digits=18, decimal_places=6)
    brokerage_aud_per_side: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    stated_by: Literal["james"] = "james"

    @model_validator(mode="after")
    def _savings_within_income(self) -> Self:
        if self.savings_aud_pa > self.income_aud_pa:
            raise ValueError("savings_aud_pa cannot exceed income_aud_pa")
        return self


class Traced(Contract):
    """A derived figure and the register line or rule it traces to."""

    value: Decimal = Field(max_digits=18, decimal_places=6)
    traced_to: str = Field(min_length=1, max_length=400)


class SleeveAllocation(Contract):
    sleeve_id: str = Field(min_length=1, max_length=64)
    #: Percent of DEPLOYABLE capital (the part above the cash floor).
    weight_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)


class MandateOutputs(Contract):
    """Everything the sizer, the sleeves and the memo read. All percents are
    of capital unless the field says deployable."""

    liquidity_reserve_aud: Traced
    deployable_capital_aud: Traced
    cash_floor_pct: Traced
    min_position_aud: Traced
    #: Names the single-name sleeves may hold in total; 0 means ETF-only.
    n_single_feasible: Traced
    position_cap_pct: Traced
    equal_weight_pct: Traced
    stop_band_pct: Traced
    risk_per_position_pct: Traced
    portfolio_dd_review_pct: Traced
    #: Percent of DEPLOYABLE capital in the ETF-core sleeve.
    etf_core_pct: Traced
    sleeve_allocations: tuple[SleeveAllocation, ...]
    structure: Structure
    rebalance_cadence: Literal["monthly"] = "monthly"
    hold_band_multiple: int = Field(default=2, ge=1, le=4)
    turnover_budget_pct_pa: Traced

    @model_validator(mode="after")
    def _allocations_sum_to_deployable(self) -> Self:
        total = self.etf_core_pct.value + sum((a.weight_pct for a in self.sleeve_allocations), Decimal("0"))
        if total != Decimal("100"):
            raise ValueError(f"etf_core_pct + sleeve allocations must equal 100 % of deployable, got {total}")
        if self.structure == "etf_only" and self.sleeve_allocations:
            raise ValueError("an etf_only mandate carries no single-name sleeve allocations")
        return self


class Mandate(ContentAddressedContract):
    """The derived mandate for one Goals row under one derivation version."""

    as_of: date
    derivation_version: str = Field(min_length=1, max_length=32)
    goals_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    outputs: MandateOutputs
