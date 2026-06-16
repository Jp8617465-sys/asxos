# 02 — Public Quant / Investment Frameworks (what matters)

*Category-2 (public theory) and category-3 (inferred institutional practice). All references in `bibliography.md`. These are publicly documented concepts — not claims about any private firm.*

## 1. Factor investing foundations

- **CAPM (Sharpe 1964):** one priced factor — market beta. Excess return is compensation for systematic risk. *ASXOS use:* none explicit; beta is neither a feature nor a control.
- **Fama-French 3-factor (1993) / 5-factor (2015):** add **size (SMB)**, **value (HML)**, then **profitability (RMW)** and **investment (CMA)**. *ASXOS use:* `pe_ratio`/`pb_ratio` proxy value; `market_cap` proxies size; `eps` touches quality. Implicitly multi-factor, never residualised against FF.
- **Carhart (1997) + Jegadeesh-Titman (1993):** **momentum (UMD)** — past 3-12m winners keep winning over 3-12m, then partially reverse. *ASXOS use:* `mom_1/3/6/12_1` are textbook momentum; `mom_12_1` is the classic skip-month construction. Carhart's survivorship-bias-free sample is itself a lesson ASXOS hasn't applied.
- **Quality / low-vol:** Asness-Frazzini-Pedersen **QMJ** (safe, profitable, growing, well-managed); Frazzini-Pedersen **betting-against-beta**. *ASXOS use:* partial (EPS, vol features) but not formalised.
- **Value × momentum interaction (Asness-Moskowitz-Pedersen 2013):** value and momentum are individually rewarded and **negatively correlated**, so the *combination* diversifies. *ASXOS use:* both styles are in the feature set; the model can learn the interaction, but it is never measured.

## 2. Market-anomaly caution (the part hobbyists skip)

- **Factor zoo & multiple testing (Harvey-Liu-Zhu 2016):** with hundreds of published factors, the conventional t > 2.0 is far too lax; a *new* factor needs **t > 3.0**, and a large fraction of published findings are likely false positives.
- **Replication crisis (Hou-Xue-Zhang):** ~64% of 447 anomalies become insignificant once microcaps are controlled (NYSE breakpoints) and returns are value-weighted. **Most paper anomalies are micro-cap, illiquid artefacts.**
- **Out-of-sample / post-publication decay:** documented anomalies tend to weaken after discovery (arbitrage, crowding).
- **Transaction costs & small/illiquid bias:** spreads, impact, and ASX small-cap illiquidity can erase a paper spread entirely. *ASXOS implication:* a high in-sample AUC means little; ASXOS must value-weight or liquidity-filter, beat momentum **net of costs**, and treat any "new edge" with the t > 3 bar.

## 3. Portfolio theory

- **Mean-variance (Markowitz 1952):** trade expected return against variance; **covariance** matters as much as means. ASXOS sizes by inverse-vol only — it ignores cross-asset covariance (the documented ASX Materials/Financials beta-clustering risk).
- **Sharpe / Information Ratio / Tracking Error:** Sharpe = excess return / total vol; **IR = active return / tracking error** is the right scorecard for an active signal vs a benchmark (AXJO).
- **Risk contribution / risk budgeting / active risk:** allocate *risk*, not dollars; know each position's marginal contribution to portfolio variance.
- **Capacity / liquidity:** how much capital before impact erodes alpha. For a **solo operator this is a non-issue on capital but a real issue on small-cap tradeability** — the binding ASX constraint.

## 4. Quant process (the assembly line)

Hypothesis → clean **point-in-time** data → feature engineering → **walk-forward** validation → **paper trading** → production with **monitoring + explicit kill criteria**. ASXOS has the production end (jobs, gates, monitoring) but is missing the **validation and paper-trading middle** — the part that establishes whether anything works.

## 5. ML for finance (López de Prado, AFML)

- **Leakage** is the dominant failure mode; **purging** (drop train rows whose label window overlaps test) + **embargo** (gap ≥ horizon) are mandatory. ASXOS's 5-fold split has neither, and its 5-day horizon overlaps fold boundaries.
- **Calibration** (does prob 0.6 mean 60%?) — ASXOS uses raw `predict_proba`, uncalibrated.
- **Label design:** fixed-time-horizon labels (ASXOS's 5-day) are the simplest; triple-barrier / meta-labeling are more robust alternatives (later, not now).
- **Expected-return vs classification; ranking vs prediction:** for portfolios, *rank* quality (IC) usually matters more than point-prediction accuracy (RMSE). ASXOS optimises a classifier+regressor but measures neither rank quality nor calibration.
- **When ML beats simple factors:** only when it captures non-linear interactions *out-of-sample, net of costs, beyond the linear factor baselines*. That is precisely the untested claim.
- **Overfitting control:** **Deflated Sharpe Ratio** and **Probability of Backtest Overfitting** correct for the number of trials. Honour t > 3 for new claims.

## 6. Platform practice (publicly documented institutional norms)

Serious systematic platforms separate **research from production**; maintain a **model registry** (versioned artefacts + metrics + lineage), a **feature store / feature contracts**, **experiment tracking**, an explicit **risk model** (Barra/MSCI-style factor covariance) feeding an **optimizer**, a curated **signal library**, **data lineage**, **incident monitoring**, and **governance gates** for promotion/demotion. ASXOS already has primitive versions of several (`model_versions`, `job_runs`, `JobMonitor`, validation gates). The gaps are **evaluation, outcome lineage, calibration, and a risk model** — see `05-platform-engineering.md`.

## 7. ASX-specific constraints (often missed)

- **Frequent, material corporate actions** (rights issues, special dividends, bonus issues) → **adjusted prices are essential**; raw close injects spurious returns.
- **Thin small-cap liquidity** → spreads/impact dominate; value-weight or liquidity-filter or the backtest lies.
- **Tight index concentration** → Materials + Financials are a large share of the ASX 200 and co-move; sector/beta clustering breaks naive diversification.
- **CGT 12-month rule** → tax-aware overlay genuinely changes optimal holding/disposal (ASXOS already encodes the 12-month boundary defer).
- **Capacity is not the constraint** for a solo operator; **tradeable liquidity and after-tax return are.**
