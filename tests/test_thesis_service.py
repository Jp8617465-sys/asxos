"""Tests for asxos/domain/theses/service.py — M-Thesis-1.

Mocks asyncpg connections; no real DB required.
Covers all hard-fail paths and the Decimal serialisation contract.

asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.theses import service as svc
from asxos.domain.theses.types import Thesis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=30)


def _make_thesis_row(
    thesis_id: int = 1,
    symbol: str = "CBA.AU",
    status: str = "watching",
    thesis_text: str | None = "Rate cycle play — NIM expansion when RBA cuts",
    entry_band_lower: Decimal | None = Decimal("42.000000"),
    entry_band_upper: Decimal | None = Decimal("45.000000"),
    stop_price: Decimal | None = Decimal("38.000000"),
    target_price: Decimal | None = Decimal("60.000000"),
    timeline_days: int | None = 540,
    actual_entry_price: Decimal | None = None,
    actual_entry_at: datetime | None = None,
    actual_exit_price: Decimal | None = None,
    actual_exit_at: datetime | None = None,
) -> dict:
    """Return a dict shaped like an asyncpg theses row."""
    return {
        "thesis_id": thesis_id,
        "symbol": symbol,
        "status": status,
        "thesis_text": thesis_text,
        "entry_band_lower": entry_band_lower,
        "entry_band_upper": entry_band_upper,
        "stop_price": stop_price,
        "target_price": target_price,
        "timeline_days": timeline_days,
        "invalidation_conditions": [],
        "themes": [],
        "actual_entry_price": actual_entry_price,
        "actual_entry_at": actual_entry_at,
        "actual_exit_price": actual_exit_price,
        "actual_exit_at": actual_exit_at,
        "last_revisited_at": _NOW,
        "revisit_due_at": _DUE,
        "opened_at": _NOW,
        "closed_at": None,
    }


def _make_conn(
    fetchrow_returns: list | None = None,
    fetch_returns: list | None = None,
) -> MagicMock:
    """Return a mock asyncpg connection.

    fetchrow_returns: list of values returned on successive fetchrow() calls.
    fetch_returns:    list of values returned on successive fetch() calls.
    """

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn.execute = AsyncMock(return_value=None)

    fr_side = iter(fetchrow_returns or [])
    fc_side = iter(fetch_returns or [[]])

    async def _fetchrow(_q, *_args):
        return next(fr_side, None)

    async def _fetch(_q, *_args):
        return next(fc_side, [])

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    return conn


# ---------------------------------------------------------------------------
# 1. open_thesis — happy path
# ---------------------------------------------------------------------------

async def test_open_thesis_happy_path() -> None:
    row = _make_thesis_row(
        thesis_text="Rate cycle play — NIM expansion when RBA cuts"
    )
    conn = _make_conn(fetchrow_returns=[row])

    t = await svc.open_thesis(
        conn, "CBA.AU",
        status="watching",
        thesis_text="Rate cycle play — NIM expansion when RBA cuts",
        stop_price=Decimal("38"),
        target_price=Decimal("60"),
        timeline_days=540,
        reasoning="Opening position on thesis",
    )

    assert isinstance(t, Thesis)
    assert t.symbol == "CBA.AU"
    assert t.status == "watching"
    assert t.thesis_id == 1


# ---------------------------------------------------------------------------
# 2. open_thesis — symbol validation
# ---------------------------------------------------------------------------

async def test_open_thesis_invalid_symbol_no_suffix_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match=r"must end with .AU or .US"):
        await svc.open_thesis(conn, "MIN")


async def test_open_thesis_invalid_suffix_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match=r"must end with .AU or .US"):
        await svc.open_thesis(conn, "MIN.ASX")


async def test_open_thesis_us_symbol_accepted() -> None:
    row = _make_thesis_row(symbol="NVDA.US")
    conn = _make_conn(fetchrow_returns=[row])
    t = await svc.open_thesis(conn, "NVDA.US")
    assert t.symbol == "NVDA.US"


# ---------------------------------------------------------------------------
# 3. enter_thesis — sets active + actual_entry_price
# ---------------------------------------------------------------------------

async def test_enter_thesis_sets_active() -> None:
    existing = _make_thesis_row(status="watching", actual_entry_price=None)
    updated = _make_thesis_row(
        status="active",
        actual_entry_price=Decimal("43.500000"),
        actual_entry_at=_NOW,
    )
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43.50"), qty=100)

    assert t.status == "active"
    assert t.actual_entry_price == Decimal("43.500000")


# ---------------------------------------------------------------------------
# 4. enter_thesis — hard-fail: no thesis_text
# ---------------------------------------------------------------------------

async def test_enter_thesis_no_thesis_text_raises() -> None:
    existing = _make_thesis_row(status="watching", thesis_text=None)
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match="thesis_text is empty"):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_empty_thesis_text_raises() -> None:
    existing = _make_thesis_row(status="watching", thesis_text="")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match="thesis_text is empty"):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


# ---------------------------------------------------------------------------
# 5. enter_thesis — hard-fail: already active / exited
# ---------------------------------------------------------------------------

async def test_enter_thesis_already_active_raises() -> None:
    existing = _make_thesis_row(status="active")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"status is .active."):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_exited_raises() -> None:
    existing = _make_thesis_row(status="exited")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"status is .exited."):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


# ---------------------------------------------------------------------------
# 6. revise_thesis — stop_price update + stop_adjusted revision
# ---------------------------------------------------------------------------

async def test_revise_thesis_stop() -> None:
    existing = _make_thesis_row(stop_price=Decimal("38.000000"))
    updated = _make_thesis_row(stop_price=Decimal("36.000000"))
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.revise_thesis(
        conn, thesis_id=1, field="stop_price", value=Decimal("36"), reasoning="Widening stop"
    )

    assert t.stop_price == Decimal("36.000000")


# ---------------------------------------------------------------------------
# 7. revise_thesis — hard-fail: unknown field
# ---------------------------------------------------------------------------

async def test_revise_thesis_invalid_field_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="not revisable"):
        await svc.revise_thesis(
            conn, thesis_id=1,
            field="arbitrary_column_injection",
            value="DROP TABLE theses",
            reasoning="test",
        )


# ---------------------------------------------------------------------------
# 8. revise_thesis — Decimal diff is string-serialised (no float)
# ---------------------------------------------------------------------------

async def test_revise_thesis_writes_decimal_diff_as_string() -> None:
    """diff JSONB must contain str representations, not floats."""
    existing = _make_thesis_row(stop_price=Decimal("38.000000"))
    updated = _make_thesis_row(stop_price=Decimal("36.000000"))
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx

    fr_returns = iter([existing, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    await svc.revise_thesis(
        conn, thesis_id=1, field="stop_price", value=Decimal("36"), reasoning="test"
    )

    # Find the INSERT INTO thesis_revisions call
    revision_calls = [(q, a) for q, a in execute_calls if "thesis_revisions" in q]
    assert revision_calls, "No revision INSERT found"

    # The diff arg is the 4th parameter (index 3): thesis_id, revised_at, type, diff, reasoning
    import json
    diff_json = revision_calls[0][1][3]  # 4th positional arg = diff JSON string
    diff = json.loads(diff_json)
    assert "stop_price" in diff
    old_val = diff["stop_price"]["old"]
    new_val = diff["stop_price"]["new"]
    # Must be parseable as Decimal — not float-formatted
    assert Decimal(old_val) == Decimal("38.000000")
    assert Decimal(new_val) == Decimal("36")
    # Must not have float precision artifacts
    assert "e" not in old_val.lower()
    assert "e" not in new_val.lower()


# ---------------------------------------------------------------------------
# 9. review_thesis — no field change; reviewed_no_change revision written
# ---------------------------------------------------------------------------

async def test_review_thesis_no_field_change() -> None:
    existing_id_row = {"thesis_id": 1}
    updated = _make_thesis_row()
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx

    fr_returns = iter([existing_id_row, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    t = await svc.review_thesis(conn, thesis_id=1, reasoning="Thesis intact; waiting for catalyst")

    assert isinstance(t, Thesis)
    # Check revision was written with correct type
    revision_calls = [(q, a) for q, a in execute_calls if "thesis_revisions" in q]
    assert revision_calls
    revision_type = revision_calls[0][1][2]  # 3rd positional arg = revision_type
    assert revision_type == "reviewed_no_change"

    import json
    diff_json = revision_calls[0][1][3]
    diff = json.loads(diff_json)
    assert diff == {}  # empty diff for no-change review


async def test_review_thesis_empty_reasoning_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.review_thesis(conn, thesis_id=1, reasoning="")


async def test_review_thesis_whitespace_reasoning_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.review_thesis(conn, thesis_id=1, reasoning="   ")


# ---------------------------------------------------------------------------
# 10. exit_thesis — sets exited + actual_exit_price + closed_at
# ---------------------------------------------------------------------------

async def test_exit_thesis_sets_exited() -> None:
    existing = _make_thesis_row(status="active", actual_entry_price=Decimal("43"))
    updated = _make_thesis_row(
        status="exited",
        actual_entry_price=Decimal("43"),
        actual_exit_price=Decimal("58.000000"),
        actual_exit_at=_NOW,
    )
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.exit_thesis(
        conn, thesis_id=1, exit_price=Decimal("58"),
        revision_type="exited", reasoning="Target approached, taking profit",
    )

    assert t.status == "exited"
    assert t.actual_exit_price == Decimal("58.000000")


# ---------------------------------------------------------------------------
# 11. exit_thesis — hard-fail: already exited
# ---------------------------------------------------------------------------

async def test_exit_thesis_already_exited_raises() -> None:
    existing = _make_thesis_row(status="exited")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"already .exited."):
        await svc.exit_thesis(conn, thesis_id=1, exit_price=Decimal("58"))


async def test_exit_thesis_already_expired_raises() -> None:
    existing = _make_thesis_row(status="expired")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"already .expired."):
        await svc.exit_thesis(conn, thesis_id=1, exit_price=Decimal("40"))


# ---------------------------------------------------------------------------
# 12. exit_thesis — hard-fail: invalid revision_type
# ---------------------------------------------------------------------------

async def test_exit_thesis_invalid_revision_type_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="revision_type must be one of"):
        await svc.exit_thesis(
            conn, thesis_id=1, exit_price=Decimal("58"),
            revision_type="wrong_type",
        )
