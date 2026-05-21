"""
Shared data types for the tax module.

All monetary values are Decimal — never float. Boundaries are pinned by
docs/foundation/spec/tax-alpha.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from fractions import Fraction
from typing import Literal

AccountType = Literal["individual", "smsf"]


# spec §2: SMSF CGT discount is exactly 1/3, individual is 50%.
CGT_DISCOUNT_INDIVIDUAL = Decimal("0.5")
CGT_DISCOUNT_SMSF = Decimal(Fraction(1, 3).numerator) / Decimal(Fraction(1, 3).denominator)

# spec §3: default corporate rate when per-security value is missing.
DEFAULT_CORPORATE_TAX_RATE = Decimal("0.30")

# spec §7: Medicare on taxable income at 2% (individuals only).
MEDICARE_LEVY_RATE = Decimal("0.02")

# spec §4.2 / §6: SMSF base tax rate before ECPI / Div 296.
SMSF_TAX_RATE = Decimal("0.15")


@dataclass(frozen=True)
class IndividualConfig:
    """spec §2/§4.1 — individual taxpayer inputs."""

    marginal_rate: Decimal
    medicare_levy_rate: Decimal = MEDICARE_LEVY_RATE
    franking_refundable: bool = True  # spec §4.1
    carried_forward_capital_loss: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        # spec §10: negative marginal rate or > 0.5 is rejected
        if not (Decimal("0") <= self.marginal_rate <= Decimal("0.5")):
            raise ValueError(
                f"marginal_rate {self.marginal_rate} out of valid range [0, 0.5]"
            )


@dataclass(frozen=True)
class SMSFConfig:
    """spec §2/§4.2/§6 — SMSF inputs."""

    fund_pension_proportion: Decimal  # [0.0, 1.0]
    fund_segregated_eligible: bool = False  # spec §2
    div296_election_made: bool = False  # spec §6.4
    div296_reset_date: date | None = None
    carried_forward_capital_loss: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not (Decimal("0") <= self.fund_pension_proportion <= Decimal("1")):
            raise ValueError(
                f"fund_pension_proportion {self.fund_pension_proportion} "
                "out of valid range [0.0, 1.0]"
            )


@dataclass(frozen=True)
class Dividend:
    """A dividend record. cash_dividend is the AUD cash, franking_pct in [0, 1].
    corporate_tax_rate from the underlying security (spec §3)."""

    symbol: str
    pay_date: date
    cash_dividend: Decimal
    franking_pct: Decimal
    corporate_tax_rate: Decimal = DEFAULT_CORPORATE_TAX_RATE
    franking_credit_override: Decimal | None = None  # spec §3 audit Issue 7

    def __post_init__(self) -> None:
        # spec §10: zero cash + non-zero franking credit is malformed
        if self.cash_dividend == 0 and (
            self.franking_credit_override is not None
            and self.franking_credit_override > 0
        ):
            raise ValueError("zero cash dividend with non-zero franking credit is malformed")
        if not (Decimal("0") <= self.franking_pct <= Decimal("1")):
            raise ValueError(f"franking_pct {self.franking_pct} out of range [0, 1]")


@dataclass(frozen=True)
class CapitalGain:
    """A single CGT event (disposal). `discountable` is the §5.1 12-month test."""

    symbol: str
    gain_aud: Decimal  # negative for losses
    discountable: bool
    holding_period_days: int  # informational; eligibility is calendar-based


@dataclass(frozen=True)
class HoldingLot:
    """Lot-level position. Mirrors the holding_lots schema (migration 0001)."""

    lot_id: int
    symbol: str
    acquired_at: date
    quantity: Decimal
    cost_base_normal: Decimal  # spec §6.4
    cost_base_div296: Decimal
    account_type: AccountType = "individual"
    disposed_at: date | None = None
    disposal_proceeds: Decimal | None = None


@dataclass(frozen=True)
class LotSelection:
    """Result of a sale: which lots were drawn down and the realised gain."""

    lot_id: int
    qty_sold: Decimal
    realised_gain_aud: Decimal
    holding_period_days: int
    discountable: bool


@dataclass(frozen=True)
class NetCapitalGain:
    """Output of the s 102-5 loss-ordering algorithm (spec §5.2)."""

    nd_remainder: Decimal
    d_remainder_pre_discount: Decimal
    discount_applied: Decimal
    net_capital_gain: Decimal
    net_capital_loss_cf: Decimal


@dataclass(frozen=True)
class DividendOutcome:
    """After-tax cash + intermediate ledger lines."""

    cash_dividend: Decimal
    franking_credit: Decimal
    grossed_up: Decimal
    tax_assessed: Decimal
    franking_offset: Decimal
    net_tax: Decimal
    after_tax_cash: Decimal


@dataclass(frozen=True)
class Div296Outcome:
    """spec §6.3 — stacked tier1 + tier2."""

    tsb_ref: Decimal
    earnings: Decimal
    lsbt: Decimal
    vlsbt: Decimal
    tier_1: Decimal
    tier_2: Decimal
    total: Decimal
    is_provisional: bool = False


@dataclass(frozen=True)
class TaxView:
    """Aggregated tax position for `asx tax-view`."""

    account_type: AccountType
    holdings_count: int
    realised_gain_aud: Decimal
    net_capital_gain: NetCapitalGain | None = None
    dividends_after_tax: Decimal = Decimal("0")
    div296_outcome: Div296Outcome | None = None
    eligibility_alerts: list[str] = field(default_factory=list)
    franking_warnings: list[str] = field(default_factory=list)
