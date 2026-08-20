# Health Check — Production Monitor

Check job health across GitHub Actions and Supabase. Run after merging anything
that touches a job, or any time something looks off.

## API — unhosted

There is nothing to probe. `asxos-api` was the only non-cron service and fell
with Render on 2026-08-12; the API has no host and no public URL today, and
whether it needs one is an open governor question
(`docs/product/scheduler-inventory-2026-08-13.md` §2 row 1). Report it as
**UNHOSTED (by decision, pending governor call)** — not as DOWN, and never
against an invented URL.

To exercise the API at all, run it locally: `make dev`, then
`curl -fsS http://127.0.0.1:8788/health`.

## GitHub Actions (the cron substrate)

```bash
gh run list --limit 20
```

Then per scheduled workflow — `daily-brief`, `us-positions`, `weekly-research`,
`pipeline-health`, `backup`:

```bash
gh run list --workflow <name>.yml --limit 5
gh run view <run-id> --log   # on any red run; the failing step names the job
```

`pipeline-health.yml` (daily 22:00 UTC) is the standing watchdog. It runs
`jobs/check_cron_health.py`, which inspects `job_runs` for stuck runs, missing
expected-daily jobs, consecutive failures and degraded rows, and **hard-fails
when it finds any**. A red `pipeline-health` run is the alarm working — read its
log first, before anything else.

Flag if:
- Any scheduled workflow has `conclusion: failure` in the last 48h
- A scheduled workflow has **no run** in its expected window. GitHub cron is
  best-effort and can skip runs entirely, so a missing run is a real signal, not
  an absence of one
- `pipeline-health` is red
- A run failed at `Install` or `setup-python` rather than at a job step — that is
  an environment/dependency break, not a data break

Note `HEALTHCHECK_URL_*` is currently set in no workflow, so the Healthchecks.io
deadman is silently skipped. Until that changes, the red run plus GitHub's own
run-failure notification IS the out-of-band signal — which is why a missing run
above must be checked deliberately.

## Supabase (via Supabase MCP, project `gxjqezqndltaelmyctnl`)

1. Active DB connections via `pg_stat_activity`:
   ```sql
   SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'postgres';
   ```
   Flag if > 80 (pool limit ~100 on Supabase free tier)

2. Slow queries:
   ```sql
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   WHERE query NOT LIKE '%pg_stat_statements%'
   ORDER BY mean_exec_time DESC LIMIT 10;
   ```

3. Job runs in last 48h:
   ```sql
   SELECT job_name, as_of, status, duration_ms, error_message
   FROM job_runs
   WHERE started_at > NOW() - INTERVAL '48 hours'
   ORDER BY started_at DESC;
   ```
   Flag any `status='failure'`. Cross-check against `gh run list`: a job with no
   `job_runs` row at all means its workflow step never started, which points at
   the workflow, not the job.

## Data freshness

```sql
SELECT 'prices'    AS tbl, MAX(dt)::date    AS latest FROM prices
UNION ALL
SELECT 'signals',          MAX(as_of)::date          FROM signals
UNION ALL
SELECT 'fundamentals',     MAX(as_of)::date          FROM fundamentals
UNION ALL
SELECT 'regulatory_events', MAX(event_date)::date    FROM regulatory_events;
```

Flag any > 3 calendar days old, allowing for cadence. Both `prices` and
`regulatory_events` come from `daily-brief` (Sun-Thu UTC), so both are weekdays
only — regulatory is **no longer daily**. **`fundamentals` is weekly now**
(`weekly-research`, Sat), so do not flag it as stale mid-week. `signals` is
not written by any scheduled workflow while Model A is shelved (rule #11), so a
frozen `signals` date is expected, not a fault.

## Output

```
Health Check — [timestamp UTC]
──────────────────────────────
API
  Host:                       UNHOSTED (pending governor decision)

GitHub Actions (last 48h)
  daily-brief:                [success/failure/no run] [run-id]
  us-positions:               [success/failure/no run]
  weekly-research:            [success/failure/no run — weekly, Sat]
  pipeline-health:            [success/failure/no run]
  backup:                     [success/failure/no run]
  Failing steps:              [list or none]

Supabase
  Active connections:         [N] / 100
  Slowest query mean_ms:      [ms]
  Failed job_runs (48h):      [list or none]

Data freshness
  prices:                     [date] ([N days old])
  signals:                    [date] (frozen — Model A shelved)
  fundamentals:               [date] ([N days old], weekly cadence)
  regulatory_events:          [date] ([N days old])
──────────────────────────────
Overall: HEALTHY / DEGRADED / CRITICAL
```
