# Claude Execute — GitHub Actions automation harness

**Status:** workflow authored 2026-08-12; installation requires James (`.github/` is
authority-guarded — the workflow file is placed by the governor, not an agent)
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

## Required secrets

| Secret | Required | Purpose |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | yes | Claude authentication for the action — minted with `claude setup-token`, bills to the Claude subscription rather than a metered API key |
| `CLAUDE_WORKFLOW_PAT` | optional | Used as `GH_TOKEN` so Claude can trigger/inspect *other* workflows (`gh workflow run` / `gh run watch`); the default `GITHUB_TOKEN` cannot start new workflow runs from inside a run. Falls back to `GITHUB_TOKEN` when absent |

## Safety model

- **Trigger:** `workflow_dispatch` only. No comment/issue/push triggers — repo events can
  carry untrusted text straight into a prompt.
- **Tool scope:** `--allowedTools` grants file read/edit, `git` status/diff/branch/commit/
  push, pytest/ruff/mypy/`make check`, and the specific `gh` verbs (`workflow run`,
  `run watch/view/list`, `pr create/view/comment`). No unrestricted Bash.
- **Ceiling:** the embedded operating rules require branch-only work (`claude/<slug>`),
  draft PRs, no migration applies (0042 explicitly never), no Model A in any decision
  basis (rule #11), stop-and-report on credential/destructive/production-risk blockers,
  and no secret values in logs or PR text. `CLAUDE.md` loads with the checkout and
  applies to every run.
- **Mechanical backstop:** GitHub branch protection on `main` (see the autonomy-unlock
  proposal) — the prompt ceiling is discipline, branch protection is enforcement.

## Verification of a run

`gh run list --workflow=claude-execute.yml` then `gh run view <id> --log`. A code-changing
run ends with a draft PR; a no-change run ends with a summary in the run log.
