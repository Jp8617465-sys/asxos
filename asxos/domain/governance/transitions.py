"""Shared governance-transition helper — Phase 2a extraction from
asxos/domain/theses/service.py::_apply_governance_transition (Phase 1).

One governance_events INSERT + one UPDATE, IN THAT ORDER, inside the
caller's existing transaction. Every per-table audit trigger (migration 0034
for theses; migration 0036 for macro_theses/themes/theme_holdings) is a
BEFORE UPDATE trigger — it runs its EXISTS check synchronously at the moment
the UPDATE statement executes, so the matching governance_events row MUST
already be written within the same transaction before the UPDATE runs, not
after. See docs/proposals/governance-first-architecture-2026-06-30.md
Section 4.7.

BUG FOUND DURING PHASE 2A LIVE VERIFICATION (fixed here): this function
originally did UPDATE-then-INSERT, inherited unchanged from Phase 1's
inline _apply_governance_transition() in theses/service.py. That order is
fundamentally incompatible with a BEFORE UPDATE trigger — confirmed live
against Supabase (`UPDATE themes SET governance_status=... ; INSERT INTO
governance_events ...` in that order, same transaction, correctly raised the
trigger's rejection, since at UPDATE time the audit row didn't exist yet).
This means Phase 1's asx thesis approve/reject would have failed against the
live trigger despite passing every mocked unit test — mocked connections
don't enforce real Postgres trigger semantics, and Phase 1's own manual
live-DB verification tested hand-written SQL in the correct order, never the
actual Python call path. Swapping to INSERT-then-UPDATE here retroactively
fixes theses/service.py's wrapper too (it now calls through this function).

Extracted now rather than left as four copies: the shape (once corrected)
hasn't needed to change since, and it is now used by theses/themes/
theme_holdings/macro_theses — four call sites of an unchanging pattern is
past the point copy-paste is cheaper than the abstraction.
"""
from __future__ import annotations

import asyncpg


async def apply_governance_transition(
    conn: asyncpg.Connection,
    *,
    table_name: str,
    id_column: str,
    object_type: str,
    object_id: int,
    from_status: str,
    to_status: str,
    reasoning: str,
    actor: str = "human",
) -> asyncpg.Record:
    """INSERT the governance_events row, THEN UPDATE <table_name>.governance_status
    — this order is load-bearing (see module docstring): the per-table audit
    trigger is BEFORE UPDATE and checks for the governance_events row's
    existence synchronously when the UPDATE fires, so the INSERT must already
    be visible within this transaction first.

    table_name/id_column are f-string-interpolated, not $N-bound — Postgres
    identifiers can't be parameterised. Every call site passes a hardcoded
    literal (e.g. table_name="theses", id_column="thesis_id"), never a
    caller-supplied string — the same trust boundary this codebase already
    applies to REVISABLE_FIELDS-looked-up column names in
    theses/service.py::revise_thesis(). Do not call this with a table_name/
    id_column derived from external input.

    Returns the updated row so callers can pass it straight to their own
    _row_to_<Thing>() constructor.
    """
    await conn.execute(
        """
        INSERT INTO governance_events
            (object_type, object_id, from_status, to_status, reasoning, actor)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        object_type,
        object_id,
        from_status,
        to_status,
        reasoning,
        actor,
    )
    row = await conn.fetchrow(
        f"""
        UPDATE {table_name}
        SET governance_status = $1
        WHERE {id_column} = $2
        RETURNING *
        """,
        to_status,
        object_id,
    )
    return row
