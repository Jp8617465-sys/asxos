-- 0006_holding_news.sql
-- M14a: market news on current holdings, sourced from EODHD /news per symbol.
-- Deduplicates cross-holding stories on url (one row per article, symbols JSONB array).
-- Applied via: mcp__supabase__apply_migration

CREATE TABLE IF NOT EXISTS holding_news (
    id              SERIAL        PRIMARY KEY,
    url             TEXT          NOT NULL UNIQUE,
    title           TEXT          NOT NULL,
    published_at    DATE          NOT NULL,
    symbols         JSONB         NOT NULL DEFAULT '[]',  -- ["BHP.AU", "RIO.AU"]
    sentiment       TEXT          NOT NULL DEFAULT '',    -- positive | negative | neutral | ""
    content_snippet TEXT          NOT NULL DEFAULT '',    -- first 500 chars
    ingested_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS holding_news_pub_idx ON holding_news (published_at DESC);

-- Pruning note: add a DELETE WHERE published_at < NOW() - INTERVAL '7 days'
-- to jobs/ingest_news.py before the gather loop as lightweight cleanup.
-- No automatic pruning trigger — kept simple for v1.
