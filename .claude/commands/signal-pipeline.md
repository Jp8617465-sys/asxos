# Signal Pipeline Task

You are working on the asxos signal generation pipeline.

<context>
- Model A v1_5: LightGBM classifier + regressor, 22 features
  (`models/model_a_v1_5_features.json`). ROC-AUC 0.7097 on 5-fold TimeSeriesSplit.
- 5 feature groups: momentum, volatility, liquidity, trend, fundamental
- Feature engine: `asxos/domain/signals/feature_engine.py` (same code path
  for training and inference)
- Loader: `asxos/domain/signals/loader.py` — 450-day lookback,
  pd.merge_asof with a 45-day fundamentals lag, zero-fills the 6
  fundamental columns when sparse
- Cache: `asxos/domain/models/cache.py` — 60s TTL re-read of
  model_versions.is_active
- Job: `jobs/generate_signals.py` — wraps everything; gates on
  `sync_prices` having a `status='success'` row in `job_runs`
- Writer: `asxos/domain/signals/writer.py` — UPSERT into the signals table
  (model, model_version, symbol, as_of)
- Schedule: 20:50 UTC Sun-Thu (06:50 Mon-Fri AEST)
- Regime: `asxos/domain/signals/regime.py` — top-10 most-traded ASX200 proxy,
  200-day MA + 20-day slope, returns bull/bear/neutral
- Thresholds: `asxos/domain/signals/thresholds.py` — canonical
  `classify_batch` (vectorised np.where) + regime overrides

Signal labels (regime=neutral; see thresholds.py for bear/bull):
  STRONG_BUY:  prob_up >= 0.65 AND expected_return >  0.05
  BUY:         prob_up >= 0.55 AND expected_return >  0
  SELL:        prob_up <= 0.45 AND expected_return <  0
  STRONG_SELL: prob_up <= 0.35 AND expected_return < -0.05
  HOLD:        everything else

Stack: FastAPI (currently unhosted) | Supabase Postgres 16 | jobs as GitHub Actions | no frontend
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- T-1 rule: never compute a feature using data after the prediction date
- All feature computation through `FeatureEngine` — never inline
- Vectorised `np.where()` / `np.select()` for label classification
- `_safe_quintile()` guards every `pd.qcut()` call
- TimeSeriesSplit (or PurgedGroupKFold) only — never random train/test split
- asyncpg + `$1` parameter syntax. No psycopg2 in the API or new jobs.
- Writer must `shap_df.reindex(preds.index)` before iterating — preds is
  rank-sorted, shap_df keeps input order
- Fundamental columns and their z-scores are zero-filled when missing;
  technical features still require a fully-populated lookback window
</constraints>

<verify>
1. No feature reads from beyond the prediction date (T-1 rule)
2. Time-series CV folds respect temporal ordering
3. Signal label classification matches `classify_batch` exactly
4. New features added to `MODEL_A_FEATURES` constant in feature_engine.py
5. `pytest tests/ -k "signal or feature or thresholds or regime"` passes
6. `make check` passes (ruff + mypy + pytest)
</verify>
