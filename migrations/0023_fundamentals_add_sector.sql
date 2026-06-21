-- 0023_fundamentals_add_sector.sql
-- Adds sector to fundamentals.
-- EODHD /fundamentals returns General.Sector (e.g. "Financial Services");
-- sync_fundamentals captures it and propagate_sector_to_universe() copies the
-- latest non-blank value into universe.sector, the cache the portfolio
-- allocator's sector cap (constraints.apply_sector_cap) groups on. Without it
-- every symbol carries sector='' and the constraint waterfall cannot converge.
-- Mirrors 0002_fundamentals_add_market_cap.sql.
-- Applied via: mcp__supabase__apply_migration

ALTER TABLE fundamentals
    ADD COLUMN IF NOT EXISTS sector TEXT;
