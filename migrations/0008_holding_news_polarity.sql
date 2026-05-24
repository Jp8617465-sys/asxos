-- 0008_holding_news_polarity.sql
-- M14b REV-K: add numeric sentiment polarity to holding_news.
--
-- EODHD /news articles include a numeric sentiment dict:
--   {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}
-- This column stores the article-level polarity ∈ [-1, +1] approx.
-- NULL = no polarity in article (EODHD does not guarantee polarity on all articles).
--
-- signal_sentiment is aggregated nightly from this column:
--   INSERT INTO signal_sentiment SELECT sym, published_at, COUNT(*), AVG(sentiment_polarity) ...
--   FROM holding_news CROSS JOIN LATERAL jsonb_array_elements_text(symbols)
--   WHERE sentiment_polarity IS NOT NULL
--   GROUP BY sym, published_at
--
-- Applied via: mcp__supabase__apply_migration

ALTER TABLE holding_news
    ADD COLUMN IF NOT EXISTS sentiment_polarity NUMERIC(8,6) DEFAULT NULL;

COMMENT ON COLUMN holding_news.sentiment_polarity IS
    'Numeric article-level polarity from EODHD /news sentiment dict, ∈ [-1, +1] approx. NULL if absent.';
