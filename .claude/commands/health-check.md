# Health Check — Production Monitor

Check service health across Render and Supabase. Run after a deploy, or
any time something looks off.

## Render (via the Render REST API — `api.render.com/v1`, `$RENDER_API_KEY`; there is no Render MCP)

For each `asxos-*` service (1 web + 8 crons):
1. `GET api.render.com/v1/services/<id>` → service status, last update
2. `GET api.render.com/v1/services/<id>/deploys` → most recent deploy status (live / failed)
3. `GET api.render.com/v1/logs` (last 100 lines) → ERROR / Traceback lines in
   the last 24h
4. Web only: hit `/health` directly:
   ```bash
   curl -fsS https://asxos-api.onrender.com/health
   ```

Flag if:
- Any asxos service is not `not_suspended`
- Any recent deploy is `build_failed` / `update_failed` / `canceled`
- The web service `/health` returns anything other than 200 + `{"status":"ok"}`
- Logs show repeated `RuntimeError: active model artefact missing`
  (lifespan would have hard-failed — meaning the service is in a restart loop)

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
   Flag any `status='failure'`.

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

Flag any > 3 calendar days old (excluding weekends — fundamentals + regulatory
are daily, prices/signals weekdays only).

## Output

```
Health Check — [timestamp UTC]
──────────────────────────────
Render
  asxos-api status:           [not_suspended/suspended]
  Last deploy:                [date] [live/failed]
  /health response:           [200 / error]

  Crons (8): [N up / N suspended / N with failed last deploy]
  Recent ERROR lines (24h):   [N]

Supabase
  Active connections:         [N] / 100
  Slowest query mean_ms:      [ms]
  Failed job_runs (48h):      [list or none]

Data freshness
  prices:                     [date] ([N days old])
  signals:                    [date] ([N days old])
  fundamentals:               [date] ([N days old])
  regulatory_events:          [date] ([N days old])
──────────────────────────────
Overall: HEALTHY / DEGRADED / CRITICAL
```
