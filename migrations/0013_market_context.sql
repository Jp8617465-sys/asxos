-- M-Market-Context: daily market indicator snapshot + regime classification.
--
-- Design: append-only (no ON CONFLICT upsert). If a job crashes mid-run and
-- re-runs with corrected data, both rows are preserved. The `market_context_current`
-- view always returns the latest row per as_of (newest ingested_at wins).
-- Brief collectors and freshness gates MUST read from the view, not the base table.

CREATE TABLE market_context (
    ctx_id                  BIGSERIAL PRIMARY KEY,
    as_of                   DATE NOT NULL,

    -- Price / breadth (computed from prices table + EODHD index feeds)
    asx200_close            NUMERIC(18,6),
    asx200_daily_change_pct NUMERIC(18,6),
    pct_above_50d_ma        NUMERIC(18,6),   -- fraction of active symbols [0,1]
    pct_above_200d_ma       NUMERIC(18,6),   -- fraction of active symbols [0,1]
    net_new_highs_lows_10d  NUMERIC(18,6),   -- (10d highs - 10d lows) / count

    -- Volatility (from EODHD AVIX)
    avix                    NUMERIC(18,6),
    avix_5d_change_pct      NUMERIC(18,6),
    avix_30d_band_pos       NUMERIC(18,6),   -- position in 30d range [0,1]

    -- Macro (EODHD + FRED + RBA)
    rba_cash_rate           NUMERIC(18,6),   -- FRED AUCBCNTO (monthly)
    aud_usd                 NUMERIC(18,6),   -- EODHD AUDUSD.FOREX
    aus_10y_yield           NUMERIC(18,6),   -- FRED IRLTLT01AUM156N (monthly)
    iron_ore_62fe           NUMERIC(18,6),   -- EODHD commodity feed

    -- Credit / global (FRED)
    us_hy_oas               NUMERIC(18,6),   -- FRED BAMLH0A0HYM2 (basis points)
    us_10y_2y_spread        NUMERIC(18,6),   -- FRED T10Y2Y (percentage points)
    vix                     NUMERIC(18,6),   -- EODHD VIX.INDX

    -- Regime output
    regime_label            TEXT NOT NULL,
    regime_rationale        JSONB NOT NULL DEFAULT '[]',

    -- Partial-data audit trail (never mixes with classifier reasoning)
    -- Format: [{"source": "fred_hy_oas", "status": "fallback_used", "detail": "..."}]
    ingestion_warnings      JSONB NOT NULL DEFAULT '[]',

    ingested_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON market_context (as_of, ingested_at DESC);

-- All consumers (brief collectors, freshness gates) read from this view.
-- Returns one row per as_of — the most recently ingested one.
CREATE VIEW market_context_current AS
    SELECT DISTINCT ON (as_of) *
    FROM market_context
    ORDER BY as_of DESC, ingested_at DESC;
