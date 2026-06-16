# 04 — Mathematics & Investment Theory to Apply

For each concept: *what it means · why it matters · ASXOS today · first practical implementation.* Priorities marked **[P0]** (correctness, do first), **[P1]** (evaluation), **[P2]** (construction/monitoring).

## 1. Return definitions

- **Arithmetic vs log returns.** Log returns are time-additive and better for stats; arithmetic for portfolio aggregation. *ASXOS:* arithmetic 5-day forward on **raw** close. *First [P0]:* compute returns on `adj_close`; document the convention.
- **Adjusted returns.** Splits/dividends/rights must be neutralised. *ASXOS:* not applied. *First [P0]:* switch features + target to `adj_close`.
- **Excess returns.** Over risk-free or benchmark (AXJO). *ASXOS:* none. *First [P1]:* evaluate signal vs AXJO excess return.
- **Forward returns & horizon.** The 5-day horizon defines the whole signal. *ASXOS:* fixed 5-day, unjustified vs weekly cadence. *First [P1]:* horizon-sensitivity check (5/10/21 day).

## 2. Cross-sectional ranking

- **Ranks / z-scores / winsorization / robust scaling.** Convert raw features to comparable cross-sectional scores; winsorize to tame outliers (critical for raw-close spikes and thin small-caps). *ASXOS:* z-scores only in the allocator; no winsorization in features. *First [P1]:* per-date winsorize + z-score features.
- **Sector/industry neutralization.** Remove sector tilts so the signal isn't just a sector bet. *ASXOS:* none. *First [P2]:* sector-relative momentum (symbol minus GICS-sector median).

## 3. Factor models

- **Market beta, size, value, quality/profitability, investment, momentum, low-vol.** The recognised return drivers. *ASXOS:* feature proxies for value/size/momentum/quality/low-vol, none formalised or residualised. *First [P1]:* regress the signal's returns on FF + momentum to test for **incremental** alpha.
- **Residualization.** Strip known-factor exposure to isolate genuine alpha. *ASXOS:* not done. *First [P2]:* residualize signal vs FF before claiming edge.

## 4. Predictive metrics

- **Rank IC (Spearman of prediction vs forward return).** The single most important signal-quality metric; ties to Grinold's IR = IC × √Breadth. *ASXOS:* **not computed.** *First [P1]:* daily rank IC of `prob_up` and `expected_return` vs realised forward return; report mean, t-stat, IR-of-IC.
- **Pearson/Spearman; hit rate.** Linear vs rank correlation; directional accuracy. *First [P1]:* alongside IC.
- **AUC.** Classifier discrimination (ASXOS's only metric). Useful but not sufficient — does not measure economic value.
- **Calibration / Brier score.** Does prob 0.6 mean 60%? *ASXOS:* uncalibrated. *First [P1]:* 10-bin reliability diagram + Brier on OOS.
- **RMSE/MAE for expected returns.** Regression accuracy — but **units must be correct first** (see `06`).

## 5. Portfolio metrics

- **Sharpe, Information Ratio, tracking error, drawdown, turnover, active share, risk contribution.** The scorecard for a *portfolio*, distinct from predictive metrics. *ASXOS:* none computed for the signal. *First [P1]:* IR + turnover of a simple top-decile long book vs AXJO; *then [P2]* drawdown, risk contribution.

## 6. Statistical robustness

- **Out-of-sample / walk-forward.** *ASXOS:* expanding TimeSeriesSplit, 5 folds. *First [P1]:* keep walk-forward.
- **Purging / embargo.** Stop label-window leakage across fold boundaries. *ASXOS:* **absent** (5-day horizon overlaps). *First [P1]:* add purge + embargo to `walk_forward_split`.
- **Bootstrapping / confidence intervals.** Quantify uncertainty on IC/Sharpe. *First [P2].*
- **Multiple-testing / FDR / t > 3 / Deflated Sharpe / decay.** Every new feature or threshold tweak is a trial; honour t > 3 (Harvey-Liu-Zhu) and deflate Sharpe (Bailey-López de Prado). *ASXOS:* no discipline yet. *First [P1]:* count trials; report deflated metrics.

## 7. Portfolio construction

- **Mean-variance / risk parity / risk budgeting.** Use covariance, not just vol. *ASXOS:* inverse-vol only. *First [P2]:* Ledoit-Wolf shrinkage covariance for sizing.
- **Constraints / transaction costs / liquidity / turnover penalties.** *ASXOS:* sector/cash caps + CGT-defer (good start), no costs/turnover. *First [P2]:* turnover penalty + ADV liquidity floor + cost model.
- **Tax-aware overlays.** *ASXOS:* CGT 12-month boundary defer already encoded — keep and measure after-tax IR.

## 8. Production monitoring

- **Data / feature / prediction / calibration drift.** Detect input or output distribution shifts. *ASXOS:* job liveness only. *First [P2]:* log feature-distribution summaries per run.
- **Realised-outcome tracking & signal decay.** *ASXOS:* `signal_outcomes` written, **never read**. *First [P1]:* read it back into rolling IC/hit-rate.
- **Kill criteria.** Pre-committed rules to demote a decayed signal. *ASXOS:* none. *First [P2]:* "rolling 3-month IC < 0.01 for 2 months → quarantine."

**Sequencing rule:** §1-2 correctness + §4 rank IC come before any §3 factor work or §7 construction. Measure before you model.
