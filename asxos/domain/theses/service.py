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

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import asyncpg
from pydantic import ValidationError as PydanticValidationError

from asxos.domain.governance import transitions as governance_transitions
from asxos.domain.theses.schemas import (
    REPORT_SECTION_KINDS,
    ReportFigure,
    ReportSection,
    ReportSectionKind,
)
from asxos.domain.theses.types import (
    _REVISION_TYPE_FOR_FIELD,
    REVISABLE_FIELDS,
    InvalidationCondition,
    Thesis,
    ThesisRevision,
)

_VALID_SYMBOL_SUFFIXES = (".AU", ".US")
_REVISIT_INTERVAL_DAYS = 30
_STALE_EVIDENCE_DAYS = 14

#: The `thesis_evidence` vocabularies, mirrored from the table's CHECK
#: constraints so a bad call fails with a named Python error before Postgres
#: rejects it. Public because the CLI renders them in its help text and a test
#: pins them against the live constraints.
EVIDENCE_TIERS = frozenset({"verified", "inferred", "speculative"})
EVIDENCE_SOURCE_TYPES = frozenset({"db_query", "external_url"})
#: migration 0061. NULL is deliberately NOT a member: a citation with no stance
#: means nobody judged it, which is a different fact from 'neutral' (someone
#: judged it and found it non-diagnostic). Callers pass None, never a sentinel.
EVIDENCE_STANCES = frozenset({"supports", "contradicts", "neutral"})
_REJECTABLE_FROM = {"draft", "evidence_complete", "pending_review"}
#: Retirement is the disposal of an ALREADY-DECIDED row, which is exactly what
#: reject_object refuses (see its docstring). The two are complements, not
#: alternatives: reject = "never accepted", retire = "was accepted, is finished".
_RETIREABLE_FROM = {"approved"}


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


def _parse_report_sections(raw: Any) -> tuple[ReportSection, ...]:
    """Parse the theses.report_sections JSONB column (migration 0040) back
    into ReportSection instances.

    ``parse_float=Decimal`` mirrors the hazard schemas.py's own module
    docstring documents for deserialising a ThesisProposal: a bare
    json.loads() would turn a JSON number literal into a float before
    Pydantic ever sees it, losing precision (CLAUDE.md #5) — belt-and-
    suspenders here since every value this module writes is already a
    quoted Decimal string (see add_report_section()'s model_dump(mode="json")
    call), but it costs nothing and matches the documented contract exactly.

    Re-validating through ReportSection.model_validate() on every read (not
    just on write) is deliberate defense in depth (CLAUDE.md #10): if a row
    were ever hand-edited outside this module, reading it back fails loudly
    (pydantic.ValidationError) rather than silently serving a corrupted
    prose-only-body or monitor_only-in-a-basis-section violation.
    """
    if raw is None:
        return ()
    if isinstance(raw, str):
        raw = json.loads(raw, parse_float=Decimal)
    return tuple(ReportSection.model_validate(item) for item in raw)


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
        # migration 0021 fields — .get() works for both asyncpg Record and plain dict
        analyst_buy_count=row.get("analyst_buy_count"),
        analyst_neutral_count=row.get("analyst_neutral_count"),
        analyst_sell_count=row.get("analyst_sell_count"),
        analyst_consensus_target=row.get("analyst_consensus_target"),
        analyst_updated_at=row.get("analyst_updated_at"),
        next_earnings_date=row.get("next_earnings_date"),
        earnings_notes=row.get("earnings_notes") or "",
        # migration 0026 fields
        conviction_level=row.get("conviction_level"),
        tax_notes=row.get("tax_notes") or "",
        # migration 0033 field
        governance_status=row.get("governance_status", "approved"),
        # migration 0040 field — .get() so a pre-migration synthetic test row
        # (no "report_sections" key at all) parses to () unchanged.
        report_sections=_parse_report_sections(row.get("report_sections")),
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
    diff: dict[str, Any],
    reasoning: str,
    source: str = "human",
    evidence_confidence: str | None = None,
    evidence_citations: list[str] | None = None,
) -> None:
    """Append one discipline event.

    `source` is 'human' (the CLI), 'agent' (an LLM discovery agent, via the
    service functions only) or 'system_screen' (the deterministic valuation
    screen, migration 0057). The 0034 provenance constraints require a
    non-human row to carry `evidence_confidence` and at least one citation —
    enforced here too so the failure names itself before Postgres does.
    """
    if source != "human" and (not evidence_confidence or not evidence_citations):
        raise ValueError(
            f"a {source!r} revision must carry evidence_confidence and at least one "
            "evidence citation (migration 0034 provenance constraints)"
        )
    await conn.execute(
        """
        INSERT INTO thesis_revisions
            (thesis_id, revised_at, revision_type, diff, reasoning,
             source, evidence_confidence, evidence_citations)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8::jsonb)
        """,
        thesis_id,
        revised_at,
        revision_type,
        json.dumps(diff),
        reasoning,
        source,
        evidence_confidence,
        json.dumps(evidence_citations or []),
    )


async def record_system_examination(
    conn: asyncpg.Connection,
    *,
    thesis_id: int,
    examined_at: datetime,
    reasoning: str,
    evidence_confidence: str,
    evidence_citations: list[str],
    diff: dict[str, Any] | None = None,
) -> None:
    """Append a `packet_examined` row (migration 0060): the system looked, James did not.

    This is the one public entry for a *job* to write `thesis_revisions`, and
    it is deliberately narrow. It cannot choose the revision type -- it is always
    `packet_examined`, which sits OUTSIDE the brief's answering-revision allowlist
    (`asxos/brief/compose.py`, `last_answering_revision_at`) -- and it never
    touches `theses.last_revisited_at` or `revisit_due_at`. So the invariant in
    `discipline.py` holds: every clock reset is still a human keystroke, and no
    job can suppress a staleness finding by calling this.

    `source` is fixed to `system_screen` (0057), so the 0034 provenance
    constraints apply and `_insert_revision` enforces them before Postgres does.
    """
    await _insert_revision(
        conn,
        thesis_id=thesis_id,
        revised_at=examined_at,
        revision_type="packet_examined",
        diff=diff or {},
        reasoning=reasoning,
        source="system_screen",
        evidence_confidence=evidence_confidence,
        evidence_citations=evidence_citations,
    )


def canonical_snapshot(snapshot_data: dict[str, Any]) -> tuple[str, str]:
    """Return (canonical JSON, sha256 of it) for an evidence snapshot.

    Sorted keys, no whitespace, `default=str` so a Decimal serialises as its
    exact string rather than a float (CLAUDE.md #5) — the hash must never depend
    on float formatting, or the tamper-evidence the `snapshot_hash` column exists
    for is evidence of nothing.

    Extracted so every writer of an evidence row hashes identically. Two writers
    with two copies of this three-line body is how a corpus ends up with rows
    whose hashes cannot be compared.
    """
    canonical = json.dumps(snapshot_data, sort_keys=True, separators=(",", ":"), default=str)
    return canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_evidence_fields(
    *,
    tier: str,
    stance: str | None,
    source_type: str,
    source_url: str | None,
    snapshot_data: dict[str, Any] | None,
) -> None:
    """Mirror `thesis_evidence`'s CHECK constraints in Python, so a bad call names
    itself before Postgres does — the same reason `_insert_revision` re-checks the
    0034 provenance pair.

    `stance` (migration 0061) is validated against the three-value vocabulary, and
    None passes: NULL means nobody judged, which is a legitimate state and the
    whole reason the column is nullable.
    """
    if tier not in EVIDENCE_TIERS:
        raise ValueError(f"unknown evidence tier {tier!r}; expected one of {sorted(EVIDENCE_TIERS)}")
    if stance is not None and stance not in EVIDENCE_STANCES:
        raise ValueError(
            f"unknown evidence stance {stance!r}; expected one of {sorted(EVIDENCE_STANCES)} "
            "or None (None means nobody judged, which is not the same as 'neutral')"
        )
    if source_type not in EVIDENCE_SOURCE_TYPES:
        raise ValueError(
            f"unknown source_type {source_type!r}; expected one of {sorted(EVIDENCE_SOURCE_TYPES)}"
        )
    if source_url is not None and source_type != "external_url":
        raise ValueError(
            "source_url is only meaningful with source_type='external_url' "
            "(thesis_evidence_url_requires_external)"
        )
    if tier != "speculative" and snapshot_data is None:
        raise ValueError(
            f"a {tier!r} citation must carry snapshot_data — only a speculative one may omit it "
            "(thesis_evidence_snapshot_required_unless_speculative)"
        )


async def add_thesis_evidence(
    conn: asyncpg.Connection,
    *,
    thesis_id: int,
    source_agent: str,
    tier: str,
    claim_text: str,
    source_table: str | None = None,
    source_as_of: datetime | None = None,
    snapshot_data: dict[str, Any] | None = None,
    stance: str | None = None,
    source_type: str = "db_query",
    source_url: str | None = None,
) -> int:
    """Append one `thesis_evidence` citation (migration 0033) and return its id.

    The INSERT primitive. `log_evidence` is the public verb — it checks the thesis
    exists and names the failure; this one assumes the caller already has.

    `retrieved_at` is deliberately never passed: it takes the column DEFAULT of
    `NOW()`, which is this row's own retrieval time. Nothing here updates an
    existing row's `retrieved_at`, because `approve_object`'s staleness gate reads
    that column and a write path that refreshed it would launder a stale thesis
    into approvable.
    """
    _validate_evidence_fields(
        tier=tier,
        stance=stance,
        source_type=source_type,
        source_url=source_url,
        snapshot_data=snapshot_data,
    )
    canonical, snapshot_hash = (
        canonical_snapshot(snapshot_data) if snapshot_data is not None else (None, None)
    )
    row = await conn.fetchrow(
        """
        INSERT INTO thesis_evidence
            (thesis_id, source_agent, tier, claim_text, source_type, source_table,
             source_as_of, snapshot_data, snapshot_hash, source_url, stance)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11)
        RETURNING evidence_id
        """,
        thesis_id,
        source_agent,
        tier,
        claim_text,
        source_type,
        source_table,
        source_as_of,
        canonical,
        snapshot_hash,
        source_url,
        stance,
    )
    return int(row["evidence_id"])


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
    invalidation_conditions: list[dict[str, Any]] | None = None,
    conviction_level: int | None = None,
    tax_notes: str | None = None,
    reasoning: str = "Initial thesis",
    governance_status: str = "approved",
    source: str = "human",
    evidence_confidence: str | None = None,
    evidence_citations: list[str] | None = None,
) -> Thesis:
    """Open a new investment thesis.

    `governance_status` defaults to 'approved' — the zero-friction human CLI
    path (0033 grandfathers human-authored theses). A system-proposed thesis
    (F-E2E r2 S4, `source='system_screen'`) opens at 'pending_review' and
    reaches 'approved' only through `approve_object()`; its 'opened' revision
    must cite evidence (0034/0057).

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
    if governance_status not in ("approved", "pending_review", "draft"):
        raise ValueError(f"open_thesis cannot open at governance_status={governance_status!r}")
    if source != "human" and governance_status == "approved":
        raise ValueError(
            f"a {source!r} thesis cannot open as approved — it enters at pending_review "
            "and needs a human approval (governance Section 4.1)"
        )
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
                last_revisited_at, revisit_due_at, opened_at,
                conviction_level, tax_notes, governance_status
            ) VALUES (
                $1, $2, $3,
                $4, $5,
                $6, $7, $8,
                $9::jsonb, $10,
                $11, $12, $11,
                $13, $14, $15
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
            conviction_level,
            tax_notes,
            governance_status,
        )
        thesis_id: int = row["thesis_id"]

        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type="opened",
            diff={},
            reasoning=reasoning,
            source=source,
            evidence_confidence=evidence_confidence,
            evidence_citations=evidence_citations,
        )

        # Upsert theme_holdings placeholder rows for each theme code.
        # ON CONFLICT DO NOTHING — if the row exists (symbol already linked to
        # this theme from a prior thesis), leave it untouched.
        # governance_status='draft' explicitly (not the column DEFAULT
        # 'approved'): a system_default placeholder is unreviewed structural
        # scaffolding, not a reviewed exposure claim — migration 0035
        # backfilled existing placeholders to 'draft' for exactly this
        # reason, and omitting it here would recreate the laundered state
        # on every new `asx thesis open --themes`. INSERTs don't fire the
        # governance audit trigger (BEFORE UPDATE only), so no
        # governance_events row is required.
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
                    (theme_id, symbol, exposure_strength, source, governance_status,
                     last_validated_at, created_at)
                VALUES ($1, $2, 0.5, 'system_default', 'draft', $3, $3)
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


async def log_evidence(
    conn: asyncpg.Connection,
    *,
    thesis_id: int,
    claim_text: str,
    tier: str,
    snapshot_data: dict[str, Any] | None = None,
    stance: str | None = None,
    source_agent: str = "human",
    source_type: str = "db_query",
    source_table: str | None = None,
    source_url: str | None = None,
    source_as_of: datetime | None = None,
) -> int:
    """Record one citation against an EXISTING thesis. Returns the evidence id.

    WHY THIS EXISTS. Until this verb, the only writer of `thesis_evidence` was a
    helper reachable solely from `open_thesis()` — so a citation could be recorded
    at the moment a thesis was created and never again. Measured 2026-09-20, that
    showed: all 26 rows in the corpus were `source_agent = 'system_screen'`, two
    per thesis, and not one recorded a judgement a human made. Human research had
    nowhere to land, so the evidence chain was a record of what the screen noticed
    rather than what anyone concluded.

    This does NOT revise the thesis. No `thesis_revisions` row is written, no
    clock moves, `last_revisited_at` and `revisit_due_at` are untouched. Citing
    something is not the same act as revisiting a thesis, and conflating them
    would let a citation buy another revisit cadence of silence — the failure
    migration 0060's header spells out for `packet_examined`.

    `stance` (migration 0061) is `supports`, `contradicts`, `neutral`, or omitted.
    Omitted means nobody judged, which is a different fact from `neutral` — do not
    pass `'neutral'` to mean "I did not think about it".

    `retrieved_at` takes the column DEFAULT of `NOW()` on the new row and no
    existing row's value is touched. `approve_object()`'s staleness gate reads
    that column, so a logging path that refreshed it would launder a stale thesis
    into approvable; logging fresh evidence beside stale evidence therefore does
    not clear the gate, which is correct.

    Raises ValueError if the thesis does not exist, or on any vocabulary or
    source-shape violation — each mirrored from the table's CHECK constraints so
    the failure names itself rather than arriving as a Postgres constraint error.
    """
    if not claim_text or not claim_text.strip():
        raise ValueError("claim_text is required — a citation with no claim cites nothing")
    if not source_agent or not source_agent.strip():
        raise ValueError("source_agent is required — every citation records who recorded it")
    _validate_evidence_fields(
        tier=tier,
        stance=stance,
        source_type=source_type,
        source_url=source_url,
        snapshot_data=snapshot_data,
    )
    existing = await conn.fetchrow(
        "SELECT symbol FROM theses WHERE thesis_id = $1", thesis_id
    )
    if existing is None:
        raise ValueError(f"Thesis {thesis_id} not found")
    return await add_thesis_evidence(
        conn,
        thesis_id=thesis_id,
        source_agent=source_agent,
        tier=tier,
        claim_text=claim_text,
        source_table=source_table,
        source_as_of=source_as_of,
        snapshot_data=snapshot_data,
        stance=stance,
        source_type=source_type,
        source_url=source_url,
    )


async def get_latest_governance_event(
    conn: asyncpg.Connection, thesis_id: int
) -> dict[str, Any] | None:
    """The most recent `governance_events` row for a thesis, or None.

    Exists so `asx thesis show` can render *why* a row sits at its
    `governance_status`, not only that it does. A status word on its own says a
    transition happened; the reasoning says what the row actually is — which is
    the whole value of the audit trail and, until this, was visible only to
    someone who thought to query `governance_events` by hand.
    """
    row = await conn.fetchrow(
        """
        SELECT from_status, to_status, event_at, reasoning, actor
        FROM governance_events
        WHERE object_type = 'thesis' AND object_id = $1
        ORDER BY event_at DESC, event_id DESC
        LIMIT 1
        """,
        thesis_id,
    )
    return dict(row) if row else None


async def list_thesis_evidence(
    conn: asyncpg.Connection, thesis_id: int, *, include_superseded: bool = False
) -> list[dict[str, Any]]:
    """Return a thesis's citations, newest first, for `asx evidence list`.

    Superseded rows are excluded by default, matching what `approve_object()`'s
    gate counts.
    """
    rows = await conn.fetch(
        f"""
        SELECT evidence_id, cited_at, source_agent, tier, stance, claim_text,
               source_type, source_table, source_url, source_as_of, retrieved_at,
               snapshot_hash, superseded_at
        FROM thesis_evidence
        WHERE thesis_id = $1 {"" if include_superseded else "AND superseded_at IS NULL"}
        ORDER BY cited_at DESC, evidence_id DESC
        """,
        thesis_id,
    )
    return [dict(r) for r in rows]


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


async def add_report_section(
    conn: asyncpg.Connection,
    thesis_id: int,
    kind: str,
    body: str,
    figures: list[ReportFigure] | None = None,
    *,
    reasoning: str = "",
) -> Thesis:
    """Add or replace one ReportSection (by kind) on an existing thesis.

    Phase C (broker-report thesis persist + render, migration 0040) — the
    human-authored first cut of the #56 ThesisProposal/ReportSection keystone
    (asxos/domain/theses/schemas.py). Upserts by kind — JSONB has no in-place
    field patch, so a section of a matching kind is replaced wholesale, not
    merged; the prior content is never lost, it survives in the revision diff
    below.

    Validates via ReportSection's own Pydantic validators — reuses
    schemas.py, does not reimplement any check: prose-only body (no inline
    $/%/thousands/x literals — those must be a ReportFigure instead), and a
    monitor_only (rule #11 Model A) figure barred from every "basis" section.
    pydantic.ValidationError is a ValueError subclass in v2, so it already
    round-trips through every existing CLI `except ValueError` handler; the
    wrap below only adds the thesis_id to the message.

    Provenance-agnostic by design: this function has no james_input-only
    restriction — the CALLER decides each ReportFigure's provenance. Today
    only the CLI calls it (james_input-only, Phase C scope); a future
    recompute engine or agent-drafted path (Phase D/E) can reuse this
    function unchanged with cited/derived figures.

    Writes revision_type='assumption_change' — the same bucket thesis_text/
    invalidation_conditions/conviction_level/tax_notes already use for
    narrative-content changes (types.py::_REVISION_TYPE_FOR_FIELD). The diff
    stores the FULL old and new ReportSection (model_dump(mode="json")), not
    a summary — thesis_revisions is the irreplaceable audit log, so a
    "replace" is never actually destructive.

    Raises ValueError if thesis_id not found, kind is not one of
    REPORT_SECTION_KINDS, or ReportSection/ReportFigure construction fails
    Pydantic validation.

    Deliberately does NOT route through governance_status / the migration
    0034 audit trigger: that trigger is BEFORE UPDATE OF governance_status
    only (verified against migrations/0034_governance_audit_trigger_and_
    revision_provenance.sql), and this UPDATE never touches that column — a
    human editing his own thesis is the existing zero-friction trust level
    (same as revise_thesis()), not an agent-governance transition.
    """
    if kind not in REPORT_SECTION_KINDS:
        raise ValueError(
            f"kind {kind!r} is not a valid section kind. "
            f"Must be one of: {', '.join(REPORT_SECTION_KINDS)}"
        )
    try:
        # kind is `str` (it arrives from the CLI as plain text) but
        # ReportSection.kind is the Literal ReportSectionKind — the runtime
        # membership check just above is what actually guarantees safety;
        # cast() only tells mypy what's already been verified, it performs
        # no runtime check itself.
        new_section = ReportSection(
            kind=cast(ReportSectionKind, kind), body=body, figures=figures or []
        )
    except PydanticValidationError as exc:
        raise ValueError(f"Invalid report section for thesis {thesis_id}: {exc}") from exc

    now = _now_utc()
    due = _revisit_due(now)

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")

        current = _parse_report_sections(existing.get("report_sections"))
        old_section = next((s for s in current if s.kind == kind), None)
        updated = (*(s for s in current if s.kind != kind), new_section)
        sections_json = json.dumps([s.model_dump(mode="json") for s in updated])

        row = await conn.fetchrow(
            """
            UPDATE theses
            SET report_sections = $1::jsonb,
                last_revisited_at = $2,
                revisit_due_at = $3
            WHERE thesis_id = $4
            RETURNING *
            """,
            sections_json,
            now,
            due,
            thesis_id,
        )

        diff = {
            "report_sections": {
                "old": old_section.model_dump(mode="json") if old_section else None,
                "new": new_section.model_dump(mode="json"),
            }
        }
        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type="assumption_change",
            diff=diff,
            reasoning=reasoning or f"{'Replaced' if old_section else 'Added'} '{kind}' section",
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
      - governance_status is not 'approved'  (migration 0033/0034 — Phase 1
        governance guard; see docs/proposals/governance-first-architecture-
        2026-06-30.md Section 4.1's evidence-requirement table, last row:
        "watching -> active (enter_thesis, investment lifecycle) — Existing
        hard-fails unchanged, plus: hard-fail unless governance_status =
        'approved'")
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
        if existing["governance_status"] != "approved":
            raise ValueError(
                f"Cannot enter thesis {thesis_id} — governance_status is "
                f"{existing['governance_status']!r}, must be 'approved'. "
                "Agent-originated theses require human approval first: "
                "asx thesis approve <id> --reason '...'"
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


async def create_thesis_from_agent_run(
    conn: asyncpg.Connection,
    run_id: int,
    symbol: str,
    *,
    reasoning: str = "Draft created from agent run",
) -> Thesis:
    """Create a thesis draft from a logged agent_runs proposal.

    PHASE 1/2 GAP (documented, not a bug): no ThesisProposal Pydantic schema
    exists yet (see asxos/domain/theses/schemas.py module docstring — the
    design doc explicitly defers a full instrument-thesis proposal shape to
    a future agentic thesis-drafter, m14_candidate_agentic_thesis_drafter).
    This function is therefore currently UNREACHABLE for object_type='thesis'
    rows in practice: it will always raise ValueError below. It exists now,
    fully wired end-to-end (CLI flag, transaction shape, error handling), so
    that landing ThesisProposal later is a schema-plus-one-branch change, not
    a new code path.

    Intended eventual behaviour once ThesisProposal exists is specified in
    docs/proposals/governance-first-architecture-2026-06-30.md Section 4.2
    ("AI agent governance") — not reproduced here to avoid two copies of a
    Phase 2 design drifting out of sync; this docstring documents Phase 1's
    actual behaviour (always raises) only.

    Raises ValueError if:
      - run_id does not exist in agent_runs
      - the agent_runs row was already acted_on
      - object_type != 'thesis' (wrong function for that proposal type)
      - object_type == 'thesis' — always, currently, per the gap above
    """
    async with conn.transaction():
        run = await conn.fetchrow(
            "SELECT * FROM agent_runs WHERE run_id = $1 FOR UPDATE", run_id
        )
        if run is None:
            raise ValueError(f"agent_runs row {run_id} not found")
        if run["acted_on"]:
            raise ValueError(f"agent_runs row {run_id} was already acted on")
        if run["object_type"] != "thesis":
            raise ValueError(
                f"agent_runs row {run_id} has object_type={run['object_type']!r} "
                "— create_thesis_from_agent_run() only accepts object_type="
                "'thesis' rows. Use the matching Phase 2 service function for "
                "macro_thesis/theme/theme_holding proposals once built."
            )

        raise ValueError(
            f"agent_runs row {run_id} has object_type='thesis', but no "
            "ThesisProposal Pydantic schema exists yet to validate "
            "proposed_object against — this is a documented Phase 1/2 gap "
            "(m14_candidate_agentic_thesis_drafter), not a bug. See "
            "asxos/domain/theses/schemas.py module docstring. "
            "create_thesis_from_agent_run() cannot create theses rows from "
            "agent proposals until that schema lands."
        )


async def _apply_governance_transition(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    from_status: str,
    to_status: str,
    reasoning: str,
) -> asyncpg.Record:
    """Thin theses-specific wrapper over the shared
    asxos.domain.governance.transitions.apply_governance_transition() —
    extracted there in Phase 2a since the same governance_events-INSERT-then-
    UPDATE pairing (in that load-bearing order — see transitions.py's module
    docstring) is now needed by themes/theme_holdings/macro_theses too. Kept
    as a wrapper (not inlined at each call site) so approve_object()/
    reject_object() below need zero changes.
    """
    return await governance_transitions.apply_governance_transition(
        conn,
        table_name="theses",
        id_column="thesis_id",
        object_type="thesis",
        object_id=thesis_id,
        from_status=from_status,
        to_status=to_status,
        reasoning=reasoning,
    )


async def approve_object(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    reasoning: str,
    accept_stale_evidence: str | None = None,
) -> Thesis:
    """Transition a thesis from pending_review to approved.

    The only human-facing path from pending_review -> approved. Hard-fails on:
      - governance_status != 'pending_review'
      - reasoning empty
      - zero non-speculative thesis_evidence rows — ALWAYS hard-fails, no
        override exists for this check (a thesis with no citable evidence
        has nothing for a human to knowingly accept; only staleness — "the
        evidence is old" — is something a human can legitimately judge as
        still valid)
      - any non-speculative evidence row's retrieved_at older than
        _STALE_EVIDENCE_DAYS (14) calendar days, UNLESS accept_stale_evidence
        is given (a non-empty reason string) — the override itself is logged
        as an ADDITIONAL governance_events row (reasoning=accept_stale_evidence),
        never folded into the approval's own reasoning field.

    Writes: theses.governance_status='approved', a governance_events row
    (from_status=<prior value>, to_status='approved', actor='human',
    reasoning=reasoning) in the SAME transaction as the theses UPDATE — this
    is what satisfies the migration 0034 trigger.
    """
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")
        if existing["governance_status"] != "pending_review":
            raise ValueError(
                f"Cannot approve thesis {thesis_id} — governance_status is "
                f"{existing['governance_status']!r}, expected 'pending_review'."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to approve a thesis")

        evidence_rows = await conn.fetch(
            """
            SELECT tier, retrieved_at FROM thesis_evidence
            WHERE thesis_id = $1 AND superseded_at IS NULL
            """,
            thesis_id,
        )
        non_speculative = [r for r in evidence_rows if r["tier"] != "speculative"]
        if not non_speculative:
            raise ValueError(
                f"Cannot approve thesis {thesis_id} — no non-speculative "
                "evidence exists. Speculative-only theses cannot be approved "
                "(no override available for this check)."
            )

        now = _now_utc()
        stale_cutoff = now - timedelta(days=_STALE_EVIDENCE_DAYS)
        stale = [r for r in non_speculative if r["retrieved_at"] < stale_cutoff]
        if stale and not accept_stale_evidence:
            raise ValueError(
                f"Cannot approve thesis {thesis_id} — {len(stale)} evidence "
                f"citation(s) older than {_STALE_EVIDENCE_DAYS} days. Pass "
                "accept_stale_evidence='<reason>' to override (logged "
                "separately)."
            )

        row = await _apply_governance_transition(
            conn, thesis_id,
            from_status=existing["governance_status"],
            to_status="approved",
            reasoning=reasoning,
        )
        if stale and accept_stale_evidence:
            # A second, separate governance_events row for the override
            # itself — never folded into the approval's own reasoning field
            # (see the docstring above). from_status='approved' here because
            # this event records the override decision made AFTER the
            # transition above, not the transition itself.
            await conn.execute(
                """
                INSERT INTO governance_events
                    (object_type, object_id, from_status, to_status, reasoning, actor)
                VALUES ('thesis', $1, 'approved', 'approved', $2, 'human')
                """,
                thesis_id,
                accept_stale_evidence,
            )

        return _row_to_thesis(row)


async def reject_object(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    reasoning: str,
) -> Thesis:
    """Transition a thesis from draft/evidence_complete/pending_review to
    rejected.

    Hard-fails if reasoning is empty or governance_status is already
    'approved'/'rejected'/'retired' (rejection only makes sense against a
    not-yet-decided row — _REJECTABLE_FROM is the allowed source-state set).

    Writes: theses.governance_status='rejected', a matching governance_events
    row in the same transaction (satisfies the migration 0034 trigger).
    """
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")
        if existing["governance_status"] not in _REJECTABLE_FROM:
            raise ValueError(
                f"Cannot reject thesis {thesis_id} — governance_status is "
                f"{existing['governance_status']!r}, expected one of "
                f"{sorted(_REJECTABLE_FROM)}."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to reject a thesis")

        row = await _apply_governance_transition(
            conn, thesis_id,
            from_status=existing["governance_status"],
            to_status="rejected",
            reasoning=reasoning,
        )

        return _row_to_thesis(row)


async def retire_object(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    reasoning: str,
) -> Thesis:
    """Transition an approved thesis to retired — the disposal of a decided row.

    This is the gap that made the 2026-09-16 register review's Rec 1
    ("retire the eleven auto-seeded rows") unexecutable as written: `reject_object`
    deliberately refuses an already-approved row, and nothing else could reach
    `governance_status='retired'`, which migration 0033 has admitted since it was
    written. So a thesis could be accepted and could be rejected, but could never
    be *finished*.

    Retire means "this row is no longer live content", NOT "this was a mistake".
    Reach for it when an approved thesis has served out or should never have been
    approved in the first place; `reject_object` remains the verb for a row that was
    never accepted.

    `theses.status` is deliberately untouched — its CHECK (migration 0012) has no
    'retired' value, and widening the investment-lifecycle enum to mirror a
    governance state is a separate call with its own migration. The two columns
    answer different questions (0033's header: status = where in the investment
    lifecycle; governance_status = is this content trustworthy).

    Hard-fails if reasoning is empty or governance_status is not 'approved'
    (_RETIREABLE_FROM). Writes: theses.governance_status='retired' plus a matching
    governance_events row in the same transaction, in that order, which is what
    satisfies the migration 0034 BEFORE UPDATE trigger.
    """
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")
        if existing["governance_status"] not in _RETIREABLE_FROM:
            raise ValueError(
                f"Cannot retire thesis {thesis_id} — governance_status is "
                f"{existing['governance_status']!r}, expected one of "
                f"{sorted(_RETIREABLE_FROM)}. A row that was never approved is "
                f"rejected, not retired."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to retire a thesis")

        row = await _apply_governance_transition(
            conn, thesis_id,
            from_status=existing["governance_status"],
            to_status="retired",
            reasoning=reasoning,
        )

        return _row_to_thesis(row)


async def update_analyst_consensus(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    buy: int | None,
    neutral: int | None,
    sell: int | None,
    target: Decimal | None,
    updated_at: date,
) -> None:
    """Update analyst consensus snapshot and record an assumption_change revision.

    Does not touch last_revisited_at / revisit_due_at — consensus data is
    external context, not a deliberate thesis review by the investor.
    """
    now = _now_utc()

    existing = await conn.fetchrow(
        "SELECT analyst_consensus_target FROM theses WHERE thesis_id = $1", thesis_id
    )
    if existing is None:
        raise ValueError(f"Thesis {thesis_id} not found")

    old_target = existing.get("analyst_consensus_target")
    diff: dict[str, Any] = {
        "analyst_consensus_target": {
            "old": _serialise(old_target),
            "new": _serialise(target),
        },
        "analyst_updated_at": {"old": "null", "new": str(updated_at)},
    }

    async with conn.transaction():
        await conn.execute(
            """
            UPDATE theses
            SET analyst_buy_count        = $1,
                analyst_neutral_count    = $2,
                analyst_sell_count       = $3,
                analyst_consensus_target = $4,
                analyst_updated_at       = $5
            WHERE thesis_id = $6
            """,
            buy, neutral, sell, target, updated_at, thesis_id,
        )
        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=now,
            revision_type="assumption_change",
            diff=diff,
            reasoning=f"Analyst consensus updated: {buy}B/{neutral}N/{sell}S, target {target}",
        )


async def log_analyst_action(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    analyst: str,
    action: str,
    from_rating: str,
    to_rating: str,
    from_target: Decimal | None,
    to_target: Decimal | None,
    event_date: date,
) -> None:
    """Log an analyst rating change as an analyst_action revision event.

    Does not modify thesis fields — purely an audit log entry.
    Use update_analyst_consensus() separately to update consensus counts.
    """
    now = _now_utc()
    diff = {
        "analyst": analyst,
        "action": action,
        "from_rating": from_rating,
        "to_rating": to_rating,
        "from_target": _serialise(from_target),
        "to_target": _serialise(to_target),
        "event_date": str(event_date),
    }
    reasoning = f"{analyst} {action}: {from_rating}→{to_rating}"
    if from_target and to_target:
        reasoning += f" target {from_target}→{to_target}"

    existing = await conn.fetchrow(
        "SELECT thesis_id FROM theses WHERE thesis_id = $1", thesis_id
    )
    if existing is None:
        raise ValueError(f"Thesis {thesis_id} not found")

    await _insert_revision(
        conn,
        thesis_id=thesis_id,
        revised_at=now,
        revision_type="analyst_action",
        diff=diff,
        reasoning=reasoning,
    )


async def set_earnings(
    conn: asyncpg.Connection,
    thesis_id: int,
    next_earnings_date: date | None,
    notes: str = "",
) -> None:
    """Set next earnings date and optional notes on a thesis.

    Operational metadata — no revision event written (not a discipline event).
    """
    existing = await conn.fetchrow(
        "SELECT thesis_id FROM theses WHERE thesis_id = $1", thesis_id
    )
    if existing is None:
        raise ValueError(f"Thesis {thesis_id} not found")

    await conn.execute(
        """
        UPDATE theses
        SET next_earnings_date = $1,
            earnings_notes     = $2
        WHERE thesis_id = $3
        """,
        next_earnings_date,
        notes,
        thesis_id,
    )


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
