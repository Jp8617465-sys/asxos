# 08 — Staged Signal Research Program

All of this lives in a read-only `research/` module (see `05`): it **reads** production tables and **writes only** research artefacts — never `signals`/`portfolio_*`. Each phase has objective · required data · code/docs · acceptance criteria · first prompt.

---

## Phase 0 — Correctness (do first; mostly read-only verification)
- **Objective:** establish that the signal *means what it claims* before measuring it.
- **Tasks:** verify `expected_return` units (bps vs fraction); verify `close` vs `adj_close`; confirm `latest_complete_trading_day` behaviour; scope a point-in-time universe.
- **Required data:** `signals.expected_return` distribution (SELECT-only), `models/*_metrics.json`, `prices` (close + adj_close), `universe`.
- **Code/docs:** a verification memo; no production change.
- **Acceptance:** units classified CONFIRMED/REFUTED; adj_close decision made; survivorship plan written.
- **First prompt:** Prompt A.

## Phase 1 — Baseline suite
- **Objective:** the humility baselines every signal must beat.
- **Tasks:** equal-weight; 12-1 momentum (skip-month); 200-day trend/MA; naive value (low P/B rank); naive quality (high ROE/EPS rank); prior-signal persistence; random.
- **Required data:** `prices` (adj_close), `fundamentals`, `universe` (ideally as-of).
- **Code/docs:** `research/baselines.py` (pure functions); design doc.
- **Acceptance:** each baseline's forward returns reproducible and unit-tested.
- **First prompt:** Prompt B.

## Phase 2 — Evaluation metrics
- **Objective:** measure skill in economic units.
- **Tasks:** rank IC (mean, t-stat, IR-of-IC); quintile/decile spreads + monotonicity; top-minus-bottom return; turnover; hit rate; calibration (reliability + Brier).
- **Required data:** `signals` (+ baselines) joined to realised forward returns (survivorship-safe).
- **Code/docs:** `research/metrics.py`; evaluation report.
- **Acceptance:** IC + spread + calibration computed for the signal **and** every baseline; first real "useful or coin flip" answer.
- **First prompt:** Prompt C.

## Phase 3 — Backtest framework
- **Objective:** trustworthy out-of-sample evidence.
- **Tasks:** walk-forward with **purge + embargo**; as-of universe snapshots; leakage checks; include delisted symbols; liquidity floor (min ADV); cost model; **Deflated Sharpe / PBO**.
- **Required data:** `universe_history`/delistings, ADV, cost assumptions.
- **Code/docs:** `research/backtest.py` (seeded, deterministic); harness design + leakage proof.
- **Acceptance:** net-of-cost IC/spread out-of-sample, deflated-significant given trial count, stable across regimes/sectors.
- **First prompt:** Prompt D.

## Phase 4 — Paper portfolio
- **Objective:** prove portfolio usefulness without real orders.
- **Tasks:** shadow book / decision ledger; position sizing (inverse-vol → shrinkage covariance); transaction-cost assumptions; CGT/tax awareness; attribution (factor vs selection).
- **Required data:** signals, prices, cost/tax assumptions, holdings model.
- **Code/docs:** decision-ledger table (research-only) + attribution; design doc.
- **Acceptance:** shadow IR/drawdown vs AXJO and vs equal-weight/momentum paper books, after cost and tax.
- **First prompt:** Prompt F (+ G for risk/liquidity overlay).

## Phase 5 — Production governance
- **Objective:** safe promotion and decay control.
- **Tasks:** promotion gates (add IC/cost gate to `validation.py`); demotion/kill criteria; drift + rolling-IC monitoring; incident response; `review_queue` / agentic review.
- **Required data:** `signal_outcomes` (read back), drift metrics.
- **Code/docs:** governance doc + monitors.
- **Acceptance:** rolling IC tracked + alarmed; promotion economically gated; kill criteria documented; `model activate` re-validates.
- **First prompt:** Prompt H (calibration) + Prompt J (red-team) before any promotion.

---

**Gate between phases:** do not advance until the prior phase's acceptance criteria are met. Specifically, **do not build Phase 3+ until Phase 1-2 show the signal beats 12-1 momentum and equal-weight on rank IC.** If it does not, the right outcome is to quarantine the signal as research-only and keep the brief honest.
