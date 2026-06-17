"""
model_a v1_6 — behavioural price-basis contract for build_target.

CI-ONLY: build_target operates on a pandas DataFrame, so this module imports
pandas/numpy at the top. In environments without them (the lint-only sandbox)
it is a collection gap, consistent with the other ML test modules
(test_feature_engine, test_signals_loader, test_train_walk_forward); it runs on
the ML-enabled CI image (the targeted-ml-tests workflow).

  * Passing CHARACTERIZATION: current build_target yields a fractional
    forward_return computed from raw close.
  * Strict-xfail DESIRED v1_6: build_target should compute forward_return from
    adj_close so corporate-action jumps in raw close do not contaminate it.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from asxos.domain.models.train import build_target


def _panel(closes: list[float], adj_closes: list[float] | None = None) -> pd.DataFrame:
    """Single-symbol panel; adj_close optional (ignored by current build_target)."""
    rows = []
    for i, close in enumerate(closes):
        row = {"symbol": "TEST.AU", "dt": date(2026, 1, 1) + timedelta(days=i), "close": close}
        if adj_closes is not None:
            row["adj_close"] = adj_closes[i]
        rows.append(row)
    return pd.DataFrame(rows)


def test_v1_5_build_target_forward_return_is_fractional() -> None:
    """CHARACTERIZATION: a +1% move over 5 days yields forward_return ~= 0.01
    (a fraction), not 100 (bps). The bps scaling is applied later, inside
    train_model_a (y_reg = forward_return * 10_000)."""
    # close[5]/close[0] = 101/100 -> +1% ; close[6]/close[1] = 102/100 -> +2%
    panel = _panel([100, 100, 100, 100, 100, 101, 102])
    out = build_target(panel).sort_values("dt").reset_index(drop=True)
    assert out.loc[0, "forward_return"] == pytest.approx(0.01, abs=1e-9)
    assert out.loc[1, "forward_return"] == pytest.approx(0.02, abs=1e-9)
    assert out.loc[0, "y_class"] == 1


@pytest.mark.xfail(
    strict=True,
    reason="model_a_v1_6 build_target will compute forward_return from adj_close, "
    "so a corporate-action jump in raw close no longer contaminates the target.",
)
def test_v1_6_build_target_uses_adj_close() -> None:
    """A 10x raw-close jump at t=5 (consolidation-like) with a smooth adj_close.
    Desired v1_6: forward_return follows adj_close (~0), not raw close (~+9.0)."""
    closes = [10, 10, 10, 10, 10, 100, 100]        # spurious 10x jump
    adj = [100, 100, 100, 100, 100, 100, 100]      # smooth adjusted series
    out = build_target(_panel(closes, adj)).sort_values("dt").reset_index(drop=True)
    # Under the v1_6 contract this is ~0; current code uses raw close -> 9.0.
    assert out.loc[0, "forward_return"] == pytest.approx(0.0, abs=1e-6)
