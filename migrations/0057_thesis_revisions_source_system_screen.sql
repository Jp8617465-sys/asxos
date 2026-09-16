-- 0057_thesis_revisions_source_system_screen.sql
-- F-E2E r2 M1 / S4: a third revision author, the deterministic valuation screen.
--
-- thesis_revisions.source (0034) admits 'human' and 'agent'. S4's
-- jobs/discover_opportunities.py opens theses from the residual-income sweep
-- (valuation_runs, 0054) — deterministic Python, not an LLM agent, so calling
-- it 'agent' would misdescribe the author and 'human' would claim a decision
-- nobody made. Decision (sprint §4, 2026-09-16): a deterministic screen is a
-- different author from an LLM agent; D-12/C17 are not crossed, and its
-- theses still enter at governance_status = 'pending_review' and need a human
-- approval.
--
-- The two provenance constraints from 0034 are deliberately untouched and
-- therefore apply to the new value: a system_screen revision must carry
-- evidence_confidence and at least one evidence_citation (the valuation run's
-- hash and the point-in-time row it read). agent_name stays NULL for
-- system_screen — there is no agent; the job name is the citation.
--
-- Widening a TEXT CHECK is one ALTER (the 0054 header's reason for CHECKs over
-- ENUMs). Expand-only: every existing row ('human', 13 rows on 2026-09-16)
-- satisfies the wider constraint.

ALTER TABLE thesis_revisions
    DROP CONSTRAINT thesis_revisions_source_check;

ALTER TABLE thesis_revisions
    ADD CONSTRAINT thesis_revisions_source_check
        CHECK (source IN ('human', 'agent', 'system_screen'));

COMMENT ON COLUMN thesis_revisions.source IS
    'human (CLI) | agent (LLM discovery agent, via the service functions only) | '
    'system_screen (deterministic valuation screen, jobs/discover_opportunities.py, '
    'migration 0057). agent and system_screen rows must cite evidence '
    '(thesis_revisions_agent_requires_citation / _confidence).';
