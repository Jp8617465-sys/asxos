-- 0010_job_runs_blocked_and_override.sql
-- P0-0: distinguish upstream-blocked runs from operational failures.
--
-- The P0 guards (P0-1 aggregate failure threshold, P0-2 upstream hard-fail)
-- will generate many runs where the right operator response is "wait for
-- the upstream job to retry" rather than "page me, something is broken."
-- Conflating these into a single 'failure' status creates alert fatigue and
-- trains operators to ignore real failures. The 'blocked' status keeps
-- them visually distinct in job_runs and in any downstream dashboards.
--
-- override_reason captures the audit trail for --allow-stale-upstream and
-- any future operator overrides. NULL on normal runs.
--
-- No existing constraint on status (verified via mcp__supabase__execute_sql);
-- existing values are only 'running' and 'success'.

ALTER TABLE job_runs
    ADD CONSTRAINT job_runs_status_check
    CHECK (status IN ('running', 'success', 'failure', 'blocked'));

ALTER TABLE job_runs
    ADD COLUMN IF NOT EXISTS override_reason TEXT;
