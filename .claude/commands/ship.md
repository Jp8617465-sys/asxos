# Ship — Feature to Production

There is no staging and **there is no deploy step**. asxos has one environment —
`main`. Merging to `main` is the whole action: job configuration in
`.github/workflows/` takes effect from that moment (`schedule:` only fires from
`main`). Nothing builds, nothing rolls out, nothing to watch go `live`. Be
deliberate — the merge is the irreversible part.

$ARGUMENTS = feature name (used for changelog if you keep one).

## Steps (stop on first failure)

**Step 1 — Quality gates**
Run `/quality-check`. If any fails: stop.

**Step 2 — Security scan**
Run `/security-scan`. If any CRITICAL finding: stop.

**Step 3 — Pre-merge check**
Run `/deploy-check`. If any item fails: stop.

**Step 4 — Merge**
Open the PR ready, confirm CI `full-check` is green on its current head, and
squash-merge it (`AGENTS.md` §8). Merges are arbi's (`AGENTS.md` §2); the only
PRs arbi opens and does not merge are `.claude/**`, `north-star.md` and §2 items.

**Step 5 — Confirm**
Config changes are live but not yet *exercised*: a schedule change proves itself
only on its next run. After the next scheduled run of anything you touched:

```bash
gh run list
gh run view <run-id> --log   # on any red run
```

Then `/health-check` for job-run health and Supabase data freshness.

## On success

```
✓ $ARGUMENTS merged to main.
Workflow config live from this commit. No deploy step.
Next scheduled run of [workflow]: [UTC time] — confirm with `gh run list`.
```

## On failure

```
✗ Ship failed at Step N — [step name]
Error: [details]
```

Pre-merge failures have no production impact. A post-merge failure shows up as a
red run: read it with `gh run view <run-id> --log` and fix forward, or revert the
commit on `main`. There is no previous build still serving traffic to fall back
on — that was a property of the old hosting.

## Constraints

- Never merge if `/deploy-check` fails
- Never merge a commit that hasn't been rebased onto `origin/main`
- Do NOT push directly to `main` — changes land through a reviewed PR
- Do NOT dispatch a production, secret-bearing workflow to "test" the change.
  Dispatch is allowed only for `full-check.yml`, `targeted-ml-tests.yml`,
  `migration-integration.yml`, `backup.yml` and `claude-execute.yml`;
  `daily-brief` and `us-positions` are denied and reserved to James
- A new secret must exist in the repo's Actions secrets BEFORE the workflow that
  reads it merges, or the first scheduled run fails
