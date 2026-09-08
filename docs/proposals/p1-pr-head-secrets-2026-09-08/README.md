# P1 — zero repository-secret-bearing PR-head workflows (2026-09-08)

Staged, not applied. `.github/**` is fenced (`.claude/settings.json`,
`authority-guard.sh`), and `AGENTS.md` §5 makes every workflow-definition edit Amber, so
James applies these. Same shape as `fence-integrity-2026-09-06/` and `asxos-control/`.

Work item: ACP plan §23.4 `P1` (programme `#204`, Phase 0 `#205`). The plan's own words:
*"`P1` must ultimately leave zero repository-secret-bearing PR-head workflows. The current
two are `migration-drift.yml` and `pr-review-agent.yml`. … Do not solve this by switching
casually to `pull_request_target` and checking out the PR head."*

## The exposure, measured

`tools/workflow_inventory.py --format md` on `main` at `226bb2f` (2026-09-08):

| Workflow | PR-head trigger | Secret refs | Exposed |
|---|---|---|---|
| `migration-drift.yml` | `pull_request` | `DATABASE_URL` | **YES** |
| `pr-review-agent.yml` | `pull_request` | `GITHUB_TOKEN`, `OPENAI_API_KEY` | **YES** |

16 workflows · 5 PR-head · **2 exposed to an authored PR**. Unchanged since the 09-06 and
09-07 measurements.

Why each is exposed, from the parsed `on:` block, not from grep:

- **migration-drift** — its `pull_request.paths` filter names **its own file**. A PR that
  edits the workflow triggers it, and the definition that runs is the *edited* one, at
  the PR head, with `DATABASE_URL` in scope. The `ref: refs/heads/main` on the checkout
  step does not help: the workflow YAML itself comes from the PR.
- **pr-review-agent** — `pull_request: [opened, reopened, synchronize, ready_for_review]`
  runs `scripts/pr_review_agent.py` from the PR head with `OPENAI_API_KEY` and
  `issues: write`. The `draft == false` guard only delays it to the ready click; the two
  open dependabot PRs (#214, #215) are not draft and re-trigger it on every synchronize.

## The change

Both patches remove the `pull_request` trigger and nothing else functional.

| Patch | Keeps | Removes | Behaviour after |
|---|---|---|---|
| `migration-drift.patch` | `schedule` (daily 06:00 UTC), `workflow_dispatch`, checkout of `refs/heads/main`, the secret | the `pull_request` block and its self-referencing paths filter | Drift still caught daily. A migration file committed-but-not-applied is caught by the next daily run after merge; `migration-integration.yml` (secretless, `pull_request`) still exercises the file at PR time. |
| `pr-review-agent.patch` | `push: main`, the env block, permissions | the `pull_request` trigger and the now-redundant `draft == false` job condition | Reviews main-branch commits only — code James merged. PR-head review of agent branches stops here and returns as an `asxos-control` broker (ACP §5.5), which is where the plan already puts it. |

Neither patch touches a step, a pinned action SHA, a permission, or a secret name.
`pull_request_target` was not used, per the plan.

Inventory on the patched files (scratch copy, same tool, same parser):

```
Workflows: 2 · PR-head: 0 · exposed to an authored PR: 0
```

Once applied on `main`, the full-tree inventory should read `16 · 3 · 0`
(`full-check`, `migration-integration`, `targeted-ml-tests` remain PR-head and secretless).

## What this does not do

- It does not move the secrets out of the product repository. Nine named Actions
  secrets remain here (`#205` findings). Evacuation to control-owned environments is the
  rest of `P1` and needs `asxos-control` to exist first (`P2`). This patch closes the
  *PR-head* exposure, which is the part that does not wait on `P2`.
- It does not close backlog `A-22` (branch-scoped producer credential on the standing
  lanes) — the plan is explicit that removing PR-head secrets does not close it.
- It does not restore PR-head review through another route. If James wants owner-run
  review of a specific PR before the broker exists, that is a `workflow_dispatch` input
  plus a small change to `scripts/pr_review_agent.py` (it currently reads the PR from
  the event payload) — a separate Green change to `scripts/`, not staged here.

## Applying

```sh
P=docs/proposals/p1-pr-head-secrets-2026-09-08
git apply --check $P/migration-drift.patch $P/pr-review-agent.patch $P/test-workflow-inventory.patch
git apply         $P/migration-drift.patch $P/pr-review-agent.patch $P/test-workflow-inventory.patch
python3 tools/workflow_inventory.py --format md     # expect: 16 · 3 · exposed 0
make check
```

**Apply all three together.** `tests/test_workflow_inventory.py::test_live_repo_exposure_set_is_pinned`
pins the exposure set to exactly these two files; `test-workflow-inventory.patch` re-pins it to
empty. Applying the workflow patches without it turns that test red; applying the test patch
first does the same in the other direction. `tests/` is not fenced, so the test change could
have been committed directly — it is staged instead for the same reason as
`fence-integrity-2026-09-06/tests-staged/`: a red test on `main` describing a change that has
not happened is a to-do list, not a test.

Tier: **Amber** (workflow definition change). Rollback is `git revert` — but note the
plan's rule: safe rollback is manual/secretless operation, never the exposed state. If
the daily drift check or the main-branch review proves unwanted after this lands, the
next move is to disable the schedule, not to restore `pull_request`.

Both patches were generated from scratch copies of the two files (`diff -u`) and
verified with `git apply --check` against `main` at `226bb2f`. The fenced files were
not opened for writing.
