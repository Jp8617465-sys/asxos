# Deploy Check — Pre-Production Checklist

Verify every item before pushing to `main` (Render auto-deploys on push).
Report PASS/FAIL per item.

## Checklist

**Code**
- [ ] `make check` — ruff + mypy + pytest all green
- [ ] No uncommitted changes: `git status -s`
- [ ] Local branch is rebased onto origin/main

**Database**
- [ ] All migrations on disk applied via Supabase MCP:
  - `ls migrations/*.sql | sort | tail -1` (latest on disk)
  - `mcp__3ec0fde8-58dc-483a-b873-6aebe5cbb341__list_migrations` →
    confirm the latest is present
- [ ] `REQUIRED_MIGRATIONS` in `asxos/api/main.py` matches the
  count of `0NNN_*.sql` files in `migrations/`

**Env vars**
- [ ] Any new `sync: false` keys added to `render.yaml` also uploaded
  to the relevant service via `mcp__render__update_environment_variables`
- [ ] No `.env*` files committed: `git log --all -- '.env*'` returns nothing
- [ ] Production secrets still match `~/Projects/asxos-secrets/.env.production`

**IaC**
- [ ] `render.yaml` parses cleanly: `python -c "import yaml; yaml.safe_load(open('render.yaml'))"`
- [ ] If new cron added, its `HEALTHCHECK_URL_<JOB>` env var exists

## Output

For each item: PASS ✓ or FAIL ✗.

- All pass → **Ready. Push to `main` to trigger Render auto-deploy, then
  run `/smoke-test https://asxos-api.onrender.com` and `/check-drift`.**
- Any fail → **Blocked. Fix the items marked ✗ above.**

Do NOT push if any item is FAIL.
