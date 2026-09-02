-- 0051_theme_candidates.sql
-- =====================================================================
--
-- DRAFT — NOT APPLIED. Apply only under James's I5 grant (Amendment H,
-- 2026-09-02), after the carrying branch's tests are green.
--
-- Stage 3 — theme and candidate engine (target-architecture.md §15):
--   * versioned ThemeVersion + relationship model;
--   * deterministic theme evidence measures;
--   * an LLM extraction/synthesis boundary;
--   * a CandidateSnapshot contract with quality and expiry checks.
-- Exit gate: one emerging theme AND one security candidate reproducible from
-- exact evidence WITHOUT converting either into a recommendation.
--
-- Same shape as 0048/0050: one authoritative `payload JSONB` per row holding
-- the complete `model.model_dump(mode="json")`; shadow columns for indexing
-- only; reconstruction is exclusively `Model.model_validate(payload)`;
-- append-only by trigger. No user_id/auth/RLS (rule #4).
--
-- The "not a recommendation" property is enforced in the contracts (a
-- validator refuses any measure or check whose key names an action, weight,
-- size, target or verdict) and mirrored here: there is no state, verdict,
-- weight or size column on either table. A candidate becomes anything more
-- only by passing through the decision engine's gate (0048), where rule #11
-- and the s766B firewall live.
-- =====================================================================

CREATE OR REPLACE FUNCTION _theme_candidates_forbid_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'append-only: % on % is forbidden -- theme/candidate snapshots are '
        'immutable and content-addressed; build a new version instead',
        TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- theme_versions  (ThemeVersion) — a governed theme, measured at a cutoff
-- ============================================================
CREATE TABLE theme_versions (
    theme_version_id    VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(theme_version_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    theme_code          TEXT         NOT NULL,
    as_of               DATE         NOT NULL,
    knowledge_cutoff    TIMESTAMPTZ  NOT NULL,
    expires_at          TIMESTAMPTZ  NOT NULL,
    macro_thesis_id     BIGINT       NULL,
    data_mode           VARCHAR(10)  NOT NULL CHECK (data_mode IN ('real', 'synthetic')),
    created_at          TIMESTAMPTZ  NOT NULL,
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'theme_version_id' = theme_version_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_theme_versions_code_asof ON theme_versions (theme_code, as_of);
CREATE TRIGGER theme_versions_forbid_mutation
    BEFORE UPDATE OR DELETE ON theme_versions
    FOR EACH ROW EXECUTE FUNCTION _theme_candidates_forbid_mutation();
COMMENT ON TABLE theme_versions IS
    'ThemeVersion — a governed theme (themes.theme_code) measured at one '
    'knowledge cutoff with deterministic breadth/membership measures and cited '
    'evidence. Append-only; payload is authoritative. Carries no verdict.';

-- ============================================================
-- candidate_snapshots  (CandidateSnapshot) — one symbol, one theme version
-- ============================================================
CREATE TABLE candidate_snapshots (
    candidate_id        VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(candidate_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    symbol              TEXT         NOT NULL,
    theme_version_id    VARCHAR(200) NOT NULL
                        REFERENCES theme_versions(theme_version_id),
    as_of               DATE         NOT NULL,
    knowledge_cutoff    TIMESTAMPTZ  NOT NULL,
    expires_at          TIMESTAMPTZ  NOT NULL,
    quality_passed      BOOLEAN      NOT NULL,
    data_mode           VARCHAR(10)  NOT NULL CHECK (data_mode IN ('real', 'synthetic')),
    created_at          TIMESTAMPTZ  NOT NULL,
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'candidate_id' = candidate_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_candidate_snapshots_symbol_asof ON candidate_snapshots (symbol, as_of);
CREATE INDEX idx_candidate_snapshots_theme ON candidate_snapshots (theme_version_id);
CREATE TRIGGER candidate_snapshots_forbid_mutation
    BEFORE UPDATE OR DELETE ON candidate_snapshots
    FOR EACH ROW EXECUTE FUNCTION _theme_candidates_forbid_mutation();
COMMENT ON TABLE candidate_snapshots IS
    'CandidateSnapshot — one security under one ThemeVersion at one cutoff: '
    'deterministic measures, quality checks, expiry, cited evidence. Not a '
    'recommendation: no verdict, weight, size or target exists on this row or '
    'in its payload (validator-enforced). Append-only.';
