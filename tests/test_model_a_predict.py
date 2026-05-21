"""
Tests for asxos.domain.models.model_a.

Uses the real Model A v1_5 artefacts shipped in models/ so a sklearn or
LightGBM API drift surfaces here. predict_with_shap calls the cache so
its DB lookup is patched to return the on-disk version directly.
"""
from __future__ import annotations

import asyncio
import json
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from asxos.domain.models import cache as cache_mod
from asxos.domain.models.cache import LoadedModel, get_cache
from asxos.domain.models.model_a import (
    _predict,
    predict_with_shap,
    top_shap_factors,
)

ARTEFACTS_DIR = Path(__file__).resolve().parent.parent / "models"


@pytest.fixture(scope="module")
def real_model() -> LoadedModel:
    """Load the committed Model A v1_5 artefacts once per test module."""
    if not (ARTEFACTS_DIR / "model_a_v1_5_classifier.pkl").exists():
        pytest.skip("Model A v1_5 artefacts not present in models/")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # silence sklearn version-skew warning
        clf = joblib.load(ARTEFACTS_DIR / "model_a_v1_5_classifier.pkl")
        reg = joblib.load(ARTEFACTS_DIR / "model_a_v1_5_regressor.pkl")
    features = json.loads((ARTEFACTS_DIR / "model_a_v1_5_features.json").read_text())["features"]
    return LoadedModel("model_a", "v1_5", clf, reg, features)


def _synthetic_features(model: LoadedModel, n: int = 12, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        rng.normal(0.0, 1.0, size=(n, len(model.features))),
        columns=model.features,
        index=[f"SYM{i:02d}.AU" for i in range(n)],
    )
    df.index.name = "symbol"
    return df


# ---------------------------------------------------------------------------
# _predict shape + value sanity
# ---------------------------------------------------------------------------

def test_predict_returns_expected_shapes(real_model: LoadedModel) -> None:
    features = _synthetic_features(real_model, n=8)

    preds, shap_df = _predict(features, real_model)

    assert list(preds.columns) == ["prob_up", "expected_return", "rank"]
    assert len(preds) == 8
    assert set(preds.index) == set(features.index)

    assert shap_df.shape == (8, len(real_model.features) + 1)
    assert list(shap_df.columns) == [*real_model.features, "bias"]


def test_predict_probabilities_within_unit_interval(real_model: LoadedModel) -> None:
    features = _synthetic_features(real_model, n=15)

    preds, _ = _predict(features, real_model)

    assert ((preds["prob_up"] >= 0.0) & (preds["prob_up"] <= 1.0)).all()
    assert np.isfinite(preds["expected_return"]).all()


def test_predict_rank_is_dense_and_sorted(real_model: LoadedModel) -> None:
    features = _synthetic_features(real_model, n=10, seed=3)

    preds, _ = _predict(features, real_model)

    # sorted by rank ascending → prob_up monotonically non-increasing
    assert preds["prob_up"].is_monotonic_decreasing
    assert preds["rank"].iloc[0] == 1
    assert preds["rank"].iloc[-1] == 10


def test_predict_missing_feature_raises(real_model: LoadedModel) -> None:
    features = _synthetic_features(real_model)
    dropped = features.drop(columns=[real_model.features[0]])

    with pytest.raises(ValueError, match="missing required columns"):
        _predict(dropped, real_model)


def test_predict_empty_frame_raises(real_model: LoadedModel) -> None:
    empty = pd.DataFrame(columns=real_model.features)
    with pytest.raises(ValueError, match="empty"):
        _predict(empty, real_model)


def test_predict_nan_features_raises(real_model: LoadedModel) -> None:
    features = _synthetic_features(real_model, n=3)
    features.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or inf"):
        _predict(features, real_model)


# ---------------------------------------------------------------------------
# top_shap_factors
# ---------------------------------------------------------------------------

def test_top_shap_factors_orders_by_absolute_magnitude() -> None:
    row = pd.Series({"a": 0.1, "b": -0.5, "c": 0.3, "d": -0.05, "bias": 0.8})
    factors = top_shap_factors(row, n=3)
    assert [name for name, _ in factors] == ["b", "c", "a"]
    assert factors[0][1] == -0.5  # signed value preserved


def test_top_shap_factors_excludes_bias() -> None:
    row = pd.Series({"a": 0.1, "bias": 99.0})
    factors = top_shap_factors(row, n=5)
    assert "bias" not in [name for name, _ in factors]


def test_top_shap_factors_handles_missing_bias() -> None:
    row = pd.Series({"a": 0.4, "b": 0.1})
    factors = top_shap_factors(row, n=1)
    assert factors == [("a", pytest.approx(0.4))]


# ---------------------------------------------------------------------------
# predict_with_shap — exercises the cache wiring
# ---------------------------------------------------------------------------

def test_predict_with_shap_uses_cache(
    real_model: LoadedModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Inject the loaded model directly so the cache short-circuits the DB lookup.
    cache = get_cache()
    cache.clear()
    cache._loaded["model_a"] = real_model
    cache._last_check["model_a"] = float("inf")

    @asynccontextmanager
    async def _fail_acquire():
        raise AssertionError("cache should not touch the DB within TTL")
        yield  # pragma: no cover

    monkeypatch.setattr(cache_mod, "acquire", _fail_acquire)

    features = _synthetic_features(real_model, n=6)
    preds, shap_df = asyncio.run(predict_with_shap(features))

    assert len(preds) == 6
    assert shap_df.shape == (6, len(real_model.features) + 1)
    cache.clear()
