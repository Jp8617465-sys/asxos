# Proposal — automate the arbi dream protocol as a scheduled weekly Routine

**Status:** draft proposal (reversible artifact; no Routine created — switching on standing
unattended write authority is James's PR-7b enactment)
**Date:** 2026-07-15 · **Amended same day** — branch protection is unavailable on this plan;
see §Amendment, which supersedes every "branch protection" reference below
**Author:** arbi main loop, synthesizing a 4-agent fan-out (requirements-analyst,
backend-architect, security-engineer, arbi-red-team)
**Scope:** should `/arbi-dream` run on an unattended weekly schedule, and if so, how — the
mechanics, the controls, and the sequenced path to get there
**Decision owner:** James (governor)

---

## The question

Turn the `/arbi-dream` memory-consolidation protocol (today: manually invoked, produced its
first candidate `docs/product/memory/dream-candidates/2026-07-15-dream.md` on draft PR #46) into
a **scheduled weekly Routine** that runs unattended and opens a dream-candidate draft PR every
week.

A scheduled `/arbi-dream` *writes* (a candidate file + a branch + a draft PR). That crosses from
**PR 7a** (scheduled, read-only, output-only — already wired: daily brief Routine
`trig_01PiLVYg2GHAKpW8Xy43z5JN`) into **PR 7b** (standing scheduled autonomy that writes/acts
unattended), which `roadmap-state.md` marks blocked on preconditions. The crux is whether a
**docs-only, candidate-only, no-DB, no-merge** dream is a separable narrow slice we can justify
now, or whether it needs the full 7b unlock.

---

## What the team found (one line each)

| Agent | Question it answered | Verdict |
|---|---|---|
| **requirements-analyst** | Is it worth doing, and what are the requirements? | RUN is the designated first PR-7b step; gate on **branch protection only** — the DB-role & scorecard preconditions are *moot for this slice* |
| **security-engineer** | Is it safe? | **GO-WITH-CONTROLS** — branch protection is a *hard* prereq; DB-role moot **iff** the Routine surface is minimized (no DB mount, no secrets — verify, don't assume); 3 false-deny traps to close |
| **backend-architect** | Does it mechanically work? | Feasible, but 3 pieces the proposal assumes "just work" **don't exist yet** — `ARBI_UNATTENDED=1` env injection, a repo-scoped GitHub token, and a deadman ping — plus the GitHub MCP write path is **denied** unattended (must use `gh`) |
| **arbi-red-team** | Is now the right time? | **CHALLENGE** — no backlog to dream next week, candidate-PR spam against a single-reviewer gate with **0 promotions ever**, unattended is the wrong mode for a *synthesis* task, and "poke" ≥ "run" today |

**They agree on more than they disagree.** All four converge that: (a) the dream is the *safest
possible* unattended write and the explicitly-designated first PR-7b slice
(`arbi-autonomy-loop.md:77-79`); (b) **branch protection on `main` is the real gate** (not the
DB-role precondition); and (c) the **"poke" version is safe and permissible today**. The only
genuine dispute is *timing* — and the red-team's timing case (unproven gate + zero backlog) is
strong and unrebutted.

---

## Reconciliation → the recommendation

**Do not switch on the unattended weekly RUN yet — but not because it's unsafe.** It's the most
reversible write in the system. Hold because:

1. **The promotion gate has never been exercised.** `promotion-log.md` shows **zero** promotions
   (only the 2026-07-10 seed); PR #46 is still open. Automating candidate *generation* floods a
   valve that has never been opened once. You cannot automate into an unproven gate.
2. **There is no backlog.** The manual run consumed the entire window (its own dedup log:
   "nothing to archive-as-stale beyond the L6 supersede"). `arbi-dream-policy.md:43-50` sets the
   cadence at "the last ~10–50 sessions" — there will not be 10–50 sessions by next Sunday. A
   weekly cron would dream over near-empty input.
3. **The prerequisites everyone actually agrees on aren't in place** — branch protection on
   `main`, and a minimized-surface Routine with its own repo token + deadman.

**The sequenced path (this is the plan):**

### Phase 0 — prove the loop once, manually (this week)
Run `/arbi-promote` on PR #46 → the first real `promotion-log.md` row. This exercises the gate
end-to-end, produces the first data point for the track-record precondition, and confirms the
candidate→approved flow works mechanically. *Nothing about automation should precede one manual
promotion.*

### Phase 1 — ~~branch protection on `main`~~ SUPERSEDED (2026-07-15): unavailable on this plan
The original Phase 1 was: require PR + CODEOWNER review + `full-check` green; no direct pushes.
**James attempted it same-day and GitHub gates branch protection (and rulesets) to paid plans on
private repos** — verified against the docs: the REST API returns the same 403 as the UI, so
there is no API workaround, and rulesets are free on *public* repos only. James declined the
upgrade (a reasonable call — the alternative below is adequate for a single-user repo).
**Replacement: the two-step substitute in §Amendment** — a detective `main-push-guard` Action
now, and the fork/machine-identity model as the Phase-3 precondition. The honest consequence
stands regardless: `.github/CODEOWNERS` is **inert on this plan** — "arbi mechanically cannot
self-approve" is not achievable for free; promotion stays a disciplined-process gate (James is
the one clicking merge), not a mechanical one.

### Phase 2 — a cadence NOW without unattended write: the POKE Routine
A PR-7a-shaped weekly reminder (emit-only — **no** branch, PR, or write) that nudges James / an
attended session to run `/arbi-dream` **when there is material to consolidate**. Permissible
today (same tier as the wired 7a brief), zero new infra, zero unattended-write risk — and per
both the red-team and security-engineer it produces a *better* dream: an attended run has the
week's context and can adjudicate the contradictions a dream is required to surface for a human
(a fresh unattended session cannot). Recommend gating the poke on a **demand signal** ("≥N new
`working/*.md` notes since the last promotion"), not a naive calendar, so it only fires when
there's actually something to dream.

### Phase 3 — earn the unattended RUN (the designated first PR-7b step)
Enable only when Phases 0–1 are done, a promotion rhythm exists, and the control set below is in
place. At that point the RUN is the right end-state (requirements-analyst's case holds): the
dream *is* the nominated first unattended write, and a demand-driven weekly candidate is genuinely
useful once the gate has throughput.

---

## Routine requirements (the Phase-3 spec)

Drawn from requirements-analyst + backend-architect; every mechanism traced to a real file.

### Cadence & trigger
- **Cron:** `0 19 * * 0` — Sunday 19:00 UTC = Monday 05:00 AEST. After the week is committed
  (dream is *not* mid-work thinking), a day past the Saturday portfolio build, and 90 min clear
  of the 20:30 daily brief so two fresh sessions don't run concurrently. Lands the candidate for
  Monday-morning AEST review alongside the brief.
- **Shape:** `create_trigger(cron, create_new_session_on_fire=true, prompt=<self-contained>)` —
  modeled on the wired 7a Routine. Prompt pins: run `/arbi-dream`; **open the PR with
  `gh pr create --draft` over Bash, NOT the GitHub MCP** (denied unattended); run the idempotency
  check first; write only `dream-candidates/` + one ledger row on the branch; never
  merge/`main`/`approved-lessons.md`; final step = `curl` the deadman ping.

### Inputs & window (no human to set it)
- **Anchor = the window-end of the most recent PROMOTED dream** (read from `promotion-log.md`),
  not the most recent candidate — this is what makes un-promoted candidates supersede cleanly.
- Gather `working/*.md` dated `> anchor` + the always-cumulative ledgers, each captured **by
  commit SHA** for provenance (the `inputs:` shape in the 07-15 candidate).

### Candidate lifecycle across weeks (the gap the manual run didn't solve)
- **Supersede-by-content, never accumulate, never auto-close.** Because the window anchors on the
  last *promotion*, each weekly candidate re-consolidates everything since — an un-promoted prior
  candidate's lessons are automatically re-absorbed. The new candidate declares
  `supersedes: <prior>-dream.md` in frontmatter but does **not** touch the prior PR (a level-7
  dream can't adjudicate; closing a PR is a human/promotion act).
- **Backstop:** if ≥3 open un-promoted candidate PRs, still produce the candidate but flag
  prominently ("N candidates stacking — promote or reject"). Surface, don't auto-close.

### Success / partial / failure (tied to `completed:`)
- **Success (`completed:true`):** ≥1 durable lesson OR ≥1 contradiction/stale/repeated-mistake;
  file on the branch; draft PR opened; deadman pinged.
- **Nothing-to-consolidate week → no-op:** no candidate, no PR; emit a log/email line only. An
  empty `completed:true` file is noise.
- **Partial/failed → `completed:false` → archived, never promoted** (per policy). Do **not** ping
  success.

### Observability (net-new — Routines are not Render crons; no JobMonitor/Healthchecks for free)
- Provision a dedicated `HEALTHCHECK_URL_ARBI_DREAM`; final prompt step `curl`s it. Deadman: if
  the run never fires / crashes / fails before the ping, Healthchecks emails James — he doesn't
  go looking. Two distinct signals: a visible draft PR (ran) vs an emailed deadman alert
  (didn't).
- **Run-ledger row:** `arbi-run-ledger.md` lives on protected `main`; an unattended run can't push
  to `main`. Resolution: commit the ledger row **inside the draft PR** on the branch
  (`task_type: dream`, `trigger: scheduled`); it reaches `main` only when James merges. This is a
  **small extension** to `arbi-dream.md` (today the ledger row is `/arbi-close`'s job, and no
  close follows an unattended dream).

---

## Controls & prerequisites (the Phase-3 gate)

From security-engineer's minimum set + backend-architect's build list. **Every item is
achievable now (greenfield — no dream Routine exists yet); bake them into provisioning.**

| # | Control | Why | Status |
|---|---|---|---|
| 1 | **Minimize the Routine's tool/env surface** — no Supabase write MCP, no `DATABASE_URL`/service-role/`RENDER_API_KEY`/`RESEND_API_KEY`, no `pytest`/`make`/network-interpreter allow | Makes the DB-role precondition **moot by construction** (stronger than a read-only role), removes the executor-bypass of the merge/DB hooks, kills the secret-exposure surface | **to build** |
| 2 | **`ARBI_UNATTENDED=1` in the Routine's *launch* env** (verify `create_trigger` env support or the deployment env), + a startup assertion that refuses to run if unset | `unattended-guard.sh:32` arms on it; it **cannot** be self-armed from inside the session (a Bash `export` is a throwaway subshell). If unset, the guard is a **no-op** and the whole mechanical story collapses | **VERIFY — critical unknown** |
| 3 | **A dedicated asxos-repo GitHub write token** as a credential helper / `GH_TOKEN` (repo + PR-write scope), never inline on the command line (or `unattended-guard.sh` A3 secret-check denies it) | The GitHub MCP write path is denied unattended → the session must `git push` + `gh pr create --draft` itself. `BACKUP_GITHUB_TOKEN` is the wrong repo scope | **to build (new infra)** |
| 4 | **Author the candidate via the Write tool only** (never a Bash heredoc/redirect), fixed generic commit message, PR body via `--body-file` | L16-class false-deny: the candidate legitimately quotes `approved-lessons.md`/`CLAUDE.md`, so `authority-guard.sh`'s command-text scan denies it if authored via Bash; a secret-name in a commit msg trips `unattended-guard.sh` A3 | **pin in `arbi-dream.md`** |
| 5 | **`gh pr create --draft` for the PR; forbid the MCP PR tool fallback** | MCP `create_pull_request` is default-denied unattended; a silent fallback ends with a pushed branch and no PR | **pin in `arbi-dream.md`** |
| 6 | ~~Branch protection on `main`~~ **SUPERSEDED — plan-gated (see §Amendment).** Replacement: **fork/machine-identity model** (the bot has zero write on the canonical repo; cross-fork PRs only) + the detective `main-push-guard` Action in the interim | The fork model delivers the same *server-side* property (the automation physically cannot push to or merge `main`) via identity separation instead of the paid feature — arguably stronger. The detective Action converts any direct push into a same-minute alarm (detection, not prevention). **Fork model = hard prerequisite for Phase 3** | **Amendment — James** |
| 7 | **A subprocess regression test** pinning the guard boundary: under `ARBI_UNATTENDED=1`, Write to `dream-candidates/*` allowed, Write to `approved-lessons.md` denied, `merge_pull_request` denied | So a future guard edit can't silently break the boundary either way (mirrors `test_review_gate_hook.py`) | **to build** |

### The DB-role finding (worth recording on its own)
The roadmap lists "agent DB read-only role (`m14_candidate_agent_db_role_scoping`)" as PR-7b
precondition (2). **For this path it is moot** — `/arbi-dream` reads only git files and never
issues a query. The correct control is #1 ("no DB mount"), which is strictly stronger and
available today. **The dream does not have to wait on the DB-role work.** (Both
requirements-analyst and security-engineer land here independently; the red-team's counter — "the
roadmap names it as a blanket 7b gate" — is a reason to *re-scope the precondition explicitly for
this slice*, not to block on DB work that has no surface here.)

---

## Memory-poisoning / trust (security-engineer)

Bounded and acceptable. The dream's inputs are **arbi-authored committed docs**, not external
untrusted text — the classic injection vector (RSS-fed `regulatory_events` next to a governed
table) is **absent**; the dream touches no DB. A poisoned/wrong working note produces at worst a
level-7 *candidate* that never reaches authority without James's CODEOWNER promotion merge. Two
sub-boundary residuals (neither reaches authority): promotion-review **fatigue** (a weekly stream
pressures the single human gate — this is exactly the "launder yesterday's mistakes" risk the
policy warns of, and the strongest argument for demand-gating the cadence), and advisory-L7
context bias while a candidate PR sits open. Mitigated by the demand-gate + the ≥3-open backstop +
the promotion rubric's evidence-diff step.

---

## Explicitly NOT in this proposal
- **No live Routine is created.** Standing unattended write authority is James's PR-7b enactment.
- **No auto-promotion / no write to `main` or `approved-lessons.md`** — that stays `/arbi-promote`,
  James-merged only.
- **No auto-close/merge of candidate PRs.**
- **No DB, Render, capital, or Model A-derived output** — permanently barred (rule #11, s766B).

## Open decisions for James
1. **Phase 0 now:** promote PR #46 to exercise the gate? (Recommended — prerequisite to everything.)
2. **~~Phase 1: branch protection~~ RESOLVED 2026-07-15: unavailable on this plan (James declined
   the upgrade).** Replacement decisions: (a) add the `main-push-guard` detective Action —
   **arbi's Write to `.github/workflows/` was permission-denied this session** (correct: workflow
   files control CI execution), so the ready-to-apply YAML is embedded in §Amendment for James to
   add; (b) adopt the fork/machine-identity model at Phase 3.
3. **Phase 2:** want the **poke** Routine armed now (demand-gated), or hold until there's a real
   cadence of work to consolidate?
4. **Re-scope precondition (2):** record that the DB-role precondition is moot for the dream slice
   (replaced by "no DB mount")? A one-line amendment to `arbi-permission-model.md` — arbi drafts,
   James approves.

---

## Amendment (2026-07-15, same day) — branch protection is plan-gated; the substitute

**Finding.** James attempted to enable branch protection and hit GitHub's plan gate: on a
**free-plan private repo**, branch protection and rulesets are paid features (rulesets are free
on public repos only), and the REST API enforces the same entitlement — `PUT
/repos/.../branches/main/protection` returns 403, so **there is no API workaround**. The only
paths to the server-side feature are upgrading (~US$4/mo GitHub Pro — James declined) or making
the repo public (hard no: it holds portfolio/financial data). Sources: GitHub REST branch-
protection docs; "About rulesets" plan matrix; community discussions #174400/#190190.

**What this does and does not change.**
- **Phase 0 (promote #46) and Phase 2 (poke Routine): unaffected.** Neither needs protection.
- **CODEOWNERS is inert on this plan** — mechanical "grader ≠ producer" via required CODEOWNER
  review is not achievable for free. Promotion remains a disciplined-process gate (James clicks
  merge), which is acceptable single-user but must be stated honestly, not implied away.
- **Phase 3 (unattended RUN):** the control-set requirement — a *server-side* backstop the
  client-side hooks can't provide — stands, but is now satisfied by **identity separation**
  instead of the paid feature.

**The two-step substitute:**

1. **Now — a detective Action (`main-push-guard`).** Cannot BLOCK a direct push (that is the
   paid feature) but converts one into a same-minute alarm: on every push to `main`, check via
   the API whether the commit is associated with a merged PR; if not, fail the run and auto-open
   an alert issue. Honest limits: detection not prevention; it alarms on James's own deliberate
   direct pushes too (close the issue with a note — that closure is the audit trail); an actor
   with write could delete the workflow (its integrity is visibility, not a boundary).
   **arbi could not write this file** — `.github/workflows/` is permission-denied in-session
   (stopped per the lockout lesson rather than routing around via Bash) — so the ready-to-apply
   YAML is below; James adds it at `.github/workflows/main-push-guard.yml`.

2. **At Phase 3 — the fork / machine-identity model** (replaces branch protection in control #6).
   Create a **machine account** (GitHub ToS explicitly permits one machine account alongside a
   personal account for automation — verify current wording before creating); it gets **zero
   write access to `Jp8617465-sys/asxos`** and works in its own **fork**: pushes `claude/**`
   branches there, opens cross-fork PRs into the canonical repo. Only James's account can merge
   or push anything — the automation identity has no write bit at all. This is *stronger* than
   branch protection in one respect (it removes the writer from the repo rather than restricting
   one branch) and it genuinely delivers grader ≠ producer: PR author (bot) and merger (James)
   are different identities, mechanically. Setup cost (second account, fork remote, bot
   `GH_TOKEN`) is paid only if/when Phase 3 is earned — and that bot token is the *same*
   dedicated credential control #3 already requires, so the two efforts converge.

**Ready-to-apply workflow** (James: save as `.github/workflows/main-push-guard.yml` — the full
header comment explaining why/limits is included):

```yaml
# main-push-guard — detective control for direct pushes to main
#
# WHY: GitHub gates branch protection (and rulesets) to paid plans on private
# repos (verified 2026-07-15; the API returns the same 403 as the UI). This is
# the free-plan SUBSTITUTE: it cannot BLOCK a direct push, but it converts one
# into a loud, same-minute alarm — a failed run plus an auto-opened issue —
# instead of a silent boundary violation (the failure mode the 2026-07-11
# PR #26 merge demonstrated: "no required-review block").
#
# HOW: on every push to main, ask the API whether the pushed commit is
# associated with a MERGED pull request (true for merge/squash/rebase merges).
# No associated merged PR => direct push => fail + open an alert issue.
#
# HONEST LIMITS:
# - Detection, not prevention. The push has already landed when this runs.
# - It alarms on James's OWN direct pushes too (by design — the convention is
#   "everything reaches main via a PR"). Deliberate direct push? Close the
#   alert issue with a note; that closure is the audit trail.
# - An actor with write could delete this file. Its integrity is convention +
#   visibility (the deletion is itself a diff), not a boundary.
#
# See docs/proposals/arbi-dream-automation-2026-07-15.md (§Amendment).

name: main-push-guard

on:
  push:
    branches: [main]

permissions:
  contents: read
  pull-requests: read
  issues: write

jobs:
  verify-merged-via-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Verify the pushed commit landed via a merged PR
        env:
          GH_TOKEN: ${{ github.token }}
          SHA: ${{ github.sha }}
          REPO: ${{ github.repository }}
          ACTOR: ${{ github.actor }}
        run: |
          set -euo pipefail
          # Commits that landed through a PR (merge, squash, or rebase) are
          # associated with >=1 pull request whose merged_at is set.
          merged_prs=$(gh api "repos/$REPO/commits/$SHA/pulls" \
            --jq '[.[] | select(.merged_at != null)] | length')
          if [ "$merged_prs" -ge 1 ]; then
            echo "OK: $SHA reached main via a merged PR."
            exit 0
          fi
          echo "::error::Direct push to main detected: $SHA by $ACTOR (no associated merged PR)."
          # Open the alarm issue (best-effort — the failed run is the primary signal).
          gh issue create \
            --repo "$REPO" \
            --title "ALERT: direct push to main ($SHA)" \
            --body "A commit reached \`main\` without a merged PR.

          - **Commit:** $SHA
          - **Actor:** $ACTOR
          - **Detected by:** main-push-guard (detective control — see the workflow header for why this is detection, not prevention)

          If this was a deliberate direct push by James, close this issue with a one-line note (that closure is the audit trail). Otherwise investigate, and if unexpected, revert via a PR." \
            || echo "::warning::Could not open the alert issue; the failed run is the alarm."
          exit 1
```

**Also skipped (recorded for completeness):** fine-grained PATs / deploy keys (cannot scope to a
branch); pre-receive hooks (not on github.com); migrating to GitLab for its free protected
branches (disproportionate — the whole governance stack is GitHub-native).
