"""
Model A retraining core. Pure-function over a panel DataFrame.

Two outputs per fold:
  - classifier (LGBMClassifier) on target = future 5-day return > 0
  - regressor  (LGBMRegressor)  on target = future 5-day return (basis points)

ml-conventions: never `train_test_split`; always TimeSeriesSplit.
Walk-forward, default 5 folds, last fold's metrics are reported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from lightgbm import LGBMClassifier, LGBMRegressor

FORWARD_RETURN_DAYS = 5
DEFAULT_N_SPLITS = 5
DEFAULT_CLF_PARAMS: dict[str, Any] = {
    "n_estimators": 800,
    "learning_rate": 0.03,
    "num_leaves": 64,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.2,
    "reg_lambda": 0.4,
    "random_state": 42,
    "verbose": -1,
}
DEFAULT_REG_PARAMS: dict[str, Any] = {
    "n_estimators": 600,
    "learning_rate": 0.05,
    "num_leaves": 48,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "verbose": -1,
}


@dataclass(frozen=True)
class TrainingResult:
    classifier: LGBMClassifier
    regressor: LGBMRegressor
    features: list[str]
    auc_per_fold: list[float]
    rmse_per_fold: list[float]
    auc_mean: float
    auc_std: float
    n_samples: int


def build_target(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Adds `forward_return` (% over the next FORWARD_RETURN_DAYS trading days
    per symbol) and `y_class` (1 if positive, else 0). Rows where the target
    is non-finite (the trailing edge of every symbol's history) are dropped.

    Input panel must have columns: symbol, dt, close.
    """
    required = {"symbol", "dt", "close"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing required columns for target: {missing}")

    df = panel.sort_values(["symbol", "dt"]).copy()
    df["forward_close"] = df.groupby("symbol")["close"].shift(-FORWARD_RETURN_DAYS)
    df["forward_return"] = (df["forward_close"] - df["close"]) / df["close"]
    df["y_class"] = (df["forward_return"] > 0).astype(int)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return df.dropna(subset=["forward_return"])


def walk_forward_split(
    panel: pd.DataFrame, n_splits: int = DEFAULT_N_SPLITS
) -> list[tuple[pd.Index, pd.Index]]:
    """
    TimeSeriesSplit by `dt` — each fold's test set comes strictly AFTER its
    train set. Returns a list of (train_idx, test_idx) tuples.

    Implementation note: sklearn's TimeSeriesSplit assumes rows are sorted in
    chronological order. We sort by `dt` then by `symbol` to keep panel rows
    grouped by time-step.
    """
    from sklearn.model_selection import TimeSeriesSplit  # type: ignore[import-not-found]

    if "dt" not in panel.columns:
        raise ValueError("panel must contain a `dt` column for time-aware splitting")
    ordered = panel.sort_values(["dt", "symbol"]).reset_index(drop=True)
    splitter = TimeSeriesSplit(n_splits=n_splits)
    return [(ordered.index[train], ordered.index[test]) for train, test in splitter.split(ordered)]


def train_model_a(
    panel: pd.DataFrame,
    features: list[str],
    *,
    n_splits: int = DEFAULT_N_SPLITS,
) -> TrainingResult:
    """
    Walk-forward train + final fit on the full set.

    Per-fold:
      - fit on train, score on test (ROC AUC for classifier, RMSE for regressor)
    Final classifier/regressor: trained on the entire dataset.
    """
    from lightgbm import LGBMClassifier, LGBMRegressor
    from sklearn.metrics import mean_squared_error, roc_auc_score  # type: ignore[import-not-found]

    if not features:
        raise ValueError("features must be a non-empty list")

    df = build_target(panel)
    if df.empty:
        raise ValueError("no rows remained after target construction")
    df = df.dropna(subset=features)
    if df.empty:
        raise ValueError("no rows remained after feature dropna")

    df = df.sort_values(["dt", "symbol"]).reset_index(drop=True)
    X = df[features].to_numpy(dtype=float)
    y_class = df["y_class"].to_numpy()
    y_reg = df["forward_return"].to_numpy() * 10_000.0  # in basis points

    aucs: list[float] = []
    rmses: list[float] = []
    for train_idx, test_idx in walk_forward_split(df, n_splits=n_splits):
        clf = LGBMClassifier(**DEFAULT_CLF_PARAMS)
        clf.fit(X[train_idx], y_class[train_idx])
        prob = clf.predict_proba(X[test_idx])[:, 1]
        aucs.append(float(roc_auc_score(y_class[test_idx], prob)))

        reg = LGBMRegressor(**DEFAULT_REG_PARAMS)
        reg.fit(X[train_idx], y_reg[train_idx])
        pred = reg.predict(X[test_idx])
        rmses.append(float(np.sqrt(mean_squared_error(y_reg[test_idx], pred))))

    final_clf = LGBMClassifier(**DEFAULT_CLF_PARAMS)
    final_clf.fit(X, y_class)
    final_reg = LGBMRegressor(**DEFAULT_REG_PARAMS)
    final_reg.fit(X, y_reg)

    return TrainingResult(
        classifier=final_clf,
        regressor=final_reg,
        features=list(features),
        auc_per_fold=aucs,
        rmse_per_fold=rmses,
        auc_mean=float(np.mean(aucs)),
        auc_std=float(np.std(aucs)),
        n_samples=len(df),
    )
