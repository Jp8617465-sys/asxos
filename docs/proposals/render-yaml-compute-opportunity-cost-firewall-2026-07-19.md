# Proposal: `ASXOS_PERSONAL_USE=1` on `asxos-compute-opportunity-cost` (render.yaml)

**Status:** proposed — arbi cannot write to `render.yaml` (authority-guarded, same
mechanism as the migrations/ and `.claude/agents/` proposals). James applies this
one-line diff directly (or via `git apply`) and pushes to `main`.

**This is a merge-blocking prerequisite, not an optional follow-up — read this before
merging the accompanying draft PR.** Unlike the other two open proposals (agent-RO
frontmatter, Phase C migration), which are additive and independently deferrable, this
one has a **breaking dependency in the other direction**: the companion code change
(already committed on `claude/whats-new-yemcl4`) makes `jobs/compute_opportunity_cost.py`
hard-fail immediately unless `ASXOS_PERSONAL_USE=1` is set in its environment. Today
`render.yaml`'s `asxos-compute-opportunity-cost` cron block does **not** set that
variable — so if the code change reaches `main` (and Render auto-deploys, per
`autoDeploy: true`) before this render.yaml diff is also applied, the **next scheduled
run (Saturday 20:05 UTC) will fail every time** until the fix lands. `job_runs` will
show `status='failed'`, Healthchecks.io will get the `/fail` ping (not silence — see
`job-conventions.md`), and Section 10 of the brief (opportunity-cost redeployment
ranking) will go stale.

Apply this diff in the same push/deploy as the PR, or immediately after — not on a
separate later schedule.

## Why the code needed the change

`jobs/compute_opportunity_cost.py` reads `theses` (symbol, watching-status) and
`holding_lots`/portfolio state to rank redeployment candidates per active thesis — the
same class of personal-advice data (s766B) as `check_au_positions.py`,
`check_us_positions.py`, `snapshot_portfolio.py`, and `check_thesis_invalidations.py`,
all of which already call `require_personal_use_job()` as their first statement
(`.claude/rules/portfolio-conventions.md`, Part 0 Q1). `compute_opportunity_cost.py` was
the one job in this family that had never gotten the in-code backstop — it relied solely
on render.yaml, the exact gap `tests/test_jobs_personal_use_gate.py`'s docstring already
called out as the R14 audit finding for the other four jobs. Sprint follow-up
(2026-07-19) closes the same gap here for consistency; see risk-register R17 context and
`docs/product/roadmap-state.md`.

The in-code guard is now live on the branch:

```python
# jobs/compute_opportunity_cost.py
async def main() -> None:
    # Personal-use firewall (Part 0 Q1 / CLAUDE.md #10). In-code backstop so a
    # missing flag fails loud rather than relying on render.yaml alone.
    require_personal_use_job()
    as_of = date.today()
    ...
```

This is correct and desired — the whole point of `require_personal_use_job()` is to fail
loud rather than silently process personal data on a misconfigured host. But it means
render.yaml must now supply the flag, matching every sibling job.

## Exact diff

Verified against the live `render.yaml` (lines 563-583) via `git apply --check`, which
now succeeds with **zero offset** (no fuzzy line-matching needed) — a first draft of
this doc had a hand-typed, incorrect hunk header; security-engineer caught it during
this change's review pass (the old header applied only via fuzzy offset-matching),
corrected below. Note: classic POSIX `patch --fuzz=0` still declines this hunk despite
the content and line counts being verified byte-accurate (a `patch`-vs-`git apply`
Plan-A matching quirk, not a content error) — apply with `git apply`, or edit the two
lines in directly using the before/after context shown here as the guide.

```diff
--- a/render.yaml
+++ b/render.yaml
@@ -563,21 +563,23 @@
   # Opportunity cost computation — 20:05 UTC Saturday (after build_portfolio 20:00 Sat).
   # CGT-adjusted ranking of redeployment candidates per active thesis.
   # Populates opportunity_cost_scenarios for brief Section 10.
   - type: cron
     name: asxos-compute-opportunity-cost
     runtime: python
     region: oregon
     plan: starter
     branch: main
     buildCommand: pip install -e ".[ml]"
     schedule: "5 20 * * 6"
     command: python jobs/compute_opportunity_cost.py
     envVars:
       - key: PYTHON_VERSION
         value: 3.12.13
+      - key: ASXOS_PERSONAL_USE
+        value: "1"
       - fromService:
           type: web
           name: asxos-api
           envVarKey: DATABASE_URL
       - key: HEALTHCHECK_URL_COMPUTE_OPPORTUNITY_COST
         sync: false
```

This mirrors the existing `asxos-check-au-positions` block byte-for-byte in pattern
(`- key: ASXOS_PERSONAL_USE` / `value: "1"`, placed immediately after `PYTHON_VERSION`
and before the `DATABASE_URL` `fromService` entry) — see `render.yaml` around line 688.

## Post-apply steps

1. Apply the diff above to `render.yaml` on `main` (directly, or by merging this PR then
   pushing this one follow-up line — either order is fine as long as both land before the
   next Saturday 20:05 UTC run).
2. `make check-drift` to confirm Render's live service config now matches
   `render.yaml` (CLAUDE.md rule #2 — no dashboard edits).
3. No manual trigger needed — the next scheduled run (Saturday 20:05 UTC) will pick it
   up. If you want to confirm sooner, a manual run via the Render dashboard's "Trigger
   Run" button is read/write-safe (idempotent UPSERT into `opportunity_cost_scenarios`
   per `job-conventions.md`) and will now require the flag to be present, i.e. it's a
   correct live test of this exact fix.

## Deferred

None — this is a single-line, single-purpose fix. It does not touch the other jobs in
this family (already gated) or open any new scope.
