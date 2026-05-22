# Model Experiment Task

You are running an ML experiment on the asxos signal system.

<context>
- Baseline: `model_a v1_5`, LightGBM classifier + regressor
- ROC-AUC: 0.7097 mean across 5-fold TimeSeriesSplit (n=1,052,811 rows)
- 22 features across 5 groups (momentum, volatility, liquidity, trend, fundamental)
- Hyperparameters of record (v1.5): `num_leaves=96`, `min_child_samples=20`,
  `class_weight=balanced`, `reg_lambda=0.6`
- Validation thresholds (M9 retraining gate):
  - `MIN_ROC_AUC=0.65`
  - `MAX_DEGRADATION=5%` (new version vs active on identical OOS window)
  - `MIN_SAMPLES=1000`
- Stack: LightGBM 4.5.0 + scikit-learn 1.5.2 + joblib
- Only model A exists in v1. Models B/C/D and the ensemble are out of v1 scope.
- Retraining job: `jobs/retrain_model_a.py` (walk-forward, writes versioned
  artefacts + a row to `model_versions` with `is_active=FALSE` until the
  operator activates via `asx model activate <version>`)
</context>

<experiment>
WHAT: $ARGUMENTS
WHERE: which files / functions / hyperparameters to modify
HOW: data splits (TimeSeriesSplit only), hyperparameter ranges, search strategy
BASELINE: v1.5 ROC-AUC 0.7097 — must beat by ≥1% on identical CV folds for
          a serious improvement claim, must not degrade by >5% to be eligible
          for activation
</experiment>

<constraints>
- Branch: `experiment/<descriptive-name>`
- All feature computation through `FeatureEngine` — never inline
- Never overwrite `models/model_a_v1_5_*` during experiments. Write new
  artefacts to `models/model_a_v1_6_*` (or higher) and a new model_versions row.
- Compare against v1.5 baseline on identical TimeSeriesSplit folds (same
  `random_state`, same fold boundaries) to control for split-induced variance.
- Report: ROC-AUC mean ± std, RMSE mean ± std, per-fold breakdown,
  confusion matrix on the held-out window, top-10 SHAP feature shifts vs v1.5
- Never activate from inside the experiment. Activation is a separate
  explicit CLI call after the operator reviews the report.
</constraints>

<verify>
1. Reproducible: random seed, data window cutoff, hyperparameters all logged
   to `models/model_a_v{version}_metrics.json`
2. No leakage: T-1 rule, TimeSeriesSplit folds non-overlapping
3. Same OOS test window as the v1.5 baseline metrics file
4. SHAP feature importance ranking written to
   `models/model_a_v{version}_shap_summary.json` if AUC improves
5. Retraining gate passes (ROC-AUC ≥ 0.65 AND degradation ≤ 5% vs v1.5)
6. `model_versions` row inserted with `is_active=FALSE`
7. Operator review: report includes per-fold table, hyperparameter diff
   from v1.5, and a one-line "ship / don't ship" recommendation
</verify>
