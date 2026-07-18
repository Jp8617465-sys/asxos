"""Theme domain service — M-Thesis-1.

All multi-statement functions use ``async with conn.transaction():``.
Stage enum values and conviction_band values are validated against the
DB CHECK constraint values — raise ValueError on mismatch (hard-fail).

References:
  migration 0012_theses_and_themes.sql
  M-THESIS-1_IMPLEMENTATION_PLAN_V2.md §4 Phase 3
  spec Part 6.2 (themes) + Part 6.3 (theme_holdings)
  CLAUDE.md non-negotiables #1, #5, #10
"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import asyncpg

from asxos.domain.governance import transitions as governance_transitions
from asxos.domain.themes.types import CoverageSegment, Theme, ThemeHolding
from asxos.domain.theses.schemas import ThemeHoldingProposal, ThemeProposal

_VALID_STAGES = frozenset(
    ("early", "early-institutional", "broad-institutional", "mainstream", "late-retail", "mature")
)
_VALID_CONVICTION_BANDS = frozenset(("low", "medium", "high"))
_VALID_DIRECTIONS = frozenset(("positive", "negative"))
_VALID_SOURCES = frozenset(("user", "llm_inferred", "system_default"))
_REJECTABLE_FROM = {"draft", "evidence_complete", "pending_review"}


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _row_to_theme(row: asyncpg.Record) -> Theme:
    return Theme(
        theme_id=row["theme_id"],
        theme_code=row["theme_code"],
        name=row["name"],
        description=row["description"],
        conviction_band=row["conviction_band"],
        stage=row["stage"],
        stage_suggested=row["stage_suggested"],
        adjacent_codes=tuple(row["adjacent_codes"] or []),
        started_at=row["started_at"],
        retired_at=row["retired_at"],
        last_reviewed_at=row["last_reviewed_at"],
        # migration 0035 fields — .get() with a fallback, not row[...], so a
        # pre-migration-shaped fixture row dict doesn't KeyError.
        macro_thesis_id=row.get("macro_thesis_id"),
        governance_status=row.get("governance_status", "approved"),
        source_run_id=row.get("source_run_id"),
    )


def _row_to_theme_holding(row: asyncpg.Record) -> ThemeHolding:
    return ThemeHolding(
        theme_id=row["theme_id"],
        symbol=row["symbol"],
        exposure_strength=row["exposure_strength"],
        direction=row["direction"],
        mechanism_text=row["mechanism_text"],
        source=row["source"],
        last_validated_at=row["last_validated_at"],
        note=row["note"],
        created_at=row["created_at"],
        # migration 0035 fields
        holding_id=row.get("holding_id"),
        governance_status=row.get("governance_status", "approved"),
        source_run_id=row.get("source_run_id"),
    )


async def create_theme(
    conn: asyncpg.Connection,
    theme_code: str,
    name: str,
    description: str,
    *,
    conviction_band: str = "medium",
    stage: str = "early",
    started_at: date | None = None,
) -> Theme:
    """Create a new investment theme.

    theme_code is a slug identifier: 'ai-infrastructure', 'lithium-oversupply-unwinding'.
    It must be unique — DB raises IntegrityError on duplicate.

    Raises ValueError if conviction_band or stage values are not in the
    permitted set (mirrors the DB CHECK constraints).
    """
    if conviction_band not in _VALID_CONVICTION_BANDS:
        raise ValueError(
            f"conviction_band must be one of {sorted(_VALID_CONVICTION_BANDS)}, "
            f"got {conviction_band!r}"
        )
    if stage not in _VALID_STAGES:
        raise ValueError(
            f"stage must be one of {sorted(_VALID_STAGES)}, got {stage!r}"
        )
    if not description:
        raise ValueError("description is required for a theme")

    now = _now_utc()
    _started = started_at or date.today()

    row = await conn.fetchrow(
        """
        INSERT INTO themes
            (theme_code, name, description, conviction_band, stage,
             started_at, last_reviewed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        theme_code,
        name,
        description,
        conviction_band,
        stage,
        _started,
        now,
    )
    return _row_to_theme(row)


async def get_theme(conn: asyncpg.Connection, theme_code: str) -> Theme | None:
    """Fetch a theme by its slug code. Returns None if not found."""
    row = await conn.fetchrow(
        "SELECT * FROM themes WHERE theme_code = $1", theme_code
    )
    return _row_to_theme(row) if row else None


async def list_themes(conn: asyncpg.Connection) -> list[Theme]:
    """List all themes ordered by theme_code."""
    rows = await conn.fetch(
        "SELECT * FROM themes ORDER BY theme_code"
    )
    return [_row_to_theme(r) for r in rows]


async def list_theme_holdings(
    conn: asyncpg.Connection, theme_code: str
) -> list[ThemeHolding]:
    """List all symbol-level holdings for a theme."""
    rows = await conn.fetch(
        """
        SELECT th.*
        FROM theme_holdings th
        JOIN themes t ON t.theme_id = th.theme_id
        WHERE t.theme_code = $1
        ORDER BY th.symbol
        """,
        theme_code,
    )
    return [_row_to_theme_holding(r) for r in rows]


async def get_coverage_rollup(conn: asyncpg.Connection) -> list[CoverageSegment]:
    """Universe -> segment coverage rollup (`asx theme coverage`).

    Answers "where am I structurally blind" directly (docs/proposals/
    thesis-coverage-framework-2026-07-11.md Tier 1a): for every segment —
    (security_kind, sector) for au_equity, one bucket per non-equity
    security_kind — how many active universe symbols exist, and how many of
    those have >=1 theme_holdings row / >=1 theses row.

    Read-only rollup over existing, fully-populated columns
    (universe.security_kind, universe.sector, theme_holdings, theses) — no
    migration, no new table. Pure SELECT; safe on the read-only DB role.
    """
    rows = await conn.fetch(
        """
        WITH base AS (
            SELECT
                u.symbol,
                u.security_kind,
                CASE WHEN u.security_kind = 'au_equity'
                     THEN COALESCE(NULLIF(u.sector, ''), 'Unclassified')
                     ELSE NULL END AS sector
            FROM universe u
            WHERE u.is_active
        ),
        theme_covered AS (SELECT DISTINCT symbol FROM theme_holdings),
        thesis_covered AS (SELECT DISTINCT symbol FROM theses)
        SELECT
            b.security_kind,
            b.sector,
            COUNT(*) AS symbol_count,
            COUNT(*) FILTER (WHERE tc.symbol IS NOT NULL) AS theme_covered_count,
            COUNT(*) FILTER (WHERE hc.symbol IS NOT NULL) AS thesis_covered_count
        FROM base b
        LEFT JOIN theme_covered tc ON tc.symbol = b.symbol
        LEFT JOIN thesis_covered hc ON hc.symbol = b.symbol
        GROUP BY b.security_kind, b.sector
        ORDER BY b.security_kind, symbol_count DESC
        """
    )
    return [
        CoverageSegment(
            security_kind=r["security_kind"],
            sector=r["sector"],
            symbol_count=r["symbol_count"],
            theme_covered_count=r["theme_covered_count"],
            thesis_covered_count=r["thesis_covered_count"],
        )
        for r in rows
    ]


async def add_adjacency(
    conn: asyncpg.Connection, code_a: str, code_b: str
) -> None:
    """Add a bidirectional adjacency between two themes.

    Appends code_b to A's adjacent_codes and code_a to B's adjacent_codes.
    Uses array_append with a guard to avoid duplicates (no-op if already adjacent).

    Hard-fails if either theme_code does not exist.
    """
    async with conn.transaction():
        for code in (code_a, code_b):
            exists = await conn.fetchval(
                "SELECT theme_id FROM themes WHERE theme_code = $1", code
            )
            if exists is None:
                raise ValueError(f"Theme code {code!r} not found")

        # code_b → A; guard: only append if not already present
        await conn.execute(
            """
            UPDATE themes
            SET adjacent_codes = array_append(adjacent_codes, $1)
            WHERE theme_code = $2
              AND NOT ($1 = ANY(adjacent_codes))
            """,
            code_b,
            code_a,
        )
        # code_a → B
        await conn.execute(
            """
            UPDATE themes
            SET adjacent_codes = array_append(adjacent_codes, $1)
            WHERE theme_code = $2
              AND NOT ($1 = ANY(adjacent_codes))
            """,
            code_a,
            code_b,
        )


async def set_stage(
    conn: asyncpg.Connection,
    theme_code: str,
    stage: str,
    note: str,
) -> Theme:
    """Set the user-confirmed stage for a theme.

    This updates `themes.stage` (user-confirmed). It does NOT touch
    `stage_suggested` — that is written only by the M-Theme-Stage-Detection
    auto-classifier (future milestone).

    Raises ValueError if stage not in the permitted set or note is empty.
    """
    if stage not in _VALID_STAGES:
        raise ValueError(
            f"stage must be one of {sorted(_VALID_STAGES)}, got {stage!r}"
        )
    if not note or not note.strip():
        raise ValueError("note is required when setting stage — state why you believe the theme is at this stage")

    now = _now_utc()
    row = await conn.fetchrow(
        """
        UPDATE themes
        SET stage = $1, last_reviewed_at = $2
        WHERE theme_code = $3
        RETURNING *
        """,
        stage,
        now,
        theme_code,
    )
    if row is None:
        raise ValueError(f"Theme code {theme_code!r} not found")
    return _row_to_theme(row)


async def attach_thesis(
    conn: asyncpg.Connection,
    theme_code: str,
    symbol: str,
    *,
    exposure_strength: Decimal,
    direction: str = "positive",
    mechanism_text: str = "",
    source: str = "user",
    note: str | None = None,
) -> ThemeHolding:
    """Attach or update a symbol's exposure to a theme.

    PK is (theme_id, symbol) — one row per stock-theme pair, per spec Part 6.3.
    This row persists across thesis lifecycle. If the row already exists,
    updates exposure_strength, direction, mechanism_text, source, last_validated_at.

    Also updates theses.themes TEXT[] for any open (non-exited/expired) theses
    on this symbol, so the denormalised array stays in sync.

    Raises ValueError if:
      - theme_code does not exist
      - direction not in ('positive', 'negative')
      - source not in ('user', 'llm_inferred', 'system_default')
      - exposure_strength not in [0, 1]
    """
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {sorted(_VALID_DIRECTIONS)}, got {direction!r}")
    if source not in _VALID_SOURCES:
        raise ValueError(f"source must be one of {sorted(_VALID_SOURCES)}, got {source!r}")
    if not (Decimal("0") <= exposure_strength <= Decimal("1")):
        raise ValueError(
            f"exposure_strength must be in [0, 1], got {exposure_strength}"
        )

    now = _now_utc()

    async with conn.transaction():
        theme_row = await conn.fetchrow(
            "SELECT theme_id FROM themes WHERE theme_code = $1", theme_code
        )
        if theme_row is None:
            raise ValueError(
                f"Theme code {theme_code!r} not found. "
                f"Create it first: `asx theme create {theme_code} --name '...' --description '...'`"
            )
        theme_id: int = theme_row["theme_id"]

        row = await conn.fetchrow(
            """
            INSERT INTO theme_holdings
                (theme_id, symbol, exposure_strength, direction,
                 mechanism_text, source, last_validated_at, note, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $7)
            ON CONFLICT (theme_id, symbol) DO UPDATE
                SET exposure_strength  = EXCLUDED.exposure_strength,
                    direction          = EXCLUDED.direction,
                    mechanism_text     = EXCLUDED.mechanism_text,
                    source             = EXCLUDED.source,
                    last_validated_at  = EXCLUDED.last_validated_at,
                    note               = EXCLUDED.note
            RETURNING *
            """,
            theme_id,
            symbol,
            exposure_strength,
            direction,
            mechanism_text,
            source,
            now,
            note,
        )

        # Sync the denormalised theses.themes TEXT[] for open theses on this symbol.
        # Only adds the code; never removes (removal is via detach_thesis).
        await conn.execute(
            """
            UPDATE theses
            SET themes = array_append(themes, $1)
            WHERE symbol = $2
              AND status NOT IN ('exited', 'expired')
              AND NOT ($1 = ANY(themes))
            """,
            theme_code,
            symbol,
        )

        return _row_to_theme_holding(row)


async def retire_theme(
    conn: asyncpg.Connection,
    theme_code: str,
    retired_at: date | None = None,
) -> Theme:
    """Mark a theme as retired (no longer investable).

    Sets retired_at to the given date (default: today). The theme row is
    preserved — history is not deleted.
    """
    _retired = retired_at or date.today()
    row = await conn.fetchrow(
        """
        UPDATE themes
        SET retired_at = $1
        WHERE theme_code = $2
        RETURNING *
        """,
        _retired,
        theme_code,
    )
    if row is None:
        raise ValueError(f"Theme code {theme_code!r} not found")
    return _row_to_theme(row)


async def approve_theme(conn: asyncpg.Connection, theme_id: int, *, reasoning: str) -> Theme:
    """Transition a theme from pending_review to approved.

    No agent producer exists yet for object_type='theme' (that's Phase 2c's
    instrument-selector/theme-researcher work) — this function exists now so
    the themes_governance_audit trigger (migration 0036) has a service-layer
    path to test against, and so a human can manually approve a theme that
    was ever hand-created at a non-'approved' governance_status. Unlike
    theses/service.py::approve_object(), there is no evidence-staleness gate
    here: nothing produces agent-originated themes yet, so there is no
    evidence to check the staleness of.
    """
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM themes WHERE theme_id = $1 FOR UPDATE", theme_id
        )
        if existing is None:
            raise ValueError(f"Theme {theme_id} not found")
        if existing["governance_status"] != "pending_review":
            raise ValueError(
                f"Cannot approve theme {theme_id} — governance_status is "
                f"{existing['governance_status']!r}, expected 'pending_review'."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to approve a theme")

        row = await governance_transitions.apply_governance_transition(
            conn,
            table_name="themes",
            id_column="theme_id",
            object_type="theme",
            object_id=theme_id,
            from_status=existing["governance_status"],
            to_status="approved",
            reasoning=reasoning,
        )
        return _row_to_theme(row)


async def reject_theme(conn: asyncpg.Connection, theme_id: int, *, reasoning: str) -> Theme:
    """Transition a theme from draft/evidence_complete/pending_review to
    rejected. See approve_theme()'s docstring for why there's no evidence
    check here (the contrast is with theses/service.py::approve_object();
    theses' own reject_object() has no evidence check either)."""
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM themes WHERE theme_id = $1 FOR UPDATE", theme_id
        )
        if existing is None:
            raise ValueError(f"Theme {theme_id} not found")
        if existing["governance_status"] not in _REJECTABLE_FROM:
            raise ValueError(
                f"Cannot reject theme {theme_id} — governance_status is "
                f"{existing['governance_status']!r}, expected one of "
                f"{sorted(_REJECTABLE_FROM)}."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to reject a theme")

        row = await governance_transitions.apply_governance_transition(
            conn,
            table_name="themes",
            id_column="theme_id",
            object_type="theme",
            object_id=theme_id,
            from_status=existing["governance_status"],
            to_status="rejected",
            reasoning=reasoning,
        )
        return _row_to_theme(row)


async def approve_theme_holding(
    conn: asyncpg.Connection, holding_id: int, *, reasoning: str
) -> ThemeHolding:
    """Transition a theme_holding from pending_review to approved.

    Takes holding_id (the migration 0035 surrogate key), never the composite
    (theme_id, symbol) natural key — this is the entire reason the surrogate
    was added (governance_events.object_id needs one BIGINT uniformly). See
    approve_theme()'s docstring for why there's no evidence check here.
    """
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theme_holdings WHERE holding_id = $1 FOR UPDATE", holding_id
        )
        if existing is None:
            raise ValueError(f"Theme holding {holding_id} not found")
        if existing["governance_status"] != "pending_review":
            raise ValueError(
                f"Cannot approve theme holding {holding_id} — governance_status is "
                f"{existing['governance_status']!r}, expected 'pending_review'."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to approve a theme holding")

        row = await governance_transitions.apply_governance_transition(
            conn,
            table_name="theme_holdings",
            id_column="holding_id",
            object_type="theme_holding",
            object_id=holding_id,
            from_status=existing["governance_status"],
            to_status="approved",
            reasoning=reasoning,
        )
        return _row_to_theme_holding(row)


async def reject_theme_holding(
    conn: asyncpg.Connection, holding_id: int, *, reasoning: str
) -> ThemeHolding:
    """Transition a theme_holding from draft/evidence_complete/pending_review
    to rejected. Takes holding_id, not (theme_id, symbol) — see
    approve_theme_holding()'s docstring."""
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT * FROM theme_holdings WHERE holding_id = $1 FOR UPDATE", holding_id
        )
        if existing is None:
            raise ValueError(f"Theme holding {holding_id} not found")
        if existing["governance_status"] not in _REJECTABLE_FROM:
            raise ValueError(
                f"Cannot reject theme holding {holding_id} — governance_status is "
                f"{existing['governance_status']!r}, expected one of "
                f"{sorted(_REJECTABLE_FROM)}."
            )
        if not reasoning or not reasoning.strip():
            raise ValueError("reasoning is required to reject a theme holding")

        row = await governance_transitions.apply_governance_transition(
            conn,
            table_name="theme_holdings",
            id_column="holding_id",
            object_type="theme_holding",
            object_id=holding_id,
            from_status=existing["governance_status"],
            to_status="rejected",
            reasoning=reasoning,
        )
        return _row_to_theme_holding(row)


async def create_theme_from_agent_run(
    conn: asyncpg.Connection,
    run_id: int,
    *,
    reasoning: str = "Draft created from agent run",
) -> Theme:
    """Validate agent_runs.proposed_object against ThemeProposal and insert a
    themes row, then advance draft -> evidence_complete -> pending_review in
    the SAME transaction — mirrors
    asxos/domain/macro_theses/service.py::create_macro_thesis_from_agent_run(),
    the reference implementation for every --from-agent-run path.

    One deliberate divergence from that reference: themes.governance_status
    DEFAULTs to 'approved' (migration 0035 grandfathers pre-existing
    human-authored rows), unlike macro_theses' DEFAULT 'draft' — so the
    INSERT here must set governance_status='draft' EXPLICITLY, or an
    agent-originated theme would be born approved and bypass the entire
    human-review gate this function exists to feed.

    proposed_object round-trips as JSONB text (no asyncpg codec registered —
    asxos/db.py) — parsed with parse_float=Decimal per theses/schemas.py's
    documented hazard. evidence_citation_ids' tier/existence check ran at log
    time (agent_run_service.log_agent_run); agent_evidence rows are
    append-only, so it is not repeated here.

    Raises ValueError if run_id does not exist, was already acted_on, or has
    object_type != 'theme'.
    """
    async with conn.transaction():
        run = await conn.fetchrow(
            "SELECT * FROM agent_runs WHERE run_id = $1 FOR UPDATE", run_id
        )
        if run is None:
            raise ValueError(f"agent_runs row {run_id} not found")
        if run["acted_on"]:
            raise ValueError(f"agent_runs row {run_id} was already acted on")
        if run["object_type"] != "theme":
            raise ValueError(
                f"agent_runs row {run_id} has object_type={run['object_type']!r} "
                "— create_theme_from_agent_run() only accepts object_type='theme' rows."
            )

        proposal_dict = json.loads(run["proposed_object"], parse_float=Decimal)
        proposal = ThemeProposal(**proposal_dict)

        existing = await conn.fetchrow(
            "SELECT theme_id FROM themes WHERE theme_code = $1", proposal.theme_code
        )
        if existing is not None:
            raise ValueError(
                f"theme_code {proposal.theme_code!r} already exists "
                f"(theme_id={existing['theme_id']}) — the agent re-proposed an "
                "existing theme; review that theme instead of duplicating it."
            )

        now = _now_utc()
        row = await conn.fetchrow(
            """
            INSERT INTO themes
                (theme_code, name, description, conviction_band, stage,
                 started_at, last_reviewed_at, macro_thesis_id,
                 governance_status, source_run_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'draft', $9)
            RETURNING *
            """,
            proposal.theme_code,
            proposal.name,
            proposal.description,
            proposal.conviction_band,
            proposal.stage,
            date.today(),
            now,
            proposal.macro_thesis_id,
            run_id,
        )
        theme_id = row["theme_id"]

        await governance_transitions.apply_governance_transition(
            conn,
            table_name="themes",
            id_column="theme_id",
            object_type="theme",
            object_id=theme_id,
            from_status="draft",
            to_status="evidence_complete",
            reasoning=reasoning,
            actor="agent",
        )
        row = await governance_transitions.apply_governance_transition(
            conn,
            table_name="themes",
            id_column="theme_id",
            object_type="theme",
            object_id=theme_id,
            from_status="evidence_complete",
            to_status="pending_review",
            reasoning=reasoning,
            actor="agent",
        )

        await conn.execute(
            "UPDATE agent_runs SET acted_on = TRUE, resulting_object_id = $1 WHERE run_id = $2",
            theme_id,
            run_id,
        )

        return _row_to_theme(row)


async def create_theme_holding_from_agent_run(
    conn: asyncpg.Connection,
    run_id: int,
    *,
    reasoning: str = "Draft created from agent run",
) -> ThemeHolding:
    """Validate agent_runs.proposed_object against ThemeHoldingProposal and
    insert a theme_holdings row (source='llm_inferred' — the first real use
    of that migration-0012 enum value), then advance draft ->
    evidence_complete -> pending_review in the SAME transaction.

    The proposal references its theme by theme_code; the theme row must
    already exist (a same-run ThemeProposal is materialised FIRST by the
    orchestrating command — this function never creates themes implicitly).

    Deliberately a plain INSERT, never ON CONFLICT DO UPDATE: an existing
    (theme_id, symbol) row means the agent re-proposed already-covered
    exposure, and silently overwriting human-reviewed content with agent
    content would bypass the review gate. Fail loudly instead (CLAUDE.md #10).

    Same governance_status='draft' explicitness as create_theme_from_agent_run
    (theme_holdings also DEFAULTs to 'approved', migration 0035).

    Raises ValueError if run_id does not exist / was acted_on / has
    object_type != 'theme_holding', if the theme_code does not resolve, or if
    the (theme, symbol) exposure already exists.
    """
    async with conn.transaction():
        run = await conn.fetchrow(
            "SELECT * FROM agent_runs WHERE run_id = $1 FOR UPDATE", run_id
        )
        if run is None:
            raise ValueError(f"agent_runs row {run_id} not found")
        if run["acted_on"]:
            raise ValueError(f"agent_runs row {run_id} was already acted on")
        if run["object_type"] != "theme_holding":
            raise ValueError(
                f"agent_runs row {run_id} has object_type={run['object_type']!r} "
                "— create_theme_holding_from_agent_run() only accepts "
                "object_type='theme_holding' rows."
            )

        proposal_dict = json.loads(run["proposed_object"], parse_float=Decimal)
        proposal = ThemeHoldingProposal(**proposal_dict)

        theme = await conn.fetchrow(
            "SELECT theme_id FROM themes WHERE theme_code = $1", proposal.theme_code
        )
        if theme is None:
            raise ValueError(
                f"theme_code {proposal.theme_code!r} does not resolve to a themes row "
                "— a same-run ThemeProposal must be materialised (asx theme open "
                "--from-agent-run) before its holdings."
            )
        theme_id = theme["theme_id"]

        existing = await conn.fetchrow(
            "SELECT holding_id FROM theme_holdings WHERE theme_id = $1 AND symbol = $2",
            theme_id,
            proposal.symbol,
        )
        if existing is not None:
            raise ValueError(
                f"theme_holdings already has ({proposal.theme_code}, {proposal.symbol}) "
                f"(holding_id={existing['holding_id']}) — the agent re-proposed covered "
                "exposure; review the existing row instead of overwriting it."
            )

        now = _now_utc()
        row = await conn.fetchrow(
            """
            INSERT INTO theme_holdings
                (theme_id, symbol, exposure_strength, direction, mechanism_text,
                 source, last_validated_at, created_at, governance_status,
                 source_run_id)
            VALUES ($1, $2, $3, $4, $5, 'llm_inferred', $6, $6, 'draft', $7)
            RETURNING *
            """,
            theme_id,
            proposal.symbol,
            proposal.exposure_strength,
            proposal.direction,
            proposal.mechanism_text,
            now,
            run_id,
        )
        holding_id = row["holding_id"]

        await governance_transitions.apply_governance_transition(
            conn,
            table_name="theme_holdings",
            id_column="holding_id",
            object_type="theme_holding",
            object_id=holding_id,
            from_status="draft",
            to_status="evidence_complete",
            reasoning=reasoning,
            actor="agent",
        )
        row = await governance_transitions.apply_governance_transition(
            conn,
            table_name="theme_holdings",
            id_column="holding_id",
            object_type="theme_holding",
            object_id=holding_id,
            from_status="evidence_complete",
            to_status="pending_review",
            reasoning=reasoning,
            actor="agent",
        )

        await conn.execute(
            "UPDATE agent_runs SET acted_on = TRUE, resulting_object_id = $1 WHERE run_id = $2",
            holding_id,
            run_id,
        )

        return _row_to_theme_holding(row)
