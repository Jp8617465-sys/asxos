# asxos — Claude Code project guide

Personal investment intelligence OS for ASX equities. Single user. Python 3.12 + FastAPI + Supabase Postgres. CLI + daily email; no frontend in v1.

## Read first

- `docs/foundation/BUILD_GUIDE.md` — the executable manual for M1 through M12.
- `docs/foundation/phase-b-failure-postmortem.md` — the lessons. The previous repo died of these; this repo encodes the fixes.
- `docs/foundation/spec/tax-alpha.md` — tax-module source of truth. Implementation reads from this; tests cite section numbers.

## Non-negotiable rules

1. **Hard-fail startup.** `asxos/api/main.py` lifespan raises on dependency-init failure. No `logger.warning(...); continue`. If the DB is unreachable, the API does not start.
2. **MCP-driven service management.** Use `mcp__render__*` and `mcp__supabase__*` for routine Render and Supabase operations. Never edit the Render dashboard for changes — every change goes through `render.yaml` + `git push` + `make check-drift`.
3. **No feature flags.** If a feature is half-built, it stays on a branch.
4. **No `user_id` columns, no auth, no RLS.** Single user.
5. **NUMERIC(18,6)** for every monetary or statistical column from day one.
6. **Calendar arithmetic for CGT 12-month rule**, never day-count. Per spec §5.1: `disposal_date >= acquisition_date + relativedelta(years=1) + timedelta(days=1)`.
7. **Medicare levy** applies to taxable income for individuals — including grossed-up dividends and net capital gains. Per spec §7.
8. **Tax math is per the spec at `docs/foundation/spec/tax-alpha.md`.** Implementation must cite spec section numbers; deviations require a spec amendment.
9. **NumPy psycopg2 adapter block** at the top of any module that writes numpy values via psycopg2. See `.claude/rules/job-conventions.md`.
10. **No graceful warnings in infra code.** Fail loudly.

## Stack

| Layer | Tech | Dev command |
|---|---|---|
| API | FastAPI 0.115 | `make dev` → 127.0.0.1:8788 |
| DB | Supabase Postgres 16 (existing project, free tier) | `mcp__supabase__execute_sql` |
| Jobs (M12+) | Render cron services | `mcp__render__*` |
| Migrations | Plain `.sql` in `migrations/`, applied via `mcp__supabase__apply_migration` | No runner script |
| Email | Resend (test sender for v1) | curl-based, no SDK |
| Monitoring | Healthchecks.io deadman | per-job ping URL |

## Database schema reference

Fifteen tables. No `user_id` anywhere. NUMERIC(18,6) on every monetary or statistical column.

- `universe` — symbol PRIMARY KEY, sector, currency, is_active
- `prices` — (symbol, dt) PK, OHLCV
- `fundamentals` — (symbol, as_of) PK
- `signals` — (model, model_version, symbol, as_of) PK, prob_up, expected_return, signal_label, confidence, regime, shap_factors JSONB
- `holding_lots` — lot-level positions for CGT, with `cost_base_normal` and `cost_base_div296`
- `current_holdings` — VIEW over holding_lots WHERE disposed_at IS NULL
- `decisions` — journal
- `regulatory_events` — daily ingest from ASIC/RBA/ATO/ASX
- `job_runs` — completion tracking
- `model_versions` — active model flag via `is_active` column
- `screening_rules` — JSON rule definitions
- `portfolio_daily_snapshots` — (as_of) PK, capital_aud, holdings_mv_aud, cash_aud, benchmark columns; re-derivable, NOT in backup_irreplaceable.sh
- `themes` — (theme_id BIGSERIAL) PK; theme_code UNIQUE slug, stage/conviction/adjacency; irreplaceable
- `theses` — (thesis_id BIGSERIAL) PK; per-symbol investment thesis with entry band, stop, target, timeline, audit trail; irreplaceable
- `thesis_revisions` — (revision_id BIGSERIAL) PK; append-only event log for every discipline event; irreplaceable
- `theme_holdings` — (theme_id, symbol) PK; symbol-level theme exposure strength; irreplaceable

## Common commands

- `make dev` — start API locally
- `make check` — ruff + mypy + pytest
- `make migrate` — reminder only; actual apply via Supabase MCP
- `make check-drift` — reconcile `render.yaml` against Render dashboard via MCP

## Known test environment gaps (do not chase)

Four tests are permanently collection-errors in the remote Claude Code sandbox because
`joblib` / `lightgbm` / `sklearn` are not installed in the sandbox Python env:

- `tests/test_cli_predict.py`
- `tests/test_generate_signals_job.py`
- `tests/test_model_a_predict.py`
- `tests/test_model_cache.py`

These pass in the production Render environment where `pip install -e ".[ml]"` is run.
Do not add workarounds or skip markers — the tests themselves are correct.

## Auto-activating rules

`.claude/rules/` files attach automatically when working in matching paths:

- `api-conventions.md` — FastAPI route patterns
- `ml-conventions.md` — feature engine, model artefacts, signal threshold ladder, numpy adapter
- `screening-conventions.md` — rule JSON schema, walk-forward methodology
- `job-conventions.md` — JobMonitor, pipeline guards, idempotency, env vars

## Custom slash commands

`.claude/commands/` has 20 domain and lifecycle commands carried verbatim from the previous repo. The seven domain commands (`signal-pipeline`, `model-experiment`, `regime-detection`, `tax-optimise`, `dashboard-component`, `feature-add`, `prompt-compose`) are the most-used.
