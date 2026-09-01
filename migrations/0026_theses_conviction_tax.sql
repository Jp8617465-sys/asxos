-- 0026_theses_conviction_tax.sql
-- PM/thesis layer (M-Thesis): add the two fields the build-readiness audit flagged
-- as missing from an otherwise-complete theses schema —
--   conviction_level : 1..5 PM conviction scale (NULL = not yet set)
--   tax_notes        : free-text CGT / franking / holding-period notes
--
-- Applied via: mcp__supabase__apply_migration (project gxjqezqndltaelmyctnl).
-- Additive + nullable: zero risk to existing rows. Both fields are revisable
-- via `asx thesis revise` (allowlisted in REVISABLE_FIELDS).

ALTER TABLE theses
    ADD COLUMN IF NOT EXISTS conviction_level SMALLINT,
    ADD COLUMN IF NOT EXISTS tax_notes        TEXT;

-- Bounded conviction scale; NULL allowed (conviction not yet assigned).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'theses_conviction_level_range'
    ) THEN
        ALTER TABLE theses
            ADD CONSTRAINT theses_conviction_level_range
            CHECK (conviction_level IS NULL OR conviction_level BETWEEN 1 AND 5);
    END IF;
END$$;
