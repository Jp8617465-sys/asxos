# 04 — Quant Research and ML Lifecycle

> **Status: RESEARCH PLANNING ONLY.**
> - No signal is approved.
> - No new model is recommended before the production loop is stable.
> - Thresholds are frozen (canonical set in `.claude/rules/ml-conventions.md`).
> - Do not add signal families. Do not retrain. Do not change tax/threshold
>   logic.
>
> This document describes the *measurement discipline* ASXOS should adopt
> **after** the loop is verified, not work to start now.

---

## 1. The gap this addresses

ASXOS runs Model A v1_5 in production **without a live realised-performance
feedback loop**: `track_signal_outcomes` is not deployed. We therefore cannot
currently answer "is the live signal actually working?" with measured evidence.
Closing that gap is the foundation of every other quant decision — and it is the
*first* Track C item, before any model or signal change.

Historical substrate already exists: the `signal_outcomes` table holds ~24k rows
and `jobs/track_signal_outcomes.py` exists in code (the service is absent).

---

## 2. Labels and horizons

| Question | Current | Research direction (later) |
|---|---|---|
| What is the label? | Model A predicts `prob_up` + `expected_return`; labels classified by the frozen threshold ladder | Make the label definition explicit and versioned: forward return over horizon H, sign or quantile, with the exact return definition (see §4) |
| What horizon(s)? | Implicit in training | Document H explicitly (e.g. 5/10/21 trading days); a signal must declare its horizon and be measured at that horizon |
| Multiple horizons? | No | Candidate later: a horizon panel so IC can be measured per horizon |

**Discipline:** a label is a contract. It must be written down, versioned, and
identical in training and in outcome-measurement. Mismatched
train-label/measure-label is a silent invalidator.

## 3. Point-in-time data and survivorship bias

| Concern | Current state | Direction |
|---|---|---|
| Point-in-time prices | EODHD bulk prices; T-1 features only (`ml-conventions.md`) | Keep; document adjusted-price semantics (Track B) |
| Point-in-time fundamentals | `merge_asof` with 45-day disclosure lag | Keep; verify the lag is conservative enough to avoid look-ahead |
| Point-in-time universe | `universe_history` table exists (~1,870 rows) | Use it for PIT membership in research; do not research against today's universe applied to the past |
| Survivorship bias | Risk if delisted symbols are dropped | Research must include delisted/inactive symbols for the period studied; `universe_history` is the substrate |

**Survivorship bias is the most common way a backtest lies.** Any harness that
selects "today's active symbols" and runs them through history will overstate
performance. The universe at time *t* must be the universe *as known at t*.

## 4. Adjusted returns

- Decide and **document** whether returns are computed on adjusted (split +
  dividend) or unadjusted prices, and apply it consistently in features,
  labels, and outcome measurement.
- A mismatch (e.g. adjusted in training, unadjusted in outcomes) produces
  IC that is wrong in ways that are very hard to spot.
- This is a Track B (Data Truth) dependency for Track C.

## 5. Baselines (simple-baseline-first policy)

Before trusting any model, measure trivial baselines on the same data, same
horizon, same universe, same costs:

| Baseline | Why |
|---|---|
| Buy-and-hold ASX 200 | The "do nothing" bar |
| Equal-weight universe | Beta with no skill |
| Past-return momentum (e.g. 12-1) | The cheapest known factor |
| Random portfolio (many draws) | The null distribution for IC/returns |

**A model that does not beat these after costs is not a signal.** Document the
baseline comparison as part of every promotion decision.

## 6. Evaluation metrics

| Metric | Definition | Use |
|---|---|---|
| Rank IC | Spearman corr of predicted score vs realised forward return, per cross-section, per day | Primary skill measure; report mean, std, t-stat, IC decay by horizon |
| Quintile spreads | Return of top quintile minus bottom quintile of the score | Monotonicity + economic magnitude |
| Turnover | Fraction of book changing per rebalance | Cost driver; a high-IC high-turnover signal can still lose after costs |
| Costs | Modelled slippage + brokerage per turnover | Net-of-cost is the only number that matters |
| Hit rate / breadth | Fraction of names with correct sign | Sanity, not a promotion gate by itself |

**Report net-of-cost or do not report.** Gross IC is a research artifact; the
decision is made on net.

## 7. Walk-forward validation

- Use `TimeSeriesSplit` / `PurgedGroupKFold` (already mandated in
  `ml-conventions.md`); **never** random `train_test_split`.
- Purge + embargo around the label horizon to prevent leakage across the
  train/test boundary.
- Walk forward: train on [0, t], test on (t, t+Δ], roll. Report out-of-sample
  metrics only.
- The retraining gates already encode part of this (ROC-AUC ≥ 0.65, ≤ 5%
  degradation vs active on the same OOS window).

## 8. Shadow paper book

- Run a paper book that takes the *live* signal each day and records what it
  *would* have done, with modelled costs, **without trading**.
- This is the bridge between backtest and reality: it measures the signal on
  data it has never seen, in production timing, including the real freshness/
  staleness conditions.
- `asxos/domain/portfolio/paper_trade.py` and the `paper_*` tables/commands
  already exist as scaffolding.

## 9. Promotion gates and kill criteria

A signal moves from research → shadow → (eventually) influence only by passing
**written, pre-registered** gates. Pre-registration matters: gates defined after
seeing results are not gates.

**Illustrative promotion gate (to be calibrated, not adopted as-is):**

- Net-of-cost rank IC mean > 0 with t-stat above a pre-set bar over the
  walk-forward window.
- Positive quintile spread, monotone across quintiles.
- Turnover/cost within budget.
- Beats all §5 baselines net of cost.
- ≥ N weeks of shadow-book agreement with backtest expectation.

**Illustrative kill criteria (pre-registered):**

- Net IC crosses zero for K consecutive weeks.
- Realised drawdown beyond a pre-set bound.
- Drift metric breaches threshold (see §13).
- Data-truth incident invalidates the inputs.

Every signal carries a **verdict file** (committed markdown) recording its
gates, its current status, and the date/evidence of any promotion or kill.

## 10. ML model lifecycle

| Stage | Current | Direction |
|---|---|---|
| Train | `domain/models/train.py`, walk-forward | Document memory budget for Render (retrain is paused on OOM risk) |
| Validate | gates in `ml-conventions.md` | Add calibration + drift to the gate set |
| Register | `model_versions` (`is_active` flag), `asx model activate` | Keep; backup already preserves `model_versions` |
| Serve | `domain/models/cache.py` (60s TTL re-read) | Keep |
| Monitor | `check_model_staleness` job exists, **service absent** | Deploy (Track D); this is the model-side analogue of `check_cron_health` |
| Retire | none | Define a quarantine/retirement workflow |

## 11. Feature leakage

- All features from T-1 data only (mandated). Add a leakage test for every new
  feature confirming only T-1 inputs (per `ml-conventions.md`).
- The shared `FeatureEngine` instance in train and inference is the structural
  fix for train/serve skew; keep the parity test
  (`test_feature_engine.py`).
- Fundamentals zero-fill (documented) is a known, accepted treatment — make sure
  the research harness applies the *same* treatment.

## 12. Target leakage

- The label must be computed from data strictly *after* the feature timestamp by
  exactly the horizon — no overlap.
- Purge/embargo in walk-forward prevents the label window of one fold leaking
  into the features of the next.
- Audit any join that could pull a future-dated row into a past-dated feature.

## 13. Calibration and drift monitoring

- **Calibration.** `prob_up` should mean what it says — measure reliability
  (predicted vs realised frequency) before trusting confidence-scaled outputs.
  Confidence is currently `clip(round(|p-0.5|*200),0,100)` — a *transform*, not
  a *calibration*.
- **Drift.** Monitor feature distributions and prediction distributions over
  time; a shift is an early kill/retrain signal. `check_model_staleness` is the
  natural home.

## 14. Explainability

- SHAP factors are already produced and stored (`signals.shap_factors` JSONB).
- Use them for (a) brief explanations of *why* a name scores as it does, and
  (b) drift diagnosis (which features are driving the change).

## 15. Simple-baseline-first policy (restated as doctrine)

> Every model must justify its existence against a trivial baseline, net of
> costs, on point-in-time, survivorship-bias-free data. If it cannot beat
> momentum and buy-and-hold after costs, it is not a signal — it is overfitting
> with extra steps.

---

## What NOT to do now

- Do not deploy `track_signal_outcomes` yet (it is the *first* Track C item,
  but Track C is Lane B — after loop stability).
- Do not retrain, recalibrate, or add features/signals.
- Do not change the frozen threshold ladder.
- Do not interpret historical `signal_outcomes` rows as a promotion signal until
  the survivorship/PIT/cost discipline above is applied.
