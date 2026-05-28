---
title: M-Thesis-0 — Feature plan
location: docs/strategy/M-THESIS-0_FEATURE_PLAN.md
status: ready to implement
milestone: M-Thesis-0
references:
  - docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md Part 12.5
  - docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md Parts A, D, J, L
estimated_effort: 2-3 days
owner: james
last_updated: 2026-05-28
---

# M-Thesis-0 — Feature plan

The V2 prerequisite milestone. Three deliverables, no thesis logic yet — this clears the runway so M-Thesis-1 onward have a clean target.

## 1 — Feature overview

**Problem.** The V2 build sequence (M-Thesis-1 → M-First-Real-Week) adds 5 new domain packages, 9 new tables, and ~15 new CLI commands on top of a CLI module that is already 1472 lines in a single file and a domain tree that doesn't yet have homes for the new concepts. Without preparation, M-Thesis-1 lands in a codebase that fights it at every turn.

**Solution.** Three concrete preparations:

1. **Split the CLI.** Move 10 existing Typer sub-apps and ~25 commands from [asxos/cli/main.py:1-1472](asxos/cli/main.py) into per-command modules. Keep public command surface byte-identical (no rename, no signature change). After this, adding 5 new sub-apps for `thesis`, `theme`, `watchlist`, `idea`, `brief` is a localised edit.
2. **Scaffold the V2 domain packages.** Create `asxos/domain/{theses,themes,regime,underlyings,brief}/` with `__init__.py`, a minimal `types.py`, and a stub module per architect's Part D layout. No business logic yet — just enough that imports resolve.
3. **Add `portfolio_daily_snapshots` table + daily ingest job.** Per spec decision D5. Required for the V2 brief's "YTD +250bps" framing and historical wealth-state queries. Cron at 20:40 UTC weekdays (after `sync_prices` 20:30, before `compose_brief` 21:00).

**Out of scope (deliberate).** Symbol migration (D1 revised — codebase + EODHD already use `.AU`/`.US`). Any thesis/theme/regime/underlying *logic*. Any change to existing CLI command behaviour. Any change to existing jobs.

**Success criteria.**

- `asx` command surface identical pre- and post-split (verified by golden-file CLI help test).
- All existing tests pass with zero modification.
- `from asxos.domain.theses import types` resolves and returns a `Thesis` dataclass stub.
- `portfolio_daily_snapshots` table exists in Supabase; daily cron runs successfully for 3 consecutive weekdays and writes one row per run.
- `render.yaml` includes the new cron service; `make check-drift` reports clean.
- New tables added to [scripts/backup_irreplaceable.sh](scripts/backup_irreplaceable.sh) — except: `portfolio_daily_snapshots` is **re-derivable** from `prices` + `holding_lots`, so it does NOT go in the backup. Document this in the migration comment.

## 2 — Technical design

### 2.1 — Architecture overview

```
asxos/cli/                            asxos/domain/                jobs/
├── __init__.py                       ├── theses/   NEW (stubs)    ├── snapshot_portfolio.py  NEW
├── main.py        ← thin entrypoint  ├── themes/   NEW (stubs)    └── (existing jobs, untouched)
├── _common.py     NEW (helpers)      ├── regime/   NEW (stubs)
├── predict.py     NEW                ├── underlyings/ NEW (stubs)
├── signal.py      NEW                ├── brief/    NEW (stubs — distinct from existing asxos/brief/)
├── holdings.py    NEW                └── (existing: portfolio, tax, signals, ...)
├── tax.py         NEW
├── model.py       NEW                migrations/
├── journal.py     NEW                └── 0011_portfolio_daily_snapshots.sql  NEW
├── profile.py     NEW
├── portfolio.py   NEW                render.yaml
├── news.py        NEW                └── + asxos-snapshot-portfolio cron service
├── brief.py       NEW
└── _registry.py   NEW (assembles sub-apps onto root)
```

### 2.2 — CLI split mechanics

The existing [asxos/cli/main.py](asxos/cli/main.py) follows a discoverable pattern: a root `app = typer.Typer(...)` plus several `*_app = typer.Typer(...)` instances mounted via `app.add_typer(*_app, name="...")`. The split preserves this exactly — each sub-app moves to its own file and is re-imported into `main.py`.

**Concrete grouping** (line ranges from current `main.py`):

| New file | Commands moved | Source lines |
|---|---|---|
| `cli/predict.py` | `predict` | 31-87 |
| `cli/signal.py` | `signal` | 89-142 |
| `cli/holdings.py` | `import-holdings` + `_infer_currency` helper | 143-248 |
| `cli/tax.py` | `tax-view`, `tax-action` | 249-425 |
| `cli/model.py` | `model_app` + `activate`, `list` | 427-519 |
| `cli/journal.py` | `journal_app` + `add`, `list`, `review` | 521-705 |
| `cli/brief.py` | `brief` (existing, V1) | 706-741 |
| `cli/profile.py` | `profile_app` + `init`, `show`, `activate`, `list`, `_require_personal_use` | 743-966 |
| `cli/news.py` | `news_app` + `signoff` | 968-977, 1397-1471 |
| `cli/portfolio.py` | `portfolio_app` + root-level `build-portfolio`, `propose-trades` + `show`, `history`, `paper-review`, `signoff` | 979-1396 |
| `cli/_common.py` | `console = Console()` and any helpers used across multiple sub-apps | (extract as found) |
| `cli/main.py` | Thin: `app = typer.Typer(...)` + imports + `app.add_typer(...)` calls | new 30-50 lines |

**Public surface preservation.** The entrypoint `asx` stays bound to `asxos.cli.main:app` (per `pyproject.toml` `[project.scripts]`). Command names, args, options, help text — all byte-identical. The only externally observable difference: `asx --help` output ordering may shift if sub-apps register in a different order; preserve original order to keep golden-file tests passing.

**`_require_personal_use()`** is referenced by `profile_app` only today, but the regulatory firewall ([.claude/rules/portfolio-conventions.md](.claude/rules/portfolio-conventions.md)) requires every CLI entry point that touches portfolio data to call it. Move to `cli/_common.py` so future CLIs (thesis, brief) can import from one place.

### 2.3 — Domain scaffolding (deliberately minimal)

Each new package gets:

```python
# asxos/domain/theses/__init__.py
"""Thesis domain — opened by M-Thesis-0 (scaffolding only).

Real implementation lands in M-Thesis-1. This package exists now so
imports resolve and the architecture is visible from `git log`.
"""

# asxos/domain/theses/types.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class Thesis:
    """Placeholder — full schema in M-Thesis-1.

    Mirrors `theses` table columns per V2 spec Part 6.1 (with D3 revision:
    status enum includes 'research').
    """
    thesis_id: int
    symbol: str
    status: str  # 'research' | 'watching' | 'active' | 'exited' | 'expired'
    # ... fields added incrementally in M-Thesis-1
```

Five packages get this treatment: `theses`, `themes`, `regime`, `underlyings`, `brief`. Each has `__init__.py` (docstring + nothing else) and `types.py` (one frozen dataclass stub).

**Why bother with stubs now?** Two reasons:
1. Architect's Part D layout becomes file-visible immediately. Future PRs land in the right package without an "and we'll create the folder when we get there" step.
2. The new `asxos/domain/brief/` is intentionally distinct from existing top-level [asxos/brief/](asxos/brief/) (V1 composer). Creating the new package now signals the supersession path — V1 stays alive until M-Brief-V2-Sections cuts over.

**No tests for stubs.** The dataclasses do nothing yet. M-Thesis-1 adds the first real tests when the schema lands.

### 2.4 — `portfolio_daily_snapshots` table

**Migration: [migrations/0011_portfolio_daily_snapshots.sql](migrations/0011_portfolio_daily_snapshots.sql)** (NEW)

```sql
-- 0011_portfolio_daily_snapshots.sql
-- M-Thesis-0: daily wealth snapshot for V2 brief's YTD/MTD framing
-- (spec decision D5). Re-derivable from prices + holding_lots —
-- NOT included in scripts/backup_irreplaceable.sh.
--
-- One row per calendar date. Job is weekday-only (UTC Sun-Thu) so weekend
-- rows are absent. YTD computations must handle gaps with COALESCE/window
-- functions, not assume row-per-day.
--
-- benchmark_xjo_close stores the raw XJO (price-only) close. benchmark_tr_level
-- is computed by the job from XJO + trailing dividend yield per spec D4.
-- If yield source is unavailable on a given day, benchmark_tr_level stays NULL
-- and the brief degrades to price-only framing in section 1 (no hard-fail —
-- this is a brief-quality concern, not infra).

CREATE TABLE portfolio_daily_snapshots (
    as_of                  DATE         PRIMARY KEY,
    capital_aud            NUMERIC(18,6) NOT NULL,
    holdings_mv_aud        NUMERIC(18,6) NOT NULL,
    cash_aud               NUMERIC(18,6) NOT NULL,
    benchmark_xjo_close    NUMERIC(18,6),
    benchmark_tr_level     NUMERIC(18,6),
    trailing_div_yield_pct NUMERIC(8,6),
    holdings_count         INTEGER       NOT NULL,
    ingested_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_portfolio_daily_snapshots_asof
    ON portfolio_daily_snapshots(as_of DESC);
```

**Column rationale.**

- `capital_aud` = `holdings_mv_aud + cash_aud`. Stored explicitly (not derived) so future schema changes to cash accounting don't break historical rows.
- `cash_aud` source: M13 profile already tracks `cash_floor_pct`. For v1, cash = `capital_aud - holdings_mv_aud`; once an explicit cash-balance table lands (post-M13.8 paper trade), the snapshot job sources from there.
- `holdings_count` is a cheap denormalisation that lets the brief say "28 active theses" without a second query.
- `trailing_div_yield_pct` stored alongside `benchmark_tr_level` so the TR derivation is auditable from the row alone.

### 2.5 — Daily ingest job

**File: [jobs/snapshot_portfolio.py](jobs/snapshot_portfolio.py)** (NEW)

Pattern follows existing [jobs/sync_prices.py](jobs/sync_prices.py) and [jobs/ingest_sentiment.py](jobs/ingest_sentiment.py) — `JobMonitor` async context manager from [asxos/jobs/utils/job_monitor.py](asxos/jobs/utils/job_monitor.py), `init_pool()` / `close_pool()` bracketing, hard-fail on missing inputs.

```python
#!/usr/bin/env python
"""
Snapshot today's portfolio capital + benchmark — M-Thesis-0.

Computes (capital_aud, holdings_mv_aud, cash_aud, benchmark_xjo_close,
benchmark_tr_level, trailing_div_yield_pct, holdings_count) and UPSERTs
into portfolio_daily_snapshots.

Schedule: weekdays 20:40 UTC (after sync_prices 20:30, before compose_brief 21:00).

Hard-fail conditions (per CLAUDE.md non-negotiable #10):
  - sync_prices job_runs.status != 'success' for as_of (UpstreamBlocked)
  - XJO close missing from prices on as_of (hard error — XJO is a primary input)
  - holdings_mv_aud computation fails for any holding (hard error)

Soft-degrade conditions (NULL column instead of failure):
  - trailing_div_yield_pct unavailable from source → benchmark_tr_level=NULL

Default: yesterday's date (consistent with sync_prices pattern). Backfill: --from.
"""
```

**Computation order (one transaction):**

1. Resolve `as_of` (default = `date.today() - timedelta(days=1)` matching sync_prices semantics).
2. Verify upstream — `SELECT status FROM job_runs WHERE job_name='asxos-sync-prices' AND as_of=$1 AND status='success'`. Missing → raise `UpstreamBlocked` (already-defined exception used by other jobs).
3. Compute `holdings_mv_aud`:
   ```sql
   SELECT SUM(ch.quantity * p.close * COALESCE(fx.rate, 1)) AS mv,
          COUNT(*) AS n
   FROM current_holdings ch
   JOIN prices p ON p.symbol = ch.symbol AND p.dt = $1
   LEFT JOIN fx_rates fx ON fx.dt = $1 AND fx.pair = 'AUDUSD'
                        AND ch.symbol LIKE '%.US'
   ```
   (FX join only for `.US` symbols — AU symbols use `rate=1`.)
4. Compute `cash_aud` per profile (M13 `profiles.cash_floor_pct × capital_aud_baseline` for v1; post-paper-trade will source from a cash ledger).
5. `capital_aud = holdings_mv_aud + cash_aud`.
6. Fetch XJO close: `SELECT close FROM prices WHERE symbol='XJO.INDX' AND dt=$1`. Hard-fail if missing.
7. Fetch trailing dividend yield from ASX/RBA monthly stats source (defer the actual fetcher to a stub function `fetch_trailing_div_yield(as_of) -> Decimal | None` for v1 — returns `None` until D4's external source is wired). When `None`, `benchmark_tr_level` stays `None`; brief degrades.
8. UPSERT one row into `portfolio_daily_snapshots`. `monitor.rows_written = 1`.

**Backfill mode (`--from YYYY-MM-DD`).** Loops day-by-day. Used once after migration to populate the table from the earliest holding-lot acquisition date forward, so YTD framings work from day one of the brief.

### 2.6 — `render.yaml` addition

Append after `asxos-build-portfolio`:

```yaml
  # Daily portfolio snapshot — 06:40 AEST weekdays (20:40 UTC prior day).
  # Runs after sync_prices (20:30 UTC) so prices are fresh; before
  # compose_brief (21:00 UTC) so the brief's section 1 has today's row.
  - type: cron
    name: asxos-snapshot-portfolio
    runtime: python
    region: oregon
    plan: starter
    branch: main
    buildCommand: pip install -e ".[ml]"
    schedule: "40 20 * * 0-4"
    command: ASXOS_PERSONAL_USE=1 python jobs/snapshot_portfolio.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.13
      - key: ASXOS_PERSONAL_USE
        value: "1"
      - fromService:
          type: web
          name: asxos-api
          envVarKey: DATABASE_URL
      - key: HEALTHCHECK_URL_SNAPSHOT_PORTFOLIO
        sync: false
```

Healthchecks UUID provisioned via `mcp__render__update_environment_variables` after merge.

### 2.7 — Data flow (the daily picture)

```
06:30 AEST sync_prices ───────► prices.{XJO.INDX, all holdings}
                                       │
06:40 AEST snapshot_portfolio ◄────────┘
   │
   ├─ upstream guard: job_runs.sync_prices status='success'
   ├─ compute holdings_mv_aud  (current_holdings × prices × fx)
   ├─ compute cash_aud         (profile cash_floor for v1)
   ├─ fetch XJO close
   ├─ fetch trailing div yield (stub → NULL for v1)
   ├─ derive benchmark_tr_level (if yield available)
   └─ UPSERT portfolio_daily_snapshots(as_of, ...)
                                       │
07:00 AEST compose_brief reads ◄───────┘
   (V1 brief: ignores the new table; V2 brief in later milestone reads it)
```

## 3 — Implementation plan

### Phase 1 — CLI split (Day 1, ~6 hours)

- [ ] Read [asxos/cli/main.py](asxos/cli/main.py) end to end; note any cross-references between sub-apps.
- [ ] Create `cli/_common.py` with `console`, `_require_personal_use`, any extracted helpers.
- [ ] Move each sub-app to its own file in the order listed in §2.2. After each move: `asx --help` and `asx <subcommand> --help` must match the pre-split output (capture as golden files in `tests/cli/test_help_surface.py`).
- [ ] Final `cli/main.py` is ~50 lines: imports + `app = typer.Typer(...)` + a sequence of `app.add_typer(...)` calls in original order.
- [ ] Run `pytest tests/` — zero failures. Run `ruff check` and `mypy asxos/cli/` — zero new errors.
- [ ] Commit: `refactor(cli): split asxos/cli/main.py into per-command modules`. No behaviour change.

### Phase 2 — Domain scaffolding (Day 1, ~2 hours)

- [ ] `mkdir asxos/domain/{theses,themes,regime,underlyings,brief}`
- [ ] For each: write `__init__.py` (docstring) and `types.py` (one frozen dataclass stub mirroring the relevant V2 spec Part 6 table).
- [ ] Add a single import smoke test in `tests/test_domain_imports.py`: `from asxos.domain.{theses,themes,regime,underlyings,brief} import types`.
- [ ] Commit: `feat(domain): scaffold V2 packages (theses, themes, regime, underlyings, brief)`. No logic.

### Phase 3 — Migration + job (Day 2, ~4 hours)

- [ ] Write [migrations/0011_portfolio_daily_snapshots.sql](migrations/0011_portfolio_daily_snapshots.sql) per §2.4.
- [ ] Apply via `mcp__supabase__apply_migration` (CLAUDE.md non-negotiable #2 — never use the dashboard).
- [ ] Verify table + index via `mcp__supabase__execute_sql` `\d portfolio_daily_snapshots`.
- [ ] Write [jobs/snapshot_portfolio.py](jobs/snapshot_portfolio.py) per §2.5. Reuse `JobMonitor`, `init_pool`/`close_pool`, `UpstreamBlocked` exception, argparse `--from` pattern from sync_prices.
- [ ] Write `tests/test_snapshot_portfolio_job.py` covering: happy path with mocked prices + holdings; missing upstream raises UpstreamBlocked; missing XJO close raises hard error; missing trailing yield leaves benchmark_tr_level NULL.
- [ ] Run job locally against dev DB for yesterday: `python jobs/snapshot_portfolio.py`. Verify single row written; check NUMERIC(18,6) precision preserved.
- [ ] Commit: `feat(jobs): add portfolio_daily_snapshots table + daily snapshot job (M-Thesis-0)`.

### Phase 4 — Cron + drift + backfill (Day 2-3, ~3 hours)

- [ ] Add `asxos-snapshot-portfolio` block to [render.yaml](render.yaml) per §2.6.
- [ ] Commit + push. Render auto-deploys.
- [ ] Provision Healthchecks.io UUID; set `HEALTHCHECK_URL_SNAPSHOT_PORTFOLIO` via `mcp__render__update_environment_variables`.
- [ ] Run `make check-drift` — must report clean.
- [ ] Backfill from earliest holding-lot acquisition: `python jobs/snapshot_portfolio.py --from YYYY-MM-DD`. Verify N weekday rows inserted.
- [ ] Wait for first weekday auto-run; verify `job_runs` row + `portfolio_daily_snapshots` row + Healthchecks ping arrived.
- [ ] Commit: `infra: schedule asxos-snapshot-portfolio weekdays 20:40 UTC`.

### Phase 5 — Documentation update (Day 3, ~1 hour)

- [ ] Update [.claude/rules/job-conventions.md](.claude/rules/job-conventions.md) "Daily Pipeline" block to include the new 20:40 UTC row.
- [ ] Update [CLAUDE.md](CLAUDE.md) database schema reference if it enumerates tables (it does at "Ten tables" — bump to eleven, add the row, note "re-derivable; not backed up").
- [ ] Update spec changelog with M-Thesis-0 completion line.
- [ ] Commit: `docs: M-Thesis-0 complete — pipeline + schema reference updated`.

**Total estimate: 16 hours over 2-3 calendar days.** Solo-developer rule (double the initial estimate) suggests planning for 4 days if other work intrudes.

## 4 — File changes summary

**New files (15):**

```
asxos/cli/_common.py
asxos/cli/_registry.py            # OPTIONAL — only if main.py gets messy
asxos/cli/predict.py
asxos/cli/signal.py
asxos/cli/holdings.py
asxos/cli/tax.py
asxos/cli/model.py
asxos/cli/journal.py
asxos/cli/brief.py
asxos/cli/profile.py
asxos/cli/news.py
asxos/cli/portfolio.py
asxos/domain/theses/{__init__.py, types.py}
asxos/domain/themes/{__init__.py, types.py}
asxos/domain/regime/{__init__.py, types.py}
asxos/domain/underlyings/{__init__.py, types.py}
asxos/domain/brief/{__init__.py, types.py}
migrations/0011_portfolio_daily_snapshots.sql
jobs/snapshot_portfolio.py
tests/cli/test_help_surface.py
tests/test_domain_imports.py
tests/test_snapshot_portfolio_job.py
```

**Modified files (4):**

```
asxos/cli/main.py             → thinned from 1472 lines to ~50
render.yaml                   → +1 cron service block
.claude/rules/job-conventions.md → +1 line in Daily Pipeline table
CLAUDE.md                     → schema reference: 10 → 11 tables
```

## 5 — Dependencies

**No new Python packages.** Reuses asyncpg, typer, httpx, dataclasses — all in `pyproject.toml` already.

**New environment variables (1):**

```
HEALTHCHECK_URL_SNAPSHOT_PORTFOLIO   # set via mcp__render__update_environment_variables
```

**External services:** Healthchecks.io UUID to provision (one new check). Resend, EODHD, Supabase, Render — all unchanged.

## 6 — Risk register

| # | Risk | Category | Mitigation |
|---|---|---|---|
| R1 | CLI split breaks `asx --help` output ordering, breaking downstream scripts | LOW | Golden-file test captures pre-split output; post-split asserts byte-equality. |
| R2 | Sub-app cross-references (e.g. `cli/portfolio.py` imports a helper from `cli/profile.py`) create circular imports | MEDIUM | Anything used by ≥2 sub-apps goes to `cli/_common.py` immediately, not at the end. |
| R3 | `current_holdings` view + `prices` join misses a holding (e.g. universe-inactive symbol) on snapshot day, undercounting capital | MEDIUM | Hard-fail if any `current_holdings` row has no matching `prices` row for as_of. Add test. |
| R4 | XJO symbol in `prices` table is `XJO.INDX` not `XJO.AU` (or vice versa) — depends on EODHD ingest convention | LOW | Verify with `SELECT DISTINCT symbol FROM prices WHERE symbol LIKE 'XJO%'` before writing job. Pin the chosen symbol in a module-level constant. |
| R5 | Trailing dividend yield source unidentified (D4 said "ASX/RBA monthly stats" but didn't pin the endpoint) | LOW (deferred) | Stub returns `None`; `benchmark_tr_level` stays NULL until the real fetcher lands. V1 brief degrades to price-only framing. M-Thesis-1 or M-Market-Context can pick this up. |
| R6 | `cash_aud` derivation is wrong because cash accounting doesn't exist yet in M13 | MEDIUM | v1: derive as `profile.cash_floor_pct × profile.capital_aud_baseline`. Document the limitation in the job docstring. Post-paper-trade (M13.8) revisits this with a real cash ledger. |
| R7 | Render cron block formatting error breaks `make check-drift` for unrelated services | LOW | YAML-validate before push; smoke-test with a no-op command before flipping to real command. |
| R8 | Healthchecks UUID forgotten → cron runs but deadman never fires → silent failure mode | MEDIUM | Phase 4 explicitly verifies first ping arrives. Make this a checklist item, not an assumption. |
| R9 | `_require_personal_use()` not invoked from new `cli/brief.py` (it isn't in the V1 either, but V2 will need it) | LOW | Out of scope for M-Thesis-0 — V1 brief already shipped without it. M-Brief-V2-Sections is the right milestone to add the gate. |
| R10 | Backfill of `portfolio_daily_snapshots` from earliest acquisition date is slow on US holdings that need historical FX | LOW | One-off operation, ran manually. Even at 5s/day for 500 weekdays = 40 minutes. Acceptable. |

No BLOCKER risks. R3 and R6 are the two PER-MILESTONE items to re-check at completion.

## 7 — Test strategy

**Unit tests (new):**

- `tests/cli/test_help_surface.py` — golden files: `asx --help`, `asx model --help`, `asx journal --help`, etc. Pre-split state captured; post-split asserts byte-equality.
- `tests/test_domain_imports.py` — `from asxos.domain.theses import types`; assert `types.Thesis` is a frozen dataclass.
- `tests/test_snapshot_portfolio_job.py` — five cases:
  1. Happy path: holdings + prices + XJO + yield all present → row written, ingested_at populated.
  2. Upstream blocked: `sync_prices` not success → `UpstreamBlocked` raised, `job_runs.status='blocked'`, no row in snapshot table.
  3. Missing XJO: hard-fail with clear error message.
  4. Missing yield: row written with `benchmark_tr_level=NULL`, `trailing_div_yield_pct=NULL`.
  5. Idempotency: run twice for same as_of → UPSERT, single row, second run's `ingested_at` is later.

**Integration test (manual):**

- After Phase 4 deploy, observe one weekday auto-run end-to-end: `job_runs` row + `portfolio_daily_snapshots` row + Healthchecks ping.

**Regression coverage:** Existing tests must pass unmodified after the CLI split (Phase 1 gate).

## 8 — Rollout plan

**Feature flag:** None. CLAUDE.md non-negotiable #3 prohibits feature flags. The new table and job are additive — no existing read path depends on them, so a partial deploy can't break anything live.

**Rollback:** Three independent reverts:

1. CLI split: `git revert` the split commit; `main.py` restored.
2. Snapshot table: `DROP TABLE portfolio_daily_snapshots CASCADE` via `mcp__supabase__execute_sql`. No FK dependents (intentional — it's a leaf).
3. Cron: remove the `asxos-snapshot-portfolio` block from `render.yaml`, push, `make check-drift`.

Each is independent — a broken cron doesn't require reverting the CLI split.

**Monitoring after rollout:**

- Healthchecks.io for `HEALTHCHECK_URL_SNAPSHOT_PORTFOLIO` — should ping every weekday at 20:42 UTC ±2 min.
- `SELECT job_name, as_of, status, duration_ms FROM job_runs WHERE job_name='asxos-snapshot-portfolio' ORDER BY as_of DESC LIMIT 7` — should show 5 success rows per trading week.
- `SELECT COUNT(*), MAX(as_of) FROM portfolio_daily_snapshots` — count grows by one each weekday.

## 9 — What this milestone does NOT do

Explicitly out of scope, to prevent scope creep:

- No thesis/theme/regime/underlying/brief *logic* — only stubs.
- No symbol migration (.AU/.US stays — D1 revised).
- No change to existing CLI commands (refactor only — public surface preserved).
- No change to existing jobs.
- No change to V1 brief behaviour (V1 brief still ignores `portfolio_daily_snapshots`).
- No `theses`/`themes`/`thesis_revisions` tables — those land in M-Thesis-1.
- No trailing-dividend-yield fetcher implementation — stub only; M-Thesis-1 or M-Market-Context picks it up.
- No `_require_personal_use()` added to new brief paths — V1 brief never had it; V2 brief will, in M-Brief-V2-Sections.

## 10 — Next steps after merge

1. Wait one trading week. Verify 5 consecutive successful auto-runs of `asxos-snapshot-portfolio`.
2. Verify `make check-drift` clean.
3. Verify `select count(*) from portfolio_daily_snapshots` = 5.
4. Open M-Thesis-1 with `/feature-plan` against the spec's M-Thesis-1 bullet (Part 12.5).
