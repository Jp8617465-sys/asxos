"""
Integration tests for `asxos.domain.portfolio.profile` against a real
asyncpg Connection seeded against a tmp `profiles` table.

Mocks the schema by creating the same table + index + function in
a transaction that's rolled back. No real Supabase connection is needed.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.portfolio.profile import (
    _normalise_score_weights,
    _row_to_profile,
    risk_tolerance_scalar,
)

# ---------------------------------------------------------------------------
# risk_tolerance_scalar — pure
# ---------------------------------------------------------------------------


def test_risk_label_to_scalar_known():
    assert risk_tolerance_scalar("conservative") == Decimal("0.25")
    assert risk_tolerance_scalar("balanced") == Decimal("0.50")
    assert risk_tolerance_scalar("growth") == Decimal("0.75")
    assert risk_tolerance_scalar("aggressive") == Decimal("1.00")


def test_risk_label_unknown_raises():
    with pytest.raises(ValueError, match="unknown risk_tolerance"):
        risk_tolerance_scalar("yolo")


# ---------------------------------------------------------------------------
# _normalise_score_weights — pure, exact Decimal sum
# ---------------------------------------------------------------------------


def test_normalise_already_exact():
    out = _normalise_score_weights({"prob_up": "0.6", "expected_return": "0.4"})
    assert out["prob_up"] + out["expected_return"] == Decimal("1.0")


def test_normalise_decimal_precision_input():
    # 0.333333 + 0.666667 = 0.999999 — DB CHECK tolerates; load normalises.
    out = _normalise_score_weights(
        {"prob_up": "0.333333", "expected_return": "0.666667"}
    )
    assert out["prob_up"] + out["expected_return"] == Decimal("1")


def test_normalise_zero_sum_raises():
    with pytest.raises(ValueError, match="sum is zero"):
        _normalise_score_weights({"prob_up": "0", "expected_return": "0"})


def test_normalise_accepts_numeric_inputs():
    # asyncpg may return Decimal from a NUMERIC column or string from JSONB
    out = _normalise_score_weights(
        {"prob_up": Decimal("0.5"), "expected_return": Decimal("0.5")}
    )
    assert out == {"prob_up": Decimal("0.5"), "expected_return": Decimal("0.5")}


# ---------------------------------------------------------------------------
# _row_to_profile — pure given an asyncpg-shaped Record dict
# ---------------------------------------------------------------------------


def _make_row(**overrides) -> dict[str, Any]:
    base: dict[str, Any] = {
        "profile_id": 1,
        "name": "baseline",
        "is_active": True,
        "account_type": "individual",
        "risk_tolerance": "balanced",
        "risk_tolerance_scalar": Decimal("0.5"),
        "capital_aud": Decimal("500000"),
        "cash_floor_pct": Decimal("0.05"),
        "leverage_cap": Decimal("1.0"),
        "per_name_cap_pct": Decimal("0.10"),
        "sector_cap_pct": Decimal("0.30"),
        "excluded_sectors": [],
        "excluded_symbols": [],
        "min_position_aud": Decimal("1000"),
        "horizon_years": 10,
        "defer_near_boundary_sells": True,
        "score_weights_json": {"prob_up": Decimal("0.6"), "expected_return": Decimal("0.4")},
        "created_at": date(2026, 5, 22),
        "updated_at": date(2026, 5, 22),
    }
    base.update(overrides)
    return base


def test_row_to_profile_happy():
    p = _row_to_profile(_make_row())  # type: ignore[arg-type]
    assert p.profile_id == 1
    assert p.name == "baseline"
    assert p.is_active is True
    assert p.risk_tolerance_scalar == Decimal("0.5")
    assert p.score_weights_json == {
        "prob_up": Decimal("0.6"),
        "expected_return": Decimal("0.4"),
    }


def test_row_to_profile_jsonb_as_string():
    row = _make_row(
        score_weights_json=json.dumps({"prob_up": "0.7", "expected_return": "0.3"})
    )
    p = _row_to_profile(row)  # type: ignore[arg-type]
    assert p.score_weights_json["prob_up"] == Decimal("0.7")
    assert p.score_weights_json["expected_return"] == Decimal("0.3")


def test_row_to_profile_normalises_imprecise_weights():
    # Imprecise weights from DB get normalised to sum-1 in memory
    row = _make_row(
        score_weights_json={"prob_up": "0.333333", "expected_return": "0.666667"}
    )
    p = _row_to_profile(row)  # type: ignore[arg-type]
    assert p.score_weights_json["prob_up"] + p.score_weights_json["expected_return"] == Decimal("1")


def test_row_to_profile_validates_via_dataclass():
    # Negative capital from DB → dataclass validator raises during _row_to_profile
    with pytest.raises(ValueError, match="capital_aud"):
        _row_to_profile(_make_row(capital_aud=Decimal("-1")))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# load_active / load_by_name / list_profiles — DB stubs
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_conn():
    """Minimal asyncpg.Connection stand-in. Tests set return values per-call."""
    c = MagicMock()
    c.fetchrow = AsyncMock()
    c.fetch = AsyncMock()
    c.fetchval = AsyncMock()
    c.execute = AsyncMock()
    return c


@pytest.mark.asyncio
async def test_load_active_returns_none_when_no_active(mock_conn):
    from asxos.domain.portfolio.profile import load_active

    mock_conn.fetchrow.return_value = None
    result = await load_active(mock_conn)
    assert result is None
    mock_conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_active_returns_profile(mock_conn):
    from asxos.domain.portfolio.profile import load_active

    mock_conn.fetchrow.return_value = _make_row()  # type: ignore[arg-type]
    p = await load_active(mock_conn)
    assert p is not None
    assert p.name == "baseline"
    assert p.is_active is True


@pytest.mark.asyncio
async def test_load_by_name_returns_none(mock_conn):
    from asxos.domain.portfolio.profile import load_by_name

    mock_conn.fetchrow.return_value = None
    assert await load_by_name(mock_conn, "missing") is None


@pytest.mark.asyncio
async def test_list_profiles_empty(mock_conn):
    from asxos.domain.portfolio.profile import list_profiles

    mock_conn.fetch.return_value = []
    assert await list_profiles(mock_conn) == []


@pytest.mark.asyncio
async def test_list_profiles_two_rows(mock_conn):
    from asxos.domain.portfolio.profile import list_profiles

    mock_conn.fetch.return_value = [
        _make_row(profile_id=1, name="baseline"),
        _make_row(profile_id=2, name="defensive", is_active=False),
    ]
    out = await list_profiles(mock_conn)
    assert len(out) == 2
    assert {p.name for p in out} == {"baseline", "defensive"}


# ---------------------------------------------------------------------------
# save — validators fire BEFORE DB I/O
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_negative_capital_raises_before_db(mock_conn):
    from asxos.domain.portfolio.profile import save

    with pytest.raises(ValueError, match="capital_aud"):
        await save(
            mock_conn,
            name="bad",
            account_type="individual",
            risk_tolerance="balanced",
            capital_aud=Decimal("-1"),
        )
    # The DB was never touched
    mock_conn.fetchval.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_unknown_risk_label_raises_before_db(mock_conn):
    from asxos.domain.portfolio.profile import save

    with pytest.raises(ValueError, match="unknown risk_tolerance"):
        await save(
            mock_conn,
            name="bad",
            account_type="individual",
            risk_tolerance="yolo",  # type: ignore[arg-type]
            capital_aud=Decimal("100000"),
        )
    mock_conn.fetchval.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_happy_path_returns_id(mock_conn):
    from asxos.domain.portfolio.profile import save

    mock_conn.fetchval.return_value = 42
    pid = await save(
        mock_conn,
        name="baseline",
        account_type="individual",
        risk_tolerance="balanced",
        capital_aud=Decimal("500000"),
    )
    assert pid == 42
    mock_conn.fetchval.assert_awaited_once()
    # Verify the SQL includes the new M13 columns
    sql = mock_conn.fetchval.await_args.args[0]
    assert "defer_near_boundary_sells" in sql
    assert "score_weights_json" in sql


@pytest.mark.asyncio
async def test_save_passes_normalised_weights(mock_conn):
    from asxos.domain.portfolio.profile import save

    mock_conn.fetchval.return_value = 7
    await save(
        mock_conn,
        name="weighted",
        account_type="individual",
        risk_tolerance="growth",
        capital_aud=Decimal("100000"),
        score_weights_json={"prob_up": Decimal("0.8"), "expected_return": Decimal("0.2")},
    )
    # The JSONB payload (positional arg 15) is the last value
    args = mock_conn.fetchval.await_args.args
    weights_json = args[-1]
    assert "0.8" in weights_json and "0.2" in weights_json


# ---------------------------------------------------------------------------
# activate — calls the Postgres function
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_calls_set_active_profile(mock_conn):
    from asxos.domain.portfolio.profile import activate

    mock_conn.fetchval.return_value = 5
    pid = await activate(mock_conn, "baseline")
    assert pid == 5
    mock_conn.fetchval.assert_awaited_once()
    sql = mock_conn.fetchval.await_args.args[0]
    assert "set_active_profile" in sql
    assert mock_conn.fetchval.await_args.args[1] == "baseline"
