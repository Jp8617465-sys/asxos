# asxos fundamentals audit handoff for Claude Code

**Date:** 2026-07-04  
**Audience:** Claude Code / future implementation sessions  
**Status:** research and planning only; no code changes implied  
**Repository:** `Jp8617465-sys/asxos`

This document packages a repo-backed audit of math/statistics, decision logic, portfolio risk, software-engineering fundamentals, and language/architecture choices for `asxos`.

Use it as a starting point. Do **not** treat it as an implementation order without verifying live repo state, live DB state, Render state, and any docs that may have changed after this file was written.

---

## 0. Executive summary

The highest-value move is **not** a rewrite and not a new black-box quant brain. The highest-value move is to make the existing math and evidence layers more explicit, more connected, and more decision-aware.

`asxos` already has more of the foundation than a fresh reviewer might assume:

- Model A, signal generation, SHAP, feature contracts, and walk-forward training already exist.
- `alpha_eval.py` already implements serious statistical diagnostics: rank-IC, effective sample size, naive/effective t-statistics, deciles, calibration/Brier, liquidity split, and underpowered-data warnings.
- A point-in-time research-store schema exists and includes security master, corporate actions, financial statements, PIT fundamentals, factor scores, index membership, and estimates.
- A factor-score engine exists for value, quality, momentum, low-vol, gross yield, and value x quality composite.
- A paper-portfolio monitor exists with NAV, total return, turnover, costs, drawdown, realised volatility, benchmark relative performance, missing-price accounting, and buckets.
- Tax math is spec-first and includes Div 296, SMSF ECPI, franking, Medicare, CGT calendar arithmetic, and TC-20 tests.
- Governance and review-agent boundaries exist, but agent DB role scoping is still a real safety gap.

The main gaps are now:

1. **State truth / doc drift:** several docs/backlogs appear stale or historical. Claude should classify current vs stale before building.
2. **Research-store live validation:** the schema/code exists, but live row counts, latest `job_runs`, and Render cron status must be verified.
3. **Risk math:** v1 portfolio construction is still risk-blind to systematic beta/correlation/factor exposure.
4. **Decision math:** `alpha_eval`, factor scores, tax, portfolio monitor, and opportunity-cost logic exist as separate pieces, but there is no explicit decision-evidence layer connecting them.
5. **Agent DB role scoping:** prompt-only SELECT constraints are not a technical control.
6. **Testing fundamentals:** property/metamorphic tests, startup hard-fail tests, and several async/DB branches remain incomplete.
7. **Language strategy:** Python should remain the primary language. Rust can be a future kernel language. Go can be a future ops-tooling language. C++ should only be used indirectly through libraries or for rare kernels.

---

## 1. Operating premise for future Claude sessions

Do not start from a blank slate.

Before proposing new work, classify every candidate item as one of:

- **implemented**
- **implemented but unpopulated**
- **implemented but untested**
- **documented but not wired**
- **explicitly deferred**
- **stale/historical documentation**
- **genuine blind spot**

A lot of wasted Claude time will come from treating stale backlog text as current truth.

---

## 2. What Claude should not rediscover from scratch

### 2.1 Alpha evaluation already exists

`asxos/domain/research/alpha_eval.py` is already a serious evidence engine. It contains:

- `ICSummary`, `DecileResult`, `CalibrationResult`, `LiquiditySplit`, `AlphaReport`
- effective sample-size guard for overlapping forward-return windows
- per-date Spearman rank-IC
- IC summaries with naive and effective t-statistics
- decile spreads with monotonicity and top-minus-upper-mid diagnostics
- calibration/Brier diagnostics
- liquidity split between tradable and illiquid names
- warnings when independent observations are too thin

Evidence pointers:

- `asxos/domain/research/alpha_eval.py:1-27` — module contract and design discipline.
- `asxos/domain/research/alpha_eval.py:41-97` — result dataclasses.
- `asxos/domain/research/alpha_eval.py:107-163` — effective sample size and IC summary.
- `asxos/domain/research/alpha_eval.py:166-226` — decile and calibration functions.
- `asxos/domain/research/alpha_eval.py:229-263` — liquidity split.
- `asxos/domain/research/alpha_eval.py:262-325` — full evaluator and warning logic.

`tests/test_alpha_eval.py` already tests the anti-self-deception features:

- clustered-date effective-N collapse
- effective t-statistic below naive t-statistic
- perfect rank-IC case
- decile monotonicity and top-decile-no-edge pathology
- miscalibration detection
- liquidity-concentrated edge
- thin-data warnings

Evidence pointers:

- `tests/test_alpha_eval.py:1-13` — test intent.
- `tests/test_alpha_eval.py:34-45` — effective sample size.
- `tests/test_alpha_eval.py:64-82` — rank-IC and effective-vs-naive t-stat.
- `tests/test_alpha_eval.py:90-105` — decile pathology.
- `tests/test_alpha_eval.py:113-122` — calibration.
- `tests/test_alpha_eval.py:130-144` — liquidity split.
- `tests/test_alpha_eval.py:152-161` — thin-data warnings.

Do **not** build a new alpha-evaluation framework unless the goal is explicitly to extend this one.

---

### 2.2 Research store and factor track are real code, not just design

The research-store schema exists in `migrations/0027_research_store.sql`. It creates:

- `rs_security_master`
- `rs_corporate_actions`
- `rs_financial_statements`
- `rs_fundamentals_pit`
- `rs_factor_scores`
- `rs_index_membership`
- `rs_estimates`

It explicitly describes the research store as the point-in-time, survivorship-free foundation for long-horizon factor research. It also flags historical index membership as unresolved and says v1 must label proxy-universe tests honestly.

Evidence pointers:

- `migrations/0027_research_store.sql:1-34` — applied-empty header, PIT discipline, EODHD availability notes.
- `migrations/0027_research_store.sql:35-65` — security master and corporate actions.
- `migrations/0027_research_store.sql:67-115` — financial statements and PIT fundamentals.
- `migrations/0027_research_store.sql:117-145` — factor scores and index membership.
- `migrations/0027_research_store.sql:147-157` — estimates.

`docs/research/research-store-schema.md` says the schema was applied but all `rs_*` tables held zero rows at that time and populated-data validation was still pending. That may now be stale, but it is a critical live-state check.

Evidence pointers:

- `docs/research/research-store-schema.md:1-8` — applied-empty warning.
- `docs/research/research-store-schema.md:17-38` — guarded `knowledge_date` rule.
- `docs/research/research-store-schema.md:51-66` — source availability and current-only index membership.
- `docs/research/research-store-schema.md:72-90` — revised build sequence, many pieces marked built but not necessarily populated at scale.
- `docs/research/research-store-schema.md:92-105` — unresolved historical index membership and populated-data validation.

`asxos/domain/research/factor_scores.py` implements the factor engine. It has:

- sector-neutral value, quality, momentum, low-vol, yield
- value x quality composite
- leak-safe `knowledge_date <= as_of`
- `dt <= as_of` for prices
- winsorized z-scores
- idempotent upsert into `rs_factor_scores`

Evidence pointers:

- `asxos/domain/research/factor_scores.py:1-34` — module design contract.
- `asxos/domain/research/factor_scores.py:48-82` — factor categories and constants.
- `asxos/domain/research/factor_scores.py:106-151` — momentum, volatility, and grossed-up yield.
- `asxos/domain/research/factor_scores.py:154-182` — raw factor computation.
- `asxos/domain/research/factor_scores.py:190-268` — sector-neutral scores.
- `asxos/domain/research/factor_scores.py:275-322` — PIT/price SQL and upsert skeleton.
- `asxos/domain/research/factor_scores.py:328-392` — refresh_factor_scores orchestration.

`jobs/eval_alpha_factors.py` evaluates the factor candidate read-only and writes nothing.

Evidence pointers:

- `jobs/eval_alpha_factors.py:1-19` — read-only factor evaluation contract.
- `jobs/eval_alpha_factors.py:36-66` — output report shape.
- `jobs/eval_alpha_factors.py:69-96` — load factor panel, fail on empty panel, run alpha_eval.

Do **not** write a new factor design doc before checking whether the existing factor pipeline is populated and live.

---

### 2.3 TC-20 Div 296 appears implemented despite stale docs

Older docs/backlog text previously described TC-20 Div 296 cost-base reset as unimplemented. Current code appears to have implemented it.

`asxos/domain/tax/positions.py` contains:

- `div296_realised_gains` input
- election path using separate Div 296 realised gains
- non-election fallback to ordinary net capital gain
- data-driven depreciated-lot warning based on `cost_base_div296 < cost_base_normal`

Evidence pointers:

- `asxos/domain/tax/positions.py:109-121` — `tax_view_smsf` arguments include `div296_realised_gains`.
- `asxos/domain/tax/positions.py:154-180` — Div 296 election vs non-election earnings path.
- `asxos/domain/tax/positions.py:192-215` — depreciated-asset warnings and 45-day franking warnings.

`tests/test_tax_positions.py` includes TC-20 tests:

- election made: Div 296 earnings use reset-cost-base gain, not ordinary gain
- election not made: Div 296 earnings use ordinary net gain

Evidence pointers:

- `tests/test_tax_positions.py:76-88` — TC-20 section header.
- `tests/test_tax_positions.py:81-113` — election path test.
- `tests/test_tax_positions.py:115-138` — non-election regression test.

Future Claude session should verify whether `CLAUDE.md` and `docs/next-session-backlog.md` still contain stale TC-20 references and update docs rather than reimplementing TC-20.

---

### 2.4 Paper portfolio monitoring already exists

`asxos/domain/portfolio/monitor.py` is a pure Decimal-only performance monitor. It includes:

- typed `Position`, `PriceBar`, `BenchmarkSeries`, `CostModel`, `MonitorInputs`
- missing-price events
- NAV series
- total-return via `adj_close` where available
- price return and total return
- benchmark relative return
- equal-weight vs model-weight return
- hit rate, payoff ratio, drawdown, realised volatility, turnover
- inferred transaction-cost estimate
- bucket attribution by sector, label, probability, and expected return

Evidence pointers:

- `asxos/domain/portfolio/monitor.py:1-31` — module design contract.
- `asxos/domain/portfolio/monitor.py:57-139` — inputs and cost model.
- `asxos/domain/portfolio/monitor.py:149-260` — output dataclasses.
- `asxos/domain/portfolio/monitor.py:274-285` — cost estimate.
- `asxos/domain/portfolio/monitor.py:242-264` — drawdown and realised volatility.
- `asxos/domain/portfolio/monitor.py:638-710` — report assembly.

The gap is **not** basic monitoring. The gap is systematic risk and decision-math integration.

---

### 2.5 Job failure monitoring was hardened

`asxos/jobs/utils/job_monitor.py` now:

- records job lifecycle to `job_runs`
- never suppresses exceptions
- marks stale `running` rows older than two hours as `failure`
- pings Healthchecks on success
- pings `healthcheck_url + "/fail"` on real failure
- treats `UpstreamBlocked` as `blocked` and does not ping

Evidence pointers:

- `asxos/jobs/utils/job_monitor.py:10-30` — class contract and status mapping.
- `asxos/jobs/utils/job_monitor.py:46-88` — stale-row healing and running row insert.
- `asxos/jobs/utils/job_monitor.py:90-146` — status update and Healthchecks ping/fail logic.

Do not rebuild job monitoring before checking live Healthchecks env coverage.

---

## 3. Current-state correction table

| Item | Old or likely stale claim | Current code/doc reality | Action |
|---|---|---|---|
| TC-20 Div 296 reset | Backlog/CLAUDE previously described it as unimplemented | `positions.py` and `tests/test_tax_positions.py` appear to implement and test TC-20 | Verify docs and update stale references; do not reimplement |
| Research store | Could be misread as only a plan | DDL, factor engine, loaders, and eval job exist; doc says applied-empty/pending validation | Verify live row counts and job runs |
| Alpha evaluation | Could be misread as a missing framework | `alpha_eval.py` and tests already implement effective-N, calibration, deciles, liquidity split | Extend only if needed; do not duplicate |
| Paper portfolio monitor | Could be misread as missing risk/performance monitor | `monitor.py` has NAV/cost/drawdown/vol/benchmark buckets | Build systematic risk report, not another monitor |
| Render/IaC | `render.yaml` says it is source of truth and lists 28 cron services | Backlog says a live diff recently found many missing services and Healthchecks gaps | Verify live Render and Healthchecks state |
| Phase-4 architecture | Describes VPS/systemd/local Postgres | Current README/CLAUDE/render indicate Render/Supabase architecture | Classify phase-4 doc as historical/superseded if still true |
| Agent SELECT-only | Agent prompts say read-only | Tool grant can still execute arbitrary SQL | Build read-only DB role/session path before more discovery agents |
| Language | Python stack may look heavy | Current repo is deeply Python-native for ML/research/tax/jobs | Keep Python primary; add Rust/Go only for targeted roles |

---

## 4. Ranked fundamentals gaps

### P0 — Truth, safety, and live-state correctness

#### P0.1 Authoritative state and doc-drift audit

**Why it matters:** Claude will waste cycles or introduce contradictions if it trusts stale backlog text.

**Evidence:**

- `README.md` and `CLAUDE.md` describe the current stack as Python/FastAPI/Supabase/Render.
- `docs/foundation/phase-4-architecture-system-architect.md` describes a VPS/systemd/local Postgres architecture, likely historical.
- `docs/next-session-backlog.md` contains items that may be stale relative to current code/tests.

**Minimal next action:** create a current-state correction table in docs, then update stale references.

**Do not build yet:** any feature described only in stale backlog text.

---

#### P0.2 Research-store live validation

**Why it matters:** The factor research path only matters if the research store is actually populated and jobs run.

**Evidence:**

- `docs/research/research-store-schema.md:1-8` explicitly says applied-empty and not validated with populated data at the time.
- `render.yaml:102-228` lists research-store cron jobs.

**Minimal next action:** verify live DB row counts and latest `job_runs` for:

- `sync_security_master`
- `sync_corporate_actions`
- `sync_financial_statements`
- `derive_fundamentals_pit`
- `compute_factor_scores`
- `eval_alpha_factors` if run manually

**Do not build yet:** new factor/allocator logic before the research store is populated and alpha_eval has real output.

---

#### P0.3 Agent DB role scoping

**Why it matters:** Discovery agents have a prompt-level SELECT-only boundary but a write-capable SQL tool. This is a real governance bypass risk.

**Evidence:**

- `.claude/agents/macro-economist.md:3-7` includes `mcp__Supabase__execute_sql`.
- `.claude/agents/macro-economist.md:121-135` says read-only/SELECT-only and treats external text as untrusted.
- `docs/next-session-backlog.md:39-59` describes the prompt-only SQL boundary risk and proposes a read-only Postgres role.

**Minimal next action:** backend-architect design for read-only DB role / MCP role selection.

**Do not build yet:** Phase 2c discovery agents (`theme-researcher`, `instrument-selector`) until role scoping is solved or deliberately accepted.

---

#### P0.4 Render and Healthchecks live truth

**Why it matters:** `render.yaml` being the source of truth does not help if the live Render account is not in sync or Healthchecks env vars are missing.

**Evidence:**

- `render.yaml:3-8` says the file is the source of truth.
- `render.yaml:10-28` lists 1 web and 28 cron services.
- `docs/next-session-backlog.md:170-183` says a live-state diff found 12 crons missing, 10 resumed, and 2 suspended pending `FRED_API_KEY`.
- `docs/next-session-backlog.md:185-213` says 12 Healthchecks checks/env vars still needed.

**Minimal next action:** run live-state drift check and Healthchecks env audit.

---

### P1 — Decision-grade math and risk

#### P1.1 Systematic risk report

**Why it matters:** Current construction has per-name and sector caps but no beta/correlation/factor exposure controls.

**Evidence:**

- `.claude/rules/portfolio-conventions.md:192-207` states v1 allocator is risk-blind to market-wide co-movement and beta cap is a v2 candidate.
- `asxos/domain/portfolio/constraints.py` enforces per-name and sector caps but not covariance/beta/factor risk.

**Minimal next action:** build a read-only risk report first:

- benchmark beta
- average pairwise correlation
- sector and factor exposure
- liquidity-adjusted exposure
- stress scenarios
- concentration warnings

**Do not build yet:** allocator optimizer changes.

---

#### P1.2 Decision-math layer

**Why it matters:** Existing math is scattered across alpha eval, tax, portfolio, monitor, and brief collectors. There is no single typed decision-evidence object.

**Minimal next action:** design a pure `asxos/domain/decision/` layer that returns evidence, confidence, blockers, and labels. Do not emit orders.

Proposed first dataclass:

```python
@dataclass(frozen=True)
class DecisionEvidence:
    symbol: str
    as_of: date
    context: str
    expected_value_after_tax_cost: Decimal | None
    confidence_grade: Literal["missing", "weak", "indicative", "decision_grade"]
    risk_flags: tuple[str, ...]
    tax_flags: tuple[str, ...]
    data_quality_flags: tuple[str, ...]
    blocker_flags: tuple[str, ...]
    explanation: tuple[str, ...]
```

**Do not build yet:** a black-box `BUY`/`SELL` engine.

---

#### P1.3 Purge/embargo wired into research training

**Why it matters:** `purge_embargo_days` exists in config/metadata, but active training still uses a simple walk-forward split.

**Evidence:**

- `asxos/domain/models/train.py:90-113` implements current `walk_forward_split`.
- `asxos/domain/models/training_config.py:52-54` declares `purge_embargo_days`.
- `asxos/domain/models/training_config.py:12-16` says v1.6 threading is future and production retrain remains unchanged.

**Minimal next action:** experiment-only purged/embargoed split and compare metrics.

**Do not build yet:** model activation or allocator wiring.

---

#### P1.4 Multiple-testing / backtest-overfitting guardrails

**Why it matters:** Factor research will create many hypotheses. Without tracking hypothesis count and OOS status, the system will find false winners.

**Evidence:**

- `docs/research/operating-model-architecture.md:72-80` warns about multiple testing and deflated Sharpe.
- `alpha_eval.py` does not currently compute deflated Sharpe, probability of backtest overfitting, or FDR adjustment.

**Minimal next action:** add a research candidate registry/report field:

- factor family
- first tested date
- number of variants tested
- in-sample/OOS split
- effective-N
- decision status: exploratory / candidate / rejected / promoted

---

#### P1.5 Opportunity-cost delta, not level screen

**Why it matters:** The brief currently flags alternatives by absolute net expected return, not advantage over current holding on the same basis.

**Evidence:**

- `asxos/domain/brief/collectors/opportunity_cost.py:10-26` explicitly says it is a level screen and needs `current_net_expected_return` from the producer.

**Minimal next action:** producer spec: add current-holding baseline under the same tax/cost model.

---

### P2 — Test and correctness improvements

#### P2.1 Property/metamorphic testing layer

**Why it matters:** Many tax/portfolio/risk rules are mathematical invariants and should be tested as such.

**Evidence:**

- `pyproject.toml:49-56` lists pytest/pytest-asyncio/pytest-cov/ruff/mypy but no property-testing dependency.
- `docs/backlog-test-coverage.md` lists many uncovered correctness paths.

**Candidate invariants:**

- adding a capital loss cannot increase tax
- increasing slippage cannot improve net expected return
- stale data cannot improve decision grade
- no-trade bands cannot increase turnover
- weights never exceed hard caps after constraints
- Decimal-only modules never ingest float money
- missing price data cannot be silently treated as verified

---

#### P2.2 Startup hard-fail tests

**Why it matters:** hard-fail startup is a non-negotiable lesson from the previous system.

**Evidence:**

- `asxos/api/main.py:20-47` hard-fails on migration drift and missing active model artifact.
- `docs/backlog-test-coverage.md:7-13` says this path lacks success and RuntimeError branch coverage.

**Minimal next action:** tests for lifespan success, migration drift failure, missing model artifact failure, and DB init failure.

---

#### P2.3 Tax-lot optimization beyond local min-CGT

**Why it matters:** `select_min_cgt` optimizes a small local post-discount gain objective and falls back to FIFO for larger lot sets.

**Evidence:**

- `asxos/domain/tax/lots.py:75-90` implements `select_min_cgt` and fallback to FIFO above `max_combo_size`.
- `asxos/domain/tax/lots.py:130-137` computes post-discount gain only.

**Minimal next action:** research-only objective function that includes tax, costs, opportunity cost, CGT boundary value, and wash-sale warning flags.

---

### P3 — Tidy and polish

#### P3.1 Shared escaped alert helper

**Why it matters:** fallback email escapes HTML, but backlog says duplicated alert helpers interpolate text into `<pre>` without escaping.

**Evidence:**

- `asxos/jobs/utils/fallback_email.py:31-60` escapes `body_text` with `html.escape()`.
- `docs/next-session-backlog.md:29-37` flags unescaped duplicate `_send_alert()` helpers.

**Minimal next action:** extract shared escaped helper and update alert jobs.

---

#### P3.2 CI enforcement realism

**Why it matters:** CI runs, but private repo branch protection is not server-enforced under the current plan.

**Evidence:**

- `.github/workflows/full-check.yml:1-51` runs ruff, mypy, full pytest with `[ml,dev]`.
- `scripts/hooks/pre-push:5-17` says private repo branch protection cannot block merges server-side, so the local hook is the real enforcement point.
- `scripts/hooks/pre-push:58-61` runs pytest only when `RUN_TESTS=1`.

**Minimal next action:** do not claim CI blocks merges. Keep local hook plus full-check signal.

---

## 5. Decision-math layer proposal

### 5.1 Should asxos have a quant-level math engine?

Yes, but not as one giant `quant_engine` and not as an oracle.

The useful version is a **decision-math layer**: pure, typed, testable modules that transform forecasts, statistics, tax, risk, costs, and data quality into replayable decision evidence.

It should answer:

- Is this signal statistically meaningful or likely noise?
- Is the sample independent enough to quote?
- Is the candidate better than the current holding after tax, cost, and risk?
- Is the portfolio accidentally one large ASX beta bet?
- Is a trade worth doing after turnover, tax, and slippage?
- Which decision label is justified: `missing`, `weak`, `indicative`, `decision_grade`, `blocked`, `paper_only`?

It should **not** answer:

- “Buy 300 shares.”
- “This is approved.”
- “Deploy capital.”

Those are human/governance decisions.

---

### 5.2 Proposed packages

```text
asxos/domain/
  risk/
    exposure.py        # beta, factor, sector, concentration
    covariance.py      # correlations and covariance estimates
    stress.py          # scenario and drawdown stress
    liquidity.py       # capacity and ADV constraints

  decision/
    evidence.py        # typed DecisionEvidence objects
    utility.py         # after-tax/after-cost expected utility
    policy.py          # decision labels and blocker rules
    thresholds.py      # no-trade bands, evidence gates

  math/
    decimal_tools.py   # Decimal guards and quantization helpers
    stats_tools.py     # bootstrap, CI, shrinkage helpers
    invariants.py      # shared invariant checks
```

Keep the math pure:

- no DB calls inside these modules
- no network calls
- no CLI output
- no HTML/email formatting
- no writes

Load data outside, pass typed inputs in, return typed outputs.

---

### 5.3 Five layers of useful math

#### Layer 1 — Statistical evidence

Mostly already started in `research/alpha_eval.py`.

Should own:

- rank-IC
- effective sample size
- effective t-statistics
- calibration
- deciles
- bootstrap confidence intervals
- multiple-testing notes
- regime-stratified evidence

#### Layer 2 — Risk math

This is the biggest missing math layer.

Should own:

- benchmark beta
- pairwise correlation
- factor exposure
- stress loss
- CVaR / expected shortfall
- liquidity-adjusted exposure
- concentration warnings

#### Layer 3 — Decision utility

Should combine:

- expected return evidence
- calibration confidence
- tax friction
- slippage/costs
- liquidity
- risk contribution
- thesis conviction
- time horizon
- no-trade bands
- stale-data penalties

Output: `DecisionEvidence`, not orders.

#### Layer 4 — Optimization

Only after evidence and risk reporting are correct.

Could eventually use constrained optimization for:

- expected utility
- cash floor
- per-name cap
- sector cap
- beta cap
- liquidity cap
- turnover cap
- tax-cost penalty
- minimum trade size
- no-trade bands
- “do nothing” as valid optimum

#### Layer 5 — Invariants and property tests

Should encode correctness rules mathematically rather than only example-based tests.

---

## 6. Language and architecture strategy

### 6.1 Recommendation

Keep Python as the primary language.

Use this rule:

```text
Python = think, research, decide, explain
Rust   = compute fast and safely, if needed
Go     = run boring infrastructure cleanly, if needed
C++    = integrate with native/vendor/high-performance code, only if forced
```

### 6.2 Why Python remains the center

The repo is already deeply Python-native:

- Python 3.12
- FastAPI
- asyncpg / psycopg2
- pandas / NumPy
- LightGBM / SHAP / scikit-learn
- Typer CLI
- pytest / ruff / mypy

Evidence pointer:

- `pyproject.toml:16-56` — runtime, ML, and dev dependencies.

The system’s bottlenecks are not raw CPU speed. They are:

- data truth
- point-in-time correctness
- calibration
- survivorship
- risk math
- tax correctness
- doc drift
- operational drift
- governance and agent safety

A rewrite does not solve those.

---

### 6.3 Go

Best use in `asxos`:

- Render/live-state reconciler
- Healthchecks manager
- cron auditor
- backup verifier
- small ops binaries

Not a good fit for:

- ML training
- SHAP
- pandas-like research
- factor experimentation
- tax simulations

Verdict: Go can be useful for ops tooling later, not as the product language.

---

### 6.4 Rust

Best use in `asxos`:

- risk/correlation kernels
- fast portfolio stress calculations
- tax-lot optimizer
- corporate-action adjustment engine
- large backtest loops
- parser/data normalization kernels

Suggested integration pattern:

```text
Python app
  calls
Rust library via PyO3/maturin
  returns typed results
Python persists / explains / emails
```

Do not use Rust until profiling or correctness pressure justifies a specific kernel.

Verdict: Rust is the best optional secondary language.

---

### 6.5 C++

Best use in `asxos`:

- existing native libraries
- vendor SDKs
- rare extreme performance kernels

Not a good default for this repo because it adds a large maintenance burden and reduces Claude Code’s ability to safely work across the codebase.

Verdict: use C++ indirectly through libraries; avoid writing core `asxos` in C++ unless forced.

---

### 6.6 If starting from scratch

Still start with Python, but design clean seams for optional kernels.

```text
Language:
  Python 3.12/3.13 primary

Storage:
  Postgres for operational truth
  DuckDB/Parquet for research snapshots if local heavy analytics becomes needed

Surfaces:
  Typer CLI first
  scheduled jobs second
  FastAPI thin health/API layer
  email brief as primary user surface
  no frontend until necessary

Math:
  NumPy/pandas for research stats
  Decimal for tax/portfolio money
  optional Rust kernels later
  optional optimization only after evidence/risk layers mature

Quality:
  ruff
  mypy
  pytest
  property tests
  golden spec tests
  migration drift tests
  live-trigger verification tests
```

No rewrite is recommended.

---

## 7. Live-readiness checklist for next Claude session

Run this before any implementation work.

### 7.1 DB row counts

Check counts and latest dates:

```sql
SELECT COUNT(*) FROM rs_security_master;
SELECT COUNT(*) FROM rs_corporate_actions;
SELECT COUNT(*) FROM rs_financial_statements;
SELECT COUNT(*) FROM rs_fundamentals_pit;
SELECT COUNT(*) FROM rs_factor_scores;
SELECT COUNT(*) FROM rs_index_membership;
SELECT COUNT(*) FROM rs_estimates;

SELECT MAX(as_of), COUNT(*) FROM rs_factor_scores;
SELECT factor_set_version, COUNT(*), MIN(as_of), MAX(as_of)
FROM rs_factor_scores
GROUP BY factor_set_version;
```

### 7.2 Research-store job runs

```sql
SELECT job_name, as_of, status, started_at, finished_at, rows_written, error_message
FROM job_runs
WHERE job_name IN (
  'sync_security_master',
  'sync_corporate_actions',
  'sync_financial_statements',
  'derive_fundamentals_pit',
  'compute_factor_scores'
)
ORDER BY started_at DESC
LIMIT 50;
```

### 7.3 Factor alpha eval readiness

```sql
SELECT COUNT(*)
FROM rs_factor_scores fs
JOIN prices p ON p.symbol = fs.symbol AND p.dt = fs.as_of
WHERE fs.factor_set_version = 'fs_v1';
```

If zero, `jobs/eval_alpha_factors.py` will fail loudly by design.

### 7.4 Render/Healthchecks checks

Verify live state against `render.yaml`:

- all 28 cron services exist
- suspended services are intentional
- `FRED_API_KEY` status for market-context/underlyings
- every `HEALTHCHECK_URL_*` env var expected by `asxos/config.py` is set where needed
- `check-cron-health` is live
- `make check-drift` / Render MCP drift process reports no mismatch

### 7.5 Docs likely to classify as current vs stale

- `README.md`
- `CLAUDE.md`
- `docs/next-session-backlog.md`
- `docs/research/research-store-schema.md`
- `docs/research/operating-model-architecture.md`
- `docs/foundation/phase-4-architecture-system-architect.md`
- `docs/foundation/spec/tax-alpha.md`

---

## 8. Recommended next-session sequence

### Step 1 — Current-state truth audit

Create or update a doc with:

- stale TC-20 references
- stale architecture references
- research-store live state
- Render live state
- Healthchecks coverage
- current blocker list

### Step 2 — Data validation before math expansion

If research-store tables are populated:

- run/read `jobs/eval_alpha_factors.py`
- capture warnings exactly
- do not overstate results
- classify factor sleeve as exploratory/candidate/rejected, not approved

If tables are empty:

- do not run factor conclusions
- fix provisioning/data flow first

### Step 3 — Risk report design

Design read-only `asxos/domain/risk/` report:

- beta
- average pairwise correlation
- sector/factor exposure
- liquidity-adjusted exposure
- stress loss
- concentration warnings

No allocator change.

### Step 4 — DecisionEvidence spec

Design typed decision output:

- evidence strength
- risk flags
- tax flags
- data-quality flags
- blocker flags
- explanation

No order/trade recommendation.

### Step 5 — Testing plan

Add a test plan before dependency changes:

- startup hard-fail tests
- property-test proposal
- live-trigger verification pattern
- alpha_loader/factor_loader DB branch tests
- monitor_loader and volatility loader tests

---

## 9. Claude Code prompt for next session

```text
You are in repo `Jp8617465-sys/asxos`.

Start by reading:
- docs/research/claude-fundamentals-audit-handoff-2026-07-04.md
- README.md
- CLAUDE.md
- docs/research/research-store-schema.md
- docs/research/operating-model-architecture.md
- docs/research/alpha-research-audit.md
- asxos/domain/research/alpha_eval.py
- asxos/domain/research/alpha_loader.py
- asxos/domain/research/factor_scores.py
- jobs/eval_alpha_factors.py
- asxos/domain/portfolio/monitor.py
- .claude/rules/portfolio-conventions.md
- docs/next-session-backlog.md
- docs/backlog-test-coverage.md
- render.yaml

Task: perform a READ-ONLY current-state and live-readiness audit before any implementation.

Do not modify code. Do not create migrations. Do not change Render. Do not update DB data. Do not open a PR unless explicitly asked.

Deliver:

1. Current-state correction table:
   - item
   - stale/old claim if any
   - current code reality
   - evidence file:line
   - action: update docs / verify live state / build later / no action

2. Research-store live readiness:
   - row counts for rs_* tables
   - latest job_runs for research-store jobs
   - factor panel join readiness
   - whether eval_alpha_factors can run meaningfully

3. Render/Healthchecks readiness:
   - services in render.yaml vs live Render state
   - suspended services
   - missing Healthchecks env vars
   - any drift

4. Ranked next actions:
   - P0: truth/safety/live-state
   - P1: measurement/risk/decision math
   - P2: tests/invariants
   - P3: polish

5. Do-not-do list:
   - do not rebuild alpha_eval
   - do not rebuild factor schema
   - do not reimplement TC-20 unless verification proves current code is wrong
   - do not change allocator before risk/evidence reports exist
   - do not treat factor results as decision-grade if alpha_eval warns they are underpowered

Rules:
- Every repo claim must cite exact file paths and line numbers.
- Do not claim something is missing until you grep/search for it.
- Classify stale docs explicitly.
- Do not give financial advice or capital-deployment recommendations.
```

---

## 10. Do-not-do list

Do not spend the next Claude session on:

- rebuilding alpha_eval
- rebuilding the research-store schema
- rebuilding factor_scores
- rebuilding the paper monitor
- rebuilding JobMonitor failure pings
- reimplementing TC-20 from stale docs
- rewriting in Go/Rust/C++
- changing allocator behavior before risk/evidence layers exist
- turning evidence labels into trade orders
- treating current-only index membership as historical ASX200 membership
- claiming factor results are decision-grade before effective-N and liquidity checks pass

---

## 11. Bottom line

`asxos` should not become a black-box quant bot and should not be rewritten.

The correct next shape is:

```text
existing alpha_eval + research_store + factor_scores + tax + monitor
        -> risk report
        -> decision evidence layer
        -> human governance / brief / journal
        -> only later constrained optimization, if evidence supports it
```

Keep Python as the main language. Add Rust later only for isolated kernels if profiling or correctness pressure proves it useful. Add Go only for boring ops tooling if that tooling becomes worth maintaining. Avoid C++ unless forced by a vendor/native library or a very specific high-performance kernel.
