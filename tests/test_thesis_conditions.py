"""Tests for asxos/domain/theses/conditions.py — the 0042 condition state
machine (design §4).

Mocked asyncpg connection with an ORDERED call log (the same technique
tests/test_governance_transitions.py uses to pin statement order): every
fetchrow/fetchval/execute is recorded, and execute results are scripted so
the idempotency (events UNIQUE → 'INSERT 0 0') and lost-update ('UPDATE 0')
branches are exercised. Mocked conns don't enforce the real UNIQUE/CHECKs —
the rolled-back live replay at 0042 apply time covers that (portfolio-
conventions verification lesson).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from asxos.domain.theses import conditions as conds
from asxos.domain.theses.types import ThesisCondition

_NOW = datetime(2026, 8, 7, 10, 0, 0, tzinfo=UTC)
_PRICE_DATE = date(2026, 8, 6)


def _cond_row(**over):
    row = {
        "condition_id": 5,
        "thesis_id": 2,
        "ordinal": 1,
        "condition_text": "Price closes below $230 stop on volume",
        "trigger_semantics": "alert_review",
        "status": "active",
        "enforcement_kind": "price_below",
        "enforcement_threshold": Decimal("230.000000"),
        "enforcement_note": "will enforce: close < 230.000000.",
        "parser_version": "cp-1",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    row.update(over)
    return row


class _Conn:
    """Scripted conn with an ordered (method, query, args) call log."""

    def __init__(self, fetchrow=None, fetchval=None, execute=None, fetch=None):
        self.calls: list[tuple[str, str, tuple]] = []
        self._fetchrow = iter(fetchrow or [])
        self._fetchval = iter(fetchval or [])
        self._execute = iter(execute or [])
        self._fetch = iter(fetch or [])

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetchrow(self, q, *a):
        self.calls.append(("fetchrow", q, a))
        return next(self._fetchrow, None)

    async def fetchval(self, q, *a):
        self.calls.append(("fetchval", q, a))
        return next(self._fetchval, None)

    async def fetch(self, q, *a):
        self.calls.append(("fetch", q, a))
        return next(self._fetch, [])

    async def execute(self, q, *a):
        self.calls.append(("execute", q, a))
        # default: every write succeeds with 1 row
        return next(self._execute, "INSERT 0 1" if "INSERT" in q else "UPDATE 1")


def _execs(conn, needle):
    return [(q, a) for m, q, a in conn.calls if m == "execute" and needle in q]


# ---------------------------------------------------------------------------
# record_trigger — TR fixture core
# ---------------------------------------------------------------------------

async def test_record_trigger_writes_event_status_revision_in_order():
    conn = _Conn(fetchrow=[_cond_row(status="active")])
    applied = await conds.record_trigger(
        conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("200.00"), source="job"
    )
    assert applied is True

    event_calls = _execs(conn, "thesis_condition_events")
    status_calls = _execs(conn, "UPDATE thesis_conditions")
    revision_calls = _execs(conn, "thesis_revisions")
    assert len(event_calls) == 1 and len(status_calls) == 1 and len(revision_calls) == 1

    # Event carries the CLOSE's date (register #21), source, threshold.
    _q, args = event_calls[0]
    assert args[2] == "triggered"
    assert args[3] == _PRICE_DATE
    assert args[4] == Decimal("200.00")
    assert args[6] == "job"

    # Status guard: from-status set is in the WHERE clause.
    q, args = status_calls[0]
    assert "status = ANY($3::text[])" in q
    assert args[2] == ["active", "re_armed"]

    # Revision written same transaction, correct type.
    _q, args = revision_calls[0]
    assert args[2] == "condition_triggered"

    # Machine transitions never touch the theses table (no revisit bump).
    assert _execs(conn, "UPDATE theses") == []


async def test_record_trigger_idempotent_on_duplicate_event():
    """Events UNIQUE conflict ('INSERT 0 0') → quiet no-op: no status flip,
    no revision, returns False (re-running a historical day after later
    transitions must not rewind state)."""
    conn = _Conn(fetchrow=[_cond_row(status="re_armed")], execute=["INSERT 0 0"])
    applied = await conds.record_trigger(
        conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("200"), source="job"
    )
    assert applied is False
    assert _execs(conn, "UPDATE thesis_conditions") == []
    assert _execs(conn, "thesis_revisions") == []


async def test_record_trigger_from_status_guard_raises_on_zero_rows():
    conn = _Conn(
        fetchrow=[_cond_row(status="triggered")],
        execute=["INSERT 0 1", "UPDATE 0"],
    )
    with pytest.raises(ValueError, match="lost update guard"):
        await conds.record_trigger(
            conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("200"), source="job"
        )


async def test_record_trigger_refuses_not_machine_checkable():
    conn = _Conn(fetchrow=[_cond_row(enforcement_kind="not_machine_checkable",
                                     enforcement_threshold=None)])
    with pytest.raises(ValueError, match="not machine-checkable"):
        await conds.record_trigger(
            conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("200"), source="job"
        )


async def test_record_trigger_refuses_human_source():
    conn = _Conn()
    with pytest.raises(ValueError, match="resolve_condition"):
        await conds.record_trigger(
            conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("200"), source="human"
        )


async def test_record_trigger_condition_not_found():
    conn = _Conn(fetchrow=[None])
    with pytest.raises(ValueError, match="not found"):
        await conds.record_trigger(
            conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("200"), source="job"
        )


# ---------------------------------------------------------------------------
# record_re_arm — RB fixture core (single close, v1)
# ---------------------------------------------------------------------------

async def test_record_re_arm_from_triggered_only():
    conn = _Conn(fetchrow=[_cond_row(status="triggered")])
    applied = await conds.record_re_arm(
        conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("245"), source="job"
    )
    assert applied is True
    q, args = _execs(conn, "UPDATE thesis_conditions")[0]
    assert args[0] == "re_armed"
    assert args[2] == ["triggered"]
    _q, args = _execs(conn, "thesis_revisions")[0]
    assert args[2] == "condition_re_armed"


async def test_sweep_source_accepted_for_machine_transitions():
    conn = _Conn(fetchrow=[_cond_row(status="triggered")])
    applied = await conds.record_re_arm(
        conn, 5, price_date=_PRICE_DATE, observed_close=Decimal("245"), source="sweep"
    )
    assert applied is True
    _q, args = _execs(conn, "thesis_condition_events")[0]
    assert args[6] == "sweep"


# ---------------------------------------------------------------------------
# resolve_condition — human, terminal
# ---------------------------------------------------------------------------

async def test_resolve_requires_reasoning():
    conn = _Conn()
    with pytest.raises(ValueError, match="reasoning is required"):
        await conds.resolve_condition(conn, 5, reasoning="  ")


async def test_resolve_is_terminal():
    conn = _Conn(fetchrow=[_cond_row(status="resolved")])
    with pytest.raises(ValueError, match="already resolved"):
        await conds.resolve_condition(conn, 5, reasoning="done")


async def test_resolve_happy_path_event_is_human_with_null_close():
    conn = _Conn(fetchrow=[_cond_row(status="triggered"), _cond_row(status="resolved")])
    c = await conds.resolve_condition(
        conn, 5, reasoning="Regime shifted back", price_date=_PRICE_DATE
    )
    assert isinstance(c, ThesisCondition)
    q, args = _execs(conn, "thesis_condition_events")[0]
    assert "'resolved'" in q and "'human'" in q
    assert args[2] == _PRICE_DATE  # price_date positional in the resolve INSERT
    _q, args = _execs(conn, "thesis_revisions")[0]
    assert args[2] == "condition_resolved"


# ---------------------------------------------------------------------------
# add_condition — authoring stores the parse baseline
# ---------------------------------------------------------------------------

async def test_add_condition_stores_parser_baseline():
    inserted = _cond_row(status="active")
    conn = _Conn(fetchrow=[{"thesis_id": 2}, inserted], fetchval=[1])
    c = await conds.add_condition(
        conn, 2,
        text="Price closes below $230 stop on volume",
        trigger_semantics="alert_review",
        reasoning="Stop discipline",
    )
    assert isinstance(c, ThesisCondition)
    q, args = next(
        (q, a) for m, q, a in conn.calls
        if m == "fetchrow" and "INSERT INTO thesis_conditions" in q
    )
    # (thesis_id, ordinal, text, semantics, kind, threshold, note, version)
    assert args[4] == "price_below"
    assert args[5] == Decimal("230.000000")
    assert "NOT enforced" in args[6]  # the echo records the narrowing
    assert args[7] == "cp-1"
    _q, rev_args = _execs(conn, "thesis_revisions")[0]
    assert rev_args[2] == "condition_added"


async def test_add_condition_rejects_bad_semantics():
    conn = _Conn()
    with pytest.raises(ValueError, match="trigger_semantics"):
        await conds.add_condition(
            conn, 2, text="x", trigger_semantics="maybe_exit", reasoning="r"
        )


async def test_add_condition_requires_text_and_reasoning():
    conn = _Conn()
    with pytest.raises(ValueError, match="text is required"):
        await conds.add_condition(conn, 2, text=" ", trigger_semantics="hard_exit", reasoning="r")
    with pytest.raises(ValueError, match="reasoning is required"):
        await conds.add_condition(conn, 2, text="x", trigger_semantics="hard_exit", reasoning="")
