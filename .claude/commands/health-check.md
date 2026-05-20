# Health Check — Production Monitor

Check current service health across Render and Supabase.
Run this 24-48 hours after a production deploy, or any time something looks wrong.

## Render (via Render MCP)

1. Get service status: is the web service running, degraded, or down?
2. List deploys: what was the last deploy and did it succeed?
3. Check logs (last 100 lines): any ERROR or CRITICAL log entries in the last 24h?
4. Get metrics: CPU usage, memory usage, p95 response time

Flag if:
- Service is not in `running` state
- Error rate in last 24h > 1%
- p95 response time > 500ms
- Memory > 80% of limit

## Supabase (via Supabase MCP)

1. Active DB connections — flag if > 80 (pool limit is 100)
2. Check for slow queries: `SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10`
3. Check job_completions for recent pipeline runs:
   ```sql
   SELECT job_name, as_of, status, duration_seconds
   FROM job_completions
   ORDER BY as_of DESC
   LIMIT 20
   ```
   Flag any job with `status = 'failed'` in the last 48h

## Signal pipeline freshness

```sql
SELECT MAX(as_of) as latest_signals FROM model_a_ml_signals;
SELECT MAX(as_of) as latest_ensemble FROM ensemble_signals;
SELECT MAX(updated_at) as latest_screen FROM screen_matches;
```
Flag if latest signals are more than 2 trading days old.

## Output

```
Health Check — [timestamp]
──────────────────────────
Render
  Service status:  [running/degraded/down]
  Last deploy:     [date] [success/failed]
  Error rate 24h:  [%]
  p95 response:    [ms]
  Memory:          [%]

Supabase
  Active connections:  [N] / 100
  Slowest query:       [query] [ms]
  Failed jobs (48h):   [list or none]

Signals freshness
  Model A:    [date] ([N days old])
  Ensemble:   [date] ([N days old])
  Screens:    [date] ([N days old])
──────────────────────────
Overall: HEALTHY / DEGRADED / CRITICAL
```
