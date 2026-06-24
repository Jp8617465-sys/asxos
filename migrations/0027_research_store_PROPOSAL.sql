-- 0027_research_store_PROPOSAL.sql
-- =====================================================================
-- PROPOSAL — NOT APPLIED. Do NOT run via mcp__supabase__apply_migration
-- until reviewed and the EODHD ingestion design is agreed. No ingestion
-- code exists for these tables yet. This file is the reviewable DDL that
-- accompanies docs/research/research-store-schema.md.
-- =====================================================================
--
-- The research store is the point-in-time, survivorship-free foundation for
-- long-horizon factor research (Layer-1 alpha). It is SEPARATE from the
-- production tables (signals / portfolio / theses). The single discipline that
-- makes it leak-free: every fundamentals/factor row carries BOTH the data date
-- (`as_of`) AND the date it became publicly usable (`knowledge_date`). Research
-- queries filter on `knowledge_date <= test_date` — never on `as_of`.
--
-- EODHD availability VERIFIED 2026-06-22 (read-only probe): Financials 35yr,
-- ROE/margins/revenue in Highlights, delisted-symbol list (1,986), dividends,
-- splits, shares-outstanding history. GAPS to resolve before ingestion:
--   * index-membership history — source unknown (NOT in the fundamentals API)
--   * franking_pct in EODHD AU dividends — field presence unverified
--   * statement filing_date — must exist for PIT lag; verify per-statement
-- NUMERIC(18,6) on every monetary/statistical column (house convention).

-- 1. Security master — one row per security EVER listed (survivorship-free).
CREATE TABLE IF NOT EXISTS rs_security_master (
    symbol          TEXT PRIMARY KEY,          -- e.g. CBA.AU
    name            TEXT,
    exchange        TEXT NOT NULL DEFAULT 'AU',
    currency        TEXT,
    security_type   TEXT,                       -- Common Stock | FUND | ETF | ...
    gics_sector     TEXT,
    gics_industry   TEXT,
    isin            TEXT,
    listed_date     DATE,
    delisted_date   DATE,                       -- NULL = currently listed
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    source          TEXT NOT NULL DEFAULT 'eodhd',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rs_secmaster_active ON rs_security_master(is_active);

-- 2. Corporate actions — splits + dividends (+ AU franking where available).
CREATE TABLE IF NOT EXISTS rs_corporate_actions (
    symbol          TEXT NOT NULL,
    ex_date         DATE NOT NULL,
    action_type     TEXT NOT NULL,              -- 'split' | 'dividend'
    split_ratio     NUMERIC(18,6),              -- e.g. 2.0 for 2:1 (split only)
    dividend_amount NUMERIC(18,6),              -- per-share (dividend only)
    franking_pct    NUMERIC(18,6),              -- AU: 0..100 if available
    pay_date        DATE,
    record_date     DATE,
    source          TEXT NOT NULL DEFAULT 'eodhd',
    PRIMARY KEY (symbol, ex_date, action_type)
);

-- 3. Raw historical financial statements (the source for PIT factors).
--    `filing_date` is the POINT-IN-TIME key — when the statement was disclosed.
CREATE TABLE IF NOT EXISTS rs_financial_statements (
    symbol          TEXT NOT NULL,
    period_end      DATE NOT NULL,              -- statement period end (e.g. 2025-06-30)
    period_type     TEXT NOT NULL,              -- 'yearly' | 'quarterly'
    statement_type  TEXT NOT NULL,              -- 'balance_sheet' | 'income' | 'cash_flow'
    filing_date     DATE,                       -- disclosure date (PIT key); fallback = period_end + lag
    currency        TEXT,
    -- promoted line items for fast factor calc; full payload in line_items
    total_revenue   NUMERIC(18,6),
    net_income      NUMERIC(18,6),
    total_assets    NUMERIC(18,6),
    total_equity    NUMERIC(18,6),
    total_debt      NUMERIC(18,6),
    shares_diluted  NUMERIC(18,6),
    line_items      JSONB NOT NULL DEFAULT '{}'::jsonb,
    source          TEXT NOT NULL DEFAULT 'eodhd',
    PRIMARY KEY (symbol, period_end, period_type, statement_type)
);
CREATE INDEX IF NOT EXISTS idx_rs_fin_filing ON rs_financial_statements(symbol, filing_date);

-- 4. Point-in-time fundamentals — derived factor INPUTS, valid from knowledge_date.
CREATE TABLE IF NOT EXISTS rs_fundamentals_pit (
    symbol              TEXT NOT NULL,
    as_of               DATE NOT NULL,          -- statement period end the snapshot summarises
    knowledge_date      DATE NOT NULL,          -- when it became usable (= filing_date or lagged) — PIT KEY
    book_value_ps       NUMERIC(18,6),
    eps_ttm             NUMERIC(18,6),
    revenue_ttm         NUMERIC(18,6),
    net_income_ttm      NUMERIC(18,6),
    roe                 NUMERIC(18,6),
    roa                 NUMERIC(18,6),
    gross_margin        NUMERIC(18,6),
    operating_margin    NUMERIC(18,6),
    net_debt            NUMERIC(18,6),
    total_equity        NUMERIC(18,6),
    shares_outstanding  NUMERIC(18,6),
    dividend_ttm        NUMERIC(18,6),
    franking_avg_pct    NUMERIC(18,6),
    source              TEXT NOT NULL DEFAULT 'eodhd_derived',
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, knowledge_date)
);
CREATE INDEX IF NOT EXISTS idx_rs_fund_pit_know ON rs_fundamentals_pit(knowledge_date);

-- 5. Computed factor scores — the Layer-1 alpha input (cross-sectional, PIT).
--    Sector-relative z-scores; market_cap reconstructed (shares × price) at compute time.
CREATE TABLE IF NOT EXISTS rs_factor_scores (
    symbol              TEXT NOT NULL,
    as_of               DATE NOT NULL,          -- the cross-section date (knowledge-date-safe)
    factor_set_version  TEXT NOT NULL,          -- e.g. 'fs_v1'
    sector              TEXT,
    market_cap_aud      NUMERIC(18,6),
    value_score         NUMERIC(18,6),          -- earnings/book/FCF yield blend (z, sector-neutral)
    quality_score       NUMERIC(18,6),          -- ROE / low-leverage / margin stability (z)
    momentum_score      NUMERIC(18,6),          -- 6-12m residual momentum (z)
    low_vol_score       NUMERIC(18,6),
    yield_score         NUMERIC(18,6),          -- grossed-up franked yield (z)
    composite_score     NUMERIC(18,6),
    n_factors_present   INTEGER NOT NULL DEFAULT 0,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, as_of, factor_set_version)
);
CREATE INDEX IF NOT EXISTS idx_rs_factor_asof ON rs_factor_scores(as_of, factor_set_version);

-- 6. Index membership history — SOURCE TBD (likely a real gap; see doc §open).
CREATE TABLE IF NOT EXISTS rs_index_membership (
    index_code      TEXT NOT NULL,              -- e.g. 'XJO' (ASX200)
    symbol          TEXT NOT NULL,
    effective_from  DATE NOT NULL,
    effective_to    DATE,                       -- NULL = current
    source          TEXT,
    PRIMARY KEY (index_code, symbol, effective_from)
);

-- 7. Analyst estimates — snapshot-only (EODHD provides current target, sparse AU history).
CREATE TABLE IF NOT EXISTS rs_estimates (
    symbol              TEXT NOT NULL,
    as_of               DATE NOT NULL,
    target_price        NUMERIC(18,6),
    eps_estimate_cy     NUMERIC(18,6),
    eps_estimate_ny     NUMERIC(18,6),
    n_analysts          INTEGER,
    source              TEXT NOT NULL DEFAULT 'eodhd',
    PRIMARY KEY (symbol, as_of)
);
