# arbi operating backlog — ingested + debated (2026-07-11)

**Status:** current · arbi-owned ranked backlog · **Source:** ChatGPT strategy note (James
relayed 2026-07-11), **debated against live repo state** by arbi.
**Owner:** arbi ranks + drives; James owns capital/merge/policy checkpoints.
**Superseded by:** N/A

The debate matters more than the list. ChatGPT's 12 items are strong, but **4 already exist**
(built this session) — capturing them as "create" would be exactly the fake-progress arbi is
supposed to catch. Deduped against ground truth, the genuinely-new high-value work is narrower.

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
