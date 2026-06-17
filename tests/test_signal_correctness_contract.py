"""
model_a v1_6 — signal-correctness source contract (P0-A units + P0-B adj_close).

RUNS IN SANDBOX: reads the relevant modules as *text* (no import), so it does
not need pandas/numpy/lightgbm. The heavy modules cannot be imported in every
environment, so the current/desired contracts are pinned at source level here;
behavioural coverage lives in test_build_target_price_basis.py (CI-only).

Matching is on robust substrings (whitespace-normalised), never line numbers,
so ordinary edits do not break these guards. Strict-xfail desired-v1_6 tests
turn RED (xpass) the moment the refactor lands — the signal to drop the marker.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _src(relpath: str) -> str:
    """Whitespace-normalised source text of a repo file."""
    raw = (_ROOT / relpath).read_text()
    return re.sub(r"[ \t]+", " ", raw)


_TRAIN = "asxos/domain/models/train.py"
_LOADER = "asxos/domain/signals/loader.py"
_ENGINE = "asxos/domain/signals/feature_engine.py"
_THRESHOLDS = "asxos/domain/signals/thresholds.py"


# --- Passing characterization of current v1_5 behaviour ----------------------

def test_v1_5_train_target_scaled_to_basis_points() -> None:
    """CHARACTERIZATION: training scales the regression target by 10_000 (bps)."""
    assert "* 10_000" in _src(_TRAIN)


def test_v1_5_forward_return_target_uses_raw_close() -> None:
    """CHARACTERIZATION: build_target's forward_return is computed from raw close."""
    src = _src(_TRAIN)
    assert 'forward_close' in src
    assert '["close"]' in src
    assert "adj_close" not in src  # target does not use the adjusted series


def test_v1_5_loader_selects_raw_close_only() -> None:
    """CHARACTERIZATION: the panel loader selects raw close, not adj_close."""
    src = _src(_LOADER)
    assert "p.close" in src
    assert "adj_close" not in src


def test_v1_5_return_features_use_raw_close() -> None:
    """CHARACTERIZATION: momentum / trend features are built from raw close."""
    src = _src(_ENGINE)
    assert '["close"].pct_change' in src      # momentum / ret_1d
    assert '"close"' in src                    # sma_200 / trend / atr basis


def test_v1_5_thresholds_are_fractional_scale() -> None:
    """CHARACTERIZATION: thresholds compare expected_return to fractional values
    (0.05), which is incompatible with the bps-scale values now stored in
    signals.expected_return — the documented current defect."""
    src = _src(_THRESHOLDS)
    assert "expected_return > 0.05" in src
    assert "expected_return < -0.05" in src


def test_liquidity_uses_raw_close_times_volume() -> None:
    """CONTRACT (already satisfied, must stay true in v1_6): dollar-volume
    liquidity uses raw close * raw volume (real tradeable dollars). v1_6 moves
    *returns* to adj_close but must NOT adjust the liquidity dollar-volume."""
    assert 'df["close"] * df["volume"]' in _src(_ENGINE)


# --- Strict-xfail desired v1_6 contracts -------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="model_a_v1_6 will switch the regression target to fractional return "
    "(drop the * 10_000 basis-point scaling).",
)
def test_v1_6_train_target_is_fractional_not_bps() -> None:
    assert "10_000" not in _src(_TRAIN)


@pytest.mark.xfail(
    strict=True,
    reason="model_a_v1_6 loader will select adj_close so returns/trend/ATR/target "
    "use the adjusted price series.",
)
def test_v1_6_loader_selects_adj_close() -> None:
    assert "adj_close" in _src(_LOADER)


@pytest.mark.xfail(
    strict=True,
    reason="model_a_v1_6 will compute returns/trend/ATR/target from adj_close "
    "(raw close retained only for liquidity dollar-volume).",
)
def test_v1_6_return_features_use_adj_close() -> None:
    assert "adj_close" in _src(_ENGINE)
