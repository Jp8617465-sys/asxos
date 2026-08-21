# Check Drift — deprecated

**Deprecated. There is nothing to reconcile.** This command diffed deployed
Render services against a checked-in `render.yaml`. Render was deleted
2026-08-12 and `render.yaml` no longer exists.

Job configuration now lives in `.github/workflows/`, in git, reviewed. There is
no separately deployed copy of it to drift from — the file *is* the
configuration, and it takes effect on merge to `main`. Deployed-state drift was
a property of the old platform, not a permanent class of risk.

## What to run instead

- **What is configured** — read the workflow files: `.github/workflows/`.
- **What actually ran** — `gh run list`, then `gh run view <run-id> --log`.
- **Whether the pipeline is healthy** — `/health-check`.
- **Whether a change is safe to merge** — `/deploy-check`.

The one real reconciliation still worth doing is schema, not services:
migrations on disk versus migrations applied in Supabase. `/deploy-check`
covers it.
