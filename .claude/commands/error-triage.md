# Error Triage — Root Cause Analysis

$ARGUMENTS = error message, stack trace, or description of the problem.

## Steps

**Step 1 — Locate origin**
- Extract the key error phrase
- `grep -rn "[error phrase]" asxos/ jobs/ tests/ --include="*.py"`
- Identify file:line

**Step 2 — Render logs (if production-side)**
- the Render API logs (`GET api.render.com/v1/logs?resource=<svc-id>`, `$RENDER_API_KEY`) for the relevant `asxos-*` service
- Report: frequency in last 24h, first/last occurrence, correlation with
  a recent deploy (`GET api.render.com/v1/services/<id>/deploys`)

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
- If Render or Supabase logs are unavailable, note this and proceed with
  codebase analysis only
- For job-runs errors, also surface the matching Healthchecks.io alert
  if any (the canonical out-of-band failure signal)
