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
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import asyncpg
from pydantic import ValidationError as PydanticValidationError

from asxos.domain.governance import transitions as governance_transitions
from asxos.domain.theses import conditions as conditions_svc
from asxos.domain.theses import lint
from asxos.domain.theses.condition_parser import PARSER_VERSION, parse_condition
from asxos.domain.theses.schemas import (
    REPORT_SECTION_KINDS,
    ReportFigure,
    ReportSection,
    ReportSectionKind,
)
from asxos.domain.theses.types import (
    _REVISION_TYPE_FOR_FIELD,
    REVISABLE_FIELDS,
    Thesis,
    ThesisRevision,
)

_VALID_SYMBOL_SUFFIXES = (".AU", ".US")
_REVISIT_INTERVAL_DAYS = 30
_STALE_EVIDENCE_DAYS = 14
_REJECTABLE_FROM = {"draft", "evidence_complete", "pending_review"}
_VALID_ATTESTATIONS = ("placeholder", "underwritten")
# Fields the underwritten ladder-coherence gate re-checks on revise (0042 D2).
_LADDER_FIELDS = ("stop_price", "entry_band_lower", "entry_band_upper", "target_price")


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
        # migration 0042 fields — .get() default matches the DB DEFAULT
        # 'placeholder' (every pre-0042 row was grandfathered to it, D4).
        attestation=row.get("attestation", "placeholder"),
        attestation_basis=row.get("attestation_basis"),
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
    conditions: list[dict[str, Any]] | None = None,
    conviction_level: int | None = None,
    tax_notes: str | None = None,
    attestation: str = "placeholder",
    attestation_basis: str | None = None,
    reasoning: str = "Initial thesis",
) -> Thesis:
    """Open a new investment thesis.

    Validates symbol suffix; inserts thesis + 'opened' revision +
    theme_holdings placeholder rows (source='system_default') in a single
    transaction.

    conditions (0042, D1/R2): each element is {"text": ..., "trigger_semantics":
    "hard_exit"|"alert_review"} — the shared parser runs at authoring and the
    machine baseline + echo are stored per condition (thesis_conditions rows +
    'condition_added' revisions, via conditions.add_condition()). The pre-0042
    invalidation_conditions JSONB parameter is gone with the column.

    attestation (0042, D4/R9): new theses are BORN 'placeholder' — ladder lint
    findings are only ECHOED for placeholders (the caller/CLI prints them; a
    placeholder may be wrong because it is *visibly* wrong and barred from
    action surfaces). Passing 'underwritten' runs the FULL attest gate
    (attest_thesis()) inside this same transaction — basis required, ladder
    coherent, stop not born-breached, baselines current.

    Raises ValueError if:
      - symbol suffix is not .AU or .US
      - any theme_code in themes does not exist in the themes table
      - a condition dict is missing "text"/"trigger_semantics"
      - attestation='underwritten' and any attest gate fails

    Themes are upserted to theme_holdings with exposure_strength=0.5 and
    source='system_default'. Use ThemeService.attach_thesis() to set the
    actual exposure_strength and mechanism_text.
    """
    _validate_symbol(symbol)
    if attestation not in _VALID_ATTESTATIONS:
        raise ValueError(
            f"attestation must be one of {list(_VALID_ATTESTATIONS)}, got {attestation!r}"
        )
    themes = themes or []
    conditions = conditions or []
    for c in conditions:
        if "text" not in c or "trigger_semantics" not in c:
            raise ValueError(
                "each condition must be {'text': ..., 'trigger_semantics': "
                f"'hard_exit'|'alert_review'}} — got {c!r}"
            )
    now = _now_utc()
    due = _revisit_due(now)

    async with conn.transaction():
        row = await conn.fetchrow(
            """
            INSERT INTO theses (
                symbol, status, thesis_text,
                entry_band_lower, entry_band_upper,
                stop_price, target_price, timeline_days,
                themes,
                last_revisited_at, revisit_due_at, opened_at,
                conviction_level, tax_notes
            ) VALUES (
                $1, $2, $3,
                $4, $5,
                $6, $7, $8,
                $9,
                $10, $11, $10,
                $12, $13
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
            themes,
            now,
            due,
            conviction_level,
            tax_notes,
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

        # 0042: conditions are normalised rows with a stored parse baseline.
        # add_condition() nests a savepoint transaction inside this one and
        # writes the thesis_conditions row + 'condition_added' revision.
        for c in conditions:
            await conditions_svc.add_condition(
                conn,
                thesis_id,
                text=c["text"],
                trigger_semantics=c["trigger_semantics"],
                reasoning=f"Authored at open: {reasoning}",
            )

        thesis = _row_to_thesis(row)
        if attestation == "underwritten":
            # Full attest gate in the same transaction — an incoherent or
            # born-breached ladder aborts the whole open (design §5, row 1).
            thesis = await attest_thesis(
                conn,
                thesis_id,
                to="underwritten",
                basis=attestation_basis,
                reasoning=f"Attested at open: {reasoning}",
            )
        return thesis


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

    0042 (D2/R1): a ladder-field revision on an UNDERWRITTEN thesis hard-fails
    on incoherence — the service mirrors the theses_ladder_coherent_long_v1
    CHECK with a readable error; the CHECK is the backstop. Placeholders are
    deliberately NOT gated (they may be wrong; they are visibly wrong), which
    is exactly what enables incremental rule repair: fix the stop first, then
    the band, then attest (KD-4's rejection of a NOT VALID constraint).
    Invalidation conditions are no longer revisable here — they live in
    thesis_conditions with their own service (conditions.py). Attestation has
    its own transition function (attest_thesis), like governance_status.
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

        if field in _LADDER_FIELDS and existing["attestation"] == "underwritten":
            prospective = {f: existing[f] for f in _LADDER_FIELDS}
            prospective[field] = value
            findings = lint.lint_ladder(
                stop_price=prospective["stop_price"],
                entry_band_lower=prospective["entry_band_lower"],
                entry_band_upper=prospective["entry_band_upper"],
                target_price=prospective["target_price"],
            )
            if findings:
                details = "; ".join(f"[{f.code}] {f.message}" for f in findings)
                raise ValueError(
                    f"Cannot revise {field} on underwritten thesis {thesis_id} — "
                    f"the resulting ladder is incoherent: {details}. For an "
                    "incremental multi-field repair, demote first: "
                    f"asx thesis attest {thesis_id} --to placeholder --reason '...'"
                )

        old_raw = existing[sql_col]
        old_str = _serialise(old_raw)
        new_str = _serialise(value)

        diff = {field: {"old": old_str, "new": new_str}}

        # sql_col is from REVISABLE_FIELDS allowlist — safe to interpolate
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
    conviction_level/tax_notes already use for
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


async def attest_thesis(
    conn: asyncpg.Connection,
    thesis_id: int,
    *,
    to: str,
    basis: str | None = None,
    reasoning: str,
) -> Thesis:
    """Transition attestation placeholder <-> underwritten (0042, D4/R9).

    The ONLY write path for theses.attestation — like governance_status, it is
    deliberately not in REVISABLE_FIELDS. No governance_events row is needed:
    the 0034 trigger is BEFORE UPDATE OF governance_status only and this
    UPDATE never touches that column.

    To 'underwritten' (the underwriting gate), hard-fails unless:
      - basis is non-empty (stored in attestation_basis; DB CHECK backstop)
      - the ladder is coherent (service mirror of the
        theses_ladder_coherent_long_v1 CHECK, readable error; the CHECK fires
        on this UPDATE as the backstop — KD-4: you mechanically cannot attest
        an incoherent ladder)
      - the stop is not currently breached vs the latest close (the BB gate —
        service-only, cross-table, cannot be a CHECK). A set stop with NO
        price history at all also refuses: an unverifiable stop cannot be
        underwritten (conservative reading).
      - every condition's baseline is current at PARSER_VERSION: stale-version
        baselines are re-parsed; identical kind+threshold → parser_version
        silently refreshed; drifted → hard-fail (the enforced promise only
        changes by human re-authoring, design §7.2).

    Demotion to 'placeholder' is always allowed with reasoning;
    attestation_basis is cleared so a stale basis can never imply
    underwriting.

    Does NOT touch last_revisited_at/revisit_due_at — attestation is a rule-
    integrity act, not a thesis-content revisit (same stance as
    approve_object()).
    """
    if to not in _VALID_ATTESTATIONS:
        raise ValueError(f"to must be one of {list(_VALID_ATTESTATIONS)}, got {to!r}")
    if not reasoning or not reasoning.strip():
        raise ValueError("reasoning is required for an attestation change")

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theses WHERE thesis_id = $1 FOR UPDATE", thesis_id
        )
        if existing is None:
            raise ValueError(f"Thesis {thesis_id} not found")
        old = existing["attestation"]
        if old == to:
            raise ValueError(f"Thesis {thesis_id} attestation is already {to!r}")

        new_basis: str | None
        if to == "underwritten":
            if not basis or not basis.strip():
                raise ValueError(
                    f"Cannot attest thesis {thesis_id} as underwritten without a "
                    "basis. Use: asx thesis attest "
                    f"{thesis_id} --basis '...'"
                )
            findings = lint.lint_ladder(
                stop_price=existing["stop_price"],
                entry_band_lower=existing["entry_band_lower"],
                entry_band_upper=existing["entry_band_upper"],
                target_price=existing["target_price"],
            )
            if findings:
                details = "; ".join(f"[{f.code}] {f.message}" for f in findings)
                raise ValueError(
                    f"Cannot attest thesis {thesis_id} — ladder incoherent: {details}"
                )
            if existing["stop_price"] is not None:
                price_row = await conn.fetchrow(
                    """
                    SELECT close, dt FROM prices
                    WHERE symbol = $1
                    ORDER BY dt DESC LIMIT 1
                    """,
                    existing["symbol"],
                )
                if price_row is None:
                    raise ValueError(
                        f"Cannot attest thesis {thesis_id} — no price history for "
                        f"{existing['symbol']} to verify the stop against (BB gate)"
                    )
                bb = lint.lint_born_breached(
                    stop_price=existing["stop_price"],
                    latest_close=Decimal(str(price_row["close"])),
                )
                if bb is not None:
                    raise ValueError(
                        f"Cannot attest thesis {thesis_id} — [{bb.code}] {bb.message} "
                        f"(latest close {price_row['close']} on {price_row['dt']})"
                    )
            cond_rows = await conn.fetch(
                """
                SELECT condition_id, ordinal, condition_text, enforcement_kind,
                       enforcement_threshold, parser_version
                FROM thesis_conditions
                WHERE thesis_id = $1 AND status <> 'resolved'
                ORDER BY ordinal
                """,
                thesis_id,
            )
            for c in cond_rows:
                if c["parser_version"] == PARSER_VERSION:
                    continue
                reparsed = parse_condition(c["condition_text"])
                if (
                    reparsed.kind == c["enforcement_kind"]
                    and reparsed.threshold == c["enforcement_threshold"]
                ):
                    await conn.execute(
                        """
                        UPDATE thesis_conditions
                        SET parser_version = $1, updated_at = NOW()
                        WHERE condition_id = $2
                        """,
                        PARSER_VERSION,
                        c["condition_id"],
                    )
                else:
                    raise ValueError(
                        f"Cannot attest thesis {thesis_id} — condition "
                        f"{c['ordinal']} baseline drifted: stored "
                        f"{c['enforcement_kind']}/{c['enforcement_threshold']} "
                        f"(parser {c['parser_version']}) vs current "
                        f"{reparsed.kind}/{reparsed.threshold} ({PARSER_VERSION}). "
                        "Re-author the condition (asx thesis condition add + "
                        "resolve the old one) so the enforced promise is the "
                        "one you attest."
                    )
            new_basis = basis.strip()
        else:
            # Demotion — always allowed; clear the basis so it cannot go stale.
            new_basis = None

        row = await conn.fetchrow(
            """
            UPDATE theses
            SET attestation = $1, attestation_basis = $2
            WHERE thesis_id = $3
            RETURNING *
            """,
            to,
            new_basis,
            thesis_id,
        )
        await _insert_revision(
            conn,
            thesis_id=thesis_id,
            revised_at=_now_utc(),
            revision_type="attestation_change",
            diff={"attestation": {"old": old, "new": to}},
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
      - attestation is not 'underwritten'  (migration 0042 — D4/R9's
        capital-eligibility gate, distinct from born-approved governance:
        capital never deploys against a placeholder)
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
        if existing["attestation"] != "underwritten":
            raise ValueError(
                f"Cannot enter thesis {thesis_id} — attestation is "
                f"{existing['attestation']!r}, must be 'underwritten'. Capital "
                "never deploys against a placeholder rule set (D4/R9). Attest "
                f"first: asx thesis attest {thesis_id} --basis '...'"
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
