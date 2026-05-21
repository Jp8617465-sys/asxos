-- 0002_fundamentals_add_market_cap.sql
-- Adds market_cap and shares_outstanding to fundamentals.
-- market_cap is required by the M5 feature engine for cross-sectional quintile ranking.
-- Applied via: mcp__supabase__apply_migration

ALTER TABLE fundamentals
    ADD COLUMN IF NOT EXISTS market_cap        NUMERIC(18,6),
    ADD COLUMN IF NOT EXISTS shares_outstanding BIGINT;
