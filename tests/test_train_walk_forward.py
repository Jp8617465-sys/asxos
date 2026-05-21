"""
Walk-forward training tests for asxos.domain.models.train.

Two strands:
- Target construction (forward returns) drops trailing rows correctly.
- TimeSeriesSplit produces folds where every test row's `dt` is strictly
  greater than every train row's `dt` (no future leakage).
- A small synthetic training run produces a valid TrainingResult.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from asxos.domain.models.train import (
    FORWARD_RETURN_DAYS,
    build_target,
    train_model_a,
    walk_forward_split,
)


def _panel(n_days: int = 80, n_symbols: int = 8, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=n_days, freq="B")
    rows = []
    for i in range(n_symbols):
        close = 50.0 + np.cumsum(rng.normal(0.05, 0.5, n_days))
        close = np.maximum(close, 1.0)
        for j, c in enumerate(close):
            rows.append({"symbol": f"S{i:02d}.AU", "dt": dates[j], "close": float(c)})
    return pd.DataFrame(rows)


def test_build_target_drops_trailing_window() -> None:
    panel = _panel(n_days=30, n_symbols=2)
    out = build_target(panel)
    # Each symbol loses the last FORWARD_RETURN_DAYS rows
    assert len(out) == 2 * (30 - FORWARD_RETURN_DAYS)
    assert (out["forward_return"].notna()).all()


def test_build_target_class_labels_match_sign() -> None:
    panel = _panel(n_days=20, n_symbols=1)
    out = build_target(panel)
    assert ((out["y_class"] == (out["forward_return"] > 0).astype(int)).all())


def test_build_target_rejects_missing_columns() -> None:
    bad = pd.DataFrame({"symbol": ["X"], "dt": [pd.Timestamp("2025-01-01")]})
    with pytest.raises(ValueError, match="required columns"):
        build_target(bad)


def test_walk_forward_no_future_leakage() -> None:
    panel = _panel(n_days=60, n_symbols=3)
    folds = walk_forward_split(panel, n_splits=5)
    ordered = panel.sort_values(["dt", "symbol"]).reset_index(drop=True)
    for train_idx, test_idx in folds:
        max_train_dt = ordered.loc[train_idx, "dt"].max()
        min_test_dt = ordered.loc[test_idx, "dt"].min()
        assert max_train_dt <= min_test_dt, (
            "TimeSeriesSplit leaked: train dt extends into test range"
        )


def test_walk_forward_produces_n_folds() -> None:
    panel = _panel(n_days=60, n_symbols=3)
    folds = walk_forward_split(panel, n_splits=4)
    assert len(folds) == 4


def test_train_model_a_returns_valid_result() -> None:
    # Build a tiny but legitimate training set with one synthetic feature.
    panel = _panel(n_days=120, n_symbols=6)
    panel["feat_a"] = panel.groupby("symbol")["close"].pct_change().fillna(0.0)
    result = train_model_a(panel, features=["feat_a"], n_splits=3)

    assert result.classifier is not None
    assert result.regressor is not None
    assert len(result.auc_per_fold) == 3
    assert 0.0 <= result.auc_mean <= 1.0
    assert result.n_samples > 0
    assert result.features == ["feat_a"]


def test_train_model_a_rejects_empty_features() -> None:
    panel = _panel(n_days=30, n_symbols=2)
    with pytest.raises(ValueError, match="features"):
        train_model_a(panel, features=[], n_splits=2)


def test_train_model_a_rejects_unusable_panel() -> None:
    # Too short to allow any forward return.
    panel = _panel(n_days=FORWARD_RETURN_DAYS, n_symbols=1)
    panel["feat_a"] = 0.0
    with pytest.raises(ValueError, match="target construction"):
        train_model_a(panel, features=["feat_a"], n_splits=2)
