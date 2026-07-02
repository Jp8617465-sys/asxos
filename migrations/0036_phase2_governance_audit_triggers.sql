-- 0036_phase2_governance_audit_triggers.sql
--
-- Governance schema, Phase 2a continued -- the bypass-prevention triggers for
-- macro_theses/themes/theme_holdings (governance-first-architecture-2026-06-30.md
-- Section 5.5, Section 7 Phase 2 entry).
--
-- THREE INDEPENDENT TRIGGER FUNCTIONS, not a shared one. migration 0034's
-- header already recorded why: PL/pgSQL validates NEW/OLD field references
-- against the trigger's BOUND table for every CASE branch, not just the one
-- that executes -- a function bound to theses cannot reference NEW.theme_id
-- even in an unreached branch. Section 5.5 of the design doc still shows the
-- broken shared-function-with-TG_ARGV design
-- (`_check_governance_audit('macro_thesis')`) -- that section is being
-- corrected to match this migration, not the other way around.
--
-- Each function below is modeled character-for-character on the CURRENT
-- (already-fixed) _check_theses_governance_audit() from migration 0034 --
-- including the from_status = OLD.governance_status check. That check was a
-- Phase 1 RETROFIT found by a post-ship security review (the original
-- version validated only object_id/to_status/xact_id, letting a
-- hand-authored governance_events row claim an arbitrary prior state) --
-- these three functions get it from day one, not as a Phase 2 rediscovery.
--
-- Applied via: mcp__supabase__apply_migration
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
-- SELECT count(*) FROM supabase_migrations.schema_migrations.

-- ============================================================
-- macro_theses
-- ============================================================
CREATE OR REPLACE FUNCTION _check_macro_theses_governance_audit() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.governance_status = OLD.governance_status THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM governance_events
        WHERE object_type = 'macro_thesis'
          AND object_id = NEW.macro_thesis_id
          AND from_status = OLD.governance_status
          AND to_status = NEW.governance_status
          AND xact_id = pg_current_xact_id()::text::bigint
    ) THEN
        RAISE EXCEPTION 'governance_status transition from % to % on macro_thesis % '
            'requires a matching governance_events row (same from_status, '
            'to_status) written in the SAME transaction (xact %) -- '
            'use the service-layer approve_object()/reject_object() functions '
            'in asxos/domain/macro_theses/service.py, not a direct UPDATE.',
            OLD.governance_status, NEW.governance_status, NEW.macro_thesis_id, pg_current_xact_id();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER macro_theses_governance_audit
    BEFORE UPDATE OF governance_status ON macro_theses
    FOR EACH ROW EXECUTE FUNCTION _check_macro_theses_governance_audit();

-- ============================================================
-- themes
-- ============================================================
CREATE OR REPLACE FUNCTION _check_themes_governance_audit() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.governance_status = OLD.governance_status THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM governance_events
        WHERE object_type = 'theme'
          AND object_id = NEW.theme_id
          AND from_status = OLD.governance_status
          AND to_status = NEW.governance_status
          AND xact_id = pg_current_xact_id()::text::bigint
    ) THEN
        RAISE EXCEPTION 'governance_status transition from % to % on theme % '
            'requires a matching governance_events row (same from_status, '
            'to_status) written in the SAME transaction (xact %) -- '
            'use the service-layer approve_theme()/reject_theme() functions '
            'in asxos/domain/themes/service.py, not a direct UPDATE.',
            OLD.governance_status, NEW.governance_status, NEW.theme_id, pg_current_xact_id();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER themes_governance_audit
    BEFORE UPDATE OF governance_status ON themes
    FOR EACH ROW EXECUTE FUNCTION _check_themes_governance_audit();

-- ============================================================
-- theme_holdings -- object_id is the holding_id surrogate (migration 0035),
-- NOT the composite (theme_id, symbol) natural key. This is the entire
-- reason the surrogate was added.
-- ============================================================
CREATE OR REPLACE FUNCTION _check_theme_holdings_governance_audit() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.governance_status = OLD.governance_status THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM governance_events
        WHERE object_type = 'theme_holding'
          AND object_id = NEW.holding_id
          AND from_status = OLD.governance_status
          AND to_status = NEW.governance_status
          AND xact_id = pg_current_xact_id()::text::bigint
    ) THEN
        RAISE EXCEPTION 'governance_status transition from % to % on theme_holding % '
            'requires a matching governance_events row (same from_status, '
            'to_status) written in the SAME transaction (xact %) -- '
            'use the service-layer approve_theme_holding()/reject_theme_holding() '
            'functions in asxos/domain/themes/service.py, not a direct UPDATE.',
            OLD.governance_status, NEW.governance_status, NEW.holding_id, pg_current_xact_id();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER theme_holdings_governance_audit
    BEFORE UPDATE OF governance_status ON theme_holdings
    FOR EACH ROW EXECUTE FUNCTION _check_theme_holdings_governance_audit();
