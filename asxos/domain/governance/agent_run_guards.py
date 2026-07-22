"""Shared agent_runs guard preamble — 07-18 audit P2 extraction.

Every ``create_<object>_from_agent_run()`` service function opens with the
identical four-step preamble (SELECT ... FOR UPDATE, not-found check,
acted_on check, object_type check) and closes by flipping ``acted_on``.
That shape existed in three live copies (macro_theses ×1, themes ×2) —
past the point copy-paste is cheaper than the abstraction, same threshold
call as ``transitions.apply_governance_transition()``.

Deliberately NOT absorbed here:
- ``theses/service.py::create_thesis_from_agent_run()`` — a documented,
  unreachable-by-design Phase 1 stub (m14_candidate_agentic_thesis_drafter);
  its inline preamble + explanatory raise are the documentation. Phase E
  rebuilds it on this helper.
- ``agent_run_service.py::log_agent_run()`` — the *write* side; it has no
  preamble (nothing exists to load yet).

Both helpers assume the caller already holds ``conn.transaction()`` — the
FOR UPDATE lock and the acted_on flip must share the caller's transaction
with the governed-row INSERT and the governance transitions, exactly as the
inline versions did.
"""
from __future__ import annotations

import asyncpg


async def load_unacted_run(
    conn: asyncpg.Connection, run_id: int, *, object_type: str, fn_name: str
) -> asyncpg.Record:
    """SELECT the agent_runs row FOR UPDATE and run the three guard checks.

    Raises ValueError (messages preserve the fragments the existing tests
    pin: "not found", "already acted on", "object_type=...") if the row is
    missing, already acted on, or carries a different object_type.
    """
    run = await conn.fetchrow(
        "SELECT * FROM agent_runs WHERE run_id = $1 FOR UPDATE", run_id
    )
    if run is None:
        raise ValueError(f"agent_runs row {run_id} not found")
    if run["acted_on"]:
        raise ValueError(f"agent_runs row {run_id} was already acted on")
    if run["object_type"] != object_type:
        raise ValueError(
            f"agent_runs row {run_id} has object_type={run['object_type']!r} "
            f"— {fn_name}() only accepts object_type={object_type!r} rows."
        )
    return run


async def mark_run_acted(
    conn: asyncpg.Connection, run_id: int, resulting_object_id: int
) -> None:
    """Flip acted_on and record the created row's PK — the closing half of
    every from-agent-run function, inside the caller's transaction."""
    await conn.execute(
        "UPDATE agent_runs SET acted_on = TRUE, resulting_object_id = $1 WHERE run_id = $2",
        resulting_object_id,
        run_id,
    )
