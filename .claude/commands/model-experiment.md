# Model Experiment Task

You are running an ML experiment on the ASX Portfolio OS trading system.

<context>
- Current baseline: Model A v1_4, LightGBM classifier + regressor
- 22 features across 8 groups (momentum, volatility, liquidity, trend, cross_sectional, fundamental, macro, sentiment)
- Validation thresholds: MIN_ROC_AUC=0.65, MAX_DEGRADATION=5%, MIN_SAMPLES=1000
- Stack: LightGBM + SHAP on FastAPI/Render
- Active models: A (technical), B (fundamentals), C (sentiment/FinBERT), D (value-growth composite)
- Ensemble: jobs/generate_ensemble_signals.py
- Retraining: jobs/retrain_model_a.py → app/features/models/services/retraining_service.py
</context>

<experiment>
WHAT: $ARGUMENTS
WHERE: Specify exact files and functions to modify
HOW: Describe the experimental approach, hyperparameters, data splits
BASELINE: Current metric to beat (MIN_ROC_AUC=0.65 for production acceptance)
</experiment>

<constraints>
- Create experiment branch: `experiment/descriptive-name`
- ALL feature computation through FeatureEngine — never inline
- Never modify production model artifacts in models/ during experiments
- Compare against baseline using identical test periods (TimeSeriesSplit)
- Report: ROC-AUC, precision per signal class, confusion matrix, Sharpe ratio
- Validate via RetrainingService before any deployment
</constraints>

<verify>
1. Experiment is fully reproducible (seed, data version, params logged)
2. No data leakage in train/test split (T-1 rule enforced)
3. Results compared against current model on same test set
4. SHAP explanations generated if AUC improves
5. Retraining validation passes (ROC-AUC >= 0.65, degradation <= 5%)
</verify>
