# Ship — Feature to Staging

Chains quality → security → performance → docs → changelog → deploy-check → staging deploy → smoke test.
Stops on first failure and reports which step failed.

$ARGUMENTS = feature name (used for docs and changelog)

## Steps (execute in order, stop on failure)

**Step 1 — Quality gates**
Run `/quality-check`. If any gate fails: stop, report gate name + error.

**Step 2 — Security scan**
Run `/security-scan`. If any CRITICAL finding: stop, list findings.

**Step 3 — Performance audit**
Check for N+1 queries, asyncpg on hot paths, bundle size impact.
If any CRITICAL perf issue: stop, report.

**Step 4 — API docs**
Generate `docs/api/$ARGUMENTS.md` covering new/changed routes.
Format: route summary table + curl examples + error codes + rate limits.

**Step 5 — Changelog**
Run `git log --oneline $(git describe --tags --abbrev=0)..HEAD`.
Append a Keep-a-Changelog entry to `CHANGELOG.md` under the current sprint heading.

**Step 6 — Deploy check**
Run `/deploy-check`. If any item fails: stop, list the failing items.

**Step 7 — Deploy to staging**
Trigger Render staging deploy via Render MCP. Wait for deploy to complete.

**Step 8 — Smoke test**
Run `/smoke-test $STAGING_URL`.
If any check fails: stop, report failed checks.

## On success

Output:
```
✓ $ARGUMENTS is ready for production.
Staging: $STAGING_URL
All 8 steps passed.

Next: review staging, then run /deploy-production to go live.
```

## On failure

Output:
```
✗ Ship failed at Step N — [step name]
Error: [error details]
Fix the issue above and re-run /ship $ARGUMENTS.
```

## Constraints

- Never auto-chain `/deploy-production` — production deploy is always an explicit human command
- If Render MCP is unavailable, stop at Step 7 and ask the user to deploy manually
