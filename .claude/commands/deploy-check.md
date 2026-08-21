# Deploy Check — Pre-Merge Checklist

Verify every item before merging to `main`. Report PASS/FAIL per item.

**There is no deploy step.** Nothing auto-deploys. Merging to `main` is what
makes a change take effect: job configuration in `.github/workflows/` becomes
live (`schedule:` only fires from `main`), and the API is currently unhosted.
So this is a pre-merge gate, not a pre-deploy one — but it is the last gate
there is, so treat it as final.

## Checklist

**Code**
- [ ] `make check` — ruff + mypy + pytest all green locally
- [ ] CI `full-check` green on the PR — `gh run list --workflow full-check.yml`,
  then `gh run view <run-id> --log` on any failure. This is the real gate; a
  local pass with sandbox ML collection gaps is not sufficient.
- [ ] No uncommitted changes: `git status -s`
- [ ] Branch is rebased onto `origin/main`

**Database**
- [ ] All migrations on disk applied via Supabase MCP:
  - `ls migrations/*.sql | sort | tail -1` (latest on disk)
  - `mcp__supabase__list_migrations` → confirm the latest is present
- [ ] `REQUIRED_MIGRATIONS` in `asxos/api/main.py` matches the applied row count
  in `supabase_migrations.schema_migrations` (it is an observed count, **not** a
  count of files in `migrations/`) — bump it when a new migration is applied
- [ ] Migration `0042` is NOT applied (reserved by the parked PR #80)

**Secrets**
- [ ] Any new env var a workflow needs is declared in that workflow's `env:`
  block AND present in the repo's Actions secrets. A missing secret surfaces as
  a red run, not a warning
- [ ] No `.env*` files committed: `git log --all -- '.env*'` returns nothing

**Workflows** (only if `.github/workflows/` changed)
- [ ] Each changed file parses: `python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml`
- [ ] Step order still reflects the dependency graph — a step must sit below
  everything it reads from
- [ ] Schedule change is intentional and recorded in the file's header comment

## Output

For each item: PASS ✓ or FAIL ✗.

- All pass → **Ready. Merge to `main`. Then confirm with `/health-check` after
  the next scheduled run of anything you touched.**
- Any fail → **Blocked. Fix the items marked ✗ above.**

Do NOT merge if any item is FAIL.
