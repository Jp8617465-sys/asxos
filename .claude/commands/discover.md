# Discovery Audit

Read `CLAUDE.md` first. Then run a read-only audit on $ARGUMENTS
(or the full system if no argument). Do NOT modify any files.

## Checks

1. **DB state (Supabase MCP, project `gxjqezqndltaelmyctnl`)**:
   ```sql
   SELECT 'universe' n, COUNT(*) FROM universe WHERE is_active
   UNION ALL SELECT 'prices', COUNT(*) FROM prices
   UNION ALL SELECT 'fundamentals', COUNT(*) FROM fundamentals
   UNION ALL SELECT 'signals', COUNT(*) FROM signals
   UNION ALL SELECT 'holding_lots_open', COUNT(*) FROM holding_lots WHERE disposed_at IS NULL
   UNION ALL SELECT 'decisions', COUNT(*) FROM decisions
   UNION ALL SELECT 'regulatory_events', COUNT(*) FROM regulatory_events
   UNION ALL SELECT 'model_versions', COUNT(*) FROM model_versions
   UNION ALL SELECT 'job_runs_last_24h',
       COUNT(*) FROM job_runs WHERE started_at > NOW() - INTERVAL '24 hours';
   ```

2. **Freshness**:
   - `SELECT MAX(dt) FROM prices` — latest price day
   - `SELECT MAX(as_of) FROM fundamentals` — latest fundamentals snapshot
   - `SELECT MAX(as_of) FROM signals` — latest signal date
   - flag if any > 3 days behind today

3. **Render service inventory** via MCP — list `asxos-*` services, their
   schedules, autoDeploy state, last deploy status

4. **Job inventory**: `SELECT job_name, status, started_at FROM job_runs ORDER BY started_at DESC LIMIT 20`

5. **Active model**: `SELECT model, version, roc_auc, is_active FROM model_versions WHERE is_active`

6. **Code inventory**:
   - `find asxos -name "*.py" | wc -l` — module count
   - `find tests -name "test_*.py" | wc -l` — test files
   - `pytest --collect-only -q 2>&1 | tail -2` — total test count

## Output

Structured report with specific numbers + dates + file paths. Flag any
divergence from `CLAUDE.md`'s "Database schema reference" section, or
between `render.yaml` and actual deployed services.

Focus: what's actually working vs what we assumed.
