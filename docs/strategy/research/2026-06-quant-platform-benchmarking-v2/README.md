# ASXOS Quant Platform Benchmarking & Signal Research Guide — v2 (modern sources, 2021–2026)

*Created 2026-06-16 · Branch `claude/quant-platform-benchmarking-guide` · Research/documentation only (no production change).*

This is a **re-run of the v1 guide with the source base restricted to ~2021–2026.** v1 (sibling folder `2026-06-quant-platform-benchmarking/`) leaned on foundational works (Markowitz 1952 → Harvey-Liu-Zhu 2016). v2 keeps the verified ASXOS facts but **rebuilds the theory, benchmarks, recommendations, and bibliography on the last five years of research** — because the field has moved materially since the classics (the replication debate reversed, the t>3 bar lost, CPCV replaced walk-forward, denoised-HRP replaced naive optimization, and ML's *net* edge was sharply re-bounded).

Four claim categories are kept separate throughout: **(1) verified ASXOS facts** (repo `file:line` @ `a719b3c`), **(2) recent public theory** (cited, `bibliography.md`), **(3) inferred institutional practice** (public, not private internals), **(4) speculative/roadmap**.

## Source-access honesty note
Most primary PDFs (Wiley/JF, INFORMS, ScienceDirect, NBER, arXiv mirrors, vendor PDFs) returned **HTTP 403** to automated fetch. Their findings are corroborated **across multiple independent search results**, not read line-by-line. Such items are flagged **"not accessed (corroborated via search)"** in `bibliography.md`, and the load-bearing numbers (e.g. JKP 82% replication, Chen FDR 9–25%, Avramov microcap concentration, ASX sector weights, "no Australian small-cap premium", franking ~40% gross-up) are marked **verify-before-quoting**. Per the research standard, nothing is asserted from a source that was neither accessed nor cross-corroborated. **Prose-caveat policy (added after red-team):** where these figures appear declaratively in the prose of this guide for readability, treat them as *claims pending primary-source confirmation, not established facts* — several rest on a single corroborating source. The independent red-team review and the resulting scope corrections are recorded in `11-redteam-and-revisions.md`.

## Reading order
| File | Contents |
|---|---|
| `01-current-asxos-data-to-signal.md` | Verified system map + plain-English explanation + classification (carried from v1; code unchanged) |
| `02-public-quant-frameworks.md` | **Modern (2021–2026)** factor/anomaly, ML-for-finance, validation, portfolio, platform consensus |
| `03-asxos-vs-institutional-standard.md` | Gap table (standard column = 2021–2026 practice) + lean solo translation |
| `04-math-and-investment-theory.md` | Returns, ranking, **rank-IC/FDR/CPCV/denoising/calibration** |
| `05-platform-engineering.md` | **Lean MLOps 2021–2026**: shared feature module, MLflow, Evidently, lineage-as-column |
| `06-signal-correctness-risks.md` | The two correctness risks + survivorship + outcomes, classified, with modern ASX evidence |
| `07-benchmark-ladder.md` | L0–L5 with **modern acceptance criteria** (DSR, PBO, rank-IC, net-of-cost) |
| `08-research-program.md` | Phase 0–5 program using Open-Source Asset Pricing baselines, CPCV, skfolio |
| `09-roadmap-30-60-90.md` | Prioritised roadmap |
| `10-future-prompts.md` | Pasteable prompts A–L (modernised) |
| `bibliography.md` | 2021–2026 source matrix, accessed/recommended flags, verify-before-quoting markers |

## Executive summary (what the modern literature changes)

The **verdict on ASXOS is unchanged**, but the modern evidence makes it sharper and, in places, more urgent:

1. **LightGBM is the *right* model** — 2021–2026 comparative work shows tree ensembles beat deep nets and transformers on tabular cross-sectional equity data, OOS, cheaply. No architecture change needed.
2. **But ML's *net* edge is narrow and conditional.** Avramov-Cheng-Metzker (Mgmt Sci 2023) show ML return-predictability concentrates in microcaps/distressed/high-volatility names and **bleeds out after costs and economic restrictions**; net edge survives only with large-cap focus, turnover control, **shrinkage** (Kelly-Malamud-Zhou "Virtue of Complexity," JF 2024), **calibration**, and **rank-IC evaluation against an explicit baseline.** ASXOS currently has none of those four.
3. **The validation is worst-in-class by the 2026 bar.** Arian-Norouzi-Seco (2024) show plain walk-forward / TimeSeriesSplit is the weakest false-discovery control; ASXOS's 5-day-overlap, no-purge split is a textbook temporal-leakage pattern (Kapoor-Narayanan, *Patterns* 2023). Fix = purge+embargo → CPCV, Deflated Sharpe, PBO.
4. **The t>3 bar lost; use FDR / empirical-Bayes shrinkage.** The replication debate is live (Jensen-Kelly-Pedersen ~82% replicate vs Hou-Xue-Zhang ~65% fail), and Chen (2022/2023) shows the t>3 call was weakly identified — modern practice is FDR control + shrinkage, and a **free baseline factor library exists** (Chen-Zimmermann Open Source Asset Pricing).
5. **Portfolio: denoise then HRP/Schur.** Modern construction (Cotton's Schur Complementary Allocation 2024; `skfolio` 2025; RMT/Ledoit-Wolf denoising) says ASXOS's covariance-free inverse-vol is the *most fragile* choice; the lean upgrade is denoise → HRP/Schur + an L1 turnover penalty (which is itself regularization).
6. **ASX-specific, now evidenced:** **`adj_close` is the single highest-value fix** (franked ex-dates/rights/splits manufacture spurious 5-day returns); **there is no Australian small-cap premium** (Small Ords has lagged ASX 100 since ~2000 — a structural small-cap tilt is uncompensated illiquidity); **franking** grosses high-yield names up ~40%+ on income price data never sees; **index concentration** (Financials ~28–30% + Materials ~20%) breaks naive diversification; **CHESS/T+1 instability** (Dec-2024 batch-settlement failure) is a live operational hazard.

**Classification (unchanged): ML-assisted ranking signal with unverified alpha.** Not a coin flip; economically unproven; possibly mis-specified at the label layer.

**Single best next action (unchanged, reinforced):** verify `expected_return` units + adopt `adj_close`, then build a **baseline (Open-Source Asset Pricing) + rank-IC + decile-spread, net-of-cost, purged** evaluation harness before any modelling.

## Self-red-team (Phase 14)
- *Overstated capability?* No — "live ML" is repeatedly distinguished from "working alpha"; modern evidence (Avramov) tightens the caution.
- *Understated risks?* No — risks lead the roadmap; the bps-units risk is the top item.
- *Benchmarked too hard vs institutions?* Guarded by the lean-solo translation and "skip the institutional kit" guidance (no Barra, no optimizer-overkill, no feature store).
- *Too much complexity too early?* The roadmap is correctness → baselines → evaluation **before** any modelling; CPCV/HRP are explicitly *later* upgrades after purge+embargo and denoising.
- *ASX constraints?* Now first-class and evidenced (no size premium, franking, concentration, settlement risk, adj_close).
- *Predictive vs portfolio usefulness?* Separated via the ladder (L2/L3 research-grade vs L4 portfolio-useful).
- *Single best next action?* `expected_return` units verification + `adj_close` adoption.
