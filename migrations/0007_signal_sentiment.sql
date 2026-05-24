-- M14b: daily aggregated sentiment per symbol, sourced from EODHD /sentiments.
-- Primary key (symbol, as_of) ensures idempotent upserts.
-- Applied via: mcp__supabase__apply_migration

CREATE TABLE IF NOT EXISTS signal_sentiment (
    symbol               TEXT         NOT NULL,
    as_of                DATE         NOT NULL,
    mention_count        INTEGER      NOT NULL,
    sentiment_normalised NUMERIC(8,6) NOT NULL,  -- range roughly [-1, +1]
    source_layer         TEXT         NOT NULL DEFAULT 'direct',
    source_confidence    NUMERIC(8,6) NOT NULL DEFAULT 1.0,
    source_metadata      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    ingested_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, as_of)
);

CREATE INDEX IF NOT EXISTS signal_sentiment_as_of_idx ON signal_sentiment (as_of DESC);
CREATE INDEX IF NOT EXISTS signal_sentiment_layer_idx ON signal_sentiment (source_layer, as_of DESC);
