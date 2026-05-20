# Phase 1 — Forensic audit of ASX Portfolio OS

This is a diagnostic of what is actually in this repository, what runs, what doesn't, and why. The framing is honest: where the code is fine, it says so; where the code is broken, it names the file and the line. The founder has decided to rebuild, but a credible rebuild starts from an accurate picture of what's being left behind.

## Headline

The codebase is not as catastrophically broken as a casual look suggests, and it is not as healthy as the documentation suggests. There is roughly fifteen sprints' worth of genuine domain code — feature engine, signal generation, SHAP, CGT and Division 296, screening, scenarios — wrapped in three layers of debt that prevent it from running:

1. Infrastructure drift: the checked-in `render.yaml` describes a system that no longer matches what is actually configured on the Render dashboard. Several crons are defined in YAML but were never created on the platform.
2. Graceful-degradation startup: every dependency initialisation in `app/main.py` lifespan downgrades failure to `logger.warning(...)` and continues. The API returns `"ASX Portfolio OS API is running ✅"` from `/` even when the asyncpg pool, model cache, Redis bridge and context consumer have all failed to initialise.
3. SaaS scaffolding overhead: of 36 feature directories under `app/features/`, only about a third hold genuine domain logic. The remainder are auth, users, notifications, admin, billing-adjacent, and other multi-tenant infrastructure that exists because the project once aspired to be a B2B SaaS.

The founder's instinct to start over is correct. Not because the code is bad — most of the domain code is good — but because the system shape (multi-tenant, multi-user, public-facing, regulatorily-cautious SaaS) is a poor fit for the actual goal (single-user personal investment intelligence OS). Carrying the domain modules forward into a clean, smaller repo will produce a working system in a fraction of the time it would take to repair the existing infrastructure.

## Why nothing runs in production

The founder reports: "Render backend doesn't run, background jobs don't run, signals don't load, no user-facing function works." Below are the verified root causes, ordered by severity.

### Graceful-degradation startup masks every failure

`app/main.py` lifespan, lines 165–300, wraps six dependency initialisations in try/except blocks that downgrade failure to `logger.warning(...)` and continue:

- Line 176–186: asyncpg pool init. On failure, logs `"asyncpg pool init failed (non-critical)"` and proceeds. Every async repository now silently has no pool.
- Line 192–225: `stock_universe` view creation. Tolerates the table-vs-view ambiguity by emitting a warning and skipping.
- Line 228–249: model cache warmup. Logs `"Model cache warming: %s/%s models loaded (some may not exist yet)"` and continues even if zero models loaded.
- Line 252–262: Redis event bridge init. Warning, continue.
- Line 266–286: Redis Streams bridge + context refresh consumer. Warning, continue.
- Line 292–300: live price background loop. Warning, continue.

The API root endpoint returns a 200 with `"ASX Portfolio OS API is running ✅"` even when all six subsystems are dead. `/health` does not probe these dependencies. This is the single most important issue in the codebase: the system actively lies about its own health. Any operational signal coming from the platform is unreliable until this is removed.

The fix is straightforward — convert warnings to hard failures for anything that must be present for the app to serve traffic — but the cumulative effect of this pattern is that the founder cannot tell, from outside, what is actually broken inside.

### `render.yaml` describes a system that doesn't exist on Render

The checked-in `render.yaml` contains explicit comments at lines 421 and 440 acknowledging:

```
# Replaces: asx-market-news + asx-holdings-news (two separate Sprint 16 crons
# that were defined in render.yaml but NEVER created on Render).
...
# This cron was defined in render.yaml but NEVER created on Render.
```

Affected crons include `news-ingestion`, `earnings-sync`, and `semantic-maintenance`. The author of these comments understood that `render.yaml` is not actually pulled by Render — services and crons are created manually through the dashboard, and the YAML file has drifted into being aspirational. Verifying which of the 25+ crons in `render.yaml` actually exist on Render requires logging into the dashboard manually. The codebase has no source of truth.

This is the second most important issue, and it is the reason "Render backend doesn't run" can be true at the same time as "the daily signals pipeline code is correct and recently fixed." The code is fine. The platform hasn't been told.

### Job env-var distribution is inconsistent

Each Render cron inherits its own environment variable set. `FRED_API_KEY` is declared for `macro-data` but not for jobs that incidentally call macro code. `VOYAGE_API_KEY` is declared for `semantic-maintenance` only, but `embed_conversations.py` needs it from other contexts. `ALERT_WEBHOOK_URL` and `ALERT_EMAIL` are referenced in `jobs/utils/job_monitor.py` but missing from `render.yaml`. When a cron fires in the wrong context, it fails with a `None`-derived 401 or a missing-env exception, and the failure is invisible because there's no central job dashboard.

Roughly 60 distinct environment variables are required across `app/` and `jobs/`. The `render.yaml` declares fewer than 40, distributed unevenly.

### Job database connections have no retry

`jobs/job_utils.py:24–35` defines `get_db_connection()` as a single attempt against `DATABASE_URL`. If the Supabase pooler is reloading, if a connection limit is hit, if auth has rotated and Render hasn't picked up the new value, the job dies immediately with SystemExit and Render only retries at the next scheduled boundary — which for most jobs is 24 hours away.

This is fixable, but it interacts badly with the previous point: when env vars are misconfigured for a given cron, the failure looks the same as a transient DB blip, and there is no telemetry to distinguish them.

### Model artefacts may not be present on cold boot

`app/main.py:228–249` preloads `model_a v1_5` classifier and regressor. The directory `models/` contains `.txt` and `.json` artefacts for v1_5, but Render's deploy layer can serve a build that does not include them depending on caching and on whether `models/` is correctly tracked. When that happens, `/signals/*` endpoints 500 with a model-not-found error even though the API booted successfully — because the warmup was a warning, not a hard failure.

### What is NOT actually broken (corrections to a casual reading)

Two claims that surface in any quick audit of this repo are false on verification:

- `jobs/load_macro_data.py` exists. It is not a missing module. The macro pipeline at `jobs/run_macro.py` will run end-to-end if FRED_API_KEY is present, even though its docstring describes an older multi-cron arrangement.
- `scripts/cron_daily_signals.py` runs the full A→B→D→Ensemble pipeline (lines 49–131). The script's own comment at line 89–92 records that Model D previously ran as a standalone cron after the ensemble was already computed, which meant D never actually contributed to the daily ensemble. That was fixed; the fix is in the repo. Whether the corresponding Render cron is configured to run the wrapper or to call `generate_signals.py` directly is a separate question, and one that can only be answered by logging into Render.

This matters for the rebuild conversation. The story is not "the code is rotten." The story is "the code has been quietly improving while the operational state has been quietly decaying." A new repo will not inherit the rot, but it must not lose the improvements.

## What is implemented vs scaffolded vs broken

`app/features/` contains 36 directories. Roughly grouped:

**Genuine domain logic, production-shaped, worth carrying forward.** These have real computation, test coverage, and the structure of code that has actually been used.

- `ml/` — feature engine (`feature_engine.py`) with 8 feature groups exactly matching `models/model_a_v1_5_features.json`. Same code path in training and inference, which is non-trivial to get right and is the single hardest thing in the repo to replace.
- `models/` — retraining service with ROC-AUC gate of 0.65, 5% degradation ceiling, 1k-sample minimum, blue-green deploy.
- `signals/` — `signal_service.py`, `investment_case_service.py` (~775 lines, rule-based narrative from SHAP), `consensus_divergence_service.py`, `portfolio_signal_service.py`.
- `screening/` — `screen_match_engine.py` translates JSON rules to parameterised SQL WHERE; `screen_query_service.py` joins the wide `model_a_features_extended`; `stock_intelligence_service.py` assigns K-Means archetypes.
- `tax_alpha/` — `cgt_alert_service.py` with real 12-month discount tier logic (50% individual, 33.33% super accumulation, 0% pension); `division_296_monitor.py` with $3M / $10M thresholds and the 2026-07-01 commencement. The foreign-holdings v3 design captured in memory extends to lots, RBA FX, upfront Div 83A, and 12 scenario groupings.
- `scenarios/` — `monte_carlo_service.py` (~725 lines), historical precedent lookup, scenario orchestration. Multi-variate return simulation with correlation matrices.
- `portfolio/` — `risk_service_v2.py`, `tax_aware_service.py`, `what_if_service.py`. Sharpe, max drawdown, tax-drag rebalancing.
- `transactions/` — categorisation, cost-basis, bank parsing, budget.
- `brief/` — deterministic rules engine for the morning brief. Not LLM-dependent. Conceptually the most defensible piece of the user-facing surface.

**Scaffolded, partially-wired, or aspirational.** These have routes and service files but are either incomplete or wrap an external service that may or may not be reachable in any given environment.

- `coach/` — semantic memory via Voyage AI embeddings (1024-dim, HNSW index). Real infrastructure dependency. The label-extraction half is good; the conversation-history half is scaffolding.
- `assistant/` — Anthropic SDK dispatch, SSE streaming. Live LLM integration. Useful but couples the system to two external dependencies.
- `explainability/` — SHAP persistence service exists in design notes; the actual computation lives in `model_a.py` and `jobs/generate_signals.py`. The feature directory is mostly stub.
- `goals/`, `context/`, `health/`, `health_score/` — domain-adjacent. Goal gap computation is real; goal versioning is scaffolding.
- `alerts/` — rule evaluation is domain. Multi-channel dispatch is plumbing.

**SaaS plumbing, no domain value, discard.**

- `auth/` and `app/auth.py` — login, JWT, token_version revocation, the forgot-password and reset-password pages. None of this exists in a single-user system.
- `users/` — profile, settings, RBAC.
- `admin/` — admin dashboards, manual job triggers.
- `notifications/` — multi-channel routing, quiet hours, subscription preferences.
- `analytics/`, `logging/`, `monitoring/`, `pipeline/` — observability and ops scaffolding. Replace with the simplest thing that works.
- The Next.js frontend in its entirety. Five-thousand-plus tests. Not until the new backend produces something worth surfacing.

The honest count: of 36 feature directories, perhaps 10–12 hold the domain knowledge worth porting. The rest is SaaS architecture.

## Migrations: what they tell us about schema decisions

122 SQL files in `migrations/`. The early migrations are clean and represent durable design decisions; the later migrations are repair work.

- 001–005: foreign keys, timestamp standardisation, performance indexes, universe view. Solid.
- 006–019: fundamentals, notifications, subscriptions, user preferences, performance snapshots, earnings calendars. Normalised, low churn.
- 020 onwards: drift becomes visible. Migration 020 fixes an FK pointing at a `users` table that did not exist (the actual table is `user_accounts`). This is a schema-design mistake that survived to a deployed migration. Migration 035 widens `NUMERIC(10,6)` columns in `model_validation_results` because the training dataset grew past the original precision. Migration 0101 promotes `signals.price` from `DOUBLE PRECISION` to `NUMERIC(18,6)` for stability.

The lesson, which matters for the new repo: use `NUMERIC(18,6)` for every monetary or statistical column from day one. Verify FK targets exist before writing the migration. The first 19 migrations are worth reading line by line as a draft of the new schema. Everything after migration 020 should be examined for whether it's solving a real domain problem (some are) or correcting an earlier mistake (most are).

## Jobs: what runs and what is dead

98 files in `jobs/`. The production-shaped jobs:

- `generate_signals.py` (~739 lines). Vectorized prediction, SHAP via Tree SHAP (`pred_contrib=True`), psycopg2 numpy type adapter registered at the top of the file, JobMonitor wrapping. This is one of the more impressive single files in the repo.
- `generate_signals_model_b.py`, `_c.py`, `_d.py`. Analogous shape.
- `generate_ensemble_signals.py`. Orchestrates the four-model ensemble with proportional weight redistribution if a model is missing.
- `retrain_model_a.py` (~543 lines). LightGBM classifier and regressor, 36-month lookback, TimeSeriesSplit cross-validation, validation gates, auto-rollback. Production-hardened.
- `build_extended_feature_set.py`. The 760-day lookback wide-feature build. Uses `if_exists='replace'` for a full rebuild each run.
- `extract_shap_thresholds.py` (~699 lines). SHAP zero-crossing detection feeding screening rules.
- `sync_live_prices_job.py`, `load_fundamentals.py`, `sync_earnings_calendar.py`, `sync_etf_holdings.py`. EODHD ingestion.
- `backtest_screening_rules.py`. Walk-forward validation.

The dead-or-near-dead:

- `discover_archetypes.py` — exploratory K-Means run.
- `aggregate_logs.py` — one-off maintenance.
- `cleanup_expired_guests.py` — housekeeping for a multi-tenant feature that does not need to exist.
- A handful of `backfill_*` jobs — valuable for bootstrapping the new repo, dead in steady state.

Roughly 85 active, 13 dead. The active set is concentrated in signal generation, retraining, and EODHD ingestion. These are the parts of the jobs directory to read carefully before designing the new job runner.

## Domain knowledge encoded in `.claude/` and docs

The `.claude/` directory in this worktree contains durable knowledge that is independent of the running system and worth carrying verbatim:

- `.claude/commands/` — 20 markdown command files, including 7 domain commands (`signal-pipeline`, `model-experiment`, `regime-detection`, `tax-optimise`, `dashboard-component`, `feature-add`, `prompt-compose`) and 13 lifecycle / ops / incident commands. These are prompt assets, not code. They survive the rebuild as-is.
- `.claude/rules/` — 5 rule files (`api-conventions.md`, `ml-conventions.md`, `screening-conventions.md`, `coach-conventions.md`, `job-conventions.md`) that auto-activate based on file path. The job-conventions file in particular documents the daily pipeline gating, idempotency expectations, the numpy adapter requirement, and the env-var list. Carry these forward.
- `CLAUDE.md` — the Command Router, the auto-activating rules pointer, the three-tier incident response (L1 auto-fix, L2 agent-fix, L3 diagnosis-only), the Discovery Wave (D1 codebase, D2 product reality, D3 tech debt running in parallel). The structure of how to think about sprints is in this file; the implementations of the individual commands are in `.claude/commands/`.
- `docs/architecture/BACKEND_ARCHITECTURE.md` — the Repository / Service / Event Bus pattern, BaseService and BaseRepo abstractions, the asyncpg shared-pool guidance. Architectural literacy worth preserving even if the new system is smaller.
- `docs/guides/WORKFLOW.md` — the 10-phase lifecycle. Carry forward as a reference for what a sprint shape looks like, but expect to use only the simpler parts in a single-user system.

The strategy and discovery documents (`docs/discovery/`, `docs/sprints/`) contain the project's intellectual history: decisions made, paths abandoned, sprint retrospectives. Worth keeping in an archive directory in the new repo but not worth reading until a future "why did we decide X" question comes up.

## What works at the unit-test level

The frontend test count (5,040) is misleading. Many are component snapshot tests that test the test framework more than the code. The backend test count (~176 in `tests/`) is more honest. The genuinely valuable tests are:

- Feature engine training-vs-serving parity tests, where they exist.
- Tax math tests on CGT discount tiers and Division 296 threshold boundaries.
- Signal threshold boundary tests at 0.65 / 0.55 / 0.45 / 0.35 probability cutoffs.
- Walk-forward backtest sanity tests for screening rules.

A new repo should aim for one to two hundred carefully-chosen tests, focused on the actual failure modes — schema drift, training/serving skew, tax math corner cases, signal threshold boundaries — and discard the long tail of low-value component tests.

## Summary for the rebuild conversation

The recoverable assets are the ML pipeline, the tax alpha module, the screening engine, the signal narrative layer, the scenario simulation code, a few dozen well-shaped jobs (signal generation, retraining, EODHD ingestion, SHAP extraction), the first 19 migrations, and the entire `.claude/` directory of commands and rules. Everything else — auth, users, notifications, admin, the frontend, the marketing surface, the AFSL / REP 798 compliance posture, the multi-channel notification dispatch — is SaaS scaffolding that exists because of the original B2B framing and should not survive the move.

The proximate causes of "nothing runs" are operational: Render configuration has drifted from `render.yaml`, env vars are unevenly distributed across crons, and the application lifecycle hides every failure as a warning. None of these are domain-logic problems. They are the kind of debt that accumulates when one person is shipping features and also operating the infrastructure, and they are the kind of debt that a clean rebuild discharges in a weekend.

The next phase distils the durable knowledge — domain, architectural, and procedural — that should land in the new repo on day one.

Ready for Phase 2?
