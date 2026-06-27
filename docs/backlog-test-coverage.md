# asxos test-coverage backlog (from audit 2026-06-27)

_33 confirmed untested gaps from the full audit (docs/audit-2026-06-27.md). Prioritised for a future coverage sprint. Mock pattern per api-conventions §Testing: mock `asxos.db.acquire` and pass synthetic asyncpg Record-shaped rows (see tests/test_brief_v2_sections.py:35 `_make_row`)._

**P0 = `api/main.py` hard-fail startup** — CLAUDE.md non-negotiable #1, zero tests on either the success path or the RuntimeError branches (migration drift, missing model artefact). Highest-value gap.

## P0

### api
- `asxos/api/main.py:18-48` — No test covers api.main lifespan, _check_migration_drift, or REQUIRED_MIGRATIONS — neither the success path nor the RuntimeError branches.
- `asxos/api/routes/health.py:9-16` — Health route returns raw dicts via JSONResponse instead of a declared Pydantic response model, deviating from api-conventions.md §Routes ('Pydantic models for every reque

## P1

### cli
- `asxos/cli/holdings.py:13-114` — No test exercises import_holdings, _run_import_holdings, _ensure_in_universe, _resolve_fx_rate, or _infer_currency — leaving the USD->AUD FX path, missing-FX RuntimeError
- `asxos/cli/journal.py:16-191` — No test file references journal_add/journal_list/journal_review or _run_journal_* helpers; all three CLI commands and their async DB paths, the symbol='-' sentinel-to-NUL
- `asxos/cli/model.py:14-101` — No tests reference model_activate, model_list, _run_model_activate, or _run_model_list; activate-not-found exit path, transaction flip, and empty-rows path are uncovered
- `asxos/cli/news.py:17-90` — Neither news_signoff nor _run_news_signoff has any covering test; --force bypass, the no-recent-ingest Exit(1) path, the decisions INSERT...RETURNING id, and the note-app
- `asxos/cli/portfolio.py:23-427` — No test module imports or exercises any CLI command in asxos/cli/portfolio.py; CLI-layer branches (date parsing 38-50, dry_run->no_persist 35-36, --side validation 141-14
- `asxos/cli/position.py:41-219` — No test exercises this CLI module (lines 41-219); only the domain layer is covered.
- `asxos/cli/profile.py:18-213` — No test references this CLI module; all four commands and async runners (init/show/activate/list), the float->Decimal(str) path, comma-split exclusion parsing, do_activat
- `asxos/cli/signal.py:11-61` — Neither signal() nor _run_signal() has any covering test; row-None Exit(1), str/dict shap handling, abs-sorted SHAP ordering/truncation, and bias/None filtering are all u
- `asxos/cli/thesis.py:1-719` — No test exercises the CLI module: tests cover asxos.domain.theses.service directly, with no CliRunner invocation of the typer commands, parsing helpers, alias registratio

### domain/portfolio
- `asxos/domain/portfolio/build.py:272-355` — persist() (lines 272-355) has no covering test: idempotent DELETE-then-reinsert, RETURNING run_id, both executemany batch inserts (target_allocations, proposed_trades), a
- `asxos/domain/portfolio/monitor_loader.py:41-249` — No test coverage for load_run_inputs/_load_benchmark/list_persisted_runs; the no-lookahead bound, entry-anchor gate, and equal-weight proxy growth index are untested.
- `asxos/domain/portfolio/volatility.py:63-108` — load_vols_for_symbols (async DB entry point: empty-symbols early return, ROW_NUMBER/ANY($1::text[]) query, per-symbol grouping, ValueError silent-omit loop at 104-107) ha

### domain/tax
- `asxos/domain/tax/cgt.py:110-140` — cgt_break_even_price (lines 110-140) has no covering test in tests/; it is live in production via position_monitor/display.py:223.
- `asxos/domain/tax/lots.py:105-106` — Line 24 divides cost_base_normal by lot.quantity with no zero guard; a zero-quantity lot raises ZeroDivisionError instead of a domain error, and partial-draw brokerage pr

## P2

### domain/brief
- `asxos/domain/brief/collectors/market_context.py:62-65` — The .get() bug has zero genuine coverage; test helper _make_row fakes a .get lambda absent from real asyncpg.Record
- `asxos/domain/brief/collectors/tax_operational.py:23-95` — collect_tax_operational has no covering test; test_brief_composer.py only uses the literal 'tax_operational' label.
- `asxos/domain/brief/collectors/underlying_drivers.py:26-110` — collect_underlying_drivers (lines 26-110) has no covering test; test_brief_v2_sections.py only exercises cross_layer_observations directly, never the collector. Untested:
- `asxos/domain/brief/collectors/wealth_state.py:23-134` — collect_wealth_state has no covering test; test_brief_composer.py only uses the literal string 'wealth_state' and never invokes the collector. Branches (no_data, cash-rat

### domain/other
- `asxos/domain/position_monitor/fetcher.py:131-180` — The two public async entry points fetch_price_data() (lines 131-161) and fetch_macro_data() (lines 164-180) have no covering tests; tests/test_position_monitor.py covers
- `asxos/domain/research/alpha_eval.py:259-321` — evaluate() only computes deciles for prob_col, never iterating score_cols, despite the module/evaluate docstring promising score-variant comparison across prob_up/composi
- `asxos/domain/research/alpha_loader.py:69-84,142-159` — load_panel and load_factor_panel (SQL panel construction, NUMERIC->float coercion, empty-DataFrame return, rn0+h join correctness) are entirely untested
- `asxos/domain/signals/loader.py:128, 136-150, 177-188, 230-234` — The `symbols is not None` batched-load path (the three `= ANY($n)` SQL branches for prices line 144, fundamentals line 183, caps line 232) has no test executing it; all l
- `asxos/domain/signals/loader.py:42-64, 122-251` — The include_adj_close=True / price_basis="adj_close" v1_6 shadow path (loader.py lines 56-57, 68-76, 85, 134-135, 170-171) has no test that executes it at runtime; only t
- `asxos/domain/underlyings/service.py:241-280` — get_5d_moves (lines 241-280) has no direct unit/integration test

### domain/regime
- `asxos/domain/regime/indicators.py:19-56` — No test exercises load_from_db; the hard-fail branches (row is None, missing_critical) and the Decimal coercion at line 47 are uncovered.

### domain/themes+theses
- `asxos/domain/themes/service.py:304-314 (attach_thesis theses.themes sync)` — The denormalised theses.themes array sync inside attach_thesis (UPDATE theses SET themes = array_append(...) WHERE status NOT IN ('exited','expired') AND NOT ($1 = ANY(th
- `asxos/domain/theses/service.py:568-697` — update_analyst_consensus, log_analyst_action, and set_earnings have NO covering tests; their existence checks, diff serialisation, and transaction behaviour are unverifie

### ingestion
- `asxos/ingestion/fundamentals.py:65-93` — fetch_and_upsert_fundamentals has no direct covering test: test_symbol_failure_does_not_raise patches it with a side_effect, so the actual INSERT...ON CONFLICT SQL, $1..$
- `asxos/ingestion/news.py:185-230` — upsert_news() has no test exercising real behaviour; the only test reference (tests/test_ingest_news_job.py:60) patches it out with AsyncMock, leaving the SQL string, jso

### other
- `asxos/brief/email.py:33-50` — send_brief() is never invoked directly by any test; the refusal guard (lines 38-41) and subject construction (line 35) are uncovered.
- `asxos/clients/fred.py:46-110` — No test exercises FREDClient, get_series, latest_value, _get, _is_retryable, or get_client (lines 46-110, 113-121).
