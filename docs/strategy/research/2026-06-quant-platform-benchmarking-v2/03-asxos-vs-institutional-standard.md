# 03 — ASXOS vs Institutional Standard (2021–2026 practice)

*"Standard" column = publicly documented 2021–2026 practice, not private firm internals.*

## 1. Gap-analysis table

| Dimension | ASXOS current | 2021–2026 standard | Gap | Risk if ignored | Near-term fix | Later fix | Metric to prove improvement |
|---|---|---|---|---|---|---|---|
| Data completeness | complete-day + recency gates | completeness SLAs + vendor cross-check | Low | stale signals | maintain | trading-day calendar | gate fires on residue/stale |
| Adjusted prices | **raw `close`** | adjusted/total-return series | **High** | spurious ASX ex-date returns | adopt `adj_close` | franking-adjusted TR | ex-date artefacts removed |
| Point-in-time data | fundamentals 45-day lag ✓ | strict PIT + leakage audit (Kapoor-Narayanan taxonomy) | Med | temporal leakage | PIT universe | feature leakage test | leakage checklist passes |
| Universe construction | `is_active` on history | as-of membership + delisting returns | **High** | survivorship inflation | `universe_history` | delist returns | backtest incl. delisted |
| Corporate actions | none explicit | full CA handling | **High** | momentum noise | `adj_close` | CA event table | CA-day artefacts gone |
| Feature library | 22, ad hoc | versioned contract + store | Med | reproducibility | contract pinned to artefact | feature store (lean) | parity test |
| Factor baselines | **none** | benchmark vs Open-Source Asset Pricing library | **High** | can't separate skill from noise | OSAP baselines | factor attribution | signal beats baselines on rank IC |
| ML model | LightGBM clf+reg | **trees confirmed best on tabular** | Low | — | keep | regularized challenger | challenger comparison |
| Target/label | 5-day fwd return | research-justified; triple-barrier/meta-label as upgrade | Med | arbitrary horizon | document horizon | meta-labeling | horizon sensitivity |
| `expected_return` units | **bps vs fraction mismatch** | consistent units | **Critical** | degenerate labels | verify+align | unit test | distribution sanity |
| Calibration | **none** | post-hoc isotonic/Platt + reliability/Brier | **High** | thresholds meaningless | calibration audit | recalibrate | Brier ↓, reliability flat |
| Backtesting | 5-fold, **no purge** | **CPCV + purge/embargo** | **High** | overfit/leakage (worst-in-class) | purge+embargo | CPCV (≥100 paths) | PBO < ~0.2–0.5 |
| Rank IC | **not measured** | core metric (mean, ICIR) | **Critical** | no skill measure | implement rank IC | rolling IC monitor | IC mean + t-stat |
| Quintile/decile spreads | **not measured** | standard diagnostic | **High** | no monotonicity check | implement | net-of-cost spread | monotone, positive net |
| Transaction costs | **none** | proportional cost model | **High** | paper alpha ≠ real | bps cost constant | impact model | net-of-cost IR |
| Turnover | **not measured** | tracked; L1 penalty | **High** | hidden cost | measure | turnover penalty (=regularization) | turnover budget met |
| Liquidity/capacity | filter only | ADV cap (capacity N/A solo) | Med | untradeable spreads | ADV position cap | — | trades within ADV cap |
| Sector/size neutrality | none | residualize/neutralize | Med | unintended bets | sector-relative features | beta/sector caps | exposure within bands |
| Risk model | inverse-vol only | **denoised covariance + HRP/Schur (skfolio)** | **High** | uncontrolled co-movement | shrinkage/RMT denoise | statistical factor model | ex-ante TE estimate |
| Portfolio optimizer | inverse-vol + caps | HRP/Schur (γ dial) | Med | fragile sizing | skfolio HRP | constrained Schur | risk-adjusted ↑ |
| Paper trading | "not a backtester" | shadow book + uncertainty-gated deploy | **High** | no live proof | decision ledger | attribution | shadow IR vs AXJO |
| Attribution | none | factor/selection attribution | Med | can't explain P&L | basic | Brinson/factor | alpha vs beta split |
| Monitoring | job_runs/deadman | + drift (Evidently) + rolling IC | Med | silent decay | read `signal_outcomes` | drift alarms | rolling IC tracked |
| Model registry | `model_versions`+metrics.json | MLflow + lineage hash | Low | — | +data-window hash+git SHA | MLflow local | lineage recorded |
| Feature registry | constant list | versioned store / shared module | Med | train/serve skew | contract doc | feast (optional) | parity test |
| Experiment tracking | none | MLflow tracking | Med | lost experiments | MLflow local | — | runs logged |
| Governance | gates + **ungated activate** | gated promotion + kill + re-validate | Med | ungated activation | re-validate on activate | IC/cost gate + kill rules | promotion gated |
| Brief/output eval | none | output QA + uncertainty display | **High** | over-confident UI | prob_up+caveat | realised-accuracy footnote | caveat shipped |
| Human approval gates | personal-use firewall ✓ | sign-off boundaries | Low | — | keep | decision ledger | — |

## 2. What a top-tier team demands → lean solo translation (Phase 11)

| Institutional demand (2021–2026) | Lean ASXOS version |
|---|---|
| Clean adjusted/total-return data | use existing `adj_close`; later franking-adjusted TR |
| Strict PIT + leakage audit | keep PIT; add purge/embargo + a feature-leakage test (Kapoor-Narayanan checklist) |
| Survivorship controls | `universe_history` or retain delisted rows + as-of join |
| Factor baselines | **Chen-Zimmermann Open Source Asset Pricing** library + 12-1 momentum |
| Cost model | one proportional bps constant + ADV-scaled term |
| Risk model | RMT/Ledoit-Wolf **denoised covariance** (not full Barra) |
| Backtest with walk-forward | **purge+embargo → CPCV** via reused `walk_forward_split`; **Deflated Sharpe + PBO** |
| Independent validation | Opus red-team (Prompt J) + uncertainty-gated deploy |
| Production monitoring | read `signal_outcomes` → rolling rank IC + **Evidently** drift |
| Model registry | `model_versions`+metrics.json + **MLflow local** + data-window hash |
| Promotion gates | add **IC/net-of-cost** gate to `validation.py`; kill rule; re-validate on `model activate` |
| Clear objective | one-page: "max after-cost, after-tax IR vs AXJO at ≤ X% turnover" |
| No unsupported claims | brief caveats + `prob_up`/`confidence` + realised-accuracy footnote |
| Allocator | **HRP/Schur via `skfolio`** + L1 turnover penalty (keep CGT overlay) |

**Skip the institutional kit:** fundamental factor risk models (Barra), market-impact optimizers, ML covariance (ResNet), Tecton/Kubeflow, beta-cap. Over-engineering for a solo operator. **Match the discipline, not the infrastructure.**
