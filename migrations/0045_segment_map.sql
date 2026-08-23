-- 0045_segment_map.sql
-- =====================================================================
--
-- Segment-valuation architecture doc (docs/proposals/
-- segment-valuation-portfolio-architecture-2026-08-18.md), defect D3, S3:
-- one versioned segment key. Verified live 2026-08-19: two sector
-- vocabularies coexist, AND the "GICS" column itself is not purely GICS --
-- rs_security_master.gics_sector holds a mix of canonical GICS names
-- (Materials, Financials, Health Care, ...) and Morningstar-style leakage
-- (Basic Materials, Financial Services, Healthcare, Technology, "Financial"
-- (truncated), "Industrial Goods", "Other") alongside 752 NULL rows (17%).
-- universe.sector is pure Morningstar with no GICS at all. Naive
-- coalesce(gics_sector, universe.sector) therefore produces duplicate
-- buckets for the same real sector (e.g. both "Financials" and "Financial
-- Services" in one aggregate).
--
-- This table is the single normalized source: one row per symbol per
-- taxonomy version, resolved through asxos/domain/research/segment_map.py's
-- alias table (GICS-preferred, Morningstar variants mapped to their GICS
-- equivalent, "Other"/blank left unresolved rather than faked).
-- =====================================================================

CREATE TABLE IF NOT EXISTS segment_map (
    symbol           TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL DEFAULT 'gics_alias_v1',
    segment_key      TEXT,                      -- NULL when unresolved (source='unresolved')
    source           TEXT NOT NULL,              -- 'gics' | 'morningstar_alias' | 'unresolved'
    effective_from   DATE NOT NULL,
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, taxonomy_version)
);

CREATE INDEX IF NOT EXISTS idx_segment_map_key
    ON segment_map(taxonomy_version, segment_key);

COMMENT ON TABLE segment_map IS
    'D3/S3: one versioned, alias-normalized segment key per symbol. '
    'Any aggregate that groups by sector should join here rather than '
    'reading universe.sector or rs_security_master.gics_sector directly, '
    'both of which carry the duplicate-vocabulary and unresolved-gap '
    'problems this table exists to fix.';
