-- 0003_model_a_v1_5_seed.sql
-- Seeds Model A v1_5 in model_versions and marks it active.
-- Artefacts live on disk at the convention path:
--   models/{model}_{version}_classifier.pkl
--   models/{model}_{version}_regressor.pkl
--   models/{model}_{version}_features.json
-- Loader: asxos/domain/models/cache.py (M6).
-- Applied via: mcp__supabase__apply_migration

-- Idempotent: safe to re-run.
INSERT INTO model_versions (model, version, roc_auc, is_active, notes)
VALUES (
    'model_a',
    'v1_5',
    0.709721,
    TRUE,
    'Seeded at M6. CV: 5-fold TimeSeriesSplit, n_samples=1052811, auc_per_fold mean 0.7097±0.014, rmse_mean 82.50. Same 22-feature set as v1.4; tuned LightGBM (num_leaves=96, min_child_samples=20, L2=0.6, class_weight=balanced).'
)
ON CONFLICT (model, version) DO UPDATE
SET roc_auc   = EXCLUDED.roc_auc,
    is_active = EXCLUDED.is_active,
    notes     = EXCLUDED.notes;
