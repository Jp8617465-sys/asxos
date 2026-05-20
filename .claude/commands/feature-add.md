# Add Feature to Signal Pipeline

<context>
Current: 22 features across 8 groups in app/features/ml/feature_engine.py
Feature groups: app/features/ml/feature_groups/ (momentum.py, volatility.py, fundamental.py, value_growth.py, etc.)
Model: LightGBM v1_4 on Render | DB: Supabase | Prediction horizon: 21 days
Feature list: models/model_a_v1_4_features.json
</context>

<task>
WHAT: Add new feature — $ARGUMENTS
WHERE: app/features/ml/feature_groups/{relevant_group}.py → registered in feature_engine.py
HOW: Implement calculation in feature group, add to FeatureEngine, retrain, evaluate
</task>

<constraints>
- Feature must be computable from data available at T-1 (no lookahead bias)
- Must handle missing values — use _safe_quintile() for any pd.qcut() calls
- Must work for all ASX symbols including illiquid small-caps
- Same code path for training AND inference (FeatureEngine)
- Update models/model_a_v{version}_features.json after successful integration
- EODHD is the sole price data source — never synthesise
</constraints>

<verify>
1. Feature correlation with existing 22 features (flag redundancy > 0.9)
2. Add leakage test confirming only T-1 data is used
3. Univariate AUC of new feature alone
4. Model AUC with and without new feature (ablation study)
5. SHAP values show meaningful, interpretable contribution
6. No NaN leakage into production predictions
7. Feature added to features.json and documented
</verify>
