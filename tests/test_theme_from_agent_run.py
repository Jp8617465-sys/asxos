"""Tests for the theme/theme_holding --from-agent-run paths — Phase 2c lane.

Mirrors tests/test_macro_theses_service.py's mocked-conn approach (no real
DB). The live-trigger statement ORDER is pinned by
tests/test_governance_transitions.py for the shared helper; these tests pin
the theme-specific behavior around it: explicit governance_status='draft' on
INSERT (themes/theme_holdings DEFAULT to 'approved', unlike macro_theses),
the theme_code resolution requirement, and the no-overwrite fail-loud rule.

asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from asxos.domain.themes import service as svc

_NOW = datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC)

_THEME_PROPOSAL = {
    "theme_code": "grid-transmission-buildout",
    "name": "Grid transmission buildout",
    "description": "Transmission capex cycle driven by renewables connection queues.",
    "conviction_band": "medium",
    "stage": "early",
    "macro_thesis_id": None,
    "evidence_citation_ids": [11, 12],
}

_HOLDING_PROPOSAL = {
    "theme_code": "grid-transmission-buildout",
    "symbol": "XYZ.AU",
    # JSON number on purpose: exercises the parse_float=Decimal path
    # (theses/schemas.py's documented deserialisation hazard).
    "exposure_strength": 0.6,
    "direction": "positive",
    "mechanism_text": "Revenue is ~70% regulated transmission capex passthrough.",
    "evidence_citation_ids": [13],
}


def _make_agent_run_row(
    run_id: int = 42,
    acted_on: bool = False,
    object_type: str = "theme",
    proposal: dict | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "acted_on": acted_on,
        "object_type": object_type,
        "proposed_object": json.dumps(
            proposal if proposal is not None
            else (_THEME_PROPOSAL if object_type == "theme" else _HOLDING_PROPOSAL)
        ),
    }


def _make_theme_row(theme_id: int = 9, governance_status: str = "draft") -> dict:
    return {
        "theme_id": theme_id,
        "theme_code": "grid-transmission-buildout",
        "name": "Grid transmission buildout",
        "description": "Transmission capex cycle driven by renewables connection queues.",
        "conviction_band": "medium",
        "stage": "early",
        "stage_suggested": None,
        "adjacent_codes": [],
        "started_at": date(2026, 7, 16),
        "retired_at": None,
        "last_reviewed_at": _NOW,
        "macro_thesis_id": None,
        "governance_status": governance_status,
        "source_run_id": 42,
    }


def _make_holding_row(holding_id: int = 31, governance_status: str = "draft") -> dict:
    return {
        "theme_id": 9,
        "symbol": "XYZ.AU",
        "exposure_strength": Decimal("0.6"),
        "direction": "positive",
        "mechanism_text": "Revenue is ~70% regulated transmission capex passthrough.",
        "source": "llm_inferred",
        "last_validated_at": _NOW,
        "note": None,
        "created_at": _NOW,
        "holding_id": holding_id,
        "governance_status": governance_status,
        "source_run_id": 42,
    }


class _RecordingConn:
    """Mock conn that records every fetchrow/execute call with its SQL."""

    def __init__(self, fetchrow_returns: list) -> None:
        self._fetchrow_returns = iter(fetchrow_returns)
        self.fetchrow_calls: list[tuple] = []
        self.execute = AsyncMock(return_value=None)

        @asynccontextmanager
        async def _tx():
            yield

        self.transaction = _tx

    async def fetchrow(self, query: str, *args):
        self.fetchrow_calls.append((query, *args))
        return next(self._fetchrow_returns, None)


# ---------------------------------------------------------------------------
# create_theme_from_agent_run
# ---------------------------------------------------------------------------

async def test_create_theme_from_agent_run_happy_path() -> None:
    conn = _RecordingConn(
        fetchrow_returns=[
            _make_agent_run_row(),                                # agent_runs FOR UPDATE
            None,                                                 # theme_code duplicate check
            _make_theme_row(governance_status="draft"),           # INSERT themes
            _make_theme_row(governance_status="evidence_complete"),  # transition 1
            _make_theme_row(governance_status="pending_review"),  # transition 2
        ]
    )
    theme = await svc.create_theme_from_agent_run(conn, 42)
    assert theme.governance_status == "pending_review"
    assert theme.theme_code == "grid-transmission-buildout"

    # The INSERT must set governance_status explicitly — themes DEFAULTs to
    # 'approved' (migration 0035 grandfather), so relying on the default
    # would silently bypass the review gate. And never an upsert.
    insert_call = next(c for c in conn.fetchrow_calls if "INSERT INTO themes" in c[0])
    assert "'draft'" in insert_call[0]
    assert "ON CONFLICT" not in insert_call[0]

    # 2 governance_events INSERTs + 1 agent_runs acted_on UPDATE.
    assert conn.execute.await_count == 3
    gov = [c for c in conn.execute.await_args_list if "governance_events" in c.args[0]]
    assert len(gov) == 2
    assert gov[0].args[1:] == ("theme", 9, "draft", "evidence_complete", "Draft created from agent run", "agent")
    assert gov[1].args[1:] == ("theme", 9, "evidence_complete", "pending_review", "Draft created from agent run", "agent")
    acted = [c for c in conn.execute.await_args_list if "acted_on" in c.args[0]]
    assert acted[0].args[1:] == (9, 42)


async def test_create_theme_from_agent_run_not_found_raises() -> None:
    conn = _RecordingConn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.create_theme_from_agent_run(conn, 999)


async def test_create_theme_from_agent_run_already_acted_on_raises() -> None:
    conn = _RecordingConn(fetchrow_returns=[_make_agent_run_row(acted_on=True)])
    with pytest.raises(ValueError, match="already acted on"):
        await svc.create_theme_from_agent_run(conn, 42)


async def test_create_theme_from_agent_run_duplicate_theme_code_raises() -> None:
    conn = _RecordingConn(
        fetchrow_returns=[
            _make_agent_run_row(),
            {"theme_id": 3},  # theme_code already exists
        ]
    )
    with pytest.raises(ValueError, match="already exists"):
        await svc.create_theme_from_agent_run(conn, 42)


async def test_create_theme_from_agent_run_wrong_object_type_raises() -> None:
    conn = _RecordingConn(fetchrow_returns=[_make_agent_run_row(object_type="macro_thesis")])
    with pytest.raises(ValueError, match="object_type='macro_thesis'"):
        await svc.create_theme_from_agent_run(conn, 42)


# ---------------------------------------------------------------------------
# create_theme_holding_from_agent_run
# ---------------------------------------------------------------------------

async def test_create_theme_holding_from_agent_run_happy_path() -> None:
    conn = _RecordingConn(
        fetchrow_returns=[
            _make_agent_run_row(object_type="theme_holding"),     # agent_runs FOR UPDATE
            {"theme_id": 9},                                      # theme_code resolution
            None,                                                 # existing-exposure check
            _make_holding_row(governance_status="draft"),         # INSERT theme_holdings
            _make_holding_row(governance_status="evidence_complete"),  # transition 1
            _make_holding_row(governance_status="pending_review"),     # transition 2
        ]
    )
    holding = await svc.create_theme_holding_from_agent_run(conn, 42)
    assert holding.governance_status == "pending_review"
    assert holding.source == "llm_inferred"
    # Decimal survived the JSON round-trip (parse_float=Decimal, rule #5) —
    # asserted on the recorded INSERT ARGUMENT (the value that actually flowed
    # through json.loads → ThemeHoldingProposal), not the mocked RETURNING row,
    # which would pass regardless of whether parse_float ran.
    holding_insert = next(
        c for c in conn.fetchrow_calls if "INSERT INTO theme_holdings" in c[0]
    )
    assert holding_insert[3] == Decimal("0.6")
    assert isinstance(holding_insert[3], Decimal)

    insert_call = next(c for c in conn.fetchrow_calls if "INSERT INTO theme_holdings" in c[0])
    assert "'draft'" in insert_call[0]
    assert "'llm_inferred'" in insert_call[0]
    # Never an upsert — silent overwrite of reviewed content is the bug.
    assert "ON CONFLICT" not in insert_call[0]

    gov = [c for c in conn.execute.await_args_list if "governance_events" in c.args[0]]
    assert len(gov) == 2
    assert gov[0].args[1:] == ("theme_holding", 31, "draft", "evidence_complete", "Draft created from agent run", "agent")
    assert gov[1].args[1:] == ("theme_holding", 31, "evidence_complete", "pending_review", "Draft created from agent run", "agent")
    acted = [c for c in conn.execute.await_args_list if "acted_on" in c.args[0]]
    assert acted[0].args[1:] == (31, 42)


async def test_create_theme_holding_unresolved_theme_code_raises() -> None:
    conn = _RecordingConn(
        fetchrow_returns=[
            _make_agent_run_row(object_type="theme_holding"),
            None,  # theme_code does not resolve
        ]
    )
    with pytest.raises(ValueError, match="does not resolve"):
        await svc.create_theme_holding_from_agent_run(conn, 42)


async def test_create_theme_holding_existing_exposure_raises() -> None:
    conn = _RecordingConn(
        fetchrow_returns=[
            _make_agent_run_row(object_type="theme_holding"),
            {"theme_id": 9},
            {"holding_id": 5},  # (theme, symbol) already covered
        ]
    )
    with pytest.raises(ValueError, match="re-proposed covered"):
        await svc.create_theme_holding_from_agent_run(conn, 42)


async def test_create_theme_holding_wrong_object_type_raises() -> None:
    conn = _RecordingConn(fetchrow_returns=[_make_agent_run_row(object_type="theme")])
    with pytest.raises(ValueError, match="object_type='theme'"):
        await svc.create_theme_holding_from_agent_run(conn, 42)
