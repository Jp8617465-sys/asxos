# Alpha-research audit — Model A (v1_5) & the portfolio pipeline

**Date:** 2026-06-22 · **Scope:** signal generation + portfolio construction · **Author:** quant audit (Prompt 2, Phase 1)
**Status:** DIAGNOSIS ONLY. No model, threshold, or pipeline code was changed. Two decisions are left open for you at the end.

---

## TL;DR

There is a **real, statistically detectable signal** in `prob_up` — but it is **short-horizon (≈5 days), poorly calibrated in absolute terms, mis-harnessed by a buy-and-hold portfolio, and accompanied by a non-functional `expected_return`**. The training set also carries survivorship and price-adjustment biases that flatter it.

**Verdict: PAPER-TRADE ONLY — continue incubation with required fixes.** Not "reject" (the signal is real); not "limited capital" (too many unfixed biases and only ~3.5 months of un-costed evidence).

This is decision-support, not advice, and a single result here is not proof of alpha.

---

## 1. Methodology & data

All performance numbers come from the **`signal_outcomes`** table — the existing `track_signal_outcomes` job records, for past signals, the realised forward return and direction:

- **24,454 rows**, **10 distinct signal dates**, **2025-12-08 → 2026-03-25** (~3.5 months).
- Fields used: `ml_prob` (prob_up), `ml_expected_return`, `signal_label`, `actual_return_5d`, `actual_return_21d`, `was_direction_correct`, `regime`.
- **All returns are GROSS** (no brokerage, no slippage).

**Caveats that bound every conclusion below:**
1. **Small sample.** 10 cross-sections over one mildly-down quarter (mean 5d return −0.98%). Significance is *suggestive, not conclusive*.
2. **Gross of costs.** On the micro-caps this model favours, realistic slippage would consume much of a sub-1% weekly edge.
3. **Single market regime** (this window was `neutral`/mildly down). No bull/bear stress.
4. **Data-quality flag.** Some `signal_outcomes` rows have NULL `ml_prob` (they sort into the top global deciles). The per-date **rank-IC** is robust to this; the pooled decile table is not, so lead with rank-IC.

Reproduce: the four SQL queries are in Appendix A.

---

## 2. Does the signal work? (the core question)

### 2a. `prob_up` ranking power — YES at 5 days, NO at 21 days

Rank-IC = Spearman correlation between `prob_up` and forward return, computed **per signal date** then averaged (the standard cross-sectional IC).

| | 5-day | 21-day |
|---|---|---|
| Mean rank-IC | **+0.1335** | +0.0171 |
| Std of IC across dates | 0.1403 | — |
| t-stat (×√10) | **3.01** ✅ | 0.48 ❌ |

**Interpretation:** A rank-IC of ~0.13 at t≈3 is a *genuinely strong* cross-sectional signal (many production equity signals run IC 0.03–0.05). The model **ranks** stocks well over the next 5 days. **But the edge evaporates by 21 days** (IC 0.017, t=0.48 — indistinguishable from noise). The signal's half-life is short, matching its 5-day training target.

### 2b. Decile monotonicity (prob_up → realised 5d return)

| prob_up decile | n | mean 5d return | mean 21d return | 5d hit-rate |
|---|---|---|---|---|
| 1 (lowest) | 2,446 | **−3.77%** | +5.16% | 26.1% |
| 2 | 2,446 | −3.10% | +8.07% | 28.0% |
| 3 | 2,446 | −2.20% | +7.82% | 28.7% |
| 4 | 2,446 | −1.08% | +2.44% | 28.0% |
| 5 | 2,445 | +0.79% | +4.53% | 30.8% |
| 6 | 2,445 | −0.86% | +2.12% | 33.7% |
| 7 | 2,445 | −0.78% | +1.19% | 36.2% |
| 8 | 2,445 | −0.05% | +2.93% | 38.0% |
| 9 | 2,445 | +0.02% | +7.03% | 35.0% |
| 10 (highest) | 2,445 | **+1.22%** | +7.87% | **43.7%** |

**Interpretation:** Top-minus-bottom 5d spread ≈ **+4.99% gross** (long D10 / short D1). The **hit-rate is cleanly monotonic 26% → 44%** even though the middle deciles' mean returns are noisy. The ranking works; the point estimates are noisy at this sample size. *(D9–10 `avg_prob` is null due to the NULL-prob rows noted above — another reason to trust the per-date rank-IC over the pooled deciles.)*

### 2c. Do the labels separate outcomes?

| label | n | mean 5d | mean 21d | 5d hit |
|---|---|---|---|---|
| STRONG_BUY | 4,691 | **+0.36%** | +6.44% | 38.7% |
| BUY | 4,112 | −0.41% | +1.86% | 37.9% |
| HOLD | 15,318 | **−1.57%** | +5.14% | 29.7% |
| SELL | 294 | +0.32% | +12.96% | 35.0% |
| STRONG_SELL | 39 | −1.63% | −4.31% | 2.6% |

**Interpretation:** On the **long side at 5d the ladder works**: STRONG_BUY (+0.36%) > BUY (−0.41%) > HOLD (−1.57%). STRONG_SELL is correctly the worst. **The short side (SELL/STRONG_SELL) is too small to trust** (n=294 / 39) and SELL is anomalously positive. The ladder's value is on the long side, short-horizon.

---

## 3. What's broken

### 3a. 🔴 `expected_return` is non-functional (units mismatch + no predictive content)

- **Units mismatch (verified by direct code read).** v1_5 trains the regressor on `forward_return × 10_000` → **basis points** (`asxos/domain/models/train.py:156`). The label ladder compares `expected_return` to **fractional** cutoffs: `expected_return > 0.05` for STRONG_BUY (`asxos/domain/signals/thresholds.py:27`). So a predicted +0.05 **bp** (0.0005%) clears the bar meant to require **+5%**. The return-gate is effectively a **rubber stamp** → labels are driven almost entirely by `prob_up`. (run_id=1: 453 STRONG_BUY of 1,703.)
- **No predictive content.** Even ignoring units, `corr(expected_return, forward 5d) = 0.013`, `21d = −0.001`. It carries ~zero signal. Range −23.6 to +323.9, mean 0.254 — wild and uncalibrated.
- **Conclusion:** `expected_return` as currently produced should **not** drive labels or position sizing. `prob_up` is the trustworthy conviction signal. (v1_6-shadow already added a `target_unit` metadata contract to fix the units ambiguity — but v1_6 is not active.)

### 3b. 🟠 `prob_up` is uncalibrated in absolute terms

- Overall directional hit-rate = **40%** at the 0.5 cutoff. This looks bad but is consistent with strong ranking: the window was mildly down (mean 5d −0.98%), so fewer than half of all names rose; `prob_up` *ranks* correctly but its **absolute probabilities don't map to realised up-rates** (no decile exceeds 44% hit).
- Cause: raw LightGBM `predict_proba`, **no Platt/isotonic calibration** (`train.py:164`).
- **Conclusion:** Treat `prob_up` as a **rank**, not a literal probability, until a calibration layer is added.

### 3c. 🔴 Horizon mismatch (the strategic blocker)

The signal's edge is at **5 days** and gone by **21**. Yet the portfolio is a **20-name buy-and-hold book, rebalanced weekly, with a 10-year stated horizon** (`profiles.horizon_years=10`). A 5-day-decay signal is being used to select multi-week/multi-year holds — **the alpha decays long before the holding period matters.** This, more than any single bug, caps the strategy's realistic edge. Fix: align rebalance cadence to the signal's half-life, *or* retrain to the holding horizon (e.g., 21d/63d labels).

---

## 4. Data integrity & validation (agent-audited, file:line)

**Sound:**
- ✓ Time-aware CV: expanding-window `TimeSeriesSplit` (`train.py:88`), test strictly after train; verified by `tests/test_train_walk_forward.py:56`.
- ✓ No hyperparameter tuning (fixed `DEFAULT_*_PARAMS`) → no tuning leakage. Feature set locked (`MODEL_A_FEATURES`) → no selection leakage.
- ✓ Features are per-symbol rolling (no cross-sectional leakage); fundamentals point-in-time with a 45-day disclosure lag (`loader.py:209`).
- ✓ ROC-AUC 0.7097 is **OOS per-fold** (mean of 5 fold test scores).

**Weaknesses:**
- 🟠 **Survivorship bias.** `is_active` is not point-in-time; training & signal loaders filter `WHERE is_active=TRUE` at *query* time (`retrain_model_a.py:138`, `loader.py:143`). Names delisted during the window are silently dropped → optimistic training.
- 🟠 **Raw-close labels (v1_5).** `price_basis="close"` (`training_config.py:105`) — ex-dividend/split jumps contaminate both momentum features and the forward-return **label**. (v1_6-shadow uses `adj_close`.)
- 🟠 **Capacity/cost blindness.** No liquidity floor at signal stage; only the allocator's $50M cap (`allocator.py:33`). The book picked sub-$0.10 names (QPM $0.018, KKO $0.035). The ~5% gross decile spread is on names that can't absorb $25–50k without large slippage.
- 🟡 **No purge/embargo** on overlapping 5d labels (`purge_embargo_days` declared but unused, `train.py:88`). Small at a 5-day horizon, but a gap vs the conventions doc.
- 🟡 **Deployed model is in-sample** — only fold metrics are OOS; the live artefact is refit on 100% of data (`train.py:172`).
- 🟡 **No probability calibration** (see 3b). **`signal_outcomes` is not versioned** in `migrations/` (schema drift) and has some NULL `ml_prob` rows.

---

## 5. Evidence table

| # | Claim | Evidence | State | Severity | Action |
|---|---|---|---|---|---|
| 1 | prob_up ranks 5d returns with real edge | rank-IC 0.1335, t=3.01 | Verified | asset | Preserve; monitor IC |
| 2 | Edge decays by 21d | rank-IC 0.017, t=0.48 | Verified | 🔴 High | Align horizon/cadence |
| 3 | expected_return broken (units + non-predictive) | corr 0.013; train.py:156 bp vs thresholds.py:27 fraction | Verified | 🔴 Critical | Fix/remove (needs sign-off) |
| 4 | prob_up uncalibrated (absolute) | 40% hit @0.5; no calibration train.py:164 | Verified | 🟠 High | Add isotonic layer |
| 5 | Survivorship bias | is_active not as-of; retrain_model_a.py:138 | Verified | 🟠 High | Effective-dated universe |
| 6 | Raw-close labels (v1_5) | training_config.py:105 | Verified | 🟠 High | Train on adj_close |
| 7 | No purge/embargo | train.py:88 | Verified | 🟡 Med | Purge+embargo CV |
| 8 | Deployed model in-sample | train.py:172 | Verified | 🟡 Med | Hold-out OOS for artefact |
| 9 | Micro-cap capacity | allocator.py:33; no signal-stage gate | Verified | 🟠 High | Liquidity filter + slippage |
| 10 | signal_outcomes unversioned + null probs | not in migrations/; null avg_prob | Verified | 🟡 Med | Migration 0025; fix nulls |
| 11 | No IC/decile/calibration analytics | grep: none | Verified | 🟠 High | Build measurement framework |
| 12 | Fundamentals PIT + per-symbol features | loader.py:209; feature_engine.py:124 | Verified | sound | none |

## 6. Top 5 blockers (ranked)

1. **Horizon mismatch** — 5-day alpha driving a buy-and-hold weekly book.
2. **`expected_return` broken** — units rubber-stamp + zero predictive content. *(Locked surface.)*
3. **`prob_up` uncalibrated** — good ranking, untrustworthy absolute probabilities.
4. **Survivorship + raw-close labels** — inflate apparent training edge.
5. **Capacity/cost blindness** — micro-cap picks; net edge likely marginal after slippage.

## 7. Investment-committee conclusion

**Continue incubation, paper-trade only.** A real 5-day ranking signal exists and is worth developing. Do **not** deploy capital until: (a) holding/rebalance horizon is aligned to the signal's half-life; (b) `expected_return` is fixed or removed; (c) `prob_up` is calibrated; (d) a **costed, liquidity-filtered, purged-OOS** backtest reproduces a **positive net** decile spread across more than one regime.

---

## 8. Prioritized Phase-2 plan & open decisions

Per your sequencing rule (measure before you change the machine), the recommended order:

1. **Signal alpha-evaluation framework** (productionize this audit): rank-IC, decile spreads, `prob_up` calibration curve, `expected_return` calibration diagnostic, 5d-vs-21d decay — as a pure module + CLI + migration `0025` (version `signal_outcomes`) + tests. *Safe, read-only, no model change.* **← recommended next build.**
2. Liquidity filter + realistic slippage (extends the cost model already shipped in the monitor).
3. `prob_up` isotonic calibration layer (diagnostics first, then the layer).
4. `expected_return` fix or removal **(repo-locked — needs explicit instruction).**
5. Purged/embargoed walk-forward CV.
6. Horizon experiment: retrain at 21d/63d labels and re-measure IC/decay.
7. Survivorship fix (effective-dated universe); adj_close labels (promote v1_6 path).

**Two decisions awaiting you:**
- **A. What to build next** — the alpha-evaluation framework (rec), that + purged CV, or hold.
- **B. `expected_return`/threshold fix** — `ml-conventions.md` marks thresholds "do not modify without explicit instruction." Authorize the fix/removal, or hold and only document.

---

## Appendix A — reproducible queries

```sql
-- 1) overall correlations + expected_return scale + hit
SELECT corr(ml_prob,actual_return_5d), corr(ml_prob,actual_return_21d),
       corr(ml_expected_return,actual_return_5d),
       min(ml_expected_return), max(ml_expected_return), avg(ml_expected_return),
       avg(actual_return_5d), avg(actual_return_21d),
       avg((was_direction_correct)::int) FROM signal_outcomes;

-- 2) prob_up decile table
WITH d AS (SELECT ntile(10) OVER (ORDER BY ml_prob) decile, ml_prob,
           actual_return_5d, actual_return_21d FROM signal_outcomes)
SELECT decile, count(*), avg(ml_prob), avg(actual_return_5d), avg(actual_return_21d),
       avg((actual_return_5d>0)::int) FROM d GROUP BY decile ORDER BY decile;

-- 3) per-date Spearman rank-IC (prob_up vs 5d/21d)
WITH r AS (SELECT signal_date,
   rank() OVER (PARTITION BY signal_date ORDER BY ml_prob) rp,
   rank() OVER (PARTITION BY signal_date ORDER BY actual_return_5d) rr5,
   rank() OVER (PARTITION BY signal_date ORDER BY actual_return_21d) rr21
   FROM signal_outcomes),
pd AS (SELECT signal_date, corr(rp,rr5) ic5, corr(rp,rr21) ic21 FROM r GROUP BY signal_date)
SELECT avg(ic5), avg(ic21), stddev(ic5),
       avg(ic5)/nullif(stddev(ic5),0)*sqrt(count(*)) t5 FROM pd;

-- 4) by signal_label
SELECT signal_label, count(*), avg(actual_return_5d), avg(actual_return_21d),
       avg((actual_return_5d>0)::int) FROM signal_outcomes GROUP BY signal_label;
```

## Appendix B — key code references
- Label/target & units: `asxos/domain/models/train.py:58` (`build_target`), `:156` (`reg_scale`/basis_points), `:88` (`walk_forward_split`).
- Thresholds: `asxos/domain/signals/thresholds.py:26-50`.
- Inference: `asxos/domain/models/model_a.py` (prob_up/expected_return columns).
- Universe/survivorship: `asxos/ingestion/universe.py`, `jobs/retrain_model_a.py:138`, `asxos/domain/signals/loader.py:143`.
- Features: `asxos/domain/signals/feature_engine.py:22` (`MODEL_A_FEATURES`).
- Outcome tracker: `jobs/track_signal_outcomes.py` → `signal_outcomes` (unversioned).
