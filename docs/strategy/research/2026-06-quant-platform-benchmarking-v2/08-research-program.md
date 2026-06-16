# 08 — Staged Signal Research Program (modern methods)

Lives in a read-only `research/` package (see `05`): reads production tables, writes only research artefacts — never `signals`/`portfolio_*`. Each phase: objective · data · code/docs · acceptance · first prompt. Methods updated to the 2021–2026 standard.

## Phase 0 — Correctness (read-only verification)
- **Objective:** confirm the signal *means what it claims*.
- **Tasks:** verify `expected_return` units (bps vs fraction); verify `close` vs `adj_close` (ASX ex-date contamination); confirm recency gates; scope a point-in-time universe.
- **Data:** `signals.expected_return` distribution, `metrics.json`, `prices` (close + adj_close), `universe`.
- **Acceptance:** units CONFIRMED/REFUTED; adj_close decision; survivorship plan.
- **First prompt:** A.

## Phase 1 — Baseline suite
- **Objective:** the humility baselines every signal must beat.
- **Tasks:** equal-weight; **12-1 momentum (skip-month)**; 200-day trend; naive value (P/B); naive quality (ROE/EPS); prior-signal persistence; random. Benchmark against the **Chen-Zimmermann Open Source Asset Pricing** factor library.
- **Data:** `prices` (adj_close), `fundamentals`, `universe` (as-of).
- **Code/docs:** `research/baselines.py` (pure functions) + design doc.
- **Acceptance:** each baseline's forward returns reproducible + unit-tested.
- **First prompt:** B.

## Phase 2 — Evaluation metrics
- **Objective:** measure skill in economic units.
- **Tasks:** **rank IC + ICIR**; **net-of-cost decile/quintile spreads** + monotonicity; hit rate; **calibration (reliability + Brier)**; turnover.
- **Data:** `signals` (+ baselines) joined to forward returns (survivorship-safe).
- **Code/docs:** `research/metrics.py` + evaluation report.
- **Acceptance:** rank IC + spread + calibration computed for signal **and** baselines; **first real "useful or coin flip" answer.**
- **First prompt:** C (+ H for calibration).

## Phase 3 — Backtest framework
- **Objective:** trustworthy OOS evidence at the 2026 bar.
- **Tasks:** **purge + embargo → CPCV** (Arian-Norouzi-Seco); as-of universe; leakage checks (Kapoor-Narayanan taxonomy); delisted symbols; liquidity floor (min ADV); proportional cost model; **Deflated Sharpe + PBO**; FDR-controlled trial counting.
- **Data:** `universe_history`/delistings, ADV, cost assumptions.
- **Code/docs:** `research/backtest.py` (seeded, deterministic) + leakage proof.
- **Acceptance:** net-of-cost IC/spread OOS, deflated-significant, PBO < ~0.2–0.5, stable across regimes/sectors.
- **First prompt:** D.

## Phase 4 — Paper portfolio
- **Objective:** prove portfolio usefulness without orders.
- **Tasks:** shadow book / decision ledger; sizing via **denoised covariance + HRP/Schur (`skfolio`)** with an **L1 turnover penalty**; ADV liquidity cap; CGT/franking-aware; attribution (factor vs selection); optional **uncertainty-gated deployment**.
- **Data:** signals, prices, cost/tax assumptions.
- **Code/docs:** decision-ledger (research-only) + attribution + design doc.
- **Acceptance:** shadow after-cost, after-tax IR/drawdown vs AXJO and vs equal-weight/momentum paper books.
- **First prompt:** F (+ G).

## Phase 5 — Production governance
- **Objective:** safe promotion + decay control.
- **Tasks:** add **IC/net-of-cost gate** to `validation.py`; demotion/**kill criteria**; **Evidently** drift + rolling rank IC monitoring; incident response; `review_queue` / agentic review (evals-in-CI + tracing).
- **Data:** `signal_outcomes` (read back), drift metrics.
- **Code/docs:** governance doc + monitors.
- **Acceptance:** rolling IC tracked + alarmed; economic promotion gate; kill criteria; `model activate` re-validates.
- **First prompt:** H + J (red-team) before any promotion.

---

**Gate between phases:** do not advance until acceptance is met. **Do not build Phase 3+ until Phase 1–2 show the signal beats 12-1 momentum and equal-weight on net-of-cost rank IC.** If it does not, quarantine the signal as research-only and keep the brief honest — which the modern evidence (Avramov; HXZ; no-AU-size-premium) says is a very real possible outcome for a long-only small-cap-inclusive ASX book.
