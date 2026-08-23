-- Broker-report thesis persistence -- Phase C (docs/proposals/broker-report-
-- rubric-2026-07-18.md; keystone schema landed dark in #56,
-- asxos/domain/theses/schemas.py -- ReportSection/ReportFigure). Gives
-- ThesisProposal.sections somewhere to live on an EXISTING theses row for
-- the human-authored path (asx thesis add-section). The agent-drafted
-- whole-ThesisProposal path (create_thesis_from_agent_run, Phase E) is a
-- separate, still-stubbed consumer of the same ReportSection/ReportFigure
-- models and is unaffected by this migration.
--
-- PROVENANCE NOTE (2026-07-21): this file was reconstructed verbatim from
-- supabase_migrations.schema_migrations.statements (version 20260719053844,
-- applied 2026-07-19T05:38:44Z) after the 2026-07-21 wake found the count
-- drift (DB=94, REQUIRED_MIGRATIONS=93, 39 files on disk) -- the migration
-- was applied to prod without its file ever being committed. The DDL below
-- is the DB's own record of what ran, byte-for-byte; only this provenance
-- comment block was added.

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
