# Alpha signal verification — Model A v1_5 (Phase 1)

**Date:** 2026-06-22 · **Question:** *Is this a statistically meaningful, investable short-horizon signal, or a sophisticated stock screener?*
**Method:** independent recomputation from `signals`/`signal_outcomes` × `prices` (total-return, per-symbol trading-day forward returns). No model/threshold/pipeline code changed.

> This **supersedes the optimistic read** in `alpha-research-audit.md`. That audit used the tracking job's stored `actual_return_5d`; independent reconstruction is weaker and less robust.

---

## 1. Executive conclusion

**Evidence of a WEAK, NON-INVESTABLE signal. Closer to a stock screener than a tradable short-horizon alpha. Data is insufficient for statistical confidence. Paper-only; do not approve capital.**

The model has a faint, short-horizon *loser-avoidance* tendency, but:
- the 5-day rank-IC is **~0.09, not robust** to return definition and **not statistically established** (the "10 dates" are ~2 independent market episodes);
- it **vanishes in the tradable universe** (IC 0.065, t=0.94) and lives mostly in **illiquid** names;
- the **top decile — where the long book fishes — has no edge**;
- it **decays to zero by 10 days and mildly reverses by 21**;
- `expected_return` is **non-predictive** and the composite does **not** beat `prob_up` alone;
- the portfolio's **buy-and-hold / weekly / 10-yr** construction is **horizon-mismatched** to a ≤5-day signal.

This is a "make it hard to fool ourselves" result: the earlier 0.13/t=3.0 headline does not survive scrutiny.

---

## 2. Verified findings (direct from data)

### 2.1 IC by horizon (per-date Spearman, total-return adj_close)

| Horizon | n dates | prob_up IC | t* | composite IC | expected_return IC |
|---|---|---|---|---|---|
| 5d | 10 | **0.095** | 1.84 | 0.091 | 0.051 |
| 10d | 10 | 0.034 | 0.68 | 0.030 | 0.003 |
| 21d | 10 | **−0.060** | −1.83 | −0.055 | −0.041 |
| 63d | 7 | 0.035 | 4.18 ⚠️ | 0.041 | — |

\* **t-stats are not trustworthy** (see 2.5). The 63d value is an overlapping-window artifact.

**Read:** 5d ranking is weak-positive; **decays to zero by 10d; mildly NEGATIVE (reversal) by 21d.**

### 2.2 Robustness to return definition (5d, same 10 dates)
| Return basis | rank-IC |
|---|---|
| Stored `actual_return_5d` (audit's method) | 0.119 (t=2.39) |
| Reconstructed close, 5 trading days | 0.093 |
| Reconstructed adj_close, 5 trading days | 0.095 |

**The audit's 0.12–0.13 is ~0.025 IC optimistic vs a clean reconstruction.** The signal is not robust to a defensible change in return definition.

### 2.3 Decile spread (5d, adj_close, per-date deciles averaged)
| Decile (prob_up) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean 5d return % | −2.66 | −2.35 | −1.93 | −1.50 | −1.24 | −1.02 | −0.67 | −0.59 | −0.73 | **−0.80** |

- Monotonic across the **bottom 80%**, then **plateaus/reverses at the top**. **D10 (−0.80%) is worse than D7/D8.**
- **Every decile is negative** (down sample); the "best" names still lost money on average.
- Top-minus-bottom 5d spread ≈ **+1.86% gross** — but it's a *short-side* result (avoid D1), not long-side. **The long-only portfolio selects from D10, the one place with no edge.**

### 2.4 Tradability / liquidity concentration (5d)
| Universe | avg names/date | IC | t |
|---|---|---|---|
| Illiquid (rest) | ~1,000 | 0.097 | 2.32 |
| **Tradable** (price≥$0.20 & $vol≥100k) | ~530 | **0.065** | **0.94** |

**The edge concentrates in names you can't trade.** In the tradable universe it is weak and not significant.

### 2.5 Sample structure (why no t-stat is trustworthy)
The 10 signal dates: **2025-12-08 (alone)**, then **2026-03-13 → 03-25** (nine near-consecutive trading days, gaps 1–3d). Forward windows of near-consecutive dates **overlap almost completely** → the effective number of independent market episodes is **≈2**, not 10. Regime: 8 neutral, 2 bear → **~one regime.** **There is effectively no statistical power; every IC is a point estimate from ~2 episodes.**

### 2.6 expected_return diagnostics
- Rank-IC: 0.051 (5d), 0.003 (10d), −0.041 (21d) → **non-predictive, mildly harmful at 21d.**
- Units bug confirmed earlier (bp vs fraction). Range −23.6…+323.9.
- **Composite (0.6·prob+0.4·exp_ret) IC ≤ prob_up IC at every horizon** → `expected_return` adds nothing; **prob_up-only ≥ composite.**

### 2.7 Calibration
| pred prob bucket | 0.07 | 0.16 | 0.25 | 0.35 | 0.45 | 0.55 | 0.64 | 0.74 | 0.83 |
|---|---|---|---|---|---|---|---|---|---|
| realised 5d up-rate | 0.26 | 0.30 | 0.31 | 0.30 | 0.33 | 0.35 | **0.36** | 0.33 | 0.33 |

**Severely miscalibrated** (pred 0.83 → realised 0.33) and **discrimination plateaus at the top.** `prob_up` is at best a weak *rank*, not a probability.

---

## 3. Answers to the 7 verification questions

1. **5d IC ~0.13?** *Refuted as stated.* ≈0.095 on clean reconstruction (0.12 only with the optimistic stored return), and not significant given ~2 independent episodes.
2. **Decay by 10/21/63d?** *Confirmed — and worse:* zero by 10d, **negative (reversal) by 21d.** 63d t is an artifact.
3. **expected_return predictive?** *Refuted.* ~0 to slightly negative; non-functional.
4. **prob_up ranking power?** *Weak/qualified.* Loser-avoidance only; **no edge in the top decile; gone in tradable names.**
5. **Composite beats prob_up alone?** *No.* Composite ≤ prob_up everywhere → quarantining `expected_return` is justified.
6. **Holding/rebalance aligned to horizon?** *No — severe mismatch.* ≤5-day signal, multi-week/10-yr book → harvests the reversal.
7. **Concentrated in illiquid/one sector/regime/period?** *Yes, badly.* Illiquid-concentrated, ~one regime, **one Dec date + one 2-week March cluster.**

---

## 4. Inferred risks (plausible, not fully proven)
- The faint 5d edge is likely **short-term reversal / microstructure** (illiquid bounce), not durable predictive alpha — consistent with illiquid concentration + 21d reversal.
- After realistic micro-cap slippage (often 100s of bps), the +1.86% gross decile spread is probably **negative net.**
- `prob_up`'s miscalibration is partly the down-sample base rate; magnitude unknown without more regimes.

## 5. Unsupported assumptions (cannot determine yet)
- True 5d IC and its stability — **needs ≥50–100 independent dates** (we have ~2 episodes).
- 63d behaviour — uncomputable from stored data; reconstruction is overlapping-window only.
- Sector/factor neutrality of the edge — not yet isolated.
- Whether the signal survives transaction costs in the tradable universe — likely not, but unproven.

---

## 6. Portfolio-construction recommendation
- **Holding period mismatched: YES.** A ≤5-day, 21d-reversing signal should not drive a buy-and-hold book. Either shorten holding to the signal half-life *or* retrain to the holding horizon (21d/63d labels) — but only after data backfill proves a longer-horizon edge exists (current 21d IC is negative).
- **Weekly rebalance:** inappropriate for the measured decay; but daily/short-horizon trading is **not justified** either (no net edge after costs/liquidity). → **Neither current nor faster trading is supported.**
- **20-name concentration:** picks from the top decile, which has no edge → concentration amplifies noise.
- **Inverse-vol weighting:** irrelevant to the core problem (the ranking itself isn't tradable).
- **expected_return in scoring:** **quarantine** (don't delete) — confirmed non-additive.
- **Liquidity filters:** should be **mandatory** for any production-like portfolio; and note the edge mostly disappears once you apply them.

---

## 7. Implementation summary (this phase)
- **Code changed:** none (verification only).
- **Queries run:** IC by horizon (5/10/21/63d) for prob_up/composite/expected_return; close-vs-adj robustness; decile spread; date-independence; liquidity-bucket IC; calibration. (All reproducible — see the framework in §9.)
- **Data:** `signals` (7 dates, May–Jun), `signal_outcomes` (24,454 rows / 10 dates / Dec–Mar), `prices` (372 trading dates, 2025-01→2026-06).

## 8. Next actions
- **Approve immediately:** quarantine `expected_return` from the composite score (research variant; prob_up-only ≥ composite). Make liquidity filters mandatory in any production-like build.
- **Approve research (the #1 prerequisite):** **backfill historical signals** — run v1_5 over 2025 daily history to produce ~250 independent cross-sections, so IC/decay/decile can be measured with power. *Nothing here is decision-grade until this exists.*
- **Freeze:** any move toward daily/short-horizon live trading; any new ML model or features; SHAP/explainability polish.
- **Do not approve:** capital deployment; treating the current 20-name book as alpha.

## 9. The repeatable framework
This verification is productionized as `asxos/domain/research/alpha_eval.py` + `scripts/alpha_eval.py` (see that module). It computes IC-by-horizon, decile spreads, score-variant comparison, liquidity buckets, and calibration — **with a built-in effective-sample-size / overlapping-window guard** so it never reports the inflated t-stats this audit had to manually discount. Its outputs become decision-grade once the signal backfill (§8) lands.
