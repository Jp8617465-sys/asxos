"""
Tests for asxos.domain.signals.regime.classify_regime.

Synthetic panels with explicit trends in the top-N most-traded symbols
let us assert bull / bear / neutral output. No DB.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from asxos.domain.signals.regime import (
    PROXY_TOP_N,
    SLOPE_WINDOW,
    SMA_WINDOW,
    classify_regime,
)


def _trended_panel(
    n_days: int = 260,
    trend: float = 0.0,
    n_symbols: int = 12,
    noise: float = 0.3,
) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.date_range("2025-01-01", periods=n_days, freq="B")
    rows = []
    for i in range(n_symbols):
        # Liquid symbols have higher dollar volume → become the proxy basket
        is_top = i < PROXY_TOP_N
        vol = 5_000_000 if is_top else 100_000
        # Larger drift on top symbols so the synthetic index reflects `trend`
        drift = trend if is_top else 0.0
        close = 50.0 + np.cumsum(rng.normal(drift, noise, n_days))
        close = np.maximum(close, 1.0)
        for j, c in enumerate(close):
            rows.append({"symbol": f"S{i:02d}.AU", "dt": dates[j], "close": float(c), "volume": vol})
    return pd.DataFrame(rows)


def test_classify_regime_bull_when_proxy_rising() -> None:
    panel = _trended_panel(n_days=SMA_WINDOW + SLOPE_WINDOW + 30, trend=0.20)
    assert classify_regime(panel) == "bull"


def test_classify_regime_bear_when_proxy_falling() -> None:
    panel = _trended_panel(n_days=SMA_WINDOW + SLOPE_WINDOW + 30, trend=-0.20)
    assert classify_regime(panel) == "bear"


def test_classify_regime_neutral_when_panel_too_short() -> None:
    panel = _trended_panel(n_days=50, trend=0.20)
    assert classify_regime(panel) == "neutral"


def test_classify_regime_neutral_on_empty_panel() -> None:
    assert classify_regime(pd.DataFrame()) == "neutral"


def test_classify_regime_neutral_on_flat_proxy() -> None:
    # No noise, no trend → proxy is exactly constant, MA == close, slope == 0 → neutral
    panel = _trended_panel(
        n_days=SMA_WINDOW + SLOPE_WINDOW + 30, trend=0.0, noise=0.0
    )
    assert classify_regime(panel) == "neutral"
