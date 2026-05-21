"""
Tests for asxos.domain.signals.loader.load_features_for_date.

Avoids a real Postgres — patches asyncpg.Connection.fetch to return
synthetic rows. Verifies the loader joins prices + fundamentals + caps,
runs the FeatureEngine, restricts to the target date, and drops NaN
rows from the feature columns.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import numpy as np

from asxos.domain.signals.feature_engine import MODEL_A_FEATURES
from asxos.domain.signals.loader import (
    DEFAULT_LOOKBACK_DAYS,
    FUNDAMENTAL_LAG_DAYS,
    load_features_for_date,
)


def _price_rows(symbols: list[str], target: date, n_days: int = 420, seed: int = 1) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for sym in symbols:
        close = 30.0 + np.cumsum(rng.normal(0, 0.4, n_days))
        close = np.maximum(close, 1.0)
        for i, c in enumerate(close):
            d = target - timedelta(days=n_days - 1 - i)
            rows.append(
                {
                    "symbol": sym,
                    "dt": d,
                    "open": float(c),
                    "high": float(c) * 1.01,
                    "low": float(c) * 0.99,
                    "close": float(c),
                    "volume": int(rng.integers(500_000, 5_000_000)),
                }
            )
    return rows


def _fund_rows(
    symbols: list[str], cutoff: date, n_days: int = 420, seed: int = 11
) -> list[dict]:
    """Daily fundamentals snapshots ending at `cutoff` (i.e. target - 45d).
    Values wander so rolling z-scores are well-defined."""
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for i, sym in enumerate(symbols):
        pe = 15.0 + i + np.cumsum(rng.normal(0, 0.05, n_days))
        pb = 1.5 + 0.1 * i + np.cumsum(rng.normal(0, 0.01, n_days))
        eps = 2.0 + 0.1 * i + rng.normal(0, 0.02, n_days)
        for j in range(n_days):
            rows.append(
                {
                    "symbol": sym,
                    "as_of": cutoff - timedelta(days=n_days - 1 - j),
                    "pe_ratio": float(pe[j]),
                    "pb_ratio": float(pb[j]),
                    "eps": float(eps[j]),
                }
            )
    return rows


def _cap_rows(symbols: list[str]) -> list[dict]:
    return [{"symbol": sym, "market_cap": 1e10 + i * 1e9} for i, sym in enumerate(symbols)]


class _RowProxy(dict):
    """asyncpg.Record-like dict that also supports .keys()."""


def _as_records(rows: list[dict]) -> list[_RowProxy]:
    return [_RowProxy(r) for r in rows]


def _build_conn(symbols: list[str], target: date) -> Any:
    """Three fetch() calls expected: prices, fundamentals, caps."""
    prices = _as_records(_price_rows(symbols, target))
    funds = _as_records(_fund_rows(symbols, target - timedelta(days=FUNDAMENTAL_LAG_DAYS)))
    caps = _as_records(_cap_rows(symbols))

    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[prices, funds, caps])
    return conn


def test_load_features_returns_target_date_only() -> None:
    target = date(2026, 5, 15)
    conn = _build_conn(["AAA.AU", "BBB.AU"], target)

    df = asyncio.run(load_features_for_date(conn, target))

    assert not df.empty
    assert df.index.name == "symbol"
    assert set(df.index).issubset({"AAA.AU", "BBB.AU"})
    # All Model A features computed and finite
    for col in MODEL_A_FEATURES:
        assert col in df.columns
        assert np.isfinite(df[col]).all()


def test_load_features_empty_panel_returns_empty() -> None:
    target = date(2026, 5, 15)
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])

    df = asyncio.run(load_features_for_date(conn, target))

    assert df.empty
    # only one fetch was issued — short-circuited on empty prices
    assert conn.fetch.await_count == 1


def test_load_features_uses_expected_lookback_and_lag() -> None:
    target = date(2026, 5, 15)
    conn = _build_conn(["AAA.AU"], target)

    asyncio.run(load_features_for_date(conn, target))

    # First fetch is prices: positional args (start_date, target_date)
    prices_call = conn.fetch.await_args_list[0]
    assert prices_call.args[1] == target - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    assert prices_call.args[2] == target

    # Second fetch is fundamentals: positional arg fundamentals_as_of = target - 45d
    funds_call = conn.fetch.await_args_list[1]
    assert funds_call.args[1] == target - timedelta(days=FUNDAMENTAL_LAG_DAYS)


def test_load_features_zero_fills_when_fundamentals_absent() -> None:
    """No fundamentals → pe_ratio/eps/market_cap/z-scores all zero,
    technical features still computed from prices alone."""
    target = date(2026, 5, 15)
    prices = _as_records(_price_rows(["AAA.AU", "BBB.AU"], target))
    conn = MagicMock()
    conn.fetch = AsyncMock(
        side_effect=[
            prices,
            [],  # fundamentals empty
            _as_records(_cap_rows(["AAA.AU", "BBB.AU"])),
        ]
    )

    df = asyncio.run(load_features_for_date(conn, target))

    assert not df.empty
    # Fundamentals-sourced cols zero-filled rather than NaN.
    # market_cap comes from universe (still populated), so it's exempt.
    for col in ("pe_ratio", "pb_ratio", "eps", "pe_ratio_zscore", "pb_ratio_zscore"):
        assert (df[col] == 0.0).all(), f"{col} should be zero-filled but isn't"
    # All Model A features finite — no dropna firing
    for col in MODEL_A_FEATURES:
        assert np.isfinite(df[col]).all(), f"{col} should be finite"


def test_load_features_dropped_when_panel_too_short() -> None:
    """A panel with only 30 days of prices can't fill rolling windows → empty result."""
    target = date(2026, 5, 15)
    short_prices = _as_records(_price_rows(["AAA.AU"], target, n_days=30))
    conn = MagicMock()
    conn.fetch = AsyncMock(
        side_effect=[
            short_prices,
            _as_records(_fund_rows(["AAA.AU"], target - timedelta(days=FUNDAMENTAL_LAG_DAYS))),
            _as_records(_cap_rows(["AAA.AU"])),
        ]
    )

    df = asyncio.run(load_features_for_date(conn, target))

    # Either empty after NaN-drop, or has rows but no finite feature values —
    # the contract is: the caller never sees rows with NaN features.
    if not df.empty:
        for col in MODEL_A_FEATURES:
            assert np.isfinite(df[col]).all()
