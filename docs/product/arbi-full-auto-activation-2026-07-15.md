# arbi full-auto activation — runbook (2026-07-15)

**Status:** current **as a runbook**, but **two of its blockers are STALE — see the
correction box below before following any step.**
**Scope:** the exact remaining distance between today's attended loop and standing
unattended autonomy (PR 7b), what was activated 2026-07-15, who owns each remaining step,
and the one-action flip + kill switches.
**Last verified:** 2026-07-15 (live `list_triggers` probe + repo state)
**Docs-truth correction:** 2026-08-13 (`SB0-01` sweep — §3.2 and §3.3 corrected against
repository evidence; **no gate lifted, no precondition marked met that was not already met by
an independent record**)
**Owner:** James (governor — every gate below clears only on his action or explicit enable)
**Superseded by:** N/A

> ### ⚠️ STALE-BLOCKER CORRECTION — 2026-08-13 (SB0-01 doc-truth sweep)
>
> This runbook is the document James would follow to turn on standing autonomy. Two of its
> blockers were overtaken by events within days of it being written and were never corrected,
> so following it as written would send him to **buy a GitHub plan he already has** and
> **apply a migration that is already applied**.
>
> | § | What this doc says | What actually happened | Evidence |
> |---|---|---|---|
> | 3.2 | `0039` "NOT applied. Apply is James's (step 3.2)" | **Applied 2026-07-16** (James-instructed, via Supabase MCP; observed count 93). The step that remains is **3.2 step 4** — re-pointing the `supabase-ro` MCP connection at the role | `session-handoff-2026-07-17.md:43`; `roadmap-state.md:959`; `risk-register.md` R16 |
> | 3.3 | Branch protection "BLOCKED on the GitHub plan… **cannot be configured**" | **GitHub Pro was activated and branch protection went LIVE on `main` 2026-07-17.** Rulesets `asxos-main` (19077432) + `main` (18221894); re-asserted as classic protection 2026-08-12 | `session-handoff-2026-07-17.md:16`; `arbi-autonomy-loop.md:45-61`; `roadmap-state.md:694-696` |
>
> **Net effect on the gate: precondition 3.3 is MET; 3.2 is partially met (migration applied,
> re-point outstanding).** Preconditions 3.4 (track record) and 3.5 (James's explicit enable)
> are untouched by this correction and remain open, so **standing activation is still OFF.**
> This box corrects facts; it does not and cannot flip a gate.

---

James's directive (2026-07-15): *"make the full auto loop a reality."* This runbook is that
directive turned into a checklist. It does not change any gate — the 7b preconditions in
`arbi-permission-model.md` / `arbi-autonomy-loop.md §Activation` stand; this doc closes the
buildable distance to them and stages the flip so activation is deliberate and one action.

---

## 1. What the "full auto loop" is (recap)

The cycle in `arbi-autonomy-loop.md`: a Routine fires a fresh session with
`ARBI_UNATTENDED=1` → `/arbi` (observe, decide THE ONE THING) → `/arbi-run`//`arbi-mission`
(reversible fan-out) → implement on a `claude/**` branch → test → review loop → **draft PR**
→ STOP (James merges = the human gate) → `/arbi-close` (ledger + memory). Weekly
`/arbi-dream`, monthly `/arbi-promote`. The loop never merges, never deploys, never touches
capital, never lifts rule #11 or the s766B firewall.

## 2. What was activated 2026-07-15 (this session)

| Item | State | Detail |
|---|---|---|
| **PR 7a daily read-only brief** | **LIVE** | Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`, cron `30 20 * * *` (06:30 AEST), fresh session per fire, push + email to James. First fire: 2026-07-15T20:30Z. |
| Docs↔reality reconciliation | done | The prior 7a Routine (`trig_01PiLVYg…`, "WIRED 2026-07-10") was **absent from the live trigger list** — the brief had silently stopped while `roadmap-state.md` and `arbi-autonomy-loop.md` still claimed it live. Both corrected to the new ID. |
| R2 read-only DB role migration | **drafted as a real file** | `migrations/0039_agent_readonly_role.sql` (renumbered from the design doc's 0038 — collides with `0038_screening_evaluator_wiring.sql`). NOT applied. Apply is James's (step 3.2). |
| Scorecard accrual wiring | **drafted** | `/arbi-close` now includes the scoring step (Step 2b) so every close appends an `episode_score` to the run-ledger — precondition (4) cannot accrue without this. |

Discovery credit: the dead-Routine finding came from this session's live-status audit
(subagent probe of `list_triggers`, re-verified by the main loop before acting).

## 3. The remaining gate — 7b preconditions, each with an owner

Per `arbi-autonomy-loop.md §Activation` (all five must hold):

### 3.1 ✅ Model A dispute resolved — MET 2026-07-11
Rule #11 is standing policy; the loop never acts on Model A for capital regardless of
autonomy tier. Nothing to do.

### 3.2 ❌ R2 read-only Postgres role — James (~15 min + password handling)
The real DB-write backstop. The migration is now a committed file
(`migrations/0039_agent_readonly_role.sql`); the design, pre-apply checks, acceptance test,
and rollback are in `docs/proposals/agent-db-readonly-role-design-2026-07-11.md`.
James's steps, in order:
1. Run the design doc's **pre-apply checks** (§ Pre-apply) via `mcp__supabase__execute_sql`.
2. Apply `0039` via `mcp__supabase__apply_migration`.
3. Set the role's password **out-of-band** (Supabase SQL editor / psql — never committed).
4. Re-point the `supabase-ro` MCP connection at the role via the Supavisor pooler
   (`asxos_agent_ro.gxjqezqndltaelmyctnl@…:6543`) — this is the step that makes the role
   load-bearing rather than defense-in-depth (design doc §2).
5. Run the design doc's **post-apply acceptance test** (SELECT works; INSERT/UPDATE/DDL fail).
6. Bump `REQUIRED_MIGRATIONS` in `asxos/api/main.py` to the observed migration count.

### 3.3 ❌ Branch protection on `main` — BLOCKED on the GitHub plan (James, 2026-07-16)
The real merge/deploy backstop; currently **not configured**, and — James confirmed
2026-07-16 — **cannot be configured on the current setup**: branch protection (and ruleset
*enforcement*) on **private** repos requires a paid GitHub plan; the account is Free and the
repo must stay private (personal financial system). Options, in order of preference:
1. **GitHub Pro (~US$4/mo)** — unlocks protected branches + CODEOWNERS enforcement on
   private repos. The only way to get the true server-side backstop. Recommended if/when
   standing write autonomy expands beyond the secperf loop (daily build loop, dreams).
2. **Accept as a documented residual** (current posture): merge/push-to-main protection is
   client-side only (`push-guard`/`pr-draft-guard`/`unattended-guard` + the draft-PR
   ceiling). Single-user blast radius; Render deploys from `main` are the exposure. The 7b
   "branch protection" precondition is then consciously waived by the governor, not met.
Until one of these, "arbi cannot self-approve its own constitution" has no server-side
enforcement and CODEOWNERS stays paper-only.

### 3.4 ❌ Track record — accrues from now (weeks, not an action)
`arbi-permission-model.md` precondition (3): scorecard trend + decision log + evals showing
arbi's calls hold up. Blocker found 2026-07-15: **nothing was producing scores** — every
run-ledger row's score column is `—` and the scorecard has never been computed. Fixed by
wiring Step 2b into `/arbi-close` (this PR). Suggested bar: **≥5 consecutive scored attended
cycles with no reversed calls** before James considers 3.5. Scores are provisional
self-scores; James spot-checks (grader ≠ producer applies to memory promotion; for the
track record the check is his review of the ledger).

### 3.5 ❌ James's explicit enable — the last word
Nothing flips without it. When 3.2–3.4 hold, the flip is §4.

## 4. The flip — one deliberate action when the gate clears

1. **Arm the guard mechanically:** add `ARBI_UNATTENDED=1` to the Claude Code environment's
   env config (environment settings, not a Routine prompt — the PreToolUse hook reads
   process env). This turns `unattended-guard.sh` from dormant to armed for every scheduled
   session in that environment. Note: the 7a brief Routine runs in the same environment and
   will also become guard-armed — a strict upgrade (its read-only promise stops being
   prompt-only; risk R5 closes from partial to structural).
2. **Create the 7b Routine** (start weekly, lowest-risk write first, per
   `arbi-autonomy-loop.md §The Routine`):
   - name: `arbi 7b — weekly dream (unattended, guard-armed)`
   - cron: `0 19 * * 6` (Sat 19:00 UTC — before the Sun crons; tunable)
   - fresh session; prompt: run `/arbi-dream` → dream-candidate **draft PR** only → report.
   - After ≥2 clean weekly cycles, add the daily build-loop Routine
     (`/arbi` → `/arbi-run` → draft PR → report; never merge).
3. **Record the enable** as a decision-log row (who/when/scope) and update
   `roadmap-state.md` PR-7b row to WIRED with the trigger ID.

## 5. Kill switches (any time, any tier)

| Target | Action |
|---|---|
| 7a daily brief | `delete_trigger trig_01BA3VmfzoRMtjKnt6XNpgPH` (or `update_trigger enabled=false`) |
| Any 7b Routine | same, with its trigger ID |
| All unattended write capability | remove `ARBI_UNATTENDED=1` from the environment config (guard disarms; but with 3.2+3.3 landed the server-side backstops still hold) |
| DB agent access | rotate/disable `asxos_agent_ro` password, or `ALTER ROLE asxos_agent_ro NOLOGIN` |
| Everything | GitHub branch protection + CODEOWNERS remain regardless — nothing lands on `main` without James |

## 6. Honest limits (unchanged by this runbook)

- `unattended-guard.sh` is a same-process pre-filter, not a boundary
  (`arbi-permission-model.md §Runtime enforcement honesty`). The boundaries are 3.2 (DB) and
  3.3 (merge/deploy). That is why they gate the flip.
- Until §4 step 1, the 7a brief's read-only promise stays prompt-enforced (risk R5, partial).
- The never-lifts list is untouched at every tier: s766B personal-advice firewall, rule #11
  (Model A quarantine, standing), irreversible tiers I5–I7 stay `always_ask`/disabled.
