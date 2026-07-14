---
name: pr-readiness
description: Run exactly one readiness pass on a mission's draft PR before handing back — diff-scope, CI, review-loop, citation, boundary, and PR-state checks. Use at the end of /arbi-mission, /arbi-team, or a long window; not a continuous poller.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git status:*)
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git fetch origin:*)
---

# PR readiness (skill)

**One pass, no polling.** Guilfoyle (or the main loop applying Guilfoyle's criteria) scores
the finished mission against this checklist; READY → hand back; NOT-READY twice → stop and
hand James the gap list — do not grind (anti-perfectionism, `.claude/agents/guilfoyle.md`
stop conditions).

Hard gates are `docs/product/rubrics/arbi-safety-boundary.md` — reference them, never
restate. On top, verify:

1. **Diff ⊆ scope** — the PR's changed-file list is exactly (or within) the mission
   envelope's scope. Any file outside scope = NOT-READY, no exceptions.
2. **Tests green** — CI (`full-check` + `targeted-ml-tests`) SUCCESS on the head sha, or the
   documented-sandbox-gap justification for anything that only runs in CI.
3. **Review loop run** — security-engineer (if the diff touches secrets/external
   input/dependencies/financial-PII **or any permission/hook/skill surface**),
   refactoring-expert, technical-writer — per CLAUDE.md; the review-gate marker reflects a
   loop that actually ran.
4. **Citations preserved** — the envelope's `required_citations` appear in the artifacts.
5. **Draft state** — the PR is a **draft**, correctly classified docs/code, body names every
   file and states the boundaries held. Ready-for-review/merge is James's (or requires his
   explicit instruction).
6. **PR-state verification** (L-cand-4 §3) — after the final push: live-read head sha, base,
   open/closed, changed-file count; on a head==base auto-close, reopen + report.
7. **No forbidden boundary in the diff** — grep the diff for the envelope's
   `forbidden_boundaries` surfaces (settings.json allows, hook weakening, migrations,
   `mcp__supabase__` writes, Render, secrets, `main`-push).
8. **Follow-ups recorded, not pursued** — anything discovered lands in the
   backlog/ledger/risk-register, not in the PR.

Then append the mission row to `docs/product/arbi-run-ledger.md` (`task_type: mission`, or
`team-mission` when ending an `/arbi-team` run) and stop.
