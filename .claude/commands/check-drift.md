# Check Drift

Compare actual deployed state to `render.yaml` and `.env.example`.
Reports any divergence. The drift-prevention discipline is CLAUDE.md
non-negotiable #2: every Render change is `render.yaml` + git push,
never the dashboard.

## Steps

1. `mcp__render__list_services` filtered to `name LIKE 'asxos-%'`
2. For each: extract name, type (web/cron), schedule, command, plan,
   region, branch, autoDeploy, healthCheckPath (web only), env-var keys
   (values redacted)
3. Parse `render.yaml` — same fields
4. Read `.env.example` — extract the expected env-var key list per service
5. Diff:
   - Service in Render but not in `render.yaml` → **DRIFT: extra service**
   - Service in `render.yaml` but not in Render → **DRIFT: missing service**
   - Schedule mismatch on any cron → **DRIFT: schedule**
   - Command mismatch on any cron → **DRIFT: command**
   - Plan / region / branch mismatch → **DRIFT: config**
   - `healthCheckPath` mismatch on the web service → **DRIFT: healthCheckPath**
   - Env-var key in Render but absent from `render.yaml` for that service → **DRIFT: extra var**
   - Env-var key in `render.yaml` (with `sync: false`) but absent from
     the live service → **DRIFT: missing var**
   - Cron env var stored as local value when `render.yaml` declares it
     via `fromService` → **DRIFT: env-var shape**
6. Report PASS or list every drift found

## Known drifts (documented, not blocking)

Carried from the M12 MCP-bootstrap. Fix when convenient (Task #4):

- `asxos-api.healthCheckPath` is empty — `render.yaml` declares `/health`.
  The MCP `create_web_service` tool doesn't accept the parameter; set in
  dashboard once.
- 7 cron services store local copies of `DATABASE_URL` /
  `EODHD_API_KEY` / `RESEND_API_KEY` / `BRIEF_*_EMAIL` instead of the
  `fromService` refs declared in `render.yaml`. The MCP create tools
  don't accept fromService shape. Fix in dashboard.

If those are the only drifts reported, output `PASS (2 expected drifts)`.

## Output

```
Drift check — [timestamp UTC]
──────────────────────────────
asxos-api                    [PASS | DRIFT: healthCheckPath]
asxos-sync-universe          [PASS]
asxos-sync-prices            [PASS]
asxos-sync-fundamentals      [PASS]
asxos-generate-signals       [PASS]
asxos-ingest-regulatory      [PASS]
asxos-compose-brief          [PASS]
asxos-retrain-model-a        [PASS]
asxos-backup-irreplaceable   [PASS]
──────────────────────────────
Result: PASS (N expected drifts) | DRIFT (N unexpected entries)
```

Run this after every `git push origin main`.
