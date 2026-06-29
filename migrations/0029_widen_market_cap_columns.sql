-- 0029_widen_market_cap_columns.sql
-- =====================================================================
-- NOT YET APPLIED. Widen the base market_cap columns from NUMERIC(18,6)
-- to NUMERIC(24,6). After applying via mcp__supabase__apply_migration:
-- bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed post-apply
-- count in supabase_migrations.schema_migrations (NOT a guessed +1).
-- =====================================================================
--
-- FORCED DEVIATION from CLAUDE.md non-negotiable #5 (NUMERIC(18,6) everywhere),
-- same accepted deviation as 0028: NUMERIC(18,6) caps at < 10^12, but market
-- caps approach/exceed it (and cents-denominated or aggregate values risk
-- overflow). 0028 widened the RESEARCH-STORE absolute-dollar columns but missed
-- these two BASE columns. The #5 intent (uniform fixed-precision Decimal, never
-- float) is preserved; only the integer width grows, ONLY for absolute-dollar
-- columns. 24,6 -> max ~10^18, far above any real market cap.
--
-- HIDDEN SECOND COLUMN: `universe.market_cap` (migrations/0001_initial.sql:33) is
-- ALSO NUMERIC(18,6) and is fed from `fundamentals.market_cap` by
-- propagate_market_cap_to_universe (asxos/ingestion/fundamentals.py). Widening
-- only `fundamentals` would leave the propagation step to overflow on write, so
-- BOTH are widened here in one migration.
--
-- UNLIKE 0028 (empty research tables = metadata-only), `fundamentals` and
-- `universe` are POPULATED, so PostgreSQL validates/rewrites each column. This is
-- NOT metadata-only. The conversion is value-preserving: (18,6) is a strict
-- subset of (24,6) (scale unchanged at 6, precision only grows), so no existing
-- value can fail validation and no fractional/integer truncation is possible.
--
-- FORWARD-ONLY: narrowing back to (18,6) only succeeds if no interim value
-- exceeds 10^12 — but storing such values is the whole point. To revert you must
-- first delete/clamp any out-of-range rows.
--
-- DEPENDENT VIEW (found by the live pre-apply catalog check — the static design
-- review missed it): the regular view public.stock_universe selects
-- universe.market_cap. PostgreSQL refuses ALTER COLUMN TYPE on a column a view
-- references ("cannot alter type of a column used by a view or rule"), so the view
-- is dropped, the columns altered, then the view recreated and re-granted — all in
-- one transaction (apply_migration is transactional, so this is atomic). The view
-- def and its grants (ALL to anon/authenticated/service_role; owner postgres) are
-- reproduced verbatim. fundamentals.market_cap has no dependents.
--
-- PRE-APPLY (see docs/design-med-2026-06-28.md Item 4):
--   1. Catalog-check for any view / expression index on these columns. (DONE:
--      only stock_universe on universe.market_cap; only pkey indexes.)
--   2. Capture before-image: SELECT max(market_cap), min(market_cap), count(*) ...
-- POST-APPLY: verify information_schema.columns shows numeric_precision=24,
--   numeric_scale=6 for both; confirm stock_universe + its grants survive; confirm
--   before/after max/min/count unchanged; then bump REQUIRED_MIGRATIONS.

DROP VIEW IF EXISTS public.stock_universe;

ALTER TABLE fundamentals ALTER COLUMN market_cap TYPE NUMERIC(24,6);
ALTER TABLE universe     ALTER COLUMN market_cap TYPE NUMERIC(24,6);

CREATE VIEW public.stock_universe AS
    SELECT symbol     AS ticker,
           name       AS company_name,
           sector,
           market_cap,
           true       AS is_active
    FROM universe;

GRANT ALL ON public.stock_universe TO anon, authenticated, service_role;
