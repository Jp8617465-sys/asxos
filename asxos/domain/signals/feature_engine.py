"""
Feature engine for Model A — 22 features from prices + fundamentals.

Same code path used in training and inference to eliminate training/serving skew.

Required input columns: symbol, dt, close, volume
Optional input columns: high, low, pe_ratio, pb_ratio, eps, market_cap

Fundamental columns (pe_ratio, pb_ratio, eps, market_cap) must be pre-joined
with a 45-day disclosure lag before calling compute_all_features().
"""
from __future__ import annotations

import logging
from typing import Any, ClassVar

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

MODEL_A_FEATURES: list[str] = [
    "ret_1d",
    "mom_1",
    "mom_3",
    "mom_6",
    "mom_12_1",
    "vol_30",
    "vol_60",
    "vol_90",
    "vol_ratio_30_90",
    "adv_20_median",
    "adv_zscore",
    "trend_200",
    "sma200_slope",
    "sma200_slope_pos",
    "atr_pct",
    "volume_skew_60",
    "pe_ratio",
    "pb_ratio",
    "eps",
    "market_cap",
    "pe_ratio_zscore",
    "pb_ratio_zscore",
]


def _safe_quintile(x: pd.Series | np.ndarray[Any, Any], q: int = 5) -> pd.Series:
    """pd.qcut() with rank-based tie-breaking; returns all-NaN Series on failure."""
    s = x if isinstance(x, pd.Series) else pd.Series(x)
    work = s.rank(method="first")
    try:
        return pd.qcut(work, q=q, labels=False, duplicates="drop")
    except ValueError:
        return pd.Series(np.nan, index=s.index)


class FeatureEngine:
    """
    Computes 22 Model A features from a symbol×date price+fundamentals DataFrame.

    Usage:
        engine = FeatureEngine()
        df_with_features = engine.compute_all_features(df)
    """

    # Window sizes in trading days — must match training configuration
    _MOM_WINDOWS: ClassVar[dict[str, int]] = {
        "mom_1": 21,
        "mom_3": 63,
        "mom_6": 126,
        "mom_12_1": 231,  # 12 months minus 1 month (252 - 21)
    }
    _VOL_WINDOWS: ClassVar[dict[str, int]] = {"vol_30": 30, "vol_60": 60, "vol_90": 90}
    _SMA_SLOPE_WINDOW: int = 20

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all 22 Model A features and return an augmented copy.

        Raises ValueError if required columns are missing.
        All inf values are replaced with NaN on return.
        """
        required = {"symbol", "dt", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = df.copy()
        df = self._momentum(df)
        df = self._volatility(df)
        df = self._liquidity(df)
        df = self._trend(df)
        df = self._fundamental(df)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        return df

    # ------------------------------------------------------------------
    # Feature groups (private)
    # ------------------------------------------------------------------

    def _momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        for name, window in self._MOM_WINDOWS.items():
            df[name] = df.groupby("symbol")["close"].pct_change(window)
        df["ret_1d"] = df.groupby("symbol")["close"].pct_change()
        return df

    def _volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        for name, window in self._VOL_WINDOWS.items():
            df[name] = df.groupby("symbol")["ret_1d"].transform(
                lambda x, w=window: x.rolling(w, min_periods=w // 2).std()
            )
        df["vol_ratio_30_90"] = df["vol_30"] / df["vol_90"]
        return df

    def _liquidity(self, df: pd.DataFrame) -> pd.DataFrame:
        dollar_vol = df["close"] * df["volume"]
        df["adv_20_median"] = dollar_vol.groupby(df["symbol"]).transform(
            lambda x: x.rolling(20, min_periods=10).median()
        )
        df["adv_zscore"] = df.groupby("symbol")["adv_20_median"].transform(
            lambda x: (x - x.rolling(252, min_periods=60).mean())
            / x.rolling(252, min_periods=60).std()
        )
        df["volume_skew_60"] = df.groupby("symbol")["volume"].transform(
            lambda x: x.rolling(60, min_periods=30).skew()
        )
        return df

    def _trend(self, df: pd.DataFrame) -> pd.DataFrame:
        df["sma_200"] = df.groupby("symbol")["close"].transform(
            lambda x: x.rolling(200, min_periods=100).mean()
        )
        df["trend_200"] = (df["close"] > df["sma_200"]).astype(int)

        def _slope(s: pd.Series) -> float:
            if s.isna().any() or len(s) < 2:
                return np.nan
            return float(np.polyfit(np.arange(len(s)), s.values, 1)[0])

        w = self._SMA_SLOPE_WINDOW
        df["sma200_slope"] = df.groupby("symbol")["sma_200"].transform(
            lambda x: x.rolling(w, min_periods=w).apply(_slope, raw=False)
        )
        df["sma200_slope_pos"] = (df["sma200_slope"] > 0).astype(int)

        # True range: use OHLC if available, else proxy with |ret_1d| * close
        if "high" in df.columns and "low" in df.columns:
            prev_close = df.groupby("symbol")["close"].shift(1)
            tr = pd.concat(
                [
                    df["high"] - df["low"],
                    (df["high"] - prev_close).abs(),
                    (df["low"] - prev_close).abs(),
                ],
                axis=1,
            ).max(axis=1)
        else:
            tr = df["ret_1d"].abs() * df["close"]

        atr_14 = tr.groupby(df["symbol"]).transform(
            lambda x: x.rolling(14, min_periods=7).mean()
        )
        df["atr_pct"] = atr_14 / df["close"]
        return df

    def _fundamental(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ("pe_ratio", "pb_ratio"):
            if col in df.columns:
                df[f"{col}_zscore"] = df.groupby("symbol")[col].transform(
                    lambda x: (x - x.rolling(252, min_periods=60).mean())
                    / x.rolling(252, min_periods=60).std()
                )
        return df
