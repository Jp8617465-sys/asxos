-- 0047_brief_section_gold.sql
-- =====================================================================
--
-- APPLIED 2026-08-24 — governor grant. Ledger name `brief_section_gold`,
-- version `20260824002827` (asx-portfolio-os / gxjqezqndltaelmyctnl).
--
-- Stage 2 gold artefacts for the live daily brief (asxos.brief). Status
-- vocabulary is SectionStatus: FRESH / STALE / MISSING / EMPTY — matching
-- asxos.brief.section.SectionStatus, not the dark V2 ok/degraded set.
--
-- Rows per as_of: the seven SECTION_ORDER names (prices, jobs, discipline,
-- outcome, regulatory, news, portfolio) plus `header` (scalars) and
-- `deltas` (BookDelta codec).
-- =====================================================================

CREATE TABLE IF NOT EXISTS brief_section_gold (
    as_of        DATE NOT NULL,
    section_name TEXT NOT NULL,
    status       TEXT NOT NULL
                 CHECK (status IN ('FRESH', 'STALE', 'MISSING', 'EMPTY')),
    computed_at  TIMESTAMPTZ,
    source       TEXT NOT NULL DEFAULT '',
    error        TEXT,
    payload      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (as_of, section_name),
    CHECK (status <> 'MISSING' OR (error IS NOT NULL AND btrim(error) <> ''))
);

COMMENT ON TABLE brief_section_gold IS
    'Per-as_of gold artefacts for the live daily brief. Seven SECTION_ORDER names plus header and deltas. Status is FRESH/STALE/MISSING/EMPTY matching asxos.brief.section.SectionStatus.';
