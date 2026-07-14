# Runbook — launching a reversible work window

**Status:** current (autonomy unlock pack, 2026-07-14)
**Scope:** operator steps for James to launch, bound, and audit a long reversible-dev window
**Last verified:** 2026-07-14
**Owner:** James (operator); the recipes are `docs/product/arbi-goal-recipes.md`
**Superseded by:** N/A

## Before launching

1. **Main is current** — merge or park anything the window would collide with; the window
   branches off `main` (`arbi-goal-recipes.md` rule: fresh branches per mission).
2. **Pick the recipe** — R1 (12-hour, 3–5 PRs) or R2 (8-hour, ≤3 PRs) from
   `arbi-goal-recipes.md`. Do not free-hand the boundaries; the recipe *is* the envelope.
3. **Know what will still prompt** — the `reversible-work-window` skill
   (`.claude/skills/reversible-work-window/SKILL.md`) pre-allows the reversible loop
   (edit/test/commit/push-to-`claude/**`/draft-PR). Anything else — bare `git push`, any
   `mcp__supabase__*` write, Render, merges — still asks or is denied. That is by design;
   deny-first is the floor.
4. **Accept the documented residual (red-team 2026-07-14):** the window skill's `Edit`/`Write`
   are unscoped and its pre-allowed test runners execute whatever the tree contains — an
   edited `conftest.py`/`Makefile` is an arbitrary-code path, and Write can reach `.claude/**`.
   Attended you see the edits; unmonitored, this residual is open until **PR-2 (Permission
   Friction Pack)** lands the mechanical guards (settings `deny` for authority paths;
   attended authority-path check in the guard hook). Launching a long unmonitored window
   before PR-2 means accepting that residual explicitly — it is listed in the skill's
   "Known limitation" section.
5. **Optional (teams):** if the window may run an `/arbi-team` mission, set the **local/user**
   env `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (see `runbooks/agent-team-mission.md`).
   Never commit this to repo config.

## Launch

6. Paste the recipe's `/goal` block verbatim (edits to its hard floor or discipline block are
   boundary changes — make them in the recipe doc via PR first, not ad-hoc in the prompt).

## During (what the window may and may not do)

- May: arbi wake → red-team → Guilfoyle-led missions → builders on `claude/**` branches →
  draft PRs. Reversible calls are made without asking (L-cand-2, `memory/working/2026-07-12-scope-reversible-without-asking.md`); JAMES_NEEDED items are
  logged and pivoted past, not ground against.
- May not (hard floor): merge/deploy/`main` push · DB write/migration · Render mutation ·
  secrets · capital/broker anything · authority-file change as active truth · leaving a
  ready artifact branch-only (L-cand-3, same memory file: the draft PR is the durable stopping point).
- Binding conduct: the **PR transaction discipline** block (L-cand-4/5) for every branch
  touch.

## After — the audit trail (10 minutes)

7. Read the **morning report**: decisions needed · completed PRs · skipped/deferred · risks
   found · recommended merge order.
8. Verify the ledger row exists (`docs/product/arbi-run-ledger.md`) and matches the report.
9. Spot-check one PR: diff ⊆ its stated scope, CI green, review-loop claims plausible,
   PR is a **draft**.
10. Merge order is yours — nothing in the window merged anything. Any slip must appear in the
   report and the ledger (a smoothed-over slip is a circuit-breaker matter, not a style
   issue).
