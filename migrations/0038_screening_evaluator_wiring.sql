-- 0038_screening_evaluator_wiring.sql
--
-- Tier 2a mechanical screen (docs/proposals/thesis-coverage-framework-2026-07-11.md,
-- buildable-now item #2). Two pieces:
--
--   1. Tightens screening_rules.source_method from a comment-only vocabulary
--      (shap_threshold | surrogate_tree | curated_composite) to a real CHECK
--      restricting it to 'curated_composite'. shap_threshold/surrogate_tree are
--      carryovers from the OLD, DEAD repo's ML-derived screening approach
--      (screen_match_engine.py / extract_shap_thresholds.py /
--      backtest_screening_rules.py -- docs/foundation/phase-1-audit.md, confirmed
--      absent from this repo's jobs/*.py). They are Model A artifacts; under
--      CLAUDE.md rule #11 (Model A quarantine, STANDING) no signal-derived
--      screening rule may ever be written. This CHECK makes that a DB-enforced
--      hard-fail, not merely a convention.
--
--   2. Adds screening_runs, a lightweight, UNGOVERNED audit log of each screen
--      evaluation. This is a data filter, the same category as `prices`/
--      `fundamentals`/`portfolio_daily_snapshots` -- re-derivable by re-running
--      the same rule against current data -- NOT investment content, so it gets
--      no governance_status/agent_runs machinery. It is deliberately NOT added
--      to scripts/backup_irreplaceable.sh.
--
-- PRE-APPLY CHECK (api-conventions.md): before applying, run
--   SELECT source_method, count(*) FROM screening_rules GROUP BY source_method;
-- via mcp__supabase__execute_sql and confirm zero rows (or, if non-zero, that
-- every row is already 'curated_composite'). Verified 2026-07-11: zero rows.
-- Re-verify live at apply time -- don't trust that finding as still current.
--
-- Apply via: mcp__supabase__apply_migration

BEGIN;

-- --- Piece 1: tighten source_method -----------------------------------------

ALTER TABLE screening_rules
    ADD CONSTRAINT screening_rules_source_method_chk
        CHECK (source_method = 'curated_composite');

COMMENT ON COLUMN screening_rules.source_method IS
    'Always ''curated_composite'' -- hand-authored, model-independent screening '
    'criteria only (PE bands, market cap floors, sector filters). The historical '
    'shap_threshold/surrogate_tree values are Model A artifacts from the old, dead '
    'repo and are permanently disallowed under CLAUDE.md rule #11 (Model A '
    'quarantine, standing). The CHECK, not this comment, is the enforcement point '
    '-- widen it deliberately if a future non-Model-A automated rule-extraction '
    'method is ever added; never widen it to re-admit shap_threshold/surrogate_tree.';

-- --- Piece 2: results log ----------------------------------------------------

CREATE TABLE screening_runs (
    id                  BIGSERIAL    PRIMARY KEY,
    rule_id             INTEGER      NOT NULL REFERENCES screening_rules(id),
    run_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    sector_scope        TEXT,        -- effective sector filter for this run (rule's
                                       -- own sector_scope intersected with any
                                       -- runtime --sector param); NULL = cross-sector
    universe_size       INTEGER      NOT NULL,  -- candidate pool size before rule_json filtering
    match_count         INTEGER      NOT NULL,  -- TRUE total matches, before bounding
    matched_symbols     TEXT[]       NOT NULL DEFAULT '{}',  -- bounded shortlist actually shown (<=limit)
    rule_json_snapshot  JSONB        NOT NULL,  -- rule_json AT EVALUATION TIME -- screening_rules
                                                  -- rows are mutable; this snapshot stops a later
                                                  -- rule edit from silently reinterpreting old runs
    duration_ms         INTEGER
);

CREATE INDEX screening_runs_rule_idx ON screening_runs (rule_id, run_at DESC);

COMMENT ON TABLE screening_runs IS
    'Audit log of each Tier 2a mechanical screen evaluation. Re-derivable (re-run '
    'the same rule_json against current fundamentals/universe/prices) -- same '
    'classification as prices/fundamentals/portfolio_daily_snapshots, NOT '
    'irreplaceable, NOT in scripts/backup_irreplaceable.sh. Not investment content: '
    'no governance_status, no agent_runs linkage. See docs/proposals/'
    'thesis-coverage-framework-2026-07-11.md Tier 2a.';

COMMENT ON COLUMN screening_runs.match_count IS
    'Total rule-passing symbols BEFORE the limit bound applied to matched_symbols. '
    'A rule matching 1800/1872 names is a no-op, not a triage tool -- match_count '
    'preserves that signal even when matched_symbols is truncated to the shortlist.';

COMMIT;
