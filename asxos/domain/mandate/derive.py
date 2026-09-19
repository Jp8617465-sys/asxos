"""`derive(goals) -> Mandate` — pure, Decimal-only, every figure traced.

Version `v1`. The constants below are this version's declared rules; James
ratifies them by ratifying the memo, and a change to any of them is a new
`DERIVATION_VERSION`, never an edit in place (the same discipline
`regime/classifier.py` applies to its thresholds).

The one rule that decides the shape of the portfolio: single-name sleeves are
feasible only when the deployable capital can hold at least as many names as
the ratified per-name cap requires (`ceil(deployable_pct / cap)`, ten at a
10 % cap and a 7.5 % floor) at the minimum position size. Below that the
mandate is ETF-only. That is the honest answer for the live book today —
A$7,749 at A$1,000 minimums holds seven names, and seven names cannot honour
a 10 % cap — and it is what `.claude/rules/portfolio-conventions.md` D-6
(caps mutually unsatisfiable) turns into a statement instead of a crash.
"""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from dateutil.relativedelta import relativedelta

from asxos.domain.mandate.types import (
    Goals,
    Mandate,
    MandateOutputs,
    SleeveAllocation,
    Structure,
    Traced,
)

DERIVATION_VERSION: Final[str] = "v1"

# --- Register constants, each with the line it comes from ---------------------
CASH_FLOOR_BASE_PCT: Final[Decimal] = Decimal("7.5")  # ADR D1
CASH_FLOOR_ELEVATED_PCT: Final[Decimal] = Decimal("10")  # ADR D1 §1.1 — top of the 5–10 % range
DRAWDOWN_TOLERANCE_ELEVATES_AT_PCT: Final[Decimal] = Decimal("20")  # D1 §1.1 (a): "if genuinely low, move toward 10 %"
RESERVE_SHARE_ELEVATES_AT: Final[Decimal] = Decimal("0.10")  # D1 §1.1 (b): material calls within ~3 years
LIQUIDITY_HORIZON_YEARS: Final[int] = 3  # D1 §1.1 (b)
MIN_POSITION_FLOOR_AUD: Final[Decimal] = Decimal("1000")  # profiles.min_position_aud; P5-01 C1
ROUND_TRIP_COST_CAP: Final[Decimal] = Decimal("0.01")  # a round trip may cost at most 1 % of the position
POSITION_CAP_PCT: Final[Decimal] = Decimal("10")  # P5-01 C4 — keep the profile's 10 %
MAX_SINGLE_NAMES: Final[int] = 20  # portfolio-conventions I.2, balanced ≈ 20
STOP_BAND_PCT: Final[Decimal] = Decimal("25")  # P5-01 C3
MODELLED_STOP_DISTANCE_PCT: Final[Decimal] = Decimal("20")  # P5-01 C2: 10 % cap × 20 % stop = 2 % at risk
ETF_CORE_FLOOR_WHEN_CONTRIBUTING_PCT: Final[Decimal] = Decimal("30")
CONTRIBUTION_SHARE_TRIGGER: Final[Decimal] = Decimal("0.25")  # savings_pa > 25 % of deployable
TURNOVER_BUDGET_PCT_PA: Final[Decimal] = Decimal("100")  # one full turn a year, monthly hold-band rebalance

ETF_SLEEVE_ID: Final[str] = "slv-etf-core-v1"
SINGLE_NAME_SLEEVE_IDS: Final[tuple[str, ...]] = (
    "slv-mom-12-1-v1",
    "slv-quality-v1",
    "slv-vq-control-v1",
    "slv-low-vol-v1",
)

_Q6: Final[Decimal] = Decimal("0.000001")
_HUNDRED: Final[Decimal] = Decimal("100")


def _q(x: Decimal) -> Decimal:
    return x.quantize(_Q6, rounding=ROUND_HALF_EVEN)


def _t(value: Decimal, traced_to: str) -> Traced:
    return Traced(value=_q(value), traced_to=traced_to)


def _liquidity_reserve(goals: Goals) -> tuple[Decimal, str]:
    horizon_end = goals.as_of + relativedelta(years=LIQUIDITY_HORIZON_YEARS)
    calls = sum((n.amount_aud for n in goals.liquidity_needs if n.due <= horizon_end), Decimal("0"))
    monthly_spend = max(Decimal("0"), goals.income_aud_pa - goals.savings_aud_pa) / Decimal("12")
    emergency = monthly_spend * Decimal(goals.emergency_months)
    trace = (
        f"ADR D1 §1.1(b): liquidity calls due within {LIQUIDITY_HORIZON_YEARS}y ({calls}) "
        f"+ emergency {goals.emergency_months} months × (income − savings)/12 ({_q(emergency)})"
    )
    return calls + emergency, trace


def _cash_floor(goals: Goals, reserve: Decimal, deployable: Decimal) -> tuple[Decimal, str]:
    low_tolerance = goals.drawdown_tolerance_pct < DRAWDOWN_TOLERANCE_ELEVATES_AT_PCT
    material_calls = deployable > 0 and (reserve / deployable) > RESERVE_SHARE_ELEVATES_AT
    if low_tolerance or material_calls:
        why = "drawdown tolerance below 20 %" if low_tolerance else "liquidity calls exceed 10 % of deployable"
        return CASH_FLOOR_ELEVATED_PCT, f"ADR D1 §1.1: {why} → top of the 5–10 % range"
    return CASH_FLOOR_BASE_PCT, "ADR D1: 7.5 % ratified working value"


def _ceil_div(a: Decimal, b: Decimal) -> int:
    q = a / b
    n = int(q)
    return n if Decimal(n) == q else n + 1


def derive(goals: Goals) -> Mandate:
    """The v1 mandate for one Goals row. Pure; the same input always yields the same hash."""
    reserve, reserve_trace = _liquidity_reserve(goals)
    deployable = max(Decimal("0"), goals.investable_assets_aud - reserve)
    cash_floor, cash_trace = _cash_floor(goals, reserve, deployable)
    deployable_pct = _HUNDRED - cash_floor

    min_position = max(MIN_POSITION_FLOOR_AUD, (Decimal("2") * goals.brokerage_aud_per_side) / ROUND_TRIP_COST_CAP)
    investable_in_names = deployable * deployable_pct / _HUNDRED
    n_by_min = int(investable_in_names / min_position) if min_position > 0 else 0
    n_required_by_cap = _ceil_div(deployable_pct, POSITION_CAP_PCT)
    n = min(MAX_SINGLE_NAMES, n_by_min) if n_by_min >= n_required_by_cap else 0
    n_trace = (
        f"floor(deployable × {deployable_pct} % ÷ min position) = {n_by_min}; "
        f"a {POSITION_CAP_PCT} % cap needs ≥ {n_required_by_cap} names, ceiling {MAX_SINGLE_NAMES} "
        f"(portfolio-conventions I.2) → {n}"
        + ("" if n else " → single names infeasible at this capital; ETF-only")
    )

    if n:
        equal_weight = deployable_pct / Decimal(n)
        contributing = goals.savings_aud_pa > CONTRIBUTION_SHARE_TRIGGER * deployable if deployable > 0 else False
        floor_contrib = ETF_CORE_FLOOR_WHEN_CONTRIBUTING_PCT if contributing else Decimal("0")
        floor_scale = _HUNDRED * (Decimal("1") - Decimal(n) / Decimal(MAX_SINGLE_NAMES))
        etf_core = max(floor_contrib, floor_scale)
        etf_trace = (
            f"max({floor_contrib} if savings > 25 % of deployable else 0, 100 × (1 − {n}/{MAX_SINGLE_NAMES}) = {_q(floor_scale)}) "
            "— contributions dominate selection when capital is small; percent of deployable"
        )
        structure: Structure = "etf_core_plus_sleeves"
        per_sleeve = _q((_HUNDRED - _q(etf_core)) / Decimal(len(SINGLE_NAME_SLEEVE_IDS)))
        sleeves = [SleeveAllocation(sleeve_id=s, weight_pct=per_sleeve) for s in SINGLE_NAME_SLEEVE_IDS]
        # Quantisation residue goes to the ETF core so the split sums to exactly 100.
        etf_core = _HUNDRED - per_sleeve * Decimal(len(sleeves))
    else:
        equal_weight = Decimal("0")
        etf_core = _HUNDRED
        etf_trace = "single names infeasible at this capital (see n_single_feasible) → 100 % of deployable in the ETF core"
        structure = "etf_only"
        sleeves = []

    outputs = MandateOutputs(
        liquidity_reserve_aud=_t(reserve, reserve_trace),
        deployable_capital_aud=_t(deployable, "investable assets − liquidity reserve"),
        cash_floor_pct=_t(cash_floor, cash_trace),
        min_position_aud=_t(min_position, f"max({MIN_POSITION_FLOOR_AUD}, 2 × brokerage ÷ {ROUND_TRIP_COST_CAP}) — round trip ≤ 1 % of the position"),
        n_single_feasible=_t(Decimal(n), n_trace),
        position_cap_pct=_t(POSITION_CAP_PCT, "P5-01 C4 — the profile's 10 % per-name cap, kept"),
        equal_weight_pct=_t(equal_weight, f"{deployable_pct} % deployable ÷ {n} names" if n else "no single names"),
        stop_band_pct=_t(STOP_BAND_PCT, "P5-01 C3 — a stop further than 25 % from entry is a material challenge finding"),
        risk_per_position_pct=_t(POSITION_CAP_PCT * MODELLED_STOP_DISTANCE_PCT / _HUNDRED, "P5-01 C2 — 10 % cap × 20 % modelled stop distance = 2 % of capital at risk"),
        portfolio_dd_review_pct=_t(goals.drawdown_tolerance_pct, "P5-01 C5 — your stated drawdown tolerance; a mandatory review, never a forced sale (reporting-only until Stage 5)"),
        etf_core_pct=_t(etf_core, etf_trace),
        sleeve_allocations=tuple(sleeves),
        structure=structure,
        turnover_budget_pct_pa=_t(TURNOVER_BUDGET_PCT_PA, "monthly rebalance with a 2N hold-band; one full turn a year"),
    )
    return Mandate(
        as_of=goals.as_of,
        derivation_version=DERIVATION_VERSION,
        goals_content_hash=goals.content_hash,
        outputs=outputs,
    )


__all__ = ["DERIVATION_VERSION", "ETF_SLEEVE_ID", "SINGLE_NAME_SLEEVE_IDS", "derive"]
