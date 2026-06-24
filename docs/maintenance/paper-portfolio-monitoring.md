# Paper-portfolio performance monitor (M13.8+)

The **scoreboard** for persisted `build-portfolio` runs. It measures whether the
model portfolio *performs*, as distinct from whether the *pipeline ran*. Treat
it as a strategy-incubation book: a single run's realised P&L is one noisy data
point and is **never** alpha proof.

## What it does

For a persisted run (`rebalance_runs` + `target_allocations` + `proposed_trades`)
it replays the entered positions forward against realised `prices`, and reports:

- portfolio NAV path, total return (`adj_close`, dividend/split adjusted) and
  price return (`close`); cash vs invested
- benchmark-relative return (`AXJO.INDX`; falls back to an equal-weight
  universe-breadth **proxy**, and flags the gap if neither is available)
- equal-weight vs model-weight baselines (selection quality)
- per-position return, P&L and contribution; sector attribution
- hit rate, average winner / loser, payoff ratio
- max drawdown, annualised realised volatility, one-way turnover
- performance bucketed by `signal_label`, `prob_up`, and `expected_return`
- estimated transaction costs (configurable bps — an **assumption**, not measured)
- explicit missing-data events (no silent forward-fill)

Every figure is evidence-labelled in the report: `[VERIFIED]` (from data),
`[INFERRED]` (an assumption), `[MISSING]` (not yet measurable / data absent).

## Architecture

| Layer | File | Role |
|---|---|---|
| Pure analytics | `asxos/domain/portfolio/monitor.py` | Decimal-only metrics; no I/O, no lookahead |
| DB loader | `asxos/domain/portfolio/monitor_loader.py` | assembles typed `MonitorInputs` from the DB |
| CLI | `scripts/monitor_paper_portfolio.py` | run, render, persist |
| Storage | `migrations/0024_paper_portfolio_perf.sql` | `paper_portfolio_run_metrics` / `_nav` / `_position_perf` |
| Tests | `tests/test_monitor_paper_portfolio.py` | pure-function tests on synthetic data |

It builds on the existing single-point evaluator `paper_trade.evaluate` (P&L vs
holding cash), reusing its `ProposedTrade` types and `total_traded_aud`
convention, and wraps the richer time-series/attribution layer around it.

## Discipline guarantees (enforced in code)

- **No lookahead** — the loader only selects `dt <= eval_as_of`; `compute_report`
  raises if any price date exceeds the eval date.
- **No silent forward-fill** — a missing bar is recorded as a `MissingPrice`
  event; carrying the last price requires `--forward-fill` and is flagged on the
  NAV point and in the event log.
- **Not-yet-measurable is first-class** — with 0 forward trading days since
  entry, the report returns `measurable=False` and `None` headline metrics
  rather than a fabricated 0%.
- **Preserves data** — all writes are idempotent UPSERTs; existing runs and
  holdings are never modified.

## Usage

```bash
# single run, evaluated as of today, persisted
python scripts/monitor_paper_portfolio.py --run-id 1

# every persisted run
python scripts/monitor_paper_portfolio.py --all

# as of a specific date (no price after this date is used)
python scripts/monitor_paper_portfolio.py --run-id 1 --as-of 2026-07-17

# compute only, no DB writes, JSON output
python scripts/monitor_paper_portfolio.py --run-id 1 --no-persist --format json

# override cost assumptions
python scripts/monitor_paper_portfolio.py --all --commission-bps 10 --slippage-bps 7
```

`--run-id` and `--all` are mutually exclusive; one is required. Persistence is on
by default (`--no-persist` to disable) and requires migration `0024` applied.

## Setup / migration

Apply the migration via Supabase MCP, then bump the API drift constant:

```
mcp__supabase__apply_migration(project_id="gxjqezqndltaelmyctnl",
    name="0024_paper_portfolio_perf", query=<file contents>)
```

`asxos/api/main.py: REQUIRED_MIGRATIONS` is bumped to 79 in the same change. The
drift check is `count < REQUIRED_MIGRATIONS`, so applying the migration ahead of
the deploy does not break the running API.

## Benchmark gap (known limitation)

`AXJO.INDX` is **not yet ingested** by `sync_prices`, so the official S&P/ASX 200
benchmark is unavailable. The monitor reports this and falls back to an
equal-weight universe-breadth proxy (clearly labelled). To enable the real
benchmark, add `AXJO.INDX` to the `sync_prices` ingestion (it already drives
`snapshot_portfolio`'s `benchmark_xjo_close`).

## Scheduling

Not scheduled. To run weekly after `build_portfolio`, add a Render cron invoking
`python scripts/monitor_paper_portfolio.py --all` — proposed, not enabled.

## What this does NOT establish

Realised paper P&L is not statistical evidence of alpha. `expected_return` is
uncalibrated (treat `prob_up` as the conviction signal). The v1 allocator is
risk-blind to market-wide co-movement. See `.claude/rules/portfolio-conventions.md`
and the alpha-research audit (Prompt 2) for the validation work that *would*
establish edge.
