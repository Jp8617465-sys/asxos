-- 0028_widen_research_dollar_columns.sql
-- =====================================================================
-- APPLIED 2026-06-24. Widen the research-store ABSOLUTE-DOLLAR columns from
-- NUMERIC(18,6) to NUMERIC(24,6). After applying: bump REQUIRED_MIGRATIONS.
-- =====================================================================
--
-- FORCED DEVIATION from CLAUDE.md non-negotiable #5 (NUMERIC(18,6) everywhere),
-- discovered by validating on real data before populating:
--   NUMERIC(18,6) caps at < 10^12. Bank/large-cap RAW financial-statement line
--   items exceed it — CBA total assets ~A$1.3e12, JPMorgan ~US$4e12 — so an
--   18,6 column raises "numeric field overflow" on the first bank ingested.
-- The #5 intent (uniform fixed-precision Decimal, never float) is preserved;
-- only the integer width grows, and ONLY for absolute-dollar raw/derived columns.
-- RATIOS and PER-SHARE values (roe, roa, margins, book_value_ps, eps_ttm,
-- franking_pct, dividend_amount, target_price) stay NUMERIC(18,6) — they are small.
-- 24,6 -> max ~10^18, far above any real line item.
-- Tables are empty, so these ALTERs are metadata-only (no row rewrite).

-- rs_financial_statements — promoted absolute-dollar line items.
ALTER TABLE rs_financial_statements
    ALTER COLUMN total_revenue  TYPE NUMERIC(24,6),
    ALTER COLUMN net_income     TYPE NUMERIC(24,6),
    ALTER COLUMN total_assets   TYPE NUMERIC(24,6),
    ALTER COLUMN total_equity   TYPE NUMERIC(24,6),
    ALTER COLUMN total_debt     TYPE NUMERIC(24,6),
    ALTER COLUMN shares_diluted TYPE NUMERIC(24,6);

-- rs_fundamentals_pit — derived absolute-dollar factor inputs.
ALTER TABLE rs_fundamentals_pit
    ALTER COLUMN revenue_ttm        TYPE NUMERIC(24,6),
    ALTER COLUMN net_income_ttm     TYPE NUMERIC(24,6),
    ALTER COLUMN net_debt           TYPE NUMERIC(24,6),
    ALTER COLUMN total_equity       TYPE NUMERIC(24,6),
    ALTER COLUMN shares_outstanding TYPE NUMERIC(24,6);

-- rs_factor_scores — reconstructed market cap (shares × price) can approach 10^12.
ALTER TABLE rs_factor_scores
    ALTER COLUMN market_cap_aud TYPE NUMERIC(24,6);
