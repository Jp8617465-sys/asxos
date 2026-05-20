---
paths:
  - jobs/**
  - scripts/cron_*
---

# Job & Cron Pipeline Conventions

## Job Structure

- All jobs use `run_cron_job()` wrapper from `scripts/cron_wrapper.py` for Sentry integration
- Critical jobs use `JobMonitor` context manager from `jobs/utils/job_monitor.py`
- Record completions via `record_job_completion()` to `job_completions` table
- Alert on failure via `ALERT_WEBHOOK_URL` (Discord/Slack) + `ALERT_EMAIL` (SMTP fallback)

## Pipeline Guards

- `pipeline_checks.is_asx_trading_day()` — skip weekends and ASX holidays
- `pipeline_checks.check_data_freshness(table, max_stale_days)` — block if upstream stale
- `pipeline_checks.validate_price_ingestion(min_ticker_count=1500)` — verify data quality
- `pipeline_checks.should_skip_non_trading_day()` — guard for non-trading days

## Daily Signal Pipeline (critical path)

```
11:00 UTC — sync_live_prices_job.py → prices
11:30 UTC — generate_signals.py → model_a_ml_signals (GATE: prices fresh ≤ 2 days)
11:30+    — generate_signals_model_b.py → model_b_ml_signals (NON-FATAL)
11:35+    — generate_ensemble_signals.py → ensemble_signals
12:00     — sync_signals_to_holdings.py → user_holdings.current_signal
12:15     — refresh_screen_matches.py → screen_matches
```

## Model Weights (Ensemble)

- A=50%, B=30%, C=12%, D=8%
- If a model is missing, weights redistribute proportionally
- Model B failure is non-fatal — ensemble falls back to Model A only

## Feature Table

- `model_a_features_extended` — wide format, 22 feature columns + date + symbol
- Built by `build_extended_feature_set.py` with 760-day lookback
- Uses `if_exists='replace'` — full rebuild each run
- Index: `idx_feat_ext_symbol_date(symbol, date DESC)`

## Idempotency

- All jobs use UPSERT patterns — safe to re-run
- DELETE operations use WHERE clauses with time bounds
- Retraining writes versioned artifacts — does not overwrite

## NumPy Adapters

- Register numpy type adapters MUST be called before any psycopg2 insert of numpy types
- Pattern: `psycopg2.extensions.register_adapter(np.int64, lambda x: AsIs(int(x)))`
- Without this, psycopg2 throws "can't adapt type 'numpy.float64'"

## Environment Variables

- `DATABASE_URL` — all jobs
- `EODHD_API_KEY` — prices, fundamentals, ETF, calendars
- `VOYAGE_API_KEY` — embed_conversations.py
- `SENTRY_DSN` — all jobs (via run_cron_job)
- `ALERT_WEBHOOK_URL` + `ALERT_EMAIL` — JobMonitor alerts
