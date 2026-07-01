-- 0034_governance_audit_trigger_and_revision_provenance.sql
--
-- Governance schema, Phase 1 continued -- the bypass-prevention trigger
-- (governance-first-architecture-2026-06-30.md Section 4.7) and
-- thesis_revisions provenance columns (Section 4.2).
--
-- THE TRIGGER IS THE LOAD-BEARING GUARANTEE of the whole governance layer --
-- without it, governance_status='approved' is a service-layer convention
-- only, bypassable by any direct UPDATE, a one-off script, or a future AI
-- session with less context than the one that designed this. This codebase
-- has zero prior CREATE TRIGGER / RETURNS TRIGGER precedent (one prior
-- precedent for a plain PL/pgSQL function, set_active_profile() in migration
-- 0005, but nothing that fires implicitly on DML) -- kept deliberately
-- minimal: one shared function, one trigger, on theses only. macro_theses/
-- themes/theme_holdings triggers are Phase 2 (they don't exist as governed
-- tables yet -- Phase 1 does not touch them).
--
-- Fix vs. the design doc's original draft: the doc used a 5-second event_at
-- time window. That has a real bypass gap -- a legitimate governance_events
-- row from an EARLIER, UNRELATED transaction within the window satisfies the
-- trigger for a completely different, unaudited UPDATE on the same object
-- (the check was never actually "same transaction", just "recent enough").
-- Fixed here by checking pg_current_xact_id() equality instead -- a value
-- Postgres already tracks precisely, not a tunable/guessable window.
-- Verified stable within a single statement via manual check before applying
-- this migration (session record: two pg_current_xact_id() calls in one
-- SELECT returned identical values).
--
-- SECOND fix, discovered while applying this migration: the originally
-- planned design used ONE shared trigger function across all 4 governed
-- tables (theses/macro_theses/themes/theme_holdings), dispatching on
-- TG_ARGV[0] with a CASE over NEW.thesis_id / NEW.macro_thesis_id / etc.
-- This fails at runtime with "record NEW has no field macro_thesis_id" --
-- PL/pgSQL validates NEW/OLD field references against the table the
-- trigger is bound to for EVERY CASE branch, not just the one that
-- executes. A function bound to `theses` cannot reference NEW.theme_id
-- even in a branch that never runs. Fixed by writing a theses-specific
-- function (_check_theses_governance_audit(), no TG_ARGV, no CASE) instead
-- of a premature cross-table abstraction. Phase 2 should write its own
-- per-table function (or a dynamic/JSON-extraction version, validated
-- against real multi-table shapes) when macro_theses/themes/theme_holdings
-- actually exist -- not assume this one generalizes.
--
-- THIRD fix, found by a security review pass after this migration was first
-- applied (still uncommitted at the time, so amended in place rather than
-- adding a new migration number -- same precedent as the SECOND fix above):
-- the EXISTS check originally validated object_type/object_id/to_status/
-- xact_id but never validated from_status against OLD.governance_status.
-- A transaction that hand-authors a governance_events INSERT with a
-- fabricated from_status (not matching the row's real prior state),
-- followed by the matching UPDATE, would satisfy the trigger -- a real gap
-- narrower than a full bypass (still requires hand-authoring both
-- statements, deliberately bypassing service.py) but wider than this
-- migration's own header comments previously disclosed. approve_object()/
-- reject_object() were never affected (both read from_status under
-- SELECT ... FOR UPDATE in the same transaction, so it's always accurate),
-- but the trigger itself should not rely on callers being well-behaved.
-- Fixed by adding `AND from_status = OLD.governance_status` to the EXISTS
-- subquery.
--
-- Applied via: mcp__supabase__apply_migration
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
-- SELECT count(*) FROM supabase_migrations.schema_migrations.

-- ============================================================
-- thesis_revisions: provenance columns
-- ============================================================
ALTER TABLE thesis_revisions
    ADD COLUMN source TEXT NOT NULL DEFAULT 'human' CHECK (source IN ('human','agent')),
    ADD COLUMN agent_name TEXT,  -- NULL when source='human'
    ADD COLUMN evidence_confidence TEXT CHECK (evidence_confidence IN ('verified','inferred','speculative')),
    ADD COLUMN evidence_citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD CONSTRAINT thesis_revisions_agent_requires_confidence
        CHECK (source = 'human' OR evidence_confidence IS NOT NULL),
    ADD CONSTRAINT thesis_revisions_agent_requires_citation
        CHECK (source = 'human' OR jsonb_array_length(evidence_citations) > 0);

COMMENT ON COLUMN thesis_revisions.source IS
    'DEFAULT human grandfathers every existing revision row -- this column '
    'did not exist before migration 0034. Set agent by the '
    'draft-creation/approve/reject service functions only.';

-- ============================================================
-- _check_theses_governance_audit(): theses-specific trigger function
-- ============================================================
-- Deliberately NOT a generic cross-table function -- see the migration
-- header comment above for why the originally planned single-shared-function
-- design fails at runtime. Phase 2 writes its own function(s) when
-- macro_theses/themes/theme_holdings exist to govern.
CREATE OR REPLACE FUNCTION _check_theses_governance_audit() RETURNS TRIGGER AS $$
BEGIN
    -- No-op if governance_status isn't actually changing (e.g. an UPDATE
    -- that touches other columns and happens to re-write the same value).
    IF NEW.governance_status = OLD.governance_status THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM governance_events
        WHERE object_type = 'thesis'
          AND object_id = NEW.thesis_id
          AND from_status = OLD.governance_status
          AND to_status = NEW.governance_status
          AND xact_id = pg_current_xact_id()::text::bigint
    ) THEN
        RAISE EXCEPTION 'governance_status transition from % to % on thesis % '
            'requires a matching governance_events row (same from_status, '
            'to_status) written in the SAME transaction (xact %) -- '
            'use the service-layer approve_object()/reject_object()/draft-creation '
            'functions in asxos/domain/theses/service.py, not a direct UPDATE.',
            OLD.governance_status, NEW.governance_status, NEW.thesis_id, pg_current_xact_id();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION _check_theses_governance_audit() IS
    'Bypass-prevention trigger function (Section 4.7), theses-specific. '
    'Rejects any governance_status transition lacking a matching '
    'governance_events row (same from_status AND to_status) written in the '
    'SAME Postgres transaction (checked via pg_current_xact_id() equality, '
    'not a time window). from_status is checked against OLD.governance_status '
    '-- not just to_status against NEW -- so a hand-authored governance_events '
    'row cannot claim an arbitrary prior state (added in a post-apply security '
    'review pass; see the THIRD fix note in this migration''s header). '
    'Deliberately NOT a generic cross-table function: PL/pgSQL validates '
    'NEW/OLD field references against the bound table at all times, even '
    'in unreached CASE branches, so a single function referencing '
    'NEW.macro_thesis_id/NEW.theme_id/NEW.holding_id fails immediately when '
    'bound to theses (which has none of those columns) -- confirmed by '
    'hitting this exact error while applying migration 0034. Phase 2 should '
    'write its own per-table function (or a properly-tested dynamic/JSON '
    'extraction version, validated against real multi-table shapes) rather '
    'than assuming this one generalizes.';

CREATE TRIGGER theses_governance_audit
    BEFORE UPDATE OF governance_status ON theses
    FOR EACH ROW EXECUTE FUNCTION _check_theses_governance_audit();
