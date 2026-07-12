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
    macro_thesis_id: int | None = None,
    governance_status: str = "approved",
    source_run_id: int | None = None,
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
        "macro_thesis_id": macro_thesis_id,
        "governance_status": governance_status,
        "source_run_id": source_run_id,
    }


def _make_holding_row(
    theme_id: int = 1,
    symbol: str = "CBA.AU",
    exposure_strength: Decimal = Decimal("0.700000"),
    direction: str = "positive",
    mechanism_text: str = "NIM benefits from higher rates",
    source: str = "user",
    note: str | None = None,
    holding_id: int | None = 1,
    governance_status: str = "approved",
    source_run_id: int | None = None,
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
        "holding_id": holding_id,
        "governance_status": governance_status,
        "source_run_id": source_run_id,
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


# ---------------------------------------------------------------------------
# Governance — approve_theme / reject_theme / approve_theme_holding /
# reject_theme_holding (Phase 2a). No agent producer exists yet for
# object_type='theme'/'theme_holding' (Phase 2c) — these exist so the
# themes_governance_audit/theme_holdings_governance_audit triggers
# (migration 0036) have a service-layer path to test against.
# ---------------------------------------------------------------------------

async def test_approve_theme_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_theme_row(governance_status="pending_review"),
            _make_theme_row(governance_status="approved"),
        ]
    )
    theme = await svc.approve_theme(conn, 1, reasoning="Evidence checks out")
    assert theme.governance_status == "approved"
    gov_calls = [c for c in conn.execute.await_args_list if "governance_events" in c.args[0]]
    assert len(gov_calls) == 1
    assert gov_calls[0].args[1:] == ("theme", 1, "pending_review", "approved", "Evidence checks out", "human")


async def test_approve_theme_wrong_status_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_theme_row(governance_status="draft")])
    with pytest.raises(ValueError, match="expected 'pending_review'"):
        await svc.approve_theme(conn, 1, reasoning="x")


async def test_approve_theme_not_found_raises() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.approve_theme(conn, 999, reasoning="x")


async def test_approve_theme_empty_reasoning_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_theme_row(governance_status="pending_review")])
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.approve_theme(conn, 1, reasoning="  ")


async def test_reject_theme_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_theme_row(governance_status="draft"),
            _make_theme_row(governance_status="rejected"),
        ]
    )
    theme = await svc.reject_theme(conn, 1, reasoning="Duplicate")
    assert theme.governance_status == "rejected"


async def test_reject_theme_already_approved_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_theme_row(governance_status="approved")])
    with pytest.raises(ValueError, match="expected one of"):
        await svc.reject_theme(conn, 1, reasoning="x")


async def test_approve_theme_holding_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_holding_row(governance_status="pending_review"),
            _make_holding_row(governance_status="approved"),
        ]
    )
    holding = await svc.approve_theme_holding(conn, 1, reasoning="Evidence checks out")
    assert holding.governance_status == "approved"
    gov_calls = [c for c in conn.execute.await_args_list if "governance_events" in c.args[0]]
    assert len(gov_calls) == 1
    # object_id is holding_id (the surrogate), not (theme_id, symbol).
    assert gov_calls[0].args[1:] == ("theme_holding", 1, "pending_review", "approved", "Evidence checks out", "human")


async def test_approve_theme_holding_wrong_status_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_holding_row(governance_status="draft")])
    with pytest.raises(ValueError, match="expected 'pending_review'"):
        await svc.approve_theme_holding(conn, 1, reasoning="x")


async def test_approve_theme_holding_not_found_raises() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.approve_theme_holding(conn, 999, reasoning="x")


async def test_reject_theme_holding_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_holding_row(governance_status="draft"),
            _make_holding_row(governance_status="rejected"),
        ]
    )
    holding = await svc.reject_theme_holding(conn, 1, reasoning="Not a real exposure")
    assert holding.governance_status == "rejected"


async def test_reject_theme_holding_empty_reasoning_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_holding_row(governance_status="draft")])
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.reject_theme_holding(conn, 1, reasoning="")


# ---------------------------------------------------------------------------
# _row_to_theme / _row_to_theme_holding — governance field defaulting
# ---------------------------------------------------------------------------

async def test_row_to_theme_defaults_governance_status_when_absent() -> None:
    """A pre-migration-0035-shaped row dict (no governance columns) round-
    trips to 'approved' via .get(), not KeyError."""
    row = _make_theme_row()
    del row["governance_status"], row["source_run_id"], row["macro_thesis_id"]
    conn = _make_conn(fetchrow_returns=[row])
    theme = await svc.get_theme(conn, "big-4-banks")
    assert theme is not None
    assert theme.governance_status == "approved"
    assert theme.source_run_id is None
    assert theme.macro_thesis_id is None


async def test_row_to_theme_holding_defaults_governance_status_when_absent() -> None:
    row = _make_holding_row()
    del row["governance_status"], row["source_run_id"], row["holding_id"]
    conn = _make_conn(fetch_returns=[[row]])
    holdings = await svc.list_theme_holdings(conn, "big-4-banks")
    assert holdings[0].governance_status == "approved"
    assert holdings[0].holding_id is None


# ---------------------------------------------------------------------------
# get_coverage_rollup — universe -> segment coverage (thesis-coverage-
# framework-2026-07-11.md Tier 1a)
# ---------------------------------------------------------------------------

def _make_coverage_row(
    security_kind: str = "au_equity",
    sector: str | None = "Financial Services",
    symbol_count: int = 193,
    theme_covered_count: int = 4,
    thesis_covered_count: int = 1,
) -> dict:
    return {
        "security_kind": security_kind,
        "sector": sector,
        "symbol_count": symbol_count,
        "theme_covered_count": theme_covered_count,
        "thesis_covered_count": thesis_covered_count,
    }


async def test_get_coverage_rollup_maps_rows_to_coverage_segments() -> None:
    rows = [
        _make_coverage_row(security_kind="au_equity", sector="Basic Materials",
                            symbol_count=779, theme_covered_count=0, thesis_covered_count=0),
        _make_coverage_row(security_kind="au_equity", sector="Financial Services",
                            symbol_count=193, theme_covered_count=1, thesis_covered_count=1),
        _make_coverage_row(security_kind="etf", sector=None,
                            symbol_count=471, theme_covered_count=0, thesis_covered_count=0),
    ]
    conn = _make_conn(fetch_returns=[rows])
    segments = await svc.get_coverage_rollup(conn)

    assert len(segments) == 3
    assert segments[0].security_kind == "au_equity"
    assert segments[0].sector == "Basic Materials"
    assert segments[0].symbol_count == 779
    assert segments[0].theme_covered_count == 0
    # Non-equity kinds report sector=None, matching universe.security_kind != 'au_equity'.
    assert segments[2].security_kind == "etf"
    assert segments[2].sector is None
    assert segments[2].symbol_count == 471


async def test_get_coverage_rollup_empty_universe_returns_empty_list() -> None:
    conn = _make_conn(fetch_returns=[[]])
    segments = await svc.get_coverage_rollup(conn)
    assert segments == []
