# 02 — Modern Public Quant Frameworks (2021–2026)

*Category-2/3. Every claim maps to a 2021–2026 source in `bibliography.md`. Foundational works appear only as anchors. Access caveat: figures marked **[verify]** are corroborated via search, not full-text.*

## 1. Factor investing & the replication debate — what changed

The pre-2021 mood was pessimistic: a 300+ "factor zoo," Harvey-Liu-Zhu's call for **t>3.0**, and Hou-Xue-Zhang's finding that **~65% of 452 anomalies fail t>1.96** once microcaps are value-weighted away. **2021–2026 partially reversed this, with sharper hygiene:**

- **Replication is a methodology debate now, not an existence debate.** Jensen-Kelly-Pedersen (*JF* 2023) report **~82% of 153 factors replicate** [verify] using a Bayesian hierarchical model, arguing correlated factors *borrow* statistical strength. Chen-Zimmermann's Open Source Asset Pricing independently replicates ~98% of clearly-significant predictors (publication-bias-adjusted returns only ~12% lower) — and ships a **free factor library** ASXOS can baseline against.
- **The t>3 bar lost.** Chen (*Mgmt Sci* 2023; WP 2022) shows it rests on weakly-identified extrapolation; directly estimable **FDR bounds put false-discovery ≤ ~9–25%** [verify]. **Modern standard = FDR control / empirical-Bayes shrinkage, not a blanket t-cutoff.**
- **Net-of-cost realism is mandatory.** Detzel-Novy-Marx-Velikov (*JF* 2023): models ignoring transaction costs don't span the achievable frontier; Novy-Marx-Velikov's "Assaying Anomalies" makes NYSE-breakpoint, value-weighted, net-of-cost testing the default.
- **Factor momentum / crowding:** Ehsani-Linnainmaa (*JF* 2022) — factors are autocorrelated and "momentum" is largely factor-timing. Crowding research (2025) finds mechanical factors (momentum/reversal) crowd and decay hyperbolically post-2015; judgment factors (value/quality) less so. Treat crowding/valuation-spread as *risk overlays, not alpha* (Asness on the difficulty of factor timing).
- **Value:** the 2018–2020 drawdown was a valuation-spread collapse, not a fundamentals breakdown; value resurged 2022–2024. Premium intact but regime/spread-conditional.

## 2. ML for return prediction — the modern consensus

- **Trees win on tabular equity data.** 2021–2026 comparisons show gradient-boosted trees (LightGBM/XGBoost) match or beat deep nets and transformers OOS at a fraction of the cost — **ASXOS's LightGBM is the right tool, not a compromise.** (Gu-Kelly-Xiu 2020 is the anchor; deep learning wins mainly via latent-factor/autoencoder structure.)
- **But the *net* edge is narrow.** Avramov-Cheng-Metzker (*Mgmt Sci* 2023): ML predictability concentrates in microcaps/distressed/high-vol; exclude those + add costs and the high-turnover ML book bleeds out. Counter-evidence (AFA "Expected Returns of ML Strategies") shows net ~1.4%/mo can survive *with* large-cap focus and turnover control. **Synthesis: ML's net edge is real but lives in the long-short, small/illiquid, high-turnover corner — a long-only large-cap weekly ASX book captures a fraction.**
- **Regularization is mandatory.** Kelly-Malamud-Zhou "Virtue of Complexity" (*JF* 2024): complex models beat simple ones **only with ridge shrinkage**.
- **Ranking > point prediction.** For portfolios, optimize/evaluate **rank-IC** (LambdaRankIC 2026), not raw error. Calibrate `prob_up` post-hoc (isotonic/Platt) before it drives decisions.
- **LLM/agentic signals: research-grade only.** ChatGPT news-sentiment predicts returns (Lopez-Lira-Tang 2023) but **decays with adoption** and is riddled with look-ahead/memorization leakage (Look-Ahead-Bench 2026). Don't build your own FinLLM (BloombergGPT cost ~$3M, underwhelmed); FinGPT shows the cheap path *if* ASXOS ever adds sentiment — which it should not until the price signal is validated.

## 3. Validation — what good looks like in 2026

- A backtest should yield a **distribution** of OOS outcomes, not a point estimate. **Combinatorial Purged Cross-Validation (CPCV)** dominates walk-forward/K-fold on Probability-of-Backtest-Overfitting (PBO) and Deflated Sharpe (Arian-Norouzi-Seco 2024); **plain walk-forward is the weakest** false-discovery control.
- **Purge + embargo** are non-negotiable: with a 5-day label you must purge ≥5 days around each train/test boundary and embargo ~1–2% of the series. ASXOS's no-purge 5-day-overlap split is a textbook temporal-leakage pattern (Kapoor-Narayanan, *Patterns* 2023).
- **Deflate the Sharpe** for the trial count (every model/feature/threshold variant is a trial); apply FDR/haircut corrections (Harvey-Liu 2021). **Evaluate by rank-IC, ICIR, and decile long-short spread, net of a cost+turnover model.**

## 4. Portfolio construction — estimation error is the enemy

- **Denoise the covariance before any optimizer** (RMT/Marchenko-Pastur, Ledoit-Wolf nonlinear shrinkage, detoning). This buys most of the OOS stability.
- **Hierarchical methods unified with optimization:** Cotton's **Schur Complementary Allocation** (2024) interpolates HRP↔min-variance via one parameter; Antonov-Lipton-López de Prado (2024) prove HRP is less noise-sensitive than Markowitz; all packaged in **`skfolio`** (2025, sklearn API). ASXOS's covariance-free inverse-vol is the *most fragile* choice.
- **A turnover (L1) penalty is regularization** — it caps trading cost *and* stabilizes weights.
- **Tax-aware optimization** (AQR/Vanguard/Goldman 2024) — defer gains, harvest losses, prefer long-term treatment — is exactly ASXOS's CGT overlay; ASXOS is directionally state-of-the-art here (no academic source covers Australian *franking*, so the spec-driven approach is appropriate).

## 5. Platform practice — lean MLOps

Modern lesson: **discipline beats tooling.** Feature stores (Feast) solve train/serve skew + point-in-time correctness — the lean equivalent is a **single shared feature module** + `as_of` SQL joins (which ASXOS already has). Add **MLflow** (local) for experiment tracking + registry, **Evidently** for drift, **lineage as a column** (data-window hash in `model_versions`), and **CI metric gates** for promotion. Skip Tecton/Databricks Feature Store/Kubeflow/full-W&B. (See `05`.)

## 6. ASX-specific constraints (now evidenced, 2021–2026)

- **`adj_close` is essential:** frequent fully-franked ex-dates, rights/bonus issues, consolidations manufacture spurious 1–5 day returns into a 5-day model. **#1 ASX fix.**
- **No Australian small-cap premium:** S&P/ASX Small Ordinaries has *lagged* the ASX 100 since ~2000. A structural small-cap tilt is **uncompensated illiquidity**, not a harvested anomaly — liquidity/spread-filter the ~1,800-name universe.
- **Franking:** imputation grosses high-yield names up ~40%+ [verify] on income price data never sees; treat as part of expected return (S&P publishes franking-adjusted total-return indices).
- **Concentration:** Financials ~28–30% + Materials ~20% [verify] of the ASX 200, in tight macro blocs — GICS caps under-protect (consistent with ASXOS's own documented v1 risk-blindness).
- **Settlement risk:** ASX is T+2; CHESS replacement (TCS BaNCS, Release 1 ~2026) gates T+1 (~2030); the Dec-2024 CHESS batch-settlement failure (RBA) is a live operational hazard → justifies the existing kill-switch/deadman discipline.
