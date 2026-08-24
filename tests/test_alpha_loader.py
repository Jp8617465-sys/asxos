"""Tests for asxos.domain.research.alpha_loader.

This module was at 0% coverage while being live: ``jobs/eval_alpha_factors.py:24``
and ``scripts/alpha_eval.py:33`` both import it. The SQL itself needs a real
Postgres to exercise, so the DB call is mocked here (mirroring
tests/test_price_coverage.py) and the tests cover what is testable without one:

  * the DataFrame post-processing — Decimal -> float coercion, date coercion,
    NULL forward returns becoming NaN rather than raising;
  * the empty-result early return, which must not touch columns that do not
    exist;
  * the bind parameter on the factor panel;
  * the horizon/SQL sync invariant that the module's own comment asks callers
    to maintain by hand ("keep this in sync with _PANEL_SQL if you add one").

That last one is the reason this file earns its keep: a horizon added to
HORIZONS without a matching LEFT JOIN would silently produce a panel missing a
return column, and alpha_eval would evaluate a horizon that is all-NaN.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from asxos.domain.research import alpha_loader
from asxos.domain.research.alpha_loader import (
    FACTOR_HORIZONS,
    HORIZONS,
    load_factor_panel,
    load_panel,
)


def _conn(rows: list[dict[str, Any]]) -> MagicMock:
    """A mock asyncpg connection whose fetch() returns `rows`.

    asyncpg hands back Record objects; load_panel only does dict(r), and a dict
    is its own dict(), so plain dicts are a faithful stand-in.
    """
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)
    return conn


def _signal_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": "BHP.AU",
        "signal_date": date(2026, 3, 2),
        "prob_up": Decimal("0.610000"),
        "expected_return": Decimal("0.021000"),
        "composite": Decimal("0.374400"),
        "signal_label": "BUY",
        "regime": "risk_on",
        "price": Decimal("44.120000"),
        "dollar_volume": Decimal("123456.780000"),
        "ret_5": Decimal("0.011000"),
        "ret_10": Decimal("-0.004000"),
        "ret_21": Decimal("0.032000"),
        "ret_63": None,  # LEFT JOIN miss — not enough forward history yet
    }
    row.update(overrides)
    return row


# --- load_panel ---------------------------------------------------------------


async def test_load_panel_empty_returns_empty_frame() -> None:
    """No rows must not raise on the date/float coercion that follows."""
    df = await load_panel(_conn([]))
    assert isinstance(df, pd.DataFrame)
    assert df.empty


async def test_load_panel_coerces_numerics_to_float() -> None:
    """NUMERIC arrives as Decimal; the research engine is numpy/pandas-based."""
    df = await load_panel(_conn([_signal_row()]))

    for col in ("prob_up", "expected_return", "composite", "price", "dollar_volume"):
        assert df[col].dtype == "float64", col
    assert df.loc[0, "prob_up"] == pytest.approx(0.61)
    assert df.loc[0, "price"] == pytest.approx(44.12)


async def test_load_panel_coerces_signal_date_to_plain_date() -> None:
    df = await load_panel(_conn([_signal_row()]))
    assert df.loc[0, "signal_date"] == date(2026, 3, 2)
    assert type(df.loc[0, "signal_date"]) is date


async def test_load_panel_null_forward_return_becomes_nan() -> None:
    """A LEFT JOIN miss (not enough forward bars) is NaN, never an exception.

    This is the common case at the long end of the panel, so it must not be an
    error path.
    """
    df = await load_panel(_conn([_signal_row()]))
    assert pd.isna(df.loc[0, "ret_63"])
    assert df["ret_63"].dtype == "float64"
    assert df.loc[0, "ret_21"] == pytest.approx(0.032)


async def test_load_panel_preserves_non_numeric_columns() -> None:
    df = await load_panel(_conn([_signal_row()]))
    assert df.loc[0, "symbol"] == "BHP.AU"
    assert df.loc[0, "signal_label"] == "BUY"
    assert df.loc[0, "regime"] == "risk_on"


async def test_load_panel_handles_multiple_symbols() -> None:
    rows = [_signal_row(), _signal_row(symbol="CBA.AU", prob_up=Decimal("0.48"))]
    df = await load_panel(_conn(rows))
    assert list(df["symbol"]) == ["BHP.AU", "CBA.AU"]
    assert df.loc[1, "prob_up"] == pytest.approx(0.48)


# --- load_factor_panel --------------------------------------------------------


def _factor_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": "CSL.AU",
        "signal_date": date(2026, 1, 30),
        "sector": "Health Care",
        "value_score": Decimal("-0.420000"),
        "quality_score": Decimal("1.180000"),
        "momentum_score": Decimal("0.330000"),
        "low_vol_score": Decimal("0.070000"),
        "yield_score": Decimal("-1.010000"),
        "composite_score": Decimal("0.230000"),
        "price": Decimal("281.400000"),
        "dollar_volume": Decimal("9876.540000"),
        "ret_21": Decimal("0.014000"),
        "ret_63": Decimal("0.041000"),
        "ret_126": None,
        "ret_252": None,
    }
    row.update(overrides)
    return row


async def test_load_factor_panel_empty_returns_empty_frame() -> None:
    df = await load_factor_panel(_conn([]))
    assert isinstance(df, pd.DataFrame)
    assert df.empty


async def test_load_factor_panel_binds_default_factor_set_version() -> None:
    """factor_set_version is a bind parameter, not interpolation."""
    conn = _conn([_factor_row()])
    await load_factor_panel(conn)
    _, args = conn.fetch.call_args[0][0], conn.fetch.call_args[0][1:]
    assert args == ("fs_v1",)


async def test_load_factor_panel_binds_explicit_factor_set_version() -> None:
    conn = _conn([_factor_row()])
    await load_factor_panel(conn, factor_set_version="fs_v2")
    assert conn.fetch.call_args[0][1:] == ("fs_v2",)


async def test_load_factor_panel_coerces_scores_and_returns() -> None:
    df = await load_factor_panel(_conn([_factor_row()]))
    for col in (
        "value_score", "quality_score", "momentum_score",
        "low_vol_score", "yield_score", "composite_score",
        "ret_21", "ret_63",
    ):
        assert df[col].dtype == "float64", col
    assert df.loc[0, "quality_score"] == pytest.approx(1.18)
    assert pd.isna(df.loc[0, "ret_252"])


async def test_load_factor_panel_keeps_sector_for_neutralisation() -> None:
    """sector is what makes sector-neutral evaluation possible downstream."""
    df = await load_factor_panel(_conn([_factor_row()]))
    assert df.loc[0, "sector"] == "Health Care"


# --- the hand-maintained sync invariant ---------------------------------------


def _left_join_horizons(sql: str) -> set[int]:
    """Horizons the SQL actually joins, read off `b.rn0 + N`."""
    return {int(m) for m in re.findall(r"b\.rn0 \+ (\d+)", sql)}


def _selected_return_horizons(sql: str) -> set[int]:
    """Horizons the SQL actually selects, read off `AS ret_N`."""
    return {int(m) for m in re.findall(r"AS ret_(\d+)", sql)}


@pytest.mark.parametrize(
    ("horizons", "sql", "float_cols", "label"),
    [
        (HORIZONS, alpha_loader._PANEL_SQL, alpha_loader._FLOAT_COLS, "signal"),
        (
            FACTOR_HORIZONS,
            alpha_loader._FACTOR_PANEL_SQL,
            alpha_loader._FACTOR_FLOAT_COLS,
            "factor",
        ),
    ],
)
def test_horizons_match_the_sql(
    horizons: tuple[int, ...], sql: str, float_cols: list[str], label: str
) -> None:
    """The module asks callers to keep HORIZONS in sync with the SQL by hand.

    A horizon added to the tuple without a matching LEFT JOIN would produce a
    panel silently missing that return column, and alpha_eval would then
    evaluate an all-NaN horizon as if it were a real result. This is the check
    that comment was asking for.
    """
    expected = set(horizons)
    assert _left_join_horizons(sql) == expected, f"{label}: LEFT JOIN drift"
    assert _selected_return_horizons(sql) == expected, f"{label}: SELECT drift"
    assert {f"ret_{h}" for h in expected} <= set(float_cols), (
        f"{label}: a ret_ column is missing from the float-coercion list, so it "
        "would stay Decimal/object and break numeric comparisons downstream"
    )
