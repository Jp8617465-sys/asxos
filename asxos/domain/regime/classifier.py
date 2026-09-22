"""
Rules-based regime classifier — M-Market-Context.

Pure function: classify(indicators) → (RegimeLabel, list[Condition])

Waterfall (top-down, first match wins):
  1. risk_off_disorderly  — extreme vol or extreme credit stress
  2. risk_off_orderly     — elevated vol or elevated spreads or thin breadth
  3. risk_on_broadening   — calm vol + wide breadth + net new highs positive
  4. risk_on_narrowing    — calm vol + moderate breadth + net new highs negative
  5. neutral_mixed        — everything else (default)

Hard-fail inputs (must not be None): avix, us_hy_oas
Soft-degrade inputs (may be None, skips condition):
  pct_above_50d_ma, pct_above_200d_ma, net_new_highs_lows_10d

Units. ``us_hy_oas`` is FRED ``BAMLH0A0HYM2`` (ICE BofA US High Yield OAS),
which FRED publishes in **percent** (2.70 means 270 bp), and
``jobs/ingest_market_context.py`` stores it unscaled. The credit thresholds
below are therefore in percent too. v1.0 carried them in basis points
(450 / 600) against a percent input, so ``hy_oas_elevated`` and
``hy_oas_stress`` could never fire — spreads would have needed to reach
45,000 bp — and the regime label was breadth-and-AVIX-only in production
for the whole of v1.0. Found 2026-09-18 (capability atlas D-1); the unit
tests had encoded the bp scale, so CI stayed green throughout.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.regime.types import Condition, RegimeLabel

# ---------------------------------------------------------------------------
# Threshold constants — bump CLASSIFIER_VERSION if any value changes
# ---------------------------------------------------------------------------
CLASSIFIER_VERSION = "v1.1"  # v1.1: HY OAS thresholds re-stated in percent (were bp vs a percent input)

_AVIX_DISORDERLY = Decimal("30")
_AVIX_RISK_OFF = Decimal("22")
_AVIX_CALM = Decimal("18")
_AVIX_VERY_CALM = Decimal("14")

# Percent, matching the stored FRED series (see module docstring). 6.00 % and
# 4.50 % are the v1.0 intent (600 bp / 450 bp) expressed in the input's unit.
_HY_OAS_UNIT = "percent"
_HY_OAS_STRESS = Decimal("6.00")
_HY_OAS_ELEVATED = Decimal("4.50")

_BREADTH_200_BULLISH = Decimal("0.70")
_BREADTH_200_MODERATE = Decimal("0.55")
_BREADTH_200_BEARISH = Decimal("0.40")


def classify(
    indicators: dict[str, Decimal | None],
) -> tuple[RegimeLabel, list[Condition]]:
    """Classify regime from a dict of indicator values.

    Required keys: 'avix', 'us_hy_oas' (hard-fail if missing/None).
    Optional keys: 'pct_above_50d_ma', 'pct_above_200d_ma', 'net_new_highs_lows_10d'.

    Returns (label, conditions) where conditions is the full list of predicates
    evaluated, with fired=True for those that contributed to the chosen label.
    """
    avix = indicators.get("avix")
    hy_oas = indicators.get("us_hy_oas")
    breadth_200 = indicators.get("pct_above_200d_ma")
    net_highs_lows = indicators.get("net_new_highs_lows_10d")

    if avix is None:
        raise RuntimeError("classify: 'avix' is required and must not be None")
    if hy_oas is None:
        raise RuntimeError("classify: 'us_hy_oas' is required and must not be None")

    conds: list[Condition] = []

    def _cond(name: str, fired: bool, value: Decimal | None, threshold: Decimal | None) -> bool:
        conds.append(Condition(name=name, fired=fired, value=value, threshold=threshold))
        return fired

    # --- Rule 1: risk_off_disorderly ---
    r1_avix = _cond("avix_extreme", avix > _AVIX_DISORDERLY, avix, _AVIX_DISORDERLY)
    r1_hy = _cond("hy_oas_stress", hy_oas > _HY_OAS_STRESS, hy_oas, _HY_OAS_STRESS)
    if r1_avix or r1_hy:
        return RegimeLabel.risk_off_disorderly, conds

    # --- Rule 2: risk_off_orderly ---
    r2_avix = _cond("avix_elevated", avix > _AVIX_RISK_OFF, avix, _AVIX_RISK_OFF)
    r2_hy = _cond("hy_oas_elevated", hy_oas > _HY_OAS_ELEVATED, hy_oas, _HY_OAS_ELEVATED)
    r2_breadth = (
        _cond("breadth_200_thin", breadth_200 < _BREADTH_200_BEARISH, breadth_200, _BREADTH_200_BEARISH)
        if breadth_200 is not None
        else False
    )
    if r2_avix or r2_hy or r2_breadth:
        return RegimeLabel.risk_off_orderly, conds

    # --- Rule 3: risk_on_broadening (must evaluate before narrowing) ---
    r3_avix = _cond("avix_very_calm", avix < _AVIX_VERY_CALM, avix, _AVIX_VERY_CALM)
    r3_breadth = (
        _cond("breadth_200_bullish", breadth_200 >= _BREADTH_200_BULLISH, breadth_200, _BREADTH_200_BULLISH)
        if breadth_200 is not None
        else False
    )
    r3_highs = (
        _cond("net_highs_positive", net_highs_lows > Decimal("0"), net_highs_lows, Decimal("0"))
        if net_highs_lows is not None
        else False
    )
    if r3_avix and r3_breadth and r3_highs:
        return RegimeLabel.risk_on_broadening, conds

    # --- Rule 4: risk_on_narrowing ---
    r4_avix = _cond("avix_calm", avix < _AVIX_CALM, avix, _AVIX_CALM)
    r4_breadth = (
        _cond("breadth_200_moderate", breadth_200 >= _BREADTH_200_MODERATE, breadth_200, _BREADTH_200_MODERATE)
        if breadth_200 is not None
        else False
    )
    r4_highs = (
        _cond("net_highs_not_positive", net_highs_lows <= Decimal("0"), net_highs_lows, Decimal("0"))
        if net_highs_lows is not None
        else False
    )
    if r4_avix and r4_breadth and r4_highs:
        return RegimeLabel.risk_on_narrowing, conds

    # --- Rule 5: neutral_mixed (default) ---
    return RegimeLabel.neutral_mixed, conds
