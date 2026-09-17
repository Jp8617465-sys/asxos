-- 0060_thesis_revisions_packet_examined.sql
-- A-47: a decision packet, once built, records that it examined a thesis.
--
-- WHY A NEW revision_type AND NOT reviewed_no_change. The brief's staleness
-- anchor (asxos/brief/compose.py, the `last_answering_revision_at` subquery)
-- is an explicit ALLOWLIST of "answering" revision types:
--   target_adjusted, reviewed_no_change, status_change, entered, expired,
--   exited, exited_by_stop, exited_by_target
-- and asxos/domain/theses/discipline.py names the failure a wrong choice here
-- would cause: "an answering-type revision that does not actually fix the
-- ladder (a reviewed_no_change hold, say) buys another N days." A machine
-- examination recorded as reviewed_no_change would let a job suppress a
-- staleness finding. `packet_examined` is deliberately OUTSIDE that allowlist,
-- so no reader counts it and no clock moves: it is safe by construction, and
-- tests/test_decision_writeback.py binds the two literals together so they
-- cannot drift apart silently.
--
-- WHAT THIS ROW MEANS. "The system built a decision packet against this
-- thesis on this date and reached this recommendation_state." It does NOT mean
-- James revisited the thesis. last_revisited_at and revisit_due_at are never
-- written from this path -- discipline.py's invariant that every clock reset is
-- a human keystroke stands, and its docstring is amended in the same PR to say
-- so about this type explicitly.
--
-- PROVENANCE. source = 'system_screen' (0057: "deterministic Python, not an
-- LLM agent"), so the two 0034 constraints bind: evidence_confidence NOT NULL
-- and at least one evidence_citation. The citations are the packet id and its
-- content_hash; the confidence is the weakest tier among the packet's
-- evidence items.
--
-- SHAPE. Widening a TEXT CHECK is one ALTER (the 0054 header's reason for
-- CHECKs over ENUMs), exactly as 0021 and 0057 did. Expand-only: every
-- existing row satisfies the wider constraint. Before-image at draft time
-- (2026-09-17): 23 rows, revised_at 2026-05-28..2026-09-16, source
-- human:13 / system_screen:10. No view depends on revision_type (pg_depend
-- checked per .claude/rules/api-conventions.md before authoring this ALTER).

ALTER TABLE thesis_revisions
    DROP CONSTRAINT IF EXISTS thesis_revisions_revision_type_check;

ALTER TABLE thesis_revisions
    ADD CONSTRAINT thesis_revisions_revision_type_check
    CHECK (revision_type IN (
        'opened', 'assumption_change', 'target_adjusted', 'stop_adjusted',
        'timeline_extended', 'reviewed_no_change', 'status_change',
        'entered', 'exited', 'exited_by_stop', 'exited_by_target',
        'expired', 'analyst_action',
        'packet_examined'
    ));

COMMENT ON COLUMN thesis_revisions.revision_type IS
    'Discipline event kind (0012, widened 0021, 0060). packet_examined (0060) records '
    'that jobs/build_decision_packets.py built a packet against the thesis; it is '
    'deliberately outside the brief''s answering-revision allowlist and never resets '
    'last_revisited_at -- a system examination is not a human revisit.';
