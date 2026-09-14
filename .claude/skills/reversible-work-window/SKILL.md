---
name: reversible-work-window
description: Pre-allow the reversible edit/test/commit loop for asxos work on claude/** or cursor/** branches so it runs without per-command prompts. Pushes, PR creation, merges, migrations and Supabase writes stay outside the allowlist and prompt as usual; arbi's authority over them is AGENTS.md §2/§8, not this skill. Use for mission build nodes.
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
edit, tests/linters, staging/commits. `cursor/**` is the Cursor Cloud Agent branch family
(template `cursor/<slug>-651f`); same reversible ceiling as `claude/**`. Quality is
`make check` + CI. Consult is risk-tiered (`docs/product/harness-profiles.md`);
there is no PreToolUse review-gate.

## What deliberately stays outside this skill

- **EVERY `git push`** — pushes always ask. The red-team (2026-07-14) proved a
  `claude/*`-glob push pattern is a FALSE boundary: a refspec like
  `git push origin claude/x:main` matches the glob and lands on remote `main`. And
  `--force-with-lease` is exactly the operation behind the #29 auto-close incident
  (L-cand-4 §2) — it earns a prompt every time. One ask per push is the price of an honest
  floor.
- **PR creation** — the GitHub tools ask. If a window run has a ready artifact and the
  PR-creation prompt cannot be answered (operator asleep), "ready + PR queued, surfaced
  first in the morning report" satisfies L-cand-3 (`docs/product/memory/working/2026-07-12-scope-reversible-without-asking.md`) — see `docs/product/arbi-goal-recipes.md`.
- Anything I5/I6: merge, push to `main`, migrations, every `mcp__supabase__*` write, Render
  API mutation, secrets. Not pre-allowed here. The settings `deny` array plus
  `authority-guard.sh` / `push-guard.sh` / `pr-draft-guard.sh` are the attended
  mechanical floor; `unattended-guard.sh` still treats `CLAUDE.md`,
  `.claude/settings.json`, and `.claude/hooks/` as authority when
  `ARBI_UNATTENDED=1`.
- `AskUserQuestion` for reversible choices — inside a window, make the reversible call and
  log it (governor correction L-cand-2, 2026-07-12,
  `docs/product/memory/working/2026-07-12-scope-reversible-without-asking.md`); ask only at
  real James-boundaries (I5/I6/P5/P6, capital, policy).

## Known limitation (red-team 2026-07-14 — accepted, gated)

`Edit`/`Write` here are unscoped, and pre-allowed executors (`pytest`, `make check`, `mypy`)
run whatever the tree contains — so an edited `conftest.py`/`Makefile` is an arbitrary-code
path that bypasses the Bash allowlist. Attended, the operator sees the edits; quality is
`make check` + CI. Authority paths still in the deny list remain blocked by
`authority-guard.sh`. **This skill must not be active in an unmonitored window
without the operator accepting the residual** — the runbook states it.

## Binding conduct while active

- **PR transaction discipline** (L-cand-4/5,
  `docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`): chain
  commit+push+PR-verify; verify PR state after any force-push/rebase; reopen+report on
  head==base auto-close; never smooth over a slip; continue only on verified-safe state.
- A ready PR is the durable stopping point (`AGENTS.md` §8 opens PRs ready, not draft).
  Landing it is arbi's, outside this skill's allowlist: the push and the merge prompt,
  and are taken per §8 once required checks pass on the current head.
- **Stale references (2026-09-14, not rewritten here):** `authority-guard.sh`, `push-guard.sh`,
  `pr-draft-guard.sh`, `unattended-guard.sh`, `docs/product/arbi-permission-model.md`,
  `arbi-goal-recipes.md` and the I0–I6 ladder were deleted or withdrawn by Amendment N
  (`docs/product/roadmap-state.md`, 2026-09-10). Retiring or rewriting this skill is a
  separate call; this edit only removes the draft-only instruction that contradicts §8.
- The runbook for launching a window: `docs/product/runbooks/reversible-work-window.md`.
