"""Thesis domain service — M-Thesis-1.

Decimal serialisation contract for diff JSONB:
  All Decimal values serialised as str(Decimal_value).
  e.g. Decimal("55.123456") → "55.123456".
  Parse back with Decimal(str_value). Never float().
  Empty diff ({}) for reviewed_no_change — reasoning is the substance.

All multi-statement functions use ``async with conn.transaction():``.
``revise_thesis()`` uses REVISABLE_FIELDS allowlist. Never interpolate raw
field names into SQL — look up the SQL column name from the allowlist first.

References:
  migration 0012_theses_and_themes.sql
  M-THESIS-1_IMPLEMENTATION_PLAN_V2.md §4 Phase 3
  CLAUDE.md non-negotiables #1, #5, #10
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import asyncpg

from asxos.domain.theses.types import (
    _REVISION_TYPE_FOR_FIELD,
    REVISABLE_FIELDS,
    InvalidationCondition,
    Thesis,
    ThesisRevision,
)

_VALID_SYMBOL_SUFFIXES = (".AU", ".US")
_REVISIT_INTERVAL_DAYS = 30


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_symbol(symbol: str) -> None:
    """Hard-fail if symbol doesn't end with a known exchange suffix."""
    if not any(symbol.upper().endswith(s) for s in _VALID_SYMBOL_SUFFIXES):
        raise ValueError(
            f"Symbol {symbol!r} must end with .AU or .US"
        )


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _revisit_due(from_dt: datetime | None = None) -> datetime:
    base = from_dt or _now_utc()
    return base + timedelta(days=_REVISIT_INTERVAL_DAYS)


def _serialise(v: Any) -> str:
    """Serialise a value for the diff JSONB contract.

    Decimal → full-precision string ("55.123456").
    None → "null".
    Everything else → str().
    """
    if v is None:
        return "null"
    if isinstance(v, Decimal):
        return str(v)
    return str(v)


def _row_to_thesis(row: asyncpg.Record) -> Thesis:
    """Convert an asyncpg Record from the theses table to a Thesis dataclass."""
    raw_ic = row["invalidation_conditions"]
    if isinstance(raw_ic, str):
        raw_ic = json.loads(raw_ic)
    ic_tuple = tuple(
        InvalidationCondition(
            condition=ic["condition"],
            status=ic["status"],
            note=ic.get("note"),
        )
        for ic in (raw_ic or [])
    )
    return Thesis(
        thesis_id=row["thesis_id"],
        symbol=row["symbol"],
        status=row["status"],
        thesis_text=row["thesis_text"],
        entry_band_lower=row["entry_band_lower"],
        entry_band_upper=row["entry_band_upper"],
        stop_price=row["stop_price"],
        target_price=row["target_price"],
        timeline_days=row["timeline_days"],
        invalidation_conditions=ic_tuple,
        themes=tuple(row["themes"] or []),
        actual_entry_price=row["actual_entry_price"],
        actual_entry_at=row["actual_entry_at"],
        actual_exit_price=row["actual_exit_price"],
        actual_exit_at=row["actual_exit_at"],
        last_revisited_at=row["last_revisited_at"],
        revisit_due_at=row["revisit_due_at"],
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
    )


def _row_to_revision(row: asyncpg.Record) -> ThesisRevision:
    diff = row["diff"]
    if isinstance(diff, str):
        diff = json.loads(diff)
    return ThesisRevision(
        revision_id=row["revision_id"],
        thesis_id=row["thesis_id"],
        revised_at=row["revised_at"],
        revision_type=row["revision_type"],
        diff=diff or {},
        reasoning=row["reasoning"],
    )


async def _insert_revision(
    conn: asyncpg.Connection,
    *,
    thesis_id: int,
    revised_at: datetime,
    revision_type: str,
    diff: dict,
    reasoning: str,
) -> None:
    await conn.execute(
        """
        INSERT INTO thesis_revisions
            (thesis_id, revised_at, revision_type, diff, reasoning)
        VALUES ($1, $2, $3, $4::jsonb, $5)
        """,
        thesis_id,
        revised_at,
        revision_type,
        json.dumps(diff),
        reasoning,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def open_thesis(
    conn: asyncpg.Connection,
    symbol: str,
    *,
    status: str = "watching",
    thesis_text: str | None = None,
    entry_band_lower: Decimal | None = None,
    entry_band_upper: Decimal | None = None,
    stop_price: Decimal | None = None,
    target_price: Decimal | None = None,
    timeline_days: int | None = None,
    themes: list[str] | None = None,
    invalidation_conditions: list[dict] | None = None,
    reasoning: str = "Initial thesis",
) -> Thesis:
    """Open a new investment thesis.

    Validates symbol suffix; inserts thesis + 'opened' revision +
    theme_holdings placeholder rows (source='system_default') in a single
    transaction.

    Raises ValueError if:
      - symbol suffix is not .AU or .US
      - any theme_code in themes does not exist in the themes table

    Themes are upserted to theme_holdings with exposure_strength=0.5 and
    source='system_default'. Use ThemeService.attach_thesis() to set the
    actual exposure_strength and mechanism_text.
    """
    _validate_symbol(symbol)
    themes = themes or []
    invalidation_conditions = invalidation_conditions or []
    now = _now_utc()
    due = _revisit_due(now)

    async with conn.transaction():
        row = await conn.fetchrow(
            """
            INSERT INTO theses (
                symbol, status, thesis_text,
                entry_band_lower, entry_band_upper,
                stop_price, target_price, timeline_days,
                invalidation_conditions, themes,
                last_revisited_at, revisit_due_at, opened_at
            ) VALUES (
                $1, $2, $3,
                $4, $5,
                $6, $7, $8,
                $9::jsonb, $10,
                $11, $12, $11
            )
            RETURNING *
            """,
            symbol,
            status,
            thesis_text,
            entry_band_lower,
            entry_band_upper,
            stop_price,
            target_price,
            timeline_days,
            json.dumps(invalidation_conditions),
            themes,
            now,
            due,
        )
        thesis_id: int = row["thesis_id"]

        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type="opened",
            diff={},
            reasoning=reasoning,
        )

        # Upsert theme_holdings placeholder rows for each theme code.
        # ON CONFLICT DO NOTHING — if the row exists (symbol already linked to
        # this theme from a prior thesis), leave it untouched.
        for code in themes:
            theme_row = await conn.fetchrow(
                "SELECT theme_id FROM themes WHERE theme_code = $1", code
            )
            if theme_row is None:
                raise ValueError(
                    f"Theme code {code!r} does not exist. "
                    f"Create it first: `asx theme create {code} --name '...' --description '...'`"
                )
            await conn.execute(
                """
                INSERT INTO theme_holdings
                    (theme_id, symbol, exposure_strength, source, last_validated_at, created_at)
                VALUES ($1, $2, 0.5, 'system_default', $3, $3)
                ON CONFLICT (theme_id, symbol) DO NOTHING
                """,
                theme_row["theme_id"],
                symbol,
                now,
            )

        return _row_to_thesis(row)


async def get_thesis(conn: asyncpg.Connection, thesis_id: int) -> Thesis | None:
    """Fetch a thesis by ID. Returns None if not found."""
    row = await conn.fetchrow(
        "SELECT * FROM theses WHERE thesis_id = $1", thesis_id
    )
    return _row_to_thesis(row) if row else None


async def get_thesis_by_symbol(
    conn: asyncpg.Connection, symbol: str
) -> Thesis | None:
    """Return the most recent open thesis for a symbol (by opened_at DESC)."""
    row = await conn.fetchrow(
        """
        SELECT * FROM theses
        WHERE symbol = $1
        ORDER BY opened_at DESC
        LIMIT 1
        """,
        symbol,
    )
    return _row_to_thesis(row) if row else None


async def list_theses(
    conn: asyncpg.Connection, *, status: str | None = None
) -> list[Thesis]:
    """List theses. If status is given, filter to that status.

    Ordered by revisit urgency (revisit_due_at ASC) then opened_at DESC.
    """
    if status is not None:
        rows = await conn.fetch(
            """
            SELECT * FROM theses
            WHERE status = $1
            ORDER BY revisit_due_at ASC, opened_at DESC
            """,
            status,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT * FROM theses
            ORDER BY status, revisit_due_at ASC, opened_at DESC
            """
        )
    return [_row_to_thesis(r) for r in rows]


async def get_history(
    conn: asyncpg.Connection, thesis_id: int
) -> list[ThesisRevision]:
    """Return all revision events for a thesis (newest first)."""
    rows = await conn.fetch(
        """
        SELECT * FROM thesis_revisions
        WHERE thesis_id = $1
        ORDER BY revised_at DESC
        """,
        thesis_id,
    )
    return [_row_to_revision(r) for r in rows]


async def revise_thesis(
    conn: asyncpg.Connection,
    thesis_id: int,
    field: str,
    value: Any,
    reasoning: str,
) -> Thesis:
    """Revise one field on a thesis with a typed audit event in thesis_revisions.

    field must be a key in REVISABLE_FIELDS — raises ValueError otherwise.
    This is the SQL injection guard: the SQL column name is never taken from
    user input directly; it is always looked up in the allowlist.

    Monetary/Decimal values in diff are serialised as str() per the contract.
    Updates last_revisited_at and revisit_due_at.
    All writes in a single transaction.

    For invalidation_conditions, pass a list of dicts:
      [{"condition": "...", "status": "active", "note": None}]
    """
    if field not in REVISABLE_FIELDS:
        raise ValueError(
            f"Field {field!r} is not revisable. "
            f"Allowed fields: {sorted(REVISABLE_FIELDS)}"
        )
    sql_col = REVISABLE_FIELDS[field]
    revision_type = _REVISION_TYPE_FOR_FIELD[field]
    now = _now_utc()
    due = _revisit_due(now)

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")

        old_raw = existing[sql_col]
        old_str = _serialise(old_raw)
        new_str = _serialise(value)

        diff = {field: {"old": old_str, "new": new_str}}

        # JSONB fields need special handling for the parameterised query.
        if field == "invalidation_conditions":
            db_value: Any = json.dumps(value)
            # sql_col is from REVISABLE_FIELDS allowlist — safe to interpolate
            row = await conn.fetchrow(
                f"""
                UPDATE theses
                SET {sql_col} = $1::jsonb,
                    last_revisited_at = $2,
                    revisit_due_at = $3
                WHERE thesis_id = $4
                RETURNING *
                """,
                db_value,
                now,
                due,
                thesis_id,
            )
        else:
            row = await conn.fetchrow(
                f"""
                UPDATE theses
                SET {sql_col} = $1,
                    last_revisited_at = $2,
                    revisit_due_at = $3
                WHERE thesis_id = $4
                RETURNING *
                """,
                value,
                now,
                due,
                thesis_id,
            )

        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type=revision_type,
            diff=diff,
            reasoning=reasoning,
        )

        return _row_to_thesis(row)


async def review_thesis(
    conn: asyncpg.Connection,
    thesis_id: int,
    reasoning: str,
) -> Thesis:
    """Record a deliberate 'reviewed, no change' discipline event.

    This is the core discipline scaffold: you must state *why* you are still
    holding. No field is changed. Only last_revisited_at and revisit_due_at
    are updated. diff is empty ({}) — the substance is in reasoning.

    Raises ValueError if reasoning is empty.
    """
    if not reasoning or not reasoning.strip():
        raise ValueError(
            "reasoning is required for a review event. "
            "State why you are still holding this position."
        )
    now = _now_utc()
    due = _revisit_due(now)

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT thesis_id FROM theses WHERE thesis_id = $1", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")

        row = await conn.fetchrow(
            """
            UPDATE theses
            SET last_revisited_at = $1, revisit_due_at = $2
            WHERE thesis_id = $3
            RETURNING *
            """,
            now,
            due,
            thesis_id,
        )

        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type="reviewed_no_change",
            diff={},
            reasoning=reasoning,
        )

        return _row_to_thesis(row)


async def enter_thesis(
    conn: asyncpg.Connection,
    thesis_id: int,
    entry_price: Decimal,
    qty: int | None = None,
) -> Thesis:
    """Transition thesis to 'active' — capital has been deployed.

    Hard-fails (raises ValueError) if:
      - status is not 'watching' or 'research'
      - thesis_text is None or empty  (cannot enter on unarticulated thesis)
      - stop_price is None
      - target_price is None

    Sets status='active', actual_entry_price, actual_entry_at.
    Writes 'entered' revision with entry price in diff.

    qty is informational only. It is NOT stored on the thesis — record
    the lot in holding_lots via `asx lot add` after entering.
    """
    now = _now_utc()
    due = _revisit_due(now)

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")

        if existing["status"] not in ("watching", "research"):
            raise ValueError(
                f"Cannot enter thesis {thesis_id} — current status is "
                f"{existing['status']!r}. Expected 'watching' or 'research'."
            )
        if not existing["thesis_text"]:
            raise ValueError(
                f"Cannot enter thesis {thesis_id} — thesis_text is empty. "
                "You must articulate the thesis before deploying capital. "
                "Use: asx thesis revise --thesis '...' --reason '...'"
            )
        if existing["stop_price"] is None:
            raise ValueError(
                f"Cannot enter thesis {thesis_id} — stop_price is not set. "
                "Use: asx thesis revise --stop PRICE --reason '...'"
            )
        if existing["target_price"] is None:
            raise ValueError(
                f"Cannot enter thesis {thesis_id} — target_price is not set. "
                "Use: asx thesis revise --target PRICE --reason '...'"
            )

        diff = {
            "status": {"old": existing["status"], "new": "active"},
            "actual_entry_price": {"old": "null", "new": str(entry_price)},
        }
        reasoning_parts = [f"Entered at {entry_price}"]
        if qty is not None:
            reasoning_parts.append(f"qty {qty}")
        reasoning = ", ".join(reasoning_parts)

        row = await conn.fetchrow(
            """
            UPDATE theses
            SET status = 'active',
                actual_entry_price = $1,
                actual_entry_at = $2,
                last_revisited_at = $2,
                revisit_due_at = $3
            WHERE thesis_id = $4
            RETURNING *
            """,
            entry_price,
            now,
            due,
            thesis_id,
        )

        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type="entered",
            diff=diff,
            reasoning=reasoning,
        )

        return _row_to_thesis(row)


async def exit_thesis(
    conn: asyncpg.Connection,
    thesis_id: int,
    exit_price: Decimal,
    *,
    revision_type: str = "exited",
    reasoning: str = "",
) -> Thesis:
    """Close an active (or any open) thesis.

    revision_type must be one of: 'exited', 'exited_by_stop', 'exited_by_target'.
    Hard-fails if status is already 'exited' or 'expired'.

    Sets status='exited', actual_exit_price, actual_exit_at, closed_at.
    """
    _VALID_EXIT_TYPES = {"exited", "exited_by_stop", "exited_by_target"}
    if revision_type not in _VALID_EXIT_TYPES:
        raise ValueError(
            f"revision_type must be one of {sorted(_VALID_EXIT_TYPES)}, "
            f"got {revision_type!r}"
        )
    now = _now_utc()

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")
        if existing["status"] in ("exited", "expired"):
            raise ValueError(
                f"Thesis {thesis_id} is already {existing['status']!r} — cannot exit again"
            )

        diff = {
            "status": {"old": existing["status"], "new": "exited"},
            "actual_exit_price": {
                "old": _serialise(existing["actual_exit_price"]),
                "new": str(exit_price),
            },
        }
        if not reasoning:
            reasoning = f"Exited at {exit_price} ({revision_type})"

        row = await conn.fetchrow(
            """
            UPDATE theses
            SET status = 'exited',
                actual_exit_price = $1,
                actual_exit_at = $2,
                closed_at = $2,
                last_revisited_at = $2
            WHERE thesis_id = $3
            RETURNING *
            """,
            exit_price,
            now,
            thesis_id,
        )

        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type=revision_type,
            diff=diff,
            reasoning=reasoning,
        )

        return _row_to_thesis(row)
