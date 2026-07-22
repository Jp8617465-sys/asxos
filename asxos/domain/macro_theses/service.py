"""Macro-thesis domain service — Phase 2a/2b.

Unlike asxos/domain/theses/service.py::create_thesis_from_agent_run() (a
permanently-unreachable Phase 1 stub — no ThesisProposal schema exists),
create_macro_thesis_from_agent_run() below is real and reachable:
MacroThesisProposal has existed since Phase 1 (asxos/domain/theses/schemas.py).

DEFERRED (m14_candidate_macro_thesis_evidence_staleness_check): approve_object()
below does not check evidence staleness before approval, unlike
theses/service.py::approve_object(). theses' check queries thesis_evidence
directly (a table with a thesis_id FK); macro_theses has no equivalent direct
FK from agent_evidence — its evidence link is indirect
(macro_theses.source_run_id -> agent_runs.proposed_object.evidence_citation_ids
-> agent_evidence.evidence_id). Implementing that join-based staleness check
is real but more involved than this phase's scope; land it when a second
evidence-heavy discovery agent (Phase 2c) makes the pattern worth generalising,
not as an isolated addition here.

References:
  migrations/0035_macro_theses_and_governance_columns.sql
  migrations/0036_phase2_governance_audit_triggers.sql
  docs/proposals/governance-first-architecture-2026-06-30.md Section 5.5
  CLAUDE.md non-negotiables #1, #5, #10
"""
from __future__ import annotations

import json
from decimal import Decimal

import asyncpg

from asxos.domain.governance import transitions as governance_transitions
from asxos.domain.governance.agent_run_guards import load_unacted_run, mark_run_acted
from asxos.domain.macro_theses.types import MacroThesis
from asxos.domain.theses.schemas import MacroThesisProposal

_REJECTABLE_FROM = {"draft", "evidence_complete", "pending_review"}


def _row_to_macro_thesis(row: asyncpg.Record) -> MacroThesis:
    """Convert an asyncpg Record from the macro_theses table to a MacroThesis
    dataclass. data_signals round-trips as JSONB text (no asyncpg codec is
    registered) — matching theses/service.py::_row_to_thesis()'s identical
    handling of invalidation_conditions."""
    raw_signals = row["data_signals"]
    if isinstance(raw_signals, str):
        raw_signals = json.loads(raw_signals)
    # machine_conditions (migration 0041) round-trips as JSONB text, same as
    # data_signals. .get() (not [...]) so a pre-0041 row shape — including the
    # mocked rows in tests that predate the column — reads as None rather than
    # KeyError; both dict and asyncpg.Record support .get().
    raw_machine = row.get("machine_conditions")
    if isinstance(raw_machine, str):
        raw_machine = json.loads(raw_machine)
    return MacroThesis(
        macro_thesis_id=row["macro_thesis_id"],
        title=row["title"],
        thesis_text=row["thesis_text"],
        regime_quadrant=row["regime_quadrant"],
        horizon_months=row["horizon_months"],
        catalyst=row["catalyst"],
        falsifier=row["falsifier"],
        data_signals=tuple(raw_signals or []),
        source_run_id=row["source_run_id"],
        governance_status=row["governance_status"],
        created_at=row["created_at"],
        retired_at=row["retired_at"],
        machine_conditions=raw_machine,
    )


async def _apply_governance_transition(
    conn: asyncpg.Connection,
    macro_thesis_id: int,
    *,
    from_status: str,
    to_status: str,
    reasoning: str,
    actor: str = "human",
) -> asyncpg.Record:
    """Thin macro_theses-specific wrapper over the shared
    asxos.domain.governance.transitions.apply_governance_transition() — same
    convention as theses/service.py::_apply_governance_transition(), applied
    here because all four call sites below repeat the identical
    table_name="macro_theses"/id_column="macro_thesis_id"/object_type=
    "macro_thesis" triple.
    """
    return await governance_transitions.apply_governance_transition(
        conn,
        table_name="macro_theses",
        id_column="macro_thesis_id",
        object_type="macro_thesis",
        object_id=macro_thesis_id,
        from_status=from_status,
        to_status=to_status,
        reasoning=reasoning,
        actor=actor,
    )


async def get_macro_thesis(conn: asyncpg.Connection, macro_thesis_id: int) -> MacroThesis | None:
    """Fetch a macro thesis by ID. Returns None if not found."""
    row = await conn.fetchrow(
        "SELECT * FROM macro_theses WHERE macro_thesis_id = $1", macro_thesis_id
    )
    return _row_to_macro_thesis(row) if row else None


async def list_macro_theses(conn: asyncpg.Connection) -> list[MacroThesis]:
    """List all macro theses, most recent first."""
    rows = await conn.fetch("SELECT * FROM macro_theses ORDER BY created_at DESC")
    return [_row_to_macro_thesis(r) for r in rows]


async def create_macro_thesis_from_agent_run(
    conn: asyncpg.Connection,
    run_id: int,
    *,
    reasoning: str = "Draft created from agent run",
) -> MacroThesis:
    """Validate agent_runs.proposed_object against MacroThesisProposal and
    insert a macro_theses row, then advance draft -> evidence_complete ->
    pending_review in the SAME transaction.

    proposed_object round-trips as JSONB text (no asyncpg codec is
    registered — asxos/db.py) — parsed here with parse_float=Decimal per
    schemas.py's documented hazard, matching every other JSONB-proposal
    reader in this codebase. Re-validating against MacroThesisProposal here
    (rather than trusting the shape blindly) is cheap — no DB round-trip
    needed for Pydantic's own field validators — and catches any drift
    between what was logged and what's read back.

    evidence_citation_ids' tier/existence check already ran once at log time
    (asxos/domain/governance/agent_run_service.py::log_agent_run()) — not
    repeated here, since agent_evidence rows are append-only/immutable
    (never overwritten after insert; superseded_at marks retirement, not
    mutation) and nothing between log time and here could invalidate that
    check.

    The two auto-advance transitions are logged with actor='agent' (not the
    default 'human') — this is a mechanical advance following directly from
    the proposal's own evidence-citation guarantee, not a human decision;
    approve_object()/reject_object() below are where a human decision is
    actually recorded.

    Raises ValueError if:
      - run_id does not exist in agent_runs
      - the agent_runs row was already acted_on
      - object_type != 'macro_thesis'
    """
    async with conn.transaction():
        run = await load_unacted_run(
            conn,
            run_id,
            object_type="macro_thesis",
            fn_name="create_macro_thesis_from_agent_run",
        )

        proposal_dict = json.loads(run["proposed_object"], parse_float=Decimal)
        proposal = MacroThesisProposal(**proposal_dict)

        row = await conn.fetchrow(
            """
            INSERT INTO macro_theses
                (title, thesis_text, regime_quadrant, horizon_months, catalyst,
                 falsifier, data_signals, source_run_id, machine_conditions)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9::jsonb)
            RETURNING *
            """,
            proposal.title,
            proposal.thesis_text,
            proposal.regime_quadrant,
            proposal.horizon_months,
            proposal.catalyst,
            proposal.falsifier,
            json.dumps(proposal.data_signals),
            run_id,
            # model_dump_json() (not json.dumps) so Decimal thresholds serialise
            # as JSON strings, never lossy floats (CLAUDE.md #5). NULL when the
            # proposal carries only free-text catalyst/falsifier.
            proposal.machine_conditions.model_dump_json()
            if proposal.machine_conditions is not None
            else None,
        )
        macro_thesis_id = row["macro_thesis_id"]

        await _apply_governance_transition(
            conn, macro_thesis_id,
            from_status="draft",
            to_status="evidence_complete",
            reasoning=reasoning,
            actor="agent",
        )
        row = await _apply_governance_transition(
            conn, macro_thesis_id,
            from_status="evidence_complete",
            to_status="pending_review",
            reasoning=reasoning,
            actor="agent",
        )

        await mark_run_acted(conn, run_id, macro_thesis_id)

        return _row_to_macro_thesis(row)


async def approve_object(
    conn: asyncpg.Connection, macro_thesis_id: int, *, reasoning: str
) -> MacroThesis:
    """Transition a macro thesis from pending_review to approved.

    See this module's docstring for why there is no evidence-staleness
    check here (m14_candidate_macro_thesis_evidence_staleness_check).
    """
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM macro_theses WHERE macro_thesis_id = $1 FOR UPDATE",
            macro_thesis_id,
        )
        if existing is None:
            raise ValueError(f"Macro thesis {macro_thesis_id} not found")
        if existing["governance_status"] != "pending_review":
            raise ValueError(
                f"Cannot approve macro thesis {macro_thesis_id} — governance_status "
                f"is {existing['governance_status']!r}, expected 'pending_review'."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to approve a macro thesis")

        row = await _apply_governance_transition(
            conn, macro_thesis_id,
            from_status=existing["governance_status"],
            to_status="approved",
            reasoning=reasoning,
        )
        return _row_to_macro_thesis(row)


async def reject_object(
    conn: asyncpg.Connection, macro_thesis_id: int, *, reasoning: str
) -> MacroThesis:
    """Transition a macro thesis from draft/evidence_complete/pending_review
    to rejected."""
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM macro_theses WHERE macro_thesis_id = $1 FOR UPDATE",
            macro_thesis_id,
        )
        if existing is None:
            raise ValueError(f"Macro thesis {macro_thesis_id} not found")
        if existing["governance_status"] not in _REJECTABLE_FROM:
            raise ValueError(
                f"Cannot reject macro thesis {macro_thesis_id} — governance_status "
                f"is {existing['governance_status']!r}, expected one of "
                f"{sorted(_REJECTABLE_FROM)}."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to reject a macro thesis")

        row = await _apply_governance_transition(
            conn, macro_thesis_id,
            from_status=existing["governance_status"],
            to_status="rejected",
            reasoning=reasoning,
        )
        return _row_to_macro_thesis(row)
