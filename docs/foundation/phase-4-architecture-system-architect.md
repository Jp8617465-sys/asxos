# Phase 4 architecture — single-user investment intelligence OS

This document specifies the day-one architecture for the new repository. The system has exactly one user, runs on one VPS, has no auth, no frontend, no notifications routing, and no compliance posture. It exists to support three workflows for that user: a daily 7am brief, ad-hoc CLI investigation, and a decisions journal. Everything else is deferred.

The diagnosis from the old repo is the load-bearing input here. The old system died from infrastructure drift between `render.yaml` and the actual Render account, plus a `lifespan` handler in `app/main.py` that downgraded every dependency-init failure to a warning. So the new architecture must make those two failure modes structurally impossible: jobs run from the same place the API runs, and a missing dependency fails loudly at boot.

## 1. Stack choices

**Language and framework.** Python 3.12 with FastAPI. Same as before, because the ML code is Python, LightGBM lives in Python, SHAP is Python, and rewriting in Go to save 60 MB of RAM is solo-founder cosplay. FastAPI loses to Litestar on aesthetics; FastAPI wins because the agent ecosystem and the existing rules in `.claude/rules/api-conventions.md` already target it.

**Database.** PostgreSQL 16, running directly on the VPS as a system service. Loser: Supabase. Supabase was a fine choice for multi-tenant SaaS with RLS, but RLS is now actively unhelpful, the realtime layer is dead weight, and the network hop to a hosted DB is the slowest part of every batch job. A local Postgres on the same box runs signals in seconds instead of minutes and costs nothing extra.

**Job runner.** systemd timers. Loser: APScheduler in-process, Celery, Render cron, GitHub Actions cron. APScheduler ties job lifetime to API lifetime, which is exactly the failure that killed the old system in reverse. Celery needs a broker and a worker and is wildly over-spec for 30 timers a day. systemd timers are already on the VPS, they survive reboots, they support `OnCalendar`, they support `Persistent=true` to catch missed runs, and `journalctl` is the log aggregator for free.

**Hosting.** One Hetzner CX22 in Falkenstein or Helsinki: 2 vCPU, 4 GB RAM, 40 GB SSD, EUR 4.51 per month. Loser: Render, Fly.io, any PaaS. The old system died because the PaaS abstraction hid the truth about what was scheduled and what was running. A VPS where `systemctl list-timers` is the source of truth removes the entire class of drift bugs.

**Frontend.** None. Loser: Next.js, Streamlit, an admin panel. The CLI plus a daily HTML email are the surface area for at least three months. When a frontend becomes necessary it will be a static SvelteKit app that reads from the same FastAPI, but that decision lives in Phase 6 or later.

**Cache.** None on day one. Loser: Redis. There is exactly one consumer of the API. Postgres can absorb every read this user will make. If the morning brief ever takes more than 10 seconds end-to-end, the first lever is a materialised view, not Redis.

**Object storage.** Local filesystem under `/var/lib/asx-os/`, backed up nightly to Backblaze B2 (USD 0.005/GB/month, effectively free at this scale). Loser: S3. The only objects are LightGBM `.joblib` files and a SQLite-format DuckDB analytics cache; both fit on the VPS disk and the recovery story is "rsync from B2".

**Observability.** systemd journal plus a `job_runs` table in Postgres plus a single Healthchecks.io account (free tier) per timer. Loser: Sentry, Datadog, Prometheus. Sentry on a single-user system catches exceptions for an audience of one who is already reading the morning brief which already says "yesterday's job failed". Healthchecks.io pings replace the cron-was-actually-scheduled hole that killed the old repo.

**SMTP.** Resend, free tier (100/day, 3k/month). Loser: Postmark, SES. Already proven in the old repo; no reason to switch.

**Total recurring cost.** EUR 4.51 (Hetzner) + EUR ~0 (Resend free tier) + EUR ~0.50 (B2 backups) + EUR 0 (Healthchecks.io free tier) + domain. Comfortably under EUR 15/month.

## 2. Repository layout

```
asx-os/
├── pyproject.toml               # uv + ruff + pytest config
├── uv.lock
├── README.md
├── .env.example                 # one env file, not eight
├── .claude/
│   ├── commands/                # 20 markdown files, ported verbatim
│   ├── rules/                   # 5 auto-activating rule files, ported verbatim
│   └── settings.json
├── src/asx_os/
│   ├── __init__.py
│   ├── config.py                # pydantic-settings, fails on missing key
│   ├── db.py                    # asyncpg pool + sync psycopg connection helpers
│   ├── api/
│   │   ├── main.py              # FastAPI app, lifespan, /health
│   │   └── routes/
│   │       ├── signals.py
│   │       ├── holdings.py
│   │       ├── tax.py
│   │       ├── journal.py
│   │       └── brief.py
│   ├── domain/                  # pure business logic, no I/O
│   │   ├── signals.py           # threshold rules, confidence math
│   │   ├── tax.py               # CGT, Div 296, franking, Div 83A
│   │   ├── regime.py            # bull/neutral/bear classifier
│   │   └── lots.py              # FIFO/LIFO/min-CGT lot selection
│   ├── ml/
│   │   ├── feature_engine.py    # ported from app/features/ml/feature_engine.py
│   │   ├── train_model_a.py     # ported from jobs/retrain_model_a.py
│   │   ├── predict.py           # vectorised inference + SHAP
│   │   └── registry.py          # model version loading, in-process cache
│   ├── ingest/
│   │   ├── eodhd.py             # single rate-limited client
│   │   ├── prices.py
│   │   ├── fundamentals.py
│   │   ├── earnings.py
│   │   └── regulatory.py        # ASX announcements + ATO releases
│   ├── jobs/                    # every entry point is `python -m asx_os.jobs.X`
│   │   ├── _runner.py           # JobMonitor port, owns job_runs writes
│   │   ├── ingest_prices.py
│   │   ├── ingest_fundamentals.py
│   │   ├── ingest_regulatory.py
│   │   ├── generate_signals.py  # ported from jobs/generate_signals.py
│   │   ├── compose_brief.py
│   │   └── retrain_model_a.py
│   └── cli/
│       └── main.py              # typer app: `asx ask`, `asx tax`, `asx journal`
├── migrations/                  # plain .sql, applied by yoyo-migrations
│   ├── 0001_core_tables.sql
│   └── ...
├── models/                      # LightGBM .joblib + .json feature lists
│   ├── model_a_v1_5.joblib
│   └── model_a_v1_5_features.json
├── tests/
│   ├── unit/                    # pure domain, no DB
│   ├── integration/             # hits a test Postgres
│   └── jobs/                    # smoke tests for each job entrypoint
├── deploy/
│   ├── asx-api.service          # systemd unit for the API
│   ├── timers/
│   │   ├── ingest-prices.timer
│   │   ├── ingest-prices.service
│   │   └── ... (one .timer + .service per job)
│   └── install.sh               # idempotent provisioner, called from CI
└── .github/workflows/
    ├── ci.yml
    └── deploy.yml
```

Three observations on this tree. First, `domain/` is pure functions: this is where the tax math from `app/features/tax_alpha/services/cgt_alert_service.py` and `division_296_monitor.py` lands, stripped of repository abstractions. Second, `jobs/` and `api/` share `domain/`, `ml/`, and `ingest/` — there is no duplication and there is no event bus, because two callers do not need a bus. Third, `deploy/` lives in the repo and is the source of truth for what runs on the VPS; CI rsyncs this directory to `/etc/systemd/system/`, which closes the drift gap that killed the old system.

## 3. Data layer

Ten tables, no `user_id` columns anywhere, no soft deletes, no RLS. Numeric discipline: all monetary amounts are `NUMERIC(18,4)`, all ratios and probabilities are `NUMERIC(8,6)`, all percentages stored as decimals not bps. `TIMESTAMPTZ` for everything time-stamped; `DATE` for trading-day-keyed rows.

| Table | PK | Key columns | Purpose |
|---|---|---|---|
| `securities` | `symbol TEXT` | sector, currency, listing_exchange, delisted_at | The universe. ASX equities first; `currency='AUD'` is the default and foreign holdings carry their listing currency. |
| `prices` | `(symbol, dt)` | open, high, low, close, adj_close, volume | Daily OHLCV. Append-only. |
| `fundamentals` | `(symbol, as_of)` | pe_ratio, pb_ratio, eps, market_cap, shares_outstanding | Quarterly + annual; `as_of` is the report date, not the fetch date. |
| `features` | `(symbol, dt)` | feature_json JSONB | Wide-format-by-row, JSONB-stored. One row per symbol per trading day. Justified below. |
| `signals` | `(model_version, symbol, as_of)` | prob_up, expected_return, signal_label, confidence, rank, shap JSONB | Replaces `model_a_ml_signals` through `model_d_signals`. One table, model_version is the discriminator. |
| `holding_lots` | `lot_id BIGSERIAL` | symbol, acquired_at, currency, qty, cost_per_unit_local, cost_per_unit_aud, fx_rate_at_acquisition, source, disposed_at, espp_metadata JSONB | Per-tax-lot, never aggregated. This is the only holdings table. Foreign holdings supported natively via `currency != 'AUD'` and the FX columns. |
| `regulatory_events` | `event_id BIGSERIAL` | source, published_at, symbols TEXT[], title, url, body, parsed_kind | ASX company announcements + ATO releases + Treasury releases. `parsed_kind` enum: earnings, capital_raising, director_trade, dividend, regulatory_change, other. |
| `decisions` | `decision_id BIGSERIAL` | created_at, kind, symbol, qty, rationale TEXT, snapshot JSONB, outcome JSONB | The journal. `snapshot` captures the signal, regime, and feature values at decision time. `outcome` is filled in lazily. |
| `model_versions` | `(model_name, version)` | trained_at, train_window_start, train_window_end, metrics JSONB, artifact_path, is_active | Tracks the LightGBM joblib that produced any given signals row. Exactly one version per model_name has `is_active = true`. |
| `job_runs` | `run_id BIGSERIAL` | job_name, started_at, finished_at, status, rows_written, error TEXT, dependencies_ok BOOL | Replaces `job_completions`. Job-completion truth lives here, not in systemd. |

That is the entire schema for day one.

**On the SHAP question.** SHAP values live inline on the `signals` row as a JSONB column. The alternative is a separate `signal_shap` table keyed by `(model_version, symbol, as_of, feature_name)` with one row per feature. The separate-table design wins on queryability — "show me every signal where `mom_12_1` was the dominant SHAP factor" becomes a clean WHERE. The inline design wins on writes (one INSERT per symbol-day instead of 22), on storage (no key duplication), and on the fact that the only consumer is the brief and the CLI, both of which want all 22 SHAP values for a given symbol-day at once. Inline wins. If a future analytics workload needs the long-format view, it lives in a DuckDB cache derived from the JSONB, not in Postgres.

**On the features question.** `features.feature_json` as JSONB rather than 22 typed columns trades schema rigidity for migration ergonomics. A 23rd feature in v1_6 is a code change in `feature_engine.py` and a backfill job, not a migration. The validation that "the feature set matches `models/model_a_v1_5_features.json`" is enforced by `predict.py` at inference time, not by the schema. The loser here is column-per-feature: it's marginally faster at SELECT and it surfaces missing values as NULLs rather than missing keys, but it forces a migration every time the feature set evolves, which is the exact friction that bred the migration 020+ repair work in the old repo.

**On holdings vs lots.** There is no `holdings` table, only `holding_lots`. The aggregated "current portfolio" is a view: `CREATE VIEW current_holdings AS SELECT symbol, SUM(qty) ... FROM holding_lots WHERE disposed_at IS NULL`. This eliminates the entire class of "aggregate row drifts from underlying lots" bugs and makes CGT lot selection a first-class operation rather than a tax-alpha-feature reconciliation problem. The foreign-holdings v3 design from the old memory (`foreign_holding_lots`, RBA FX, upfront Div 83A) folds into the same table via the `currency` and `espp_metadata` columns.

**Not carried over.** `user_accounts`, `user_holdings`, `user_portfolios`, `assistant_conversations`, `assistant_memories`, `health_scores`, every `*_subscriptions` table, every `notification_*` table, every `alert_*` table, every `screening_*` table from the old extended schema, the `archetypes` clustering output, `signal_evidence_chains`, `goal_*` tables. The reasons: no user table means no FK target, no subscription means no billing surface, the assistant memory belongs in the journal not a separate store, screening is a CLI verb against `signals` not a separate domain.

## 4. First 10 migrations

These are the only migrations on day one. The repair-work pattern from the old repo (migration 020+) does not start fresh — it gets prevented by keeping the first 10 honest.

```
0001_core_tables.sql              -- securities, prices, fundamentals
0002_features.sql                  -- features table, JSONB column, GIN index
0003_signals.sql                   -- signals table with model_version FK
0004_model_versions.sql            -- model registry
0005_holding_lots.sql              -- lots table, view for current_holdings
0006_regulatory_events.sql         -- announcements + ATO releases
0007_decisions.sql                 -- journal
0008_job_runs.sql                  -- job execution audit
0009_indexes.sql                   -- composite indexes: (symbol, dt DESC), (as_of, signal_label), (symbol, disposed_at)
0010_views.sql                     -- current_holdings, latest_signals_per_symbol, regulatory_events_today
```

Migration `0010_views.sql` is the seam between physical storage and the query surface the brief and CLI consume. Views absorb the change pressure that would otherwise become migrations 020+.

## 5. API and lifecycle

The API has no auth. Bound to `127.0.0.1:8788` only; the CLI talks to it over loopback, the brief composer talks to it from the same machine. There is no `0.0.0.0` listener and no reverse proxy. A future need for remote access becomes a WireGuard config change, not an auth implementation.

`src/asx_os/api/main.py` owns the lifespan. The lifespan handler must, before yielding, verify in this exact order: Postgres reachable and migrations current (compare max applied migration ID to filesystem); EODHD API key present and the `/exchange-symbol-list` endpoint returns 200; the active LightGBM model joblib loads and produces a prediction on a fixture row; the `models_dir` and `data_dir` are writable. Any failure raises and the process exits with code 1. There is no `logger.warning(...) and continue`. systemd will record the failure, the healthcheck will fail, and the morning will start with a known-bad signal instead of an API claiming health while signals are stale.

`/health` probes the same things as the lifespan minus the model-load (since the model is already cached) plus a query for "newest row in `prices`" and "newest row in `signals`" and returns these with timestamps. If `signals.max(as_of)` is more than 1 trading day behind `prices.max(dt)`, the endpoint returns 503, not 200. This is the second structural defence against the old failure mode: stale signals cannot present as healthy.

The router layer is thin in the WORKFLOW sense — routes delegate to `domain/` and to thin repository functions in the same file. No `BaseService` and no `BaseRepository` abstractions; with one user and no event bus, the layers add ceremony without earning it.

## 6. Job runner

systemd timers, with one `.timer` + one `.service` per job, both checked into `deploy/timers/`. CI deploys these files via rsync to `/etc/systemd/system/` and runs `systemctl daemon-reload && systemctl enable --now asx-*.timer`. The drift gap is closed because `git diff` against the deployed unit files is the audit.

Each `.service` file invokes `/opt/asx-os/.venv/bin/python -m asx_os.jobs.<job_name>` with the same env file as the API (`EnvironmentFile=/etc/asx-os/env`). Each job is a thin entrypoint that wraps domain logic in `src/asx_os/jobs/_runner.py`. The runner is the port of `jobs/utils/job_monitor.py:137-285`: it opens a `job_runs` row at start, captures stdout/stderr, records duration, writes the closing row at end including row counts, and on failure pings the configured Healthchecks.io URL for that job.

`Persistent=true` on every timer means a missed run (VPS reboot, host outage) executes on next boot rather than skipping. `RandomizedDelaySec=60` on the ingestion jobs spreads load. `OnFailure=asx-failure-alert@%n.service` is a one-line handler that emails me via Resend.

Failure alerting has exactly two paths. The first is Healthchecks.io: every timer has a corresponding check, and a missed ping (failed run, or systemd never fired it) generates an email. This catches the drift mode where the unit file is wrong and the job never runs — Render-cron's blind spot. The second path is the `OnFailure` handler for jobs that ran but exited non-zero. Both arrive in the same inbox.

Job completion truth lives in `job_runs`, not journalctl. The morning brief queries `job_runs` to render the "yesterday's pipeline" section, and any row with `status != 'ok'` blocks the rest of the brief from generating until acknowledged via `asx job ack <run_id>`.

## 7. First 6 jobs

```
01_ingest_prices.py       06:30 AET  weekdays  → EODHD bulk daily endpoint, writes `prices`
02_ingest_fundamentals.py 04:00 AET  daily     → EODHD fundamentals, writes `fundamentals` (only changed rows)
03_compute_features.py    06:45 AET  weekdays  → reads prices+fundamentals, writes `features`
04_generate_signals.py    06:50 AET  weekdays  → reads features+model, writes `signals` with SHAP
05_ingest_regulatory.py   06:55 AET  daily     → ASX announcements API + ATO RSS, writes `regulatory_events`
06_compose_brief.py       07:00 AET  weekdays  → composes HTML, sends via Resend, writes `decisions` row if I reply
```

The chain is linear and the dependencies are explicit. Job 03 reads `job_runs` to confirm 01 succeeded for today's date; if not, it exits with status `skipped_upstream_failed` rather than writing partial features. This is the third structural defence against the old failure mode: jobs cannot succeed on top of a broken upstream because the dependency check is at job entry.

Job 06 is the user-facing artifact and gets the most defensive engineering: if any of 01-05 has a row in `job_runs` for today's date with `status != 'ok'`, the brief composes anyway but leads with the failures rather than silently degrading. The user sees a known-bad morning, not a confident-and-wrong one.

Retraining (`retrain_model_a.py`) is a seventh job that runs weekly on Sundays at 02:00 AET; it is not in the first six because it is not in the daily critical path. Earnings ingestion is folded into `02_ingest_fundamentals.py` for now since EODHD bundles it; it splits if the volume justifies it.

## 8. ML pipeline structure

`src/asx_os/ml/feature_engine.py` is the unchanged port of `app/features/ml/feature_engine.py`, including the `_safe_quintile()` guard and the 8 feature groups. The same module is imported by `03_compute_features.py` (training and inference batch) and by `predict.py` (ad-hoc CLI calls). There is no training-vs-inference fork; that was the right call in the old repo and stays.

Training is a one-shot script invoked via `asx ml retrain model_a` from the CLI or via the weekly systemd timer. It is not a notebook — notebooks rot, scripts get tested. The script lives at `src/asx_os/ml/train_model_a.py`, reads from the same Postgres, uses `TimeSeriesSplit` with the same validation gates (ROC AUC ≥ 0.65, ≤ 5% degradation vs current active, ≥ 1k samples), and writes the resulting `.joblib` to `/var/lib/asx-os/models/model_a_v<n>.joblib`. On success it inserts a row into `model_versions` and atomically swaps `is_active` via a transaction. Blue-green deployment is replaced by atomic version swap: the API caches the active version in-memory and re-reads `model_versions.is_active` on every request via a 60-second TTL in `registry.py`. No hot-reload, no SIGHUP — at most 60 seconds of stale model, which for a daily signal pipeline is invisible.

The model is loaded into a process-local in-memory cache. There is no sidecar inference service: at one prediction per symbol per day across ~2200 ASX symbols, LightGBM's `predict_proba` with `pred_contrib=True` completes in under 3 seconds on the CX22's 2 vCPU. A sidecar would be over-engineering for a workload that fits inside one process.

SHAP is computed in the same `04_generate_signals.py` call that produces predictions, using Tree SHAP via `pred_contrib=True` exactly as in the old `jobs/generate_signals.py`. The resulting per-feature contributions are written to `signals.shap` as a JSONB object keyed by feature name. The CLI verb `asx explain BHP.AU` reads that JSONB and renders a sorted bar chart in the terminal via `rich`.

Model versions are tracked in the `model_versions` table. The signals table FKs to `(model_name, version)`, which means "what did model_a_v1_4 say about BHP on 2026-01-15 vs what did model_a_v1_5 say" is a single SQL query. This is the foundation for the strategy evolution journal.

## 9. EODHD ingestion

Single module: `src/asx_os/ingest/eodhd.py`. One `EODHDClient` class, instantiated once per process via a `lru_cache`-decorated constructor. The client owns the API key, the rate limiter (token bucket, 100k/day with a 1000/minute peak ceiling), the retry policy (3 attempts with exponential backoff on 5xx and 429), and the response parsing.

Raw responses are not stored. The old repo had no raw-vs-canonical split and that was correct: EODHD is a stable source, the rate limit is the binding constraint not the storage cost, and a raw layer would just be an opportunity to fall out of sync with the canonical layer. The ingest modules (`prices.py`, `fundamentals.py`, `earnings.py`) call the client and write directly to canonical tables.

Idempotency is by primary key. `prices` is keyed on `(symbol, dt)`; the writer uses `INSERT ... ON CONFLICT (symbol, dt) DO UPDATE SET ...` so a re-run of `01_ingest_prices.py` for today's date is safe and the most recent value wins. `fundamentals` uses the same pattern keyed on `(symbol, as_of)`. The numpy adapter registration from the top of `jobs/generate_signals.py` is ported into `db.py` and runs at module import, so every job that touches Postgres gets the adapters without re-registration.

Prices, fundamentals, and earnings share the `EODHDClient` (rate limit, retry, key management) but have separate canonical writers. Earnings folds into `fundamentals.py` for now since EODHD returns earnings in the same payload; it splits only if a future earnings-calendar feature needs richer scheduling than fundamentals provide.

## 10. Tax alpha layer

Tax math lives in `src/asx_os/domain/tax.py` as pure functions: `cgt_discount_for(account_type, holding_period_days) -> Decimal`, `franking_gross_up(cash_dividend, franking_pct, tax_rate) -> Decimal`, `div_296_liability(super_balance, tcb_change) -> Decimal`, `div_83a_treatment(espp_grant, vest_date, market_value) -> Div83AOutcome`. The signatures take primitives and return primitives or small dataclasses. No `Service` classes, no repository injection, no event publishing.

The reason: tax math is the most-reused logic in the system. The brief calls it (CGT discount eligibility today), the signals job calls it (post-tax expected return ranking), the CLI calls it (`asx tax sell BHP 200`), the journal records its output (snapshot of CGT cost at decision time). A pure-function module is callable from all four contexts with zero plumbing. The lot-selection algorithms — FIFO, LIFO, min-CGT — live in `domain/lots.py` and are similarly pure, taking a `list[HoldingLot]` and a `qty_to_sell` and returning the selected lots plus the CGT consequence.

The Div 296 threshold logic ($3M soft / $10M hard, 2026-07-01 commencement) carries over from `division_296_monitor.py`. The 50% / 33.33% / 0% CGT discount tiers from `cgt_alert_service.py` carry over. The foreign-holdings v3 design carries over inside `lots.py` with `currency` and `fx_rate_at_acquisition` as first-class fields.

There is no `tax_alpha` feature module. Tax is a function library, not a domain, because there is no user-facing surface called "tax" — there is a CGT line item in the brief and a `asx tax` CLI verb and that is all.

## 11. Regulatory monitoring

Three sources, one job (`05_ingest_regulatory.py`), 06:55 AET daily.

The sources: ASX Markets Announcements (https://www.asx.com.au/asx/v2/statistics/todayAnns.do, public, no auth, JSON), ATO legislative announcements RSS (https://www.ato.gov.au/rss/), Treasury press releases RSS (https://treasury.gov.au/rss). All three are polled once daily; the job is idempotent on `(source, url)`.

The parser lives in `src/asx_os/ingest/regulatory.py`. It does not attempt rich NLP. It does three things: extract title and publish date, regex-match ASX tickers in title and body to populate `symbols TEXT[]`, and classify into the `parsed_kind` enum via a 20-line keyword heuristic (earnings/results → `earnings`; capital raising/placement/SPP → `capital_raising`; director transaction/Form 3Y → `director_trade`; dividend → `dividend`; ATO/Treasury source → `regulatory_change`; else `other`).

Affected-symbol matching is the tickers extracted from the title plus body. Cross-referencing against current holdings happens at brief-composition time, not at ingest time, so the regulatory table stays universe-wide and the morning brief filters to "what affects me today" by joining against `current_holdings`. The single daily job replaces the multi-channel notification dispatcher from the old repo: there is no real-time push, there is the 7am email.

## 12. Testing posture

Target: 400 tests. The old repo had 5,040. The 92% reduction is intentional and the breakdown is:

- 250 unit tests in `tests/unit/`: pure-function coverage on `domain/tax.py`, `domain/lots.py`, `domain/signals.py`, `domain/regime.py`, plus the feature engine's deterministic transforms. These run in under 5 seconds with no DB.
- 100 integration tests in `tests/integration/`: route → domain → Postgres, against a test database that gets created and torn down per test session. These cover the API surface, signal persistence, and the `current_holdings` view.
- 30 job smoke tests in `tests/jobs/`: each of the six jobs gets an end-to-end test against a seeded DB. These are the tests that would have caught the old repo's failure mode.
- 20 ML regression tests: fixtures of known feature-rows with expected signal output, locked at model release time. A retraining job that breaks these without an explicit "approved drift" marker fails CI.

The classes of failure tests must cover, in priority order: (1) jobs that silently succeed while writing zero rows; (2) signal threshold boundary conditions; (3) CGT discount eligibility on the day-365 boundary; (4) foreign-currency lot disposal with FX rate at acquisition vs disposal; (5) Div 296 threshold crossing; (6) the lifespan handler refusing to start with a missing dependency. Categories 1 and 6 are the structural fixes for the old failure.

CI is one GitHub Actions workflow (`ci.yml`): ruff format check, ruff lint, mypy on `domain/` and `ml/` only (the layers where types pay back), pytest. One workflow because one user maintains one repo and parallel workflows are a coordination tax with no benefit at this scale.

Pre-commit is one hook running `ruff format` and `ruff check --fix`. Nothing else. The 80% Jest coverage gate, the Husky chain, and the Prettier check from the old repo were correct for a team and overkill for one person. They added friction without catching anything the test suite didn't.

Target 400, not 4000, because every test is solo-maintained and a test suite that takes 90 seconds to run is a test suite that gets run; a 12-minute suite is a suite that gets skipped. The marginal value of test 401 is below the marginal cost of maintaining it.

## 13. What is deliberately NOT in the day-one architecture

The following are explicit no's. Each has been considered and rejected on a one-line argument.

**Redis or any cache.** One user, Postgres is fast enough, the materialised-view escape valve exists.

**An event bus.** Two callers (the API and the jobs) do not need a bus; they need a function call and they share the same `domain/` module.

**Multi-environment config (staging, prod).** One VPS is the production environment; the test environment is a local Postgres + pytest. Staging is a feature for teams shipping behind change-management.

**Sentry.** The user reads the morning brief. The morning brief leads with failures. That is the alerting layer.

**Background workers (Celery, RQ, ARQ).** systemd timers replace the entire category; the API itself does no background work.

**A reverse proxy (Caddy, Nginx).** The API binds to 127.0.0.1 and is consumed locally. No TLS termination because nothing crosses the network boundary.

**An ORM (SQLAlchemy).** asyncpg directly. The schema is ten tables; SQLAlchemy is overhead with no payback at this scale.

**Migrations tool beyond yoyo.** Yoyo is `pip install yoyo-migrations` and applies plain `.sql` files. Alembic is a feature for teams.

**Pydantic for the schema layer.** Pydantic at the API boundary only. Domain functions take primitives.

**A frontend.** Three months minimum, possibly never. The CLI plus a daily email cover both the daily and ad-hoc workflows.

**Auth, RLS, JWT, token revocation, password reset.** No users beyond me.

**Notification routing.** Resend → my inbox. One channel.

**An admin dashboard.** `psql` is the admin dashboard.

**A status page.** Healthchecks.io shows green/red for every timer; that is the status page.

**Feature flags.** Git branches.

**Schema versioning beyond migration numbers.** Migration 0001-0010 is the schema; version 2 is migration 0011.

**A model serving framework (BentoML, MLflow serving).** LightGBM `.joblib` + a 30-line `registry.py` + an in-process cache. Done.

**OpenTelemetry, Prometheus, Grafana.** `job_runs` + journalctl. The day this is insufficient is the day this product has users.

**Multi-region anything.** Falkenstein and ASX market data over the public internet. The 250ms RTT to EODHD does not compound to a meaningful latency at one-batch-per-day cadence.

**A separate analytics database.** DuckDB against the Postgres dump only if and when an analytical workload outgrows Postgres. It will not in 2026.

**Sprint ceremony.** The 7-sprint roadmap from the old memory becomes a `docs/roadmap.md` and the `.claude/commands/` carry over. There is no `PROJECT_STATUS.md` and no sprint-close workflow, because the audience for those was a future hire who was never going to exist.

This architecture should be holdable in one head, runnable on one machine, debuggable with `journalctl` and `psql`, and replaceable in chunks without forcing a rewrite of the chunks it touches. If anything in the above section gets added in month two, it should be because a specific observed problem demanded it, not because a similar system somewhere else has it.
