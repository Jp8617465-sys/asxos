# asxos current-state / live-readiness audit — 2026-07-04

**Session type:** read-only audit. No code changed, no migrations, no Render or Supabase state modified.
**Audited repo:** `jp8617465-sys/asxos` @ `6b99face` (main, merged 2026-07-04T05:08Z).
**Live state queried:** Supabase project `asx-portfolio-os` (`gxjqezqndltaelmyctnl`) and the Render account, both at ~05:30 UTC 2026-07-04.
**Starting hypothesis:** `docs/research/claude-fundamentals-audit-handoff-2026-07-04.md` (on unmerged asxos branch `claude/fundamentals-audit-report-2026-07-04`).

---

## 0. Headline findings

1. **The fundamentals handoff is already one session out of date.** `docs/session-handoff-2026-07-04.md` (merged to asxos main 05:08 UTC today) supersedes it on two P0 facts: (a) **Model A's signal reliability is formally in dispute** and blocks Phase 2c + any real capital decision (session-handoff-2026-07-04.md:10-81; CLAUDE.md:24 rule #11), and (b) the Render drift the handoff asked us to verify was **fixed last night** — 12 never-provisioned crons were created, all 29 render.yaml services now exist live (session-handoff-2026-07-04.md:127-134).
2. **The research store is no longer "applied-empty" but is only ~half-populated and the pipeline is stalled mid-chain.** Security master (4,370 rows) and corporate actions (41,456) populated on 2026-06-27; `sync_financial_statements` **crashed** that day (344 rows / 8 symbols, manually marked failed 2026-07-02); `derive_fundamentals_pit` ran against the partial data (43 rows); `compute_factor_scores` has **never run** — its cron was only created 2026-07-03T11:07Z. The factor panel join is **0 rows**; `eval_alpha_factors` cannot run meaningfully yet.
3. **The whole weekly research-store chain fires TODAY (Sat) 16:10–17:30 UTC.** It is the first run that includes `compute-factor-scores` and the first retry of the crashed statements sync. Tomorrow's `job_runs` is the real readiness verdict.
4. **Every repo-code claim in the fundamentals handoff verified true** (alpha_eval, factor engine, TC-20, monitor, JobMonitor, agent-scoping gap, purge/embargo not wired, no risk layer). Its line numbers have drifted in places; corrected below. One of its P2 items is already done: startup hard-fail tests now exist (`tests/test_api_main.py`).
5. **Healthchecks deadman coverage: 13 of 28 crons have no `HEALTHCHECK_URL_*` set live** (render.yaml expects one per cron). Blocked on the Healthchecks.io API key (pending James). The two watchdog crons (`check-cron-health`, `check-model-staleness`) have **never executed** — first scheduled runs are tonight 21:05/22:00 UTC.

---

## 1. Doc classification — current vs stale

| Doc | Classification | Key evidence |
|---|---|---|
| `docs/session-handoff-2026-07-04.md` | **CURRENT** (newest authority) | Merged 05:08Z today; Model A dispute :10-81; provisioning :127-134 |
| `docs/next-session-backlog.md` | **PARTIALLY STALE** | Top 2026-07-04 half current (P(-1) :5-14, provisioning update :181-194, agent-scoping :234-254, Healthchecks :202-208). Bottom 2026-06-28 half: TC-20 "unimplemented" :293-296 and the whole TC-20 kickoff §:343-392 are **stale** (TC-20 is shipped). :225 says "five" unescaped alert jobs; six exist |
| `CLAUDE.md` | **PARTIALLY STALE** | :125-127 "TC-20 … unimplemented" contradicted by `asxos/domain/tax/positions.py:117,155-170,191-213` + `tests/test_tax_positions.py:353-413`; :122 cites spec v1.4 (now v1.5). Rest verified current, incl. Model A quarantine rule #11 at :24 |
| `README.md` | **PARTIALLY STALE** | :11 and :41 claim "eight Render cron services / ten tables" vs 28 crons (render.yaml, `grep -c "type: cron"` = 28) and ~40 tables (CLAUDE.md:39); :22 still calls the phase-4 VPS doc "the chosen architecture" |
| `docs/foundation/phase-4-architecture-system-architect.md` | **STALE-HISTORICAL, unmarked** | :11 local Postgres "Loser: Supabase", :13 systemd "Loser: … Render cron", :15 Hetzner VPS "Loser: Render". No supersede banner anywhere in its 293 lines |
| `docs/foundation/spec/tax-alpha.md` | **CURRENT** | v1.5 header :3; TC-20 matrix row :418; changelog :469-502; matches `asxos/domain/tax/` exactly |
| `docs/research/research-store-schema.md` | Honest point-in-time, **now superseded by live DB** | :1-5 "applied-empty, all rs_* hold 0 rows" was true 2026-06-22; live DB now has 4 of 7 tables populated (see §3) |
| `docs/research/session-handoff.md` (2026-06-25) | **PARTIALLY STALE** | :82 "HEALTHCHECK_URL_* still empty" — 15 of 28 now set; row-count table :17-25 superseded by the 6/27 run |
| `docs/research/operating-model-architecture.md` | **PARTIALLY STALE** | Prescriptive core current (multiple-testing/deflated-Sharpe :70-73, :196 — still unimplemented in code); snapshots stale (:96 "factor_scores absent", :102 "research store barely exists" — both now built) |
| `docs/research/alpha-research-audit.md` | Evidence **current**, next-steps **stale** | Its 5d-edge/21d-reversal finding (:44-48, :95-97) is the basis of the live Model A dispute; its §8 open decisions (:162-164) have since been executed |
| `docs/backlog-test-coverage.md` | **HEAVILY PARTIALLY STALE** | :10-11 P0 (api/main, health route) now covered by `tests/test_api_main.py`; :16-24 P1 CLI block now covered by `tests/test_cli_*.py` (all use CliRunner). Residual P2 gaps (brief collectors, `clients/fred.py`, `brief/email.py`, `lots.py`) appear real |
| `docs/next-session-kickoff.md` | **STALE** | References old branch + open PR; :22 `REQUIRED_MIGRATIONS = 84` vs actual 90 (`asxos/api/main.py:15`) |
| `docs/audit-2026-06-27.md` | Dated audit, stale on TC-20 | :42, :54 claim `cost_base_div296` never read — now consumed by `positions.py` |
| `.claude/agents/tax-spec-conformance.md` | **STALE on TC-20** | :9, :28 "TC-20 … unimplemented"; also `.claude/agents/README.md:71` |
| `claude-fundamentals-audit-handoff-2026-07-04.md` | Starting hypothesis — **code claims all verified; state claims partially superseded**; unmerged (branch only) | See §2. Its "backlog accurate line-by-line" framing is overstated (TC-20 rows) |

---

## 2. Current-state correction table

| Item | Stale/old claim | Verified current reality | Evidence | Action |
|---|---|---|---|---|
| TC-20 Div 296 reset | "Unimplemented" (CLAUDE.md:125-127; backlog:293-296, 343-392; audit-2026-06-27.md:42,54; tax-spec-conformance.md:9,28) | Implemented + tested. Election path uses Div 296 gains, non-election falls back to ordinary NCG, depreciated-lot + 45-day warnings | `asxos/domain/tax/positions.py:117,155-165,166-170,191-210,213`; `tests/test_tax_positions.py:353-355,358,392` | **Docs update only** — do not reimplement |
| Research store | "Applied-empty" (research-store-schema.md:1-5) | 4/7 tables populated on 2026-06-27; chain stalled at statements crash; factors never computed | Live DB (§3); `migrations/0027_research_store.sql:34-155`; only later rs_* change is width-widening `0028` | Verify tonight's chain run; then fix statements sync |
| Alpha evaluation | Could be misread as missing | Exists exactly as described: effective-N, naive+effective t, deciles, calibration/Brier, liquidity split, thin-data warnings | `asxos/domain/research/alpha_eval.py:39-95,105-123,126-142,145-161,164-199,202-224,227-252,292-315`; tests `tests/test_alpha_eval.py:32-159` | Extend only; no rebuild |
| Deflated Sharpe / PBO / FDR | — | Absent from code; docs-only mentions | Only hits: `operating-model-architecture.md:70-73`, `phase-2-survives-the-fire.md:71` | P1 registry (below) |
| Factor engine | — | Built: sector-neutral 5 factors + value×quality, leak-safe `knowledge_date<=as_of` / `dt<=as_of`, winsorized z, idempotent upsert, `fs_v1` | `asxos/domain/research/factor_scores.py:46,50,71-79,212-213,229,232-266,273-290,292-309,319-390` | Populate, don't redesign |
| Paper monitor | Could be misread as missing | Full NAV/drawdown/vol/turnover/cost/bucket monitor exists | `asxos/domain/portfolio/monitor.py:147-153,176-188,200-258,329-395,499-543,562-607,615-700` | Build risk report instead |
| Systematic risk layer | — | **Does not exist**: no `asxos/domain/risk/`, no beta/covariance/correlation anywhere in `asxos/` | Repo-wide grep empty; risk = inverse-vol only (`volatility.py`); risk-blindness documented `.claude/rules/portfolio-conventions.md:190-204`; caps only in `constraints.py:35-56,64-114` | P1 design (read-only report first) |
| Render/IaC drift | "12 crons missing, 2 suspended pending FRED_API_KEY" (backlog:181-194) | **Resolved 2026-07-03/04**: 29/29 asxos services live; only `asxos-retrain-model-a` suspended (intentional — model frozen); FRED_API_KEY set on both consumers, both ran success 7/03. No Blueprint ever connected — render.yaml is manual-reconciliation IaC (`make check-drift` is an echo prompt, Makefile:59-60) | Render API live check §4; `session-handoff-2026-07-04.md:127-134` | Keep render.yaml + MCP reconciliation; no re-provisioning |
| Phase-4 architecture doc | Presented as "chosen" (README.md:22) | Historical/abandoned (VPS/systemd/local-Postgres), unmarked | `phase-4-architecture-system-architect.md:11,13,15,90,101,161-167,255` | Add supersede banner + fix README |
| Agent SELECT-only | Prompt-level only | Confirmed: **6 agents** hold `mcp__Supabase__execute_sql` (benchmark-performance-analyst, macro-economist, market-context-narrator, portfolio-coherence-reviewer, thesis-coherence-guard, thesis-milestone-monitor — each frontmatter line 4); **zero technical enforcement** (no GRANT SELECT / read-only role / `default_transaction_read_only` anywhere) | `.claude/agents/*.md:4`; `macro-economist.md:121-127`; backlog item at `next-session-backlog.md:234-254` (handoff's :39-59 was wrong) | P0 design read-only DB role before Phase 2c |
| Purge/embargo | Declared in config | Recorded as metadata only, never consumed by training | `asxos/domain/models/train.py:88-111` (plain expanding walk-forward, used :161); `training_config.py:51,67-68,10-14`; consumed only in `metadata.py:28,42,66`, `retrain_model_a.py:256` | P1 experiment-only split |
| Opportunity cost | Level screen | Confirmed: absolute >5% threshold, needs `current_net_expected_return` from producer | `asxos/domain/brief/collectors/opportunity_cost.py:8-13,16-24,39` | P1 producer spec |
| Startup hard-fail tests | "Lacks coverage" (backlog-test-coverage.md:10-11; handoff P2.2) | **Already done** — `tests/test_api_main.py` covers `_check_migration_drift` + lifespan success/failure branches | `tests/test_api_main.py:1-12`; guard itself `asxos/api/main.py:15,18-30,41-44` | Retire the backlog entry |
| Migration drift | Kickoff says `REQUIRED_MIGRATIONS=84` | Live `supabase_migrations.schema_migrations` = **90** = `REQUIRED_MIGRATIONS` (api boots; asxos-api deploy `live` on 6b99face). Caution: `public.schema_migrations` (87 rows) is a legacy table — not the gate's source | `asxos/api/main.py:15,22-24`; live SQL | Fix kickoff doc; always read the ledger |
| Alert-helper escaping | "Five alert jobs" (backlog:225) | **Six** unescaped `_send_alert` helpers interpolating raw text into `<pre>`; only `fallback_email.py` escapes | `jobs/check_us_positions.py:115,131`; `validate_price_data.py:31,47`; `check_model_staleness.py:33,49`; `check_au_positions.py:127,143`; `check_thesis_invalidations.py:103,118`; `check_cron_health.py:108,121`; escaping at `asxos/jobs/utils/fallback_email.py:46-51` | P2 shared escaped helper |
| config.py ↔ render.yaml healthcheck vocabulary | — | config.py missing fields for `compute_opportunity_cost` + `detect_theme_stages` (those jobs read `os.environ` directly; `extra="ignore"` at config.py:10 hides it); orphan `healthcheck_url_monitor_paper_portfolio` (config.py:70) has no cron | `asxos/config.py:48-75`; `jobs/check_us_positions.py:138,141` | P2 tidy |
| Hypothesis registry | — | Confirmed absent (no candidate/hypothesis tracking anywhere; legacy `signal_registry` being dropped in `0030:31-32`) | Repo-wide grep | P1 add registry field |
| Property testing | — | No hypothesis dep; dev deps = pytest/pytest-asyncio/pytest-cov/ruff/mypy only | `pyproject.toml:47-54` | P2 |
| Model A (NEW since handoff) | Handoff silent | Reliability disputed (5d decay / 21d reversal claim, unverified); retrain cron suspended, model frozen at 2026-05-21 (`retrain_model_a` failing since 2026-06-06 in job_runs); signals live-verified: 25,514 rows, 15 as_of dates, 2026-05-20→2026-07-02 | `docs/session-handoff-2026-07-04.md:10-81`; `CLAUDE.md:24`; live SQL | **P0: run the decay check; ask James for the ChatGPT audit** |

---

## 3. Research-store live readiness (queried 2026-07-04 ~05:30 UTC)

**Row counts:**

| Table | Rows | Notes |
|---|---|---|
| `rs_security_master` | 4,370 | matches ~2,382 active + ~1,986 delisted target |
| `rs_corporate_actions` | 41,456 | populated 6/27 (run took 1h39m) |
| `rs_financial_statements` | 344 | **8 distinct symbols only** (~0.3% of active universe) — crash artifact |
| `rs_fundamentals_pit` | 43 | latest `knowledge_date` 2025-09-26; derived from partial statements |
| `rs_factor_scores` | 0 | job never ran |
| `rs_index_membership` | 0 | known open gap (survivorship) |
| `rs_estimates` | 0 | not built |

**job_runs (research jobs — full history is a single chain run, Sat 2026-06-27):**

| Job | Status | Detail |
|---|---|---|
| `sync_security_master` | success | 4,370 rows, 16:10→16:20 UTC |
| `sync_corporate_actions` | success | 41,456 rows, 16:30→18:09 UTC |
| `sync_financial_statements` | **failure** | started 16:50; "prior run crashed (process never exited cleanly) — marked failed manually 2026-07-02" |
| `derive_fundamentals_pit` | success* | 42 rows at 17:10 — ran against partial statements (*success flag, garbage-in) |
| `compute_factor_scores` | **never ran** | Render cron created 2026-07-03T11:07Z; first scheduled run 2026-07-04 17:30 UTC |

**Factor panel / eval readiness:** join of `rs_factor_scores × prices` at `fs_v1` = **0 rows** → `jobs/eval_alpha_factors.py` fails loudly by design (`jobs/eval_alpha_factors.py:77-86`). **Do not run factor conclusions.** Prices themselves are current (max `dt` 2026-07-02, 1,896 symbols, ~18mo depth — the power ceiling in `docs/research/session-handoff.md:32-35` still binds).

**Today is the decisive day.** The weekly chain runs Sat 16:10/16:30/16:50/17:10/17:30 UTC — first run with `compute-factor-scores` included and first retry of the crashed statements sync. Two risks for tonight:
1. The statements crash root cause was diagnosed only as "process never exited cleanly"; the `--active-only` fan-out over ~2,382 names is the first-ever full-scale run (`docs/research/session-handoff.md:87-88` warned exactly this).
2. **Fixed-offset chain ordering is already broken in practice:** on 6/27 corporate actions ran 16:30→18:09, i.e. `derive_fundamentals_pit` (17:10) fired mid-upstream; a full statements fan-out will not finish in its 20-minute slot either, so tonight's PIT/factor runs will likely again consume incomplete upstream data. Dependency gating (or generous spacing) is a real defect to design for — not to hotfix tonight.

**Verification for tomorrow:** re-run the §7.1/7.2 queries from the fundamentals handoff; expect `rs_financial_statements` symbols ≈ active universe, `rs_fundamentals_pit` multi-year, `rs_factor_scores` > 0, then (and only then) run `eval_alpha_factors` read-only and capture its underpower warnings verbatim.

---

## 4. Render / Healthchecks readiness

**Services:** 29/29 asxos services exist (28 cron + 1 web `asxos-api`), matching `render.yaml:8-22` (28 × `type: cron` counted). The backlog's "12 missing" drift (`next-session-backlog.md:181-194`) was resolved 2026-07-03/04 (`session-handoff-2026-07-04.md:127-134`). `asxos-api` is `live` on the latest merge (6b99face); migration gate passes (ledger 90 = required 90).

**Suspended:** only `asxos-retrain-model-a` — intentional (Model A frozen at its 2026-05-21 snapshot pending the reliability dispute; `session-handoff-2026-07-04.md:43-49`). The ~25 other suspended crons in the account belong to the legacy `asx-portfolio-os` project — except `cleanup-conversations` (legacy repo) which is **still live daily at 02:30 UTC**, succeeding; flag to James whether it should stay.

**FRED_API_KEY:** present on `asxos-ingest-market-context` and `asxos-ingest-underlyings`; both ran successfully 2026-07-03. Resolved.

**Healthchecks deadman coverage — the remaining gap.** render.yaml expects a `HEALTHCHECK_URL_<JOB>` per cron (all 28); live env vars exist on only 15. **Missing on 13:** check-au-positions, check-cron-health, check-model-staleness, check-thesis-invalidations, check-us-positions, compute-factor-scores, compute-opportunity-cost, detect-theme-stages, ingest-market-context, ingest-underlyings, ingest-sentiment, track-signal-outcomes, validate-price-data. (Backlog says 12 at :202-208; `compute-factor-scores` was created after that count.) Blocked on the Healthchecks.io API key (pending James — `session-handoff-2026-07-04.md:163-164`). Direct Healthchecks.io verification was not possible from this session (no API key in the environment); coverage is inferred from Render env keys. JobMonitor behaves correctly without URLs (`asxos/jobs/utils/job_monitor.py:139-142` pings only when set; `job_runs` records regardless).

**Watchdogs have never fired:** `asxos-check-cron-health` and `asxos-check-model-staleness` (created 2026-07-03T12:03Z) show zero cron-run events and no `job_runs` rows; first scheduled runs are tonight 21:05/22:00 UTC. Until they run once, the system has **no operating deadman layer** (and 13 crons wouldn't ping Healthchecks even on success). Verify both tomorrow; `check_cron_health` alerts + raises RuntimeError on findings (`jobs/check_cron_health.py:4-10,26-39,108`).

---

## 5. Ranked next actions

**P0 — truth, safety, live-state**
1. **Model A decay check** (blocks everything downstream of `signals`): get James's ChatGPT audit, then run the Spearman rank-persistence check across day 0/+5/+21 on the 15 as_of dates (25,514 rows verified live). Per `session-handoff-2026-07-04.md:51-76`.
2. **Tomorrow: verify tonight's research-store chain** (§3 queries). If statements crash again, diagnose the fan-out; design dependency-gated chaining to replace fixed cron offsets.
3. **Doc-drift fixes** (pure doc edits, no code): TC-20 stale refs (CLAUDE.md:125-127; backlog:293-296 + delete/mark §343-392; tax-spec-conformance.md:9,28), README cron/table counts (:11,:41) + phase-4 "chosen" framing (:22), supersede banner on phase-4 doc, kickoff `REQUIRED_MIGRATIONS`, retire covered entries in backlog-test-coverage.md.
4. **Agent DB role scoping** (backlog:234-254): read-only Postgres role / MCP role selection for the 6 execute_sql agents before Phase 2c (Phase 2c is anyway blocked on #1).
5. **Healthchecks:** 13 URLs + API key (needs James); confirm watchdogs' first runs tonight.

**P1 — decision-grade math (unchanged from handoff, all preconditions verified)**
6. Read-only systematic risk report (`asxos/domain/risk/` — nothing exists today).
7. `DecisionEvidence` layer spec (no orders).
8. Purged/embargoed split, experiment-only (`purge_embargo_days` currently decorative).
9. Hypothesis/candidate registry (deflated-Sharpe/PBO/FDR all absent from code).
10. Opportunity-cost delta producer (`current_net_expected_return`).

**P2 — tests/correctness**
11. Property-testing layer (add hypothesis; invariants list in handoff §P2.1 stands).
12. Shared escaped alert helper (six unescaped `_send_alert`s — see §2).
13. Tax-lot objective research (still local post-discount-gain only, `lots.py:80,87-88,100-104,128-135`).
14. ~~Startup hard-fail tests~~ — already done (`tests/test_api_main.py`).

**P3 — polish**
15. config.py healthcheck field vocabulary sync (two missing, one orphan).
16. CI realism: keep the local pre-push hook framing (`scripts/hooks/pre-push:5-9,56-60`); don't claim CI blocks merges.

---

## 6. Do-not-do list (reaffirmed + extended)

All items from the fundamentals handoff §10 remain valid: do not rebuild alpha_eval / research-store schema / factor_scores / monitor / JobMonitor; do not reimplement TC-20 (verified correct); do not rewrite in Go/Rust/C++; do not change the allocator before risk/evidence layers; do not turn evidence labels into orders; do not treat current-only index membership as historical ASX200; do not call factor results decision-grade before effective-N/liquidity checks pass.

Added by this audit:
- **Do not use Model A output or anything downstream of it for real capital decisions** until the reliability dispute is resolved (CLAUDE.md non-negotiable #11).
- **Do not run `eval_alpha_factors` conclusions before `rs_factor_scores` is populated** (join is 0 rows today; job fails loudly by design).
- **Do not re-provision Render services or re-apply migrations** — 29/29 exist; ledger is at 90 (`public.schema_migrations` (87) is a legacy table, not the gate's source).
- **Do not trust `derive_fundamentals_pit`'s "success" status** from 6/27 — it ran on crash-truncated statements; a success flag is not data completeness.
- **Do not leave the fundamentals handoff unmerged** — it lives only on `claude/fundamentals-audit-report-2026-07-04`; merge or archive it, or it becomes the next lost/stale artifact (this repo has already lost one handoff that way — `docs/research/session-handoff.md:6-9`).
