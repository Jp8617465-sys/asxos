-- 0054_equity_valuation.sql
-- F-VAL/r0: the content-addressed valuation store.
--
-- Shape follows migrations/0050_research_registry.sql exactly: one authoritative
-- `payload JSONB` holding the complete model.model_dump(mode="json"); every other
-- column a NON-AUTHORITATIVE shadow for indexing only; reconstruction is
-- exclusively Model.model_validate(payload); append-only by trigger.
--
-- =====================================================================
-- WHY `terminal_convention` EXISTS FROM ROW ONE (James's ruling, 2026-09-08)
-- =====================================================================
-- Option A was chosen over adding the discriminator later, in this order of
-- weight:
--
--   (i)  Hash continuity is the property a content-addressed store exists to
--        provide. `ContentAddressedContract` hashes model_dump excluding only
--        content_hash, so adding a payload field later means an identical input
--        re-run after the change hashes DIFFERENTLY from the row already stored
--        — a discontinuity with no defect to point at. Spending that later to
--        save one column now is a bad trade at any discount rate.
--   (ii) The discriminator is load-bearing, not speculative: measurement shows
--        the terminal convention is worth roughly half of value while beta is
--        worth ~2.8 points of price. A cross-run comparison that does not group
--        by convention is meaningless.
--   (iii) Retroactive labelling is the only cost that cannot be undone. An
--        ADD COLUMN NOT NULL DEFAULT would label historical runs with a
--        convention they were never DECLARED under — true in substance,
--        invented in provenance.
--
-- A TEXT column with a CHECK, deliberately NOT a Postgres ENUM type: widening a
-- CHECK is one ALTER in one migration, whereas ALTER TYPE ... ADD VALUE cannot
-- run inside a transaction block and cannot be reverted.
--
-- One value is defined now. The application validator REFUSES an unknown value
-- rather than defaulting it, so a convention this migration has never heard of
-- fails loudly at both layers instead of silently becoming zero_excess.
--
-- `zero_excess`  ROE fades to Ke over the horizon; terminal value = book; no
--                perpetual excess return. The conservative convention, and the
--                only one Phase 1 ran.
--
-- The second convention (fading excess return with an explicit persistence
-- parameter) lands in Phase 2 as a universe-wide run ALONGSIDE zero_excess,
-- never instead of it. It widens this CHECK; it does not reshape the table.

-- =====================================================================
-- Scenario pre-registration: committed BEFORE any model run
-- =====================================================================
CREATE TABLE valuation_scenario_preregistrations (
    preregistration_id  VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(preregistration_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    registered_by       TEXT         NOT NULL CHECK (registered_by <> ''),
    registered_at       TIMESTAMPTZ  NOT NULL,
    applies_to          TEXT         NOT NULL CHECK (applies_to <> ''),
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'preregistration_id' = preregistration_id)
                        CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_valuation_prereg_registered ON valuation_scenario_preregistrations (registered_at DESC);

-- =====================================================================
-- Valuation runs. Failures are rows, not exceptions — a blocked run is a
-- record of what was missing, kept forever, exactly as research_runs keeps
-- outcome='fail'.
-- =====================================================================
CREATE TABLE valuation_runs (
    run_id              VARCHAR(200) PRIMARY KEY
                        CHECK (char_length(run_id) >= 1),
    content_hash        VARCHAR(64)  NOT NULL UNIQUE
                        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    symbol              TEXT         NOT NULL CHECK (symbol <> ''),
    as_of               DATE         NOT NULL,
    knowledge_cutoff    TIMESTAMPTZ  NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL,
    method              VARCHAR(40)  NOT NULL
                        CHECK (method IN ('residual_income')),
    -- The discriminator. See the header. Widen this CHECK to add a convention.
    terminal_convention VARCHAR(40)  NOT NULL
                        CHECK (terminal_convention IN ('zero_excess')),
    franking_convention VARCHAR(40)  NOT NULL
                        CHECK (franking_convention IN
                               ('pre_tax_no_franking_adjustment', 'grossed_up_resident')),
    outcome             VARCHAR(10)  NOT NULL CHECK (outcome IN ('valued', 'blocked')),
    -- A blocked run carries no value. Enforced here, not only in Python.
    value_per_share     NUMERIC(18,6) NULL CHECK (value_per_share IS NULL OR value_per_share >= 0),
    data_mode           VARCHAR(10)  NOT NULL CHECK (data_mode IN ('real', 'synthetic')),
    preregistration_id  VARCHAR(200) NOT NULL
                        REFERENCES valuation_scenario_preregistrations(preregistration_id),
    payload             JSONB        NOT NULL
                        CHECK (jsonb_typeof(payload) = 'object')
                        CHECK (payload->>'run_id' = run_id)
                        CHECK (payload->>'content_hash' = content_hash)
                        CHECK (payload->>'terminal_convention' = terminal_convention),
    CONSTRAINT valuation_runs_blocked_carries_no_value
        CHECK ((outcome = 'blocked' AND value_per_share IS NULL)
            OR (outcome = 'valued'  AND value_per_share IS NOT NULL)),
    CONSTRAINT valuation_runs_cutoff_matches_as_of
        CHECK (knowledge_cutoff::date = as_of)
);
CREATE INDEX idx_valuation_runs_symbol_asof ON valuation_runs (symbol, as_of DESC);
-- The comparison index: cross-convention queries are the reason (ii) above.
CREATE INDEX idx_valuation_runs_convention ON valuation_runs (terminal_convention, as_of DESC);

CREATE OR REPLACE FUNCTION _valuation_forbid_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'append-only: % on % is forbidden -- valuation records are immutable and '
        'content-addressed; register a new run instead of mutating an existing one',
        TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER valuation_prereg_forbid_mutation
    BEFORE UPDATE OR DELETE ON valuation_scenario_preregistrations
    FOR EACH ROW EXECUTE FUNCTION _valuation_forbid_mutation();

CREATE TRIGGER valuation_runs_forbid_mutation
    BEFORE UPDATE OR DELETE ON valuation_runs
    FOR EACH ROW EXECUTE FUNCTION _valuation_forbid_mutation();
