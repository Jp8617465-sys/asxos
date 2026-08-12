# Claude Execute — GitHub Actions automation harness

**Status:** installed on `main` 2026-08-12 by PR #91; authority amended in the follow-up
autonomy pack so the workflow's allowed-tools, prompt ceiling, and repo guards agree
**Workflow:** `.github/workflows/claude-execute.yml`
**Owner:** James triggers; Claude executes inside the run

## What it is

A `workflow_dispatch` workflow that runs Claude Code in automation mode via
`anthropics/claude-code-action@v1`, so build/fix/runbook tasks can be dispatched with one
command instead of driven interactively:

```bash
gh workflow run claude-execute.yml \
  -f prompt="Run tests, fix failures, and open a PR if changes are required."
```

Optional inputs: `-f max_turns=30` (default 20), `-f run_tests=false` (default true —
installs the project with `.[ml]` and expects the relevant pytest selection to run before
Claude declares done).

## Execution authority

This is an **attended, governor-triggered I3/I4 execution path**, not standing unattended
autonomy. For the scoped prompt James supplies, Claude is authorised to:

- create and work on a `claude/<short-slug>` branch;
- edit code, documentation, and configuration needed for the task;
- run tests, lint, type checks, `make check`, and validation-only workflow dispatches;
- commit, push the branch, and open a draft PR;
- update the PR by pushing follow-up commits and posting status/evidence comments;
- inspect workflow results with `gh run list/view/watch`;
- continue through recoverable failures inside scope, including test, lint, type,
  dependency-resolution, merge-base, and validation failures.

The run must stop and report the exact blocker instead of proceeding when it would need
credentials or secret creation, destructive DB operations or production data mutation,
production deployment or irreversible production writes, direct pushes to `main`, PR
ready/merge actions, self-merging unless repository policy and James's explicit instruction
authorise that exact PR, migration `0042`, or any Model A / capital-execution boundary.

## Required secrets

| Secret | Required | Purpose |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | yes | Claude authentication for the action — minted with `claude setup-token`, bills to the Claude subscription rather than a metered API key |
| `CLAUDE_WORKFLOW_PAT` | optional | Used as `GH_TOKEN` so Claude can trigger/inspect *other* workflows (`gh workflow run` / `gh run watch`); the default `GITHUB_TOKEN` cannot start new workflow runs from inside a run. Falls back to `GITHUB_TOKEN` when absent |

## Safety model

- **Trigger:** `workflow_dispatch` only. No comment/issue/push triggers — repo events can
  carry untrusted text straight into a prompt.
- **Tool scope:** `--allowedTools` grants file read/edit, `git` status/diff/branch/commit/
  push, pytest/ruff/mypy/`make check`, and the specific `gh` verbs (`workflow run` for
  validation-only workflows, `run watch/view/list`, `pr create/view/comment`). No
  unrestricted Bash.
- **Ceiling:** the embedded operating rules require branch-only work (`claude/<slug>`),
  draft PRs, no migration applies (0042 explicitly never), no Model A in any decision
  basis (rule #11), stop-and-report on credential/destructive/production-risk blockers,
  and no secret values in logs or PR text. `CLAUDE.md` loads with the checkout and
  applies to every run.
- **Mechanical backstop:** `push-guard.sh` blocks direct `main` pushes, force/delete
  shapes, non-draft PR creates, PR ready/merge, production/secret-bearing workflow runs,
  and release mutations. Server-side branch protection/rulesets, if configured, are an
  additional backstop; do not assume they are present.

Validation workflow dispatch is intentionally narrow. The harness may run
`full-check.yml`, `targeted-ml-tests.yml`, and `migration-integration.yml`; it must not
dispatch `backup.yml`, `daily-brief.yml`, `pipeline-health.yml`, `weekly-research.yml`,
`us-positions.yml`, release workflows, deploy workflows, or any secret-bearing production
job without James's explicit approval.

## Verification of a run

`gh run list --workflow=claude-execute.yml` then `gh run view <id> --log`. A code-changing
run ends with a draft PR; a no-change run ends with a summary in the run log.
