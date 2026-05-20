---
paths:
  - app/features/ml/**
  - app/features/signals/**
  - app/features/models/**
  - jobs/generate_signals*
  - jobs/retrain_*
  - jobs/generate_ensemble*
  - jobs/backtest_*
  - jobs/build_training*
  - jobs/build_extended*
  - models/**
---

# ML Pipeline Rules — ASX Portfolio OS

## Model Artefacts
- Never modify `.pkl` / `.joblib` files directly — use the retraining pipeline (`jobs/retrain_model_a.py`)
- Model version convention: `v{major}_{minor}` (e.g., `v1_4` → `v1_5`); increment minor on retrain
- Model files: `models/model_a_v{version}_classifier.pkl`, `_regressor.pkl`, `_features.json`
- Always validate via `RetrainingService` before deploying a new model version

## Feature Engine
- ALL feature computation must go through `FeatureEngine` (`app/features/ml/feature_engine.py`) — never compute features inline
- 8 feature groups: momentum, volatility, liquidity, trend, cross_sectional, fundamental, macro, sentiment
- Feature groups live in `app/features/ml/feature_groups/` — new groups must be importable from there
- `_safe_quintile()` must guard every `pd.qcut()` call to handle all-NaN or low-cardinality groups
- Same FeatureEngine instance used in training AND inference — this eliminates training/serving skew

## Data Integrity
- ALL features must be computable from data available at T-1 (day before prediction date)
- Never use `train_test_split` — always `TimeSeriesSplit` or `PurgedGroupKFold`
- EODHD API is the sole price data source — never synthesise or interpolate prices
- Missing fundamental columns are zero-filled (see `generate_signals.py` lines 274-280)

## Signal Generation
- Scripts MUST register numpy type adapters for psycopg2 BEFORE any DB writes:
  ```python
  for np_type, py_type in [(np.int64, int), (np.int32, int), (np.float64, float), ...]:
      psycopg2.extensions.register_adapter(np_type, lambda x, cast=py_type: AsIs(cast(x)))
  ```
- Use vectorized `np.where()` for signal classification — never `.apply()` row-by-row
- Confidence formula: `(np.abs(prob_up - 0.5) * 200).astype(int)`

## Validation Thresholds
- MIN_ROC_AUC: 0.65 (env: `MIN_ROC_AUC`)
- MAX_DEGRADATION: 5% (env: `MAX_DEGRADATION_PERCENT`)
- MIN_SAMPLES: 1000 (env: `MIN_TRAINING_SAMPLES`)
- Do not accept changes that reduce model performance below these floors

## Signal Thresholds (do not modify without explicit instruction)
- STRONG_BUY: prob_up >= 0.65 AND expected_return > 0.05
- BUY: prob_up >= 0.55 AND expected_return > 0
- SELL: prob_up <= 0.45 AND expected_return < 0
- STRONG_SELL: prob_up <= 0.35 AND expected_return < -0.05
- HOLD: all other cases

## Testing ML Changes
- Run: `pytest tests/ -k "signal or model" -v`
- For feature engine changes: verify feature parity between training and inference paths
- For new features: add a leakage test confirming only T-1 data is used
