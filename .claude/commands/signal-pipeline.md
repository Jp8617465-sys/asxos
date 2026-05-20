# Signal Pipeline Task

You are working on the ASX Portfolio OS signal generation pipeline.

<context>
- Model A v1_4: LightGBM classifier + regressor, 22 features (see models/model_a_v1_4_features.json)
- Feature groups: momentum, volatility, liquidity, trend, cross_sectional, fundamental, macro, sentiment
- Feature engine: app/features/ml/feature_engine.py (same code path for training + inference)
- Signal thresholds (vectorized np.where in jobs/generate_signals.py):
  STRONG_BUY: prob_up >= 0.65 AND expected_return > 0.05
  BUY: prob_up >= 0.55 AND expected_return > 0
  SELL: prob_up <= 0.45 AND expected_return < 0
  STRONG_SELL: prob_up <= 0.35 AND expected_return < -0.05
  HOLD: all other cases
- Models B/C/D + ensemble: see jobs/generate_signals_model_b.py, _c.py, _d.py, generate_ensemble_signals.py
- Backend: FastAPI on Render (port 8788) | DB: Supabase | Frontend: Next.js on Vercel
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- NEVER compute features using future data — all features use T-1 data only
- ALL feature computation goes through FeatureEngine — never compute inline
- Use vectorized np.where() for signal classification — never .apply() row-by-row
- Register numpy type adapters for psycopg2 BEFORE any DB writes
- LightGBM model artifacts stay on Render, never deployed to Vercel
- _safe_quintile() must guard every pd.qcut() call
- Validate with TimeSeriesSplit or PurgedGroupKFold — never random splits
</constraints>

<verify>
Before completing, confirm:
1. No feature uses data from after the prediction date (T-1 rule)
2. Time series cross-validation folds respect temporal ordering
3. Signal thresholds match the 5-level classification exactly
4. numpy adapters registered before any psycopg2 writes
5. Any new features added to feature_engine.py, not computed inline
</verify>
