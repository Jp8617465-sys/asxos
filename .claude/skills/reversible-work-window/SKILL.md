---
name: reversible-work-window
description: Run asxos dev work under arbi/Guilfoyle — code/docs/test work on claude/** or cursor/** branches, landed the AGENTS.md section 8 way (branch, make check, ready PR, wait for checks, squash). Use for long working windows (the /goal recipes) and mission build nodes. It does not reach capital, the north-star/personal-use invariant, or .claude/ — those are James's.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash(git status:*)
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git branch:*)
  - Bash(git fetch origin:*)
  - Bash(git checkout -B claude/*)
  - Bash(git switch claude/*)
  - Bash(git switch -c claude/*)
  - Bash(git checkout -B cursor/*)
  - Bash(git checkout -b cursor/*)
  - Bash(git switch cursor/*)
  - Bash(git switch -c cursor/*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push -u origin claude/*)
  - Bash(git push -u origin cursor/*)
  - Bash(make check:*)
  - Bash(make lint:*)
  - Bash(make type:*)
  - Bash(make test:*)
  - Bash(pytest:*)
  - Bash(python -m pytest:*)
  - Bash(python -m py_compile:*)
  - Bash(ruff check:*)
  - Bash(mypy:*)
  - Bash(bash -n:*)
  - mcp__github__create_pull_request
  - mcp__github__pull_request_read
  - mcp__github__merge_pull_request
---

# Reversible work window

Pre-allows the loop `AGENTS.md` §8 describes — branch, edit, `make check`, commit, push to
`claude/**` or `cursor/**`, open a **ready** PR, wait for required checks, squash-merge —
without a per-command prompt for each step. Everything outside that loop is decided by the
session's ordinary permission mode.

> **Rewritten 2026-09-14.** The previous version was written on 2026-07-14 under the
> I0–I6 permission ladder and the four-guard hook fence. Both were deleted by the
> chief-of-staff rollout (#254), and this file kept instructing behaviour that
> `AGENTS.md` now forbids — most consequentially *"Draft PR is the durable stopping
> point. Never mark ready-for-review or merge inside a window."* `AGENTS.md` §8.3 says
> the opposite in as many words ("Open the PR **ready**, not draft"), and §0 says there
> is "no draft-PR ceiling". A skill that tells arbi to stop at a draft does not make it
> safer; it makes it stop halfway and leaves the work unlanded.

## What is pre-allowed, and why that is the right ceiling

The whole §8 landing sequence, because a half-landed change is not a safer change. The
reversal-cost classes in `AGENTS.md` §6 are what bound risk here, not a prompt count: a
**Green** change is one revert away from gone, and an **Amber** one records its reversal
cost in the PR body and runs the mitigation for its shape before merging.

`cursor/**` is the Cursor Cloud Agent branch family (template `cursor/<slug>-651f`), same
ceiling as `claude/**`.

Quality is `make check` locally, then the required checks on the PR's current head. Local
results are a preflight, not a substitute (`AGENTS.md` §4). Review is risk-tiered per
`CLAUDE.md` §Review consult — Tier A for `asxos/**`, `jobs/**`, `scripts/*.py` and
behaviour-bearing tests; Tier B for docs and config. There is no PreToolUse review-gate.

## What is deliberately not pre-allowed here

- **Bare `git push`.** Only `git push -u origin claude/*` and `cursor/*` are pre-allowed.
  The red-team finding of 2026-07-14 still holds and is the reason the pattern is written
  with the explicit `-u origin` prefix: a bare `claude/*` glob is a FALSE boundary,
  because a refspec like `git push origin claude/x:main` matches it and lands on remote
  `main`. `--force-with-lease` is the operation behind the #29 auto-close incident and is
  outside this skill every time.

- **Anything touching `AGENTS.md` §2 or `.claude/`.** Capital and `asxos/capital/`; the
  personal-use invariant and `north-star.md`; spend over the A$50/day cap; and `.claude/`
  itself, where arbi's own permissions are written. arbi drafts those as a PR and James
  merges. *This file is one of them* — a change to this skill is drafted, never
  self-landed.

- **Migrations.** Authoring one on a branch is ordinary work. Applying one is the §8
  five-step sequence in one sitting, including reading `backup.yml`'s run conclusion and
  confirming it is `success` — a judgement a pre-allow cannot make, and not a thing to do
  from inside a long unattended window.

- **`AskUserQuestion` for reversible choices.** Inside a window, make the reversible call,
  record it as a `DECISION / TAKING / REVERSAL` row (`AGENTS.md` §7) and keep going.
  Governor correction L-cand-2, 2026-07-12
  (`docs/product/memory/working/2026-07-12-scope-reversible-without-asking.md`). Ask only
  at a genuine §2 boundary.

## Known limitation (red-team 2026-07-14 — still accepted)

`Edit`/`Write` here are unscoped, and the pre-allowed executors (`pytest`, `make check`,
`mypy`) run whatever the tree contains — so an edited `conftest.py` or `Makefile` is an
arbitrary-code path that does not pass through the Bash allowlist.

What has changed since that finding is the surrounding floor, and it is worth stating
precisely rather than implying it is unchanged. The four guard hooks it assumed
(`authority-guard.sh`, `push-guard.sh`, `pr-draft-guard.sh`, `unattended-guard.sh`) and the
`ARBI_UNATTENDED` variable that armed them are **gone**. What remains is
`.claude/hooks/secrets-guard.sh` (one PreToolUse hook, refusing the three shapes that would
leak a secret value into a transcript), the `main` ruleset (PR required, `full-check` on the
current head, linear history, no force push, **empty bypass list — it binds James's own
credential, which is the one arbi pushes with**), and `full-check` itself.

So the residual is real and the mitigation is the ruleset, not a hook: an edited
`conftest.py` cannot land without `full-check` passing on the PR head, and it cannot reach
`main` except through a PR.

## Binding conduct while active

- **PR transaction discipline** (L-cand-4/5,
  `docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`): chain
  commit → push → PR-state verify; re-verify after any rebase; reopen and report on a
  `head == base` auto-close; never smooth over a slip; continue only from a verified state.
- **Finish the landing.** Open the PR ready, wait for required checks on the *current*
  head, squash-merge, then watch the first production run that exercises the change
  (`AGENTS.md` §8.6). A red run is a §7 incident: stop merging new work and fix it.
- **Class every PR** in its body (`AGENTS.md` §6). Amber carries its reversal cost and the
  mitigation taken.
- The operator runbook: `docs/product/runbooks/reversible-work-window.md`.
