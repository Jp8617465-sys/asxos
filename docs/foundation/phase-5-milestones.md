# Phase 5 — Milestones to a working personal system

**Status:** **historical** — the dated rebuild-era milestone plan (M1–M12, 2026-06). Classified
**HISTORICAL** in `docs/product/model-a-reference-manifest.md`.
**Superseded on Model A only:** see the note below.

> **⛔ ONE DEFERRAL CONDITION HAS BEEN MET, AND THE DOCUMENT SAYS IT HASN'T — annotated
> 2026-08-13, mission `P1-05`.** (Handed forward by `SB0-01`,
> `docs/product/doc-truth-map-2026-08-13.md` §6.2.)
>
> §Explicit non-goals reads: *"**No model B/C/D feature work.** … Defer until Model A's signal
> quality is the bottleneck **(it isn't — usage is the bottleneck)**."*
>
> **The parenthetical is the exact proposition the 2026-07-11 decay analysis refuted.** On 19,032
> matured signals, `corr(ml_prob, 21d return) = −0.03` and STRONG_BUY returned **−0.09%** at 21d
> against HOLD's **+5.07%** — conviction inverted at the top. Model A's signal quality **was** the
> bottleneck; the assumption that it wasn't is why the question went unasked for months.
>
> **The non-goal's conclusion nevertheless survives, for the opposite reason.** James did not
> respond by building models B/C/D — he **shelved the ML engine** entirely
> (`docs/product/ml-engine-shelf-2026-07-11.md`) and made the product the model-independent moat
> (discipline, tax, themes, ETFs). So "no model B/C/D feature work" is still the right call; the
> stated *reason* is wrong. **The trigger condition fired and the answer was to stop, not to
> escalate.**
>
> CLAUDE.md rule **#11** stands. **Retained verbatim as a dated record.**

This is the migration plan from "nothing" to "working personal investment OS for James." It is a sequence of milestones, each small enough to complete in one to three days of focused work, each with a definition of done that is testable rather than aspirational.

The milestones are stack-agnostic across the two Phase 4 proposals on the table — the capability progression is the same whether holdings live as a table or a view, whether the email vendor is Resend or SES, whether tests cap at 100 or 400. Where the architectural choice matters operationally, it's called out inline.

After M7 the system is genuinely useful: James can open his email at 7am, read what changed, see his tax actions, and act on any of them. Everything after M7 is enrichment, not foundation.

The plan deliberately avoids "implement screening" or "build the brief" as single milestones. Those are programmes of work, not milestones. Each milestone below is one specific capability that either works end-to-end or does not.

## M1 — Repo bootstrap and hard-fail lifecycle

**One to two days.**

A new repo `asxos` exists with the Phase 4 directory tree (whichever variant wins). `pyproject.toml`, `.python-version` pinned to 3.12, `docker-compose.yml` with Postgres 16, `Makefile` with the eight or so entry points (`make dev`, `make migrate`, `make test`, `make sync-prices`, `make signals`, `make brief`, `make retrain`, `make shell`). `.env.example` listing every required variable.

A single `0001_universe.sql` migration applies cleanly. The FastAPI app boots locally with a lifespan handler that opens the asyncpg pool, verifies the migration table is current, and refuses to start if either fails. `/health` returns 200 with a JSON body listing the database connection age and the migration count. `GET /` is unimplemented; this is not a public service.

`.claude/commands/` and `.claude/rules/` are copied verbatim from the old repo. The `Makefile` includes a `make claude-rules-check` target that diffs against the canonical copy.

**Definition of done**: `make dev` starts the API on port 8788. `curl http://localhost:8788/health` returns 200 with DB connection info. `make migrate` applies all migrations. `pytest` runs and passes (with zero tests at this point, that's the trivial pass). Killing the Postgres container and re-curling `/health` returns 503, not 200. The hard-fail behaviour is verified.

## M2 — EODHD price ingestion for one symbol, end to end

**Two days.**

The `asxos/ingestion/eodhd.py` module exists. It exposes a single rate-limited async function for fetching daily prices. The `asxos/jobs/sync_prices.py` entry point pulls today's prices for `BHP.AU` (one symbol, hardcoded) and UPSERTs them into the `prices` table. `JobMonitor` is ported from `jobs/utils/job_monitor.py:137–285` in the old repo and records the run in `job_completions`.

Migration `0002_prices.sql` defines the table with `(symbol, dt) PRIMARY KEY` and `NUMERIC(18,6)` price columns. The numpy adapter block from `jobs/generate_signals.py:35–46` is in place at the top of any module that writes numpy values.

`make sync-prices` runs the job. Running it twice on the same day produces zero new rows (idempotency verified).

**Definition of done**: a fresh `BHP.AU` daily row appears in `prices` after `make sync-prices`. `job_completions` shows the run. A re-run is a no-op. One test in `tests/test_eodhd_ingestion.py` verifies idempotency by mocking the EODHD response.

## M3 — Universe loaded, prices for all ASX-listed symbols

**One day.**

`asxos/ingestion/universe.py` loads the active ASX universe from EODHD's exchange listing endpoint into `universe`. `sync_prices.py` is changed from a hardcoded symbol to "every active universe row, via EODHD's bulk EOD endpoint." Total wall time for one day's prices should be under five minutes for ~2,200 tickers.

The `universe` migration `0001_universe.sql` adds `is_active` and `delisted_at` columns. Delistings between runs are detected (universe row is updated to `is_active=false`, not deleted).

**Definition of done**: `make sync-universe` populates `universe` with at least 2,000 rows. `make sync-prices` fills today's prices for all active symbols in under five minutes. Running the same day twice is idempotent. `job_completions` shows both runs with correct timings.

## M4 — Fundamentals refresh

**One day.**

`asxos/ingestion/fundamentals.py` and `asxos/jobs/sync_fundamentals.py`. Fundamentals are per-symbol, rate-limited harder than prices, but only need to run weekly. UPSERT into `fundamentals` on `(symbol, as_of)`.

This milestone is small but separates concerns: prices change daily, fundamentals change quarterly. Conflating them in one job was a pattern in the old repo and made debugging harder.

**Definition of done**: `make sync-fundamentals` populates today's fundamentals row for every active universe entry. Re-running the same week is a no-op (or updates trivially). Failure on one symbol does not abort the rest.

## M5 — Feature engine ported, features computable for one date

**Three days.** The single longest milestone.

`asxos/domain/signals/feature_engine.py` and `asxos/domain/signals/feature_groups/` are ported from the old repo's `app/features/ml/feature_engine.py` and `feature_groups/`. The eight feature groups (momentum, volatility, liquidity, trend, cross_sectional, fundamental, macro, sentiment) all produce the same 22 features defined in `models/model_a_v1_5_features.json`.

`_safe_quintile` is preserved. The FeatureEngine class is the same instance used by both the (forthcoming) training and inference paths — no parallel implementation, no skew.

A CLI command `asxos features <date>` computes the full feature matrix for the given date, prints summary statistics, and writes nothing to the database. This milestone deliberately does not persist features; computation happens in-process for both training and inference.

The first real test lands: `test_feature_engine.py` computes the feature matrix twice for the same date and asserts every value is exactly equal. This is the training/serving parity test that the old repo's discipline was trying to enforce.

**Definition of done**: `asxos features 2026-05-15` prints a feature matrix with ~2,000 rows and 22 columns. Re-running produces byte-identical output. `pytest tests/test_feature_engine.py` passes.

## M6 — Model A loaded, predictions and SHAP for one date

**Two days.**

The Model A artefact files (`model_a_v1_5_classifier.txt`, `model_a_v1_5_regressor.txt`, `model_a_v1_5_features.json`) are copied from the old repo into `models/`. The 0009 migration adds `model_versions` with the `is_active` flag (per the system-architect proposal — operationally cleaner than a config restart).

`asxos/domain/models/cache.py` loads the active model into memory at API startup. `asxos/domain/models/model_a.py` exposes `predict_with_shap(features_df) -> (predictions_df, shap_df)`. The CLI command `asxos predict <date>` computes features, runs prediction, computes SHAP via `pred_contrib=True`, and prints the top 10 buys with their top 3 SHAP factors.

This milestone uses the existing v1_5 artefact — no training yet. The training pipeline lands in M9.

`/health` now also verifies the active model file exists and is loadable.

**Definition of done**: `asxos predict 2026-05-15` prints a sensible ranking. SHAP factors are computed and look reasonable (positive `mom_6` should usually push toward buy, etc.). `/health` 503s if the model file is renamed away.

## M7 — Signals persisted with SHAP, daily pipeline assembled

**Two days.**

Migration `0004_signals.sql` adds the signals table with `shap_factors JSONB` inline. `asxos/jobs/generate_signals.py` does the end-to-end: compute features → predict → compute SHAP → classify via the threshold ladder → write to `signals` with SHAP as JSONB. The threshold module (`asxos/domain/signals/thresholds.py`) is config-loaded with the canonical values from Phase 2. `apply_regime_thresholds` is ported.

Regime detection lands too — `asxos/domain/signals/regime.py` classifies the current market as bull/neutral/bear and that value is stored on each signal row.

`make daily-signals` runs prices sync, signals generation, in sequence. systemd timer for the daily pipeline is checked into `deploy/timers/` and the deploy script rsyncs it to `/etc/systemd/system/` (per the system-architect proposal — closes the Render drift gap structurally).

The first ad-hoc query works: a small CLI command `asxos signal BHP.AU` reads from `signals` and prints today's prediction with the top 3 SHAP factors as a human-readable line.

Tests added: `test_thresholds.py` covers signal classification at exact probability boundaries (0.65, 0.55, 0.45, 0.35). `test_shap_jsonb.py` verifies the JSONB shape is queryable for "give me the top 3 SHAP for this signal."

**Definition of done**: a full daily run on a fresh database (universe → prices → signals) writes ~2,000 signal rows. `asxos signal BHP.AU` prints `BHP.AU: BUY (confidence 12) — driving factors: mom_6 (+0.027), pe_ratio_zscore (-0.018), trend_200 (+0.012)`. Boundary tests pass.

## M8 — Holdings and tax alpha layer

**Three days.**

Migration `0005_holding_lots.sql` adds the lot-level holdings table with `currency` and `fx_rate_aud_per_native` columns to support the foreign holdings v3 design from memory. A `current_holdings` view aggregates lots into per-symbol positions (per the system-architect proposal — eliminates the aggregate-drift bug class).

A CLI command `asxos import-holdings <csv>` reads a CSV of James's actual positions and lots and loads them. Format is documented in the README; one-time import.

`asxos/domain/tax/` lands in full: `cgt.py`, `franking.py`, `div_296.py`, `div_83a.py`, `positions.py`. All pure functions. `positions.tax_adjusted_view(holdings, lots, account_type, super_balance, fy_realised_gains)` returns the bundled view: per-position franking-adjusted yield, CGT discount eligibility date, post-discount tax cost of immediate disposal, Div 296 incremental exposure.

CLI lands: `asxos tax-view` prints the tax-adjusted view for the current holdings. `asxos tax-action` prints any holdings that cross a CGT discount eligibility date in the next 30 days, plus any holdings whose disposal would push the account past a Div 296 threshold.

Tests are substantive here: `test_tax_cgt.py` covers the 12-month boundary on the exact day, the day before, the day after, and across each account type. `test_tax_div_296.py` covers $2,999,999, $3,000,000, $3,000,001, and the same for $10M. `test_tax_franking.py` covers the gross-up at 30% and 25% corporate tax rates, both refundable and non-refundable account contexts.

**Definition of done**: `asxos import-holdings positions.csv` loads James's real position book. `asxos tax-view` produces a non-empty, plausible-looking table. The tax tests pass at every boundary.

## M9 — Retraining pipeline, model version flip

**Three days.**

`asxos/jobs/retrain_model_a.py` ports the old retraining job. Loads 36 months of prices and fundamentals, builds features via the same FeatureEngine used at inference, fits LightGBM classifier and regressor, runs walk-forward validation, applies the three gates (ROC AUC ≥ 0.65, ≤ 5% degradation, ≥ 1k samples). On pass: writes `model_a_v{N}_classifier.txt` to `models/` and inserts a row into `model_versions` with `is_active=false`. On fail: prints the reason, exits non-zero, no artefact written.

A separate CLI command `asxos model activate v1_6` flips `is_active` in `model_versions`. The next API restart loads the new artefact. The model cache logs the version it loaded at startup.

This milestone deliberately does not auto-deploy. James reviews the retraining output and explicitly activates.

Walk-forward validation lives as a function in `asxos/domain/models/validation.py`. It's tested with synthetic data — `test_walk_forward.py` covers TimeSeriesSplit boundaries.

**Definition of done**: `make retrain` produces a new candidate model artefact and a `model_versions` row. The output prints the ROC AUC and degradation versus the active version. `asxos model activate v1_6` flips the active flag. Restarting the API loads the new version (visible in startup logs).

## M10 — Regulatory ingestion, decisions journal

**Two days.**

`asxos/domain/regulatory/ingest.py` scrapes four sources: ASIC media releases (RSS), RBA monetary policy decisions (RSS), ATO ruling updates, ASX listing notices. Each new item normalises into `regulatory_events`. The `affects_symbols` column is filled by a simple matcher (regex on stock codes plus a name-to-symbol lookup over `universe`).

Migration `0006_decisions.sql` adds the journal table with `top_shap_factors JSONB` and `reasoning_md TEXT`. CLI: `asxos journal add BHP.AU buy 100 'thesis: model says BUY, regime is bull, CGT-eligible date for existing lot is in 30 days'` appends a row that snapshots the current model state.

`asxos journal` lists recent decisions. `asxos journal review` shows decisions older than 60 days that haven't had an outcome recorded yet.

**Definition of done**: `make ingest-regulatory` populates `regulatory_events` with overnight items. `asxos journal add` creates a row that includes the current model signal and top SHAP factors. `asxos journal review` flags stale decisions.

## M11 — Morning brief, end-to-end usable workflow

**Two days.**

`asxos/brief/compose.py` produces a ~200-word brief from canned inputs: signal changes on holdings since yesterday, market regime, pending tax actions within 30 days, regulatory events affecting held symbols in the last 24 hours. `asxos/brief/email.py` sends via Resend (per system-architect; alternatives are SES or Mailgun, choose at M11 implementation time).

`make morning-brief` runs ingest-regulatory → daily signals → compose → send. systemd timer fires this at 07:00 Sydney each weekday. The brief is also printed to terminal for local invocations.

Tests: `test_brief_compose.py` verifies that given canned inputs the brief produces non-empty text and contains the expected sections (signals changed, regime, tax actions, regulatory). No assertion on exact wording — that's content, not contract.

This is the first time the system is end-to-end useful for James. After M11 he opens his email at 7am, reads the brief, sees the day's tax actions, and is ready to act before lunch.

**Definition of done**: `make morning-brief` sends an email to James's inbox with a non-empty brief. The brief mentions specific symbols, the current regime, and at least one tax action if any are within 30 days. The systemd timer fires at 07:00 the next morning without manual intervention.

## M12 — Production VPS, scheduled timers running

**Two to three days.**

Provision a Hetzner CPX11 (or CX22 per the system-architect proposal — both fit under €10/month). Ubuntu 24.04. Install Docker, Docker Compose, systemd timers. Deploy via `git pull` + `docker compose up -d` + the timer rsync. SSH-only access via Tailscale. Nightly Postgres dump to a single S3-compatible bucket (R2 or Backblaze B2).

A `deploy.sh` script in the repo handles the full sequence. `make deploy` runs it remotely.

Observability: structured logs go to `/var/log/asxos/` via systemd. A Healthchecks.io account (free tier) provides deadman's-switch alerting — the morning-brief job pings on success, and a missed ping after 90 minutes triggers a Slack webhook. This is the minimum observability that catches "the brief stopped sending and nobody noticed."

**Definition of done**: James receives a 7am email from his own VPS for five consecutive trading days. `journalctl -u asxos-morning-brief` shows successful runs. A deliberately-broken job (e.g., revoke the EODHD key for a day) triggers a Healthchecks alert. The nightly Postgres dump appears in the bucket.

## After M12: not in the first three months

The list is as important as the milestones above. After M12 the system is working. The temptations to resist:

- **No frontend until M12 has been operational for at least a month.** A Streamlit page for the brief is fine eventually; it is not a milestone in the first quarter. Email and CLI are enough.
- **No second user.** Not James's spouse, not a friend, not "to test the auth flow." The architecture has no auth and the schema has no `user_id`. Adding a second user is a one-week minimum of rebuilding patterns that were deliberately discarded.
- **No additional models in the ensemble.** Model A only until M12+. Model B, C, D were sources of complexity in the old repo for marginal blended signal improvement. The first version of the system uses Model A's signal and that is enough.
- **No semantic memory, no Voyage embeddings, no Anthropic SDK integration.** The Coach concept from the old repo was scaffolding that never produced value. Don't port it.
- **No archetype clustering, no surrogate trees.** Screening rules from SHAP zero-crossings is enough for the first quarter. K-Means archetypes are interesting for narrative; they did not move signal quality.
- **No alternative data sources.** EODHD is the sole price and fundamentals source. Adding ABS, RBA, or scraped sources is a separate programme. Resist the urge to fold in macroeconomic data beyond what Model A already uses.
- **No backtest UI.** A function call from the CLI is enough. Building a UI for backtests in the first three months is over-investing in tooling.
- **No model B/C/D feature work.** Each was a sprint-sink in the old repo. Defer until Model A's signal quality is the bottleneck (it isn't — usage is the bottleneck).
- **No property module.** The data sources, valuation models, and tax treatment are qualitatively different. Property is its own project, started after the equities loop is genuinely useful for six months.
- **No multi-portfolio support.** There is one portfolio. If James wants to model "what if I held this instead", that's the `what_if_service` reimplementation as a pure function — not a new portfolios table.
- **No web auth experiment.** Not "what if we add Clerk just in case." Not until M12 has been running for a quarter and someone other than James actually wants in.
- **No CI investment beyond the basics.** One GitHub Actions workflow, three jobs (ruff, mypy, pytest). No matrix builds, no nightly runs, no preview environments.
- **No premature schema additions.** If a feature needs a column that isn't there, add a migration. If a feature seems like it might need a column eventually, do not add it speculatively.
- **No "let's port the coach" or "let's bring back the assistant".** The LLM-driven brief was scaffolding. The deterministic brief in M11 is the actual product. If LLM-augmented briefs make sense later, they layer on top of the deterministic version — never as the foundation.

## Velocity expectation

Twelve milestones at one to three days each is roughly four to six weeks of focused effort. With normal interruptions and the realities of solo development, plan for eight to ten weeks calendar time. The reward is a system that genuinely runs every morning and produces real decision support, on infrastructure that costs under €15 per month, with a test suite that's load-bearing rather than performative.

The old repo took fifteen-plus sprints to get to a state where it does not run. The new repo should reach M11 — a working morning brief — in fewer days than the old repo's last sprint took.

## Summary

Twelve milestones, each with a testable definition of done. The first eleven get James to a working morning email. M12 puts it on a server he doesn't have to babysit. Everything after M12 is enrichment, and the "do not build" list is the discipline that keeps the system from sliding back into the SaaS shape that broke the old one.

The five-phase rebuild document set is now complete. Phases 1 through 5 are in `docs/rebuild/`. The system-architect's independent Phase 4 proposal is in `phase-4-architecture-system-architect.md` for comparison with `phase-4-architecture.md`.

Ready to compare the two Phase 4 architectures and pick the path forward?
