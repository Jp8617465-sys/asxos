-- 0044_fundamentals_pit_currency.sql
-- =====================================================================
-- APPLIED TO PRODUCTION 2026-08-21 (schema_migrations 96 -> 97).
-- REQUIRED_MIGRATIONS was bumped 96 -> 97 in asxos/api/main.py in the same
-- sitting, to the OBSERVED count.
--
-- *** DO NOT RE-APPLY. ***  The DDL is idempotent (ADD COLUMN IF NOT EXISTS)
-- but the COMMENT ON COLUMN below is NOT: re-running this file would overwrite
-- the live comment and add a second schema_migrations row. Neither backstop
-- catches that -- the API's startup guard compares `count < REQUIRED_MIGRATIONS`
-- and so misses ahead-drift (docs/audit-2026-06-27.md), and
-- .github/workflows/migration-integration.yml only executes the 0043
-- behavioural contract, never this file.
--
-- Segment-valuation architecture doc (docs/proposals/
-- segment-valuation-portfolio-architecture-2026-08-18.md), defect D1: every
-- monetary column on rs_fundamentals_pit is a cross-currency ratio today --
-- 612 symbols report in a non-AUD currency (14 distinct currencies observed
-- live 2026-08-18), and nothing records which. This column is the storage-
-- layer half of the fix: it lets any future aggregation (L1 segment_metrics,
-- not yet built) group by currency and either convert or explicitly disclose
-- excluded non-AUD capitalisation, instead of silently mixing units the way
-- the naive aggregate did (Materials computed to a 560.75% earnings yield).
--
-- NOTE on the two figures above (612 / 14): segval-live-validation-2026-08-20.md
-- Patch 0 Edit 1 proposes 530 / 20, scoped to period_type='yearly'. The session
-- that applied this migration did NOT independently measure them and has left
-- them unchanged rather than assert an unverified number -- which is the same
-- error class as the "102" figure this file previously carried. Edit 1 remains
-- undischarged; SQL `--` comments never reach the database, so applying could
-- never have fixed them.
--
-- Deliberately NOT included here: full FX conversion. That needs a sourced
-- multi-currency rate feed (fx_rates today covers AUDUSD only) and is
-- out of scope for this migration -- ratified as its own follow-up in the
-- architecture doc's Section 8.1.
-- =====================================================================

ALTER TABLE rs_fundamentals_pit
    ADD COLUMN IF NOT EXISTS currency TEXT;

-- The string below is the text ACTUALLY APPLIED, transcribed back from the live
-- database via col_description('rs_fundamentals_pit'::regclass, ...) rather than
-- re-drafted. Do not "tidy" it without re-reading the database first.
COMMENT ON COLUMN rs_fundamentals_pit.currency IS
    'Reporting currency of the source statement, carried through from '
    'rs_financial_statements.currency. NULL for pre-existing rows written '
    'before this column existed, and for any statement whose own currency '
    'was unrecorded (947 symbols measured 2026-08-21). Any aggregate that '
    'sums monetary columns across rows MUST group by this column (or filter '
    'to a single value) rather than assume AUD.';

-- AS-APPLIED DIVERGES FROM AS-RATIFIED, recorded rather than absorbed:
-- segval-live-validation-2026-08-20.md Patch 0 Edit 2 ruled "deliberately no
-- count in the COMMENT", reasoning that any statement-level count answers a
-- different question than the comment asks. A count was nevertheless applied.
-- 947 is measured correctly (distinct symbols in rs_financial_statements with
-- NULL/blank currency, 2026-08-21) but it describes symbols with AT LEAST ONE
-- unusable yearly statement row -- NOT symbols whose PIT currency ends up NULL,
-- because compute_pit_factors falls back income->balance. It is a strict
-- superset. A future re-issue should drop the count per Edit 2's reasoning;
-- this note exists so that reasoning is not silently lost.
