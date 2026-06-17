"""
model_a v1_6 — artefact-metadata correctness contract (P0 signal correctness).

RUNS IN SANDBOX: pure stdlib (json + pathlib); imports no pandas/numpy/lightgbm,
so it executes everywhere, not just on the ML-enabled CI image.

Two kinds of test (per the v1_6 contract design):
  * Passing CHARACTERIZATION of current v1_5 artefact behaviour.
  * Strict-xfail DESIRED v1_6 contracts the current artefacts do not yet meet.
    A strict xfail stays green while the defect exists and turns RED (xpass) the
    moment v1_6 satisfies it — forcing removal of the marker at that point.

Nothing here mutates artefacts; it only reads the committed v1_5 metadata JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def _load_json(name: str) -> dict:
    return json.loads((_MODELS_DIR / name).read_text())


# Fields the v1_6 artefact metadata MUST declare so units / price basis are
# self-describing (see the v1_6 design doc). v1_5 records none of these.
_REQUIRED_V1_6_META: frozenset[str] = frozenset(
    {
        "target_unit",            # e.g. "fractional_forward_return_5d"
        "price_basis",            # e.g. "adj_close"
        "feature_price_basis",    # adj_close for returns/trend/ATR
        "liquidity_price_basis",  # raw close for dollar-volume
        "label_horizon_days",     # 5
        "purge_embargo_days",     # walk-forward leakage guard
        "train_start",
        "train_end",
    }
)


def _missing_v1_6_fields(meta: dict) -> set[str]:
    return set(_REQUIRED_V1_6_META) - set(meta)


# --- Passing characterization of current v1_5 artefacts ----------------------

def test_v1_5_metrics_rmse_is_basis_point_scale() -> None:
    """CHARACTERIZATION (v1_5): the live regressor's RMSE is basis-point scale.

    A regressor trained on a *fractional* 5-day return would report RMSE on the
    order of ~0.0x. v1_5 reports rmse_mean ~= 82.5, which is only sensible if the
    target was scaled to basis points (forward_return * 10_000). This is the
    artefact-level proof of the expected_return unit mismatch.
    """
    metrics = _load_json("model_a_v1_5_metrics.json")
    assert "rmse_mean" in metrics
    rmse = float(metrics["rmse_mean"])
    # Far above any plausible fractional-return RMSE (~0.0x) -> basis points.
    assert rmse > 1.0, f"expected bps-scale RMSE, got {rmse} (looks fractional?)"


def test_v1_5_features_contract_is_22() -> None:
    """CHARACTERIZATION (v1_5): the locked 22-feature contract."""
    feats = _load_json("model_a_v1_5_features.json")
    assert len(feats["features"]) == 22


def test_v1_6_metadata_validator_accepts_a_complete_dict() -> None:
    """The v1_6 metadata contract is satisfiable: a complete dict has no gaps.

    Guards the validator itself so the strict-xfail below fails for the right
    reason (missing fields), not a broken contract definition.
    """
    complete = {
        "model_version": "v1_6",
        "target_unit": "fractional_forward_return_5d",
        "price_basis": "adj_close",
        "feature_price_basis": "adj_close",
        "liquidity_price_basis": "raw_close",
        "label_horizon_days": 5,
        "purge_embargo_days": 5,
        "train_start": "2025-01-02",
        "train_end": "2026-06-15",
    }
    assert _missing_v1_6_fields(complete) == set()


# --- Strict-xfail desired v1_6 contract --------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="model_a_v1_6 artefact metadata will declare target_unit / price_basis "
    "/ label_horizon_days / purge_embargo_days; v1_5 records none of these.",
)
def test_v1_6_artifact_metadata_declares_units_and_price_basis() -> None:
    metrics = _load_json("model_a_v1_5_metrics.json")
    assert _missing_v1_6_fields(metrics) == set()
