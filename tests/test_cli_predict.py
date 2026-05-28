"""
CLI smoke test for `asx predict <date>`.

Patches db pool + feature loader so the test exercises the Typer wiring,
argument parsing, the cache hand-off, and the rich.Table render — but
without a real Postgres connection.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import joblib
import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import predict as predict_mod
from asxos.domain.models import cache as cache_mod
from asxos.domain.models.cache import LoadedModel, get_cache

runner = CliRunner()
ARTEFACTS_DIR = Path(__file__).resolve().parent.parent / "models"


@pytest.fixture
def loaded_model(monkeypatch: pytest.MonkeyPatch) -> LoadedModel:
    if not (ARTEFACTS_DIR / "model_a_v1_5_classifier.pkl").exists():
        pytest.skip("Model A v1_5 artefacts not present in models/")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clf = joblib.load(ARTEFACTS_DIR / "model_a_v1_5_classifier.pkl")
        reg = joblib.load(ARTEFACTS_DIR / "model_a_v1_5_regressor.pkl")
    features = json.loads((ARTEFACTS_DIR / "model_a_v1_5_features.json").read_text())["features"]
    model = LoadedModel("model_a", "v1_5", clf, reg, features)

    cache = get_cache()
    cache.clear()
    cache._loaded["model_a"] = model
    cache._last_check["model_a"] = float("inf")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _no_db():
        raise AssertionError("CLI must not touch the DB in this test")
        yield  # pragma: no cover

    monkeypatch.setattr(cache_mod, "acquire", _no_db)

    yield model
    cache.clear()


def _features_frame(model: LoadedModel, n: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    df = pd.DataFrame(
        rng.normal(0.0, 1.0, size=(n, len(model.features))),
        columns=model.features,
        index=[f"SYM{i:02d}.AU" for i in range(n)],
    )
    df.index.name = "symbol"
    return df


def test_predict_command_renders_top_table(loaded_model: LoadedModel) -> None:
    features = _features_frame(loaded_model, n=12)

    with (
        patch.object(predict_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(predict_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(predict_mod, "acquire") as acquire_patch,
        patch.object(predict_mod, "load_features_for_date", new=AsyncMock(return_value=features)),
    ):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _conn() -> Any:
            yield object()

        acquire_patch.side_effect = _conn

        result = runner.invoke(cli_main.app, ["predict", "2026-05-15", "--top", "5"])

    assert result.exit_code == 0, result.output
    assert "Model A" in result.output
    assert "2026-05-15" in result.output
    assert "prob_up" in result.output
    # 5 ranked rows shown
    assert sum(line.startswith("│") and "SYM" in line for line in result.output.splitlines()) >= 5


def test_predict_command_empty_features_returns_nonzero(loaded_model: LoadedModel) -> None:
    empty = pd.DataFrame(columns=loaded_model.features)

    with (
        patch.object(predict_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(predict_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(predict_mod, "acquire") as acquire_patch,
        patch.object(predict_mod, "load_features_for_date", new=AsyncMock(return_value=empty)),
    ):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _conn() -> Any:
            yield object()

        acquire_patch.side_effect = _conn

        result = runner.invoke(cli_main.app, ["predict", "2026-05-15"])

    assert result.exit_code == 1
    assert "No features computable" in result.output


def test_predict_command_bad_date_format() -> None:
    result = runner.invoke(cli_main.app, ["predict", "not-a-date"])
    assert result.exit_code != 0
    assert "YYYY-MM-DD" in result.output
