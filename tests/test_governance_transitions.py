"""Tests for asxos/domain/governance/transitions.py — Phase 2a.

Mocks asyncpg connections; no real DB required.
asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.

Note on why call ORDER gets its own dedicated assertion here (not just "both
calls happened"): a mocked connection cannot enforce real Postgres trigger
semantics, so a test that only checks call *content* (not relative order)
would have passed even with the original, live-broken UPDATE-then-INSERT
implementation — exactly what happened during this phase's own
implementation (see transitions.py's module docstring for the full account,
confirmed live against Supabase: a BEFORE UPDATE trigger's EXISTS check runs
synchronously at UPDATE time, so the governance_events INSERT MUST be
visible in the same transaction before the UPDATE fires, not after). The
`_make_conn` helper below logs execute()/fetchrow() calls into ONE shared
ordered list specifically so order can be asserted, not just content.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from asxos.domain.governance import transitions as svc


def _make_conn(update_row: dict) -> MagicMock:
    """A single shared, ordered call log across both execute() and
    fetchrow() — critical for asserting INSERT-before-UPDATE order, which a
    per-method call list can't express."""
    conn = MagicMock()
    calls: list[tuple[str, str, tuple]] = []  # (method, query, args)

    async def _fetchrow(q, *args):
        calls.append(("fetchrow", q, args))
        return update_row

    async def _execute(q, *args):
        calls.append(("execute", q, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute
    conn._calls = calls
    return conn


async def test_apply_governance_transition_insert_before_update_order() -> None:
    """Load-bearing order, confirmed live against Supabase: the per-table
    audit trigger is BEFORE UPDATE and checks for the governance_events row
    synchronously when the UPDATE fires — INSERT must happen first, in the
    same transaction, or the trigger rejects the UPDATE. Getting this
    backwards is exactly the bug this test now pins (see module docstring
    and transitions.py's own docstring for the incident this test replaces)."""
    row = {"thesis_id": 1, "governance_status": "approved"}
    conn = _make_conn(row)

    result = await svc.apply_governance_transition(
        conn,
        table_name="theses",
        id_column="thesis_id",
        object_type="thesis",
        object_id=1,
        from_status="pending_review",
        to_status="approved",
        reasoning="Evidence checks out",
    )

    assert result == row
    assert len(conn._calls) == 2
    first_method, first_query, first_args = conn._calls[0]
    second_method, second_query, _ = conn._calls[1]

    assert first_method == "execute"
    assert "INSERT INTO governance_events" in first_query
    assert first_args == ("thesis", 1, "pending_review", "approved", "Evidence checks out", "human")

    assert second_method == "fetchrow"
    assert "UPDATE theses" in second_query


async def test_apply_governance_transition_table_name_and_id_column_interpolated() -> None:
    """table_name/id_column are f-string-interpolated into the UPDATE (Postgres
    identifiers can't be $N-bound) — confirm each governed table's own name/PK
    ends up in the actual SQL text, not left as a literal 'theses'."""
    conn = _make_conn({"holding_id": 5, "governance_status": "approved"})

    await svc.apply_governance_transition(
        conn,
        table_name="theme_holdings",
        id_column="holding_id",
        object_type="theme_holding",
        object_id=5,
        from_status="pending_review",
        to_status="approved",
        reasoning="Approved for real",
    )

    fetchrow_query = next(q for method, q, _ in conn._calls if method == "fetchrow")
    assert "UPDATE theme_holdings" in fetchrow_query
    assert "WHERE holding_id = $2" in fetchrow_query


async def test_apply_governance_transition_default_actor_is_human() -> None:
    conn = _make_conn({"macro_thesis_id": 1, "governance_status": "rejected"})

    await svc.apply_governance_transition(
        conn,
        table_name="macro_theses",
        id_column="macro_thesis_id",
        object_type="macro_thesis",
        object_id=1,
        from_status="pending_review",
        to_status="rejected",
        reasoning="Not convincing",
    )

    _, _, args = conn._calls[0]
    assert args[-1] == "human"


async def test_apply_governance_transition_actor_override() -> None:
    """create_macro_thesis_from_agent_run()'s auto-advance transitions pass
    actor='agent' — confirm the override actually reaches the INSERT."""
    conn = _make_conn({"macro_thesis_id": 1, "governance_status": "evidence_complete"})

    await svc.apply_governance_transition(
        conn,
        table_name="macro_theses",
        id_column="macro_thesis_id",
        object_type="macro_thesis",
        object_id=1,
        from_status="draft",
        to_status="evidence_complete",
        reasoning="Draft created from agent run",
        actor="agent",
    )

    _, _, args = conn._calls[0]
    assert args[-1] == "agent"
