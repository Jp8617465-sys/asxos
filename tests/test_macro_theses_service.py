"""Tests for asxos/domain/macro_theses/service.py — Phase 2b.

Mocks asyncpg connections; no real DB required.
asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.macro_theses import service as svc

_NOW = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)

_PROPOSAL = {
    "title": "Risk-off regime persists",
    "thesis_text": "Elevated vol and soft iron ore point to a defensive tilt.",
    "regime_quadrant": "falling_growth_falling_inflation",
    "horizon_months": 6,
    "catalyst": "RBA pause",
    "falsifier": "AVIX below 15 for 5 sessions",
    "data_signals": ["avix", "iron_ore_62fe"],
    "evidence_citation_ids": [1, 2],
}


def _make_macro_thesis_row(
    macro_thesis_id: int = 7,
    governance_status: str = "draft",
    source_run_id: int | None = 42,
) -> dict:
    return {
        "macro_thesis_id": macro_thesis_id,
        "title": "Risk-off regime persists",
        "thesis_text": "Elevated vol and soft iron ore point to a defensive tilt.",
        "regime_quadrant": "falling_growth_falling_inflation",
        "horizon_months": 6,
        "catalyst": "RBA pause",
        "falsifier": "AVIX below 15 for 5 sessions",
        "data_signals": "[\"avix\", \"iron_ore_62fe\"]",
        "source_run_id": source_run_id,
        "governance_status": governance_status,
        "created_at": _NOW,
        "retired_at": None,
    }


def _make_agent_run_row(
    run_id: int = 42,
    acted_on: bool = False,
    object_type: str = "macro_thesis",
) -> dict:
    return {
        "run_id": run_id,
        "acted_on": acted_on,
        "object_type": object_type,
        "proposed_object": json.dumps(_PROPOSAL),
    }


def _make_conn(fetchrow_returns: list | None = None, fetch_returns: list | None = None) -> MagicMock:
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
# get_macro_thesis / list_macro_theses
# ---------------------------------------------------------------------------

async def test_get_macro_thesis_found() -> None:
    conn = _make_conn(fetchrow_returns=[_make_macro_thesis_row()])
    mt = await svc.get_macro_thesis(conn, 7)
    assert mt is not None
    assert mt.macro_thesis_id == 7
    assert mt.data_signals == ("avix", "iron_ore_62fe")


async def test_get_macro_thesis_not_found() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    mt = await svc.get_macro_thesis(conn, 999)
    assert mt is None


async def test_list_macro_theses() -> None:
    conn = _make_conn(fetch_returns=[[_make_macro_thesis_row(), _make_macro_thesis_row(macro_thesis_id=8)]])
    theses = await svc.list_macro_theses(conn)
    assert len(theses) == 2
    assert {t.macro_thesis_id for t in theses} == {7, 8}


# ---------------------------------------------------------------------------
# create_macro_thesis_from_agent_run
# ---------------------------------------------------------------------------

async def test_create_macro_thesis_from_agent_run_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_agent_run_row(),  # SELECT agent_runs FOR UPDATE
            _make_macro_thesis_row(governance_status="draft"),  # INSERT macro_theses
            _make_macro_thesis_row(governance_status="evidence_complete"),  # transition 1 UPDATE
            _make_macro_thesis_row(governance_status="pending_review"),  # transition 2 UPDATE
        ]
    )
    mt = await svc.create_macro_thesis_from_agent_run(conn, 42)
    assert mt.governance_status == "pending_review"

    # Exactly 2 additional governance_events INSERTs (the two auto-advance
    # hops) + 1 agent_runs UPDATE — 3 execute() calls total.
    assert conn.execute.await_count == 3
    gov_calls = [c for c in conn.execute.await_args_list if "governance_events" in c.args[0]]
    assert len(gov_calls) == 2
    assert gov_calls[0].args[1:] == ("macro_thesis", 7, "draft", "evidence_complete", "Draft created from agent run", "agent")
    assert gov_calls[1].args[1:] == ("macro_thesis", 7, "evidence_complete", "pending_review", "Draft created from agent run", "agent")

    agent_run_update = [c for c in conn.execute.await_args_list if "agent_runs" in c.args[0]]
    assert len(agent_run_update) == 1
    assert agent_run_update[0].args[1:] == (7, 42)


async def test_create_macro_thesis_from_agent_run_not_found_raises() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.create_macro_thesis_from_agent_run(conn, 999)


async def test_create_macro_thesis_from_agent_run_already_acted_on_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_agent_run_row(acted_on=True)])
    with pytest.raises(ValueError, match="already acted on"):
        await svc.create_macro_thesis_from_agent_run(conn, 42)


async def test_create_macro_thesis_from_agent_run_wrong_object_type_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_agent_run_row(object_type="theme")])
    with pytest.raises(ValueError, match="object_type='theme'"):
        await svc.create_macro_thesis_from_agent_run(conn, 42)


# ---------------------------------------------------------------------------
# approve_object / reject_object
# ---------------------------------------------------------------------------

async def test_approve_object_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_macro_thesis_row(governance_status="pending_review"),
            _make_macro_thesis_row(governance_status="approved"),
        ]
    )
    mt = await svc.approve_object(conn, 7, reasoning="Evidence checks out")
    assert mt.governance_status == "approved"
    gov_calls = [c for c in conn.execute.await_args_list if "governance_events" in c.args[0]]
    assert len(gov_calls) == 1
    assert gov_calls[0].args[1:] == ("macro_thesis", 7, "pending_review", "approved", "Evidence checks out", "human")


async def test_approve_object_wrong_status_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_macro_thesis_row(governance_status="draft")])
    with pytest.raises(ValueError, match="expected 'pending_review'"):
        await svc.approve_object(conn, 7, reasoning="x")


async def test_approve_object_empty_reasoning_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_macro_thesis_row(governance_status="pending_review")])
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.approve_object(conn, 7, reasoning="   ")


async def test_approve_object_not_found_raises() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.approve_object(conn, 999, reasoning="x")


async def test_reject_object_happy_path() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_macro_thesis_row(governance_status="pending_review"),
            _make_macro_thesis_row(governance_status="rejected"),
        ]
    )
    mt = await svc.reject_object(conn, 7, reasoning="Not convincing")
    assert mt.governance_status == "rejected"


async def test_reject_object_from_draft_succeeds() -> None:
    conn = _make_conn(
        fetchrow_returns=[
            _make_macro_thesis_row(governance_status="draft"),
            _make_macro_thesis_row(governance_status="rejected"),
        ]
    )
    mt = await svc.reject_object(conn, 7, reasoning="Duplicate of an existing thesis")
    assert mt.governance_status == "rejected"


async def test_reject_object_already_approved_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_macro_thesis_row(governance_status="approved")])
    with pytest.raises(ValueError, match="expected one of"):
        await svc.reject_object(conn, 7, reasoning="x")


async def test_reject_object_empty_reasoning_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_macro_thesis_row(governance_status="draft")])
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.reject_object(conn, 7, reasoning="")


# ---------------------------------------------------------------------------
# Phase 2b done-criteria: full draft -> pending_review -> approved cycle
# ---------------------------------------------------------------------------

async def test_phase2b_done_criteria_agent_run_to_approved_end_to_end() -> None:
    """Mirrors Phase 1's own synthetic done-criteria test: drive a real
    agent_runs row through create_macro_thesis_from_agent_run() then
    approve_object(), proving the state machine end-to-end."""
    conn = _make_conn(
        fetchrow_returns=[
            _make_agent_run_row(),
            _make_macro_thesis_row(governance_status="draft"),
            _make_macro_thesis_row(governance_status="evidence_complete"),
            _make_macro_thesis_row(governance_status="pending_review"),
        ]
    )
    mt = await svc.create_macro_thesis_from_agent_run(conn, 42)
    assert mt.governance_status == "pending_review"

    conn2 = _make_conn(
        fetchrow_returns=[
            _make_macro_thesis_row(governance_status="pending_review"),
            _make_macro_thesis_row(governance_status="approved"),
        ]
    )
    approved = await svc.approve_object(conn2, mt.macro_thesis_id, reasoning="Reviewed the evidence, sound thesis")
    assert approved.governance_status == "approved"
