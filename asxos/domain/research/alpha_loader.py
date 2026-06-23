"""
DB loader for the alpha-evaluation engine (M14 research).

Builds the historical signal panel from ``signal_outcomes`` (the recorded
prob_up / expected_return / label / regime per past signal) joined forward to
``prices`` for total-return forward returns at multiple horizons. Forward
returns use a per-symbol trading-day index on ``adj_close`` (dividend/split
adjusted) — the same reconstruction the Phase-1 verification used.

Returns a plain pandas DataFrame; all statistics live in ``alpha_eval.py`` so
they stay testable without a DB.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import asyncpg

# Forward-return horizons (trading days). The SQL below has a LEFT JOIN per
# horizon; keep this in sync with _PANEL_SQL if you add one.
HORIZONS = (5, 10, 21, 63)

_PANEL_SQL = """
WITH px AS (
    SELECT symbol, dt, close, adj_close, volume,
           row_number() OVER (PARTITION BY symbol ORDER BY dt) AS rn
    FROM prices WHERE adj_close IS NOT NULL
),
base AS (
    SELECT so.symbol, so.signal_date,
           so.ml_prob            AS prob_up,
           so.ml_expected_return AS expected_return,
           so.signal_label, so.regime,
           pr.rn AS rn0, pr.adj_close AS a0,
           pr.close AS price, (pr.close * pr.volume) AS dollar_volume
    FROM signal_outcomes so
    JOIN px pr ON pr.symbol = so.symbol AND pr.dt = so.signal_date
    WHERE so.ml_prob IS NOT NULL
)
SELECT b.symbol, b.signal_date, b.prob_up, b.expected_return,
       (0.6 * b.prob_up + 0.4 * b.expected_return) AS composite,
       b.signal_label, b.regime, b.price, b.dollar_volume,
       f5.adj_close  / b.a0 - 1 AS ret_5,
       f10.adj_close / b.a0 - 1 AS ret_10,
       f21.adj_close / b.a0 - 1 AS ret_21,
       f63.adj_close / b.a0 - 1 AS ret_63
FROM base b
LEFT JOIN px f5  ON f5.symbol  = b.symbol AND f5.rn  = b.rn0 + 5
LEFT JOIN px f10 ON f10.symbol = b.symbol AND f10.rn = b.rn0 + 10
LEFT JOIN px f21 ON f21.symbol = b.symbol AND f21.rn = b.rn0 + 21
LEFT JOIN px f63 ON f63.symbol = b.symbol AND f63.rn = b.rn0 + 63
"""

_FLOAT_COLS = [
    "prob_up", "expected_return", "composite", "price", "dollar_volume",
    "ret_5", "ret_10", "ret_21", "ret_63",
]


async def load_panel(conn: asyncpg.Connection) -> pd.DataFrame:
    """Load the full historical signal panel as a DataFrame.

    Columns: symbol, signal_date, prob_up, expected_return, composite,
    signal_label, regime, price, dollar_volume, ret_5, ret_10, ret_21, ret_63.
    NUMERIC columns are coerced to float (research engine is numpy/pandas-based).
    """
    rows = await conn.fetch(_PANEL_SQL)
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df
    df["signal_date"] = pd.to_datetime(df["signal_date"]).dt.date
    for c in _FLOAT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df
