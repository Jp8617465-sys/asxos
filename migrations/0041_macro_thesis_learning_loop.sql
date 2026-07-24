-- 0041_macro_thesis_learning_loop.sql
--
-- DRAFT — NOT applied by the build session. James applies via
-- mcp__supabase__apply_migration against project gxjqezqndltaelmyctnl, then
-- bumps REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
--   SELECT count(*) FROM supabase_migrations.schema_migrations
-- (the observed count, not a guessed +1 — api-conventions.md).
--
-- Macro-thesis learning loop, Layer A
-- (docs/proposals/macro-thesis-learning-loop-2026-07-21.md §3). Adds:
--   1. macro_theses.machine_conditions JSONB — the optional structured,
--      machine-evaluable form of a thesis's catalyst/falsifier (shape =
--      MachineConditions in asxos/domain/theses/schemas.py).
--   2. macro_thesis_outcomes — the re-derivable outcome ledger the evaluator
--      cron (jobs/score_macro_theses.py) UPSERTs one row per thesis per run.
--   3. Backfill of the two existing approved theses (#6, #7) with their
--      falsifier predicates (their catalysts stay prose-only — see below).
--
-- RENDER CRON IS A FOLLOW-UP: do NOT wire the asxos-score-macro-theses cron in
-- render.yaml until AFTER this migration is applied. A cron that runs before
-- macro_thesis_outcomes / the machine_conditions column exist would hard-fail
-- (CLAUDE.md #1). Sequence: apply 0041 -> bump REQUIRED_MIGRATIONS -> add the
-- cron.

BEGIN;

-- ============================================================
-- 1. macro_theses.machine_conditions
-- ============================================================
ALTER TABLE macro_theses ADD COLUMN machine_conditions JSONB;

COMMENT ON COLUMN macro_theses.machine_conditions IS
    'Optional structured predicates over market_context_current signals, '
    'evaluated by jobs/score_macro_theses.py (the macro-thesis learning loop, '
    'Layer A). NULL = free-text catalyst/falsifier only (not machine-scorable). '
    'Thresholds are JSON strings at NUMERIC(18,6) precision, never bare JSON '
    'numbers (CLAUDE.md #5). Shape = MachineConditions in '
    'asxos/domain/theses/schemas.py: {catalyst?, falsifier?} each a '
    '{combine: all|any, conditions: [{signal, op, threshold, window, '
    'aggregation}]}. Written via MacroThesisProposal.machine_conditions '
    '(model_dump_json) or a hand-annotation UPDATE.';

-- ============================================================
-- 2. macro_thesis_outcomes — the evaluator's outcome ledger
-- ============================================================
CREATE TABLE macro_thesis_outcomes (
    macro_thesis_id     BIGINT       NOT NULL REFERENCES macro_theses(macro_thesis_id),
    as_of               DATE         NOT NULL,
    status              TEXT         NOT NULL
                            CHECK (status IN ('confirmed','falsified','open','expired')),
    catalyst_progress   NUMERIC(18,6),          -- fraction of catalyst conditions satisfied [0,1]; NULL if no catalyst predicate
    falsifier_triggered BOOLEAN      NOT NULL DEFAULT FALSE,
    days_elapsed        INTEGER,
    days_to_horizon     INTEGER,
    evaluation_detail   JSONB,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (macro_thesis_id, as_of)
);

COMMENT ON TABLE macro_thesis_outcomes IS
    'Daily outcome ledger for the macro-thesis learning loop, Layer A '
    '(jobs/score_macro_theses.py UPSERTs one row per approved thesis per run, '
    'idempotent on (macro_thesis_id, as_of)). Re-derivable from macro_theses + '
    'market_context history — NOT governance content and NOT in '
    'backup_irreplaceable.sh (same classification as screening_runs / '
    'portfolio_daily_snapshots). A falsifier trigger flags James for review; it '
    'never auto-retires or auto-changes governance_status (system proposes, '
    'human decides).';

-- ============================================================
-- 3. Backfill the two existing approved macro theses (#6, #7)
-- ============================================================
-- This is a plain UPDATE of machine_conditions ONLY. It does NOT touch
-- governance_status, so the BEFORE UPDATE OF governance_status trigger from
-- migration 0036 (_check_macro_theses_governance_audit) does NOT fire — that
-- trigger is scoped `BEFORE UPDATE OF governance_status`, and an UPDATE that
-- leaves that column untouched never enters the trigger. No governance_events
-- row is required here.
--
-- Only the FALSIFIERS are encoded: they are the fully-flat, machine-evaluable
-- half. The CATALYSTS for #6/#7 are intentionally left prose-only (NULL) —
-- both are nested `A AND (B OR C)` trees, which the flat MachinePredicate
-- defers (backend-architect §6). (macro_thesis #11 / run 7 similarly leans on
-- crosses_*, also deferred — annotate when that grammar lands.)

-- #6 breadth-led catch-down: falsified if breadth stays broad AND the index
-- holds — pct_above_200d_ma >= 0.50 on 10 consecutive rows with asx200_close
-- above 8,600 on those same rows.
UPDATE macro_theses
SET machine_conditions = '{"falsifier":{"combine":"all","conditions":[{"signal":"pct_above_200d_ma","op":"gte","threshold":"0.50","window":10,"aggregation":"consecutive"},{"signal":"asx200_close","op":"gt","threshold":"8600","window":10,"aggregation":"consecutive"}]}}'::jsonb
WHERE macro_thesis_id = 6;

-- #7 sticky AU long end: falsified if the 10y yield closes below 4.25 on 5
-- consecutive daily rows.
UPDATE macro_theses
SET machine_conditions = '{"falsifier":{"combine":"all","conditions":[{"signal":"aus_10y_yield","op":"lt","threshold":"4.25","window":5,"aggregation":"consecutive"}]}}'::jsonb
WHERE macro_thesis_id = 7;

COMMIT;
