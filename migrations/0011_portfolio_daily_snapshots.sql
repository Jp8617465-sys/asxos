-- 0011_portfolio_daily_snapshots.sql
-- M-Thesis-0: daily wealth snapshot for V2 brief's YTD/MTD framing (spec D5).
--
-- Re-derivable from prices + holding_lots — NOT in scripts/backup_irreplaceable.sh.
--
-- One row per calendar date. Job runs weekdays only (UTC Sun-Thu 20:40) so
-- weekend rows are absent. YTD/MTD computations must handle gaps with
-- COALESCE/window functions, not assume row-per-day.
--
-- benchmark_xjo_close stores the raw AXJO.INDX price-only close.
-- benchmark_tr_level is computed from XJO close + trailing div yield per spec D4.
-- Both stay NULL until AXJO.INDX is added to the sync_prices ingestion pipeline.
-- The brief degrades gracefully to no-benchmark framing when these are NULL.

CREATE TABLE portfolio_daily_snapshots (
    as_of                  DATE          PRIMARY KEY,
    capital_aud            NUMERIC(18,6) NOT NULL,
    holdings_mv_aud        NUMERIC(18,6) NOT NULL,
    cash_aud               NUMERIC(18,6) NOT NULL,
    benchmark_xjo_close    NUMERIC(18,6),
    benchmark_tr_level     NUMERIC(18,6),
    trailing_div_yield_pct NUMERIC(8,6),
    holdings_count         INTEGER       NOT NULL,
    ingested_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_portfolio_daily_snapshots_asof
    ON portfolio_daily_snapshots (as_of DESC);
