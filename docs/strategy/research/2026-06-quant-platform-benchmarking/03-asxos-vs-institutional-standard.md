# 03 — ASXOS vs Institutional Standard (gap analysis)

*Category-1 (ASXOS state) vs category-3 (publicly documented institutional norm). "Standard" = what serious systematic platforms publicly do, not any firm's internals.*

## 1. Gap-analysis table

| Dimension | ASXOS current | Institutional standard | Gap | Risk if ignored | Near-term fix | Later fix | Metric to prove improvement |
|---|---|---|---|---|---|---|---|
| Data completeness | complete-day + recency gates (`cf5d974`,`a719b3c`) | completeness SLAs + vendor cross-check | Low | stale signals | maintain | trading-day calendar | gate fires on residue/stale days |
| Adjusted prices | **raw `close`** (`loader.py:119`) | adjusted (splits/divs/rights) | **High** | spurious ex-date returns | use `adj_close` | total-return series | ex-date return spikes removed |
| Point-in-time data | fundamentals 45-day lag ✓; prices PIT ✓ | strict PIT everywhere | Med | label leakage | PIT universe | fundamental vintages | leakage test passes |
| Universe construction | `is_active` on history (`loader.py:132`) | universe-as-of snapshots | **High** | survivorship inflation (~2-5%/yr) | universe_history table | delisting returns | backtest incl. delisted names |
| Corporate actions | none explicit | full CA handling | **High** | momentum noise | `adj_close` covers most | CA event table | CA-day artefacts gone |
| Feature library | 22 features, ad hoc | versioned feature store + contracts | Med | reproducibility | feature contract doc | feature registry | contract pinned to artefact |
| Factor baselines | **none** | always benchmark vs FF/momentum | **High** | can't tell skill from noise | baseline suite | factor attribution | signal beats baselines on IC |
| ML model | LightGBM clf+reg | ensembles + linear challengers | Low | — | keep | linear challenger | challenger comparison |
| Target/label | 5-day fwd return | research-chosen horizon | Med | arbitrary horizon | document/justify | multi-horizon | horizon sensitivity analysis |
| `expected_return` units | **bps vs fraction mismatch** | consistent units | **Critical** | degenerate labels | verify + align | unit test | distribution sanity check |
| Calibration | **none** | reliability diagrams, isotonic/Platt | **High** | thresholds meaningless | calibration audit | recalibrate | Brier ↓, reliability flat |
| Backtesting | 5-fold, **no purge** | walk-forward + purge/embargo | **High** | overfit, leakage | purged WF | CPCV + DSR | leakage gap closed |
| Rank IC | **not measured** | core metric | **Critical** | no skill measure | implement IC | rolling IC monitor | IC mean + t-stat |
| Quintile spreads | **not measured** | core diagnostic | **High** | no monotonicity check | implement | decile + t-stats | monotone spread |
| Transaction costs | **none** | spread + impact modelled | **High** | paper alpha ≠ real | cost constant | impact model | net-of-cost IR |
| Turnover | **not measured** | always tracked | **High** | hidden cost | measure | turnover penalty | turnover budget met |
| Liquidity/capacity | filter only | ADV-based caps | Med | untradeable spreads | liquidity floor | capacity curve | spread within ADV cap |
| Sector/size neutrality | none | residualise / neutralise | Med | unintended bets | sector-relative features | Barra-style neutralisation | exposure within bands |
| Risk model | inverse-vol only | factor covariance | **High** | uncontrolled co-movement | shrinkage cov | factor risk model | ex-ante TE estimate |
| Portfolio optimizer | inverse-vol + caps | MVO / risk-parity | Med | suboptimal sizing | document | constrained MVO | risk-adjusted ↑ |
| Paper trading | "not a backtester" (`paper_trade.py`) | shadow book pre-live | **High** | no live proof | decision ledger | full attribution | shadow IR vs AXJO |
| Attribution | none | factor/selection attribution | Med | can't explain P&L | basic attribution | Brinson/factor | alpha vs beta split |
| Monitoring | job_runs/deadman | + drift + calibration dashboards | Med | silent decay | read `signal_outcomes` | drift alarms | rolling IC tracked |
| Model registry | `model_versions`+`metrics.json` | full registry + lineage | Low | — | + baseline metric + git SHA | challenger tracking | lineage recorded |
| Feature registry | constant list | versioned store | Med | train/serve skew | contract doc | feature store | parity test |
| Experiment tracking | none | MLflow-style | Med | lost experiments | lightweight table | experiment UI | experiments logged |
| Governance | gates + **manual ungated activate** | gated promotion + kill | Med | ungated activation | re-validate on activate | kill criteria | promotion gated |
| Brief/output eval | none | output QA | **High** | over-confident UI | add prob_up+caveat | realised-accuracy footnote | caveat shipped |
| Human approval gates | personal-use firewall ✓ | sign-off boundaries | Low | — | keep | decision ledger | — |

## 2. What a top-tier quant team would demand → lean ASXOS translation (Phase 11)

ASXOS does **not** need Renaissance/Two-Sigma/Citadel infrastructure. The lean solo-operator equivalents:

| Institutional demand | Lean ASXOS version |
|---|---|
| Clean adjusted data | use the existing `adj_close` column; fundamentals already 45-day-lagged |
| Point-in-time data | keep PIT prices/fundamentals; add universe-as-of |
| Survivorship controls | one `universe_history` table (or retain delisted rows `is_active=FALSE` and join as-of) |
| Factor baselines | a `research/baselines.py` computing 5-6 baselines from existing `prices` |
| Cost model | one per-trade bps constant + ADV-scaled impact term |
| Risk model | Ledoit-Wolf shrinkage covariance over the candidate set (weekly, Decimal/NumPy) |
| Walk-forward + purge | extend existing `walk_forward_split` with purge + embargo |
| Independent validation | the Opus red-team prompt (J) before any promotion |
| Production monitoring | read `signal_outcomes` into a rolling-IC line + a decay alarm |
| Model registry | `model_versions` + `metrics.json` exist; add baseline-relative metric + data window + git SHA |
| Strict promotion gates | extend `validation.py` with an IC/cost gate; define a 3-strike kill rule; re-validate on `model activate` |
| Clear portfolio objective | a one-page written objective: "max after-cost, after-tax IR vs AXJO at ≤ X% turnover" |
| No unsupported claims | brief caveats + `prob_up`/`confidence` display + realised-accuracy footnote |

**Principle:** match the *discipline* of institutions (evaluation, lineage, governance) at solo scale — not their *infrastructure*.
