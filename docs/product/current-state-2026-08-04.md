# asxos Current State — full project audit (2026-08-04)

**Status:** current (point-in-time audit; the living reconciliation remains `roadmap-state.md`)
**Scope:** whole repo — concept inventory (engineering + financial), current state wired
against `north-star.md`, deployment/pipeline audit, roadmap-stack reconciliation
**Trigger:** James, 2026-08-04 — "unpack this entire project to ensure we are on track"
**Owner:** arbi wake session (`/arbi`, interactive); humans may edit freely
**Superseded by:** N/A (supersedes nothing; cites the governing doc for every area)

Every figure below traces to a live probe run this wake (git, GitHub, Render REST,
`supabase-ro` SQL, Routine list) or a cited file line. Probe gaps are stated, not filled in.

---

## 1. Live-state snapshot (probed 2026-08-04)

- **Git:** `main` @ `9d442de` ("/arbi-close 2026-07-24 + REQUIRED_MIGRATIONS 95 after 0041
  (#69)"). **Zero commits in ~11 days.** Audit branch `claude/project-audit-roadmap-ey3gem`
  even with main.
- **Open PRs:** exactly one — **draft #70**, "investment-engine implementation dossier"
  (opened 2026-07-25, 157 files, +39,974/−88). See §6.
- **DB:** applied migrations = 95 = `REQUIRED_MIGRATIONS` (`asxos/api/main.py:15`) — 0041
  applied; consistent. Content: 13 theses · 1 theme · 4 macro theses (3 approved) ·
  0 unacted agent runs.
- **Freshness:** `prices.dt` = `signals.as_of` = `portfolio_daily_snapshots.as_of` =
  **2026-08-03** — the data plane ran green straight through the git-idle window.
  `regulatory_events` = 2 rows (still starved; RBA-only by design since the Treasury/ATO
  retirements).
- **Render:** 29 services; only `asxos-retrain-model-a` suspended (expected, rule #11).
- **Two new bugs, both previously unseen** (details §5): `derive_fundamentals_pit` failing
  since ~07-30; the 7a daily-brief Routine dead since 07-18.
- **Probe gaps this wake:** sandbox pytest not run (CI `full-check` is authority — green at
  #69); Healthchecks.io not probed.

## 2. Concept inventory — software engineering

**Counts on disk:** 41 migrations · 120 test files (118 `test_*.py`) · 15 docs/proposals ·
35 docs/product files (+ `memory/`, `rubrics/`, `runbooks/`) · 25 subagents · 31 slash
commands · 5 rules · 5 hooks.

**Architecture.** Three-plane topology: one FastAPI web service + Supabase Postgres 16 (only
datastore) + 28 single-purpose Render crons (`render.yaml`). Hard-fail startup — the ASGI
lifespan raises on any dependency-init failure, incl. the `REQUIRED_MIGRATIONS` drift gate
(`asxos/api/main.py`); encodes postmortem lesson 1 (`docs/foundation/phase-b-failure-postmortem.md`).
18 bounded domain subpackages under `asxos/domain/`; a separate 11-adapter ingestion layer
(`asxos/ingestion/`) so jobs never call vendors directly; the `asx` CLI (18 command modules)
as primary UI; thin `jobs/*.py` entry points wrapping `JobMonitor`.

**Data/DB engineering.** Plain-SQL numbered migrations, applied via Supabase MCP (no runner);
`NUMERIC(18,6)` on every monetary/statistical column from day one; Postgres `BEFORE UPDATE`
governance audit triggers enforcing transition+audit-row atomicity in the DB itself
(migrations 0034/0036); the `asxos_agent_ro` read-only role (0039) as the physical backstop
for agent SELECT-only; governed read surface via views (`current_holdings`,
`governed_active_*`). Standing hazard: asxos is a ~43-table tenant in a ~165-table shared
Supabase project — mandatory `pg_depend` pre-apply check (`docs/db-shared-project-audit-2026-06-28.md`).

**Reliability/ops.** `JobMonitor` async context manager (records `job_runs`, pings
Healthchecks deadman per job, re-raises — never swallows); three-state job outcome
success/blocked/failure with `UpstreamBlocked`→blocked to avoid alert fatigue;
`check_cron_health` meta-job (detects stuck/consecutive-failing jobs, emails via Resend);
`render.yaml`-as-IaC reconciled by `make check-drift` against the live Render REST API
(postmortem lesson 2); dark-launch env gates with a written exit plan (the sanctioned
exception to "no feature flags"); fail-loud rule #10 throughout; irreplaceable-only backup
(`scripts/backup_irreplaceable.sh`); deployment-surface tests (`test_cron_pool_init`,
`test_render_backup_build`) closing the "local-correct, deployed-broken" gap.

**Agent/AI engineering.** 25 subagents, advisory-by-default (only `refactoring-expert` +
`technical-writer` mutate files): 11 dev-side, 2 finance-conformance, 5 investment-analysis,
3 discovery, 3 program-management (`arbi`/`arbi-red-team`/`guilfoyle`) + `reversible-work-builder`.
arbi as bounded constitutional operating authority — governor(James)/controller(arbi) split,
two-axis I0–I6 / P0–P6 permission ladder with a "runtime enforcement honesty" section
(`docs/product/arbi-*.md`). Mechanical gates: `review-gate.sh` (diff-hash-keyed commit
marker), `unattended-guard.sh` (fail-closed default-deny when `ARBI_UNATTENDED=1`),
`authority-guard.sh` (always-on; it blocked a Bash call during this very audit),
`push-guard.sh`/`pr-draft-guard.sh` (deny-only, draft-PR ceiling). Git-native memory:
`/arbi-dream` → candidate PR → `/arbi-promote` behind CODEOWNERS. Slash-command fan-out
pattern (subagents can't spawn subagents, so `/pm-review`, `/discover-macro`, `/arbi` run
the fan-out in the main loop). Agents never write the DB — proposals become rows only via
human-run CLI with `agent_runs`/`agent_evidence`/`governance_events` audit trail.

**Quality.** Two CI lanes (`full-check` = ruff+mypy+full pytest; `targeted-ml-tests` fast
lane) + a comment-only `pr-review-agent`; `make check` mirrors CI locally; the 3-agent
review loop (security-engineer → refactoring-expert → technical-writer) armed by the review
gate; documented sandbox test gaps with the re-derivation command as the only authority
(enumerated lists are forbidden — they rotted repeatedly); "load-bearing tests only" policy
(~400 tests each defending a named failure class); spec-first domain logic (tax code cites
`tax-alpha.md` section numbers; tests named by TC-ID).

**Other gates.** Secret redaction at source and sink (`asxos/redaction.py`, CWE-532/209);
`defusedxml` for RSS; the s766B personal-use firewall as a literal runtime gate
(`ASXOS_PERSONAL_USE=1` required, env var ships in the same change as the gated job); rule
#11 as an evidence-backed engineering kill-switch; `docs/README.md` as the docs
source-of-truth map ("trust the map, fix the doc"); auto-attaching path rules; the numpy
psycopg2 adapter block (#9).

## 3. Concept inventory — financial / investment management

<!-- FILLED FROM EXPLORE SWEEP -->
_(pending sweep result)_

## 4. Current state wired against the North Star

`north-star.md` defines the product as a morning briefing + thesis discipline system —
"disciplined alpha-seeking faithful to James's own thinking" — ranked by the three-layer
moat, with the ML engine shelved (2026-07-11) and the model-independent moat as the product.

| North-star element | Source | State today (probed/cited) | Honest verdict |
|---|---|---|---|
| **Moat 1 — morning ritual** (brief as "his own thinking, sharper") | `north-star.md:60-63,84-85` | `compose_brief` SUCCESS daily (08-03). But: portfolio section dark (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`), news/sentiment render dark, governed macro theses reach **no surface** (dev-loop #9 unbuilt), and the 7a daily arbi brief has been **dead since 07-18** | **Partially delivered.** The brief that ships is thinner than what the system computes. The gap is render/surfacing, not compute — the standing "surfacing gap" finding (`roadmap-state.md` portfolio-team-visibility) still holds |
| **Moat 2 — discipline scaffolding** | `north-star.md:64-66` | Discipline evaluator merged (#29) + rendered in the brief (#41/#44); `check_thesis_invalidations`, `check_au_positions`, `check_us_positions`, `detect_theme_stages` all SUCCESS 08-03; thesis governance triggers live | **Live and running.** Strongest layer. Content thin (13 theses, 1 active) but the machinery is real |
| **Moat 3 — theme stewardship** | `north-star.md:67-69` | 1 theme · 4 macro theses (3 approved, first governed macro content 07-21/22) · **zero ETF/LIC coverage** · discovery agents (macro-economist, sector-screener, theme-researcher) wired read-only · Layer A falsifier-scoring **inert** (cron never wired — zero `job_runs` rows ever) | **Machinery built, content starved.** The universe→segment→thesis narrowing layer (coverage framework proposal) remains the gap |
| **Success: brief un-dark-launched** | `north-star.md:84-85` | Both dark gates still `0`; both expire **2026-08-31**; the 4-week paper-trade window has **never started** → cannot complete before expiry | **Not met, and now time-inconsistent** — needs a fresh decision, not waiting |
| **Success: discipline events reach James before they cost money** | `north-star.md:86-89` | Position/thesis monitors ran daily. BUT `check_cron_health` was correctly RED for 7 straight days (07-28..08-03) over `derive_fundamentals_pit` and **nobody saw it** — the 7a Routine (the channel) was dead | **Failed at the meta level this fortnight.** This is the HUBS failure class recurring one level up: the alert existed; the delivery channel didn't. Same lesson as 07-15 (silent Routine death) — now twice |
| **Success: Decimal-exact, cited numbers** | `north-star.md:90-91` | Decimal-only domain convention enforced (`portfolio-conventions.md`); NUMERIC(18,6) throughout; brief-truth fix (#68) removed the false −75.7% | **Met by standing convention** |
| **Non-negotiable: rule #11 (Model A quarantine)** | `north-star.md:98-108` | Mechanically enforced: `build_portfolio` BLOCKED 08-01 (correct), `retrain_model_a` suspended, allocation gate requires `approved_for_allocation` | **Holding.** PR #70's "Model A retirement plan" must be conformance-checked against it before any merge (§6) |
| **Non-negotiable: s766B firewall** | `north-star.md:109-115` | `ASXOS_PERSONAL_USE` gates on CLI + jobs (R12/R14 closures, #33/#59); first gated `compute_opportunity_cost` run SUCCESS 08-01 — the env-drift fix held | **Holding** |

**One-line verdict:** the model-independent product the north star now names *is* mostly
built and its data plane is healthy — but its two delivery channels (the enriched brief and
the daily arbi read) are respectively dark-gated and dead, so almost none of it reaches
James daily. The binding constraint is **surfacing + operating discipline, not compute.**

## 5. Deployment & data-pipeline audit

**What "deployed" looks like today:** 29 Render services (cron-dominated) against Supabase
Postgres, config-as-code in `render.yaml` (drift-checked via `make check-drift`), FastAPI
service with hard-fail startup (`REQUIRED_MIGRATIONS` gate), Resend email, Healthchecks.io
deadman. Managed exclusively via the Render REST API — no dashboard edits.

Pipeline ledger (latest `job_runs` per job, probed 2026-08-04):

| Lane | Jobs | State |
|---|---|---|
| Ingestion | sync_prices, sync_universe, sync_fundamentals, sync_financial_statements, sync_corporate_actions, sync_security_master, ingest_news, ingest_sentiment, ingest_market_context, ingest_underlyings, ingest_regulatory, validate_price_data | **All SUCCESS** (08-01..08-03 per cadence). Regulatory is structurally thin (RBA-only; 2 rows) — re-adding a second source is a named backlog item |
| Derived / research | compute_factor_scores, track_signal_outcomes, compute_opportunity_cost | SUCCESS. `compute_opportunity_cost` first gated run green 08-01 |
| Derived / research | **derive_fundamentals_pit** | **FAILING since ~07-30 — `TimeoutError`, 3+ consecutive** (the only red pipeline). Root-cause not yet diagnosed; owner: next session, `performance-engineer` route (timeout class) |
| Signals (dormant by policy) | generate_signals (passive monitor) SUCCESS; retrain_model_a SUSPENDED; build_portfolio **BLOCKED (correct, rule #11)** | Working as designed |
| Portfolio & brief | snapshot_portfolio, compose_brief | SUCCESS daily through 08-03 |
| Monitors | check_model_staleness, check_au_positions, check_us_positions, check_thesis_invalidations, detect_theme_stages: SUCCESS. **check_cron_health: RED 7 consecutive days** — correctly flagging derive_fundamentals_pit | The monitor worked; the human channel didn't |
| **Built but never deployed** | `jobs/score_macro_theses.py` (Layer A, migration 0041 applied) | **Zero `job_runs` rows ever — cron confirmed unwired.** Needs `render.yaml` entry + push + `make check-drift` (James's authorization, carried from 07-24) |
| Ops channel | 7a daily arbi brief Routine (`trig_01BA3VmfzoRMtjKnt6XNpgPH`) | **DEAD — last fired 2026-07-18**, `next_run_at` stuck 07-19. Second silent-stop occurrence (first 07-15). The secperf write-loop Routine is stalled the same way |

**"Getting this project deployed" therefore concretely means, in order:** (1) fix
`derive_fundamentals_pit` and clear the health-check red; (2) revive (or deliberately
retire) the 7a Routine so red streaks can't run unseen again; (3) wire the one built-but-
unscheduled cron (`score_macro_theses`); (4) re-decide the two 2026-08-31 dark-launch
expiries; (5) build the macro-brief render layer so deployed compute reaches the reader.
Not more services — a working readout for the ones that exist.

## 6. Roadmap-stack reconciliation (including PR #70)

The repo now carries **four planning schemes** — BUILD_GUIDE M1–M12 (done; static manual),
the executable-roadmap PR1–8 (PR1 landed; PR2 substantially satisfied via `supabase-ro` +
the #65 frontmatter repoint), governance Phases 0–4 (through 2b done, 2c reframed
model-independent), and the live dev-loop queue in `roadmap-state.md` (#9 render layer,
#10 instrument-selector) — reconciled by `roadmap-state.md`, whose whole mandate is to be
the single cross-walk.

**Draft PR #70** ("investment-engine implementation dossier", opened 2026-07-25, 157 files,
+39,974/−88) would add a fifth: a 12-week / 14-initiative programme under
`docs/programs/investment-engine/` (36 versioned contracts, 38 schemas, 42 golden fixtures,
a validator, 8h/12h mission recipes, sprint gates, a "Model A retirement plan" via
M-A2/M-A3 missions). Its programme content may well be valuable. But it **also edits nine
authority docs** — CLAUDE.md, `docs/README.md`, `roadmap-state.md`,
`next-session-backlog.md`, `arbi-operating-backlog.md`, `cleanup-backlog.md`,
`dark-launch-exit-plan.md`, `guards-backlog.md`, `backlog-test-coverage.md` — under a
"canonical-vs-legacy precedence" claim.

**arbi's ruling-shape (this wake):** that makes #70 a **supersession attempt on the
authority ladder, not just a proposal.** Under `arbi-authority.md`, branch-only state never
outranks main: until James rules, `roadmap-state.md` on main remains the current authority
and `docs/programs/` does not exist as truth. The #64 precedent applies verbatim
(`decision-log.md`): assess and **clean-extract the net-new delta; never force-merge the
stacked whole.** Two specific checks before any disposition: (a) per-file reconciliation of
the nine authority-doc edits against main @ `9d442de`; (b) conformance of its "Model A
retirement plan" with rule #11 as **standing policy** — retiring dormant runtime can be
consistent with the shelf, but nothing may soften the quarantine or the pre-registered
decay bar (`north-star.md:98-108`, `ml-engine-shelf-2026-07-11.md`).

**Repo-organisation finding:** the docs sprawl is itself the risk. Header-rot is live
(`docs/README.md` last verified 07-05; `next-session-backlog.md` self-declares half-stale),
and #70 is simultaneously a symptom of that sprawl and — if merged unreconciled — an
accelerant (a fifth scheme claiming precedence). The fix is a **precedence ruling, then
pruning under it** — not another document.

## 7. arbi's brief (2026-08-04, verbatim verdict block)

STATUS · WHAT CHANGED · NEW BUGS · THE PICTURE as delivered by the `arbi` agent this wake —
recorded in full in the session log; operative conclusions:

- **NEXT ACTIONS (ranked):**
  1. **THE ONE THING — triage draft PR #70**: fetch `agent/investment-engine-dossier`,
     reconcile its nine authority-doc edits against main file-by-file (net-new /
     superseding-with-evidence / contradicting-main), assess `docs/programs/` as a
     programme proposal, check the Model A retirement plan against rule #11, deliver one
     MERGE / CLEAN-EXTRACT / CLOSE verdict for James. Owner: main loop consulting
     `system-architect` + `technical-writer`; `arbi-red-team` gates the verdict.
  2. **Deployment-truth pass**: fix `derive_fundamentals_pit`; revive the 7a Routine;
     wire the `score_macro_theses` cron (James's authorization).
  3. **Dev-loop #9** — the macro-brief render layer — once #70's precedence is settled
     (it touches the same doc surfaces; building first risks collision).
  4. **Draft the 2026-08-31 dark-launch re-decision** (portfolio brief + paper-trade
     evaluator) for James's ruling.
- **DECISIONS NEEDED (James):** #70 disposition · CBA thesis one-word retire confirm
  (carried since 07-16) · RLS/agent-DB-role posture · `score_macro_theses` cron
  authorization · paper-trade window vs the 08-31 expiries · `asx news signoff` word.
- **WHAT NOT TO DO:** merge #70 wholesale; treat `docs/programs/` as current truth while
  branch-only; let #70's retirement plan touch rule #11/decay-bar/`approved_for_allocation`
  semantics; act on Model A output for capital; re-run the resolved decay check; count dark
  surfaces as delivered; let the 08-31 expiries roll over silently.

## 8. Bottom line

The project is **on track on substance, off track on delivery and operating rhythm**: the
model-independent moat named by the north star is built and its pipelines are healthy, but
(a) an 11-day idle window let a pipeline failure run unseen because the watchdog channel
had silently died, (b) the newest and largest piece of planning work (PR #70) sits
unreconciled against the authority stack it tries to replace, and (c) the two gates that
would let James actually *receive* the product (dark-launch brief sections; macro render
layer) are respectively expiring un-exercised and unbuilt. The queue in §7 addresses these
in leverage order.
