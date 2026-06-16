# 02 — Quant Guide v2 Synthesis (next-decision claims only)

*Category-3. Full guide: branch `claude/quant-platform-benchmarking-guide`, `docs/strategy/research/2026-06-quant-platform-benchmarking-v2/`. Source caveats preserved.*

## What the guide says the signal is
**ML-assisted ranking signal with unverified alpha.** Live pipeline: market/fundamental data → 22 engineered features (momentum/vol/liquidity/trend/value) → LightGBM classifier (`prob_up`, 5-day up-move) + regressor (`expected_return`) → static dual-threshold labels → `signals` table → brief + `build_portfolio`. Not a coin flip statistically; economically unproven.

## What the guide says is (and isn't) the problem
- **Model class is fine.** 2021–2026 evidence: tree ensembles (LightGBM) beat deep nets/transformers on tabular cross-sectional equity data. No architecture change needed.
- **The problems are correctness, baselines, validation, costs/turnover, calibration, governance** — not the model.

## P0 (the guide's top two) — now CONFIRMED in this pack (`04`)
1. `expected_return` units (train `×10_000` vs fractional thresholds).
2. raw `close` vs `adj_close`.

## P1 gaps (the guide's high-priority list)
No factor baseline suite; no rank IC / ICIR; no quintile/decile spreads; no net-of-cost evaluation; no turnover/cost model; no purge/embargo/CPCV; no Deflated Sharpe / PBO; no calibration; no `signal_outcomes` read-back; no paper portfolio; no durable `price_coverage` metadata.

## The guide's recommended order
1. Verify P0 (units, adj_close). → **done; both CONFIRMED.**
2. Build baselines + rank-IC + quintile/decile (net-of-cost), benchmarked vs **Chen-Zimmermann Open Source Asset Pricing** + 12-1 momentum.
3. Then backtest (purge/embargo → CPCV, Deflated Sharpe, PBO) → paper portfolio → governance.

## Do-not-build-yet (the guide is explicit)
Do not optimize thresholds, retrain models, add new signals, or treat labels as portfolio-ready until correctness + evidence improve. Defer CPCV/Schur-HRP/MLflow/Evidently behind the L2 rank-IC verdict (the v2 red-team revision).

## Modern-literature conclusions (with caveats preserved)
- ML net edge is **narrow and conditional** (Avramov-Cheng-Metzker 2023) — concentrates in microcaps/high-turnover; a long-only large-cap weekly ASX book may capture near-zero. `[verify]`
- Validation must be stricter than plain walk-forward (CPCV > walk-forward; Arian-Norouzi-Seco 2024).
- Multiple-testing matters; **t>3 superseded by FDR/empirical-Bayes** (Chen 2022/2023). `[verify]`
- ASX specifics: **adjusted prices matter** (now empirically confirmed, `04`); **assume no Australian small-cap premium** `[verify]`; sector concentration matters; franking is real total-return not in price-only data; liquidity/capacity is the binding constraint.

## Source-integrity caveat
Several guide figures (no-AU-size-premium, sector weights, franking gross-up, JKP 82%, Chen FDR, Avramov microcap concentration) were corroborated via search, **not read from primary PDFs** → treat as **claims pending confirmation**, not facts. The guide's `11-redteam-and-revisions.md` overrides parts of its own roadmap (defers machinery behind the L2 verdict).

## Net effect on ASXOS's plan
The guide's "verify P0 first" is vindicated — and this pack shows **both P0 risks are real**. Everything downstream (baselines, rank-IC, portfolio, metadata) is untrustworthy until the label semantics (`er` scale) and price basis (`adj_close`) are corrected.
