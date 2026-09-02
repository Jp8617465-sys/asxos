-- 0049_pit_knowledge_tier.sql
-- =====================================================================
--
-- APPLIED to production 2026-09-02 as ledger name `pit_knowledge_tier`, under
-- James's in-session I5 grant ("I authorise you to apply the migrations",
-- 2026-09-02; Amendment H click H-18). Verified after apply: column TEXT,
-- CHECK constraint present, index present, every pre-existing row NULL.
--
-- Stage 1 exit gate, clause (1): "one historical decision date can be replayed
-- using ONLY facts with known_at <= cutoff" (target-architecture.md §15).
--
-- That predicate is only meaningful if `knowledge_date` records something we
-- actually knew. Today it records two different things under one column:
--
--   * a real disclosure date the vendor reported and the PIT guard accepted
--     (`derive_knowledge_date_tiered` -> "filed"), and
--   * `period_end + 75 days` when no usable disclosure date existed
--     (-> "estimated") — a convention about how long filing usually takes,
--     not an event anyone observed.
--
-- The second kind can even land in the FUTURE. Measured live 2026-09-02:
-- 326 of 54,160 rows carry knowledge_date = 2026-09-13, every one of them
-- period_end 2026-06-30 + 75d, with report_date NULL and filing_date equal to
-- period_end (so the guard correctly rejected it).
--
-- NOTE, because the previously recorded diagnosis is wrong and someone will
-- read it: target-architecture.md's A.0 note attributes these rows to the
-- derive step "falling back to the vendor's report_date", report_date being a
-- scheduled announcement date. That is not the mechanism. The guard already
-- excludes any date > as_of by construction, and in every observed case
-- report_date is NULL. The cause is the synthetic lag fallback.
--
-- Those rows are harmless to today's readers, which all filter
-- `knowledge_date <= as_of` and therefore cannot see them. They are not
-- harmless to a replay, which could declare itself clean while resting on a
-- date nobody ever observed.
--
-- This migration records the distinction. It deliberately does NOT clamp or
-- delete anything: clamping an estimated date back to as_of would assert we
-- knew something earlier than we did, which is precisely the look-ahead leak
-- the PIT guard exists to prevent.
--
-- Backfill: pre-existing rows are NULL — honestly "not yet classified" rather
-- than a guess. The weekly `derive_fundamentals_pit` job upserts on
-- (symbol, knowledge_date) and will stamp the tier on every row it touches,
-- so the NULLs drain as the job runs. A replay that requires provenance must
-- treat NULL as "unknown", never as "filed".
-- =====================================================================

ALTER TABLE rs_fundamentals_pit
    ADD COLUMN IF NOT EXISTS knowledge_tier TEXT;

ALTER TABLE rs_fundamentals_pit
    DROP CONSTRAINT IF EXISTS rs_fundamentals_pit_knowledge_tier_check;

ALTER TABLE rs_fundamentals_pit
    ADD CONSTRAINT rs_fundamentals_pit_knowledge_tier_check
    CHECK (knowledge_tier IS NULL OR knowledge_tier IN ('filed', 'estimated'));

COMMENT ON COLUMN rs_fundamentals_pit.knowledge_tier IS
    'Provenance of knowledge_date. filed = a real disclosure date the vendor '
    'reported and the PIT guard accepted. estimated = no usable disclosure date '
    'existed, so knowledge_date is period_end + lag_days — a convention, not an '
    'observed event, and it may fall in the future. NULL = written before this '
    'column existed and not yet re-derived. A point-in-time replay that claims '
    'to use only known facts MUST require ''filed''; NULL is not ''filed''.';

-- Replay reads filter on (knowledge_date, knowledge_tier) together.
CREATE INDEX IF NOT EXISTS idx_rs_fundamentals_pit_knowledge_tier
    ON rs_fundamentals_pit (knowledge_tier, knowledge_date);
