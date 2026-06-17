"""
model_a artefact metadata — v1_6 self-describing contract.

Pure stdlib (no pandas/numpy/lightgbm), so it imports and tests everywhere.
This is the home of the v1_6 "units + price basis are recorded, not inferred"
contract that closes the P0-A ambiguity (v1_5 artefacts never declared whether
expected_return was basis points or a fraction).

It does NOT train, load artefacts, or touch the DB — it only builds a dict.
"""
from __future__ import annotations

from typing import Any

# Must match train.FORWARD_RETURN_DAYS (kept local to avoid importing the
# pandas-heavy train module just for one constant).
DEFAULT_LABEL_HORIZON_DAYS = 5

# Fields a v1_6 artefact metadata blob must declare. Mirrors the contract in
# tests/test_model_artifact_contract.py.
REQUIRED_V1_6_FIELDS: frozenset[str] = frozenset(
    {
        "target_unit",
        "price_basis",
        "feature_price_basis",
        "liquidity_price_basis",
        "label_horizon_days",
        "purge_embargo_days",
        "train_start",
        "train_end",
    }
)


def build_artifact_metadata(
    *,
    model_version: str,
    target_unit: str,
    price_basis: str,
    train_start: str,
    train_end: str,
    purge_embargo_days: int = DEFAULT_LABEL_HORIZON_DAYS,
    label_horizon_days: int = DEFAULT_LABEL_HORIZON_DAYS,
    liquidity_price_basis: str = "close",
) -> dict[str, Any]:
    """Self-describing artefact metadata for the v1_6 contract.

    `feature_price_basis` mirrors `price_basis` (returns / trend / ATR);
    liquidity dollar-volume always uses raw close, so `liquidity_price_basis`
    defaults to "close" and should stay that way.

    Records units + price basis + leakage guard so a future reader never infers
    them from artefact magnitudes (the v1_5 bps/fraction ambiguity).
    """
    if target_unit not in ("basis_points", "fraction"):
        raise ValueError(f"target_unit must be 'basis_points' or 'fraction', got {target_unit!r}")
    if price_basis not in ("close", "adj_close"):
        raise ValueError(f"price_basis must be 'close' or 'adj_close', got {price_basis!r}")
    return {
        "model_version": model_version,
        "target_unit": target_unit,
        "price_basis": price_basis,
        "feature_price_basis": price_basis,
        "liquidity_price_basis": liquidity_price_basis,
        "label_horizon_days": label_horizon_days,
        "purge_embargo_days": purge_embargo_days,
        "train_start": train_start,
        "train_end": train_end,
    }
