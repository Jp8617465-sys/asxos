# Ship — Feature to Production

There is no staging. asxos has one environment — main. Pushing to `main`
triggers Render auto-deploy across all 9 services. Be deliberate.

$ARGUMENTS = feature name (used for changelog if you keep one).

## Steps (stop on first failure)

**Step 1 — Quality gates**
Run `/quality-check`. If any fails: stop.

**Step 2 — Security scan**
Run `/security-scan`. If any CRITICAL finding: stop.

**Step 3 — Deploy check**
Run `/deploy-check`. If any item fails: stop.

**Step 4 — Push**
```bash
git push origin main
```

**Step 5 — Watch the deploy**
For each service that auto-deploys, watch the build via
`mcp__render__list_deploys`. Wait until each is `live` (or fail).
The web service (`asxos-api`) is the fastest signal — if its lifespan
hard-fails (DB unreachable, migration drift, model artefact missing) the
deploy will not go live.

**Step 6 — Smoke test**
```
/smoke-test https://asxos-api.onrender.com
```

**Step 7 — Drift check**
```
/check-drift
```

## On success

```
✓ $ARGUMENTS shipped.
asxos-api: live at https://asxos-api.onrender.com
All 9 services auto-deployed. /health green. No drift.
```

## On failure

```
✗ Ship failed at Step N — [step name]
Error: [details]
```

If the failure is post-push (Step 5+), the previous build is still running
on Render — the new bad build never replaced it. No rollback action needed.
If the failure is pre-push, no production impact.

## Constraints

- Never push if `/deploy-check` fails
- Never push a commit that hasn't been rebased onto `origin/main`
- If you're on a feature branch, fast-forward `main` first then push;
  Render only auto-deploys from `main`
- The token in `~/Projects/asxos-secrets/.env.production` must match
  `ASXOS_API_TOKEN` set on `asxos-api` — if you rotated locally, upload
  via `mcp__render__update_environment_variables` BEFORE pushing
