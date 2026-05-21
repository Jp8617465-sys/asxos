"""
Market-regime detection.

Computes a synthetic ASX200 proxy from the top-N most-liquid symbols in
the universe (by 20-day median dollar volume), then asks whether the
proxy's last close is above or below its 200-day moving average and
which side of that MA the slope is on.

Regimes:
    bull    — proxy > 200d MA AND 20d slope positive
    bear    — proxy < 200d MA AND 20d slope negative
    neutral — anything else (chop, transition)

Pure function over a (symbol, dt, close, volume) panel — no DB / network.
The job calls `classify_regime(panel)` after loading the lookback window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PROXY_TOP_N = 10
SMA_WINDOW = 200
SLOPE_WINDOW = 20


def _proxy_series(panel: pd.DataFrame, top_n: int = PROXY_TOP_N) -> pd.Series:
    """Equal-weighted close-price index over the top-N most-traded symbols."""
    needed = {"symbol", "dt", "close", "volume"}
    missing = needed - set(panel.columns)
    if missing:
        raise ValueError(f"regime panel missing columns: {missing}")

    work = panel.copy()
    work["dollar_volume"] = work["close"].astype(float) * work["volume"].astype(float)
    liq = work.groupby("symbol")["dollar_volume"].median().sort_values(ascending=False)
    top_symbols = liq.head(top_n).index.tolist()

    proxy = (
        work[work["symbol"].isin(top_symbols)]
        .groupby("dt")["close"]
        .mean()
        .sort_index()
    )
    return proxy.astype(float)


def _slope(s: pd.Series) -> float:
    if s.isna().any() or len(s) < 2:
        return float("nan")
    return float(np.polyfit(np.arange(len(s)), s.to_numpy(), 1)[0])


def classify_regime(panel: pd.DataFrame) -> str:
    """
    Returns one of 'bull' | 'bear' | 'neutral'. Defaults to 'neutral' when
    the proxy can't be computed (fewer than SMA_WINDOW points).
    """
    if panel.empty:
        return "neutral"

    proxy = _proxy_series(panel)
    if len(proxy) < SMA_WINDOW:
        return "neutral"

    sma = proxy.rolling(SMA_WINDOW, min_periods=SMA_WINDOW).mean()
    last_close = proxy.iloc[-1]
    last_sma = sma.iloc[-1]
    if not (np.isfinite(last_close) and np.isfinite(last_sma)):
        return "neutral"

    recent_sma = sma.iloc[-SLOPE_WINDOW:]
    slope = _slope(recent_sma)

    if last_close > last_sma and slope > 0:
        return "bull"
    if last_close < last_sma and slope < 0:
        return "bear"
    return "neutral"
