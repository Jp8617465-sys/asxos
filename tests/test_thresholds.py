"""
Boundary tests for asxos.domain.signals.thresholds.

Each milestone after M7 derives signal-label semantics from here, so the
boundaries are pinned tightly. Asserts:
- classify boundaries at 0.65/0.55/0.45/0.35 and 0.05/-0.05.
- apply_regime_thresholds shifts cutoffs in bull/bear only as documented.
- classify_batch is row-equivalent to apply_regime_thresholds.
- confidence_from_prob_up matches the ml-conventions integer formula.
"""
from __future__ import annotations

import numpy as np
import pytest

from asxos.domain.signals.thresholds import (
    apply_regime_thresholds,
    classify,
    classify_batch,
    confidence_from_prob_up,
)


@pytest.mark.parametrize(
    "prob, exp, label",
    [
        (0.65, 0.05001, "STRONG_BUY"),
        (0.6499, 0.06, "BUY"),
        (0.55, 0.0001, "BUY"),
        (0.5499, 0.01, "HOLD"),
        (0.5, 0.0, "HOLD"),
        (0.45, -0.0001, "SELL"),
        (0.4501, -0.01, "HOLD"),
        (0.35, -0.05001, "STRONG_SELL"),
        (0.3501, -0.06, "SELL"),
        (0.65, 0.05, "BUY"),  # strict > on expected_return rules out STRONG_BUY at exactly 0.05
    ],
)
def test_classify_boundary(prob: float, exp: float, label: str) -> None:
    assert classify(prob, exp) == label


def test_apply_regime_thresholds_neutral_matches_classify() -> None:
    for p in (0.20, 0.40, 0.50, 0.60, 0.80):
        for r in (-0.10, -0.04, 0.0, 0.04, 0.10):
            assert apply_regime_thresholds(p, r, "neutral") == classify(p, r)


def test_apply_regime_thresholds_bear_tightens_buys() -> None:
    # neutral STRONG_BUY (0.66, 0.06) downgrades in bear because cutoff is 0.70/0.06
    assert classify(0.66, 0.06) == "STRONG_BUY"
    assert apply_regime_thresholds(0.66, 0.06, "bear") != "STRONG_BUY"
    # crossed cutoffs satisfy bear
    assert apply_regime_thresholds(0.71, 0.07, "bear") == "STRONG_BUY"
    assert apply_regime_thresholds(0.60, 0.01, "bear") == "BUY"


def test_apply_regime_thresholds_bull_tightens_sells() -> None:
    assert classify(0.34, -0.06) == "STRONG_SELL"
    assert apply_regime_thresholds(0.34, -0.06, "bull") != "STRONG_SELL"
    assert apply_regime_thresholds(0.29, -0.07, "bull") == "STRONG_SELL"
    assert apply_regime_thresholds(0.40, -0.01, "bull") == "SELL"


def test_classify_batch_matches_per_row_neutral() -> None:
    p = np.array([0.66, 0.56, 0.50, 0.44, 0.34])
    r = np.array([0.06, 0.01, 0.00, -0.01, -0.06])
    batch = classify_batch(p, r, regime="neutral")
    per_row = [apply_regime_thresholds(float(pi), float(ri), "neutral") for pi, ri in zip(p, r, strict=False)]
    assert list(batch) == per_row


def test_classify_batch_matches_per_row_bear() -> None:
    p = np.array([0.71, 0.66, 0.60, 0.50, 0.30])
    r = np.array([0.07, 0.06, 0.01, 0.00, -0.07])
    batch = classify_batch(p, r, regime="bear")
    per_row = [apply_regime_thresholds(float(pi), float(ri), "bear") for pi, ri in zip(p, r, strict=False)]
    assert list(batch) == per_row


def test_classify_batch_matches_per_row_bull() -> None:
    p = np.array([0.65, 0.45, 0.40, 0.30, 0.25])
    r = np.array([0.06, -0.01, -0.01, -0.06, -0.08])
    batch = classify_batch(p, r, regime="bull")
    per_row = [apply_regime_thresholds(float(pi), float(ri), "bull") for pi, ri in zip(p, r, strict=False)]
    assert list(batch) == per_row


def test_confidence_formula() -> None:
    arr = confidence_from_prob_up(np.array([0.5, 0.6, 0.4, 0.8, 0.2, 1.0, 0.0]))
    # 0 / 20 / 20 / 60 / 60 / 100 / 100
    assert list(arr) == [0, 20, 20, 60, 60, 100, 100]


def test_confidence_clamped() -> None:
    # Even if prob_up is nonsensical (e.g. 1.5 from a buggy model), confidence
    # must be clamped to [0, 100].
    arr = confidence_from_prob_up(np.array([1.5, -0.5]))
    assert (arr <= 100).all() and (arr >= 0).all()
