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

**`migrations/` (currently through 0028) is the canonical schema** — roughly 40
tables across the signal, portfolio, tax, paper-trade, research-store, FX and
position-monitor subsystems. The list below is a partial overview of the core
tables, **not exhaustive** — do not trust it for completeness; read the migrations.
No `user_id` anywhere. NUMERIC(18,6) on every monetary or statistical column.

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
- `make check` — ruff + mypy + pytest (enforced in CI by the `full-check` workflow on PRs to `main` and `claude/**` pushes; `targeted-ml-tests` is the fast ML lane)
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

One additional runtime gap (not a collection-error, fails during execution):

- `tests/test_train_walk_forward.py::test_train_model_a_returns_valid_result` — requires
  `lightgbm` in the venv. The system Python has it; the sandbox venv does not. Passes
  on Render.

## Known coverage gaps (verify, don't assume)

Coverage prose rots. Verify against the suite (`pytest --co -q`) before trusting
any "X is covered" claim — including this file. Current known gaps:

- **§7 Medicare + CGT income tax are now wired into the aggregator** (Phase 1).
  `tax_view_*` (`asxos/domain/tax/positions.py`) emit a `CgtTaxOutcome`
  (income_tax + medicare + total_tax) on the net-gain branch: individual = marginal
  + 2% (TC-11 $1,950, asserted end-to-end); SMSF = 15% on the ECPI-adjusted base,
  Medicare 0. One residual item (not blocking): the cents-quantization of the CGT
  ledger lines is a documented choice (bases keep full precision). Previously
  unverified SMSF ECPI-on-CGT stacking path **closed by TC-24** (spec v1.4, §5.2,
  §4.2): $10,000 discountable gain, 60% pension → net gain $6,666.67, taxable base
  $2,666.67, fund tax $400.00. See `tests/test_tax_positions.py::test_tc24_smsf_ecpi_stacks_with_cgt_discount`.
- **Div 296 TC-20 (cost-base reset, s 296-50) is unimplemented**, not merely
  untested. `div296_reset_date` is a config field nothing consumes yet. Building
  it is a spec-governed change (non-negotiable #8 — requires a spec amendment).
- **TC-21 (45-day franking warning, s 207-145) is now implemented** in
  `asxos/domain/tax/dividends.py::check_45_day_warnings` + wired into
  `tax_view_smsf()`. Four tests in `test_tax_positions.py` cover the positive
  case and three boundary cases. Credits are never auto-removed (§4.3).

## Auto-activating rules

`.claude/rules/` files attach automatically when working in matching paths:

- `api-conventions.md` — FastAPI route patterns
- `ml-conventions.md` — feature engine, model artefacts, signal threshold ladder, numpy adapter
- `screening-conventions.md` — rule JSON schema, walk-forward methodology
- `job-conventions.md` — JobMonitor, pipeline guards, idempotency, env vars

## Subagents — delegation policy

`.claude/agents/` holds 13 subagents — 11 dev-side (architecture/quality/docs) plus
2 finance-domain conformance agents (`tax-spec-conformance`, `portfolio-invariant-guard`,
routed in the table below); see `.claude/agents/README.md`.
They are **advisory by default**: most are read-only and return analysis, designs,
or specs as text that the main loop then implements. Only `refactoring-expert`
(code) and `technical-writer` (docs) can mutate files. `security-engineer` and
`performance-engineer` may run read-only tooling via Bash but never edit.

**Route dev work through these agents — do not freelance work that has an owner.**
Before acting, consult the relevant agent:

| About to… | Consult first |
|---|---|
| Start a feature whose scope isn't already a written spec | `requirements-analyst` |
| Add a module / cross-domain dependency / structural change | `system-architect` |
| Design or change an API route, DB schema/migration, auth, or write-path job | `backend-architect` |
| Add, swap, or upgrade a dependency or external service | `tech-stack-researcher` |
| Touch a hot path (API query, job throughput, ML inference, vol calc) | `performance-engineer` |

**After any non-trivial code change, before committing, run the review loop:**

1. `security-engineer` — if the change touches secrets, external input, dependencies, or financial/PII data.
2. `refactoring-expert` — reduce complexity/duplication without changing behaviour.
3. `technical-writer` — update affected docs, runbooks, and docstrings.

`deep-research-agent` and `learning-guide` are on-demand (research / explanation),
not part of the per-change loop. `frontend-architect` is dormant (no v1 frontend).

Delegate proactively: prefer dispatching the relevant agent over doing its job
inline — specialised review should happen by default, not only when asked.

The eleven above are domain-neutral DEV agents. Two **finance-domain conformance**
agents (also advisory, read-only) now sit alongside them — use them proactively:

| About to touch… | Consult |
|---|---|
| `asxos/domain/tax/*` or `tests/test_tax_*` | `tax-spec-conformance` (spec↔test↔code) |
| `asxos/domain/portfolio/*` | `portfolio-invariant-guard` (firewall, hard-fails, Decimal-only) |

A runtime in-product tax/portfolio LLM agent is a structural **NO** (personal-advice
firewall + Decimal-only determinism). Signals/ML conformance is already covered by
`ml-conventions.md` + `targeted-ml-tests`; no agent for it.

### Review gate (enforced)

`.claude/hooks/review-gate.sh` (wired via `.claude/settings.json` as a `PreToolUse`
hook on Bash) **blocks `git commit` when Python files are staged** until the review
loop has run for that exact staged diff. Flow: stage → attempt commit → the hook
denies with instructions → run `security-engineer` / `refactoring-expert` /
`technical-writer` on the staged diff → `touch .claude/.review-passed-<sha>` (the
hook prints the exact marker path) → retry the commit. The marker is keyed to the
staged-diff hash, so any further change re-arms the gate.

Honest limit: the hook cannot itself spawn an agent or verify one ran — it forces a
deliberate step (write the marker) rather than guaranteeing the review happened.
Writing the marker without running the loop is an explicit, visible bypass. Doc-only
and config-only commits (no staged `*.py`) are not gated.

## Custom slash commands

`.claude/commands/` has 20 domain and lifecycle commands carried verbatim from the previous repo. The seven domain commands (`signal-pipeline`, `model-experiment`, `regime-detection`, `tax-optimise`, `dashboard-component`, `feature-add`, `prompt-compose`) are the most-used.
