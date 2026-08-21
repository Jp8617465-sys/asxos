# ASXOS session handoff — 2026-07-17

**Status:** current · supersedes `session-handoff-2026-07-16.md`
**Session type:** attended (James = governor) — guardrail repair + branch-protection enablement
**Owner:** arbi maintains; James owns risk appetite
**Next session:** read this + `docs/product/roadmap-state.md` + `docs/product/risk-register.md` + `CLAUDE.md` before acting.

---

## Session summary — what shipped

- **R16 RESOLVED** (PreToolUse guards inert in the web/remote harness). Two-layer cause:
  1. `.*`-matcher hooks don't fire in this harness — fixed with **exact per-tool matchers** (PR #51, merged 2026-07-16).
  2. The load-bearing blocker: the hook scripts were committed **non-executable (100644)** and `settings.json` invoked them **by bare path**, so the OS returned exit 126 and the harness saw no decision. Only `review-gate.sh` (which kept its `100755` bit) ever fired.
  **Fix:** PR #53 (squash `a56670f`) wraps every `.claude/hooks/*.sh` invocation in `bash`, which runs them regardless of exec bit. Revives `authority-guard`, `push-guard`, `pr-draft-guard`, `unattended-guard`. Verified end-to-end in-session (probe denied through the real PreToolUse chain).
- **GitHub Pro ACTIVE + branch protection live on `main`.** Ruleset: require a PR, require the `full-check` status check, **0 required approvals** (solo-repo-safe), block force-push, restrict deletions. Confirmed enforcing — #53 sat at `mergeable_state=blocked` until `full-check` went green. This is the server-side backstop R5/R16 named as the missing piece: the safety boundary has moved from local prompts to GitHub.
- **PR #52 closed** (superseded — it targeted `claude/idea-lane-2026-07-16`, which predates #51 and would have conflicted on `main`).

## DO THIS FIRST — verify the guardrails actually fire (a running container can't hot-reload settings)

In a **fresh session on `main`**, run:

```
python3 -c "print('render.yaml')"
```

- **DENIED** by `authority-guard` → guards are live. Proceed.
- **PRINTS** the string → the fix did not take. **STOP**, do no work that assumes mechanical guards, and escalate to James.

## Standing guardrails (constitutional — never cross)

- **Rule #11** — Model A is quarantined. Do NOT use its signals / candidate scans / allocator output / new-thesis proposals for any real capital decision. Dormant passive monitor only.
- **s766B personal-advice firewall** — no personal financial advice surfaced in a multi-user shape.
- **RED ZONE (never autonomous):** push/merge to `main`, force-push, deploy / Render mutation, DB writes / apply migrations, read secrets / `.env`, capital or broker execution, and **direct edits to authority files** (`.claude/**`, `.github/**`, `migrations/**`, `render.yaml`, `CLAUDE.md`, `docs/product` governance docs). Hard-denied in `settings.json`, and `.claude/`/`.git` are additionally gated by the auto-mode classifier.
- **Authority / boundary changes** may only be **DRAFTED as a PR for James to merge** — never self-applied, never self-merged. arbi does not merge; James merges.
- **Unattended runs** (`ARBI_UNATTENDED=1` — set in the launch env; arbi cannot self-arm it): reversible, non-authority, draft-PR-only. Nothing touching `.claude/**` is possible unattended (deny rule + classifier + `unattended-guard` all block it).

## Prioritized next work

1. **[ATTENDED-ONLY — touches `.claude/`] The lane-rework** — the enabling change now that `main` is protected. Move yellow-lane files (`migrations/**`, `render.yaml`, `.github/**`, `CLAUDE.md`, `docs/product/**`, `.claude/**`) OUT of hard-`deny` and replace with an attended/branch-only **authority-maintenance** PreToolUse hook (same shape as `unattended-guard`: deny these paths when `ARBI_UNATTENDED=1`, or unless `ASXOS_AUTHORITY_MAINTENANCE=1`). Note: `.claude/**` and `.git` stay classifier-gated regardless, so they become edit-with-approval, not free. **Draft PR only; James merges.** Cannot be done unattended.
2. **[OK — normal doc] Update `risk-register.md` R16** → `resolved 2026-07-17 (PR #53, a56670f)`.
3. **[OK] Branch cleanup** — delete merged/dead branches: `claude/hook-bash-wrap-2026-07-17` (merged), `Jp8617465-sys-patch-1` (PR #52 closed), `claude/hook-matcher-fix-2026-07-16` (merged via #51), `claude/pretooluse-guard-container-test-xz0uey` (nothing of value pushed). **Do NOT delete** `claude/idea-lane-2026-07-16` — it carries 3 unmerged commits (a themes `--from-agent-run` feature + 2 doc artifacts) needing separate handling.
4. **[JAMES-GATED, tracked] R2** — re-point the agent MCP to the read-only Postgres role (migration 0039 applied 2026-07-16; MCP re-point pending). The real DB-write backstop. Not a solo/automated task.

## Operational gotchas

- **`authority-guard` substring-matches raw command text:** a write-verb token (`>`, `cp`, `python`, `mv`, …) in the SAME command that also names an authority path — even inside an `echo` label or a `2>/dev/null` redirect — is denied. Keep authority-path reads free of redirects and write-verb words.
- **`review-gate`** blocks `git commit` while `.py` is staged until the review loop runs and the `.claude/.review-passed-<sha>` marker is written. Doc/config-only commits are not gated.
- **Landing any authority change:** GitHub MCP → branch off `main` → `create_or_update_file` → **draft PR** → James marks ready + merges (`full-check` must be green). The local Edit/Write tools and Bash writes to authority paths are blocked (deny rule + classifier).
- **Model identity** never appears in commits / PRs / code — chat only.

## Pending James

- The fresh-session **probe confirmation** on `main` (30 seconds).
- Decide whether/when to do the **lane-rework** (attended).
- Remainder of `/arbi-close` not done here: **`roadmap-state.md` header bump** + **decision-log / run-ledger rows** for this session.

## Do NOT

- Reopen PR #52 or #53, or re-open the R16 change (merged, done).
- Merge to `main`, deploy, write the DB, or act on Model A autonomously.

---

_arbi-close bookend for 2026-07-17. Guardrail layer fixed **and** server-side backstop live in one session._
