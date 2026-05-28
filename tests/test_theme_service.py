"""Tests for asxos/domain/themes/service.py — M-Thesis-1.

Mocks asyncpg connections; no real DB required.
asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.themes import service as svc
from asxos.domain.themes.types import Theme, ThemeHolding

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC)
_TODAY = date(2026, 5, 28)


def _make_theme_row(
    theme_id: int = 1,
    theme_code: str = "big-4-banks",
    name: str = "Big 4 Banks",
    description: str = "Australian major bank oligopoly",
    conviction_band: str = "medium",
    stage: str = "mainstream",
    stage_suggested: str | None = None,
    adjacent_codes: list | None = None,
    started_at: date = _TODAY,
    retired_at: date | None = None,
) -> dict:
    return {
        "theme_id": theme_id,
        "theme_code": theme_code,
        "name": name,
        "description": description,
        "conviction_band": conviction_band,
        "stage": stage,
        "stage_suggested": stage_suggested,
        "adjacent_codes": adjacent_codes or [],
        "started_at": started_at,
        "retired_at": retired_at,
        "last_reviewed_at": _NOW,
    }


def _make_holding_row(
    theme_id: int = 1,
    symbol: str = "CBA.AU",
    exposure_strength: Decimal = Decimal("0.700000"),
    direction: str = "positive",
    mechanism_text: str = "NIM benefits from higher rates",
    source: str = "user",
    note: str | None = None,
) -> dict:
    return {
        "theme_id": theme_id,
        "symbol": symbol,
        "exposure_strength": exposure_strength,
        "direction": direction,
        "mechanism_text": mechanism_text,
        "source": source,
        "last_validated_at": _NOW,
        "note": note,
        "created_at": _NOW,
    }


def _make_conn(
    fetchrow_returns: list | None = None,
    fetch_returns: list | None = None,
    fetchval_returns: list | None = None,
) -> MagicMock:
    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn.execute = AsyncMock(return_value=None)

    fr_side = iter(fetchrow_returns or [])
    fc_side = iter(fetch_returns or [[]])
    fv_side = iter(fetchval_returns or [])

    async def _fetchrow(_q, *_args):
        return next(fr_side, None)

    async def _fetch(_q, *_args):
        return next(fc_side, [])

    async def _fetchval(_q, *_args):
        return next(fv_side, None)

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    conn.fetchval = _fetchval
    return conn


# ---------------------------------------------------------------------------
# 1. create_theme — inserts row
# ---------------------------------------------------------------------------

async def test_create_theme_inserts_row() -> None:
    row = _make_theme_row()
    conn = _make_conn(fetchrow_returns=[row])

    theme = await svc.create_theme(
        conn, "big-4-banks", "Big 4 Banks",
        "Australian major bank oligopoly",
        conviction_band="medium",
        stage="mainstream",
    )

    assert isinstance(theme, Theme)
    assert theme.theme_code == "big-4-banks"
    assert theme.stage == "mainstream"
    assert theme.retired_at is None


async def test_create_theme_invalid_conviction_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="conviction_band must be one of"):
        await svc.create_theme(conn, "code", "Name", "Desc", conviction_band="extreme")


async def test_create_theme_invalid_stage_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="stage must be one of"):
        await svc.create_theme(conn, "code", "Name", "Desc", stage="zombie")


async def test_create_theme_empty_description_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="description is required"):
        await svc.create_theme(conn, "code", "Name", "")


# ---------------------------------------------------------------------------
# 2. add_adjacency — bidirectional; both arrays updated
# ---------------------------------------------------------------------------

async def test_add_adjacency_bidirectional() -> None:
    """Both theme codes exist; execute is called twice (once per direction)."""
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx

    # fetchval is called once per code to verify existence
    fv_side = iter([1, 2])  # theme_ids for code_a and code_b

    async def _fetchval(_q, *_args):
        return next(fv_side, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchval = _fetchval
    conn.execute = _execute

    await svc.add_adjacency(conn, "big-4-banks", "rates-up")

    assert len(execute_calls) == 2, f"Expected 2 UPDATEs, got {len(execute_calls)}"

    # First call: append 'rates-up' to big-4-banks.adjacent_codes
    first_args = execute_calls[0][1]
    assert "rates-up" in first_args

    # Second call: append 'big-4-banks' to rates-up.adjacent_codes
    second_args = execute_calls[1][1]
    assert "big-4-banks" in second_args


async def test_add_adjacency_missing_code_raises() -> None:
    """Hard-fail if either theme code doesn't exist."""

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx

    # First fetchval returns None → code does not exist
    fv_side = iter([None])

    async def _fetchval(_q, *_args):
        return next(fv_side, None)

    conn.fetchval = _fetchval

    with pytest.raises(ValueError, match="not found"):
        await svc.add_adjacency(conn, "nonexistent-code", "other-code")


# ---------------------------------------------------------------------------
# 3. set_stage — does NOT touch stage_suggested
# ---------------------------------------------------------------------------

async def test_set_stage_does_not_touch_stage_suggested() -> None:
    """set_stage updates stage (user-confirmed) but never writes stage_suggested."""
    # stage_suggested is 'mainstream'; user sets stage to 'late-retail'
    row = _make_theme_row(stage="late-retail", stage_suggested="mainstream")
    execute_calls: list = []
    conn = _make_conn(fetchrow_returns=[row])

    async def _execute(query, *args):
        execute_calls.append((query, args))
        return None

    conn.execute = _execute

    theme = await svc.set_stage(conn, "big-4-banks", "late-retail", note="Too broad now")

    assert theme.stage == "late-retail"
    assert theme.stage_suggested == "mainstream"  # unchanged

    # No UPDATE should touch stage_suggested column
    for query, _ in execute_calls:
        assert "stage_suggested" not in query, (
            f"set_stage must not write stage_suggested, but found it in: {query!r}"
        )


async def test_set_stage_invalid_stage_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="stage must be one of"):
        await svc.set_stage(conn, "big-4-banks", "zombie", note="test")


async def test_set_stage_empty_note_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="note is required"):
        await svc.set_stage(conn, "big-4-banks", "mainstream", note="")


# ---------------------------------------------------------------------------
# 4. add_adjacency — idempotent guard (no duplicate in SQL)
# ---------------------------------------------------------------------------

async def test_add_adjacency_guard_clause_in_sql() -> None:
    """The UPDATE SQL must include the NOT (x = ANY(adjacent_codes)) guard."""
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fv_side = iter([1, 2])

    async def _fetchval(_q, *_args):
        return next(fv_side, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchval = _fetchval
    conn.execute = _execute

    await svc.add_adjacency(conn, "big-4-banks", "rates-up")

    for query, _ in execute_calls:
        assert "ANY(adjacent_codes)" in query, (
            f"Expected duplicate guard in UPDATE, not found in: {query!r}"
        )


# ---------------------------------------------------------------------------
# 5. attach_thesis — upserts theme_holdings with (theme_id, symbol) PK
# ---------------------------------------------------------------------------

async def test_attach_thesis_returns_holding() -> None:
    theme_row = {"theme_id": 1}
    holding_row = _make_holding_row()
    conn = _make_conn(fetchrow_returns=[theme_row, holding_row])

    holding = await svc.attach_thesis(
        conn, "big-4-banks", "CBA.AU",
        exposure_strength=Decimal("0.7"),
        direction="positive",
        mechanism_text="NIM benefits from higher rates",
    )

    assert isinstance(holding, ThemeHolding)
    assert holding.symbol == "CBA.AU"
    assert holding.exposure_strength == Decimal("0.700000")
    assert holding.direction == "positive"


async def test_attach_thesis_invalid_direction_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="direction must be one of"):
        await svc.attach_thesis(
            conn, "big-4-banks", "CBA.AU",
            exposure_strength=Decimal("0.7"),
            direction="bullish",  # invalid
        )


async def test_attach_thesis_strength_out_of_range_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="exposure_strength must be in"):
        await svc.attach_thesis(
            conn, "big-4-banks", "CBA.AU",
            exposure_strength=Decimal("1.1"),
        )


async def test_attach_thesis_missing_theme_raises() -> None:
    # fetchrow for theme lookup returns None → theme doesn't exist
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.attach_thesis(
            conn, "nonexistent-theme", "CBA.AU",
            exposure_strength=Decimal("0.5"),
        )
