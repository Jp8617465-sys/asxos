-- 0031_thesis_disposal_return_and_benchmark_seed.sql
-- Core value loop, Stage 1 (benchmark-tracked performance + thesis post-mortem).
--
-- Two additive changes, zero risk to existing rows:
--
--   1. thesis_revisions.disposal_return_vs_xjo_pct — at thesis close, the stock's
--      holding-period return minus the XJO return over the same window. Makes the
--      post-mortem loop concrete ("BHP closed +12% vs XJO +6%"). Populated by the
--      benchmark-performance-analyst agent / close workflow; NULL until a thesis
--      is closed with benchmark data available.
--
--   2. Seed AXJO.INDX (S&P/ASX 200 price index) into `universe` so sync_prices
--      Phase 1.5 can ingest it (the prices→universe FK requires the row) and
--      snapshot_portfolio can populate benchmark_xjo_close / benchmark_tr_level.
--      Seeded is_active = FALSE ON PURPOSE: an index is a benchmark REFERENCE, not
--      a tradeable-equity universe member. Every equity consumer filters
--      `WHERE is_active` (generate_signals, sync_fundamentals, retrain_model_a,
--      refresh_universe's delisting sweep), so is_active = FALSE keeps the index
--      out of the ML/equity paths with no code changes there. sync_prices picks it
--      up via a dedicated `symbol LIKE '%.INDX'` query (get_index_symbols).
--
-- Applied via: mcp__supabase__apply_migration (project gxjqezqndltaelmyctnl).
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
-- SELECT count(*) FROM supabase_migrations.schema_migrations.

ALTER TABLE thesis_revisions
    ADD COLUMN IF NOT EXISTS disposal_return_vs_xjo_pct NUMERIC(18,6);

INSERT INTO universe (symbol, name, sector, currency, is_active)
VALUES ('AXJO.INDX', 'S&P/ASX 200', 'Index', 'AUD', FALSE)
ON CONFLICT (symbol) DO NOTHING;
