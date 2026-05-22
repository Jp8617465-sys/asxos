# Add Feature to Signal Pipeline

<context>
- Current: 22 Model A features across 5 groups in
  `asxos/domain/signals/feature_engine.py`
- Groups: `_momentum`, `_volatility`, `_liquidity`, `_trend`, `_fundamental`
  (private methods on FeatureEngine; not separate files like the old repo)
- Canonical feature list: `MODEL_A_FEATURES` constant at the top of
  feature_engine.py — must match `models/model_a_v1_5_features.json`
- Active model: `model_a v1_5` (LightGBM, 22 features). New feature
  requires a retrain via `jobs/retrain_model_a.py` to be useful at predict time.
- Prediction horizon: 21 trading days
- Tests: `tests/test_feature_engine.py` (parity + completeness)
</context>

<task>
WHAT: Add new feature — $ARGUMENTS
WHERE: extend a `_<group>` method on `FeatureEngine` and append the column name to `MODEL_A_FEATURES`. If the new feature loads from a new column the loader doesn't yet pull, also update `asxos/domain/signals/loader.py:_load_panel`.
HOW: implement → add to MODEL_A_FEATURES list → write tests → retrain → activate via `asx model activate <new_version>`
</task>

<constraints>
- T-1 only — no data from after the prediction date
- `_safe_quintile()` guards any `pd.qcut()` call (handles all-NaN groups)
- Must work for illiquid small-caps (most features fall back to NaN
  gracefully under `min_periods` rules; loader drops rows where
  technical features are NaN, zero-fills fundamentals)
- Same `FeatureEngine` instance is used in training and inference
- EODHD is the sole price source — never synthesise or interpolate
- After successful retrain: copy
  `models/model_a_v{new}_classifier.pkl`, `_regressor.pkl`, `_features.json`
  into `models/`, INSERT a row into `model_versions`, then activate via
  the CLI. The MODEL_A_FEATURES constant must match the new features.json.
</constraints>

<verify>
1. Correlation with existing 22 features (flag any > 0.9 — likely redundant)
2. Leakage test: feature uses only T-1 inputs
3. Univariate ROC-AUC of the new feature alone (sanity check)
4. Model AUC with and without the new feature (ablation; on identical
   TimeSeriesSplit folds)
5. SHAP values show interpretable contribution direction
6. No NaN leakage: `np.isfinite` holds on the post-loader feature snapshot
   for the technical-feature subset
7. `pytest tests/test_feature_engine.py` parity test still green
8. `MODEL_A_FEATURES` list and `models/model_a_v{new}_features.json` agree
9. `make check` green
</verify>
