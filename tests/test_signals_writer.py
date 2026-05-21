"""
Tests for asxos.domain.signals.writer.persist_signals.

Captures the SQL executemany payload so we can assert UPSERT semantics,
label classification, confidence formula, and JSON-serialisation of SHAP
without a real Postgres. The async conn is a MagicMock with an AsyncMock
on executemany.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from asxos.domain.signals.writer import persist_signals


def _conn() -> MagicMock:
    c = MagicMock()
    c.executemany = AsyncMock()
    return c


def _preds_shap() -> tuple[pd.DataFrame, pd.DataFrame]:
    idx = pd.Index(["AAA.AU", "BBB.AU", "CCC.AU"], name="symbol")
    preds = pd.DataFrame(
        {"prob_up": [0.80, 0.50, 0.30], "expected_return": [0.10, 0.0, -0.10], "rank": [1, 2, 3]},
        index=idx,
    )
    shap = pd.DataFrame(
        {"mom_6": [0.5, -0.1, 0.2], "pe_ratio": [0.1, 0.0, -0.2], "bias": [0.05, 0.05, 0.05]},
        index=idx,
    )
    return preds, shap


def test_persist_signals_writes_rows_with_expected_payload() -> None:
    preds, shap = _preds_shap()
    conn = _conn()
    n = asyncio.run(
        persist_signals(
            conn,
            model="model_a",
            model_version="v1_5",
            as_of=date(2026, 5, 20),
            preds=preds,
            shap_df=shap,
            regime="neutral",
        )
    )

    assert n == 3
    conn.executemany.assert_awaited_once()
    sql, rows = conn.executemany.await_args.args
    assert "INSERT INTO signals" in sql
    assert "ON CONFLICT (model, model_version, symbol, as_of) DO UPDATE" in sql

    # Row layout: model, version, symbol, as_of, prob_up, exp_ret,
    # label, confidence, regime, shap_json
    by_symbol = {r[2]: r for r in rows}

    assert by_symbol["AAA.AU"][6] == "STRONG_BUY"
    assert by_symbol["BBB.AU"][6] == "HOLD"
    assert by_symbol["CCC.AU"][6] == "STRONG_SELL"

    # Confidence: |p - 0.5| * 200 → 60 / 0 / 40
    assert by_symbol["AAA.AU"][7] == 60
    assert by_symbol["BBB.AU"][7] == 0
    assert by_symbol["CCC.AU"][7] == 40

    # Regime echoed
    assert all(r[8] == "neutral" for r in rows)

    # JSON-serialised shap with mom_6 / pe_ratio / bias preserved
    shap_aaa = json.loads(by_symbol["AAA.AU"][9])
    assert shap_aaa == {"mom_6": 0.5, "pe_ratio": 0.1, "bias": 0.05}


def test_persist_signals_uses_regime_thresholds() -> None:
    """A row that's STRONG_BUY in neutral should drop in bear if it doesn't clear bear cutoffs."""
    idx = pd.Index(["X.AU"], name="symbol")
    preds = pd.DataFrame({"prob_up": [0.66], "expected_return": [0.06], "rank": [1]}, index=idx)
    shap = pd.DataFrame({"mom_6": [0.1], "bias": [0.0]}, index=idx)
    conn = _conn()

    asyncio.run(
        persist_signals(
            conn,
            model="model_a",
            model_version="v1_5",
            as_of=date(2026, 5, 20),
            preds=preds,
            shap_df=shap,
            regime="bear",
        )
    )

    _, rows = conn.executemany.await_args.args
    assert rows[0][6] != "STRONG_BUY"  # bear demands >= 0.70


def test_persist_signals_empty_short_circuits() -> None:
    conn = _conn()
    empty_idx = pd.Index([], name="symbol")
    n = asyncio.run(
        persist_signals(
            conn,
            model="model_a",
            model_version="v1_5",
            as_of=date(2026, 5, 20),
            preds=pd.DataFrame({"prob_up": [], "expected_return": [], "rank": []}, index=empty_idx),
            shap_df=pd.DataFrame({"mom_6": [], "bias": []}, index=empty_idx),
            regime="neutral",
        )
    )
    assert n == 0
    conn.executemany.assert_not_awaited()


def test_persist_signals_index_mismatch_raises() -> None:
    preds, shap = _preds_shap()
    bad_shap = shap.rename(index={"AAA.AU": "ZZZ.AU"})
    conn = _conn()
    with pytest.raises(ValueError, match="same symbol index"):
        asyncio.run(
            persist_signals(
                conn,
                model="model_a",
                model_version="v1_5",
                as_of=date(2026, 5, 20),
                preds=preds,
                shap_df=bad_shap,
                regime="neutral",
            )
        )


def test_persist_signals_realigns_shap_index_order() -> None:
    """preds comes back rank-sorted from model_a._predict; shap_df keeps the
    input order. Writer must reindex shap_df to preds, not just check set
    equality, so per-row payloads aren't misattributed across symbols."""
    preds, shap = _preds_shap()
    # Shuffle shap_df order so it no longer matches preds row-wise
    shuffled = shap.loc[["CCC.AU", "AAA.AU", "BBB.AU"]]
    conn = _conn()
    asyncio.run(
        persist_signals(
            conn,
            model="model_a",
            model_version="v1_5",
            as_of=date(2026, 5, 20),
            preds=preds,
            shap_df=shuffled,
            regime="neutral",
        )
    )
    _, rows = conn.executemany.await_args.args
    by_symbol = {r[2]: json.loads(r[9]) for r in rows}
    # mom_6 in fixture: AAA=0.5, BBB=-0.1, CCC=0.2 — verify by-symbol map preserves
    assert by_symbol["AAA.AU"]["mom_6"] == 0.5
    assert by_symbol["BBB.AU"]["mom_6"] == -0.1
    assert by_symbol["CCC.AU"]["mom_6"] == 0.2


def test_persist_signals_nan_shap_to_null() -> None:
    """SHAP nan values must serialise to JSON null, not the literal token 'NaN'."""
    idx = pd.Index(["A.AU"], name="symbol")
    preds = pd.DataFrame({"prob_up": [0.6], "expected_return": [0.02], "rank": [1]}, index=idx)
    shap = pd.DataFrame({"mom_6": [np.nan], "bias": [0.0]}, index=idx)
    conn = _conn()
    asyncio.run(
        persist_signals(
            conn,
            model="model_a",
            model_version="v1_5",
            as_of=date(2026, 5, 20),
            preds=preds,
            shap_df=shap,
            regime="neutral",
        )
    )
    _, rows = conn.executemany.await_args.args
    payload = json.loads(rows[0][9])
    assert payload["mom_6"] is None
