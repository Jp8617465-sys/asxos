"""
model_a v1_6 — signal-correctness source contract (P0-A units + P0-B adj_close).

RUNS IN SANDBOX: reads the relevant modules as *text* (no import), so it does
not need pandas/numpy/lightgbm. Behavioural coverage lives in
test_build_target_price_basis.py (CI-only via importorskip).

After the v1_6 *shadow path* (Stage 3) these modules are versioned: the defaults
reproduce v1_5 byte-for-byte, and a v1_6 opt-in adds adj_close / fractional
support. The checks below pin BOTH the preserved v1_5 defaults and the new v1_6
support. Matching is on robust substrings (whitespace-normalised), never line
numbers.
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


# --- v1_5 default preservation (the shadow path must not change v1_5) ---------

def test_train_default_target_unit_is_basis_points() -> None:
    """v1_5 default preserved: the bps scale (10_000.0) and the basis_points
    default both remain, so a default train run reproduces v1_5."""
    src = _src(_TRAIN)
    assert "10_000.0" in src                          # bps scale retained
    assert 'target_unit: str = "basis_points"' in src


def test_build_target_default_price_basis_is_close() -> None:
    """build_target is versioned: default raw close (v1_5); adj_close opt-in."""
    assert 'price_basis: str = "close"' in _src(_TRAIN)


def test_loader_default_excludes_adj_close() -> None:
    """v1_5 default preserved: include_adj_close defaults False (panel + SQL
    unchanged); adj_close is opt-in for the v1_6 path."""
    assert "include_adj_close: bool = False" in _src(_LOADER)


def test_feature_engine_default_price_basis_is_close() -> None:
    """v1_5 default preserved: FeatureEngine defaults to the close basis."""
    assert 'price_basis: str = "close"' in _src(_ENGINE)


def test_thresholds_unchanged_fractional_scale() -> None:
    """thresholds.py is untouched: still compares expected_return to fractional
    values (0.05). v1_6 thresholds are re-derived in a LATER stage, not here."""
    src = _src(_THRESHOLDS)
    assert "expected_return > 0.05" in src
    assert "expected_return < -0.05" in src


def test_liquidity_uses_raw_close_times_volume() -> None:
    """CONTRACT (must stay true in v1_6): dollar-volume liquidity uses raw
    close * raw volume. The v1_6 path moves *returns* to adj_close but must NOT
    adjust the liquidity dollar-volume."""
    assert 'df["close"] * df["volume"]' in _src(_ENGINE)


# --- v1_6 contracts IMPLEMENTED in this branch (formerly strict xfail) --------

def test_v1_6_loader_can_select_adj_close() -> None:
    """Implemented: loader selects adj_close when include_adj_close=True."""
    assert "p.adj_close" in _src(_LOADER)


def test_v1_6_feature_engine_supports_adj_close_basis() -> None:
    """Implemented: FeatureEngine computes returns/trend/ATR from adj_close when
    price_basis='adj_close' (via self._price_col)."""
    src = _src(_ENGINE)
    assert "adj_close" in src
    assert "self._price_col" in src


def test_v1_6_build_target_supports_adj_close() -> None:
    """Implemented: build_target accepts price_basis='adj_close'."""
    assert "adj_close" in _src(_TRAIN)


# --- v1_6 contract NOT yet implemented (remains strict xfail) ------------------

@pytest.mark.xfail(
    strict=True,
    reason="v1_6 uses target_unit='fraction' for a fractional target, but the bps "
    "scale constant (10_000.0) stays in train.py for the v1_5 default until v1_5 is "
    "retired — so train.py still contains '10_000'. Flips only when the bps path is "
    "removed (post-v1_6 promotion).",
)
def test_v1_6_train_module_has_no_bps_constant() -> None:
    assert "10_000" not in _src(_TRAIN)
