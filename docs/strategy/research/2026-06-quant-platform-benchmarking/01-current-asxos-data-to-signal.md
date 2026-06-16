# 01 — Current ASXOS Data-to-Signal System (verified)

*All claims here are read from `origin/main` HEAD `a719b3c` with `file:line` evidence. This is category-1 "verified ASXOS facts."*

## 1. Verified system map

| Layer | What it is | Evidence |
|---|---|---|
| **Ingestion** | EODHD AU bulk + US per-symbol prices, AUDUSD FX (`sync_prices`, 20:30 Sun–Thu); EODHD fundamentals (`sync_fundamentals`, 18:00 daily); exchange list (`sync_universe`, Sat); per-holding news (`ingest_news`); ATO/RBA/Treasury RSS (`ingest_regulatory`) | `render.yaml`, `asxos/ingestion/*`, `jobs/*` |
| **Price completeness** | `latest_complete_trading_day` anchor (`cf5d974`), sync completeness logging (`fe406d8`), generate_signals recency gate (`a719b3c`). Residue (12/14-row non-trading days) classified, not trusted | `asxos/domain/prices/coverage.py` |
| **Feature engineering** | `FeatureEngine`, 22-feature `MODEL_A_FEATURES`, 450-day lookback, fundamentals via `merge_asof` with 45-day disclosure lag | `feature_engine.py:22-45`, `loader.py:186-198` |
| **Model / scoring** | `model_a_v1_5`: LightGBM `LGBMClassifier` → `prob_up = predict_proba[:,1]`; `LGBMRegressor` → `expected_return`; TreeSHAP (logit space); joblib artefacts; 60s-TTL cache | `model_a.py:42-50`, `cache.py` |
| **Thresholds / labels** | Static dual-threshold ladder, regime-tightened extremes; vectorised `np.where`; confidence = `clip(round(|p−0.5|·200),0,100)` | `thresholds.py:26-97` |
| **Signal storage** | `signals(model, model_version, symbol, as_of, prob_up, expected_return, signal_label, confidence, regime, shap_factors)`, PK `(model, model_version, symbol, as_of)`, UPSERT | migration `0001:95-108`, `writer.py:71-82` |
| **Brief usage** | Regime by **exact** `as_of`; label-change table vs holdings + one top SHAP factor; **prob_up / confidence not shown** | `compose.py:159-234`, `brief.html.j2` |
| **Portfolio usage** | `build_portfolio` filters `{STRONG_BUY, BUY}`, ranks by z-composite `0.6·z(prob_up)+0.4·z(expected_return)`, sizes by **inverse-volatility**; 2-day staleness hard-fail. `snapshot_portfolio` does **not** read signals | `build.py:110-133`, `allocator.py:108-172` |
| **Monitoring / backup** | `JobMonitor`→`job_runs` (success/blocked/failure), Healthchecks deadman, externally-verified `pg_dump` backup; `check_model_staleness` | `job_monitor.py`, job-conventions.md |
| **Research / backtest evidence** | ROC-AUC 0.7097 / n=1,052,811 **in prose only** (`ml-conventions.md:3`); promotion gates enforced; **no economic backtest, no rank IC, no baseline** | `validation.py:17-19`, `retrain_model_a.py` |

**Structural fact:** the model is fed **only** by `prices`, `fundamentals`, and `universe`. News and regulatory data feed only the brief. Computed sentiment (`signal_sentiment`) is **read by nothing** — a write-only dead-end table.

## 2. The 22-feature contract (`MODEL_A_FEATURES`, `feature_engine.py:22-45`)

- **Momentum (5):** `ret_1d`, `mom_1` (21d), `mom_3` (63d), `mom_6` (126d), `mom_12_1` (231d skip-month).
- **Volatility (4):** `vol_30`, `vol_60`, `vol_90` (rolling std of `ret_1d`), `vol_ratio_30_90`.
- **Liquidity (3):** `adv_20_median` (close×volume), `adv_zscore` (vs 252d), `volume_skew_60`.
- **Trend (4):** `trend_200` (close>SMA200), `sma200_slope` (20-day polyfit), `sma200_slope_pos`, `atr_pct`.
- **Value/quality (6):** `pe_ratio`, `pb_ratio`, `eps`, `market_cap`, `pe_ratio_zscore`, `pb_ratio_zscore`.

Technical features are trailing-window / `pct_change` / `shift` → **no forward lookahead**. Fundamentals join via `merge_asof(direction="backward")` on `effective_dt = as_of + 45d` → point-in-time at disclosure-lag granularity. **All price features use raw `close`, not `adj_close`** (`loader.py:119,134`) — see `06-signal-correctness-risks.md`.

## 3. Labels (`thresholds.py`)

| Label | Base rule |
|---|---|
| STRONG_BUY | `prob_up ≥ 0.65` AND `expected_return > 0.05` |
| BUY | `prob_up ≥ 0.55` AND `expected_return > 0` |
| HOLD | everything else |
| SELL | `prob_up ≤ 0.45` AND `expected_return < 0` |
| STRONG_SELL | `prob_up ≤ 0.35` AND `expected_return < −0.05` |

Regime tightens **only the extremes**: bear → STRONG_BUY (0.70, 0.06); bull → STRONG_SELL (0.30, −0.06). Regime itself = 200-day SMA position + 20-day slope on a top-10-liquidity proxy → bull/bear/neutral. Code thresholds match `ml-conventions.md` exactly.

## 4. Plain-English explanation (Phase 2)

- **What data comes in?** Daily OHLCV (raw close), quarterly-ish fundamentals (P/E, P/B, EPS, market cap), the active universe. News/regulatory exist but don't feed the model.
- **Which tables store it?** `prices`, `fundamentals`, `universe` (model inputs); `signals` (output); `holding_news`, `regulatory_events`, `signal_sentiment`, `portfolio_daily_snapshots`, `job_runs`, `model_versions`, `fx_rates`.
- **What features are built?** The 22 above — a momentum/volatility/liquidity/trend/value blend.
- **ML, heuristic, factor, or blended?** **ML-assisted and factor-flavoured**: LightGBM learns a non-linear map from factor-style features to a 5-day forward outcome; a fixed heuristic ladder turns scores into labels.
- **What does LightGBM do?** Gradient-boosted decision trees. Classifier → P(up in 5 trading days); regressor → size of the 5-day forward return.
- **`prob_up`?** Model probability of an up-move over 5 trading days (uncalibrated).
- **`expected_return`?** Regression point estimate of the 5-day return — **units suspect** (see `06`).
- **BUY/HOLD/SELL?** A directional opinion over ~1 week. BUY/STRONG_BUY = above-threshold up-probability *and* positive expected return; HOLD = the large middle.
- **Output type?** *All of the above* — a probability, an expected return, a cross-sectional rank (by `prob_up`), a label, plus a confidence restatement.

## 5. Classification (Phase 10)

**Current classification: ML-assisted ranking signal with unverified alpha.**

- **Why:** it is genuinely a live ML model with plausible statistical discrimination (claimed AUC ≈ 0.71, i.e. **not** a coin flip at 0.50), but it has **never** been measured in the units that determine economic value (rank IC, quintile spread, net-of-cost return, turnover), has no baseline comparison, no calibration, and a possible label mis-specification (`expected_return` units).
- **Would UPGRADE it** to *validated research signal*: stable positive **rank IC** (e.g. ≥ 0.03 monthly) and a positive **top-minus-bottom quintile spread** out-of-sample with purge/embargo, **net of realistic costs**, **beating 12-1 momentum and equal-weight**, on a survivorship-controlled universe.
- **Would DOWNGRADE it:** IC indistinguishable from zero after costs; AUC collapses under purged walk-forward; spread driven only by illiquid micro-caps.
- **Would make it UNTRUSTWORTHY:** confirmation of the bps units bug; raw-close corporate-action artefacts dominating momentum; unquantified survivorship inflation.
- **What the brief should say meanwhile:** present labels **with `prob_up`, `confidence`, regime, and an explicit "research-stage, single-model, unvalidated — not advice" caveat**; add a realised hit-rate/IC footnote once `signal_outcomes` is read back. Today the brief shows hard BUY/SELL with none of this.
- **What must NOT be used for portfolio decisions yet:** the labels as standalone buy/sell instructions, and any implied "two independent signals agree" framing (the `expected_return` arm may be inert).
