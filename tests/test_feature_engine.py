"""
Tests for the M5 feature engine.
All synthetic data — no DB or network calls.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from asxos.domain.signals.feature_engine import MODEL_A_FEATURES, FeatureEngine, _safe_quintile


def _make_prices(n: int = 300, symbol: str = "BHP.AU", with_fundamentals: bool = False) -> pd.DataFrame:
    """Generate a price series long enough for all rolling windows."""
    rng = np.random.default_rng(42)
    close = 40.0 + np.cumsum(rng.normal(0, 0.5, n))
    close = np.maximum(close, 1.0)
    df = pd.DataFrame(
        {
            "symbol": symbol,
            "dt": pd.date_range("2023-01-01", periods=n, freq="B"),
            "close": close,
            "volume": rng.integers(500_000, 5_000_000, n),
        }
    )
    if with_fundamentals:
        df["pe_ratio"] = 15.0 + rng.normal(0, 2, n)
        df["pb_ratio"] = 1.8 + rng.normal(0, 0.3, n)
        df["eps"] = 2.5 + rng.normal(0, 0.5, n)
        df["market_cap"] = 5e10 + rng.normal(0, 1e9, n)
    return df


def _make_multi(n: int = 300) -> pd.DataFrame:
    """Two-symbol DataFrame for cross-symbol tests."""
    return pd.concat([_make_prices(n, "BHP.AU"), _make_prices(n, "CBA.AU")], ignore_index=True)


def test_compute_all_features_rejects_unsorted_dt() -> None:
    # Lookback features depend on per-symbol ascending dt order; an unsorted panel
    # must fail loudly, not silently emit wrong-but-finite features.
    shuffled = _make_prices(300).sample(frac=1.0, random_state=0).reset_index(drop=True)
    with pytest.raises(ValueError, match="sorted ascending by dt"):
        FeatureEngine().compute_all_features(shuffled)


def test_compute_all_features_accepts_sorted_dt() -> None:
    # The happy path (already sorted, as all production callers pass) is unaffected.
    out = FeatureEngine().compute_all_features(_make_prices(300))
    assert len(out) == 300


# ---------------------------------------------------------------------------
# Basic output shape
# ---------------------------------------------------------------------------


def test_all_22_features_present():
    """All 22 model features are present when fundamentals are pre-joined."""
    engine = FeatureEngine()
    df = _make_prices(300, with_fundamentals=True)
    out = engine.compute_all_features(df)
    missing = [f for f in MODEL_A_FEATURES if f not in out.columns]
    assert missing == [], f"Missing features: {missing}"


def test_output_row_count_unchanged():
    engine = FeatureEngine()
    df = _make_prices(300)
    out = engine.compute_all_features(df)
    assert len(out) == len(df)


def test_missing_required_column_raises():
    engine = FeatureEngine()
    df = _make_prices(300).drop(columns=["volume"])
    with pytest.raises(ValueError, match="volume"):
        engine.compute_all_features(df)


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------


def test_ret_1d_is_pct_change():
    engine = FeatureEngine()
    df = _make_prices(300)
    out = engine.compute_all_features(df)
    expected = df["close"].pct_change()
    pd.testing.assert_series_equal(
        out["ret_1d"].reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_mom_values_are_finite_or_nan():
    engine = FeatureEngine()
    out = engine.compute_all_features(_make_prices(300))
    for feat in ("mom_1", "mom_3", "mom_6", "mom_12_1"):
        assert np.isfinite(out[feat].dropna()).all(), f"{feat} has inf values"


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


def test_trend_200_binary():
    engine = FeatureEngine()
    out = engine.compute_all_features(_make_prices(300))
    vals = out["trend_200"].dropna().unique()
    assert set(vals).issubset({0, 1})


def test_sma200_slope_pos_consistent_with_slope():
    engine = FeatureEngine()
    out = engine.compute_all_features(_make_prices(300))
    mask = out["sma200_slope"].notna()
    expected_pos = (out.loc[mask, "sma200_slope"] > 0).astype(int)
    pd.testing.assert_series_equal(
        out.loc[mask, "sma200_slope_pos"],
        expected_pos,
        check_names=False,
    )


# ---------------------------------------------------------------------------
# Fundamentals — optional columns don't crash; zscore is computed when present
# ---------------------------------------------------------------------------


def test_fundamentals_absent_no_crash():
    engine = FeatureEngine()
    out = engine.compute_all_features(_make_prices(300))
    # pe_ratio and pb_ratio not in input — zscores should be absent or all-NaN
    for col in ("pe_ratio_zscore", "pb_ratio_zscore"):
        if col in out.columns:
            assert out[col].isna().all()


def test_pe_ratio_zscore_computed_when_present():
    engine = FeatureEngine()
    df = _make_prices(300)
    df["pe_ratio"] = 15.0 + np.random.default_rng(7).normal(0, 2, 300)
    out = engine.compute_all_features(df)
    assert "pe_ratio_zscore" in out.columns
    # at least some non-NaN values after warmup window
    assert out["pe_ratio_zscore"].notna().sum() > 0


# ---------------------------------------------------------------------------
# _safe_quintile
# ---------------------------------------------------------------------------


def test_safe_quintile_normal_case():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    result = _safe_quintile(s, q=5)
    assert result.notna().all()
    assert set(result.unique()).issubset({0.0, 1.0, 2.0, 3.0, 4.0})


def test_safe_quintile_single_element_returns_nan():
    # 1 element can't be split into 5 bins — qcut raises, we return NaN
    s = pd.Series([5.0])
    result = _safe_quintile(s, q=5)
    assert result.isna().all()


def test_safe_quintile_all_nan_returns_nan():
    s = pd.Series([np.nan] * 10)
    result = _safe_quintile(s, q=5)
    assert result.isna().all()


# ---------------------------------------------------------------------------
# Multi-symbol: no cross-contamination
# ---------------------------------------------------------------------------


def test_multi_symbol_ret_1d_no_contamination():
    """First row of each symbol group must have NaN ret_1d, not a cross-symbol value."""
    engine = FeatureEngine()
    out = engine.compute_all_features(_make_multi(300))
    for sym in ("BHP.AU", "CBA.AU"):
        first_idx = out[out["symbol"] == sym].index[0]
        assert pd.isna(out.loc[first_idx, "ret_1d"])
