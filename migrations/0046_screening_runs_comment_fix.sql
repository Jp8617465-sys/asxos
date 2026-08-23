-- 0046_screening_runs_comment_fix.sql
--
-- Comment-only. No data-changing DDL. Corrects two COMMENT ON COLUMN texts
-- that PR #151 made false when it made --limit display-only and started
-- persisting every passing symbol (the displayed shortlist used to be what
-- matched_symbols stored, so the audit log could read "50 matched, 20
-- recorded"). The CREATE TABLE comments in 0038 are updated in the same
-- change so a restore-drill replay agrees with production after this file
-- is applied.
--
-- Numbering: 0042 is reserved by parked PR #80 and must not be applied;
-- 0045 exists on disk and is unapplied. 0046 is the next free number.
-- Apply via: mcp__supabase__apply_migration

BEGIN;

COMMENT ON COLUMN screening_runs.match_count IS
    'Total rule-passing symbols. A rule matching 1800/1872 names is a no-op, not a '
    'triage tool. Equal to cardinality(matched_symbols) since PR #151, which made '
    '--limit display-only and enforces the equality in log_run(); the two columns '
    'are kept separate because match_count is the pre-registered figure.';

COMMENT ON COLUMN screening_runs.matched_symbols IS
    'EVERY passing symbol, unbounded by --limit, ordered by symbol so two runs over '
    'identical data produce byte-identical arrays. Before PR #151 this held only the '
    'displayed shortlist, which wrote "50 matched, 20 recorded" into the audit log.';

COMMIT;
