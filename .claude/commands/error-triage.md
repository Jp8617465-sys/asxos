# Error Triage — Root Cause Analysis

$ARGUMENTS = error message, stack trace, or description of the problem.

## Steps

**Step 1 — Locate origin**
- Extract the key error phrase
- `grep -rn "[error phrase]" asxos/ jobs/ tests/ --include="*.py"`
- Identify file:line

**Step 2 — GitHub Actions logs (if it failed in a scheduled job)**
- `gh run list --workflow <name>.yml --limit 10` — find the failing runs
- `gh run view <run-id> --log` — the failing step names the `jobs/*.py` script
- Report: frequency across recent runs, first/last occurrence, and the commit each
  run was pinned to (`gh run view <run-id> --json headSha`). A failure that starts
  at one commit is a regression; one that comes and goes is data or upstream API

**Step 3 — Supabase logs (if DB-side)**
- `mcp__3ec0fde8-58dc-483a-b873-6aebe5cbb341__get_logs` for the affected
  service slice (`api` | `postgres` | `auth` | `realtime`)
- Check `job_runs.error_message` for the failing job

**Step 4 — Reproduce + understand**
- Read file at origin ±20 lines
- Identify root cause: what input/state triggers this?
- Is there a test that should have caught it?

**Step 5 — Propose fix**
- Minimal patch at the root cause, not the symptom
- Regression test to add
- Blast radius: all symbols, specific data state, specific cron window?

## Output

```
Error Triage: [error summary]
──────────────────────────────
Origin:      [file:line]
Frequency:   [N occurrences in last 24h]
First seen:  [timestamp]
Root cause:  [one paragraph]

Proposed fix:
[code diff or description]

Test to add:
[test description]

Blast radius: [scope]
```

## Constraints

- Do NOT apply the fix without explicit user confirmation
- If the error is in a migration or a `models/` pickle, stop and ask
- If Actions or Supabase logs are unavailable, note this and proceed with
  codebase analysis only
- For job-runs errors, also surface the matching Healthchecks.io alert
  if any (the canonical out-of-band failure signal)
