"""
model_a v1_6 shadow-training-readiness contracts for ModelTrainingConfig.

Pure stdlib (no pandas/numpy/lightgbm) — runs everywhere, including the
lint-only sandbox. These guard the v1_6 training *readiness* invariants:
  * v1_5 config defaults reproduce the active production behaviour exactly.
  * the v1_6 config declares adj_close basis + fractional target + raw-close
    liquidity, and produces complete self-describing artefact metadata.
  * the config cannot represent activation, and the production training entry
    point (jobs/retrain_model_a.py) cannot activate a model — activation is the
    separate, explicit `asx model activate` command.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from asxos.domain.models.metadata import REQUIRED_V1_6_FIELDS
from asxos.domain.models.training_config import (
    MODEL_A_V1_5_CONFIG,
    MODEL_A_V1_6_CONFIG,
    ModelTrainingConfig,
    select_training_config,
    training_panel_columns,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


# --- v1_5 default preservation ------------------------------------------------

def test_v1_5_config_defaults_unchanged() -> None:
    """The v1_5 config reproduces the active production behaviour exactly."""
    c = MODEL_A_V1_5_CONFIG
    assert c.model_version == "model_a_v1_5"
    assert c.price_basis == "close"
    assert c.target_unit == "basis_points"
    assert c.liquidity_price_basis == "close"
    assert c.include_adj_close is False


def test_default_construction_is_v1_5_behaviour() -> None:
    """A config built with only a version name defaults to the v1_5 path."""
    c = ModelTrainingConfig(model_version="model_a_v1_5")
    assert c.train_model_a_kwargs == {"target_unit": "basis_points", "price_basis": "close"}
    assert c.load_panel_kwargs == {"include_adj_close": False}


# --- v1_6 config --------------------------------------------------------------

def test_v1_6_config_exists_and_uses_adj_close_fraction() -> None:
    """v1_6 config: adj_close basis, fractional target, raw-close liquidity."""
    c = MODEL_A_V1_6_CONFIG
    assert c.model_version == "model_a_v1_6"
    assert c.price_basis == "adj_close"
    assert c.target_unit == "fraction"
    assert c.liquidity_price_basis == "close"
    assert c.include_adj_close is True


def test_v1_6_kwargs_thread_into_trainer_and_loader() -> None:
    """The config exposes exactly the kwargs a future shadow run threads in."""
    c = MODEL_A_V1_6_CONFIG
    assert c.train_model_a_kwargs == {"target_unit": "fraction", "price_basis": "adj_close"}
    assert c.load_panel_kwargs == {"include_adj_close": True}


def test_v1_6_metadata_includes_required_fields() -> None:
    """to_artifact_metadata() produces complete, correct v1_6 metadata."""
    meta = MODEL_A_V1_6_CONFIG.to_artifact_metadata(
        train_start="2015-01-01", train_end="2026-06-01"
    )
    # every required v1_6 field is present
    assert REQUIRED_V1_6_FIELDS <= set(meta)
    assert meta["model_version"] == "model_a_v1_6"
    assert meta["target_unit"] == "fraction"
    assert meta["price_basis"] == "adj_close"
    assert meta["feature_price_basis"] == "adj_close"
    assert meta["liquidity_price_basis"] == "close"
    assert meta["label_horizon_days"] == 5
    assert meta["purge_embargo_days"] == 5
    assert meta["train_start"] == "2015-01-01"
    assert meta["train_end"] == "2026-06-01"


# --- validation guards --------------------------------------------------------

def test_adj_close_requires_include_adj_close() -> None:
    with pytest.raises(ValueError, match="requires include_adj_close"):
        ModelTrainingConfig(model_version="x", price_basis="adj_close", include_adj_close=False)


def test_rejects_bad_price_basis_and_target_unit() -> None:
    with pytest.raises(ValueError, match="price_basis"):
        ModelTrainingConfig(model_version="x", price_basis="vwap")
    with pytest.raises(ValueError, match="target_unit"):
        ModelTrainingConfig(model_version="x", target_unit="dollars")


def test_liquidity_basis_must_stay_raw_close() -> None:
    with pytest.raises(ValueError, match="liquidity_price_basis"):
        ModelTrainingConfig(
            model_version="x",
            price_basis="adj_close",
            include_adj_close=True,
            liquidity_price_basis="adj_close",
        )


# --- no-activation guards -----------------------------------------------------

def test_config_cannot_represent_activation() -> None:
    """The config has no field that could activate a model (defence in depth)."""
    field_names = {f.name for f in dataclasses.fields(ModelTrainingConfig)}
    assert not any("activate" in n or "is_active" in n for n in field_names)


def test_retrain_job_inserts_inactive_and_never_activates() -> None:
    """The training entry point cannot flip is_active to TRUE.

    jobs/retrain_model_a.py inserts a candidate model_versions row with
    is_active = FALSE. It may READ the active row (SELECT ... WHERE is_active =
    TRUE, to compute the degradation baseline) but contains no statement that
    SETs is_active TRUE — i.e. no activation UPDATE.
    """
    src = (_REPO_ROOT / "jobs" / "retrain_model_a.py").read_text()
    normalized = src.replace(" ", "").lower()
    # candidate insert pins is_active FALSE
    assert "values($1,$2,$3,false,$4)" in normalized
    # no activation: the job never does `UPDATE ... SET is_active = TRUE`
    assert "setis_active=true" not in normalized


def test_activation_lives_only_in_explicit_cli_command() -> None:
    """The only is_active=TRUE flip is the explicit `asx model activate`."""
    cli_src = (_REPO_ROOT / "asxos" / "cli" / "model.py").read_text().replace(" ", "").lower()
    assert "is_active=true" in cli_src  # activation exists, but only here


# --- select_training_config ---------------------------------------------------

def test_select_training_config_maps_known_versions() -> None:
    assert select_training_config("model_a_v1_5") is MODEL_A_V1_5_CONFIG
    assert select_training_config("model_a_v1_6") is MODEL_A_V1_6_CONFIG


def test_select_training_config_unknown_falls_back_to_v1_5() -> None:
    """Any non-v1_6 version resolves to the v1_5 baseline recipe (identity)."""
    assert select_training_config("model_a_v1_7") is MODEL_A_V1_5_CONFIG
    assert select_training_config("model_a_v9_9") is MODEL_A_V1_5_CONFIG
    assert select_training_config("") is MODEL_A_V1_5_CONFIG


# --- training_panel_columns ---------------------------------------------------

_FEATS = ["ret_1d", "vol_30", "pe_ratio"]


def test_panel_columns_v1_5_excludes_adj_close() -> None:
    cols = training_panel_columns(MODEL_A_V1_5_CONFIG, _FEATS)
    assert "adj_close" not in cols
    assert {"symbol", "dt", "close"} <= set(cols)
    assert set(_FEATS) <= set(cols)


def test_panel_columns_v1_6_includes_adj_close() -> None:
    cols = training_panel_columns(MODEL_A_V1_6_CONFIG, _FEATS)
    assert "adj_close" in cols
    # raw close is still kept (build_target grouping + raw-close liquidity)
    assert {"symbol", "dt", "close"} <= set(cols)
    assert set(_FEATS) <= set(cols)


def test_panel_columns_is_deterministic_sorted() -> None:
    cols = training_panel_columns(MODEL_A_V1_6_CONFIG, _FEATS)
    assert cols == sorted(cols)
