-- 0042_rules_integrity.sql
-- Rules-integrity build (finance red-team 2026-08-08; decisions D1/D2/D4, R8 per D7).
--   D4/R9: theses.attestation ('placeholder'|'underwritten') + basis; ALL 13 rows
--          grandfathered 'placeholder' (governor ruling, D4).
--   D1/R2: thesis_conditions + thesis_condition_events replace the write-once
--          theses.invalidation_conditions JSONB (dropped below). Per-condition
--          trigger_semantics; ESS lock on holding_lots.
--   D2/R1: attestation-gated ladder CHECKs (v1 long-only formalisation of the
--          migration 0012:92-93 deferred TODO).
-- NO interaction with the 0034/0036 governance triggers: they are
-- BEFORE UPDATE OF governance_status only; nothing here touches that column
-- and the new tables carry no governance triggers. No governance_events rows
-- are required by anything in this migration.
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
-- count (expected 96).
-- Scheduling for the R8 sweep lives in .github/workflows/weekly-research.yml
-- (NOT render.yaml — Render is being decommissioned).

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────
-- Guard: this backfill was written against the exact 2026-08-08 packet
-- state (13 theses; HUBS thesis_id=2 with 4 conditions; ESPP lot id=1).
-- Hard-fail if reality has moved (CLAUDE.md #10) — re-derive, don't guess.
-- ─────────────────────────────────────────────────────────────────────────
DO $$
DECLARE n INT;
BEGIN
    SELECT count(*) INTO n FROM theses;
    IF n <> 13 THEN
        RAISE EXCEPTION '0042 backfill expects exactly 13 theses rows, found % — re-verify before applying', n;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM theses
        WHERE thesis_id = 2 AND symbol = 'HUBS.NYSE'
          AND jsonb_array_length(invalidation_conditions) = 4
    ) THEN
        RAISE EXCEPTION '0042 backfill expects thesis 2 = HUBS.NYSE with 4 invalidation conditions — re-verify';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM holding_lots
        WHERE id = 1 AND broker_ref = 'ESPP-2026-05-31' AND disposed_at IS NULL
    ) THEN
        RAISE EXCEPTION '0042 backfill expects open ESPP lot id=1 (ESPP-2026-05-31) — re-verify';
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────
-- 1. Attestation (D4/R9). DEFAULT 'placeholder' is deliberate and permanent:
--    new rules are BORN placeholder — the exact inverse of the born-approved
--    governance_status default the red team condemned (register #2).
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE theses
    ADD COLUMN attestation TEXT NOT NULL DEFAULT 'placeholder'
        CHECK (attestation IN ('placeholder', 'underwritten')),
    ADD COLUMN attestation_basis TEXT,
    ADD CONSTRAINT theses_underwritten_requires_basis
        CHECK (attestation = 'placeholder'
               OR (attestation_basis IS NOT NULL AND btrim(attestation_basis) <> ''));

COMMENT ON COLUMN theses.attestation IS
    'placeholder = numbers not underwritten by James; barred from action-framed '
    'surfaces and alert action-verbs (service layer, D4/R9). underwritten = '
    'James attests the ladder; the theses_ladder_coherent_long_v1 CHECK fires '
    'on the attesting UPDATE, so an incoherent ladder cannot be attested. '
    'All 13 pre-0042 rows grandfathered to placeholder per governor ruling D4 '
    '(2026-08-08). Transition ONLY via theses service attest_thesis().';

-- ─────────────────────────────────────────────────────────────────────────
-- 2. Ladder CHECKs (D2/R1) — v1 LONG-ONLY (0012:92-93 TODO formalised).
--    Gated on attestation (KD-4): placeholders exempt; attesting re-validates.
--    Strict band (lower < upper): E02 shows point bands are a systematic
--    authoring artifact, not intent. A future short/direction column must
--    replace _long_v1 with direction-aware comparisons.
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE theses
    ADD CONSTRAINT theses_ladder_coherent_long_v1 CHECK (
        attestation = 'placeholder' OR (
            (stop_price IS NULL OR entry_band_lower IS NULL OR stop_price < entry_band_lower)
            AND (entry_band_lower IS NULL OR entry_band_upper IS NULL OR entry_band_lower < entry_band_upper)
            AND (entry_band_upper IS NULL OR target_price IS NULL OR entry_band_upper < target_price)
            AND (stop_price IS NULL OR target_price IS NULL OR stop_price < target_price)
        )
    );
-- (existing weaker theses_entry_band_order (lower <= upper, all rows) is kept.)

-- ─────────────────────────────────────────────────────────────────────────
-- 3. thesis_conditions — current per-condition state + AUTHORING-TIME parse
--    baseline ("what the parser will enforce", D1/R2). The daily job
--    evaluates the STORED baseline, never re-parses text at runtime.
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE thesis_conditions (
    condition_id        BIGSERIAL   PRIMARY KEY,
    thesis_id           BIGINT      NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    ordinal             SMALLINT    NOT NULL,          -- authored 1..n display order
    condition_text      TEXT        NOT NULL CHECK (btrim(condition_text) <> ''),
    trigger_semantics   TEXT        NOT NULL
                            CHECK (trigger_semantics IN ('hard_exit', 'alert_review')),
    -- authored INTENT. Effective semantics = alert_review whenever the
    -- instrument is disposal-locked (computed at read time, never stored).
    status              TEXT        NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'triggered', 're_armed', 'resolved')),
    -- Machine-evaluability baseline, stored at authoring by the shared parser:
    enforcement_kind      TEXT      NOT NULL
                            CHECK (enforcement_kind IN ('price_below', 'price_above',
                                                        'not_machine_checkable')),
    enforcement_threshold NUMERIC(18,6),
    CONSTRAINT thesis_conditions_threshold_iff_checkable
        CHECK ((enforcement_kind = 'not_machine_checkable') = (enforcement_threshold IS NULL)),
    enforcement_note    TEXT        NOT NULL CHECK (btrim(enforcement_note) <> ''),
    -- The parser echo, verbatim. For unparseable conditions this is the LOUD
    -- marking every consumer must render (e.g. 'NOT MACHINE-CHECKED — manual
    -- review only'); a skip is never silent again (register #5).
    parser_version      TEXT        NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (thesis_id, ordinal)
);
CREATE INDEX idx_thesis_conditions_thesis ON thesis_conditions (thesis_id);
CREATE INDEX idx_thesis_conditions_evaluable
    ON thesis_conditions (status)
    WHERE enforcement_kind <> 'not_machine_checkable';

-- ─────────────────────────────────────────────────────────────────────────
-- 4. thesis_condition_events — append-only episode log with PRICE-DATE
--    provenance (register #21: the old note stamped the run date).
--    An "episode" is derivable (triggered..re_armed pairs); no episode table.
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE thesis_condition_events (
    event_id        BIGSERIAL   PRIMARY KEY,
    condition_id    BIGINT      NOT NULL REFERENCES thesis_conditions(condition_id) ON DELETE CASCADE,
    thesis_id       BIGINT      NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    event_type      TEXT        NOT NULL CHECK (event_type IN ('triggered', 're_armed', 'resolved')),
    price_date      DATE        NOT NULL,   -- the CLOSE's dt, never the run date
    observed_close  NUMERIC(18,6),          -- NULL only for human 'resolved'
    threshold       NUMERIC(18,6),          -- enforcement_threshold at event time
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- run/detection time, kept separately
    source          TEXT        NOT NULL CHECK (source IN ('job', 'human', 'sweep', 'migration')),
    note            TEXT,
    CONSTRAINT thesis_condition_events_resolved_by_human_only
        CHECK (event_type <> 'resolved' OR source IN ('human', 'migration')),
    UNIQUE (condition_id, price_date, event_type)   -- idempotent re-runs (job-conventions)
);
CREATE INDEX idx_condition_events_condition ON thesis_condition_events (condition_id, price_date DESC);
CREATE INDEX idx_condition_events_thesis    ON thesis_condition_events (thesis_id, price_date DESC);

-- ─────────────────────────────────────────────────────────────────────────
-- 5. Instrument constraints — ESS lock on the LOT (KD-3), consumed by every
--    alert surface. Replaces the free-text-only representation in
--    theses.tax_notes (which stays as human narrative, no longer load-bearing).
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE holding_lots
    ADD COLUMN disposal_locked BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN lock_end        DATE,
    ADD COLUMN lock_note       TEXT,
    ADD CONSTRAINT holding_lots_lock_end_requires_locked
        CHECK (disposal_locked OR lock_end IS NULL),
    ADD CONSTRAINT holding_lots_locked_requires_note
        CHECK (NOT disposal_locked OR (lock_note IS NOT NULL AND btrim(lock_note) <> ''));

COMMENT ON COLUMN holding_lots.lock_end IS
    'NULL while disposal_locked = locked INDEFINITELY (end date unknown). A '
    'known end date auto-expires the lock: locked-as-of-D means disposal_locked '
    'AND (lock_end IS NULL OR lock_end >= D). Effective trigger semantics on '
    'any thesis condition for a locked symbol are demoted to alert_review.';

UPDATE holding_lots
SET disposal_locked = TRUE,
    lock_end        = NULL,
    lock_note       = 'ESS trading window locked (ESPP-2026-05-31) — NON-DISPOSABLE until '
                      'the window opens; end date UNKNOWN, confirm from plan administrator '
                      'and set lock_end. Source: theses.tax_notes (thesis 2), migrated 0042.'
WHERE id = 1;

-- ─────────────────────────────────────────────────────────────────────────
-- 6. Backfill HUBS conditions (thesis 2). Baselines hand-transliterated from
--    condition_parser cp-1 and PINNED BY TEST
--    (tests/test_condition_parser.py::test_migration_0042_baselines_match_parser).
--    Semantics = alert_review for ALL migrated rows (KD-5: intent unproven at
--    authoring; upgrading to hard_exit is a human act via asx thesis condition).
-- ─────────────────────────────────────────────────────────────────────────
INSERT INTO thesis_conditions
    (thesis_id, ordinal, condition_text, trigger_semantics, status,
     enforcement_kind, enforcement_threshold, enforcement_note, parser_version)
VALUES
    (2, 1, 'Price closes below $230 stop on volume', 'alert_review', 'triggered',
     'price_below', 230.000000,
     'will enforce: close < 230.000000. Qualifier ''on volume'' NOT enforced (recorded narrowing).',
     'cp-1'),
    (2, 2, '50d MA ($243.61) not recaptured within 2 weeks of breach', 'alert_review', 'active',
     'not_machine_checkable', NULL,
     'NOT MACHINE-CHECKED — manual review only. Contains frozen embedded value ''50d MA ($243.61)'' (authoring-time; re-derived by sweep).',
     'cp-1'),
    (2, 3, 'Macro regime shifts to risk_off_disorderly', 'alert_review', 'active',
     'not_machine_checkable', NULL,
     'NOT MACHINE-CHECKED — manual review only.',
     'cp-1'),
    (2, 4, 'Three or more sell-side downgrades with consensus target below $220', 'alert_review', 'active',
     'not_machine_checkable', NULL,
     'NOT MACHINE-CHECKED — manual review only. Contains a price-like clause (''below $220'') that is NOT enforced.',
     'cp-1');

-- Corrected-provenance event for condition 1: the true trigger close is the
-- 2026-07-02 192.12 close; the old JSONB note stamped the 07-03 RUN date.
INSERT INTO thesis_condition_events
    (condition_id, thesis_id, event_type, price_date, observed_close, threshold, source, note)
SELECT c.condition_id, 2, 'triggered', DATE '2026-07-02', 192.120000, 230.000000, 'migration',
       'Migrated from theses.invalidation_conditions JSONB. Original note misdated the '
       'trigger to 2026-07-03 (run date); 192.12 is the 2026-07-02 close (E05/D01, red-team '
       'packet 2026-08-08). Episode history 06-03..08-07 NOT reconstructed here — the '
       'sweep_rule_integrity tape replay writes it (source=''sweep'').'
FROM thesis_conditions c WHERE c.thesis_id = 2 AND c.ordinal = 1;

-- ─────────────────────────────────────────────────────────────────────────
-- 7. Extend thesis_revisions.revision_type (last rebuilt in 0021).
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE thesis_revisions
    DROP CONSTRAINT IF EXISTS thesis_revisions_revision_type_check;
ALTER TABLE thesis_revisions
    ADD CONSTRAINT thesis_revisions_revision_type_check
    CHECK (revision_type IN (
        'opened', 'assumption_change', 'target_adjusted', 'stop_adjusted',
        'timeline_extended', 'reviewed_no_change', 'status_change',
        'entered', 'exited', 'exited_by_stop', 'exited_by_target',
        'expired', 'analyst_action',
        -- 0042:
        'attestation_change',    -- placeholder <-> underwritten (human only)
        'condition_added',       -- new thesis_conditions row
        'condition_triggered',   -- machine/sweep state transition
        'condition_re_armed',    -- machine/sweep state transition
        'condition_resolved',    -- human resolution
        'integrity_flag'         -- R8 sweep finding (diff = {"flag": {...}})
    ));

-- Grandfathering audit: one discipline-log row per thesis (D4 ruling).
INSERT INTO thesis_revisions (thesis_id, revised_at, revision_type, diff, reasoning)
SELECT thesis_id, NOW(), 'attestation_change',
       '{"attestation": {"old": "null", "new": "placeholder"}}'::jsonb,
       'Grandfathered to attestation=placeholder per governor ruling D4 (finance red-team '
       '2026-08-08): all 13 pre-0042 rules are unattested pending re-attestation via '
       'asx thesis attest.'
FROM theses;

-- ─────────────────────────────────────────────────────────────────────────
-- 8. Drop the write-once JSONB column (KD-1). Leaving it would recreate the
--    stale-read split-brain of register #1. Thesis 2's content is fully
--    migrated above; all other rows are empty arrays.
--    (PRE-APPLY: run the api-conventions.md dependent-object check for
--    out-of-band views over theses.invalidation_conditions before applying.)
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE theses DROP COLUMN invalidation_conditions;

COMMIT;
