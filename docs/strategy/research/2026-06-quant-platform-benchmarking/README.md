# ASXOS Quant Platform Benchmarking & Signal Research Guide

*Created: 2026-06-16 · Branch: `claude/quant-platform-benchmarking-guide` · Status: research/documentation only (no production change)*

This guide answers one question honestly: **is the ASXOS signal useful, or close to a coin flip — and what does it take to make it a serious, lean, solo-operator quant intelligence platform?**

It is deliberately structured to separate four very different kinds of claim. Do not blur them:

1. **Verified ASXOS facts** — read from the repo at `origin/main` HEAD `a719b3c`, with `file:line` evidence. These are true of the code as it stands.
2. **Public quant/investment theory** — canonical academic and institutional concepts, cited in `bibliography.md`.
3. **Inferred institutional best practice** — what serious systematic platforms *publicly* do. Not claims about any private firm's internals.
4. **Speculative / future ideas and near-term roadmap** — opinions and recommendations, clearly marked.

## Reading order

| File | Contents |
|---|---|
| `01-current-asxos-data-to-signal.md` | Verified system map + plain-English signal explanation + classification |
| `02-public-quant-frameworks.md` | Factor investing, anomaly caution, portfolio theory, quant process, ML-for-finance, platform practice |
| `03-asxos-vs-institutional-standard.md` | Gap-analysis table + what a top-tier team demands + lean solo translation |
| `04-math-and-investment-theory.md` | Returns, ranking, factors, predictive metrics, portfolio metrics, robustness, construction, monitoring |
| `05-platform-engineering.md` | Data/feature contracts, registries, lineage, reproducibility, run types, research/prod split |
| `06-signal-correctness-risks.md` | The two high-priority risks + survivorship + outcomes, each classified CONFIRMED/LIKELY/etc. |
| `07-benchmark-ladder.md` | L0–L5 ladder with evidence, status, gaps, acceptance criteria |
| `08-research-program.md` | Phase 0–5 research program with first prompts |
| `09-roadmap-30-60-90.md` | Prioritised practical roadmap |
| `10-future-prompts.md` | Pasteable prompts A–L for follow-up work |
| `bibliography.md` | Source matrix with links, concept, ASXOS relevance, confidence |

## Executive summary

ASXOS runs a **real, live LightGBM classifier + regressor signal** (`model_a_v1_5`) over a 22-feature momentum / volatility / liquidity / trend / value blend, wired into a disciplined, hard-failing production pipeline that is now operationally GREEN with first-class data-completeness gating (`latest_complete_trading_day`, recency gate `a719b3c`). For a solo operator, that plumbing is genuinely strong and rare.

**But the signal is not yet a *validated* signal.** Its only evidence is a documented classifier ROC-AUC (0.7097) that is (a) not artefact- or test-backed in the repo, (b) produced without purge/embargo on a survivorship-biased universe, and (c) **never translated into the metrics that decide whether a signal makes money** — rank IC, quintile spreads, turnover, net-of-cost return. There is no baseline comparison, no calibration, no economic backtest, and the table that records realised outcomes (`signal_outcomes`) is written and never read.

**Two correctness risks dominate and must be resolved before any optimisation:**
1. **`expected_return` units (LIKELY mis-specified, HIGH severity):** the regressor target is trained in **basis points** (`forward_return × 10_000`, `train.py:134`) but `expected_return` is returned unscaled (`model_a.py:43`) and compared to **fractional** thresholds (`> 0.05`). If the live artefact follows this path, the magnitude arm of every label collapses to a sign check.
2. **Raw `close` vs `adj_close` (CONFIRMED, MED–HIGH):** features *and* target use raw `close` (`loader.py:119,134`); `adj_close` exists in-schema but is unused → corporate-action noise.

**Classification: ML-assisted ranking signal with unverified alpha.** Not a coin flip statistically (AUC ≈ 0.71 implies discrimination), but economically unproven and possibly mis-specified at the label layer.

**Single best next action:** verify the two correctness risks (read-only), then build a *baseline + rank-IC + quintile* evaluation harness and read back `signal_outcomes`. Do **not** add model complexity, new features, or new signal families until the signal is shown to beat 12-1 momentum and equal-weight net of costs, out-of-sample.

## Self-critique / red-team of this guide (Phase 14)

- **Did we overstate ASXOS capability?** Risk present — the pipeline is strong, but "live ML model" must not be heard as "working alpha." Stated repeatedly that alpha is unverified.
- **Did we understate the correctness risks?** No — they are placed first and gate the roadmap.
- **Did we benchmark too aggressively vs institutions?** Mitigated by the explicit *lean solo translation* (§03): ASXOS does **not** need Barra/optimizer infrastructure now; it needs evaluation.
- **Too much complexity too early?** Guarded by the Do-Not-Build-Yet list and a roadmap that puts correctness + evaluation before any modelling.
- **ASX-specific constraints ignored?** Addressed: thin small-cap liquidity, frequent corporate actions, tight Materials/Financials beta-clustering, CGT 12-month rule, single-user capacity (capacity is a non-issue; liquidity and corporate actions are the binding ASX constraints).
- **Predictive quality vs portfolio usefulness conflated?** Explicitly separated (a high-AUC model can still be useless after costs/turnover).
- **Research vs production signal separated?** Yes — the benchmark ladder (L2 research-grade vs L4 portfolio-useful vs L5 production-governed) encodes the distinction.
- **Single best next action:** `expected_return` units verification — cheapest, highest-information, unblocks everything downstream.
