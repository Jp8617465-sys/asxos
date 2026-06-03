"""
Signal-label thresholds. Locked at BUILD_GUIDE M7 / ml-conventions.md.

`classify` is the canonical map from (prob_up, expected_return) to one of
STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL.

`apply_regime_thresholds` tightens the buy bar in bear regimes and the sell
bar in bull regimes; falls back to `classify` for neutral.

`confidence_from_prob_up` is the ml-conventions integer formula:
    int(abs(prob_up - 0.5) * 200), clamped to [0, 100].

`classify_batch` is the vectorised numpy version for the daily job — never
use `.apply()` row-by-row in the pipeline (ml-conventions.md).
"""
from __future__ import annotations

from typing import Any

import numpy as np

LABELS = ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
REGIMES = ("bull", "bear", "neutral")


def classify(prob_up: float, expected_return: float) -> str:
    if prob_up >= 0.65 and expected_return > 0.05:
        return "STRONG_BUY"
    if prob_up >= 0.55 and expected_return > 0:
        return "BUY"
    if prob_up <= 0.35 and expected_return < -0.05:
        return "STRONG_SELL"
    if prob_up <= 0.45 and expected_return < 0:
        return "SELL"
    return "HOLD"


def apply_regime_thresholds(prob_up: float, expected_return: float, regime: str) -> str:
    """Regime-conditioned label. Stricter buys in bear, stricter sells in bull."""
    if regime == "bear":
        if prob_up >= 0.70 and expected_return > 0.06:
            return "STRONG_BUY"
        if prob_up >= 0.60 and expected_return > 0:
            return "BUY"
    elif regime == "bull":
        if prob_up <= 0.30 and expected_return < -0.06:
            return "STRONG_SELL"
        if prob_up <= 0.40 and expected_return < 0:
            return "SELL"
    return classify(prob_up, expected_return)


def confidence_from_prob_up(prob_up: np.ndarray[Any, Any] | float) -> np.ndarray[Any, Any]:
    """0..100 integer scale (ml-conventions.md).

    Uses np.round to dodge the float-precision case `(0.6-0.5)*200 == 19.999...`
    which would truncate to 19 under a naive `.astype(int)`.
    """
    arr = np.abs(np.asarray(prob_up, dtype=float) - 0.5) * 200.0
    return np.clip(np.round(arr), 0, 100).astype(int)  # type: ignore[no-any-return]


def classify_batch(
    prob_up: np.ndarray[Any, Any],
    expected_return: np.ndarray[Any, Any],
    regime: str = "neutral",
) -> np.ndarray[Any, Any]:
    """
    Vectorised classifier — row-equivalent to apply_regime_thresholds.

    Bear/bull "tighten" only the STRONG_* labels; the plain BUY/SELL masks
    use the neutral cutoff (this matches the early-return + fall-through
    structure of apply_regime_thresholds, where a row that doesn't clear
    the stricter inner branch lands in the neutral `classify`).
    """
    p = np.asarray(prob_up, dtype=float)
    r = np.asarray(expected_return, dtype=float)

    if regime == "bear":
        sb_mask = (p >= 0.70) & (r > 0.06)
    else:
        sb_mask = (p >= 0.65) & (r > 0.05)

    if regime == "bull":
        ss_mask = (p <= 0.30) & (r < -0.06)
    else:
        ss_mask = (p <= 0.35) & (r < -0.05)

    b_mask = (p >= 0.55) & (r > 0)
    s_mask = (p <= 0.45) & (r < 0)

    labels = np.full(p.shape, "HOLD", dtype=object)
    labels = np.where(s_mask, "SELL", labels)
    labels = np.where(b_mask, "BUY", labels)
    labels = np.where(ss_mask, "STRONG_SELL", labels)
    labels = np.where(sb_mask, "STRONG_BUY", labels)
    return labels
