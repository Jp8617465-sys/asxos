-- 0061_evidence_stance.sql
-- Does a citation support the thesis, contradict it, or neither? Today the
-- schema cannot express the question, so nobody has ever answered it.
--
-- WHAT THIS ADDS. One nullable TEXT column, `stance`, on both evidence tables
-- (`thesis_evidence`, 0033; `agent_evidence`, the governance audit trail),
-- with a CHECK that admits exactly three values and NULL.
--
-- WHY NULL IS THE POINT, AND WHY THERE IS NO DEFAULT. NULL means *nobody
-- judged*. 'neutral' means *someone judged this and found it non-diagnostic*.
-- Those are different facts, and telling them apart is the entire reason the
-- column exists: a corpus of unmarked rows is a corpus nobody weighed, and a
-- corpus of 'neutral' rows is a corpus someone read and dismissed. A DEFAULT
-- of any value -- 'neutral' most temptingly -- would silently assert the
-- second about rows that are the first, which is exactly the laundering
-- `0059` had to undo for `theses.governance_status`. So: no DEFAULT, and the
-- 26 existing rows are NOT backfilled.
--
-- Those 26 rows are all `source_agent = 'system_screen'`, all tier
-- 'verified', two per thesis across theses 14-26 (measured 2026-09-20). A
-- deterministic valuation screen does not hold an opinion about the thesis it
-- produced evidence for; leaving them NULL is the accurate record, not a gap
-- to be filled later.
--
-- WHY NOW, AT 26 ROWS. The column is the only way to ever ask *what
-- disconfirming evidence did I record* -- the query that detects confirmation
-- bias, and the input the challenge layer's `rule_*` functions
-- (asxos/domain/decision_engine/challenge/rules.py) do not currently have.
-- Adding it today costs one ALTER per table against a corpus that is entirely
-- mechanical. Adding it at 500 rows, most of them human, costs a judgement
-- backfill over rows whose author no longer remembers -- which in practice
-- means it never happens and the question stays unaskable.
--
-- SHAPE. Expand-only (AGENTS.md §5): a nullable column with a NULL-permitting
-- CHECK cannot invalidate an existing row, and every current row satisfies it
-- by holding NULL. TEXT + CHECK rather than an ENUM, per the 0054 header's
-- reasoning -- widening the vocabulary later is one ALTER, whereas an ENUM
-- value cannot be removed at all. No view depends on either table (pg_depend
-- checked per .claude/rules/api-conventions.md before authoring these ALTERs),
-- so there is nothing downstream to rebuild.
--
-- BEFORE-IMAGE at draft time (2026-09-20): thesis_evidence 26 rows,
-- agent_evidence 42 rows, zero of either carrying a stance (the column did not
-- exist). Ledger at 112 rows, head 20260917114415.
--
-- APPLIED 2026-09-20 as 20260920094907 via the AGENTS.md §8 sequence:
-- migration-integration green on the branch (run 35503134757), backup.yml run
-- 35503221429 read to `success`, then applied. Post-apply: ledger 113 rows,
-- both columns nullable with NULL default, 26 + 42 rows and 0 marked -- the
-- ALTER invented no judgements, which is the property the header argues for.

ALTER TABLE thesis_evidence
    ADD COLUMN stance TEXT;

ALTER TABLE thesis_evidence
    ADD CONSTRAINT thesis_evidence_stance_check
    CHECK (stance IS NULL OR stance IN ('supports', 'contradicts', 'neutral'));

ALTER TABLE agent_evidence
    ADD COLUMN stance TEXT;

ALTER TABLE agent_evidence
    ADD CONSTRAINT agent_evidence_stance_check
    CHECK (stance IS NULL OR stance IN ('supports', 'contradicts', 'neutral'));

COMMENT ON COLUMN thesis_evidence.stance IS
    'Does this citation support the thesis, contradict it, or neither? '
    'supports | contradicts | neutral, or NULL (migration 0061). '
    'NULL means nobody judged; neutral means someone judged it non-diagnostic. '
    'Never defaulted and never backfilled -- the distinction is the column''s '
    'purpose. Deterministic screen output (source_agent = ''system_screen'') '
    'holds no stance and stays NULL.';

COMMENT ON COLUMN agent_evidence.stance IS
    'Does this citation support the proposal it was cited for, contradict it, '
    'or neither? supports | contradicts | neutral, or NULL (migration 0061). '
    'Same semantics as thesis_evidence.stance: NULL means nobody judged.';
