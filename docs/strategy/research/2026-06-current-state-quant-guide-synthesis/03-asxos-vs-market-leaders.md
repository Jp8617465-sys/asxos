# 03 — ASXOS vs Serious Quant / Institutional Standard

*Category-4 = publicly documented standard (not private fund internals). Condensed; full table in the v2 guide `03`. Updated with this pack's confirmed findings.*

## Gap table (top dimensions)
| Dimension | ASXOS now | Serious-quant standard | Gap | Near-term fix | Acceptance metric |
|---|---|---|---|---|---|
| Adjusted prices | **raw close** (adj_close 100% present, 25% differ — CONFIRMED) | adjusted/total-return | **RED** | adopt adj_close + retrain | ex-date artefacts gone |
| `expected_return` units | **bps vs fractional thresholds (CONFIRMED)** | consistent units | **RED** | re-derive thresholds / recalibrate | labels match intent |
| Calibration | none | reliability + Brier; isotonic/Platt | High | calibration audit | Brier ↓, reliability flat |
| Factor baselines | none | benchmark vs OSAP library + 12-1 mom | High | baseline suite | beats baselines on rank IC |
| Rank IC / decile spread | none | core metric, net-of-cost | High | implement metrics | positive net-of-cost IC |
| Transaction costs / turnover | none | proportional cost + turnover | High | cost stub + turnover | net-of-cost IR |
| Backtesting | 5-fold, no purge | purge/embargo → CPCV; DSR; PBO | High | purge+embargo first | PBO < ~0.2–0.5 |
| Survivorship / universe | `is_active` on history | as-of membership + delistings | High | universe_history | backtest incl. delisted |
| Risk model / optimizer | inverse-vol only | denoised covariance → HRP/Schur | Med | (defer behind L2) | risk-adjusted ↑ |
| Price completeness | dynamic, not persisted; 4-day gap | completeness SLA + durable metadata | Med | price_coverage table (`05`) | gaps auto-flagged |
| Monitoring / outcomes | job_runs + deadman; `signal_outcomes` unread | drift + rolling rank IC | Med | read-back outcomes | rolling IC tracked |
| Model registry / experiments | model_versions + metrics.json; no tracking | MLflow + lineage hash | Low–Med | data-window hash + MLflow local | lineage recorded |
| Brief/output honesty | hard labels, no prob_up/caveat | uncertainty + track record shown | High | brief caveat (E) | caveat shipped |
| Governance | statistical gates; ungated activate | economic gate + kill + re-validate | Med | IC/cost gate + kill rule | promotion gated |

## Top 10 gaps (priority order)
1. `expected_return` units (RED, confirmed). 2. raw vs adj_close (RED, confirmed). 3. No rank IC. 4. No factor baselines. 5. No cost/turnover model. 6. No calibration. 7. No purge/embargo (leakage). 8. Survivorship + no-AU-size-premium. 9. `signal_outcomes` unread. 10. Brief over-confidence.

## Top 5 near-term fixes
1. P0 units fix (model-preserving, approval-gated). 2. Brief honesty caveat (E). 3. adj_close + retrain (sequential). 4. Baseline + rank-IC harness (read-only research). 5. Durable `price_coverage` metadata (`05`).

## Top 5 do-not-build-yet
1. Threshold *optimization* (vs the one-off scale correction). 2. Model retraining for performance (vs the adj_close-correctness retrain). 3. New signals / signal families. 4. CPCV/Schur-HRP/MLflow/Evidently machinery (defer behind L2 verdict). 5. Portfolio automation.

## Lean translation (solo operator)
Match institutional **discipline**, not infrastructure: OSAP baselines (not a custom factor lib), one bps cost constant (not an impact model), denoised covariance (not Barra), MLflow-local (not Tecton), brief caveat (not a BI suite). See v2 guide `03`/`05`.
