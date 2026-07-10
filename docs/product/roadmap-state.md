# asxos Roadmap & State — the reconciled picture

**Status:** current (living document — refreshed every `/arbi` and `/arbi-close`)
**Scope:** whole repo — the single reconciliation of every roadmap + the live state
**Last verified:** 2026-07-10 (seeded from docs; **live snapshot not yet established** —
the first `/arbi` run fills it)
**Owner:** arbi (`.claude/agents/arbi.md`) reads and refreshes this; humans may edit freely
**Superseded by:** N/A

---

## State header — arbi's durable memory (read this first)

The at-a-glance fields `/arbi` reads and `/arbi-close` refreshes. Everything below is the
detail behind these lines.

- **Current status:** M1–M14a built (M13/M14a **dark-launched**); governance through
  Phase 2b; the V2 thesis product and Phase 2c are **blocked** on the P0 Model A dispute.
  The arbi program-management layer landed 2026-07-10.
- **Top blocker:** **P0 — Model A signal reliability in dispute** (CLAUDE.md rule #11
  quarantine). Blocks Phase 2c and all real-capital deployment.
- **Current workstream:** the arbi PM layer (this change). Next substantive workstream:
  the Model A decay check.
- **Open PRs:** _run `/arbi` to populate from live GitHub; none tracked at seeding beyond
  this branch (`claude/asxos-product-manager-agent-tzszlv`)._
- **Recently completed:** governance Phase 0.5–2b (PR #11); `ingest_market_context` fixes
  (#12/#13); 12 Render crons provisioned; first `/discover-macro` cycle. (handoff §Session
  summary)
- **Blocked items:** Phase 2c (`theme-researcher`, `instrument-selector`); V2 thesis
  product; real-capital deployment — all downstream of P0.
- **Next actions:** see the ranked queue below. #1 = Model A decay check.
- **Decisions needed from James:** the ChatGPT Model A audit; HUBS lock-window end date;
  HUBS acquisition FX rate (0.6450 est. vs vendor 0.7171 — sign-flips AUD P&L); approve or
  reject `agent_runs` #3 & #4; Healthchecks.io API key for the 12 new crons. (handoff
  §Pending)
- **Known risks:** (1) Model A horizon mismatch — the foundation risk; (2)
  `m14_candidate_agent_db_role_scoping` — agent SELECT-only is prompt-enforced only;
  (3) v1 allocator risk-blindness to ASX beta clustering (`m14_candidate_beta_cap`);
  (4) built-but-dark-launched layers are unreleased, not done.
- **Last verified:** 2026-07-10 (state as of the 2026-07-04 handoff; live snapshot pending
  the first `/arbi`).

---

Why this file exists: asxos has **three roadmaps and two milestone schemes that
partially contradict each other** (BUILD_GUIDE M1–M12; the V2 `M-Thesis-*` sequence;
governance Phase 0–4; plus `M13`/`M14a` in the strategy audit and `PR1–8` in the
executable roadmap). Nothing reconciled them into one "where are we." This file is that
reconciliation. It does **not** replace the source docs — it cross-walks them and cites
each. On any conflict, the newest `session-handoff-*.md` wins on priority (per
`docs/README.md`), the source doc wins on detail.

State claims below are **as of the 2026-07-04 handoff** unless a `/arbi` run has since
refreshed the *Last wake snapshot* at the bottom. Treat pre-first-wake numbers as
doc-derived, not live-probed.

---

## Reconciled position — one cross-walk

| Scheme | Where it lives | Status today | Source |
|---|---|---|---|
| Rebuild M1–M12 | `docs/foundation/BUILD_GUIDE.md` | **All done.** Static manual, not a tracker. | `/sprint-plan` ("M1–M12 should all be done") |
| Portfolio M13 | `asxos/domain/portfolio/*` | **Built, dark-launched** (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`). Weekly Sat 20:00 UTC. | V2 arch audit Part A |
| News/sentiment M14a/M14b | `asxos/ingestion/{news,sentiment}.py` | **Built, dark-launched** (`ASXOS_NEWS_BRIEF_ENABLED=0`). | V2 arch audit Part A |
| Governance Phase 0 / 0.5 | model-filtering + `approved_for_allocation` gate | **Done** (PR #11). | `next-session-backlog.md` P0 |
| Governance Phase 1 | governance schema + first Postgres trigger | **Done** (PR #11). | `next-session-backlog.md` P0 |
| Governance Phase 2a+2b | `macro_theses`, per-table audit triggers, `macro-economist`, `/discover-macro` | **Done** (PR #11). First live `/discover-macro` cycle run 2026-07-04. | handoff §Session summary |
| Governance Phase 2c | `theme-researcher` + `instrument-selector` | **Not started — BLOCKED** on Model A + agent DB role scoping. | handoff §5 |
| Governance Phase 3 | executable thesis invalidation | **Not started.** | `next-session-backlog.md` |
| Governance Phase 4 | `/pm-review` 5→7 agents | **Not started.** | `next-session-backlog.md` |
| V2 product `M-Thesis-*` | `V2_..._BRIEF_SPEC.md` Part 8 | **Blocked** at the foundation — the thesis layer rests on a signal engine under dispute. | V2 spec Part 8 |
| Executable roadmap PR1–8 | `executable-roadmap-2026-07-04.md` §D | PR1 (docs cleanup) partly landed; **PR2 (agent DB read-only scoping) is the near-term unblocker**; PR5 = the Model A audit job. | executable-roadmap §D |

**One-line reconciled read (corrected 2026-07-10, scan `wf_f54323f5-d7d`):** *M1–M14a are
built (M13/M14a dark-launched); governance is through Phase 2b. The Model A dispute gates
only the signal-driven **allocator** path (`PortfolioService.build` → `allocator.py`) + the
peripheral opportunity-cost ranking — NOT the thesis/discipline scaffolding, tax engine,
theme stewardship, or governance, which are **authoritative and shippable today**. The
cleanest forward move is the Model A decay check (measuring, not deploying), then agent DB
role scoping — not another layer on top.*

---

## Blocked — P0 first (read `docs/session-handoff-2026-07-04.md`)

- **P0 — Model A signal reliability is in dispute, unresolved.** James: signals *"greatly
  diminish after 5 days and completely swing around at 21 days."* If true, it's a
  **horizon mismatch at the core of the product** (theses hold for months; HUBS has a
  365-day timeline). Model A is the *only* model and gates every signal/allocator/scan.
  CLAUDE.md rule #11 quarantines it from real-capital decisions until resolved. **This
  blocks Phase 2c and all non-paper deployment.**
- **Blocked-by-P0 (narrow, corrected 2026-07-10):** the signal-driven **allocator** capital
  path + the peripheral `compute_opportunity_cost` ranking; governance Phase 2c (needs a
  trusted signal engine); real *signal-driven* capital deployment. **NOT blocked:** the
  thesis/discipline scaffolding, tax engine, theme stewardship, governance, and the brief's
  non-signal sections — all authoritative today (scan `wf_f54323f5-d7d`, verdict supported).
- **Second-order unblocker:** agent DB role scoping (`m14_candidate_agent_db_role_scoping`
  / PR2) — a prerequisite the roadmap places *before* Phase 2c regardless of Model A.

## In flight

- Nothing committed in-flight as of seeding. (The first `/arbi` fills this from live
  git/PR/`TaskList` state.)

## Ranked next-action queue

Each action names its north-star tie, the roadmap item it advances, and the owning
agent/command. arbi keeps this ranked; it is brief-only and does not execute these.

1. **Get the ChatGPT audit from James, then run the Model A decay check.** North-star:
   the success criterion that a signal's edge persists over the held horizon. Method
   (from handoff §2): Spearman rank correlation of `prob_up`/`expected_return`/
   `signal_label` at day 0 vs +5 vs +21 for symbols with signals ≥5 and ≥21 days apart;
   say plainly if the 15-date sample is too thin. Owner: main loop + `system-architect`/
   `backend-architect` if the claim holds. **This is THE one thing.**
2. **Agent DB read-only role scoping (PR2 / `m14_candidate_agent_db_role_scoping`).**
   North-star: non-negotiable #2 (firewall integrity) before more agents sit next to
   governed tables. Owner: `backend-architect`. Prereq for Phase 2c.
3. **Resolve the two open governance proposals** — review/approve or reject `agent_runs`
   #3 and #4 (`asx macro-thesis open --from-agent-run` → `approve`). Owner: James +
   main loop. (Does not expire.)
4. **HUBS data hygiene** — lock-window end date → `theses.tax_notes`; verify the
   `acquisition_fx_rate=0.6450` vs vendor `0.7171` sign-flip against the brokerage
   statement. Owner: James supplies, main loop records.

## Deferred index — `m14_candidate_*` (aggregated; grep to refresh)

Never aggregated before this file. Refresh with `grep -rn m14_candidate_ .`.

| Slug | What it defers | Cited in |
|---|---|---|
| `m14_candidate_agent_db_role_scoping` | Read-only Postgres role for agent MCP sessions (the only *security* deferral) | `portfolio-conventions.md`, `next-session-backlog.md:256` |
| `m14_candidate_agentic_thesis_drafter` | No `ThesisProposal` schema yet — agent-drafted theses can't be created end-to-end | `theses/schemas.py:21`, `theses/service.py` |
| `m14_candidate_macro_thesis_evidence_staleness_check` | `macro_theses.approve_object()` skips the evidence-staleness check theses have | `macro_theses/service.py:8,209` |
| `m14_candidate_governance_aware_revisit_cadence` | `approve_object()` doesn't reset revisit cadence on approval | `portfolio-conventions.md:84` |
| `m14_candidate_conviction_weighted_cadence` | Conviction-weighted revisit cadence not built | `governance-first-architecture-2026-06-30.md:310` |
| `m14_candidate_beta_cap` | Market-beta cap (v1 allocator is risk-blind to ASX beta clustering) | `portfolio-conventions.md:204` |
| `m14_candidate_security_kind_enum` | `security_kind` enum to disambiguate overloaded `universe.is_active` | `portfolio-conventions.md:208,222` |

## Dark-launch gate status (the hidden release state)

"Built but off." A layer being code-complete is not the same as released.

| Gate | Guards | State |
|---|---|---|
| `ASXOS_PORTFOLIO_BRIEF_ENABLED` | M13 portfolio brief section | `0` — off until 4-week paper-trade sign-off (M13.8) |
| `ASXOS_NEWS_BRIEF_ENABLED` | M14a/b news+sentiment brief section | `0` — off |
| `ASXOS_PERSONAL_USE` | s766B personal-advice firewall — gate 1 for any portfolio/brief surface (CLI `_require_personal_use()`) | must be `1`; the portfolio brief needs this **and** `ASXOS_PORTFOLIO_BRIEF_ENABLED` (`portfolio-conventions.md` §Regulatory firewall) |
| `ASXOS_V2_BRIEF_ENABLED` (proposed) | future single master gate for V2 brief sections | not yet plumbed |

---

## Decision log & outcomes (arbi's memory)

Moved to its own canonical file: **`decision-log.md`** (append-only; the run audit trail is
`arbi-run-ledger.md`; standing risks are `risk-register.md`). arbi reads the decision log
first each wake and checks whether its last call held up. It was split out of this file so it
can grow without bloating the reconciled-state view and so the promotion gate + run ledger
reference one canonical decision history.

## Autonomy roadmap — the ASXOS Autonomy Kernel (10-PR sequence)

How arbi grows from a brief into the bounded autonomous operating layer. Governance +
memory/dream policy land **before** scheduled autonomy — without them, scheduled autonomy
just repeats mistakes faster. Each PR is a deliberate, separate change.

| PR | What | Status |
|---|---|---|
| 1 | Constitution + authority hierarchy (`arbi-constitution.md`, `arbi-authority.md`, `arbi-permission-model.md`) | **done (2026-07-10)** |
| 2 | Scorecard + eval rubrics (`arbi-scorecard.md`, `rubrics/`, `arbi-evals.md`) | **done (2026-07-10)** |
| 3 | Read-only `/arbi` | **done** |
| 4 | Docs-write `/arbi-close` | **done** |
| 5 | Memory policy + run ledger (`arbi-memory-policy.md`, `arbi-run-ledger.md`, `decision-log.md`) | **done (docs)** |
| 6 | Dream policy + promotion gate (`arbi-dream-policy.md`, `arbi-promotion-gate.md`) | **done (docs)** |
| **7a** | Scheduled **read-only dry-run** brief (Routine fires `/arbi`; **output only**) | **WIRED 2026-07-10** — daily 20:30 UTC (06:30 AEST), fresh session, push+email to James; Routine `trig_01PiLVYg2GHAKpW8Xy43z5JN` |
| **7b** | **Standing** scheduled autonomy (arbi writes/acts unattended on a schedule) | **blocked** on the 3 preconditions below |
| 8 | Multi-agent delegation (arbi coordinates specialists) | **attended bridge `/arbi-run` shipped 2026-07-10** (governor-invoked, reversible: arbi plans → main loop fans out named specialists); *standing/unattended* dispatch still gated on preconditions + runtime |
| 9 | GitHub operator mode (docs-only draft PRs) | not started |
| 10 | Live read-only watchdog (reacts to CI/PR/data events) | not started |

PRs 1–6 are the **governance + learning foundation**, complete as docs (the runtime they map
onto — Managed Agents memory/dreams/outcomes — is not provisioned here).

**PR 7a is the one autonomous-execution step that is safe *before* the preconditions:** a
scheduled `/arbi` that runs **read-only**. It runs the observe → diff → synthesize → present
steps and emits a **draft brief / issue / email — and nothing else.** It explicitly does
**not** perform the I2 state-refresh a human-invoked `/arbi` does (that write is
authorised by James invoking it interactively; an unattended run has no such invocation). So
PR 7a: **no writes** (not even `roadmap-state.md`), no DB, no Render, no GitHub mutation, no
branch creation, no roadmap-state overwrite, no capital-impacting output, no Model A-derived
recommendation. It is **I0–I1 only** — deliberately boring, read-only, and impossible to
confuse with real autonomy. **PR 7b onward** (standing scheduled autonomy that writes/acts
unattended) stays blocked on the preconditions.

**As wired** (Routine `trig_01PiLVYg2GHAKpW8Xy43z5JN`, daily 20:30 UTC = 06:30 AEST, fresh
session, push+email to James): the read-only guarantee is **prompt-enforced only** — the fresh
session holds write tools but the trigger instructs it to emit the brief and never write
(risk **R5**; a role-scoped runtime would enforce it mechanically). Pause/stop it any time by
disabling or deleting that trigger. To promote to PR 7b (unattended writes), clear the
preconditions below first. PRs 7–10 run **git-native** — Claude Code Routines
(schedule) + git (memory: `memory/`) + GitHub branch-protection/PRs/CI + the
`unattended-guard.sh` hook. The loop machinery is **built** (guard hook, memory
bank, `/arbi-dream`, `/arbi-promote`, `/arbi-run`; see `arbi-autonomy-loop.md`);
standing activation stays gated. Managed Agents is an optional hosted backend,
not a prerequisite.

**Preconditions before PR 7b+ (standing / writing scheduled autonomy — NOT required for the
7a read-only dry run):** (1) the P0 Model A dispute resolved; (2)
`m14_candidate_agent_db_role_scoping` landed (read-only DB role); (3) the scorecard trend +
decision log + eval suite showing arbi's calls hold up
(`arbi-permission-model.md` §promotion preconditions).

**Never lifts, at any PR:** the personal-advice firewall (s766B) — arbi automates *what gets
built*, never *what to trade*; the Model A quarantine (rule #11) until resolved; and the
irreversible tiers (5–7) stay `always_ask`/disabled regardless of track record. Autonomy
expands only on the reversible dev/ops side.

---

## Last wake snapshot

_Not yet established. The first `/arbi` run records: timestamp, current branch, ahead-of-
main count, open PRs, latest commit sha, test pass/fail count, latest on-disk migration,
and data-feed freshness (`prices.dt`, `signals.as_of`, recent `job_runs`). Subsequent
`/arbi` runs diff against this block to surface "what changed / new bugs" and then
overwrite it._

```
(baseline pending — run /arbi)
```
