# 07 — ASXOS Benchmark Ladder (L0 → L5)

A signal climbs these levels in order. ASXOS is solidly **L0**, partially **L1**, and reaches into **L5** on ops/governance plumbing — but the **L2/L3/L4 evidence core is missing**. Invest there.

---

## L0 — Operational signal — ✅ **MET**
- **Required evidence:** jobs run, data fresh, signals written, brief honest.
- **ASXOS status:** recovery GREEN; crons recovered; deadman + backup; honest stale email; recency gate (`a719b3c`).
- **Gaps:** none material.
- **Next step / acceptance:** maintain. *Accept:* green `job_runs`, deadman healthy.

## L1 — Data-trust signal — 🟡 **PARTIAL**
- **Required:** adjusted prices, complete-day anchor, point-in-time universe, no partial data, no stale generation.
- **ASXOS status:** complete-day anchor + recency gate done; **raw close** and **survivorship universe** remain (`06`, Risks 2 & 4).
- **Gaps:** `adj_close` not used; `is_active` applied to history.
- **Next step:** adopt `adj_close`; build `universe_history`.
- **Acceptance:** features/target on `adj_close`; backtests include then-listed/now-delisted names; ex-date artefacts gone.

## L2 — Baseline-beating signal — ❌ **NOT MET**
- **Required:** beats equal-weight, 12-1 momentum, trend/MA, naive value/quality, and prior-signal persistence, measured by **rank IC** and **return spreads**.
- **ASXOS status:** no baselines, no IC, no spreads computed.
- **Gaps:** the entire evaluation harness.
- **Next step:** baseline suite (`08` Phase 1) + IC/quintile metrics (Phase 2).
- **Acceptance:** signal's rank IC and top-minus-bottom quintile spread **exceed every baseline** over a multi-year sample (pre-cost first, then net-of-cost).

## L3 — Research-grade signal — ❌ **NOT MET**
- **Required:** out-of-sample, walk-forward with **purge/embargo**, costs, turnover, liquidity, regime/sector/size splits, survivorship controls, statistical confidence (deflated).
- **ASXOS status:** 5-fold no purge; no costs/turnover/liquidity; survivorship-biased.
- **Gaps:** purged walk-forward harness; cost model; deflated significance.
- **Next step:** backtest framework (`08` Phase 3).
- **Acceptance:** positive net-of-cost IC/spread out-of-sample, **Deflated Sharpe** significant given trial count, stable across regimes/sectors, t-stat respecting the multiple-testing bar.

## L4 — Portfolio-useful signal — ❌ **NOT MET**
- **Required:** improves a paper portfolio's risk-adjusted return / drawdown / tracking error; handles capacity/liquidity/tax; stable enough for decision support.
- **ASXOS status:** `build_portfolio` exists (filter + z-composite + inverse-vol) but unproven; `paper_trade.py` is explicitly "not a backtester."
- **Gaps:** shadow book, attribution, cost/tax-aware sizing, risk model.
- **Next step:** paper portfolio + attribution (`08` Phase 4).
- **Acceptance:** shadow book beats equal-weight/momentum paper books on **after-cost, after-tax IR or drawdown** over a sustained out-of-sample window.

## L5 — Production-governed signal — 🟡 **PARTIAL**
- **Required:** monitored, drift-aware, outcome-tracked, kill criteria, promotion/demotion gates, human-approval boundaries.
- **ASXOS status:** promotion gates (statistical: MIN_ROC_AUC=0.65, MAX_DEGRADATION=5%, MIN_SAMPLES=1000) + JobMonitor + personal-use firewall; **but** `signal_outcomes` unread, no kill criteria, **ungated manual activation**.
- **Gaps:** outcome read-back, drift/calibration monitoring, IC/cost promotion gate, kill rules, re-validation on `model activate`.
- **Next step:** governance (`08` Phase 5).
- **Acceptance:** rolling IC tracked + alarmed; promotion requires an economic gate; documented kill criteria; activation re-validates.

---

**Ladder principle:** **L5 plumbing without L2-L4 evidence is governance over an unmeasured signal.** ASXOS must climb L2 → L3 → L4 (evidence) while keeping its strong L0/L5 plumbing — not add more L5 governance to an unproven signal.
