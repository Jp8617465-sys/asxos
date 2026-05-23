"""
Core dataclasses for the portfolio construction layer (M13).

All monetary, weight, and statistical values are Decimal. Never float.
Validators raise ValueError on every bound check; no silent clamping
(CLAUDE.md non-negotiable #1 / #10).

Profile is the only type populated in M13.1; AllocationCandidate /
AllocationTarget / HoldingSnapshot / ProposedTrade / RebalanceResult are
added in M13.3+ and reserved here as forward declarations would be added
in their own sub-milestones — kept as separate files to keep the
diffs small.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

RiskTolerance = Literal["conservative", "balanced", "growth", "aggressive"]
AccountType = Literal["individual", "smsf"]

# Canonical risk label → scalar mapping. Used to validate consistency in
# Profile.__post_init__ and as the source for profile.risk_tolerance_scalar().
RISK_TOLERANCE_SCALARS: dict[RiskTolerance, Decimal] = {
    "conservative": Decimal("0.25"),
    "balanced": Decimal("0.50"),
    "growth": Decimal("0.75"),
    "aggressive": Decimal("1.00"),
}

# Default score weights. The DB stores per-profile under `score_weights_json`
# with a precision-tolerant CHECK constraint (sum ∈ [0.999, 1.001]). The
# load function in profile.py normalises to exact Decimal("1") on read.
DEFAULT_SCORE_WEIGHTS: dict[str, Decimal] = {
    "prob_up": Decimal("0.6"),
    "expected_return": Decimal("0.4"),
}


@dataclass(frozen=True)
class Profile:
    """One named investment profile. At most one row has is_active=TRUE
    (enforced by a partial unique index in migration 0005). Field bounds
    mirror the SQL CHECK constraints exactly so a violation surfaces in
    Python before it hits the DB.

    Mutability convention: profile rows are never updated in place. To
    change a setting, `asx profile init --name <new>` then activate.
    """

    profile_id: int | None  # None pre-insert
    name: str
    is_active: bool
    account_type: AccountType
    risk_tolerance: RiskTolerance
    risk_tolerance_scalar: Decimal  # [0, 1]; must match RISK_TOLERANCE_SCALARS[risk_tolerance]
    capital_aud: Decimal
    cash_floor_pct: Decimal  # [0, 1]
    leverage_cap: Decimal  # [1, 3]; 1.0 = no margin
    per_name_cap_pct: Decimal  # (0, 0.5]
    sector_cap_pct: Decimal  # (0, 1]
    excluded_sectors: tuple[str, ...]
    excluded_symbols: tuple[str, ...]
    min_position_aud: Decimal
    horizon_years: int
    defer_near_boundary_sells: bool  # spec §5.1 — defer sells within 30d of CGT eligibility
    score_weights_json: dict[str, Decimal]  # composite-score weighting (prob_up, expected_return)
    created_at: date
    updated_at: date

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")

        if self.account_type not in ("individual", "smsf"):
            raise ValueError(
                f"account_type must be 'individual' or 'smsf', got {self.account_type!r}"
            )

        if self.risk_tolerance not in RISK_TOLERANCE_SCALARS:
            raise ValueError(
                f"risk_tolerance must be one of {list(RISK_TOLERANCE_SCALARS)}, "
                f"got {self.risk_tolerance!r}"
            )

        # Scalar must equal the canonical mapping for the label. This catches
        # drift between the DB row and the Python representation.
        expected_scalar = RISK_TOLERANCE_SCALARS[self.risk_tolerance]
        if self.risk_tolerance_scalar != expected_scalar:
            raise ValueError(
                f"risk_tolerance_scalar {self.risk_tolerance_scalar} does not match "
                f"label {self.risk_tolerance!r} (expected {expected_scalar})"
            )

        if not (Decimal("0") <= self.risk_tolerance_scalar <= Decimal("1")):
            raise ValueError(
                f"risk_tolerance_scalar {self.risk_tolerance_scalar} outside [0, 1]"
            )

        if self.capital_aud < Decimal("0"):
            raise ValueError(f"capital_aud must be non-negative, got {self.capital_aud}")

        if not (Decimal("0") <= self.cash_floor_pct <= Decimal("1")):
            raise ValueError(f"cash_floor_pct {self.cash_floor_pct} outside [0, 1]")

        if not (Decimal("1") <= self.leverage_cap <= Decimal("3")):
            raise ValueError(f"leverage_cap {self.leverage_cap} outside [1, 3]")

        if not (Decimal("0") < self.per_name_cap_pct <= Decimal("0.5")):
            raise ValueError(
                f"per_name_cap_pct {self.per_name_cap_pct} outside (0, 0.5]"
            )

        if not (Decimal("0") < self.sector_cap_pct <= Decimal("1")):
            raise ValueError(f"sector_cap_pct {self.sector_cap_pct} outside (0, 1]")

        if self.min_position_aud < Decimal("0"):
            raise ValueError(
                f"min_position_aud must be non-negative, got {self.min_position_aud}"
            )

        if self.horizon_years < 0:
            raise ValueError(f"horizon_years must be non-negative, got {self.horizon_years}")

        # score_weights_json shape — keys present, both in [0, 1], sum ≈ 1
        # (tolerance band; load_active normalises to exact sum=1).
        required_keys = {"prob_up", "expected_return"}
        if set(self.score_weights_json.keys()) != required_keys:
            raise ValueError(
                f"score_weights_json keys must be {required_keys}, "
                f"got {set(self.score_weights_json.keys())}"
            )
        for k in required_keys:
            v = self.score_weights_json[k]
            if not isinstance(v, Decimal):
                raise TypeError(
                    f"score_weights_json[{k!r}] must be Decimal, got {type(v).__name__}"
                )
            if not (Decimal("0") <= v <= Decimal("1")):
                raise ValueError(f"score_weights_json[{k!r}] {v} outside [0, 1]")
        wsum = self.score_weights_json["prob_up"] + self.score_weights_json["expected_return"]
        if not (Decimal("0.999") <= wsum <= Decimal("1.001")):
            raise ValueError(
                f"score_weights_json sum {wsum} outside tolerance band [0.999, 1.001]"
            )

        # Exclusions: tuples of trimmed non-empty strings.
        for kind, items in (("excluded_sectors", self.excluded_sectors),
                            ("excluded_symbols", self.excluded_symbols)):
            if not isinstance(items, tuple):
                raise TypeError(f"{kind} must be a tuple, got {type(items).__name__}")
            for s in items:
                if not isinstance(s, str) or not s.strip():
                    raise ValueError(f"{kind} must contain non-empty strings; got {s!r}")


# ---------------------------------------------------------------------------
# M13.3 — Allocator types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AllocationCandidate:
    """Signal row joined to universe + computed vol — input to the allocator.

    Constructed by the orchestrator (M13.6 build.py) from signals × universe × vol.
    daily_vol is annualised (misleading name retained from the plan).
    """

    symbol: str
    sector: str | None
    market_cap_aud: Decimal | None
    signal_label: str  # STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL
    prob_up: Decimal
    expected_return: Decimal
    daily_vol: Decimal  # annualised volatility from volatility.annualised_vol_from_prices
    confidence: int  # 0..3 ladder


@dataclass(frozen=True)
class AllocationTarget:
    """Per-symbol target after inverse-vol weighting.

    target_weight is a fraction of total capital. Weights sum to
    (leverage_cap - cash_floor_pct) across the portfolio, e.g. 0.95
    with leverage_cap=1.0 and cash_floor_pct=0.05.

    constraint_log is populated by M13.4; the allocator always initialises
    it to {}. M13.4 creates new instances via dataclasses.replace().
    """

    symbol: str
    sector: str | None
    target_weight: Decimal  # [0, leverage_cap]; sums to leverage_cap - cash_floor_pct
    inv_vol_score: Decimal  # raw 1/sigma — explainability + waterfall redistribution
    signal_label: str
    prob_up: Decimal
    expected_return: Decimal
    constraint_log: dict  # populated by M13.4 constraints.apply_constraints()


# ---------------------------------------------------------------------------
# M13.5 — Tax overlay types
# ---------------------------------------------------------------------------

TradeSide = Literal["buy", "sell", "hold"]


@dataclass(frozen=True)
class HoldingSnapshot:
    """Lot-level position snapshot used by the tax overlay and rebalance engine.

    ``days_to_cgt_discount`` is computed at snapshot time using calendar
    arithmetic per spec §5.1:
        disposal_date >= acquired_at + relativedelta(years=1) + timedelta(days=1)
    A value of 0 means the lot is already CGT-discount-eligible (≥12 months held).
    account_type is derived from the active profile at snapshot time (plan H.1 CRITICAL-1
    resolution: no account_type column on holding_lots; profile is single-user).
    """

    lot_id: int
    symbol: str
    acquired_at: date
    quantity: Decimal
    cost_base_normal: Decimal  # AUD total for the lot
    cost_base_div296: Decimal
    account_type: AccountType
    current_price_aud: Decimal
    days_to_cgt_discount: int  # 0 if already eligible (calendar arithmetic per §5.1)


@dataclass(frozen=True)
class ProposedTrade:
    """A single proposed rebalance action.

    ``side`` is "buy", "sell", or "hold" (drift below threshold).
    ``delta_qty`` and ``delta_aud`` are signed: positive for buys, negative for sells.
    ``lot_hints`` is populated by the tax overlay on sells; empty dict otherwise.
    ``rationale_tags`` accumulates annotations from the constraint waterfall (M13.4)
    and the tax overlay (M13.5 loss-harvest, M13.6 boundary-defer).
    """

    symbol: str
    side: TradeSide
    delta_qty: Decimal  # signed: + buy, - sell
    delta_aud: Decimal  # signed
    target_qty: Decimal
    current_qty: Decimal
    reference_price: Decimal
    rationale_tags: dict
    lot_hints: dict  # populated on sells only
