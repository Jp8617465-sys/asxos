"""
Load prices + fundamentals from Postgres and compute Model A features
for a single target date. Reused by `asx predict` (M6) and the daily
signal generation job (M7).

Lookback default 450 calendar days — enough to fully populate the
longest rolling window (252-day adv_zscore / pe_ratio_zscore) with
margin for holidays and weekends.

Fundamentals are attached as a time-varying as-of join: for each
(symbol, dt) row in the price panel we attach the most-recent
fundamentals snapshot with as_of <= dt - 45 days.  Rolling z-score
features (pe_ratio_zscore, pb_ratio_zscore) require variation over
the lookback window — the M4 fundamentals refresh writes a row per
symbol per day, giving the daily granularity needed.
"""
from __future__ import annotations

from datetime import date, timedelta

import asyncpg
import numpy as np
import pandas as pd

FUNDAMENTAL_LAG_DAYS = 45
DEFAULT_LOOKBACK_DAYS = 450

# Fundamental features (and their derived z-scores) are zero-filled when
# missing — ml-conventions.md treats absent fundamentals as a neutral input
# rather than a disqualifier. Technical features (momentum, vol, trend) still
# require a fully-populated lookback window.
FUNDAMENTAL_FEATURE_COLS: tuple[str, ...] = (
    "pe_ratio",
    "pb_ratio",
    "eps",
    "market_cap",
    "pe_ratio_zscore",
    "pb_ratio_zscore",
)


async def load_panel(
    conn: asyncpg.Connection,
    target_date: date,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """Raw symbol-by-dt panel with prices, fundamentals (45-day lag), and caps.
    Used by the regime detector (needs full history) and the feature loader."""
    start_date = target_date - timedelta(days=lookback_days)
    fundamentals_cutoff = target_date - timedelta(days=FUNDAMENTAL_LAG_DAYS)
    return await _load_panel(conn, start_date, target_date, fundamentals_cutoff)


def features_from_panel(panel: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """Run the FeatureEngine on a pre-loaded panel and return the target-date
    snapshot, indexed by symbol, with zero-filled fundamentals."""
    from asxos.domain.signals.feature_engine import (
        MODEL_A_FEATURES,
        FeatureEngine,
    )

    if panel.empty:
        return panel

    engine = FeatureEngine()
    enriched = engine.compute_all_features(panel)

    target_ts = pd.Timestamp(target_date)
    snapshot = enriched.loc[enriched["dt"] == target_ts].copy()
    if snapshot.empty:
        return snapshot

    snapshot = snapshot.set_index("symbol")

    # ml-conventions: zero-fill fundamental features and their z-scores. A
    # sparse fundamentals table (e.g. early production days) would otherwise
    # drop every row via the technical-feature dropna below.
    for col in FUNDAMENTAL_FEATURE_COLS:
        if col in snapshot.columns:
            snapshot[col] = snapshot[col].fillna(0.0)

    technical_features = [f for f in MODEL_A_FEATURES if f not in FUNDAMENTAL_FEATURE_COLS]
    snapshot = snapshot.dropna(subset=technical_features)
    return snapshot


async def load_features_for_date(
    conn: asyncpg.Connection,
    target_date: date,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    Returns the features DataFrame restricted to `target_date`, indexed by
    symbol. Rows where any Model A feature is non-finite are dropped — the
    caller decides whether an empty result is acceptable.
    """
    panel = await load_panel(conn, target_date, lookback_days=lookback_days)
    return features_from_panel(panel, target_date)


async def _load_panel(
    conn: asyncpg.Connection,
    start_date: date,
    target_date: date,
    fundamentals_cutoff: date,
) -> pd.DataFrame:
    price_rows = await conn.fetch(
        """
        SELECT p.symbol, p.dt, p.open, p.high, p.low, p.close, p.volume
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        WHERE p.dt BETWEEN $1 AND $2
          AND u.is_active = TRUE
        ORDER BY p.symbol, p.dt
        """,
        start_date,
        target_date,
    )
    if not price_rows:
        return pd.DataFrame()

    prices = pd.DataFrame(price_rows, columns=price_rows[0].keys())
    prices["dt"] = pd.to_datetime(prices["dt"]).astype("datetime64[us]")
    for col in ("open", "high", "low", "close", "volume"):
        prices[col] = pd.to_numeric(prices[col], errors="coerce")
    # merge_asof requires the left frame sorted globally by `on` (dt).
    prices = prices.sort_values(["dt", "symbol"]).reset_index(drop=True)

    fund_rows = await conn.fetch(
        """
        SELECT symbol, as_of, pe_ratio, pb_ratio, eps
        FROM fundamentals
        WHERE as_of <= $1
        ORDER BY symbol, as_of
        """,
        fundamentals_cutoff,
    )
    if fund_rows:
        funds = pd.DataFrame(fund_rows, columns=fund_rows[0].keys())
        funds["as_of"] = pd.to_datetime(funds["as_of"]).astype("datetime64[us]")
        for col in ("pe_ratio", "pb_ratio", "eps"):
            funds[col] = pd.to_numeric(funds[col], errors="coerce")
        funds = funds.sort_values(["symbol", "as_of"]).reset_index(drop=True)

        # Apply the 45-day disclosure lag by shifting the as_of forward, then
        # do a backward as-of join: each (symbol, dt) gets the most recent
        # fundamentals snapshot whose effective date <= dt.
        funds["effective_dt"] = funds["as_of"] + pd.Timedelta(days=FUNDAMENTAL_LAG_DAYS)
        funds = funds.drop(columns=["as_of"]).sort_values(["effective_dt", "symbol"]).reset_index(
            drop=True
        )

        panel = pd.merge_asof(
            prices,
            funds,
            by="symbol",
            left_on="dt",
            right_on="effective_dt",
            direction="backward",
        )
        panel = panel.drop(columns=["effective_dt"])
        # Restore per-symbol chronological order for the feature engine.
        panel = panel.sort_values(["symbol", "dt"]).reset_index(drop=True)
    else:
        panel = prices.copy()
        for col in ("pe_ratio", "pb_ratio", "eps"):
            panel[col] = np.nan

    cap_rows = await conn.fetch(
        "SELECT symbol, market_cap FROM universe WHERE is_active = TRUE"
    )
    if cap_rows:
        caps = pd.DataFrame(cap_rows, columns=cap_rows[0].keys())
        caps["market_cap"] = pd.to_numeric(caps["market_cap"], errors="coerce")
        panel = panel.merge(caps, on="symbol", how="left")
    else:
        panel["market_cap"] = np.nan

    # Force numeric dtypes so downstream rolling/z-score ops work even when
    # merge_asof / left-merge leaves an all-NA column as object dtype.
    for col in ("pe_ratio", "pb_ratio", "eps", "market_cap"):
        panel[col] = pd.to_numeric(panel[col], errors="coerce")

    return panel
