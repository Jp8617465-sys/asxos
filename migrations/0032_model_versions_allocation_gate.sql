-- 0032_model_versions_allocation_gate.sql
--
-- Contamination-isolation gate (governance architecture Section 4.4 Step B).
--
-- build.py/compose.py previously selected the "production model" by name
-- (a hardcoded _PRODUCTION_MODEL = "model_a" constant, Step A). That is a
-- convention, not a guard — nothing stops a second model's rows (a future
-- factor sleeve, a debugging insert) from silently reaching the allocator
-- the moment a second model_versions row exists and is marked is_active.
--
-- approved_for_allocation is a second, orthogonal bit alongside is_active:
-- is_active means "current version of this model" (already enforced
-- per-model by model_versions_one_active_idx); approved_for_allocation
-- means "this model is allowed to influence the live portfolio at all".
-- A new model can be inserted, backtested, and iterated within its own
-- model namespace without ever being visible to build.py/compose.py,
-- because that requires a second, separate, explicit human action.
--
-- Applied via: mcp__supabase__apply_migration

ALTER TABLE model_versions
    ADD COLUMN approved_for_allocation BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN model_versions.approved_for_allocation IS
    'Gate for production allocator reads (build.py, compose.py). FALSE by '
    'default -- a new model_version row is NOT eligible for build-portfolio '
    'or the brief until explicitly approved. is_active alone only controls '
    'which version of an already-approved model is current; it does not '
    'imply production-allocation eligibility.';

-- Explicit one-time grandfather of the only model in production today.
-- Not a DEFAULT TRUE -- that would defeat the gate's purpose for every
-- future row. This is a deliberate, reviewed decision recorded here.
UPDATE model_versions
SET approved_for_allocation = TRUE
WHERE model = 'model_a' AND version = 'v1_5';
