-- 0048_decision_packets.sql
-- =====================================================================
--
-- APPLIED 2026-09-01 — governor grant (James's explicit instruction,
-- attended session). Ledger name `decision_packets`, version
-- `20260901062502` (asx-portfolio-os / gxjqezqndltaelmyctnl).
-- Authored by the Slice 1 "decision spine" mission; applied only after
-- PR #183 went green (full-check CI + tax/security consults) and James
-- authorized the apply.
--
-- Persists the decision-engine contract chain
-- (asxos/domain/decision_engine/types.py, 705 lines, FROZEN -- do not
-- edit that file to make persistence easier) from EvidencePacket
-- through DecisionPacket. One table per top-level
-- ContentAddressedContract: evidence_packets, thesis_versions,
-- challenge_results, portfolio_assessments, decision_packets. No
-- `evidence_items` table -- EvidenceItem lives only inside
-- evidence_packets.payload (see below). No user_id/auth/RLS (CLAUDE.md
-- rule #4, single user).
--
-- ROUND-TRIP FIDELITY IS THE LOAD-BEARING PROPERTY. Every table carries
-- exactly one authoritative `payload JSONB NOT NULL` column holding the
-- complete `model.model_dump(mode="json")` of the top-level contract,
-- nested tuples/sub-models included verbatim (items, scenarios,
-- constraints, findings, model_and_prompt_manifest, size_range,
-- trading_calendar, upstream_hashes, tax_assessment_reference).
-- repository.load() MUST reconstruct exclusively via
-- `ModelClass.model_validate(row["payload"])`. Every other column on
-- these tables is a derived, NON-AUTHORITATIVE shadow copy for
-- indexing/filtering ONLY -- never read back into a reconstructed
-- model. This is not stylistic: NUMERIC(18,6) and TIMESTAMPTZ columns
-- round-trip through Postgres at a fixed display scale/precision that
-- can differ in string form from what the Pydantic model originally
-- serialized (e.g. Decimal("100") vs Decimal("100.000000") are
-- numerically equal but serialize to different JSON strings under
-- model_dump(mode="json")) -- reconstructing loss_budget_aud from the
-- NUMERIC(18,6) shadow column instead of payload would silently break
-- verify_content_hash() on every PortfolioAssessment. See
-- portfolio_assessments.loss_budget_aud below.
--
-- Append-only: every table gets a BEFORE UPDATE OR DELETE trigger
-- (_decision_engine_forbid_mutation()) that hard-fails any mutation.
-- decision_packets.supersede(): INSERT a new row with a new
-- decision_packet_id and supersedes_packet_id pointing at the old
-- row's id; the old row is never touched (CLAUDE.md rule #10).
--
-- Applied via: mcp__supabase__apply_migration -- BY JAMES ONLY.
-- =====================================================================

CREATE OR REPLACE FUNCTION _decision_engine_forbid_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'append-only: % on % is forbidden -- decision-engine contracts are '
        'immutable and content-addressed; insert a new row (see supersede() '
        'on decision_packets) instead of mutating an existing one',
        TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- evidence_packets  (EvidencePacket, types.py:234-260)
-- ============================================================
CREATE TABLE evidence_packets (
    evidence_packet_id VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(evidence_packet_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    as_of                DATE         NOT NULL,
    knowledge_cutoff     TIMESTAMPTZ  NOT NULL,
    expires_at           TIMESTAMPTZ  NOT NULL,
    data_mode            VARCHAR(10)  NOT NULL
                        CHECK (data_mode IN ('real','synthetic')),
    created_at           TIMESTAMPTZ  NOT NULL,
    payload              JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'evidence_packet_id' = evidence_packet_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_evidence_packets_as_of ON evidence_packets (as_of);
CREATE TRIGGER evidence_packets_forbid_mutation
    BEFORE UPDATE OR DELETE ON evidence_packets
    FOR EACH ROW EXECUTE FUNCTION _decision_engine_forbid_mutation();

COMMENT ON TABLE evidence_packets IS
    'Top-level EvidencePacket (types.py:234). payload is authoritative '
    '(model_dump(mode="json")); all other columns are non-authoritative '
    'query shadows. Never read items back from anywhere but payload.';

-- ============================================================
-- thesis_versions  (ThesisVersion, types.py:273-307)
-- ============================================================
CREATE TABLE thesis_versions (
    thesis_version_id    VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(thesis_version_id) >= 1),
    content_hash          VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    security_id           VARCHAR(200) NOT NULL,
    symbol                VARCHAR(100) NOT NULL,
    exchange              VARCHAR(100) NOT NULL,
    version               INTEGER      NOT NULL CHECK (version >= 1),
    evidence_packet_id    VARCHAR(200) NOT NULL
                        REFERENCES evidence_packets(evidence_packet_id),
    as_of                 DATE         NOT NULL,
    knowledge_cutoff      TIMESTAMPTZ  NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL,
    theme                 VARCHAR(500)   NOT NULL,
    investment_question   VARCHAR(5000)  NOT NULL,
    variant_view          VARCHAR(10000) NOT NULL,
    thesis_summary        VARCHAR(20000) NOT NULL,
    horizon_months        SMALLINT     NOT NULL
                        CHECK (horizon_months BETWEEN 1 AND 120),
    payload               JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'thesis_version_id' = thesis_version_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_thesis_versions_symbol_asof ON thesis_versions (symbol, as_of DESC);
CREATE INDEX idx_thesis_versions_evidence_packet ON thesis_versions (evidence_packet_id);
CREATE TRIGGER thesis_versions_forbid_mutation
    BEFORE UPDATE OR DELETE ON thesis_versions
    FOR EACH ROW EXECUTE FUNCTION _decision_engine_forbid_mutation();

-- ============================================================
-- challenge_results  (ChallengeResult, types.py:317-338)
-- ============================================================
CREATE TABLE challenge_results (
    challenge_result_id   VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(challenge_result_id) >= 1),
    content_hash           VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    thesis_version_id      VARCHAR(200) NOT NULL
                        REFERENCES thesis_versions(thesis_version_id),
    evidence_packet_id     VARCHAR(200) NOT NULL
                        REFERENCES evidence_packets(evidence_packet_id),
    as_of                  DATE         NOT NULL,
    knowledge_cutoff       TIMESTAMPTZ  NOT NULL,
    created_at             TIMESTAMPTZ  NOT NULL,
    outcome                VARCHAR(10)  NOT NULL
                        CHECK (outcome IN ('pass','revise','abstain')),
    strongest_bear_case    VARCHAR(20000) NOT NULL,
    independent_of_author  BOOLEAN      NOT NULL CHECK (independent_of_author),
    payload                JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'challenge_result_id' = challenge_result_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_challenge_results_thesis_version ON challenge_results (thesis_version_id);
CREATE TRIGGER challenge_results_forbid_mutation
    BEFORE UPDATE OR DELETE ON challenge_results
    FOR EACH ROW EXECUTE FUNCTION _decision_engine_forbid_mutation();

-- ============================================================
-- portfolio_assessments  (PortfolioAssessment, types.py:363-399)
-- ============================================================
CREATE TABLE portfolio_assessments (
    portfolio_assessment_id VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(portfolio_assessment_id) >= 1),
    content_hash             VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    portfolio_snapshot_id    VARCHAR(200) NOT NULL,
    thesis_version_id        VARCHAR(200) NOT NULL
                        REFERENCES thesis_versions(thesis_version_id),
    as_of                    DATE         NOT NULL,
    knowledge_cutoff         TIMESTAMPTZ  NOT NULL,
    created_at               TIMESTAMPTZ  NOT NULL,
    assessment_state         VARCHAR(20)  NOT NULL
                        CHECK (assessment_state IN
                            ('initiate','watch','avoid','add','trim','exit_review','abstain')),
    loss_budget_aud          NUMERIC(18,6) NOT NULL CHECK (loss_budget_aud >= 0),
    marginal_risk            VARCHAR(10000) NOT NULL,
    opportunity_cost         VARCHAR(10000) NOT NULL,
    payload                  JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'portfolio_assessment_id' = portfolio_assessment_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_portfolio_assessments_thesis_version ON portfolio_assessments (thesis_version_id);
CREATE INDEX idx_portfolio_assessments_state ON portfolio_assessments (assessment_state);
CREATE TRIGGER portfolio_assessments_forbid_mutation
    BEFORE UPDATE OR DELETE ON portfolio_assessments
    FOR EACH ROW EXECUTE FUNCTION _decision_engine_forbid_mutation();

-- ============================================================
-- decision_packets  (DecisionPacket, types.py:443-529)
-- ============================================================
CREATE TABLE decision_packets (
    decision_packet_id      VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(decision_packet_id) >= 1),
    content_hash              VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    schema_version             VARCHAR(100) NOT NULL,
    as_of                      DATE         NOT NULL,
    knowledge_cutoff           TIMESTAMPTZ  NOT NULL,
    recommendation_state       VARCHAR(20)  NOT NULL
                        CHECK (recommendation_state IN
                            ('initiate','watch','avoid','add','trim','exit_review','abstain')),
    expires_at                 TIMESTAMPTZ  NOT NULL,
    expiry_reason              VARCHAR(30)  NOT NULL DEFAULT 'default'
                        CHECK (expiry_reason IN
                            ('default','material_event','stale_evidence',
                             'constraint_change','portfolio_snapshot_change')),
    portfolio_snapshot_id      VARCHAR(200) NOT NULL,
    evidence_packet_id         VARCHAR(200) NOT NULL
                        REFERENCES evidence_packets(evidence_packet_id),
    thesis_version_id          VARCHAR(200) NOT NULL
                        REFERENCES thesis_versions(thesis_version_id),
    challenge_result_id        VARCHAR(200) NOT NULL
                        REFERENCES challenge_results(challenge_result_id),
    portfolio_assessment_id    VARCHAR(200) NOT NULL
                        REFERENCES portfolio_assessments(portfolio_assessment_id),
    benchmark_id                VARCHAR(200) NOT NULL,
    staging_framework           VARCHAR(10000) NOT NULL,
    scenario_summary            VARCHAR(10000) NOT NULL,
    risk_summary                VARCHAR(10000) NOT NULL,
    decision_ask                 VARCHAR(10000) NOT NULL,
    model_independence           BOOLEAN NOT NULL CHECK (model_independence),
    created_at                    TIMESTAMPTZ NOT NULL,
    supersedes_packet_id          VARCHAR(200) NULL
                        REFERENCES decision_packets(decision_packet_id),
    payload                        JSONB NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'decision_packet_id' = decision_packet_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_decision_packets_thesis_version ON decision_packets (thesis_version_id);
CREATE INDEX idx_decision_packets_state ON decision_packets (recommendation_state);
CREATE INDEX idx_decision_packets_as_of ON decision_packets (as_of);
CREATE INDEX idx_decision_packets_supersedes ON decision_packets (supersedes_packet_id)
    WHERE supersedes_packet_id IS NOT NULL;
CREATE TRIGGER decision_packets_forbid_mutation
    BEFORE UPDATE OR DELETE ON decision_packets
    FOR EACH ROW EXECUTE FUNCTION _decision_engine_forbid_mutation();

COMMENT ON TABLE decision_packets IS
    'Top-level DecisionPacket (types.py:443). Append-only: supersede() '
    'INSERTs a new row with supersedes_packet_id set; the old row is '
    'never UPDATEd (enforced by decision_packets_forbid_mutation, not '
    'just convention). payload is authoritative for reconstruction.';
