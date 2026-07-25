# arbi operating backlog — ingested + debated (2026-07-11)

**Status:** legacy strategy-note inventory; not executable sequencing authority ·
**Source:** ChatGPT strategy note (James relayed 2026-07-11), debated against the
then-live repository state by Arbi.
**Owner:** arbi ranks + drives; James owns capital/merge/policy checkpoints.
**Superseded by:** `roadmap.yaml` for the accepted investment-engine programme.
Rows outside that scope are hypotheses to refresh and admit through the canonical
roadmap or a separately approved mission; their historical rank is not current
priority.

This preserves the original debate and provenance. It does not compete with the
twelve-week sprint order, reopen accepted decisions, or authorise work from a
stale status label.

---

## Already built — do NOT rebuild (arbi correction to the note)

| # | ChatGPT item | Reality |
|---|---|---|
| 4 | Portfolio Manager charter/schema | **DONE this session** — `portfolio-manager-charter.md`, `portfolio-policy.md`, `recommendation-schema.md`, `portfolio-outcome-ledger.md` + the **Portfolio ladder P0–P6** in `arbi-permission-model.md`. The recommendation schema already carries target/action/dollar_delta/rationale/evidence/tax_impact/risk_impact/confidence/do_not_execute_if/james_approval. The one field to fold in from the note: `current_weight`/`share_delta`/`invalidation` (minor schema add). |
| 6 (commands) | `/arbi-dream` + `/arbi-promote` | **DONE** as commands + the git-native memory (`memory/`, dream-candidates, promotion-log). Gap is the **cadence** (scheduling), not the commands — that's item R7 below. |
| 9 | Autonomy budget | **MOSTLY DONE** — `arbi-permission-model.md` (I5–I6 / P5–P6 never standing) + `.claude/hooks/unattended-guard.sh` mechanically blocks unattended: main-merge, DB writes, migrations, Render API mutations, secrets, capital. The note's "max one branch / stop after one PR-or-brief" per-run bounds are the incremental add (R8). |
| 2 (build) | Product Reality Sweep | The **playbook exists** (`memory/playbooks/product-reality-sweep.md`) with the 8 checks + scorecard target. It needs **running**, not building (R2). |

## The genuinely-new / in-flight work — ranked (arbi's order, not the note's)

| Rank | Item | Status | arbi note | Owner |
|---|---|---|---|---|
| **R1** | **Finish ETF Phase-1 Slice 2** — ingest VGS.AU+VAS.AU + passive mandates | **in-flight** (Slice 1 done + live: `security_kind` 0037, readers→au_equity, both fund auto-liquidation paths closed, writers fixed) | Don't task-switch off a live build that's 60% done and unblocks James's real portfolio. Slice 2 is small + additive. | main loop + `backend-architect` |
| **R2** | **Product Health Scorecard + Data Contracts** (built together) | **NEW — the biggest real gap** | Agree with the note's #1. But build it WITH `data-contracts.md`: the contracts (per-table purpose / required-freshness / min-rows / health-query / recovery) ARE the scorecard's data-freshness queries. `scripts/product_health.py` runs them read-only → `product-health-scorecard.md`. Today alone this would have flagged: `signal_outcomes` empty, `rba_cash_rate` null, market_context ingest 404s. | `backend-architect` + main loop |
| **R3** | **Run the Product Reality Sweep** (`/arbi-run`) | **NEW run** (playbook exists) | First real use of R2's instrumentation. Produces the ship/fix/quarantine/delete table. Make it the recurring weekly ritual once R2 lands. | arbi plans, main loop dispatches |
| **R4** | **arbi red-team agent** (`.claude/agents/arbi-red-team.md`) | **NEW — high value** | A shadow critic that challenges arbi's "one thing," checks for task-switching / recency-overfit / cleanup-mistaken-for-product / lower-trust-memory-overriding-truth. Concrete case: it would have flagged today's Render→ETF task-switch as a structured parallel-work decision. Keeps arbi honest as it gains power. | main loop |
| **R5** | **James Inbox** (`docs/product/james-inbox.md`) | **NEW — low-effort, high-clarity** | One place for James-ONLY decisions (capital, merge, migration, policy, conviction, execution). Reinforces the operating split. Would consolidate the currently-scattered asks (merge #24, HUBS conviction, ETF scope). | arbi maintains |
| **R6** | **Dark-launch exit plan** (`docs/product/dark-launch-exit-plan.md`) | **NEW — medium** | Every dark-launched surface (portfolio brief, news brief, V2 brief tree, paper-trade eval, pm-review) gets ship / delete / keep-dark-with-expiry. Prevents "built but off" = permanent fake progress. `roadmap-state.md` tracks gate status; this forces the decision. | arbi drafts, James decides |
| **R7** | **Ritual cadence** — Daily `/arbi`, `/arbi-close`, weekly `/arbi-dream`, `/arbi-promote` | **PARTIAL** (commands exist; no schedule) | Wire the scheduled read-only `/arbi` (PR 7a — allowed today) via a Routine; the write rituals stay attended until the promotion preconditions. Consistent per-run scoring (note #5) into run-ledger/decision-log. | main loop + James (schedule) |
| **R8** | **Cleanup-backlog → issues** + per-run scoring discipline | **PARTIAL** | `cleanup-backlog.md` has owners/tags/order; issue-ify it (owner/risk/scope/acceptance/files/reversibility/approval) so arbi picks work mechanically. Add the note's "max one branch / stop after one PR" unattended bounds to the permission model. | arbi |

## Sequencing debate (where I diverge from the note)

The note says "scorecard + reality sweep **before** ETF Phase-1 implementation." I **half-agree**:
- **Agree** the instrumentation (R2) is overdue and would have caught today's writer-breakage
  class earlier — it's the #1 *new* build.
- **Disagree** on pausing ETF: Slice 1 is already done + live in prod, and Slice 2 is small,
  additive, and the thing that makes ASXOS represent James's actual portfolio. Pausing a 60%-
  done live build to start a new one is the task-switch the red-team (R4) is meant to prevent.
- **Resolution:** finish ETF Slice 2 (R1, small), then build R2 (scorecard+contracts) as the
  next major workstream, then R3 (run the sweep) as its first use. R4–R8 slot after.

**One-line honest frame:** the note is right that arbi's next leap is *operating the project
daily + measuring product health*, not more governance theory — but ~1/3 of it is already
built, and the ETF build in flight should land before the instrumentation, not wait behind it.

---

# Second ChatGPT note (2026-07-12) — autonomy / permission architecture

**Source:** ChatGPT autonomy-and-permissions writeup (James relayed 2026-07-12), **debated
against live repo state** by arbi. James's framing: *"For backlog additional feedback from
chatgpt."* — i.e. capture-and-evaluate, not adopt.

**Calibration filter applied** (`competitive-gap-analysis-2026-07-11.md` calibration note, and
the standing "built ≠ right" lesson): a recommendation from an external tool is a **hypothesis to
check against asxos's actual governance docs**, not a work order. Some of the note cites Anthropic
docs accurately and maps cleanly onto what asxos already does; some proposes structure asxos has
already built under different names; and some is genuinely new and worth doing. Deduped below.

## The note's core diagnosis — AGREE

> "arbi is working. The bottleneck is no longer 'can arbi reason?' — it's permission friction +
> insufficiently-graduated autonomy tiers."

This matches lived experience this session: the repeated `mcp__supabase__execute_sql` /
`AskUserQuestion` / merge prompts that stalled work, and James's own *"I'm sick of allowing sqls
and the project stopping."* The `.claude/settings.json` allowlist (30 entries) covers **wake +
inspect** (read-only probes), not **work a reversible branch for hours**. That gap is real.

## Already exists — do NOT rebuild (arbi correction to the note)

| Note item | Reality |
|---|---|
| "Split permissions into three operating profiles (wake-readonly / reversible-work / irreversible-review)" | The **tiers already exist** conceptually — `arbi-permission-model.md` I0–I6 (infra) + P0–P6 (portfolio), where I5/I6 + P5/P6 are never standing. What does NOT exist is a **materialised `permissions.allow` profile for the reversible-work tier** — today's `settings.json` only encodes the wake-readonly slice. So the *profiles* are designed; only the reversible-work allowlist is unbuilt. That's the genuine gap, narrower than "split into three profiles." |
| "Add `unattended-guard` style hook" | **DONE** — `.claude/hooks/unattended-guard.sh` already arms under `ARBI_UNATTENDED=1` and blocks push/merge/deploy/main, DB writes/migrations, Render mutations, secret exposure, authority-file edits, write-capable MCP/Supabase/GitHub ops. The note's own analysis acknowledges this exists and is "directionally strong." No rebuild. |
| "Don't use `bypassPermissions` in this repo" | **Already the standing position** — the auto-mode classifier denied a `bypassPermissions` set earlier this session precisely because asxos has live Supabase/Render/secrets; arbi did not work around it. Agreement, not a new action. |
| "Use `/arbi-run` as a main-loop command (subagent can't spawn subagents)" | **DONE** — that's exactly why `/arbi-run` exists (`arbi-run.md` + the command). The note re-derives an existing design choice. |
| "Branch protection + CODEOWNERS is the real poisoning firewall" | **Partially DONE** — CODEOWNERS + the memory-path gating exist (PR #24). Branch protection on `main` is **NOT configured** — already surfaced as a risk in the PR #26/#27 I6 merge records. This is a real open item (see R-A2 below), not new information. |
| "Land the read-only DB role before unattended DB-aware autonomy" | **Design DONE, not applied** — `docs/proposals/agent-db-readonly-role-design-2026-07-11.md` + draft migration (unapplied). Already tracked as `m14_candidate_agent_db_role_scoping` / autonomy precondition (2). The note correctly ranks it high; it's already the named blocker. |

## Genuinely-new / worth-doing — ranked (arbi's order)

| Rank | Item | Status | arbi note | Owner |
|---|---|---|---|---|
| **R-A1** | **Materialise the reversible-work `permissions.allow` profile** — branch-safe git (`checkout -b claude/*`, `add`, `commit`, `push -u origin claude/*`), `ruff`/`mypy`/`pytest`, GitHub read + draft-PR update. Keep I5/I6/P5/P6 (merge, deploy, migration, DB write, Render mutation, secret, main push, authority-file edit) denied — enforced by the existing guard hook + the auto-mode classifier. | **NEW — the direct fix for the friction** | This is the smallest change that stops the "allow prompt grinding" during productive windows. Scope it as explicit allow rules, **never** `Bash(*)`. Must be reviewed against the guard hook so the deny set is not accidentally widened. | `backend-architect` → James (settings is a self-modification tier; James signs the allowlist) |
| **R-A2** | **Configure branch protection on `main`** (PR required, no direct/force push, `full-check` + `targeted-ml-tests` green required, CODEOWNERS review on authority/memory/policy paths). | **NEW — infra, James-owned** | PR #24 named branch protection as the *mechanical* poisoning firewall; without it arbi's self-improvement loop still has a prompt-level-only gap. Higher priority than broadening autonomy. Infra outside the repo — James configures in GitHub settings. | James (GitHub settings) |
| **R-A3** | **`/goal` recipes doc** — measurable end-state + proof command + must-not-change constraints + turn/time limit, for: reversible-work window, PR-hardening loop, product-health loop, review-comments loop. | **NEW — low-effort, high-leverage** | Directly addresses "it keeps asking me and work halts": `/goal` reduces per-turn prompts the way auto-mode reduces per-tool prompts. Cheap to write, reversible (docs). Verify `/goal` semantics against the live harness before committing recipes (the note cites Anthropic docs — check they match this environment). | arbi drafts |
| **R-A4** | **Skill-scoped `allowed-tools`** on arbi workflows (`arbi-run`, product-health, reversible-work-window) so pre-approval is scoped to the active workflow instead of globally widening `settings.json`. Use `disable-model-invocation: true` on side-effecting workflows (ship/merge/deploy/promote). | **NEW — medium; the cleaner alternative to R-A1** | This is arguably *better* than R-A1: it narrows the blast radius of any allow rule to only-while-the-skill-runs. Worth prototyping one skill (`reversible-work-window`) and comparing against the flat `settings.json` allowlist before choosing. **Verify** asxos's harness supports skill `allowed-tools` + `disable-model-invocation` as the note claims. | arbi + `backend-architect` |
| **R-A5** | **Auto-mode config in user/local settings** (NOT project settings — a repo can't grant itself auto-mode) with asxos-specific hard-deny (DB writes/migrations, Render mutations, merge, main push, secrets, authority/memory edits, capital) + `classifyAllShell: true`. | **NEW — do LAST, after R-A1/R-A2** | Auto-mode only after the mechanical gates (branch protection R-A2, read-only DB role) are real — otherwise the classifier is the *only* backstop. Lives in user/local config, so it's James's machine-level setup, not a repo artifact. | James (local/user settings) |

## Sequencing (arbi's call — this pass is capture-only, nothing built)

1. **R-A1** (reversible-work allowlist) is the immediate friction fix — but it's a `settings.json`
   self-modification, so it needs James's explicit sign-off on the exact rule list (same gate as
   the wake-readonly allowlist got earlier this session). Draft the diff, James approves.
2. **R-A2** (branch protection) + the **read-only DB role** (already designed) are the two
   *mechanical* gates that must exist **before** any standing/unattended write autonomy — both are
   James-owned infra, outside the repo. Higher priority than R-A5.
3. **R-A3** (`/goal` recipes) is cheap, reversible, and independently useful — can land anytime.
4. **R-A4** (skill `allowed-tools`) is the cleaner long-run shape; prototype one and compare.
5. **R-A5** (auto-mode) is last, gated on 2.

**Honest frame:** the note is a good, well-sourced articulation of the *right* direction
(pre-approve the boring reversible path; keep dangerous paths impossible or James-gated), and it
maps cleanly onto Anthropic's own guidance. But ~half of it is already built (guard hook, tier
design, `/arbi-run`, read-only-DB-role design, the anti-`bypassPermissions` stance), and the
genuinely-new work is narrower: **one reversible-work allowlist, branch protection, `/goal`
recipes, and a skill-scoped-tools prototype** — none of which is built in this pass. Every "verify
against the live harness" caveat above is load-bearing: the note cites Anthropic public docs, and
this environment's harness may differ — check before encoding any recipe or `allowed-tools` block.
Nothing here is adopted policy until James rules on R-A1's exact rule list.
