-- Migration 0019: position_monitor_runs
-- Append-only log of weekly position monitor runs.
-- Each CLI invocation of `asx position monitor SYMBOL` inserts one row.
-- History is read via `asx position history SYMBOL`.

CREATE TABLE position_monitor_runs (
    run_id              BIGSERIAL PRIMARY KEY,
    symbol              TEXT NOT NULL,
    as_of               DATE NOT NULL,

    -- Price inputs (auto-fetched from EODHD)
    current_price       NUMERIC(18,6) NOT NULL,
    ma_50d              NUMERIC(18,6) NOT NULL,
    ma_200d             NUMERIC(18,6) NOT NULL,
    avg_weekly_move     NUMERIC(18,6) NOT NULL,

    -- Macro inputs (auto-fetched from FRED)
    vix_5d_move         NUMERIC(18,6) NOT NULL,
    hy_oas_5d_move      NUMERIC(18,6) NOT NULL,

    -- Sentiment inputs (manual prompts with last-run defaults)
    retail_ratio        NUMERIC(18,6) NOT NULL,
    news_sentiment      NUMERIC(18,6) NOT NULL,

    -- Optional position context (from thesis / holding_lots if available)
    stop_price          NUMERIC(18,6),

    -- Classifier outputs
    stage_label         TEXT NOT NULL,
    underlying_label    TEXT NOT NULL,
    weighted_movement   NUMERIC(18,6) NOT NULL,
    regime_label        TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON position_monitor_runs (symbol, as_of DESC);
