"""
Model A: predict + SHAP for one date.

predict_with_shap takes a symbol-indexed features DataFrame and returns:
  preds_df   — symbol-indexed; prob_up, expected_return, rank
  shap_df    — symbol-indexed; one column per feature + 'bias' (LightGBM
               TreeSHAP in logit space for the binary classifier head)

Same FeatureEngine instance must produce `features_df` in training and at
inference to avoid serving skew (ml-conventions.md).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from asxos.domain.models.cache import LoadedModel, get_cache


async def predict_with_shap(
    features_df: pd.DataFrame,
    *,
    model_name: str = "model_a",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model = await get_cache().get(model_name)
    return _predict(features_df, model)


def _predict(features_df: pd.DataFrame, model: LoadedModel) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = [f for f in model.features if f not in features_df.columns]
    if missing:
        raise ValueError(f"features_df missing required columns: {missing}")
    if len(features_df) == 0:
        raise ValueError("features_df is empty — nothing to predict")

    X = features_df[model.features].astype(float).to_numpy()
    if not np.isfinite(X).all():
        raise ValueError(
            "features_df contains NaN or inf — fill or drop before predict"
        )

    prob_up = model.classifier.predict_proba(X)[:, 1]
    expected_return = model.regressor.predict(X)

    shap_contribs = model.classifier.predict(X, pred_contrib=True)
    shap_df = pd.DataFrame(
        shap_contribs,
        index=features_df.index,
        columns=[*model.features, "bias"],
    )

    preds = pd.DataFrame(
        {"prob_up": prob_up, "expected_return": expected_return},
        index=features_df.index,
    )
    preds["rank"] = preds["prob_up"].rank(ascending=False, method="min").astype(int)
    return preds.sort_values("rank"), shap_df


def top_shap_factors(shap_row: pd.Series, n: int = 3) -> list[tuple[str, float]]:
    """Top-N features by |SHAP contribution|, excluding the bias term."""
    contribs = shap_row.drop(labels="bias", errors="ignore")
    ordered = contribs.reindex(contribs.abs().sort_values(ascending=False).index)
    return [(str(name), float(val)) for name, val in ordered.head(n).items()]
