-- 0021: theses analyst consensus + earnings fields + thesis_revisions analyst_action type
-- Gap 3: analyst consensus fields
-- Gap 7: analyst_action revision type
-- Gap 8: earnings date fields

ALTER TABLE theses
    ADD COLUMN IF NOT EXISTS analyst_buy_count          INTEGER       DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS analyst_neutral_count      INTEGER       DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS analyst_sell_count         INTEGER       DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS analyst_consensus_target   NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS analyst_updated_at         DATE          DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS next_earnings_date         DATE          DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS earnings_notes             TEXT          NOT NULL DEFAULT '';

-- Extend CHECK to include 'analyst_action'
ALTER TABLE thesis_revisions
    DROP CONSTRAINT IF EXISTS thesis_revisions_revision_type_check;

ALTER TABLE thesis_revisions
    ADD CONSTRAINT thesis_revisions_revision_type_check
    CHECK (revision_type IN (
        'opened', 'assumption_change', 'target_adjusted', 'stop_adjusted',
        'timeline_extended', 'reviewed_no_change', 'status_change',
        'entered', 'exited', 'exited_by_stop', 'exited_by_target',
        'expired', 'analyst_action'
    ));
