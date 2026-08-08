# asxos docs map

**Status:** current
**Scope:** whole repo — navigation index / source-of-truth map
**Last verified:** 2026-08-08 (wake-up and branch-only entries; older claims retain their dates)
**Read priority:** read first
**Superseded by:** N/A

Where truth lives. Status labels used across the repo: `current` | `historical` | `superseded` | `stale` | `branch-only`.
**If a doc contradicts this map, trust the "Authoritative source" column below and fix the doc.**

**New session, unsure where to start?** Read `../CLAUDE.md`, then the newest `session-handoff-*.md`, then this map — then stop and ask. Do not invent your own entry point.

**Handoffs live on `main`.** Any doc a future session must read has to be committed to `main`. A handoff that lives only on a feature branch or in plan-mode is a process defect — this repo has already lost one that way (`research/session-handoff.md:6-9`).

---

## Read first, in order
1. `../CLAUDE.md` — agent guide + non-negotiables (note **standing** rule **#11**: Model A quarantine — resolved 2026-07-11 *against* Model A; the quarantine stands as policy)
2. `session-handoff-2026-08-08.md` — the newest dated handoff and current priority state after it reaches `main`; it separates shipped evidence, branch-only work, and unratified future-state recommendations
3. `product/roadmap-state.md` — the living reconciled state (**current authority**); the P0 Model A dispute is **RESOLVED 2026-07-11** and the ML engine **shelved** — see `model-a-decay-analysis-2026-07-11.md` + `product/ml-engine-shelf-2026-07-11.md`. Where priority conflicts, the newest handoff wins and the roadmap must be reconciled
4. `foundation/BUILD_GUIDE.md` — the executable manual for M1–M12
5. `foundation/phase-b-failure-postmortem.md` — the lessons the previous repo died of; this repo encodes the fixes
6. `next-session-backlog.md` — itemized backlog (top half current; the 2026-06-28 half is partially stale — see its banners)
7. `executable-roadmap-2026-07-04.md` — a historical sequencer; reconcile any still-relevant item through the current handoff/roadmap instead of reviving it wholesale

## Authoritative source by area
| Area | Authoritative source |
|---|---|
| Repo overview | `../README.md` (pointers only — no live counts) |
| Claude session entry | `../CLAUDE.md` → newest `session-handoff-*.md` → this map |
| Live deployment | `../render.yaml` + live Render via MCP (`make check-drift`). No Blueprint is connected — `render.yaml` is the reconciliation target, not auto-applied. |
| Schema / migrations | `../migrations/` + live `supabase_migrations.schema_migrations` (must equal `REQUIRED_MIGRATIONS` in `../asxos/api/main.py`). `public.schema_migrations` is a dead legacy table — never read it. |
| Tax math | `foundation/spec/tax-alpha.md` (v1.5 — TC-20 is implemented; spec-first per non-negotiable #8) |
| Governance | `proposals/governance-first-architecture-2026-06-30.md` + `../.claude/rules/portfolio-conventions.md` |
| Research store | `../migrations/0027_research_store.sql` for schema; the **live DB** for state (`research/research-store-schema.md`'s "applied-empty" header is a 2026-06-22 snapshot) |
| Model A / alpha evidence | **`model-a-decay-analysis-2026-07-11.md`** (the resolution — no usable edge on 19,032 matured signals) + **`product/ml-engine-shelf-2026-07-11.md`** (James's shelve decision + how it plays out) are authoritative on status; live `signals`/`signal_outcomes` + `../asxos/domain/research/alpha_eval.py` for the data; audit design in `model-a-audit-and-extension-plan-2026-07-04.md` Part A; `research/alpha-research-audit.md` is the pre-training-period diagnosis (not live-signal truth) |
| Portfolio invariants | `../.claude/rules/portfolio-conventions.md` |
| Risk | none built (v1 is risk-blind by design — `../.claude/rules/portfolio-conventions.md`); design notes in `model-a-audit-and-extension-plan-2026-07-04.md` Part C |
| Backlog / session state | `next-session-backlog.md` + the newest `session-handoff-*.md` (handoff outranks backlog on priority; backlog outranks handoff on itemized detail) |
| Product vision / program state | `product/north-star.md` (the charter — "The Output") + `product/roadmap-state.md` (living reconciled roadmap + 10-PR autonomy sequence). `/arbi` ("wake up") is the session entry ritual; `/arbi-close` writes the handoff. |
| arbi governance (the Autonomy Kernel) | `product/arbi-constitution.md` (authority + limits) + `product/arbi-authority.md` (source-of-truth ladder) + `product/arbi-permission-model.md` (blast-radius: **Infrastructure ladder I0–I6** + **Portfolio ladder P0–P6**) + `product/arbi-harness.md` (operating contract) + `product/arbi-scorecard.md` (hard gates + reward) + `product/arbi-promotion-gate.md` + `product/arbi-memory-policy.md` + `product/arbi-dream-policy.md` + `product/arbi-evals.md` + `product/rubrics/` + ledgers (`arbi-run-ledger.md`, `decision-log.md`, `risk-register.md`) + `product/james-inbox.md` (decisions reserved to James) + `product/dark-launch-exit-plan.md` (ship/delete/keep-dark verdicts for gated surfaces) + `product/memory/` (the git-native second brain) + `product/arbi-autonomy-loop.md` (the self-driving loop) + `product/arbi-managed-agent-spec.md` (optional hosted backend) + `.claude/agents/arbi-red-team.md` (adversarial gate on arbi's "one thing") + `.claude/agents/guilfoyle.md` + `.claude/commands/arbi-mission.md` (mission-control execution lead under arbi: `/arbi-mission` turns an approved mission into a task graph → specialists → draft PR, attended + reversible) + **the autonomy unlock pack (2026-07-14)**: `product/guilfoyle-mission-control.md` (the stack narrative + mission routing) + `product/arbi-goal-recipes.md` (long-window `/goal` prompts incl. the 12-hour recipe + PR transaction discipline) + `product/runbooks/` (`reversible-work-window.md`, `agent-team-mission.md`) + `.claude/agents/reversible-work-builder.md` (the mutation hands) + `.claude/commands/arbi-team.md` (agent-teams form, large parallel missions, plan-approval gate) + `.claude/skills/` (`reversible-work-window`, `arbi-mission`, `agent-team-mission`, `pr-readiness` — skill-scoped allowed-tools, the R-A4 prototype) + `.github/CODEOWNERS` + `.claude/hooks/unattended-guard.sh` (unattended tier guard). James is governor; arbi is the bounded operating controller; guilfoyle is its execution lead. |
| Portfolio decision-support governance | `product/portfolio-manager-charter.md` (the role: allocation memos James acts on, never executes) + `product/portfolio-policy.md` (James's capital mandate — objectives, risk, hard constraints) + `product/recommendation-schema.md` (the shape of an action memo) + `product/portfolio-outcome-ledger.md` (memos → decisions → outcomes) + the Portfolio ladder P0–P6 in `product/arbi-permission-model.md`. The firewall is **execution** (James's broker), not analysis; rule #11 keeps every memo model-independent. Surfaced via `/pm-review`. |
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

## Historical / background (do not treat as current)
- `foundation/phase-*.md` — rebuild history. `foundation/phase-4-architecture-system-architect.md` describes an abandoned VPS/systemd/local-Postgres design, superseded by the live Render/Supabase stack (see its banner).
- `audit-2026-06-27.md`, `strategy/*` — dated snapshots.
- `research/repo-navigation-audit-and-plan-prompt-2026-07-04.md` — HISTORICAL/executed: the origin of this docs map (shipped in PR #16). Kept as the map's rationale record.
- `research/claude-fundamentals-audit-handoff-2026-07-04.md` — HISTORICAL: the original fundamentals hypothesis. State claims superseded by `session-handoff-2026-07-04.md`; code claims verified into `live-readiness-audit-plan-2026-07-04.md`; language strategy (§6) defers to `executable-roadmap-2026-07-04.md` §H.
- `asxos-live-readiness-audit-2026-07-04.md` — HISTORICAL: the original ~05:30 UTC audit that `live-readiness-audit-plan-2026-07-04.md` was built against. Live state (§3) re-verified unchanged ~06:00 (plan §2); classification findings (§1/§2) executed in this map; next-actions (§5) sequenced by `executable-roadmap-2026-07-04.md`.

## Stale — do not use as a session entry point
- `next-session-kickoff.md` — references a three-migration-epochs-old branch/state (see its banner).

## Branch-only

- `agent/arbi-authority-gate0@eeed24019edf` — Gate0 deny-only/worktree/MCP hardening; code-ready with MCP canary pending, no authority increase, review-policy cutover held.
- `agent/arbi-future-state-operating-model@33eb00e3cd34` — reviewed future-state proposal; `CHALLENGE / CONDITIONAL ADOPT`, not canonical product state.
- `agent/investment-engine-dossier@6cfaf15518d8` — large investment-engine source-material dossier; extract selectively, do not merge wholesale.

A doc a future session must read still has to be committed to `main`; branch-only artifacts are
candidate evidence, not authority (`research/session-handoff.md:6-9`).
