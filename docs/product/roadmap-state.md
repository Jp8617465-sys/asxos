# asxos Roadmap & State — the reconciled picture

**Status:** current (living document — refreshed every `/arbi` and `/arbi-close`)
**Scope:** whole repo — the single reconciliation of every roadmap + the live state
**Last verified:** 2026-07-14 (post-merge reconciliation — James merged the six-PR train
#32→#33→#35→#31→#34→#36: sync_financial_statements batching, R12 firewall gate, R13 review-gate
hardening, Guilfoyle mission-control, overnight governance record, orchestrator-mode sketch.
Monitoring lane fixes all on main. **Confirmed (2026-07-14, later same day): #29 (discipline
evaluator) and #38 (autonomy unlock pack) are both MERGED to main** (`2a49df9`, `1af76e4`) — all
"#29 open/draft" references below have been corrected to reflect this. Remaining open: #5 —
recommend close, superseded by the ML shelf; #39 (permission-friction/guard pack) — open draft,
`full-check` CI failing.)
**Owner:** arbi (`.claude/agents/arbi.md`) reads and refreshes this; humans may edit freely
**Superseded by:** N/A

---

## State header — arbi's durable memory (read this first)

The at-a-glance fields `/arbi` reads and `/arbi-close` refreshes. Everything below is the
detail behind these lines.

- **Current status:** M1–M14a built (M13/M14a **dark-launched**); governance through
  Phase 2b. **P0 Model A dispute RESOLVED 2026-07-11 (no usable edge); James SHELVED the ML
  engine** — the product is now explicitly the **model-independent moat** (discipline, tax,
  themes, ETFs). arbi PM layer + operating stack (constitution/authority/permission/
  scorecard/memory/dream + operating docs) landed 2026-07-10–11. Portfolio-team-visibility
  PR2 (both halves — PR2a loader + PR2b render) is now landing this session (2026-07-14).
- **Top blocker:** **None at the product level** — the 6-month P0 is closed. Rule #11 (Model
  A quarantine) is now **standing policy**, not a blocker to lift. What gates *further
  autonomy* (not the product): agent DB role-scoping + a scorecard track record. What gates
  *specific capital/policy moves*: the `james-inbox.md` items.
- **Current workstream:** post-shelf model-independent build. The monitoring lane is **fully
  merged** (PRs #26, #30, #32) — remaining validation is the first post-merge Saturday
  `sync_financial_statements` run (`duration_ms` watch-item) and the next Sun 03:00 UTC
  `track_signal_outcomes` cron. **#29 (discipline evaluator) is MERGED** (`2a49df9`) — next
  product lane, portfolio-team-visibility **PR2 (both halves)**, is also landing this
  session: **PR2a** (the `_discipline_findings()` loader + `BriefData` field) and **PR2b**
  (the `brief.html.j2` "Portfolio discipline" render block — the increment that actually
  changes James's emailed brief); then ETF Slice 2 (gated on VGS/VAS lot data).
- **Open PRs (as of 2026-07-14 reconciliation):** **#29** (discipline evaluator) is **MERGED**
  (`2a49df9`) — no longer open. Remaining open: **#5** (June quant-benchmarking research —
  recommend CLOSE as superseded by the 07-11 decay analysis + ML shelf; merging it would import
  pre-shelf ML-roadmap guidance as if current), and this session's PR2 (both PR2a loader +
  `BriefData` field, and PR2b `brief.html.j2` render block), landing as a draft PR.
- **Recently completed (on `main`, 2026-07-13/14 merge train):** monitoring lane restored +
  batched (`track_signal_outcomes` cast, `snapshot_portfolio` trading-day anchor,
  `sync_financial_statements` OOM fix + `executemany` batching — PRs #30/#32); **R12 resolved**
  (s766B gate on all 11 theme CLI entry points, #33); **R13 resolved** (review-gate same-step
  staging bypass hardened + 15 hook tests, #35); **Guilfoyle mission-control landed**
  (charter + `/arbi-mission`, thesis-as-broker-report reframe, HUBS 10/20 recorded, #31);
  overnight governance record (#34); orchestrator-mode lean sketch (#36). Earlier: shelve ML +
  ETF Slice 2a (#25); P0 decay resolution; ETF Phase-1 `security_kind` (migration 0037, #24).
- **Blocked items:** real *signal-driven* capital deployment stays **dormant by standing
  policy** (rule #11), not by an open dispute. Phase 2c is **reframed** model-independent
  (discovery/discipline/ETF) and no longer waits on a signal engine
  (`ml-engine-shelf-2026-07-11.md`).
- **Next actions:** see the ranked queue below. Monitoring lane is merged (queue #1 done —
  residual = watch the first post-merge Sat run). **#29 (discipline evaluator) is MERGED**
  (`2a49df9`); candidate new #1 (2026-07-14) is portfolio-team-visibility **PR2, both
  halves** — **PR2a** (the `_discipline_findings()` loader) and **PR2b** (the
  `brief.html.j2` render block) — landing together this session as a draft PR.
- **Decisions needed from James:** see **`james-inbox.md`** — HUBS concentration policy (reframed
  2026-07-12: ESPP, not a conviction pick); CBA thesis #1 fix-or-retire; VGS/VAS holding-lot data.
- **Portfolio-team visibility (NEW 2026-07-12):** James asked why the portfolio team didn't
  auto-flag HUBS/CBA. Root cause = a **surfacing gap**, not a compute gap — the daily discipline
  cards are computed then discarded at render (V1 email has no discipline section; the V2 tree is
  KEEP-DARK), and the `/pm-review` LLM findings die in markdown. Reversible fix proposed (3
  specialists): a model-independent deterministic discipline **section in the brief James already
  reads** (no gate flip, `ASXOS_PERSONAL_USE` only), then a findings-sink table, then a later gated
  LLM `/pm-review` Routine. Full: `docs/proposals/portfolio-team-visibility-2026-07-12.md`.
  Corrects an earlier arbi error: M13.8 paper-trade sign-off **is** scoped in code
  (`paper_trade.py:294`), not unscoped. Honest scope note: this fixes the *flagging-visibility*
  half; automated *stock rating / thesis generation* is the shelved-ML (rule #11) + unbuilt
  discovery-agent track, a separate conversation.
- **Known risks:** (1) `m14_candidate_agent_db_role_scoping` — agent SELECT-only is
  prompt-enforced only; (2) v1 allocator risk-blindness to ASX beta clustering
  (`m14_candidate_beta_cap`); (3) built-but-dark-launched layers are unreleased, not done
  (`dark-launch-exit-plan.md`); (4) R5 — the scheduled 7a brief's read-only guarantee is
  prompt-enforced only.
- **Last verified:** 2026-07-11 (post-shelf; reflects the P0 resolution + ML-shelf decision).

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
| Governance Phase 2c | `theme-researcher` + `instrument-selector` | **Not started — reframed model-independent** (`ml-engine-shelf-2026-07-11.md`); the sole remaining prereq is agent DB role scoping, not Model A. | handoff §5 |
| Governance Phase 3 | executable thesis invalidation | **Not started.** | `next-session-backlog.md` |
| Governance Phase 4 | `/pm-review` 5→7 agents | **Not started.** | `next-session-backlog.md` |
| V2 product `M-Thesis-*` | `V2_..._BRIEF_SPEC.md` Part 8 | **Re-scoped model-independent** — the thesis/discipline/tax layer is authoritative and shippable today; the signal-engine framing is retired (ML shelved 2026-07-11). | V2 spec Part 8 |
| Executable roadmap PR1–8 | `executable-roadmap-2026-07-04.md` §D | PR1 (docs cleanup) partly landed; **PR2 (agent DB read-only scoping) is the near-term unblocker**; PR5 = the Model A audit job. | executable-roadmap §D |

**One-line reconciled read (updated 2026-07-11 — P0 resolved, ML shelved):** *M1–M14a are
built (M13/M14a dark-launched); governance is through Phase 2b. The Model A P0 is **resolved
against Model A** (no usable edge on 19,032 matured signals) and James has **shelved the ML
engine** — the signal-driven allocator + opportunity-cost ranking stay **dormant by standing
policy** (rule #11), and the product IS the model-independent moat (thesis/discipline
scaffolding, tax engine, theme stewardship, governance, ETFs) — all authoritative and
shippable today. The cleanest forward move is the model-independent build: fix the monitoring
crons (`track_signal_outcomes`'s fix is committed on PR #26, pending merge + deploy), then ETF
Slice 2, with agent DB role scoping ahead of any new agents — not a signal engine.*

---

## Blocked — P0 (RESOLVED 2026-07-11; read `docs/model-a-decay-analysis-2026-07-11.md`)

- **P0 — Model A signal reliability: RESOLVED, against Model A.** The decay check ran directly
  on **19,032 matured `signal_outcomes`**: `corr(ml_prob, 21d return) = −0.03`; STRONG_BUY
  returned −0.09% at 21d vs HOLD's +5.07% (conviction inverted at the top) — **no usable edge**
  over the weeks-to-months horizon theses hold for. James's original distrust is vindicated.
  **Rule #11 → standing** (not removed; removal would mean Model A is fine). This closes the
  *dispute*; it does not by itself unblock Phase 2c — that now needs James's strategic call
  (retrain a new version to a pre-registered decay bar / shelve the ML engine / both). The
  model-independent product (discipline, tax, themes, ETFs) was never blocked and is the path
  forward.
- **Strategic call MADE (James, 2026-07-11): SHELVE the ML engine.** Model A is demoted from
  product alpha-engine → dormant passive monitor; the product IS the model-independent moat.
  How it plays out (crons, allocator, brief, Phase 2c reframe, the revival decay-bar):
  **`docs/product/ml-engine-shelf-2026-07-11.md`**. Phase 2c is now the model-independent
  discovery/discipline/ETF expansion — it no longer waits on a trusted signal engine.
- **Dormant-by-standing-policy (narrow, updated 2026-07-11):** the signal-driven
  **allocator** capital path + the peripheral `compute_opportunity_cost` ranking; real
  *signal-driven* capital deployment. These are dormant under rule #11 (standing), not
  "blocked pending a fix." **Governance Phase 2c is NOT in this list** — it is reframed
  model-independent (`ml-engine-shelf-2026-07-11.md`) and its only remaining prereq is agent
  DB role scoping, not a signal engine. **NOT affected at all:** the thesis/discipline
  scaffolding, tax engine, theme stewardship, governance, and the brief's non-signal sections
  — all authoritative today (scan `wf_f54323f5-d7d`, verdict supported).
- **Second-order unblocker:** agent DB role scoping (`m14_candidate_agent_db_role_scoping`
  / PR2) — a prerequisite the roadmap places *before* Phase 2c regardless of Model A.

## In flight

- **MERGED 2026-07-11 as PR #25 (`eff3732`):** the post-shelf reconciliation + arbi operating
  docs + **ETF Slice 2a** kind-aware ingestion (`asxos/ingestion/universe.py`, with
  `refresh_universe` test coverage) — formerly branch `claude/asxos-product-manager-agent-tzszlv`,
  now on main. No longer awaiting a merge call.
- **ETF Slice 2 (VGS/VAS holdings) — not started.** Code side is unblocked (Slice 2a merged);
  it is now gated only on James's holding-lot data (`james-inbox.md` VGS/VAS row).
- **MERGED 2026-07-11 as PR #26:** the 2026-07-11 wake + 8-hour autonomy window output —
  read-only probe allowlist, monitoring lane first pass (`check_model_staleness` shelf-aware,
  `track_signal_outcomes` init-pool fix), `validate_price_data` $0.02 floor,
  `sync_financial_statements` 512Mi-OOM bounded-worker fix.
- **MERGED 2026-07-13/14 (six-PR train, James-ordered #32→#33→#35→#31→#34→#36):** monitoring
  lane finished + batched (#30 earlier same day, then #32); R12 s766B theme-CLI gate (#33);
  R13 review-gate hardening (#35); Guilfoyle mission-control + thesis-as-broker-report
  reframe + HUBS 10/20 record (#31); overnight governance record (#34); orchestrator-mode
  lean sketch (#36).
- **MERGED 2026-07-14: PR #29** (discipline evaluator, `2a49df9`) — `discipline.py` + 19 tests
  landed on main. The follow-on PR2a/PR2b (loader + `brief.html.j2` render block) is also
  **MERGED** (#41, plus companion tests #44) — the emailed brief now renders discipline findings.
- **PR #5 no longer open** (resolved since the 07-13 wake, per the 2026-07-16 open-PR probe).
- **Open drafts awaiting James's merge train (2026-07-16):** #47 (regulatory degraded-note
  visibility + CGT tax-actions folded into the gated discipline digest — merge first: closes a
  firewall-parity gap) · #46 (dream candidate + automation plan; promote manually as Phase 0) ·
  #42 (product-health scorecard regen). CI green not yet verified on any of the three.

## Ranked next-action queue

Each action names its north-star tie, the roadmap item it advances, and the owning
agent/command. arbi keeps this ranked; it is brief-only and does not execute these.

**Current #1 (2026-07-16 wake): root-cause and fix the `regulatory_events` starvation** —
2 rows, latest 2026-07-08, while `ingest_regulatory` reports green daily (Treasury source
dead behind `assert_partial_success(0.5)` passing on RBA alone). Draft PR #47 ships the
*visibility* layer (DEGRADED-note surfacing); this action is the *feed* root-cause — live-probe
the Treasury URL, fix/replace/retire per fail-loud (CLAUDE.md #1/#10), regression-test the
degraded path. North-star: backdrop events reach James before they cost money. Owner: main
loop, consulting `backend-architect`; draft PR for James's merge. Close behind: probe CI on
#47/#46/#42 and stage the merge train; James applies 0038+0039 and re-points the MCP (item 6).

1. **DONE 2026-07-13/14 — monitoring lane restored and merged** (PRs #30 + #32: cast fix,
   trading-day snapshot anchor, OOM fix, batched writes). Residual watch-items, not work:
   first post-merge Sat `sync_financial_statements` run (`duration_ms` vs the 5400s deadline)
   and next Sun `track_signal_outcomes` cron. **#29 (discipline evaluator) is MERGED**
   (`2a49df9`) — see In flight. Candidate replacement #1 is now portfolio-team-visibility
   **PR2, both halves** — **PR2a** (loader) + **PR2b** (render block) — landing together
   this session as a draft PR. _Historical detail of the original item kept below for audit:_ PR #26
   half-healed it — `check_model_staleness` is now SUCCESS(07-12). Three live failures remain
   (live-verified this wake via `job_runs` + Render events): (a) `sync_financial_statements` shows an
   **orphaned `running` row** from a Render `oomKilled(512Mi, ~78s)` at 07-11 16:50Z — that was the
   **PRE-fix** code; PR #26's bounded-worker fix deployed ~07-11 21:10 but is UNEXERCISED (weekly job,
   next run Sat 07-18), so the stale row persists and holds `check_cron_health` red. Action = validate
   the deployed fix with one manual trigger (heals the row + tests it under load); harden concurrency
   first if `performance-engineer` flags 8 workers as unsafe at 512Mi. (b) `snapshot_portfolio`
   **false-blocked** (`UpstreamBlocked: sync_prices has no success row for 2026-07-11` — a Saturday;
   `portfolio_daily_snapshots` frozen since 07-08); make its freshness gate business-day/calendar-aware,
   mirroring how `check_model_staleness` was made shelf-aware. (c) `track_signal_outcomes`
   FAILURE(07-12) on `AmbiguousParameterError` ($1 text vs varchar) — one-line explicit cast
   (monitor-hygiene for the shelved-Model-A passive monitor, NOT a rule #11 re-enable).
   `check_cron_health` (FAILURE 07-12) is failing **correctly** — it is reporting the stuck job;
   it goes green once (a) clears. North-star tie: discipline/health events must reach James before
   they cost money (`north-star.md:64–67` — the HUBS-stop failure class). Roadmap: post-shelf
   model-independent live-ops lane (`ml-engine-shelf-2026-07-11.md:82–90`). Owner: main loop
   (consult `performance-engineer` + `backend-architect`); land as a draft PR for James's merge.
   _Note: `retrain_model_a` FAILURE(06-06)+SUSPENDED is expected (shelved), not part of this fix._
   - **(context) Model A decay check — DONE 2026-07-11, P0 RESOLVED against Model A**
     (`docs/model-a-decay-analysis-2026-07-11.md`; 19,032 matured signals; no usable edge; rule
     #11 standing; James SHELVED the ML engine). Do **not** re-run it — that is recency overfit,
     not diligence (`arbi-red-team`).
2. **Agent DB read-only role scoping (PR2 / `m14_candidate_agent_db_role_scoping`).**
   North-star: non-negotiable #2 (firewall integrity) before more agents sit next to
   governed tables. Owner: `backend-architect`. Prereq for Phase 2c.
3. **Resolve the two open governance proposals** — review/approve or reject `agent_runs`
   #3 and #4 (`asx macro-thesis open --from-agent-run` → `approve`). Owner: James +
   main loop. (Does not expire.)
4. **HUBS data hygiene** — lock-window end date → `theses.tax_notes`. (Acquisition FX
   `0.6450` **confirmed** = brokerage statement, James 2026-07-11 — an ESPP fill FX ≠ spot;
   HUBS is ~flat, not −29%. See `portfolio-outcome-ledger.md`.) Owner: James supplies the
   lock date; main loop records.
5. **Universe→segment→stock coverage framework — ALL instrument kinds, not just equities.**
   2,377 active tracked instruments (au_equity 1,872 · ETF 471 · hybrid 21 · LIC 13), 13 theses
   (0.55%), 1 theme, 0 macro_theses, **zero ETF/LIC/hybrid coverage at all** — the gap is a
   missing narrowing layer (universe → segment → screen → thesis), not too few theses
   (north-star.md explicitly wants a small opinionated set, not universal coverage). James, same
   day: "the etf's etc [need to be] included in our investment plan not just individual
   equities" — the framework treats instrument kind as first-class from Tier 0, not a later
   add-on. Full framework: `docs/proposals/thesis-coverage-framework-2026-07-11.md`. Buildable
   now, no agent DB role scoping dependency: (1) coverage rollup — sector for equities, an
   explicit non-equity bucket for ETF/hybrid/LIC (pure SQL, zero schema — answers "where am I
   structurally blind" directly); (2) wire `screening_rules` — schema-only since migration 0001,
   zero readers, confirmed unwired — to a real `curated_composite` evaluator — **LANDED
   2026-07-12 for the au_equity/fundamentals path**: `asxos/domain/screening/{types,evaluator}.py`
   + `asx screen list`/`run` (`asxos/cli/screen.py`), draft migration
   `0038_screening_evaluator_wiring.sql` (**NOT yet applied**, tightens `source_method` to
   `curated_composite` only, adds the non-governed `screening_runs` audit log); the ETF/LIC
   kind-appropriate criteria (asset-class/geography/breadth for funds — a small net-new taxonomy)
   — **scoped 2026-07-12**: `docs/proposals/etf-lic-screening-criteria-2026-07-12.md`
   (`requirements-analyst`-researched, EODHD field availability checked against real docs, not
   assumed). Phase-1 recommendation: liquidity (`prices`-derived) + distribution yield/franking
   (`rs_corporate_actions`-derived) only — zero new external ingestion, zero unresolved
   vendor-availability risk. Everything else (asset class, geography, cost, AUM, tracking error,
   NAV premium/discount for LICs) waits on a live EODHD probe against a real ASX ETF/LIC symbol
   before further scoping is trusted. Not yet built — needs James's sign-off since it touches
   already-shipped, review-gated evaluator code; (3) wire the missing `asx theme approve|reject|open
   --from-agent-run` CLI verbs onto `themes/service.py`'s already-built governance functions
   (`theme_holdings.symbol` already supports mixed equity+ETF holdings in one theme, no schema
   change needed); (4) clear the 2 pending `macro_theses` `agent_runs` proposals (item 3 above)
   before adding a 4th discovery agent to the queue. Blocked on agent DB role scoping (item 2
   above): a new `sector-screener` discovery agent (bottom-up, coverage-driven — sibling to, not
   a mode of, `theme-researcher`'s top-down macro-conditioned design), sharing
   `theme-researcher`/`instrument-selector`'s not-yet-built `create_theme_from_agent_run()`/
   `create_theme_holding_from_agent_run()` service functions. Governance path identical to
   `macro-economist` at every step — no direct agent writes, ever. Triggered by James,
   2026-07-11. **Spec drafted 2026-07-12**: `docs/proposals/sector-screener-agent-spec-2026-07-12.md`
   — full frontmatter, data sources, 4-step invocation procedure, `ThemeProposal`/
   `ThemeHoldingProposal` JSON output schema, boundaries, and a 6-stage pre-go-live checklist.
   Deliberately NOT materialized as a live `.claude/agents/*.md` file — that step waits on item 6
   (DB role scoping applied) so the agent is never invocable next to governed tables under
   prompt-level-only SELECT enforcement. Owner: `requirements-analyst` (drafted) →
   `system-architect`/`backend-architect` (design) → James (scope sign-off, then apply item 6 to
   unblock materialization).
6. **Agent DB read-only role — design drafted, ready to apply.**
   `docs/proposals/agent-db-readonly-role-design-2026-07-11.md`: a full draft migration
   (`0038_agent_readonly_role.sql`, NOT applied) creating `asxos_agent_ro` — LOGIN, default-deny
   writes (no INSERT/UPDATE/DELETE/TRUNCATE grant, no sequence privileges), `SELECT` on
   everything, `ALTER DEFAULT PRIVILEGES` so future tables auto-grant. Two corrections to the
   original brief: `approve_object`/`reject_object` are Python, not Postgres functions (nothing
   to `REVOKE EXECUTE`); `nextval`/`setval` are `pg_catalog` built-ins (the real control is no
   sequence grant, not a function revoke). Honest limit: whether the role becomes load-bearing
   depends on whether `supabase-ro` is a connection-string MCP (can point at the role via the
   Supavisor pooler — strong) or the hosted Supabase MCP (can't accept a custom role — the
   migration stays defense-in-depth only). Pre-apply checks, post-apply acceptance test, and a
   rollback script are included. **Next: James applies the migration + re-points the MCP
   connection (infra, outside this repo) — this is what actually satisfies autonomy
   precondition (2).**
7. **Competitive gap analysis — Div 296 is a time-boxed opportunity, not just a backlog item.**
   `docs/product/competitive-gap-analysis-2026-07-11.md` (deep-research-agent, cited/confidence-
   rated). Headline: no consumer AU tool models Division 296 (Sharesight explicitly cannot) or
   enforces thesis discipline — asxos already has both built; the gap is surfacing, not engine
   work. **Time-sensitive finding worth weighing against ETF Slice 2 sequencing:** the s296-50
   cost-base-reset election hinges on **market values at 30 June 2026** (already ~11 days past at
   time of writing) — capturing those reset-date valuations now, while fresh, is a concrete,
   perishable, on-moat feature no competitor offers. Full prioritized P1-P6 roadmap (each tagged
   DIFFERENTIATION or TABLE-STAKES) in the doc. Owner: James — decide whether P1 (Div 296 reset
   workflow) jumps the queue ahead of ETF Slice 2 given the perishability.
8. **Multi-instrument expansion (ETFs / LICs / all ASX vehicles).** North-star: moat
   layers 2–3 (discipline + theme stewardship), and it advances **independent of the Model
   A P0** (rule #11 is moot for passive funds — no signal attaches). James: *"I want ETFs
   and all investment vehicles on the ASX involved."* Full plan (valuation = market price;
   look-through = separate exposure layer; `security_kind` keystone; readers-first-then-
   ingestion ordering invariant; minimal Phase-1 cut to hold VGS/VAS): **`docs/proposals/
   multi-instrument-expansion-2026-07-11.md`**. Owner: `system-architect` +
   `backend-architect` (specs done this session); needs James's 4 scope answers before build.

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
| `m14_candidate_espp_employer_concentration` | ESPP/employer-stock treatment: a lot marker (`acquisition_source='espp_employer'` + `tradeable_from`), an `employer_concentration_cap_pct` policy, and the **10% soft-flag / 20% hard-trim** rule James set 2026-07-13 — fold into the `security_kind` build, "build later when it matters." Excludes HUBS from conviction checks; applies the tighter employer cap; gates trim on the lock. | `james-inbox.md` (HUBS resolved 2026-07-13); portfolio-coherence-reviewer 2026-07-13 |

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
| **7a** | Scheduled **read-only dry-run** brief (Routine fires `/arbi`; **output only**) | **RE-WIRED 2026-07-15** — daily 20:30 UTC (06:30 AEST), fresh session, push+email to James; Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`. The 2026-07-10 Routine (`trig_01PiLVYg…`) was found **absent from the live trigger list** on 2026-07-15 while these docs still claimed it live — the brief had silently stopped. Standing lesson: verify with `list_triggers` on wake; never trust this cell alone |
| **7b** | **Standing** scheduled autonomy (arbi writes/acts unattended on a schedule) | **blocked** on the 3 preconditions below |
| 8 | Multi-agent delegation (arbi coordinates specialists) | **`/arbi-run` shipped 2026-07-10** (thin attended bridge); **`/arbi-mission` + `guilfoyle` mission-control drafted 2026-07-13** — its graph-driven, readiness-gated evolution (task graph → specialists → draft PR), still attended + reversible (Guilfoyle plans/judges, never prioritises/spawns/merges); *standing/unattended* dispatch still gated on the 3 preconditions + runtime |
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

**As wired** (Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`, re-created 2026-07-15 — the original
2026-07-10 Routine was found missing from the live trigger list; daily 20:30 UTC = 06:30 AEST,
fresh session, push+email to James): the read-only guarantee is **prompt-enforced only** — the
fresh session holds write tools but the trigger instructs it to emit the brief and never write
(risk **R5**; setting `ARBI_UNATTENDED=1` in the environment config would arm
`unattended-guard.sh` mechanically for these runs — see
`arbi-full-auto-activation-2026-07-15.md`). Pause/stop it any time by disabling or deleting
that trigger. To promote to PR 7b (unattended writes), clear the
preconditions below first. PRs 7–10 run **git-native** — Claude Code Routines
(schedule) + git (memory: `memory/`) + GitHub branch-protection/PRs/CI + the
`unattended-guard.sh` hook. The loop machinery is **built** (guard hook, memory
bank, `/arbi-dream`, `/arbi-promote`, `/arbi-run`; see `arbi-autonomy-loop.md`);
standing activation stays gated. Managed Agents is an optional hosted backend,
not a prerequisite.

**Preconditions before PR 7b+ (standing / writing scheduled autonomy — NOT required for the
7a read-only dry run):** (1) ✅ **MET 2026-07-11** — the P0 Model A dispute is resolved (rule
#11 is now standing policy, not an open question); (2) `m14_candidate_agent_db_role_scoping`
landed (read-only DB role); (3) the scorecard trend + decision log + eval suite showing
arbi's calls hold up (`arbi-permission-model.md` §promotion preconditions). Preconditions (2)
and (3) remain open — resolving the dispute did not by itself unlock standing autonomy.

**Never lifts, at any PR:** the personal-advice firewall (s766B) — arbi automates *what gets
built*, never *what to trade*; the Model A quarantine (rule #11), now **standing policy** —
it lifts only when a *new* model version passes a pre-registered decay bar AND earns
`approved_for_allocation`, never on the basis of v1_5; and the irreversible tiers (5–7) stay
`always_ask`/disabled regardless of track record. Autonomy expands only on the reversible
dev/ops side.

---

## Last wake snapshot

_Recorded by the 2026-07-16 interactive `/arbi` wake — supersedes the 07-13 snapshot; later
runs diff against this._

```
Last wake: 2026-07-16 (interactive /arbi)
- branch: claude/wake-up-arbi-yq98tv — EVEN with origin/main (0 ahead), clean tree
- latest main commit: f89f77f "arbi full-auto activation pack: 7a re-wire, secperf mission loop +
  hardened guard, 0039 agent-ro migration, scorecard accrual (#45)". Landed since 07-13 wake:
  #29 (2a49df9), #39, #41, #44, #45.
- open PRs (all DRAFT): #47 (regulatory degraded-note visibility + CGT tax-actions folded into
  gated discipline digest — closes the ungated tax-actions render) · #46 (dream candidate
  2026-07-15 + dream-automation plan; its own rec: promote MANUALLY as Phase 0, no unattended
  switch) · #42 (product-health scorecard regen). #5 no longer open. CI status NOT probed.
- tests (sandbox): 756 passed / 39 failed / 65 errors — ALL failures+errors are sandbox-env gaps
  (uv-isolated pytest lacks pytest-asyncio, asyncpg, dateutil, joblib; pip can't reach it).
  WORSE than CLAUDE.md's documented 16 — the gap list has rotted again. CI full-check is authority.
- migrations: on-disk through 0039_agent_readonly_role.sql; DB applied=91, latest 2026-07-11
  → 0038 AND 0039 are drafts, NOT applied. REQUIRED_MIGRATIONS=91 consistent.
- Render: 29 asxos services — all not_suspended EXCEPT asxos-retrain-model-a=SUSPENDED (expected)
- freshness: prices.dt=2026-07-15 · signals.as_of=2026-07-15 · portfolio_snap.as_of=2026-07-15
  (UNFROZEN — recovered vs 07-13) · signal_outcomes=24,454 (post-fix run due Sun 07-19) ·
  regulatory_events=2 rows latest 2026-07-08 (STILL STARVED — Treasury dead behind green cron) ·
  macro_theses pending_review=0 · active theses=1
- job_runs (last 3d): ALL 18 recently-run jobs SUCCESS — check_cron_health 3/3, staleness 3/3,
  snapshot_portfolio 3/3 (recovered), sync_financial_statements SUCCESS 07-13 (PR #26 OOM fix
  exercised, orphan healed), compose_brief 3/3. The 07-13 error list is fully cleared except
  regulatory starvation. Healthchecks.io not probed this session.
```

_The 2026-07-16 wake's ONE THING: root-cause + fix the dead Treasury regulatory feed
(`jobs/ingest_regulatory.py`), riding behind draft PR #47's visibility layer._
