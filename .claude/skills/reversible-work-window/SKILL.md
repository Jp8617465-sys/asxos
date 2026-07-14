---
name: reversible-work-window
description: Run asxos reversible dev work under arbi/Guilfoyle — code/docs/test work on claude/** branches that may open draft PRs but cannot merge, deploy, migrate, mutate production DB/Render, read secrets, or execute capital actions. Use for long autonomy windows (the /goal recipes) and mission build nodes.
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
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push -u origin claude/*)
  - Bash(git push --force-with-lease -u origin claude/*)
  - Bash(make check:*)
  - Bash(pytest:*)
  - Bash(python -m pytest:*)
  - Bash(python -m py_compile:*)
  - Bash(ruff check:*)
  - Bash(mypy:*)
  - Bash(bash -n:*)
---

# Reversible work window

This skill is the **prototype of orchestrator-mode R-A4** (skill-scoped `allowed-tools`
instead of broadening the standing permission surface —
`docs/proposals/orchestrator-mode-2026-07-13.md`). While it is active, the reversible
branch/edit/test/draft-PR loop runs without per-command allow prompts. Everything else
prompts or is denied exactly as before.

## What is pre-allowed (and why it is safe)

Only I0–I4 actions (`docs/product/arbi-permission-model.md` — the authority): read/search,
edit, tests/linters, staging/commits (the `review-gate.sh` hook still gates every commit with
staged `.py`, including the R13 same-step-staging denial), and push **only to `claude/**`
branches** (`git push -u origin claude/...` — the pattern binds the ref).

## What deliberately stays outside this skill

- **Bare `git push`** — not listed, so it asks. A glob cannot see the current branch's
  upstream, so an unqualified push cannot be mechanically proven safe; type the explicit
  `claude/**` form instead. **This is honest pattern-granularity: a glob is a convenience
  filter, not a boundary.**
- Anything I5/I6: merge, push to `main`, `gh pr merge`, migrations, every `mcp__supabase__*`
  write, Render API mutation, secrets. Not pre-allowed here and still denied/asked at the
  settings/hook layer — the hard floor is unchanged by this skill.
- `AskUserQuestion` for reversible choices — inside a window, make the reversible call and
  log it (governor correction L-cand-2, 2026-07-13); ask only at real James-boundaries
  (I5/I6/P5/P6, capital, policy).

## Binding conduct while active

- **PR transaction discipline** (L-cand-4/5,
  `docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`): chain
  commit+push+PR-verify; verify PR state after any force-push/rebase; reopen+report on
  head==base auto-close; never smooth over a slip; continue only on verified-safe state.
- Draft PR is the durable stopping point. Never mark ready-for-review or merge inside a
  window unless James instructed it.
- The runbook for launching a window: `docs/product/runbooks/reversible-work-window.md`.
