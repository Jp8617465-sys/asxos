-- 0035_macro_theses_and_governance_columns.sql
--
-- Governance schema, Phase 2a (governance-first-architecture-2026-06-30.md
-- Section 5.5, Phase 2 entry in Section 7). Schema only -- no triggers here
-- (those are migration 0036, matching the 0033/0034 split: schema first so
-- referential dependencies apply cleanly and can be verified before the more
-- novel PL/pgSQL layer goes on top).
--
-- macro_theses is a net-new table (zero rows, zero readers) -- the top of the
-- macro -> theme -> instrument discovery hierarchy the design doc's Section 5
-- describes. themes/theme_holdings gain the same governance_status/
-- source_run_id pair theses got in migration 0033, grandfathered to
-- 'approved' for all pre-existing (100% human-authored/human-driven) rows,
-- with one carve-out: theme_holdings rows with source='system_default' are
-- open_thesis()-generated placeholders, never actually reviewed as an
-- assertion about theme exposure -- grandfathering those to 'approved' would
-- silently launder an unreviewed placeholder into reviewed content the
-- moment this column appears, so they backfill to 'draft' instead.
--
-- Applied via: mcp__supabase__apply_migration
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
-- SELECT count(*) FROM supabase_migrations.schema_migrations.

BEGIN;

-- ============================================================
-- macro_theses: net-new table
-- ============================================================
CREATE TABLE macro_theses (
    macro_thesis_id   BIGSERIAL    PRIMARY KEY,
    title             TEXT         NOT NULL,
    thesis_text       TEXT         NOT NULL CHECK (thesis_text <> ''),
    regime_quadrant   TEXT         NOT NULL CHECK (regime_quadrant IN (
                          'rising_growth_rising_inflation', 'rising_growth_falling_inflation',
                          'falling_growth_rising_inflation', 'falling_growth_falling_inflation')),
    horizon_months    SMALLINT     CHECK (horizon_months BETWEEN 1 AND 36),
    catalyst          TEXT         NOT NULL,
    falsifier         TEXT         NOT NULL,
    data_signals      JSONB        NOT NULL DEFAULT '[]',
    source_run_id     BIGINT       REFERENCES agent_runs(run_id),  -- NULL = human-authored
    governance_status TEXT         NOT NULL DEFAULT 'draft'
                          CHECK (governance_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
    -- DEFAULT 'draft' here, unlike theses.governance_status's DEFAULT 'approved'
    -- (migration 0033) -- this table is net-new and zero-row, its primary
    -- output surface is the macro-economist agent, so agent-drafted is the
    -- expected norm, not the exception being grandfathered around.
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    retired_at        DATE,

    CONSTRAINT macro_theses_retired_requires_approved
        CHECK (retired_at IS NULL OR governance_status IN ('approved', 'retired'))
        -- Prevents retiring a thesis that was never approved -- retiring a
        -- draft/pending_review row would be a confusing state (retiring
        -- something that was never live).
);
CREATE INDEX idx_macro_theses_active ON macro_theses (created_at DESC)
    WHERE retired_at IS NULL AND governance_status = 'approved';

COMMENT ON COLUMN macro_theses.governance_status IS
    'Provenance/approval state (see theses.governance_status, migration 0033, '
    'for the full state-machine rationale). DEFAULT draft (not approved) '
    'because this table starts empty -- agent-drafted is the norm here, not '
    'a grandfathered exception.';

-- ============================================================
-- themes: link to macro_theses + governance columns
-- ============================================================
ALTER TABLE themes
    ADD COLUMN macro_thesis_id  BIGINT REFERENCES macro_theses(macro_thesis_id) ON DELETE SET NULL,
    ADD COLUMN governance_status TEXT NOT NULL DEFAULT 'approved'
        CHECK (governance_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
    ADD COLUMN source_run_id BIGINT REFERENCES agent_runs(run_id);

COMMENT ON COLUMN themes.governance_status IS
    'DEFAULT approved grandfathers every existing human-authored row -- this '
    'column did not exist before migration 0035. See '
    'docs/proposals/governance-first-architecture-2026-06-30.md Section 5.5.';

-- ============================================================
-- theme_holdings: surrogate key + governance columns
-- ============================================================
ALTER TABLE theme_holdings
    ADD COLUMN holding_id BIGSERIAL UNIQUE,
    -- Surrogate key so governance_events.object_id can reference one BIGINT
    -- uniformly across all governed tables -- theme_holdings' natural PK
    -- (theme_id, symbol) is composite and doesn't fit that shape.
    ADD COLUMN governance_status TEXT NOT NULL DEFAULT 'approved'
        CHECK (governance_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
    ADD COLUMN source_run_id BIGINT REFERENCES agent_runs(run_id);

-- The one carve-out from the grandfather-to-approved default: system_default
-- placeholder rows (open_thesis()'s inline theme-attach upsert) are not
-- reviewed content and should not masquerade as approved exposure.
UPDATE theme_holdings
SET governance_status = 'draft'
WHERE source = 'system_default';

-- ============================================================
-- Gated views -- the read surface for the brief, /pm-review, and any future
-- allocator code (Section 5.5). Prefixed governed_active_* (not suffixed)
-- so all four group together in any schema listing and the load-bearing
-- word reads first. Zero consumers wire up to these yet (Phase 4, Section 6)
-- -- shipping schema ahead of ingestion matches this repo's existing pattern
-- (e.g. migration 0027's research-store tables).
--
-- Deliberately NOT named active_theses/active_themes/etc: that would collide
-- in prose (not in code -- SQL view vs Python module are different
-- namespaces) with asxos/domain/brief/collectors/active_theses.py, an
-- unrelated pre-existing section-collector module.
-- ============================================================
CREATE VIEW governed_active_theses AS
    SELECT * FROM theses WHERE governance_status = 'approved' AND status NOT IN ('expired');

CREATE VIEW governed_active_themes AS
    SELECT * FROM themes WHERE governance_status = 'approved' AND retired_at IS NULL;

CREATE VIEW governed_active_theme_holdings AS
    SELECT * FROM theme_holdings WHERE governance_status = 'approved';
    -- No retired_at/status column on this table -- the governance predicate
    -- alone is the correct filter here, not a copy-pasted liveness clause.

CREATE VIEW governed_active_macro_theses AS
    SELECT * FROM macro_theses WHERE governance_status = 'approved' AND retired_at IS NULL;

COMMIT;
