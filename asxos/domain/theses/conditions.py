"""Thesis-condition CRUD + state machine (0042, D1/R2).

Transition table (design §4; every write path below is one transaction):

  — (insert)          authored                → active     (human)
  active | re_armed   close crosses threshold → triggered  (job/sweep)
  triggered           close back on safe side → re_armed   (job/sweep; single
                                                            close, v1 — hysteresis
                                                            is R4, deferred)
  triggered           close still breached    → no-op      (no daily spam;
                                                            duration is DERIVED
                                                            from events + tape,
                                                            never a counter)
  active|triggered|re_armed  human resolution → resolved   (terminal; re-opening
                                                            = add_condition, new
                                                            row, new baseline)

Concurrency: three writers exist (daily job, CLI, R8 sweep). Machine
transitions guard the from-status in the UPDATE's WHERE clause — 0 rows
updated ⇒ raise, no lost updates (the pre-0042 whole-JSONB-array
read-modify-write hazard, KD-1). Idempotency: the events UNIQUE
(condition_id, price_date, event_type) is checked FIRST via ON CONFLICT DO
NOTHING — a re-run over an already-recorded close is a quiet no-op (returns
False), never a duplicate event and never a spurious status flip.

DELIBERATE divergence from every other theses write path (design §10.7):
machine transitions do NOT touch theses.last_revisited_at / revisit_due_at —
a machine fact is not a human revisit. Human condition acts (add / resolve)
also leave the revisit clock alone: the clock tracks whole-thesis reviews
(review_thesis / revise_thesis), not condition bookkeeping.
"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import asyncpg

from asxos.domain.theses.condition_parser import PARSER_VERSION, parse_condition
from asxos.domain.theses.types import ConditionEvent, ThesisCondition

_VALID_SEMANTICS = ("hard_exit", "alert_review")
_MACHINE_SOURCES = ("job", "sweep")


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _row_to_condition(row: Any) -> ThesisCondition:
    return ThesisCondition(
        condition_id=row["condition_id"],
        thesis_id=row["thesis_id"],
        ordinal=row["ordinal"],
        condition_text=row["condition_text"],
        trigger_semantics=row["trigger_semantics"],
        status=row["status"],
        enforcement_kind=row["enforcement_kind"],
        enforcement_threshold=row["enforcement_threshold"],
        enforcement_note=row["enforcement_note"],
        parser_version=row["parser_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_event(row: Any) -> ConditionEvent:
    return ConditionEvent(
        event_id=row["event_id"],
        condition_id=row["condition_id"],
        thesis_id=row["thesis_id"],
        event_type=row["event_type"],
        price_date=row["price_date"],
        observed_close=row["observed_close"],
        threshold=row["threshold"],
        detected_at=row["detected_at"],
        source=row["source"],
        note=row["note"],
    )


async def _insert_revision(
    conn: asyncpg.Connection,
    *,
    thesis_id: int,
    revision_type: str,
    diff: dict[str, Any],
    reasoning: str,
) -> None:
    """Local mirror of service.py::_insert_revision — kept module-private here
    to avoid a service↔conditions circular import (service imports this
    module for open_thesis's condition writes). Same table, same Decimal-
    string diff contract."""
    await conn.execute(
        """
        INSERT INTO thesis_revisions
            (thesis_id, revised_at, revision_type, diff, reasoning)
        VALUES ($1, $2, $3, $4::jsonb, $5)
        """,
        thesis_id,
        _now_utc(),
        revision_type,
        json.dumps(diff),
        reasoning,
    )


# ---------------------------------------------------------------------------
# Authoring
# ---------------------------------------------------------------------------

async def add_condition(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    text: str,
    trigger_semantics: str,
    reasoning: str,
) -> ThesisCondition:
    """Author a new condition: parse the machine baseline NOW and store it
    alongside the text — the daily job evaluates the stored baseline, never a
    runtime re-parse (design §3). Writes the thesis_conditions row + a
    'condition_added' revision in one transaction.

    trigger_semantics is required and explicit — the authored intent is
    load-bearing (alert action-verbs hang off it) and must never be defaulted
    silently at the service layer.
    """
    if trigger_semantics not in _VALID_SEMANTICS:
        raise ValueError(
            f"trigger_semantics must be one of {list(_VALID_SEMANTICS)}, "
            f"got {trigger_semantics!r}"
        )
    if not text or not text.strip():
        raise ValueError("condition text is required")
    if not reasoning or not reasoning.strip():
        raise ValueError("reasoning is required to add a condition")

    parsed = parse_condition(text)

    async with conn.transaction():
        exists = await conn.fetchrow(
            "SELECT thesis_id FROM theses WHERE thesis_id = $1", thesis_id
        )
        if exists is None:
            raise ValueError(f"Thesis {thesis_id} not found")

        ordinal = await conn.fetchval(
            "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM thesis_conditions WHERE thesis_id = $1",
            thesis_id,
        )
        row = await conn.fetchrow(
            """
            INSERT INTO thesis_conditions
                (thesis_id, ordinal, condition_text, trigger_semantics,
                 enforcement_kind, enforcement_threshold, enforcement_note,
                 parser_version)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            thesis_id,
            ordinal,
            text.strip(),
            trigger_semantics,
            parsed.kind,
            parsed.threshold,
            parsed.echo,
            PARSER_VERSION,
        )
        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revision_type="condition_added",
            diff={
                "condition_added": {
                    "ordinal": str(ordinal),
                    "text": text.strip(),
                    "trigger_semantics": trigger_semantics,
                    "enforcement_kind": parsed.kind,
                    "enforcement_threshold": (
                        str(parsed.threshold) if parsed.threshold is not None else "null"
                    ),
                    "parser_version": PARSER_VERSION,
                }
            },
            reasoning=reasoning,
        )
        return _row_to_condition(row)


# ---------------------------------------------------------------------------
# Machine transitions (job / sweep)
# ---------------------------------------------------------------------------

async def _record_machine_transition(
    conn: asyncpg.Connection,
    condition_id: int,
    *,
    event_type: str,
    to_status: str,
    allowed_from: tuple[str, ...],
    revision_type: str,
    price_date: date,
    observed_close: Decimal,
    source: str,
    note: str | None,
) -> bool:
    """Shared trigger/re-arm mechanics. Returns True if the transition was
    applied, False if this (condition, price_date, event_type) was already
    recorded (idempotent re-run — nothing written). Raises on an invalid
    from-status (lost update / caller bug) — the failed UPDATE rolls the
    event INSERT back with it."""
    if source not in _MACHINE_SOURCES:
        raise ValueError(
            f"source must be one of {list(_MACHINE_SOURCES)} for machine "
            f"transitions, got {source!r} — human resolution goes through "
            "resolve_condition()"
        )
    async with conn.transaction():
        cond = await conn.fetchrow(
            """
            SELECT thesis_id, ordinal, condition_text, status,
                   enforcement_kind, enforcement_threshold
            FROM thesis_conditions WHERE condition_id = $1 FOR UPDATE
            """,
            condition_id,
        )
        if cond is None:
            raise ValueError(f"Condition {condition_id} not found")
        if cond["enforcement_kind"] == "not_machine_checkable":
            raise ValueError(
                f"Condition {condition_id} is not machine-checkable — a machine "
                "transition on it would be a silent-skip inversion (register #5)"
            )

        # Idempotency FIRST (events UNIQUE): an already-recorded close is a
        # quiet no-op, whatever the current status — re-running a historical
        # day after later transitions must not flip the state back.
        ins = await conn.execute(
            """
            INSERT INTO thesis_condition_events
                (condition_id, thesis_id, event_type, price_date,
                 observed_close, threshold, source, note)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (condition_id, price_date, event_type) DO NOTHING
            """,
            condition_id,
            cond["thesis_id"],
            event_type,
            price_date,
            observed_close,
            cond["enforcement_threshold"],
            source,
            note,
        )
        if ins.endswith(" 0"):
            return False

        upd = await conn.execute(
            """
            UPDATE thesis_conditions
            SET status = $1, updated_at = NOW()
            WHERE condition_id = $2 AND status = ANY($3::text[])
            """,
            to_status,
            condition_id,
            list(allowed_from),
        )
        if upd != "UPDATE 1":
            raise ValueError(
                f"Condition {condition_id} {event_type} refused: status is "
                f"{cond['status']!r}, expected one of {list(allowed_from)} "
                "(lost update guard — 0 rows updated)"
            )

        await _insert_revision(
            conn,
            thesis_id=cond["thesis_id"],
            revision_type=revision_type,
            diff={
                "condition_status": {"old": cond["status"], "new": to_status},
                "condition_id": str(condition_id),
                "ordinal": str(cond["ordinal"]),
                "price_date": str(price_date),
                "observed_close": str(observed_close),
                "threshold": (
                    str(cond["enforcement_threshold"])
                    if cond["enforcement_threshold"] is not None
                    else "null"
                ),
                "source": source,
            },
            reasoning=(
                f"Condition {cond['ordinal']} ({cond['condition_text'][:80]!r}) "
                f"{event_type}: close {observed_close} vs threshold "
                f"{cond['enforcement_threshold']} on {price_date} [{source}]"
            ),
        )
    return True


async def record_trigger(
    conn: asyncpg.Connection,
    condition_id: int,
    *,
    price_date: date,
    observed_close: Decimal,
    source: str = "job",
    note: str | None = None,
) -> bool:
    """active|re_armed → triggered on a breaching close. price_date is the
    CLOSE's dt, never the run date (register #21)."""
    return await _record_machine_transition(
        conn,
        condition_id,
        event_type="triggered",
        to_status="triggered",
        allowed_from=("active", "re_armed"),
        revision_type="condition_triggered",
        price_date=price_date,
        observed_close=observed_close,
        source=source,
        note=note,
    )


async def record_re_arm(
    conn: asyncpg.Connection,
    condition_id: int,
    *,
    price_date: date,
    observed_close: Decimal,
    source: str = "job",
    note: str | None = None,
) -> bool:
    """triggered → re_armed on a single recaptured close (v1; hysteresis is
    R4, deferred)."""
    return await _record_machine_transition(
        conn,
        condition_id,
        event_type="re_armed",
        to_status="re_armed",
        allowed_from=("triggered",),
        revision_type="condition_re_armed",
        price_date=price_date,
        observed_close=observed_close,
        source=source,
        note=note,
    )


# ---------------------------------------------------------------------------
# Human resolution (terminal)
# ---------------------------------------------------------------------------

async def resolve_condition(
    conn: asyncpg.Connection,
    condition_id: int,
    *,
    reasoning: str,
    price_date: date | None = None,
    note: str | None = None,
) -> ThesisCondition:
    """Human-only terminal transition. Reasoning is required — resolving a
    rule is a discipline event. Re-opening = add_condition (new row, new
    baseline). The events CHECK (resolved_by_human_only) backstops the
    source restriction at the DB level."""
    if not reasoning or not reasoning.strip():
        raise ValueError("reasoning is required to resolve a condition")
    when = price_date or date.today()

    async with conn.transaction():
        cond = await conn.fetchrow(
            """
            SELECT thesis_id, ordinal, condition_text, status, enforcement_threshold
            FROM thesis_conditions WHERE condition_id = $1 FOR UPDATE
            """,
            condition_id,
        )
        if cond is None:
            raise ValueError(f"Condition {condition_id} not found")
        if cond["status"] == "resolved":
            raise ValueError(
                f"Condition {condition_id} is already resolved (terminal) — "
                "re-opening means add_condition (new row, new baseline)"
            )

        await conn.execute(
            """
            INSERT INTO thesis_condition_events
                (condition_id, thesis_id, event_type, price_date,
                 observed_close, threshold, source, note)
            VALUES ($1, $2, 'resolved', $3, NULL, $4, 'human', $5)
            """,
            condition_id,
            cond["thesis_id"],
            when,
            cond["enforcement_threshold"],
            note or reasoning,
        )
        upd = await conn.execute(
            """
            UPDATE thesis_conditions
            SET status = 'resolved', updated_at = NOW()
            WHERE condition_id = $1 AND status IN ('active', 'triggered', 're_armed')
            """,
            condition_id,
        )
        if upd != "UPDATE 1":
            raise ValueError(
                f"Condition {condition_id} resolve refused: status is "
                f"{cond['status']!r} (lost update guard — 0 rows updated)"
            )
        await _insert_revision(
            conn,
            thesis_id=cond["thesis_id"],
            revision_type="condition_resolved",
            diff={
                "condition_status": {"old": cond["status"], "new": "resolved"},
                "condition_id": str(condition_id),
                "ordinal": str(cond["ordinal"]),
                "price_date": str(when),
                "source": "human",
            },
            reasoning=reasoning,
        )

        row = await conn.fetchrow(
            "SELECT * FROM thesis_conditions WHERE condition_id = $1", condition_id
        )
        return _row_to_condition(row)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

async def list_conditions(
    conn: asyncpg.Connection, thesis_id: int
) -> list[ThesisCondition]:
    rows = await conn.fetch(
        "SELECT * FROM thesis_conditions WHERE thesis_id = $1 ORDER BY ordinal",
        thesis_id,
    )
    return [_row_to_condition(r) for r in rows]


async def get_events(
    conn: asyncpg.Connection, condition_id: int
) -> list[ConditionEvent]:
    rows = await conn.fetch(
        """
        SELECT * FROM thesis_condition_events
        WHERE condition_id = $1
        ORDER BY price_date, event_id
        """,
        condition_id,
    )
    return [_row_to_event(r) for r in rows]
