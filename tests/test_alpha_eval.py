"""
Tests for the alpha-evaluation engine (M14 research) — pure, synthetic data.

Focus on the discipline features that stop us fooling ourselves:
  * effective_sample_size collapses under clustered dates (overlapping windows)
  * effective_t < naive_t when dates are clustered
  * decile_spread surfaces the 'top decile has no edge' pathology
  * liquidity_split detects an edge concentrated in illiquid names
  * calibration detects a miscalibrated probability
  * a perfectly-ranked panel yields IC == 1
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from asxos.domain.research.alpha_eval import (
    calibration,
    decile_spread,
    effective_sample_size,
    evaluate,
    ic_summary,
    liquidity_split,
    spearman_ic_per_date,
)

# ---------------------------------------------------------------------------
# Effective sample size
# ---------------------------------------------------------------------------


def test_effective_n_collapses_under_clustering():
    # 10 consecutive calendar days, 5-day horizon -> windows overlap -> ~2 episodes
    dates = pd.date_range("2026-03-13", periods=10, freq="D").date.tolist()
    assert effective_sample_size(dates, 5) <= 3
    # the same 10 dates spaced a month apart -> all independent
    spaced = pd.date_range("2026-01-01", periods=10, freq="30D").date.tolist()
    assert effective_sample_size(spaced, 5) == 10


def test_effective_n_empty_and_singleton():
    assert effective_sample_size([], 5) == 0
    assert effective_sample_size(["2026-01-01"], 21) == 1


# ---------------------------------------------------------------------------
# IC
# ---------------------------------------------------------------------------


def _panel(dates, n_per_date, score_fn, ret_fn, *, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in dates:
        scores = rng.permutation(n_per_date) / n_per_date
        for s in scores:
            rows.append({"signal_date": d, "symbol": f"S{int(s*n_per_date)}",
                         "prob_up": score_fn(s), "ret_5": ret_fn(s, rng)})
    return pd.DataFrame(rows)


def test_perfect_rank_ic_is_one():
    dates = ["2026-01-01", "2026-02-01"]
    df = _panel(dates, 50, lambda s: s, lambda s, rng: s)  # ret == score
    ic = spearman_ic_per_date(df, "prob_up", "ret_5")
    assert len(ic) == 2
    assert ic.min() > 0.999


def test_effective_t_below_naive_t_when_clustered():
    # 6 clustered dates, all with the same modest IC
    dates = pd.date_range("2026-03-13", periods=6, freq="D").date.tolist()
    df = _panel(dates, 60, lambda s: s, lambda s, rng: s * 0.1 + rng.normal(0, 0.05))
    ic = spearman_ic_per_date(df, "prob_up", "ret_5")
    eff = effective_sample_size(list(ic.index), 5)
    s = ic_summary(ic, 5, "prob_up", eff)
    assert s.n_dates == 6
    assert s.effective_n <= 3
    # effective t must be smaller in magnitude than naive t (fewer independent obs)
    assert abs(s.effective_t) < abs(s.naive_t)


# ---------------------------------------------------------------------------
# Decile spread — top-decile-no-edge detection
# ---------------------------------------------------------------------------


def test_decile_monotonic():
    dates = ["2026-01-01", "2026-02-01"]
    df = _panel(dates, 100, lambda s: s, lambda s, rng: s)  # ret rises with score
    d = decile_spread(df, "prob_up", "ret_5", 5)
    assert d.spread_pct > 0
    assert d.top_minus_upper_mid_pct > 0      # top is the best
    assert d.monotonic_frac > 0.8


def test_decile_top_has_no_edge():
    # ret rises with score up to 0.8, then DECLINES for the top names
    dates = ["2026-01-01", "2026-02-01"]
    df = _panel(dates, 100, lambda s: s,
                lambda s, rng: (s if s <= 0.8 else 1.6 - s))
    d = decile_spread(df, "prob_up", "ret_5", 5)
    assert d.top_minus_upper_mid_pct < 0      # top decile underperforms upper-mid


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def test_calibration_detects_miscalibration():
    # predicted 0.8 everywhere, but only 30% actually go up -> miscalibrated
    rows = []
    for i in range(100):
        rows.append({"prob_up": 0.8, "ret_5": 0.01 if i < 30 else -0.01})
    df = pd.DataFrame(rows)
    c = calibration(df, "prob_up", "ret_5")
    assert c.buckets[-1]["realised_up_rate"] == 0.3
    assert c.miscalibration > 0.4            # |0.8 - 0.3|
    assert 0 <= c.brier <= 1


# ---------------------------------------------------------------------------
# Liquidity split
# ---------------------------------------------------------------------------


def test_liquidity_split_detects_illiquid_concentration():
    rng = np.random.default_rng(1)
    rows = []
    for d in ["2026-01-01", "2026-02-01"]:
        for i in range(40):
            s = i / 40
            # illiquid: ret tracks score (edge here). tradable: ret is noise.
            rows.append({"signal_date": d, "symbol": f"I{i}", "prob_up": s,
                         "ret_5": s, "price": 0.01, "dollar_volume": 500.0})
            rows.append({"signal_date": d, "symbol": f"T{i}", "prob_up": s,
                         "ret_5": rng.normal(0, 0.1), "price": 5.0, "dollar_volume": 5_000_000.0})
    df = pd.DataFrame(rows)
    q = liquidity_split(df, "prob_up", "ret_5", 5)
    assert q.illiquid_ic > 0.9
    assert q.illiquid_ic > q.tradable_ic + 0.5


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def test_evaluate_warns_on_thin_data():
    dates = pd.date_range("2026-03-13", periods=5, freq="D").date.tolist()
    df = _panel(dates, 60, lambda s: s, lambda s, rng: s * 0.1)
    df["composite"] = df["prob_up"]
    df["expected_return"] = df["prob_up"]
    rep = evaluate(df, horizons=(5,))
    assert rep.n_dates == 5
    # must warn about thin / overlapping data
    assert any("independent" in w or "indicative" in w for w in rep.warnings)
    assert any(s.score == "prob_up" and s.horizon == 5 for s in rep.ic)
