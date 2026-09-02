-- 0050_research_registry.sql
-- =====================================================================
--
-- DRAFT — NOT APPLIED. Apply only under James's I5 grant (Amendment H,
-- 2026-09-02: "I authorise you to apply the migrations"), after the carrying
-- branch's tests are green.
--
-- Stage 2 — research registry and evaluation (target-architecture.md §15):
--   * ResearchHypothesis, ResearchRun, StrategyVersion contracts;
--   * reproducible cost-aware evaluation harness;
--   * walk-forward records;
--   * paper promotion state machine.
-- Exit gate: one hypothesis reproduced from raw data through evaluation;
-- failed variants remain visible; NO research can self-promote into capital.
--
-- Same shape as 0048 (the decision spine), for the same reason: every table
-- carries one authoritative `payload JSONB` holding the complete
-- `model.model_dump(mode="json")`; every other column is a NON-AUTHORITATIVE
-- shadow for indexing only; reconstruction is exclusively
-- `Model.model_validate(payload)`. Append-only, enforced by a BEFORE UPDATE
-- OR DELETE trigger, not by convention. No user_id/auth/RLS (rule #4).
--
-- The capital boundary is structural, not procedural: `promotion_state` is a
-- CHECK-constrained enum with NO capital value. There is no column, no
-- state, and no foreign key from this schema to model_versions,
-- approved_for_allocation, holding_lots, or the allocator. A research
-- result reaches capital only by a human writing a governed thesis — the
-- path the decision engine already gates (rule #11, s766B).
-- =====================================================================

CREATE OR REPLACE FUNCTION _research_registry_forbid_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'append-only: % on % is forbidden -- research-registry records are '
        'immutable and content-addressed; register a new version instead of '
        'mutating an existing one',
        TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- research_hypotheses  (ResearchHypothesis)
-- ============================================================
CREATE TABLE research_hypotheses (
    hypothesis_id       VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(hypothesis_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    factor              VARCHAR(100) NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL,
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'hypothesis_id' = hypothesis_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE TRIGGER research_hypotheses_forbid_mutation
    BEFORE UPDATE OR DELETE ON research_hypotheses
    FOR EACH ROW EXECUTE FUNCTION _research_registry_forbid_mutation();
COMMENT ON TABLE research_hypotheses IS
    'ResearchHypothesis — a falsifiable statement about a factor, universe, '
    'rebalance and horizon. Append-only; payload is authoritative.';

-- ============================================================
-- strategy_versions  (StrategyVersion)
-- ============================================================
CREATE TABLE strategy_versions (
    strategy_version_id VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(strategy_version_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    hypothesis_id       VARCHAR(200) NOT NULL
                        REFERENCES research_hypotheses(hypothesis_id),
    code_ref            VARCHAR(300) NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL,
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'strategy_version_id' = strategy_version_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_strategy_versions_hypothesis ON strategy_versions (hypothesis_id);
CREATE TRIGGER strategy_versions_forbid_mutation
    BEFORE UPDATE OR DELETE ON strategy_versions
    FOR EACH ROW EXECUTE FUNCTION _research_registry_forbid_mutation();
COMMENT ON TABLE strategy_versions IS
    'StrategyVersion — one concrete parameterisation of a hypothesis, bound '
    'to the code that evaluates it. Append-only.';

-- ============================================================
-- research_runs  (ResearchRun) — successes AND failures, forever
-- ============================================================
CREATE TABLE research_runs (
    run_id              VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(run_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    hypothesis_id       VARCHAR(200) NOT NULL
                        REFERENCES research_hypotheses(hypothesis_id),
    strategy_version_id VARCHAR(200) NOT NULL
                        REFERENCES strategy_versions(strategy_version_id),
    as_of               DATE         NOT NULL,
    panel_hash          VARCHAR(64)  NOT NULL
                        CHECK (panel_hash ~ '^[0-9a-f]{64}$'),
    outcome             VARCHAR(20)  NOT NULL
                        CHECK (outcome IN ('evaluated', 'fail')),
    created_at          TIMESTAMPTZ  NOT NULL,
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'run_id' = run_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_research_runs_hypothesis ON research_runs (hypothesis_id, created_at);
CREATE INDEX idx_research_runs_outcome ON research_runs (outcome);
CREATE TRIGGER research_runs_forbid_mutation
    BEFORE UPDATE OR DELETE ON research_runs
    FOR EACH ROW EXECUTE FUNCTION _research_registry_forbid_mutation();
COMMENT ON TABLE research_runs IS
    'ResearchRun — one evaluation of one StrategyVersion over one panel. '
    'Failed variants are rows with outcome = fail and are never deleted: '
    'the exit gate says failed variants remain visible.';

-- ============================================================
-- research_promotions — the paper promotion state machine's log
-- ============================================================
-- The enum is the boundary. Note what is NOT in it.
CREATE TABLE research_promotions (
    promotion_id        BIGSERIAL    PRIMARY KEY,
    strategy_version_id VARCHAR(200) NOT NULL
                        REFERENCES strategy_versions(strategy_version_id),
    from_state          VARCHAR(20)  NOT NULL
                        CHECK (from_state IN ('research', 'paper_candidate', 'paper', 'retired')),
    to_state            VARCHAR(20)  NOT NULL
                        CHECK (to_state IN ('research', 'paper_candidate', 'paper', 'retired')),
    evidence_run_id     VARCHAR(200) NULL
                        REFERENCES research_runs(run_id),
    reason              VARCHAR(2000) NOT NULL,
    decided_by          VARCHAR(100) NOT NULL,
    decided_at          TIMESTAMPTZ  NOT NULL,
    CONSTRAINT research_promotions_no_self_loop CHECK (from_state <> to_state)
);
CREATE INDEX idx_research_promotions_strategy ON research_promotions (strategy_version_id, decided_at);
CREATE TRIGGER research_promotions_forbid_mutation
    BEFORE UPDATE OR DELETE ON research_promotions
    FOR EACH ROW EXECUTE FUNCTION _research_registry_forbid_mutation();
COMMENT ON TABLE research_promotions IS
    'Append-only log of promotion_state transitions. The CHECK enums are the '
    'capital boundary: no capital state exists here or anywhere in this '
    'schema. Research reaches capital only through a governed thesis.';
