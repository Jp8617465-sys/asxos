-- 0044_fundamentals_pit_currency.sql
-- =====================================================================
--
-- Segment-valuation architecture doc (docs/proposals/
-- segment-valuation-portfolio-architecture-2026-08-18.md), defect D1: every
-- monetary column on rs_fundamentals_pit is a cross-currency ratio today —
-- 612 symbols report in a non-AUD currency (14 distinct currencies observed
-- live 2026-08-18), and nothing records which. This column is the storage-
-- layer half of the fix: it lets any future aggregation (L1 segment_metrics,
-- not yet built) group by currency and either convert or explicitly disclose
-- excluded non-AUD capitalisation, instead of silently mixing units the way
-- the naive aggregate did (Materials computed to a 560.75% earnings yield).
--
-- Deliberately NOT included here: full FX conversion. That needs a sourced
-- multi-currency rate feed (fx_rates today covers AUDUSD only) and is
-- out of scope for this migration — ratified as its own follow-up in the
-- architecture doc's §8.1.
-- =====================================================================

ALTER TABLE rs_fundamentals_pit
    ADD COLUMN IF NOT EXISTS currency TEXT;

COMMENT ON COLUMN rs_fundamentals_pit.currency IS
    'Reporting currency of the source statement, carried through from '
    'rs_financial_statements.currency. NULL for pre-existing rows written '
    'before this column existed, and for any statement whose own currency '
    'was unrecorded (102 symbols observed 2026-08-18). Any aggregate that '
    'sums monetary columns across rows MUST group by this column (or filter '
    'to a single value) rather than assume AUD.';
