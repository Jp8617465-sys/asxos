-- 0001_initial.sql
-- Full initial schema for asxos.
-- Applied via: mcp__supabase__apply_migration (never psql directly in production)
-- NUMERIC(18,6) on every monetary or statistical column.
-- No user_id anywhere — single-user system.
--
-- Drops old-system tables that exist on this reused Supabase project before
-- recreating them with the correct schema. Old data is from the broken previous
-- system and will be re-ingested fresh.

-- ============================================================
-- Drop old-system views and tables (wrong schemas)
-- ============================================================
DROP VIEW IF EXISTS stock_universe CASCADE;
DROP VIEW IF EXISTS v_current_models CASCADE;
DROP VIEW IF EXISTS current_holdings CASCADE;

DROP TABLE IF EXISTS signals         CASCADE;
DROP TABLE IF EXISTS model_versions  CASCADE;
DROP TABLE IF EXISTS fundamentals    CASCADE;
DROP TABLE IF EXISTS prices          CASCADE;
DROP TABLE IF EXISTS universe        CASCADE;
DROP TABLE IF EXISTS screening_rules CASCADE;

-- ============================================================
-- universe
-- ============================================================
CREATE TABLE universe (
    symbol          TEXT        PRIMARY KEY,
    name            TEXT        NOT NULL DEFAULT '',
    sector          TEXT        NOT NULL DEFAULT '',
    currency        TEXT        NOT NULL DEFAULT 'AUD',
    market_cap      NUMERIC(18,6),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- prices
-- ============================================================
CREATE TABLE prices (
    symbol          TEXT        NOT NULL REFERENCES universe(symbol),
    dt              DATE        NOT NULL,
    open            NUMERIC(18,6),
    high            NUMERIC(18,6),
    low             NUMERIC(18,6),
    close           NUMERIC(18,6) NOT NULL,
    volume          BIGINT,
    adj_close       NUMERIC(18,6),
    PRIMARY KEY (symbol, dt)
);

CREATE INDEX prices_dt_idx ON prices (dt DESC);

-- ============================================================
-- fundamentals
-- ============================================================
CREATE TABLE fundamentals (
    symbol          TEXT        NOT NULL REFERENCES universe(symbol),
    as_of           DATE        NOT NULL,
    pe_ratio        NUMERIC(18,6),
    pb_ratio        NUMERIC(18,6),
    eps             NUMERIC(18,6),
    dividend_yield  NUMERIC(18,6),
    franking_pct    NUMERIC(18,6),   -- 0–100
    roe             NUMERIC(18,6),
    debt_to_equity  NUMERIC(18,6),
    revenue         NUMERIC(18,6),
    net_income      NUMERIC(18,6),
    PRIMARY KEY (symbol, as_of)
);

-- ============================================================
-- model_versions
-- ============================================================
CREATE TABLE model_versions (
    id              SERIAL      PRIMARY KEY,
    model           TEXT        NOT NULL,   -- e.g. 'model_a'
    version         TEXT        NOT NULL,   -- e.g. 'v1_5'
    roc_auc         NUMERIC(18,6),
    trained_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN     NOT NULL DEFAULT FALSE,
    notes           TEXT        NOT NULL DEFAULT '',
    UNIQUE (model, version)
);

-- Only one active version per model at a time
CREATE UNIQUE INDEX model_versions_one_active_idx
    ON model_versions (model) WHERE is_active;

-- ============================================================
-- signals
-- ============================================================
CREATE TABLE signals (
    model           TEXT        NOT NULL,
    model_version   TEXT        NOT NULL,
    symbol          TEXT        NOT NULL REFERENCES universe(symbol),
    as_of           DATE        NOT NULL,
    prob_up         NUMERIC(18,6) NOT NULL,
    expected_return NUMERIC(18,6) NOT NULL,
    signal_label    TEXT        NOT NULL,   -- STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL
    confidence      INTEGER     NOT NULL,   -- 0–100
    regime          TEXT        NOT NULL DEFAULT 'neutral',
    shap_factors    JSONB       NOT NULL DEFAULT '{}',
    PRIMARY KEY (model, model_version, symbol, as_of),
    FOREIGN KEY (model, model_version) REFERENCES model_versions(model, version)
);

CREATE INDEX signals_as_of_idx     ON signals (as_of DESC);
CREATE INDEX signals_symbol_idx    ON signals (symbol, as_of DESC);
CREATE INDEX signals_label_idx     ON signals (signal_label, as_of DESC);
CREATE INDEX signals_shap_gin_idx  ON signals USING gin (shap_factors);

-- ============================================================
-- holding_lots  (lot-level positions for CGT)
-- ============================================================
CREATE TABLE holding_lots (
    id                      SERIAL      PRIMARY KEY,
    symbol                  TEXT        NOT NULL REFERENCES universe(symbol),
    acquired_at             DATE        NOT NULL,
    quantity                NUMERIC(18,6) NOT NULL,
    cost_base_normal        NUMERIC(18,6) NOT NULL,   -- AUD, s 110-25 ITAA97
    cost_base_div296        NUMERIC(18,6) NOT NULL,   -- AUD, reduced by concessional contributions
    account_type            TEXT        NOT NULL DEFAULT 'individual',  -- individual | smsf
    disposed_at             DATE,
    disposal_proceeds       NUMERIC(18,6),
    broker_ref              TEXT        NOT NULL DEFAULT '',
    notes                   TEXT        NOT NULL DEFAULT '',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX holding_lots_symbol_idx ON holding_lots (symbol, acquired_at);
CREATE INDEX holding_lots_held_idx   ON holding_lots (disposed_at) WHERE disposed_at IS NULL;

-- ============================================================
-- current_holdings  (view — excludes disposed lots)
-- ============================================================
CREATE VIEW current_holdings AS
    SELECT
        hl.id,
        hl.symbol,
        hl.acquired_at,
        hl.quantity,
        hl.cost_base_normal,
        hl.cost_base_div296,
        hl.account_type,
        hl.broker_ref,
        hl.notes
    FROM holding_lots hl
    WHERE hl.disposed_at IS NULL;

-- ============================================================
-- decisions  (journal)
-- ============================================================
CREATE TABLE decisions (
    id              SERIAL      PRIMARY KEY,
    symbol          TEXT,                   -- NULL for portfolio-level decisions
    decision_date   DATE        NOT NULL,
    action          TEXT        NOT NULL,   -- BUY | SELL | HOLD | REVIEW | NOTE
    rationale       TEXT        NOT NULL DEFAULT '',
    signal_ref      TEXT,                   -- model/version/as_of for traceability
    tax_note        TEXT        NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX decisions_date_idx ON decisions (decision_date DESC);

-- ============================================================
-- regulatory_events
-- ============================================================
CREATE TABLE regulatory_events (
    id              SERIAL      PRIMARY KEY,
    source          TEXT        NOT NULL,   -- ASIC | RBA | ATO | ASX
    published_at    DATE        NOT NULL,
    title           TEXT        NOT NULL,
    url             TEXT        NOT NULL DEFAULT '',
    summary         TEXT        NOT NULL DEFAULT '',
    relevance_tags  JSONB       NOT NULL DEFAULT '[]',
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, url)
);

CREATE INDEX regulatory_events_pub_idx ON regulatory_events (published_at DESC);
CREATE INDEX regulatory_events_src_idx ON regulatory_events (source, published_at DESC);

-- ============================================================
-- job_runs  (completion tracking, UPSERT on job_name + as_of)
-- ============================================================
CREATE TABLE job_runs (
    id              SERIAL      PRIMARY KEY,
    job_name        TEXT        NOT NULL,
    as_of           DATE        NOT NULL,
    status          TEXT        NOT NULL,   -- success | failure | skipped
    duration_ms     INTEGER,
    rows_written    INTEGER,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    UNIQUE (job_name, as_of)
);

CREATE INDEX job_runs_name_idx ON job_runs (job_name, as_of DESC);

-- ============================================================
-- screening_rules
-- ============================================================
CREATE TABLE screening_rules (
    id              SERIAL      PRIMARY KEY,
    name            TEXT        NOT NULL UNIQUE,
    source_method   TEXT        NOT NULL,   -- shap_threshold | surrogate_tree | curated_composite
    rule_json       JSONB       NOT NULL,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    description     TEXT        NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
