# arbi autonomy loop — the self-driving cycle (git-native)

**Status:** current (machinery built; **standing activation gated — see §Activation**)
**Scope:** how arbi runs the observe→decide→act→learn loop on a schedule, in Claude Code
**Last verified:** 2026-08-12 (`claude-execute.yml` installed by PR #91; guard carve-outs
PRs #92/#93 — layer 2 branch protection confirmed CONFIGURED, activation precondition 2 now
MET; standing scheduled activation still gated on preconditions 3–5 — see §Activation).
**Layer 1 re-verified 2026-08-20** after the worktree-scoping defect below.
**Owner:** James enables standing autonomy; arbi runs within the guardrails
**Superseded by:** N/A

The hourly/daily loop you asked for — built on **Claude Code Routines + git + GitHub**, no
Managed Agents required. Managed Agents is an optional hosted backend, not a prerequisite
(`arbi-managed-agent-spec.md` is the map for that later option).

---

## The cycle

```
Routine fires (ARBI_UNATTENDED=1)                         ← scheduler (Claude Code Routine)
  → /arbi            observe live state, decide THE ONE THING          (I0-I1)
  → /arbi-run        dispatch the named specialists in parallel        (I4, reversible)
  → implement        on a claude/** branch                            (I2-I3)
  → test             make check / targeted pytest + ruff(0.7.0) + mypy
  → review loop      security-engineer / refactoring-expert / technical-writer
  → open a PR        CI runs; report to James                          (I3, draft)
  → STOP at merge    ← James merges (I6 = prod deploy)                 ← THE HUMAN GATE
  → /arbi-close      append run-ledger + decision-log + working memory (I2)
weekly:  /arbi-dream    consolidate → dream-candidate PR
monthly: /arbi-promote  candidate → approved-lessons (James merges)
```

The loop drives itself to a **green PR** and stops. It does not merge — merge = prod deploy,
reserved to James (I6). It learns every cycle (the ledgers) and consolidates weekly
(the dream), so it stops repeating mistakes.

## What makes an unattended run SAFE (three mechanical layers)

Not prompt-hope — mechanical, defense-in-depth:

1. **`unattended-guard.sh`** (`.claude/hooks/`, armed by `ARBI_UNATTENDED=1`): a PreToolUse
   hook that DENIES push/merge to `main`, force-push, RW-DB SQL, migrations, Render
   mutations, PR merges, secret reads, and edits to authority/boundary files. Attended
   sessions: total no-op. (Verified 13/13 cases 2026-07-10 — **scoped to the primary
   checkout**; see the correction below.)

   **⚠️ The 13/13 verification was narrower than it read (corrected 2026-08-20).** Every path
   and branch lookup in this hook was anchored to `$CLAUDE_PROJECT_DIR`, so a tool call made
   inside a **git worktree** resolved against an unrelated tree: the repo-relative strip never
   matched, and the authority- and capital-path categories silently failed **OPEN** — the
   inverse of this hook's fail-closed contract. That is the topology `arbi-run-ledger.md`
   itself recommends for parallel missions, so it was a live gap, not a theoretical one.
   `review-gate.sh` (staged Python committed ungated) and `push-guard.sh` (a push from a
   worktree on `main`) carried the same defect. **Closed 2026-08-20:** all three now resolve
   the payload's own `.cwd` to its git toplevel and test both that checkout and the control
   checkout, mirroring `authority-guard.sh` — the only one that was already correct.
   Re-verified live against a real worktree (ALLOW before, DENY after) with eight primary-root
   regression cases unchanged: `tests/test_hook_worktree_scope.py`.

   **Standing lesson — a hook verification matrix is only valid for the execution context it
   ran in.** Re-verify every guard whenever a new context is introduced: a worktree, a
   container, an alternate runtime. Compare **R16** (a harness where `.*`-matcher hooks never
   fire) and **R17** (a runtime where the controls are inert) — all three are the same family,
   *the control exists and is not applying in this execution context*.
2. **GitHub branch protection on `main`** (the real merge/deploy backstop — server-side,
   unbypassable from a session): require PR + `full-check` green + CODEOWNERS approval; no
   direct pushes; arbi's identity cannot self-approve. **✅ CONFIGURED — recorded 2026-08-12,
   live since 2026-07-17** (supersedes this layer's earlier "*Config step for
   James/backend-architect*" note). Two rulesets — `asxos-main` (id 19077432) and `main`
   (id 18221894) — enforce PR-required, `full-check` required, deletion blocked and
   non-fast-forward blocked; classic protection was re-asserted 2026-08-12 with the same
   shape and `required_approving_review_count: 0`. **Two caveats keep this layer honest:**
   `enforce_admins: false`, so a token acting as a repo admin bypasses all of it (it binds
   agents and non-admin credentials, not James); and at 0 required approvals the
   "CODEOWNERS approval" clause above is the *target* shape, not today's enforcement —
   `.github/CODEOWNERS` is **advisory**. A 1-approval setting was tried and reverted
   2026-08-12: on a solo repo GitHub forbids self-approval, so requiring one turned every
   merge into an `enforce_admins:false` admin bypass — weaker audit evidence for zero added
   enforcement. Making it mechanical needs a review identity that is not the PR author (a
   second account or a GitHub App) — a governor decision, not a settings tweak. Verify
   before relying on it: `gh api repos/Jp8617465-sys/asxos/branches/main/protection`.
3. **R2 read-only Postgres role** for agent MCP sessions (`m14_candidate_agent_db_role_scoping`):
   the real DB-write backstop. *Migration drafted as `migrations/0039_agent_readonly_role.sql`
   (2026-07-15, NOT applied) — apply + re-point `supabase-ro` are James's steps; the guard is
   the interim.*

The hook reduces risk **R5** (prompt-only enforcement) from total to partial; (2) and (3)
are what actually bound the irreversible tiers. **Updated 2026-08-12: (2) has landed** — with
the `enforce_admins`/CODEOWNERS caveats above — leaving (3) as the one outstanding mechanical
backstop. See `arbi-permission-model.md §Runtime enforcement honesty` — the infra **I5–I6**
and portfolio **P5–P6** tiers stay treated-as-disabled until (3) lands as well (P6 execution
is already enforced by no execution tool being mounted).

## Activation — NOT on by default

Standing unattended autonomy (the loop writing/dispatching on a schedule) is **PR 7b/8**,
gated. Turn it on only when ALL hold:

1. ✅ **MET 2026-07-11 — Model A dispute resolved** *against* Model A (no usable edge on
   19,032 matured signals, `docs/model-a-decay-analysis-2026-07-11.md`); James **shelved the
   ML engine** (`ml-engine-shelf-2026-07-11.md`). Rule #11 now **stands as policy** (not
   lifted) — the loop must never act on Model A for capital regardless.
2. ✅ **MET 2026-08-12 — branch protection** configured on `main` (layer 2 above): PR
   required, `full-check` required, deletion and non-fast-forward blocked; rulesets live
   since 2026-07-17, classic protection re-asserted 2026-08-12. What the tick does **not**
   claim: `enforce_admins: false` and CODEOWNERS-advisory-at-0-approvals mean this is met as
   a *server-side merge backstop*, not as a mechanical grader≠producer gate.
3. **R2 read-only DB role** landed (layer 3 above).
4. **Track record** — several attended cycles logged in the run-ledger with clean scorecards.
5. **James's explicit enable.**

Preconditions 3, 4 and 5 remain open, so standing activation is still **off**.

Until then: **run it attended** — you invoke `/arbi` → `/arbi-run` → review → PR, exactly
as this session did (the loop's inner cycle, run by hand). That already works today.

**The step-by-step path from here to the flip — including who owns each precondition, the
one-action activation procedure, and every kill switch — is
`arbi-full-auto-activation-2026-07-15.md`.**

## Attended GitHub Actions harness

`claude-execute.yml` is the GitHub Actions form of the attended loop. It is manually
dispatched, branch-and-draft-PR bounded, and does not make the scheduled 7b loop live. Inside
the task prompt James gives it, Claude may build, test, commit, push a `claude/**` branch,
open/update a draft PR, inspect validation results, and continue through recoverable failures
until the scoped work is done or an approval gate is reached.

The approval gates are unchanged: credentials/secrets, destructive DB operations, production
data mutation, production deploys or irreversible writes, direct `main` pushes, PR
ready/merge or self-merge without the existing James-instructed policy path, migration
`0042`, Model A decision use, and capital execution all stop for James.

## The Routine (7a live; 7b ready to enable — do NOT enable before the gate)

A daily/weekly Claude Code Routine (`create_trigger`) firing a fresh session whose prompt:
sets the loop, runs `/arbi` → (if a clear reversible #1) `/arbi-run` → implement on a branch
→ test → review → open a **draft** PR → report; **never merges**. The session env carries
`ARBI_UNATTENDED=1` so the guard is armed. Cadence suggestion: a **weekly `/arbi-dream`**
first (lowest-risk write — candidate on a branch), then a daily build-loop once the gate
clears.

PR 7a (the read-only morning brief) is live as Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`
(**re-wired 2026-07-15**, daily 20:30 UTC = 06:30 AEST, fresh session, push+email).
**History lesson:** the original 2026-07-10 Routine (`trig_01PiLVYg…`) was found **absent
from the live trigger list** on 2026-07-15 while this doc still claimed it live — the brief
had silently stopped. A Routine is live state, not doc state: verify with `list_triggers`
before repeating the claim.

## Cost

Runs under this environment's Claude Code plan — **no separate API bill** (unlike Managed
Agents' metered usage). Cost is model tokens per cycle: a brief is cents; a full build-loop
cycle with fan-out is more. Cap cadence to control spend.
