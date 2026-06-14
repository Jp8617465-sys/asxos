# 02 — Roadmap Tracks

> **Status: planning. No track is approved for implementation.** Tracks are
> split into two lanes; Lane B stays parked until the loop is stable
> (gate G3 in `01-current-state-and-recovery-gates.md`).

## Lane definitions

- **Lane A — Production reliability / near-term cleanup.** Opens after the core
  loop is GREEN (gate G1). Each item still needs explicit per-item approval.
- **Lane B — Strategic platform evolution.** Opens only after 5 consecutive
  green trading days (gate G3).

| Track | Primary lane |
|---|---|
| A — Production Reliability | Lane A |
| B — Data Truth | Lane A (deploy) → Lane B (semantics) |
| C — Quant Research | Lane B |
| D — ML / Model Lifecycle | Lane B |
| E — Portfolio and Risk | Lane A (restore) → Lane B (extend) |
| F — Automation and Review | Lane B (design first) |
| G — Platform Architecture | Lane B |
| H — Product Experience | Lane A (footer) → Lane B (reshape) |
| I — Hedge-fund lean translation | cross-cutting doctrine |

---

## Track A — Production Reliability

- **Objective.** The minimal loop runs green daily and the system reports its
  own health truthfully.
- **Why it matters.** This is the Phase B lesson. An unmonitored loop is the
  exact failure mode that killed the predecessor (`healthy` API over dead
  dependencies). ASXOS currently has the watcher written
  (`jobs/check_cron_health.py`) but **not running**.
- **Current state.** Loop live, unproven; monitoring tier absent (11 declared
  services not live); backup writes no `job_runs` row; one healthcheck gap
  (`ingest_sentiment`).
- **Near-term (Lane A).** Verify loop → deploy `check_cron_health` (with
  `_EXPECTED_DAILY` trimmed to live jobs to avoid false-MISSING storms) →
  backup `job_runs` row → close healthcheck/DB-roll gaps → Render drift
  reconcile.
- **Later (Lane B).** Single job-health dashboard; aggregate staleness
  alerting; expanded API health surface.
- **Dependencies.** Verification gate G1.
- **Risks.** Deploying `check_cron_health` *before* the other monitors exist
  floods MISSING alerts for the 7 absent jobs in its expected-daily set.
- **Success metric.** 5 consecutive trading days, all live expected-daily jobs
  green, zero deadman misses, backup visible in `job_runs`.

## Track B — Data Truth

- **Objective.** Every downstream number traces to correct, point-in-time,
  corporate-action-aware data.
- **Why it matters.** Signals/portfolio/tax are only as good as price and
  fundamental truth. Adjusted-vs-unadjusted prices and dividend handling are
  silent-error factories.
- **Current state.** EODHD bulk prices (~644k rows); 45-day fundamentals
  `merge_asof` lag; `validate_price_data` job exists but **service absent**; US
  migration `0009` present; `universe_history` exists; corporate-action and
  delisting handling minimal.
- **Near-term (Lane A).** Deploy `validate_price_data`; document the
  adjusted-price contract; surface `data_quality_flags`.
- **Later (Lane B).** PIT universe membership; corporate-action ingestion;
  delist/inactive lifecycle; US-session readiness.
- **Dependencies.** Track A monitoring live.
- **Risks.** Changing price semantics silently invalidates historical signals
  and any backtest.
- **Success metric.** `validate_price_data` green daily; zero unexplained
  gaps/dupes; documented adjusted-price semantics.

## Track C — Quant Research

- **Objective.** A disciplined harness that decides whether a signal earns
  production, with explicit kill criteria. *(Research only — no signal is
  approved here.)*
- **Why it matters.** The active model runs without a live realised-performance
  feedback loop: `track_signal_outcomes` is **absent**. Promotion/retirement is
  currently judgement, not measured evidence.
- **Current state.** `signal_outcomes` table holds ~24k historical rows;
  `track_signal_outcomes` job exists, service absent; no rank-IC / quintile /
  turnover reporting surface; no shadow paper book wired to a verdict file.
- **Near-term (Lane B).** Deploy `track_signal_outcomes`; define labels and
  horizons explicitly; compute rank IC + quintile spreads + turnover/cost on
  existing outcomes.
- **Later (Lane B).** Walk-forward harness; shadow paper book; promotion gates +
  kill criteria as committed `verdict` files.
- **Dependencies.** Tracks A/B. **Do not change thresholds or add signal
  families.**
- **Success metric.** A reproducible weekly IC/quintile/turnover report plus a
  written promotion/kill gate per signal.

## Track D — ML / Model Lifecycle

- **Objective.** Trustworthy retraining with leakage prevention, calibration,
  drift monitoring, and a quarantine policy.
- **Why it matters.** `retrain_model_a` is paused (OOM / M12 risk);
  `check_model_staleness` is absent. A model can silently decay with no alarm.
- **Current state.** Model A v1_5 active; `TimeSeriesSplit` / `PurgedGroupKFold`,
  T-1 features, retraining gates (ROC-AUC ≥ 0.65, ≤ 5% degradation) in
  `ml-conventions.md`; SHAP explainability present.
- **Near-term (Lane B).** Read-only label/feature/leakage audit; deploy
  `check_model_staleness`; document retraining memory budget.
- **Later (Lane B).** Scheduled retrain with calibration + drift metrics;
  simple-baseline-first policy; model retirement/quarantine workflow.
- **Dependencies.** Track C feedback. **No retraining now.**
- **Success metric.** Retrain runs within memory budget, passes gates, drift
  monitored, every promotion reversible.

## Track E — Portfolio and Risk

- **Objective.** A CGT-aware, risk-explicit decision ledger from proposal to
  outcome.
- **Why it matters.** This is the user-facing product; correctness and
  auditability are the value.
- **Current state.** Full Decimal portfolio stack
  (allocator/constraints/tax_overlay/rebalance/paper_trade); `decisions`
  journal; position monitors (`check_us/au_positions`) exist but **absent**;
  thesis integration landed-dark; **v1 risk-blindness documented** (no
  market-beta cap).
- **Near-term (Lane A).** Deploy position monitors; restore `build_portfolio`
  (after loop green + DB roll); decision-ledger provenance view.
- **Later (Lane B).** Risk exposure / beta-cap (v2 candidate), sizing,
  liquidity, thesis-driven decisions, attribution, manual-override log.
- **Dependencies.** Tracks A/B/C. **No tax-logic or threshold changes;**
  `build_portfolio` restart only after loop green.
- **Success metric.** A proposed trade traceable to signal row + model_version +
  profile + data freshness; CGT boundary respected (spec §5.1).

## Track F — Automation and Review

- **Objective.** Events → reviews → human approval, with **zero autonomous
  production mutation**.
- **Why it matters.** Scales operator attention without surrendering control —
  the governance the postmortem demands.
- **Current state.** None (no `ops_events` / `review_queue`); all mutations
  manual/approved (the recovery-session discipline).
- **Near-term (Lane B).** Design only — `ops_events`, `review_queue`, severity
  model.
- **Later (Lane B).** Auto-review creation from failures/staleness/missed-backup/
  drawdown; Claude/Opus prompt generation; human-approval gates.
- **Dependencies.** Track A; explicit governance decisions.
- **Risks.** Premature automation re-introduces silent mutation — the original
  sin.
- **Success metric.** Every incident produces a review row + suggested prompt;
  no automated DB/Render/Git change without approval.

## Track G — Platform Architecture

- **Objective.** Choose the execution topology that scales to ASX + US without
  30 drifting crons.
- **Why it matters.** The many-cron fan-out is the dominant drift surface
  (24 declared / 13 live / 11 absent today).
- **Current state.** 22 jobs as individual Render crons; service-local env; no
  orchestrator/queue; MCP-driven mutation intent.
- **Near-term (Lane B).** Decision memo (many-crons vs master orchestrator vs
  DB-queue worker); env-group architecture design.
- **Later (Lane B).** Observability API; event-driven reviews; possible custom
  connector; ASX + US execution hosts.
- **Dependencies.** Track A stable first.
- **Success metric.** A chosen topology with a drift-detection guarantee
  (`make check-drift` enforced in deploy).

## Track H — Product Experience

- **Objective.** A daily brief the operator trusts — fresh, explained, honest,
  prioritized.
- **Why it matters.** The brief is the only output surface and the in-band
  operational channel.
- **Current state.** V1 procedural brief active (`asxos/brief/compose.py`); V2
  collector brief dark (`asxos/domain/brief/composer.py`); no stale-section
  footer; no "what changed today."
- **Near-term (Lane A).** Stale-section health footer (guards-backlog P1-3);
  brief delivery observability (`brief_runs`).
- **Later (Lane B).** V2 reshape (severity tuples, cross-layer observations,
  "one thing today"); signal explanations; alert prioritization; no fabricated
  confidence.
- **Dependencies.** Tracks B/C; reshape touches every section (Lane B epic).
- **Success metric.** Brief always sends, always shows section health, never
  fabricates a regime/confidence.

## Track I — Top 1% Hedge Fund Principles, Lean ASXOS Version

- **Objective.** Import elite systematic discipline at solo scale (detail in
  `04-quant-research-and-ml.md` and `09-decision-backlog.md`).
- **Why it matters.** Keeps ASXOS honest about what it should and should not
  trust.
- **Current state.** Strong hard-fail/spec-first foundations; weak on live
  performance attribution and promotion gates.
- **Near-term.** Adopt "measure daily, promote slowly, kill fast" as the
  operating doctrine for Tracks C/D.
- **Success metric.** Every production signal has a written kill criterion and a
  daily-measured live metric.

---

## Sequencing summary

```
Verification GREEN (G1)
   └─ Lane A batch 1: build_portfolio DB roll · deploy check_cron_health (trimmed) · backup job_runs
   └─ Lane A batch 2: sentiment root-cause + healthcheck · drift reconcile · DSN test
   └─ Lane A batch 3: cleanup-conversations decision · position monitors · validate_price_data
5 green days (G3)
   └─ Lane B: Quant research harness → ML lifecycle → automation design → architecture memo → V2 reshape
```

**Highest-value single Lane A action once green:** deploy the monitoring tier,
starting with `check_cron_health` (expected-set trimmed to live jobs). The
predecessor died because nothing was watching; ASXOS has the watcher written but
not running.
