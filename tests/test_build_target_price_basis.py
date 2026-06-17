"""
model_a v1_6 — behavioural price-basis contracts for build_target + FeatureEngine.

CI-ONLY: these operate on pandas DataFrames, so the module imports pandas at the
top. In environments without pandas/numpy (the lint-only sandbox) it is a
collection gap, consistent with the other ML test modules (test_feature_engine,
test_signals_loader, test_train_walk_forward); it runs on the ML-enabled CI
image (the targeted-ml-tests workflow). It carries the *behavioural* proof of
the v1_6 shadow path:
  * v1_5 default behaviour is preserved (default == explicit "close").
  * v1_6 (price_basis="adj_close") uses the adjusted series for returns/target.
  * liquidity dollar-volume stays raw close * volume even under the adj basis.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from asxos.domain.models.train import build_target
from asxos.domain.signals.feature_engine import FeatureEngine


def _panel(closes: list[float], adj_closes: list[float] | None = None) -> pd.DataFrame:
    """Single-symbol target panel; adj_close optional."""
    rows = []
    for i, c in enumerate(closes):
        row = {"symbol": "TEST.AU", "dt": date(2026, 1, 1) + timedelta(days=i), "close": c}
        if adj_closes is not None:
            row["adj_close"] = adj_closes[i]
        rows.append(row)
    return pd.DataFrame(rows)


def _feature_panel(closes: list[float], adj_closes: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    n = len(closes)
    vols = volumes if volumes is not None else [1_000_000.0] * n
    return pd.DataFrame(
        {
            "symbol": ["T.AU"] * n,
            "dt": [date(2026, 1, 1) + timedelta(days=i) for i in range(n)],
            "close": closes,
            "adj_close": adj_closes,
            "volume": vols,
        }
    )


# --- build_target -------------------------------------------------------------

def test_v1_5_build_target_forward_return_is_fractional() -> None:
    """CHARACTERIZATION: a +1% move over 5 days yields forward_return ~= 0.01
    (fraction). The bps scaling is applied later, in train_model_a."""
    panel = _panel([100, 100, 100, 100, 100, 101, 102])
    out = build_target(panel).sort_values("dt").reset_index(drop=True)
    assert out.loc[0, "forward_return"] == pytest.approx(0.01, abs=1e-9)
    assert out.loc[1, "forward_return"] == pytest.approx(0.02, abs=1e-9)
    assert out.loc[0, "y_class"] == 1


def test_build_target_default_matches_explicit_close() -> None:
    """v1_5 PRESERVED: the default build_target equals price_basis='close'."""
    panel = _panel([100, 100, 100, 100, 100, 101, 102])
    default = build_target(panel).sort_values("dt").reset_index(drop=True)
    close = build_target(panel, price_basis="close").sort_values("dt").reset_index(drop=True)
    assert default["forward_return"].equals(close["forward_return"])


def test_v1_6_build_target_uses_adj_close() -> None:
    """IMPLEMENTED: with price_basis='adj_close', a 10x raw-close jump (smooth
    adj_close) yields forward_return ~= 0 — corporate-action contamination gone."""
    closes = [10, 10, 10, 10, 10, 100, 100]        # spurious 10x jump
    adj = [100, 100, 100, 100, 100, 100, 100]      # smooth adjusted series
    out = build_target(_panel(closes, adj), price_basis="adj_close").sort_values("dt").reset_index(drop=True)
    assert out.loc[0, "forward_return"] == pytest.approx(0.0, abs=1e-6)
    # And the raw-close basis would still be contaminated (~+9.0):
    raw = build_target(_panel(closes, adj), price_basis="close").sort_values("dt").reset_index(drop=True)
    assert raw.loc[0, "forward_return"] == pytest.approx(9.0, abs=1e-6)


# --- FeatureEngine ------------------------------------------------------------

def test_feature_engine_default_equals_close_basis() -> None:
    """v1_5 PRESERVED: FeatureEngine() == FeatureEngine(price_basis='close')."""
    panel = _feature_panel([100, 101, 102, 103, 104], [100, 101, 102, 103, 104])
    a = FeatureEngine().compute_all_features(panel.copy())
    b = FeatureEngine(price_basis="close").compute_all_features(panel.copy())
    assert a["ret_1d"].equals(b["ret_1d"])
    assert a["trend_200"].equals(b["trend_200"])


def test_feature_engine_adj_basis_returns_use_adj_close() -> None:
    """IMPLEMENTED: under adj basis, ret_1d follows adj_close, not raw close."""
    panel = _feature_panel([10, 10, 100, 100], [100, 100, 100, 100])
    eng = FeatureEngine(price_basis="adj_close").compute_all_features(panel.copy())
    # adj_close 100->100 at t=2 -> 0.0, not the raw close 10->100 (+900%).
    assert eng["ret_1d"].iloc[2] == pytest.approx(0.0, abs=1e-9)


def test_feature_engine_liquidity_stays_raw_close_under_adj_basis() -> None:
    """CONTRACT: dollar-volume liquidity uses RAW close * volume even when the
    return basis is adj_close (real tradeable dollars)."""
    n = 12
    panel = _feature_panel([10.0] * n, [100.0] * n, [5.0] * n)  # raw close 10, adj 100
    eng = FeatureEngine(price_basis="adj_close").compute_all_features(panel.copy())
    # dollar_vol = raw close(10) * vol(5) = 50 (NOT adj 100*5 = 500).
    assert eng["adv_20_median"].iloc[-1] == pytest.approx(50.0, abs=1e-9)
