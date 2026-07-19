# Proposal: `theses.report_sections` migration (Phase C, migration 0040)

**Status:** proposed — arbi cannot write to `migrations/` (authority-guarded, same
mechanism as the agent-RO frontmatter proposal). James applies via
`mcp__supabase__apply_migration` (project `gxjqezqndltaelmyctnl`), checks the file into
`migrations/0040_thesis_report_sections.sql`, and bumps `REQUIRED_MIGRATIONS` in
`asxos/api/main.py` to the observed post-apply count.

**Companion code:** the Python/CLI side of Phase C (persist + render) is already built and
tested in the accompanying draft PR — `asxos/domain/theses/{types,service}.py`,
`asxos/cli/thesis.py`, plus `tests/test_thesis_service.py` / `tests/test_cli_thesis.py`. That
code reads `row.get("report_sections")` defensively, so it does not crash pre-migration — but
`asx thesis add-section` will fail with a Postgres "column does not exist" error until this
migration is applied. **This migration is a hard prerequisite for the feature to work at all,**
not an optional follow-up.

**Additive, safe, non-destructive:** `ADD COLUMN ... NOT NULL DEFAULT '[]'::jsonb` is a
metadata-only change in Postgres ≥11 (no table rewrite, no lock escalation). Every existing
`theses` row reads back `report_sections = []` with zero behavior change. No dependent-object
check needed per `.claude/rules/api-conventions.md` (nothing can depend on a column that didn't
exist).

**Pre-apply check (per `api-conventions.md`) — not applicable here**, since this is a pure
`ADD COLUMN`, not an `ALTER`/`DROP` on an existing column. No dependent-object query needed.

## Exact SQL

```sql
-- migrations/0040_thesis_report_sections.sql
--
-- Broker-report thesis persistence — Phase C (docs/proposals/broker-report-
-- rubric-2026-07-18.md; keystone schema landed dark in #56,
-- asxos/domain/theses/schemas.py — ReportSection/ReportFigure). Gives
-- ThesisProposal.sections somewhere to live on an EXISTING theses row for
-- the human-authored path (asx thesis add-section). The agent-drafted
-- whole-ThesisProposal path (create_thesis_from_agent_run, Phase E) is a
-- separate, still-stubbed consumer of the same ReportSection/ReportFigure
-- models and is unaffected by this migration.
--
-- Applied via: mcp__supabase__apply_migration (project gxjqezqndltaelmyctnl).
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the
-- observed SELECT count(*) FROM supabase_migrations.schema_migrations
-- (not a guessed +1 — api-conventions.md).

ALTER TABLE theses
    ADD COLUMN IF NOT EXISTS report_sections JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN theses.report_sections IS
    'Array of ReportSection (asxos/domain/theses/schemas.py), each with '
    'figures: list[ReportFigure]. Decimal values are JSON strings '
    '(Pydantic model_dump(mode="json") contract) -- never a bare JSON '
    'number. Written only via asxos.domain.theses.service.add_report_section(), '
    'which re-validates through ReportSection/ReportFigure on every write '
    '(prose-only body, monitor_only barred from basis sections). Phase C '
    'first cut: provenance is always james_input. Does not participate in '
    'the theses_governance_audit trigger (migration 0034) -- that trigger '
    'is BEFORE UPDATE OF governance_status only.';
```

## Why JSONB-on-`theses`, not a normalized `thesis_report_sections` table

Exact precedent already on this table: `invalidation_conditions JSONB NOT NULL DEFAULT
'[]'::jsonb` (migration 0012). Both are small (≤10 kinds), Pydantic-validated-wholesale arrays
that are always read/written as a complete per-thesis unit and have no identity outside their
thesis — the same reasoning `.claude/rules/portfolio-conventions.md` already applies to keep
`theme_holdings` governance inside `themes/service.py` rather than a fourth package ("it has no
identity outside a theme"). Contrast: `thesis_evidence` (migration 0033) genuinely is a
normalized table because it needs independent per-row operations (tier filtering, staleness
checks, per-row supersession) — report sections need none of that in this cut.

## Governance trigger interaction — verified, not assumed

Read the live trigger definition directly: `migrations/0034_governance_audit_trigger_and_
revision_provenance.sql:137-139` — `CREATE TRIGGER theses_governance_audit BEFORE UPDATE OF
governance_status ON theses`. This is column-scoped; it only fires when `governance_status` is
in the UPDATE's target list. `add_report_section()`'s UPDATE never touches that column, so the
trigger cannot fire — no `governance_events` row is required for this write path. This is the
kind of thing `.claude/rules/portfolio-conventions.md`'s "Verification lesson" section says to
check against real SQL rather than assume; done here, not inferred.

## Deferred (deliberately, to keep this a one-statement migration)

Widening `thesis_revisions.revision_type`'s CHECK constraint with a new
`'report_section_updated'` value. `add_report_section()` reuses the existing
`'assumption_change'` bucket (already home to `thesis_text`/`invalidation_conditions`/
`conviction_level`/`tax_notes` — i.e. "narrative/assumption content changed"). Real, but a
separate, later change if a distinct revision-type label proves useful.

## After applying

1. Bump `REQUIRED_MIGRATIONS` in `asxos/api/main.py` to the observed count.
2. Verify: `asx thesis add-section CBA.AU --kind moat --body "Durable network effects." --figure "Fair value=130.50"` then `asx thesis show CBA.AU --full-report`.
3. Merge the companion draft PR (Phase C code) — it is safe to merge before or after this
   migration; the code degrades gracefully pre-migration (every read is `.get()`-defensive), it
   simply cannot *write* a section until the column exists.
