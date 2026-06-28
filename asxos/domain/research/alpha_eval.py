"""
Alpha-evaluation engine — pure analytics (M14 research).

Productionizes the Phase-1 signal verification (docs/research/alpha-signal-
verification.md) into a repeatable, testable engine. Given a panel of historical
signals joined to forward returns, it computes rank-IC by horizon, IC decay,
decile spreads, score-variant comparison (prob_up vs composite vs expected_return),
liquidity-bucket IC, and prob_up calibration.

Design contract (skeptical-by-construction)
-------------------------------------------
* No I/O. Pure functions over a pandas panel; the DB loader lives in
  ``alpha_loader.py``. This keeps the statistics unit-testable on synthetic data.
* EFFECTIVE SAMPLE SIZE GUARD. Cross-sectional IC t-stats assume independent
  dates. When signal dates are spaced closer than the return horizon, their
  forward windows overlap and the naive t-stat is inflated. Every IC summary
  therefore reports BOTH the naive t (n dates) and the effective t (number of
  non-overlapping dates at that horizon). Callers must quote the effective t.
* No alpha claims. This module measures; it does not bless. A positive IC here
  is not "alpha" until it survives costs, liquidity, and out-of-sample replication
  on a sufficient number of INDEPENDENT dates.

Research module: pandas/numpy are appropriate here (large-panel vectorised
stats), unlike the Decimal-only portfolio domain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ICSummary:
    horizon: int
    score: str
    n_dates: int
    effective_n: int          # non-overlapping dates at this horizon
    mean_ic: float
    std_ic: float
    naive_t: float            # mean/std*sqrt(n_dates)  — OPTIMISTIC
    effective_t: float        # mean/std*sqrt(effective_n) — quote THIS
    significant: bool         # |effective_t| >= 2.0


@dataclass(frozen=True)
class DecileResult:
    horizon: int
    score: str
    bucket_means_pct: list[float]   # length n_buckets, low->high score
    top_pct: float
    bottom_pct: float
    spread_pct: float               # top - bottom
    monotonic_frac: float           # fraction of adjacent steps that increase
    top_minus_upper_mid_pct: float  # D_top - D_(top-2): negative => top has no edge


@dataclass(frozen=True)
class CalibrationResult:
    n: int
    brier: float
    buckets: list[dict[str, Any]]   # [{pred, realised_up_rate, n}]
    miscalibration: float  # mean |pred - realised| over buckets (weighted)


@dataclass(frozen=True)
class LiquiditySplit:
    horizon: int
    score: str
    tradable_ic: float
    tradable_effective_t: float
    tradable_avg_names: float
    illiquid_ic: float
    illiquid_effective_t: float
    illiquid_avg_names: float


@dataclass(frozen=True)
class AlphaReport:
    horizons: list[int]
    n_dates: int
    date_min: str
    date_max: str
    regimes: dict[str, int]
    ic: list[ICSummary]
    deciles: list[DecileResult]
    calibration: CalibrationResult | None
    liquidity: list[LiquiditySplit]
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core statistics (pure)
# ---------------------------------------------------------------------------

_TRADING_DAYS_PER_CAL_DAY = 1.40  # ~252 trading / 365 calendar


def effective_sample_size(dates: list[Any], horizon_trading_days: int) -> int:
    """Greedily count dates spaced at least ``horizon`` trading days apart.

    Forward-return windows of dates closer than the horizon overlap, so they are
    not independent. We approximate the trading-day gap from the calendar gap
    (``cal_gap / 1.40``). Returns the count of non-overlapping observations
    (always >= 1 when dates is non-empty).
    """
    if not dates:
        return 0
    ds = sorted(pd.to_datetime(d) for d in set(dates))
    min_cal_gap = horizon_trading_days * _TRADING_DAYS_PER_CAL_DAY
    kept = 1
    last = ds[0]
    for d in ds[1:]:
        if (d - last).days >= min_cal_gap:
            kept += 1
            last = d
    return kept


def spearman_ic_per_date(
    df: pd.DataFrame, score_col: str, ret_col: str, date_col: str = "signal_date"
) -> pd.Series:
    """Per-date Spearman rank-IC between score and forward return.

    Rows with NaN score or return are dropped per date before ranking, so a
    missing forward price never contaminates the rank. Dates with < 5 valid rows
    are skipped (an IC on a handful of names is meaningless).
    """
    out: dict[object, float] = {}
    for d, g in df[[date_col, score_col, ret_col]].dropna().groupby(date_col):
        if len(g) < 5:
            continue
        # Spearman == Pearson on ranks. Computing it this way avoids a scipy
        # dependency (pandas' method="spearman" imports scipy.stats).
        out[d] = g[score_col].rank().corr(g[ret_col].rank())
    return pd.Series(out, dtype=float).dropna()


def ic_summary(
    per_date_ic: pd.Series, horizon: int, score: str, effective_n: int
) -> ICSummary:
    n = int(per_date_ic.shape[0])
    mean = float(per_date_ic.mean()) if n else 0.0
    std = float(per_date_ic.std(ddof=1)) if n > 1 else float("nan")
    naive_t = mean / std * np.sqrt(n) if (n > 1 and std > 0) else float("nan")
    eff = max(1, min(effective_n, n))
    eff_t = mean / std * np.sqrt(eff) if (n > 1 and std > 0) else float("nan")
    sig = bool(abs(eff_t) >= 2.0) if eff_t == eff_t else False  # NaN-safe
    return ICSummary(
        horizon=horizon, score=score, n_dates=n, effective_n=eff,
        mean_ic=round(mean, 4), std_ic=round(std, 4) if std == std else float("nan"),
        naive_t=round(naive_t, 2) if naive_t == naive_t else float("nan"),
        effective_t=round(eff_t, 2) if eff_t == eff_t else float("nan"),
        significant=sig,
    )


def decile_spread(
    df: pd.DataFrame, score_col: str, ret_col: str, horizon: int,
    date_col: str = "signal_date", n_buckets: int = 10,
) -> DecileResult:
    """Per-date score buckets, mean forward return per bucket averaged across dates.

    Per-date bucketing avoids pooling a miscalibrated score across regimes. The
    ``top_minus_upper_mid`` field surfaces the 'top decile has no edge' pathology
    found in Phase 1 (a negative value means the highest bucket underperforms the
    bucket two below it).
    """
    valid = df[[date_col, score_col, ret_col]].dropna()
    per_date_bucket: list[pd.Series] = []
    for _, g in valid.groupby(date_col):
        if len(g) < n_buckets * 2:
            continue
        try:
            b = pd.qcut(g[score_col].rank(method="first"), n_buckets, labels=False)
        except ValueError:
            continue
        per_date_bucket.append(g.assign(_b=b).groupby("_b")[ret_col].mean())
    if not per_date_bucket:
        return DecileResult(horizon, score_col, [], float("nan"), float("nan"),
                            float("nan"), float("nan"), float("nan"))
    means = pd.concat(per_date_bucket, axis=1).mean(axis=1) * 100.0
    vals = [round(float(x), 3) for x in means.reindex(range(n_buckets)).values]
    top, bottom = vals[-1], vals[0]
    steps = np.diff([v for v in vals if v == v])
    monotonic = float((steps > 0).mean()) if len(steps) else float("nan")
    upper_mid = vals[-3] if len(vals) >= 3 else float("nan")
    return DecileResult(
        horizon=horizon, score=score_col, bucket_means_pct=vals,
        top_pct=top, bottom_pct=bottom, spread_pct=round(top - bottom, 3),
        monotonic_frac=round(monotonic, 3) if monotonic == monotonic else float("nan"),
        top_minus_upper_mid_pct=round(top - upper_mid, 3) if upper_mid == upper_mid else float("nan"),
    )


def calibration(
    df: pd.DataFrame, prob_col: str, ret_col: str, n_buckets: int = 10
) -> CalibrationResult:
    """prob bucket -> realised up-rate, plus Brier score. Measures whether
    prob_up is a calibrated probability or merely a rank."""
    valid = df[[prob_col, ret_col]].dropna().copy()
    if valid.empty:
        return CalibrationResult(0, float("nan"), [], float("nan"))
    valid["_up"] = (valid[ret_col] > 0).astype(float)
    valid["_bk"] = np.minimum((valid[prob_col] * n_buckets).astype(int), n_buckets - 1)
    rows: list[dict[str, Any]] = []
    miscal_num = 0.0
    for _, g in valid.groupby("_bk"):
        pred = float(g[prob_col].mean())
        realised = float(g["_up"].mean())
        rows.append({"pred": round(pred, 3), "realised_up_rate": round(realised, 3), "n": len(g)})
        miscal_num += abs(pred - realised) * len(g)
    brier = float(((valid[prob_col] - valid["_up"]) ** 2).mean())
    return CalibrationResult(
        n=len(valid), brier=round(brier, 4),
        buckets=sorted(rows, key=lambda r: r["pred"]),
        miscalibration=round(miscal_num / len(valid), 4),
    )


def liquidity_split(
    df: pd.DataFrame, score_col: str, ret_col: str, horizon: int,
    dollar_vol_col: str = "dollar_volume", price_col: str = "price",
    min_price: float = 0.20, min_dollar_vol: float = 100_000.0,
    date_col: str = "signal_date",
) -> LiquiditySplit:
    """IC within the tradable subset vs the illiquid remainder. Surfaces the
    Phase-1 finding that the edge concentrates in untradable names."""
    d = df.copy()
    tradable_mask = (d[price_col] >= min_price) & (d[dollar_vol_col] >= min_dollar_vol)
    out = {}
    for name, sub in (("tradable", d[tradable_mask]), ("illiquid", d[~tradable_mask])):
        ic = spearman_ic_per_date(sub, score_col, ret_col, date_col)
        eff = effective_sample_size(list(ic.index), horizon)
        s = ic_summary(ic, horizon, score_col, eff)
        avg_names = float(
            sub.dropna(subset=[score_col, ret_col]).groupby(date_col).size().mean()
        ) if not sub.empty else 0.0
        out[name] = (s, avg_names)
    return LiquiditySplit(
        horizon=horizon, score=score_col,
        tradable_ic=out["tradable"][0].mean_ic, tradable_effective_t=out["tradable"][0].effective_t,
        tradable_avg_names=round(out["tradable"][1], 0),
        illiquid_ic=out["illiquid"][0].mean_ic, illiquid_effective_t=out["illiquid"][0].effective_t,
        illiquid_avg_names=round(out["illiquid"][1], 0),
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def evaluate(
    df: pd.DataFrame,
    *,
    horizons: tuple[int, ...] = (5, 10, 21, 63),
    score_cols: tuple[str, ...] = ("prob_up", "composite", "expected_return"),
    prob_col: str = "prob_up",
    date_col: str = "signal_date",
    regime_col: str = "regime",
) -> AlphaReport:
    """Full evaluation over a panel.

    Expected columns: ``signal_date``, ``symbol``, the score columns, ``regime``
    (optional), ``ret_{h}`` for each horizon, and (for liquidity) ``price`` +
    ``dollar_volume``. Forward returns are total-return fractions.
    """
    warnings: list[str] = []
    dates = sorted(df[date_col].dropna().unique())
    n_dates = len(dates)

    regimes: dict[str, int] = {}
    if regime_col in df.columns:
        regimes = {str(k): int(v) for k, v in df.groupby(regime_col)[date_col].nunique().items()}

    ic: list[ICSummary] = []
    deciles: list[DecileResult] = []
    liquidity: list[LiquiditySplit] = []
    for h in horizons:
        ret_col = f"ret_{h}"
        if ret_col not in df.columns:
            warnings.append(f"horizon {h}: column {ret_col} absent — skipped")
            continue
        usable_dates = sorted(df.loc[df[ret_col].notna(), date_col].unique())
        eff = effective_sample_size(usable_dates, h)
        if eff < 5:
            warnings.append(
                f"horizon {h}: only {eff} independent (non-overlapping) date(s) — "
                f"IC/t are NOT decision-grade; backfill more signal dates."
            )
        for sc in score_cols:
            if sc not in df.columns:
                continue
            per_date = spearman_ic_per_date(df, sc, ret_col, date_col)
            ic.append(ic_summary(per_date, h, sc, effective_sample_size(list(per_date.index), h)))
        deciles.append(decile_spread(df, prob_col, ret_col, h, date_col))
        if {"price", "dollar_volume"}.issubset(df.columns):
            liquidity.append(liquidity_split(df, prob_col, ret_col, h, date_col=date_col))

    calib = None
    if "ret_5" in df.columns and prob_col in df.columns:
        calib = calibration(df, prob_col, "ret_5")

    if n_dates < 30:
        warnings.append(
            f"Only {n_dates} signal date(s) total. Treat all results as indicative; "
            f"statistical significance requires backfilling historical signals."
        )

    return AlphaReport(
        horizons=list(horizons), n_dates=n_dates,
        date_min=str(dates[0]) if dates else "", date_max=str(dates[-1]) if dates else "",
        regimes=regimes, ic=ic, deciles=deciles, calibration=calib,
        liquidity=liquidity, warnings=warnings,
    )
