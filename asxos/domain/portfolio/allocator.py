"""
Inverse-volatility risk-parity allocator (M13.3).

All math is Decimal-only; no numpy (plan Part C). The allocator produces
*raw* AllocationTarget weights summing to:

    target_sum = profile.leverage_cap - profile.cash_floor_pct

e.g. 0.95 with leverage_cap=1.0, cash_floor_pct=0.05. Constraint
trimming (per-name / sector / cash floor) happens in M13.4.

Position-count → risk-scalar mapping (plan amendment I.2: this is a UX
heuristic, not a finance-research-grade model; revisit with realised
data in M14+):

    conservative (0.25) → 30 names
    balanced     (0.50) → 20 names
    growth       (0.75) → 15 names
    aggressive   (1.00) → 10 names
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.portfolio.types import (
    DEFAULT_SCORE_WEIGHTS,
    AllocationCandidate,
    AllocationTarget,
    Profile,
)

_BUY_LABELS: frozenset[str] = frozenset({"STRONG_BUY", "BUY"})
_MIN_MARKET_CAP_AUD: Decimal = Decimal("50000000")

# (risk_scalar, position_count) anchors. Linear interpolation between segments.
_POSITION_COUNT_ANCHORS: list[tuple[Decimal, int]] = [
    (Decimal("0.25"), 30),
    (Decimal("0.50"), 20),
    (Decimal("0.75"), 15),
    (Decimal("1.00"), 10),
]


def position_count_for(risk_scalar: Decimal) -> int:
    """Map a risk_tolerance_scalar ∈ [0.25, 1.00] to a target position count.

    Exact anchors: conservative(0.25)→30, balanced(0.50)→20, growth(0.75)→15,
    aggressive(1.00)→10. Values between anchors are linearly interpolated and
    rounded to the nearest integer. Out-of-range values are clamped.
    """
    anchors = _POSITION_COUNT_ANCHORS
    if risk_scalar <= anchors[0][0]:
        return anchors[0][1]
    if risk_scalar >= anchors[-1][0]:
        return anchors[-1][1]
    for i in range(len(anchors) - 1):
        x0, y0 = anchors[i]
        x1, y1 = anchors[i + 1]
        if x0 <= risk_scalar <= x1:
            t = float((risk_scalar - x0) / (x1 - x0))
            return max(1, round(y0 + t * (y1 - y0)))
    return anchors[-1][1]  # unreachable


def filter_buy_universe(
    candidates: list[AllocationCandidate],
    excluded_sectors: tuple[str, ...],
    excluded_symbols: tuple[str, ...],
    min_market_cap_aud: Decimal = _MIN_MARKET_CAP_AUD,
) -> list[AllocationCandidate]:
    """Retain only investable buy candidates.

    Keeps a candidate if ALL of:
    - signal_label in {STRONG_BUY, BUY}
    - symbol not in excluded_symbols
    - sector not in excluded_sectors (None sector is not excluded by sector filter)
    - market_cap_aud is not None and >= min_market_cap_aud
    - daily_vol > 0 (required for inverse-vol weighting)
    """
    ex_sectors = frozenset(excluded_sectors)
    ex_symbols = frozenset(excluded_symbols)
    out: list[AllocationCandidate] = []
    for c in candidates:
        if c.signal_label not in _BUY_LABELS:
            continue
        if c.symbol in ex_symbols:
            continue
        if c.sector is not None and c.sector in ex_sectors:
            continue
        if c.market_cap_aud is None or c.market_cap_aud < min_market_cap_aud:
            continue
        if c.daily_vol <= Decimal("0"):
            continue
        out.append(c)
    return out


def _decimal_std(values: list[Decimal]) -> Decimal:
    """Population std-dev. Returns Decimal('0') for n <= 1 (no variance)."""
    n = len(values)
    if n <= 1:
        return Decimal("0")
    mean = sum(values, Decimal("0")) / Decimal(n)
    variance = sum((v - mean) ** 2 for v in values) / Decimal(n)
    return variance.sqrt()


def rank_candidates(
    buys: list[AllocationCandidate],
    score_weights: dict[str, Decimal] | None = None,
) -> list[AllocationCandidate]:
    """Sort buy candidates by composite z-score (highest first).

    composite = w_prob_up * z(prob_up) + w_expected_return * z(expected_return)

    Weights default to DEFAULT_SCORE_WEIGHTS (0.6 / 0.4 per plan). Pass
    profile.score_weights_json for per-profile tuning (plan amendment I.3).

    Tiebreaks: confidence descending, then symbol ascending.
    """
    if not buys:
        return []

    weights = score_weights if score_weights is not None else DEFAULT_SCORE_WEIGHTS

    prob_ups = [c.prob_up for c in buys]
    exp_rets = [c.expected_return for c in buys]

    mean_p = sum(prob_ups, Decimal("0")) / Decimal(len(buys))
    mean_e = sum(exp_rets, Decimal("0")) / Decimal(len(buys))
    std_p = _decimal_std(prob_ups)
    std_e = _decimal_std(exp_rets)

    w_p = weights["prob_up"]
    w_e = weights["expected_return"]

    def composite(c: AllocationCandidate) -> Decimal:
        z_p = (c.prob_up - mean_p) / std_p if std_p else Decimal("0")
        z_e = (c.expected_return - mean_e) / std_e if std_e else Decimal("0")
        return w_p * z_p + w_e * z_e

    # Pre-compute scores once per candidate; sort key uses negation for
    # descending composite and confidence, ascending for symbol.
    scored: list[tuple[Decimal, AllocationCandidate]] = [
        (composite(c), c) for c in buys
    ]
    return [
        c
        for _, c in sorted(
            scored,
            key=lambda item: (-item[0], -item[1].confidence, item[1].symbol),
        )
    ]


def inverse_vol_weights(candidates: list[AllocationCandidate]) -> list[Decimal]:
    """Compute inverse-vol weights: w_i = (1/sigma_i) / sum_j(1/sigma_j).

    Returns weights summing to Decimal('1'), aligned to input order.
    Raises ValueError if any candidate has daily_vol <= 0.
    """
    if not candidates:
        return []
    for c in candidates:
        if c.daily_vol <= Decimal("0"):
            raise ValueError(
                f"{c.symbol} has daily_vol={c.daily_vol}; "
                "inverse-vol weighting requires vol > 0"
            )
    inv_vols = [Decimal("1") / c.daily_vol for c in candidates]
    total = sum(inv_vols, Decimal("0"))
    return [iv / total for iv in inv_vols]


def allocate(
    *,
    candidates: list[AllocationCandidate],
    profile: Profile,
) -> list[AllocationTarget]:
    """End-to-end: filter → rank → top-N(risk_scalar) → inverse-vol weight.

    Returns AllocationTarget[] with weights summing to:
        target_sum = profile.leverage_cap - profile.cash_floor_pct

    Hard-fails with RuntimeError if the buy universe is empty after filtering.
    """
    buy_universe = filter_buy_universe(
        candidates,
        profile.excluded_sectors,
        profile.excluded_symbols,
    )
    if not buy_universe:
        raise RuntimeError(
            "no investable universe after filtering; "
            "check signal coverage, exclusions, and market-cap floor"
        )

    ranked = rank_candidates(buy_universe, profile.score_weights_json)
    n = position_count_for(profile.risk_tolerance_scalar)
    top_n = ranked[:n]

    raw_weights = inverse_vol_weights(top_n)
    # target_sum: fraction of capital to deploy (leverage_cap=1.0 → 100% of capital,
    # minus cash floor). With default leverage_cap=1.0 and cash_floor=0.05: 0.95.
    target_sum = profile.leverage_cap - profile.cash_floor_pct

    return [
        AllocationTarget(
            symbol=c.symbol,
            sector=c.sector,
            target_weight=w * target_sum,
            inv_vol_score=Decimal("1") / c.daily_vol,
            signal_label=c.signal_label,
            prob_up=c.prob_up,
            expected_return=c.expected_return,
            constraint_log={},
        )
        for c, w in zip(top_n, raw_weights, strict=False)
    ]
