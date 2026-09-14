# asxos docs map

**Status:** current
**Scope:** whole repo — navigation index / source-of-truth map
**Last verified:** 2026-08-12 (newest-handoff entry refreshed per the 08-11 handoff's own drafted amendment; 2026-08-12 guard-carveouts proposal mapped) · 2026-08-10 (Stage 0 authority alignment; older claims retain their dates)
**Read priority:** read first
**Superseded by:** N/A

Where truth lives. Status labels used across the repo: `current` | `historical` | `superseded` | `stale` | `branch-only`.
**If a doc contradicts this map, trust the "Authoritative source" column below and fix the doc.**

**New session, unsure where to start?** Read `../CLAUDE.md`, then the newest `session-handoff-*.md`, then this map — then stop and ask. Do not invent your own entry point.

**Handoffs live on `main`.** Any doc a future session must read has to be committed to `main`. A handoff that lives only on a feature branch or in plan-mode is a process defect — this repo has already lost one that way (`research/session-handoff.md:6-9`).

---

## Read first, in order
1. `../CLAUDE.md` — agent guide + non-negotiables (note **standing** rule **#11**: Model A quarantine — resolved 2026-07-11 *against* Model A; the quarantine stands as policy)
2. `session-handoff-2026-08-11.md` — the newest dated handoff and current priority state; it records the five-PR remediation session, and separates code-complete work from what is actually live in production (four defects fixed in code, zero closed in production)
3. `product/target-architecture.md` — **the ratified target (2026-08-10).** asxos is a
   research-to-capital-decision-to-learning engine; the brief is an experience layer over an
   immutable decision. Read its Errata §0 and Appendix F (the governor rulings) before proposing
   work. **Ratified and canonical since 2026-08-10** (PR #79, merged `9ede7ad`); Stage 0 is
   complete, but that is **not** implementation authority — each stage needs its own approved
   work order
4. `product/roadmap-state.md` — **the single live queue** (Stages 0→6); the P0 Model A dispute is **RESOLVED 2026-07-11** and the ML engine **shelved** — see `model-a-decay-analysis-2026-07-11.md` + `product/ml-engine-shelf-2026-07-11.md`. Where priority conflicts, the newest handoff wins and the roadmap must be reconciled
5. `foundation/BUILD_GUIDE.md` — the executable manual for M1–M12
6. `foundation/phase-b-failure-postmortem.md` — the lessons the previous repo died of; this repo encodes the fixes
7. `next-session-backlog.md` — **reference-only**, not a queue; its itemised evidence is retained but priority comes only from `product/roadmap-state.md`
8. `executable-roadmap-2026-07-04.md` — a historical sequencer; reconcile any still-relevant item through the current handoff/roadmap instead of reviving it wholesale

## Authoritative source by area
| Area | Authoritative source |
|---|---|
| Repo overview | `../README.md` (pointers only — no live counts) |
| Claude session entry | `../CLAUDE.md` → newest `session-handoff-*.md` → this map |
| Live deployment | GitHub Actions workflows in `../.github/workflows/` (Render was deleted 2026-08-12). Config lives in git; secrets in the repo's Actions secrets. |
| Schema / migrations | `../migrations/` + live `supabase_migrations.schema_migrations` (must equal `REQUIRED_MIGRATIONS` in `../asxos/api/main.py`). `public.schema_migrations` is a dead legacy table — never read it. |
| Tax math | `foundation/spec/tax-alpha.md` (v1.5 — TC-20 is implemented; spec-first per non-negotiable #8) |
| Governance | `proposals/governance-first-architecture-2026-06-30.md` + `../.claude/rules/portfolio-conventions.md` |
| Research store | `../migrations/0027_research_store.sql` for schema; the **live DB** for state (`research/research-store-schema.md`'s "applied-empty" header is a 2026-06-22 snapshot) |
| Model A / alpha evidence | **`model-a-decay-analysis-2026-07-11.md`** (the resolution — no usable edge on 19,032 matured signals) + **`product/ml-engine-shelf-2026-07-11.md`** (James's shelve decision + how it plays out) are authoritative on status; live `signals`/`signal_outcomes` + `../asxos/domain/research/alpha_eval.py` for the data; audit design in `model-a-audit-and-extension-plan-2026-07-04.md` Part A; `research/alpha-research-audit.md` is the pre-training-period diagnosis (not live-signal truth) |
| Portfolio invariants | `../.claude/rules/portfolio-conventions.md` |
| Risk | **Policy** exists (`product/portfolio-policy.md` — sector cap, position count, CGT rules, and the accepted v1 co-movement blindness); **no enforcement engine is built** beyond the allocator's constraint waterfall (`../.claude/rules/portfolio-conventions.md`). The numeric risk *mandate* is **DEFERRED** — blocker: "James must complete the capital/risk calibration before Stage 4" (`product/target-architecture.md` F4). Until then vol/beta/correlation/drawdown are **reporting-only**, under five non-deferrable universal gates. Design notes: `model-a-audit-and-extension-plan-2026-07-04.md` Part C |
| Backlog / session state | `product/roadmap-state.md` is **the single live queue**; `next-session-backlog.md` is reference-only. The newest `session-handoff-*.md` carries session continuity but does not create a competing queue. |
| Product vision / program state | `product/north-star.md` is the charter; `product/target-architecture.md` is the ratified target; `product/roadmap-state.md` is the single live queue. `/arbi` ("wake up") is the session entry ritual; `/arbi-close` writes the handoff. |
| Architectural decisions (D1–D14) | `product/architecture-decision-record.md` — the living decision record placed 2026-08-23: cash floor 7.5% (D1), 0% gross leverage (D2), the eight-criteria Model A successor bar (D4), vertical slices not sprints (D6), GitHub Issues as work substrate (D10), the three ticket types (D11), the two-layer challenge mechanism (D12–D14), and the §6 build sequence. Evidence base archived at `archive/asxos-audit-v2-correctness-and-delivery.md` (active input until Slice 0 merges) and `archive/asxos-delivery-diagnostic.md` (superseded — do not act on); ticketing research at `research-archive/work-management-ticketing-2026-08-23.md`. **Unreconciled conflict, James rules:** D10 calls `product/roadmap-state.md` frozen and moves actionable work to GitHub Issues, which contradicts the “Backlog / session state” row above and read-first item 4. Until James reconciles, those rows stand and D10 is ratified-but-not-in-force. |
| Daily brief (email) | `product/daily-brief-v2.md` is the implementation SoT for the morning email (pipeline, `SectionResult`, information design, stages 0–3). `asxos/brief/compose.py` is the live send path. Does not replace the north-star or target-architecture. Historical strategy notes under `strategy/V2_*` are not this spec. |
| Agent authority | **`AGENTS.md` is the contract** — who arbi is, James's reserved domain (§2: what the product is for, capital, spend above the cap), the reversal-cost classes (§6), landing work and the migration sequence (§8), delegation (§9), the source-of-truth ladder (§10) and secrets (§13). It wins over every other repo doc. `CLAUDE.md` adds the domain facts, the non-negotiable rules and the schema reference. |
| arbi's operating state | `product/roadmap-state.md` (reconciled position, ranked queue, amendments, last-wake snapshot) + `product/decision-log.md` (append-only: every ONE THING and whether it worked) + `product/risk-register.md` + `product/james-inbox.md` (what is still James's under `AGENTS.md` §2) + `product/dark-launch-exit-plan.md` (ship/delete/keep-dark verdicts for gated surfaces) + `product/memory/` (the git-native second brain: `lessons.md` and `project-facts.md`, written directly, no candidate/approved split). Specialist roster and the canonical owner→agent table: `../.claude/agents/README.md`. Rituals: `/arbi` wakes and does the one thing, `/arbi-close` records and lands the handoff, `/arbi-mission` runs a multi-node mission (`guilfoyle` plans, arbi lands it), `/arbi-team` the parallel form, `/build` the one-file path. |
| Portfolio decision-support governance | `product/portfolio-manager-charter.md` (the role: allocation memos James acts on, never executes) + `product/portfolio-policy.md` (James's capital mandate — objectives, risk, hard constraints) + `product/recommendation-schema.md` (the shape of an action memo) + `product/portfolio-outcome-ledger.md` (memos → decisions → outcomes) + `AGENTS.md` §2 (capital is James's: placing, modifying or cancelling a real order, moving funds, enabling live trading). The firewall is **execution** (James's broker), not analysis; rule #11 keeps every memo model-independent. Surfaced via `/pm-review`. |
| Agent routing | `../CLAUDE.md` "Subagents — delegation policy" tables are the source; a lint-enforced transcription is planned in a later process PR |
| Agent DB role scoping | enforcement design (not yet implemented): `model-a-audit-and-extension-plan-2026-07-04.md` Part B + `live-readiness-audit-plan-2026-07-04.md` §7. **Provisioning-route decision: `pr2a-supabase-ro-provisioning-plan-2026-07-05.md`** — route gated on a feasibility check; no frontmatter flips until the chosen route passes the full live-fire battery |
| Language / stack strategy (incl. Rust/Go) | `executable-roadmap-2026-07-04.md` §H is the single source (verdict "not now"; Python primary; Rust later for kernels only; Go rejected-for-now; adopt uv). Rust/Go are planned — not in the repo. Older language notes (e.g. `research/claude-fundamentals-audit-handoff-2026-07-04.md` §6) defer to §H. |

## If you are about to… read this first
| About to… | Read |
|---|---|
| Run a migration / `ALTER` / `DROP` | `db-shared-project-audit-2026-06-28.md` §2 (mandatory `pg_depend` pre-apply check; asxos is a 43-table tenant in a shared ~165-table project) |
| Touch tax math | `foundation/spec/tax-alpha.md` + CLAUDE.md #8 (spec amendment first) |
| Touch the portfolio / allocator | `../.claude/rules/portfolio-conventions.md` |
| Work on the research store / factors | `research/research-store-schema.md` + live-DB verification |
| Act on a Model A signal | **STOP** — CLAUDE.md rule #11 (Model A is quarantined) |
| Decide what to work on next / start a session | `/arbi` ("wake up") — reconciles the roadmaps + live state; reads `product/north-star.md` + `product/roadmap-state.md` |

## Current audits / plans (2026-07-04 → 07-05)
- `session-handoff-2026-07-04.md` — session state as of 2026-07-04. **Its P0 (Model A dispute) is RESOLVED 2026-07-11** — see `model-a-decay-analysis-2026-07-11.md` + `product/ml-engine-shelf-2026-07-11.md`; read it for session context, not for current Model A status
- `live-readiness-audit-plan-2026-07-04.md` — live-state audit + docs-cleanup plan
- `model-a-audit-and-extension-plan-2026-07-04.md` — Model A audit design + agent DB scoping (Part B) + Rust/Go RFC (Part C); holds the verbatim detail the roadmap only sequences
- `executable-roadmap-2026-07-04.md` — the sequencer (5 workstreams + PR plan)
- `pr2a-supabase-ro-provisioning-plan-2026-07-05.md` — PR 2A: the `supabase-ro` provisioning-route decision (local-stdio recommended; the hosted/custom connector is transport-unstable; stop/go gate before the six frontmatter flips)

## Current proposed execution programmes (reference-only; not the live queue)

- `proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md` — two-lane
  programme for the outcome engine and Arbi second brain, queued by James after the existing
  remediation work on 2026-08-12. It sequences bounded work orders and a Claude Code handoff; it
  grants no blanket implementation or authority change. `product/roadmap-state.md` retains the
  canonical queue and activates one packet item at a time.
- `proposals/asxos-research-to-decision-live-slice-brief-2026-08-10.md` — prototype evidence and
  the bounded read-only real-data adapter recommendation; the prototype was later adopted by PR #87.
- `proposals/arbi-outcome-programme-convergence-sprint-2026-08-08.md` — pre-Stage-0 convergence
  source material. Its dated repository/PR state is historical; retain its contract-reuse and
  exact-evidence principles, but do not revive it as a queue.

## Historical / background (do not treat as current)
- `foundation/phase-*.md` — rebuild history. `foundation/phase-4-architecture-system-architect.md` describes an abandoned VPS/systemd/local-Postgres design, superseded by the live GitHub Actions/Supabase stack (see its banner).
- `audit-2026-06-27.md`, `strategy/*` — dated snapshots.
- `research/repo-navigation-audit-and-plan-prompt-2026-07-04.md` — HISTORICAL/executed: the origin of this docs map (shipped in PR #16). Kept as the map's rationale record.
- `research/claude-fundamentals-audit-handoff-2026-07-04.md` — HISTORICAL: the original fundamentals hypothesis. State claims superseded by `session-handoff-2026-07-04.md`; code claims verified into `live-readiness-audit-plan-2026-07-04.md`; language strategy (§6) defers to `executable-roadmap-2026-07-04.md` §H.
- `asxos-live-readiness-audit-2026-07-04.md` — HISTORICAL: the original ~05:30 UTC audit that `live-readiness-audit-plan-2026-07-04.md` was built against. Live state (§3) re-verified unchanged ~06:00 (plan §2); classification findings (§1/§2) executed in this map; next-actions (§5) sequenced by `executable-roadmap-2026-07-04.md`.

## Stale — do not use as a session entry point
- `next-session-kickoff.md` — references a three-migration-epochs-old branch/state (see its banner).

## Branch-only

- local-only `agent/arbi-authority-gate0@eeed24019edf` — Gate0 deny-only/worktree/MCP hardening; code-ready with MCP canary pending, no authority increase, review-policy cutover held.
- local-only `agent/arbi-future-state-operating-model@33eb00e3cd34` — reviewed future-state proposal; `CHALLENGE / CONDITIONAL ADOPT`, not canonical product state.
- local `agent/investment-engine-dossier@6cfaf15518d8` — large investment-engine source-material dossier; its matching remote branch is four commits behind; extract selectively, do not merge wholesale.

A doc a future session must read still has to be committed to `main`; branch-only artifacts are
candidate evidence, not authority (`research/session-handoff.md:6-9`).
