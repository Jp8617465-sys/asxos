"""
Persist Model A signals to the `signals` table.

Schema (migration 0001):
    PK (model, model_version, symbol, as_of)
    confidence INTEGER, regime TEXT, shap_factors JSONB

Idempotent: ON CONFLICT DO UPDATE. Safe to re-run for the same as_of.
"""
from __future__ import annotations

import json
from datetime import date

import asyncpg
import numpy as np
import pandas as pd

from asxos.domain.signals.thresholds import classify_batch, confidence_from_prob_up


async def persist_signals(
    conn: asyncpg.Connection,
    *,
    model: str,
    model_version: str,
    as_of: date,
    preds: pd.DataFrame,
    shap_df: pd.DataFrame,
    regime: str,
) -> int:
    if preds.empty:
        return 0

    if set(preds.index) != set(shap_df.index):
        raise ValueError("preds and shap_df must share the same symbol index")

    # `preds` is sorted by rank from model_a._predict; shap_df keeps the
    # input order. Re-align shap_df to preds so per-row iteration matches.
    shap_df = shap_df.reindex(preds.index)

    prob_up = preds["prob_up"].to_numpy(dtype=float)
    expected_return = preds["expected_return"].to_numpy(dtype=float)
    labels = classify_batch(prob_up, expected_return, regime=regime)
    confidence = confidence_from_prob_up(prob_up)

    rows: list[tuple] = []
    for i, symbol in enumerate(preds.index):
        shap_row = {
            k: (None if not np.isfinite(v) else float(v))
            for k, v in shap_df.loc[symbol].items()
        }
        rows.append(
            (
                model,
                model_version,
                str(symbol),
                as_of,
                float(prob_up[i]),
                float(expected_return[i]),
                str(labels[i]),
                int(confidence[i]),
                regime,
                json.dumps(shap_row),
            )
        )

    await conn.executemany(
        """
        INSERT INTO signals (
            model, model_version, symbol, as_of,
            prob_up, expected_return, signal_label,
            confidence, regime, shap_factors
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
        ON CONFLICT (model, model_version, symbol, as_of) DO UPDATE SET
            prob_up         = EXCLUDED.prob_up,
            expected_return = EXCLUDED.expected_return,
            signal_label    = EXCLUDED.signal_label,
            confidence      = EXCLUDED.confidence,
            regime          = EXCLUDED.regime,
            shap_factors    = EXCLUDED.shap_factors
        """,
        rows,
    )
    return len(rows)
