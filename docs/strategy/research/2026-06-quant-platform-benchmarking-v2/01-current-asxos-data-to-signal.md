# 01 — Current ASXOS Data-to-Signal System (verified)

*Category-1 verified facts, read from `origin/main` HEAD `a719b3c` with `file:line`. The code is unchanged since the v1 guide, so this section is carried forward; only the modern-source framing in later files differs.*

## 1. Verified system map

| Layer | What it is | Evidence |
|---|---|---|
| **Ingestion** | EODHD AU bulk + US per-symbol prices, AUDUSD FX (`sync_prices`, 20:30 Sun–Thu); EODHD fundamentals (`sync_fundamentals`, 18:00 daily); exchange list (`sync_universe`, Sat); per-holding news (`ingest_news`); ATO/RBA/Treasury RSS (`ingest_regulatory`) | `render.yaml`, `asxos/ingestion/*`, `jobs/*` |
| **Price completeness** | `latest_complete_trading_day` anchor (`cf5d974`), sync completeness logging (`fe406d8`), generate_signals recency gate (`a719b3c`) | `asxos/domain/prices/coverage.py` |
| **Feature engineering** | `FeatureEngine`, 22-feature `MODEL_A_FEATURES`, 450-day lookback, fundamentals via `merge_asof` with 45-day disclosure lag | `feature_engine.py:22-45`, `loader.py:186-198` |
| **Model / scoring** | `model_a_v1_5`: LightGBM `LGBMClassifier` → `prob_up = predict_proba[:,1]`; `LGBMRegressor` → `expected_return`; TreeSHAP; joblib artefacts; 60s-TTL cache | `model_a.py:42-50`, `cache.py` |
| **Thresholds / labels** | Static dual-threshold ladder, regime-tightened extremes; vectorised `np.where`; confidence = `clip(round(|p−0.5|·200),0,100)` | `thresholds.py:26-97` |
| **Signal storage** | `signals(model, model_version, symbol, as_of, prob_up, expected_return, signal_label, confidence, regime, shap_factors)`, PK + UPSERT | `0001:95-108`, `writer.py:71-82` |
| **Brief usage** | Regime by exact `as_of`; label-change table vs holdings + one top SHAP factor; **prob_up/confidence not shown** | `compose.py:159-234` |
| **Portfolio usage** | `build_portfolio` filters `{STRONG_BUY,BUY}`, ranks by z-composite `0.6·z(prob_up)+0.4·z(expected_return)`, sizes by **inverse-vol**; 2-day staleness hard-fail. `snapshot_portfolio` does not read signals | `build.py:110-133`, `allocator.py:108-172` |
| **Monitoring / backup** | `JobMonitor`→`job_runs`, Healthchecks deadman, externally-verified `pg_dump`; `check_model_staleness` | `job_monitor.py` |
| **Research/backtest evidence** | ROC-AUC 0.7097 / n=1,052,811 **in prose only** (`ml-conventions.md:3`); promotion gates enforced; **no economic backtest, no rank IC, no baseline** | `validation.py:17-19` |

**Structural fact:** the model is fed **only** by `prices`, `fundamentals`, `universe`. News/regulatory feed only the brief. `signal_sentiment` is computed and **read by nothing**. `signal_outcomes` is written by `track_signal_outcomes` and **read by nothing** (no feedback loop).

## 2. The 22-feature contract (`feature_engine.py:22-45`)

Momentum (5): `ret_1d`, `mom_1/3/6/12_1`. Volatility (4): `vol_30/60/90`, `vol_ratio_30_90`. Liquidity (3): `adv_20_median`, `adv_zscore`, `volume_skew_60`. Trend (4): `trend_200`, `sma200_slope`, `sma200_slope_pos`, `atr_pct`. Value/quality (6): `pe_ratio`, `pb_ratio`, `eps`, `market_cap`, `pe_ratio_zscore`, `pb_ratio_zscore`. **All price features use raw `close`, not `adj_close`** (`loader.py:119,134`).

## 3. Labels (`thresholds.py`)

STRONG_BUY `prob_up≥0.65 & er>0.05`; BUY `≥0.55 & er>0`; SELL `≤0.45 & er<0`; STRONG_SELL `≤0.35 & er<−0.05`; HOLD else. Regime tightens extremes only (bear SB→0.70/0.06; bull SS→0.30/−0.06). Matches `ml-conventions.md`.

## 4. Plain English

A live LightGBM model produces, per ASX symbol per day, a probability of a 5-trading-day up-move (`prob_up`), a forward-return estimate (`expected_return`, units suspect — `06`), a rank, and a label. It is an **ML-assisted, factor-flavoured blend** (momentum/vol/liquidity/trend/value); sentiment/news do not feed it. Output is *all of*: probability, expected return, rank, label, confidence.

## 5. Classification (Phase 10)

**ML-assisted ranking signal with unverified alpha.** Not a coin flip (claimed AUC≈0.71 ≠ 0.50), but never measured in economic units (rank IC, quintile spread, net-of-cost return), no baseline, no calibration, and a possible label mis-specification.

- **Upgrade** → validated research signal: stable positive net-of-cost **rank IC** + monotone **decile spread**, out-of-sample with **purge/embargo**, **beating an Open-Source-Asset-Pricing baseline and 12-1 momentum**, on a survivorship-controlled universe, **Deflated-Sharpe-significant** for the trial count.
- **Downgrade:** IC ≈ 0 after costs; AUC collapses under CPCV; edge only in illiquid micro-caps.
- **Untrustworthy:** confirmed bps-units bug; raw-close ex-date artefacts; unquantified survivorship.
- **Brief meanwhile:** show `prob_up`/`confidence`/regime + "research-stage, single-model, unvalidated — not advice" caveat; add realised-accuracy once `signal_outcomes` is read back.
- **Do not yet use for portfolio decisions:** labels as standalone buy/sell instructions.
