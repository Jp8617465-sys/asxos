---
paths:
  - asxos/domain/signals/**
  - asxos/domain/models/**
  - jobs/generate_signals*
  - jobs/retrain_*
  - models/**
---

# ML Pipeline Rules — asxos

## Model Artefacts

- Active model: `model_a_v1_5` (LightGBM classifier + regressor, ROC-AUC 0.7097
  on 5-fold TimeSeriesSplit, n=1,052,811 training rows).
- Artefacts on disk under `models/`:
  - `models/model_a_v{version}_classifier.pkl`
  - `models/model_a_v{version}_regressor.pkl`
  - `models/model_a_v{version}_features.json`
- Version convention: `v{major}_{minor}` — increment minor on retrain.
- Active version is the row in `model_versions` where `is_active = TRUE`.
  Flip via `asx model activate <version>` (M9 CLI).
- Loader: `asxos/domain/models/cache.py` (60s TTL re-read of is_active).

## Feature Engine

- All feature computation goes through `FeatureEngine` in
  `asxos/domain/signals/feature_engine.py`. Never inline.
- 5 feature groups (momentum, volatility, liquidity, trend, fundamental).
  The 22-feature contract is locked in `MODEL_A_FEATURES` constant.
- Same `FeatureEngine` instance is used in training and inference — this
  is the structural fix for training/serving skew.
- `_safe_quintile()` guards every `pd.qcut()` call (handles all-NaN groups).
- Fundamentals are joined via `pd.merge_asof` with a 45-day disclosure lag
  in `asxos/domain/signals/loader.py`.

## Data Integrity

- All features computed from T-1 data only — no lookahead.
- Validation uses `TimeSeriesSplit` (or `PurgedGroupKFold`). Never random
  `train_test_split`.
- EODHD is the sole price source. No synthesised or interpolated prices.
- Fundamental features (`pe_ratio`, `pb_ratio`, `eps`, `market_cap`,
  `pe_ratio_zscore`, `pb_ratio_zscore`) are **zero-filled** when absent.
  See `FUNDAMENTAL_FEATURE_COLS` in `asxos/domain/signals/loader.py`.
  Technical features still require a fully-populated lookback window.

## Signal Generation

- Use vectorised `np.where()` (or `np.select`) for label classification.
  Never `.apply()` row-by-row. The canonical batch is
  `asxos.domain.signals.thresholds.classify_batch`.
- Confidence: `np.clip(np.round(np.abs(p - 0.5) * 200), 0, 100).astype(int)`.
  See `confidence_from_prob_up`.
- Writer (`asxos/domain/signals/writer.py`) re-aligns `shap_df` to
  `preds.index` before iterating — `preds` is rank-sorted, `shap_df` keeps
  input order, so set-equality is not enough.

## Signal Thresholds (canonical — do not modify without explicit instruction)

```
STRONG_BUY  : prob_up >= 0.65 AND expected_return >  0.05
BUY         : prob_up >= 0.55 AND expected_return >  0
SELL        : prob_up <= 0.45 AND expected_return <  0
STRONG_SELL : prob_up <= 0.35 AND expected_return < -0.05
HOLD        : everything else
```

Regime-conditioned overrides (see `apply_regime_thresholds`):
- `bear` tightens STRONG_BUY to (0.70, 0.06); BUY falls through to neutral.
- `bull` tightens STRONG_SELL to (0.30, -0.06); SELL falls through to neutral.

## Validation Thresholds (retraining gate, M9)

- MIN_ROC_AUC: 0.65 — reject if below.
- MAX_DEGRADATION: 5% — reject if new version is more than 5% worse than
  the active version on the same OOS test window.
- MIN_SAMPLES: 1000 — reject if training set is too small.

## NumPy adapters

- API + signal writer use asyncpg, which handles numpy types natively —
  no adapters needed.
- Jobs that use psycopg2 (e.g. legacy training scripts) must register
  adapters BEFORE any `executemany` / `execute` with numpy values:
  ```python
  for np_type, py_type in [(np.int64, int), (np.int32, int), (np.float64, float)]:
      psycopg2.extensions.register_adapter(np_type, lambda x, cast=py_type: AsIs(cast(x)))
  ```

## Testing

- `pytest tests/ -k "signal or model or feature or thresholds or regime"`
- For feature engine changes: keep `test_feature_engine.py` parity test
  (m1 = m2 on repeated `compute_all_features`).
- For new features: add a leakage test confirming only T-1 inputs.
- For threshold changes: update the boundary parameterisation in
  `tests/test_thresholds.py` and verify `classify_batch_matches_per_row`.
