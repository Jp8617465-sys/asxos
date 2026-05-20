# Phase 2 — What survives the fire

This is the durable knowledge worth carrying from the old repo into the new one. Four sections: domain knowledge, architectural patterns, anti-patterns and lessons, reusable specifications and verbatim code.

The cut is ruthless. If something is conceptually valuable but the code is broken, the concept survives and the code does not. If something looks impressive but never actually worked end-to-end, it does not survive. If something is genuinely good code, it is named here with a file path and line range so it can be copied verbatim.

## Domain knowledge worth carrying

### ASX market structure and data sourcing

- EODHD is the sole price data source. Never synthesise prices, never interpolate, never fill forward beyond a single missing day. The ASX has ~2,200 listed tickers; a practical working universe is the top 500 by market cap or some equivalent liquidity filter. Tickers carry `.AU` as the canonical suffix; `.AX` is legacy and should be normalised on ingest.
- EODHD Pro tier is roughly 100,000 calls per day. The bulk EOD endpoint can refresh the entire universe in a few hundred calls. Fundamentals, earnings calendars and ETF constituents have their own endpoints. Cache aggressively in the application layer; never call EODHD from a request-serving code path.
- The ASX trades 10:00–16:00 Sydney time, but live prices have a 15–20 minute delay on most retail data feeds and the cleanest workflow is end-of-day. The trading calendar exclusions (`is_asx_trading_day`) are non-trivial — public holidays differ by state. Use the helper module rather than recomputing.

### Model A: 22-feature specification

The deployed Model A is a LightGBM classifier with a paired regressor, v1_5, defined by `models/model_a_v1_5_features.json`. The 22 features, by group, are:

- Momentum: `ret_1d`, `mom_1`, `mom_3`, `mom_6`, `mom_12_1` (12-month minus most recent month).
- Volatility: `vol_30`, `vol_60`, `vol_90`, `vol_ratio_30_90`.
- Liquidity: `adv_20_median`, `adv_zscore`.
- Trend: `trend_200`, `sma200_slope`, `sma200_slope_pos`, `atr_pct`, `volume_skew_60`.
- Fundamental: `pe_ratio`, `pb_ratio`, `eps`, `market_cap`, `pe_ratio_zscore`, `pb_ratio_zscore`.

The feature engine pattern matters more than the specific list. Eight feature groups (`momentum`, `volatility`, `liquidity`, `trend`, `cross_sectional`, `fundamental`, `macro`, `sentiment`), each in its own module under `app/features/ml/feature_groups/`, all routed through a single `FeatureEngine` instance used identically in training and inference. This is the canonical anti-skew design and worth carrying forward exactly.

### Signal thresholds

The five-level classification is the user-visible output. The boundaries are calibrated and should not move casually:

- `STRONG_BUY`: `prob_up >= 0.65` and `expected_return > 0.05`
- `BUY`: `prob_up >= 0.55` and `expected_return > 0`
- `SELL`: `prob_up <= 0.45` and `expected_return < 0`
- `STRONG_SELL`: `prob_up <= 0.35` and `expected_return < -0.05`
- `HOLD`: everything else

Confidence is an integer derived from probability distance from 0.5: `(np.abs(prob_up - 0.5) * 200).astype(int)`. Regime-conditional tightening (bear / neutral regimes shift thresholds inward to suppress noise) lives in `apply_regime_thresholds` and is worth preserving.

### Validation gates for retraining

- ROC AUC floor: 0.65
- Maximum degradation vs prior model: 5%
- Minimum training samples: 1,000

A new model artefact that fails any gate does not deploy. Blue-green hot reload of the model file under `models/` means a successful candidate replaces the live model without a process restart.

### Tax alpha — Australian-specific rules

The CGT and Division 296 logic in `app/features/tax_alpha/services/` is genuinely correct and represents nontrivial domain research. The rules:

- CGT discount tiers by account type: 50% individual, 33.33% superannuation accumulation phase, 0% pension phase. The discount applies when the holding period exceeds 12 months.
- Division 296 (commences 2026-07-01): a 15% additional tax on super balances above $3M, with a $10M tier triggering further treatment. The new code should compute exposure per account and surface alerts as the balance crosses thresholds.
- Franking credit grossing-up: dividends from Australian companies carry franking credits up to the corporate tax rate (30% for large companies, 25% for base-rate entities). Effective yield = `dividend × (1 + franking_credit_rate / (1 - franking_credit_rate))` for fully franked dividends in a refundable-credit account.
- Division 83A (ESS): tax treatment of employee share schemes, including the upfront vs deferred election. Relevant to the spouse's CRM ESPP tranches captured in memory.
- Foreign holdings v3 design: a separate `foreign_holding_lots` table, RBA FX rates for translation, upfront Division 83A treatment, twelve scenario groupings for disposal. This design survives the rebuild; the code can be rewritten more cleanly.

### Regime detection

The bull/neutral/bear classifier (`app/features/ml/regime_classifier.py`) is real and is referenced in signal generation. The new repo should preserve regime as ambient context — a single value attached to each daily signal batch — rather than build a separate regime feature. Regime-conditional signal thresholds (tighten in neutral, tighten harder in bear) are the practical use of the classifier. HMM-based regime detection over multi-asset returns is a future module, not a day-one need.

### Screening engine: SHAP → rules → archetypes

The pipeline is sound:

1. SHAP values are computed for every signal row via Tree SHAP (`pred_contrib=True`).
2. For each feature, find the zero-crossing point in the SHAP-vs-feature-value scatter — the value at which the feature flips from positive to negative contribution. Pure function in `jobs/extract_shap_thresholds.py:155–212`.
3. The zero-crossing becomes a candidate screening rule.
4. Rules are walk-forward backtested (1y train, 6mo test, 3mo step). Activation gate: walk-forward efficiency > 0.5 and hit rate > 50%.
5. Surviving rules become published screens; rules that fail are kept for diagnostics but not surfaced.

The walk-forward methodology is the single most important methodological choice in the project. Never `train_test_split`. Always `TimeSeriesSplit` or `PurgedGroupKFold`. Deflated Sharpe Ratio for multiple-testing control. Survivorship bias disclaimer on every backtest, with a 2–5% annual inflation estimate for small-cap results.

K-Means archetype assignment (`stock_intelligence_service.py`) clusters stocks into four archetypes from their feature vectors. Useful for narrative, not load-bearing for signal quality. Carry the concept; build the code when there's a use for it.

### SHAP as first-party explanation

The product positioning that survives is: "this is our model, here is why it said BUY, here are the three features that pushed it past the threshold today." That's defensible domain content with a real moat. The alternative — synthesising third-party signal composites — has none.

For a single-user system the AFSL / REP 798 framing falls away entirely, but the underlying discipline (model is explainable per signal, not just per population) is good practice for one's own decisions too.

## Architectural patterns that worked

### Repository, service, event bus separation

The pattern from `docs/architecture/BACKEND_ARCHITECTURE.md`: routes are thin and delegate to services; services hold business logic and emit events; repositories own data access. `BaseService` provides `event_bus` and `publish_event`. `BaseRepo` provides CRUD primitives. `AsyncBaseRepository` provides the same shape over asyncpg for hot paths. The pattern was sometimes ignored in the old repo (some routes had inline SQL, some services bypassed the bus) but where it was followed the code is testable and clean. Carry it forward.

The event bus transform (`emit("signal_generated")` becomes `EventType("signal.generated")`) is a small but elegant detail. Cross-feature communication via events rather than direct imports keeps modules decoupled.

### Shared asyncpg pool

`app/core/db.py` exposes a single asyncpg pool initialised at lifespan startup. Hot paths (signals, portfolio, screening) use it through `AsyncBaseRepository`. Never open a per-request connection; never let psycopg2 leak into a request handler. Carry the rule.

### Migrations-first commit order

Schema changes ship before the code that depends on them. Numbered SQL files, applied in order, never modified once applied. The first 19 migrations in this repo are a good template for the new schema. Migration 020 onward is repair work and should not be replayed.

### Discovery Wave

The three-agent parallel discovery (D1 codebase audit, D2 product reality, D3 tech debt) before every sprint is one of the more useful procedural patterns in `.claude/`. Run them in a single message with parallel tool calls. The new repo will be smaller and discovery will be cheaper, but the habit is worth keeping.

### Three-tier incident response

L1 auto-fix (lint, format, type), L2 agent-fix (failing test, broken route), L3 diagnosis-only (data corruption, auth breach, outage — no fix without human review). The clear separation kept the agent from doing destructive fixes under pressure. Carry the framing.

### Custom slash command router

`.claude/commands/` with twenty markdown files routes intent to the right agent or procedure. The seven domain commands (`signal-pipeline`, `model-experiment`, `regime-detection`, `tax-optimise`, `dashboard-component`, `feature-add`, `prompt-compose`) are pure prompt assets and survive verbatim. The lifecycle commands (`sprint-state`, `discover`, `sprint-plan`, `sprint-close`) will simplify in a single-user repo but the shapes are reusable.

### Serialisation boundary

Backend returns snake_case. Frontend hooks in `frontend/hooks/` map to camelCase at exactly one boundary. This was strictly enforced and worked. Carry the rule if a frontend ever returns.

## Anti-patterns and lessons learned

### Graceful-degradation startup is the highest-cost mistake

Every dependency initialisation failure in `app/main.py` is downgraded to `logger.warning(...)` and the process continues. The API claims health. Users see 500s on every protected endpoint. The fix is one-line: convert warnings to hard failures for anything that must be present. The lesson is broader: build the system to fail loudly. A new repo should refuse to boot if the database is unreachable or the model file is missing. Silent degradation is worse than a crash because nobody knows to fix it.

### Env var sprawl

Sixty distinct environment variables across `app/` and `jobs/`, declared inconsistently across Render crons. Carry the discipline: every required variable is loaded at startup through one module that fails fast if any is missing. Optional variables default explicitly. No `os.getenv("X")` scattered through services.

### Schema drift from preventable mistakes

Migration 020 fixed an FK pointing at a `users` table that did not exist. Migration 035 widened `NUMERIC(10,6)` columns. Migration 0101 promoted a `DOUBLE PRECISION` to `NUMERIC(18,6)`. All three were avoidable. The rule for the new repo: use `NUMERIC(18,6)` for every monetary or statistical column from day one; verify FK targets exist before applying; review each migration as if it were the only chance to get it right (because it is).

### The synthesis-gap positioning trap

The B2B SaaS pitch eventually settled on the "synthesis gap": surface composite views the user can't easily get elsewhere. The truth is that surfacing third-party composites is undifferentiated, while building first-party explanations from your own model is defensible. For a personal tool the positioning question is irrelevant, but the methodological lesson stays: own your model, own your explanations, don't be a thin shell over a vendor's signal.

### SaaS framing warped every layer

Multi-tenant assumptions cost: `user_id INT` on every table, RLS policies on every user-facing table, JWT and token revocation, password reset flows, login pages, multi-channel notifications, admin dashboards. None of this is necessary in a single-user system, and most of it slowed every sprint. The rule for the new repo: do not add an architectural seam (auth, multi-tenancy, billing) unless a real second user is about to appear. Premature multi-tenancy is the most expensive mistake the project made.

### The 5,040-test trap

Test counts are vanity numbers. Most of the frontend tests in this repo are component snapshots that test the test framework. The backend has 176 tests and only some are load-bearing. The new repo should aim for around 100 backend tests, focused on the failure modes that actually broke things: training/serving parity, tax math at threshold boundaries, signal classification at probability cutoffs, schema migration safety. Volume is not coverage.

### ASIC REP 798 and AFSL posturing

The compliance framing assumed a consumer product subject to general advice rules. For a personal tool none of this applies — no licence is needed to make decisions about one's own capital, no disclaimers required, no audit trail of advice generation. Strip all of it. Keep the underlying discipline (model is explainable, decisions are recorded for self-review) because it's good practice; drop the regulatory scaffolding.

## Reusable specifications and verbatim code

### NumPy adapter registration (copy verbatim)

From `jobs/generate_signals.py:35–46`. Every script that writes numpy values to psycopg2 must register these adapters before any insert:

```python
import psycopg2.extensions
for np_type, py_type in [
    (np.int64, int),
    (np.int32, int),
    (np.float64, float),
    (np.float32, float),
    (np.bool_, bool),
]:
    psycopg2.extensions.register_adapter(
        np_type, lambda x, cast=py_type: psycopg2.extensions.AsIs(cast(x))
    )
```

This block is the canonical fix for "can't adapt type 'numpy.float64'" errors. It costs nothing and prevents a class of silent insertion failures.

### Vectorised signal classification

From `jobs/generate_signals.py:421–430`:

```python
signals["signal"] = apply_regime_thresholds(signals, regime)
signals["confidence"] = (np.abs(signals["prob_up"] - 0.5) * 200).astype(int)
```

No `.apply()`, no row-by-row iteration. `apply_regime_thresholds` is a single `np.where` ladder over the five threshold bands. This is the right shape for any function operating on a few hundred to a few thousand signal rows.

### SHAP zero-crossing function

From `jobs/extract_shap_thresholds.py:155–212`. Pure function, easily testable, no DB dependency. Takes a feature-value array, a SHAP-value array, and an optional population median; returns the interpolated feature value at the zero crossing or `None` if monotonic. Multiple crossings: pick the one nearest the population median. Copy verbatim.

### JobMonitor context manager

From `jobs/utils/job_monitor.py:137–285`. Wraps a cron entry point with timing, completion recording (`job_completions` table), and webhook plus SMTP alerting on failure. The simplest version useful for a personal system can probably drop SMTP and keep the webhook, but the context-manager shape is right.

### First-19-migrations template

The first nineteen SQL files in `migrations/` represent the durable schema decisions. Read each before writing the new schema. Migration 001 shows the right idempotency pattern (`DO $$ BEGIN IF NOT EXISTS (...) THEN ... END IF; END $$`) for adding constraints. Migration 003 shows the right composite-index discipline for signal and holding queries.

### Custom slash commands (copy `.claude/commands/` verbatim)

Seven domain commands worth preserving as-is: `signal-pipeline`, `model-experiment`, `regime-detection`, `tax-optimise`, `dashboard-component`, `feature-add`, `prompt-compose`. Five auto-activating rule files: `api-conventions.md`, `ml-conventions.md`, `screening-conventions.md`, `coach-conventions.md`, `job-conventions.md`. The rule files in particular encode hard-won detail (the numpy adapter pattern, the signal threshold table, the walk-forward parameters) and should land in the new repo on day one.

The thirteen lifecycle and ops commands (`sprint-state`, `discover`, `sprint-plan`, `sprint-close`, `quality-check`, `ship`, `deploy-check`, `smoke-test`, `health-check`, `error-triage`, `security-scan`, `harden`, `catchup`) will simplify in a single-user repo but the shapes are reusable.

### XML prompt structure

The `prompt-compose` command and the founder's own prompt habits show a consistent shape: `<context>`, `<task>`, `<constraints>`, `<output_format>`. Carry forward — it produces more usable output from Claude than free-form prose.

### Signal thresholds, validation gates, walk-forward parameters

These are configuration, not code, but they survive the rebuild and should be the first numbers in any new config file:

```
SIGNAL_STRONG_BUY_PROB = 0.65
SIGNAL_STRONG_BUY_RETURN = 0.05
SIGNAL_BUY_PROB = 0.55
SIGNAL_SELL_PROB = 0.45
SIGNAL_STRONG_SELL_PROB = 0.35
SIGNAL_STRONG_SELL_RETURN = -0.05

MIN_ROC_AUC = 0.65
MAX_DEGRADATION_PERCENT = 0.05
MIN_TRAINING_SAMPLES = 1000

WALK_FORWARD_TRAIN_MONTHS = 12
WALK_FORWARD_TEST_MONTHS = 6
WALK_FORWARD_STEP_MONTHS = 3
WALK_FORWARD_EFFICIENCY_GATE = 0.5
WALK_FORWARD_HIT_RATE_GATE = 0.50
```

### Screening rule JSON schema

Documented in `screening-conventions.md` and worth keeping verbatim:

```json
{
  "type": "combined",
  "version": 2,
  "logic": "AND",
  "conditions": [
    {"feature": "mom_6", "op": ">=", "value": 0.04},
    {"feature": "pe_ratio", "op": "<=", "value": 25.0}
  ]
}
```

Operators: `<=`, `>=`, `<`, `>`, `==`, `!=`, `between`. Combined logic: `AND` or `OR`. The translator from rule JSON to parameterised SQL is in `app/features/screening/services/screen_match_engine.py` and is worth re-reading before writing the new version.

## Summary

What survives the fire: the ASX-specific domain content, the Model A spec and threshold ladder, the tax alpha rules, the feature engine pattern, the SHAP-as-explanation positioning, the walk-forward methodology, the migration discipline, and a handful of pure functions and configuration blocks worth copying verbatim. The structural patterns (Repo/Service/EventBus, Discovery Wave, three-tier incident response, custom slash command router) survive in form. The `.claude/` directory survives in its entirety.

What does not survive: SaaS multi-tenancy assumptions, the graceful-degradation startup pattern, env var sprawl, the AFSL / REP 798 compliance posture, the 5,040-test discipline, premature schema decisions that later required repair migrations, and the synthesis-gap positioning narrative.

The next phase proposes what the new system should actually be, given that it is a personal investment intelligence OS and not a SaaS.

Ready for Phase 3?
