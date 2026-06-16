# 04 — Mathematics & Investment Theory (modern framing)

*Each concept: meaning · why it matters (2021–2026) · ASXOS today · first practical step. Priorities: **[P0]** correctness, **[P1]** evaluation, **[P2]** construction/monitoring.*

## 1. Return definitions
Arithmetic vs log; **adjusted/total-return**; excess (over AXJO/RFR); forward; horizon. *ASXOS:* arithmetic 5-day on **raw** close. *First [P0]:* compute on `adj_close`; treat **franking** as part of total return for ASX (S&P franking-adjusted TR convention); justify the 5-day horizon vs weekly cadence.

## 2. Cross-sectional ranking
Ranks, z-scores, **winsorization**, robust scaling, **sector neutralization**. Modern ranking-loss work (LambdaRankIC 2026) shows optimizing the *ordering* beats point error at low signal-to-noise. *ASXOS:* z-scores only in allocator; no winsorization. *First [P1]:* per-date winsorize + z-score features; sector-relative momentum.

## 3. Factor models
Market/size/value/quality/investment/momentum/low-vol; **residualization** isolates incremental alpha. Modern caution: no Australian size premium (residualize against it, don't bet on it). *ASXOS:* feature proxies, never residualized. *First [P1]:* regress signal returns on an Open-Source-Asset-Pricing factor set to test for *incremental* alpha.

## 4. Predictive metrics (the missing core)
- **Rank IC** (Spearman of prediction vs forward return) + **ICIR** — the 2021–2026 standard, tied to Grinold's IR≈IC√Breadth. *ASXOS:* **not computed.** *First [P1]:* daily rank IC of `prob_up`/`expected_return`; mean, t-stat, ICIR.
- **Decile long-short spread**, monotonicity, hit rate; AUC is *insufficient* (measures discrimination, not economic value).
- **Calibration / Brier; post-hoc isotonic/Platt.** *ASXOS:* uncalibrated. *First [P1]:* reliability diagram + Brier on a time-ordered held-out fold; calibrate `prob_up` before sizing.
- **RMSE/MAE for `expected_return`** — only meaningful after the units fix (`06`).

## 5. Portfolio metrics
Sharpe, **Information Ratio**, tracking error, drawdown, **turnover**, active share, risk contribution. *ASXOS:* none computed for the signal. *First [P1]:* IR + turnover of a top-decile book vs AXJO; *then [P2]* drawdown, risk contribution.

## 6. Statistical robustness (biggest modern shift)
- **Walk-forward → purge+embargo → CPCV.** Plain walk-forward is worst-in-class (Arian-Norouzi-Seco 2024); ASXOS's no-purge 5-day-overlap split leaks (Kapoor-Narayanan 2023). *First [P1]:* purge ≥5 days + embargo ~1–2%; graduate to CPCV (≥100 paths).
- **Multiple testing: FDR / empirical-Bayes, NOT t>3.** Chen (2022/2023): the t>3 bar is weakly identified; control FDR, shrink estimates. *First [P1]:* log a trial counter; shrink `expected_return` toward the cross-sectional mean.
- **Deflated Sharpe Ratio + Probability of Backtest Overfitting** (Bailey-López de Prado): correct for trials/skew/kurtosis; CSCV-based PBO is cheap even solo. *First [P1]:* report DSR not raw Sharpe; reject configs with PBO > ~0.2–0.5.

## 7. Portfolio construction (modern)
- **Denoise covariance first** (RMT/Marchenko-Pastur, Ledoit-Wolf, detone) — captures most OOS stability. *ASXOS:* inverse-vol, no covariance. *First [P2]:* shrinkage/denoised covariance.
- **HRP / Schur Complementary Allocation** (Cotton 2024, `skfolio` 2025): robust on ill-conditioned matrices; γ dial from HRP→min-variance. *First [P2]:* HRP/Schur via `skfolio`, keeping sector/cash caps.
- **Turnover (L1) penalty = regularization** + min-trade threshold. **Tax-aware overlay** (keep CGT 12-month defer + loss-harvest tag).

## 8. Production monitoring
Data/feature/prediction/**calibration** drift; realised-outcome tracking; signal decay; **kill criteria**. *ASXOS:* job liveness only; `signal_outcomes` unread. *First [P1]:* read `signal_outcomes` → rolling rank IC; *[P2]* Evidently drift (PSI/KS); kill rule ("rolling 3-mo IC < 0.01 for 2 months → quarantine").

**Sequencing rule (reinforced by modern evidence):** correctness (§1) + rank-IC/baselines (§4, §6) **before** any factor work (§3) or construction (§7). Measure — net of costs, purged, deflated — before you model.
