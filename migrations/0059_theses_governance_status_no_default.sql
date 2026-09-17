-- 0059_theses_governance_status_no_default.sql
-- Close the column default that laundered eleven unreviewed rows into 'approved'.
--
-- Migration 0033 added theses.governance_status as NOT NULL DEFAULT 'approved',
-- and said why: it "grandfathers every existing thesis" so the human CLI path
-- had zero friction on day one. That was right for the backfill and wrong to
-- leave standing, and the cost was measured on 2026-09-17.
--
-- WHAT HAPPENED. Eleven rows (thesis_id 3-13) were bulk-inserted in a single
-- transaction at 2026-06-24 10:24:25 by a paper-build seeder that has since been
-- deleted. It omitted governance_status, so every row took this DEFAULT and
-- landed at 'approved' -- the status every brief collector filters on and trusts
-- (asxos/domain/brief/collectors/*.py all carry `AND governance_status =
-- 'approved'`). It also omitted `source`, so thesis_revisions recorded them as
-- 'human'. They carried NULL target_price, NULL stop_price, NULL timeline_days
-- and a zero-width entry band, and 0 thesis_evidence rows. Before 2026-09-17
-- there were 0 governance_events rows of object_type='thesis' in the whole
-- database: nobody had ever approved, rejected or retired a thesis. As the
-- register review put it, "'approved' on these rows means nobody ever said no."
--
-- Consequence, measured: check_thesis_invalidations ran 61 times over the 84 days
-- to 2026-09-15 and could not fire on one of them -- no stop to breach, no
-- timeline to expire. The silence was structural. It would have looked identical
-- if every one of those eleven positions had collapsed.
--
-- WHY THE DEFAULT AND NOT AN APPROVAL-PATH GATE. The first draft of the register
-- review proposed hardening approve_object(). Its own red-team pass found that
-- reasoning wrong and recorded the correction: these rows never went through
-- approve_object, so a gate there would have been bypassed by exactly the route
-- they took. If the stated cause is the default, the fix is the default.
--
-- WHAT THIS CHANGES. An INSERT that omits governance_status now fails loudly on
-- the NOT NULL constraint instead of silently claiming approval. Nothing in the
-- codebase does that: open_thesis() (asxos/domain/theses/service.py) binds the
-- column explicitly as $15, and there is no other INSERT INTO theses anywhere in
-- asxos/, jobs/ or scripts/. So this is inert for every live path and fatal only
-- for the shape that caused the incident.
--
-- The Python-side default stays: open_thesis(governance_status="approved") is an
-- explicit, reviewed, test-covered decision in code. A default in a function
-- signature is readable; a default in the schema is invisible to the caller.
--
-- NOT IN SCOPE, deliberately. (1) The level gate -- refusing 'approved' when a
-- thesis states no falsifiable number -- is the second half of this fix, and it
-- is a real change to the human CLI flow (`asx thesis open SYMBOL` makes every
-- level optional today). Filed as a backlog row rather than smuggled in here.
-- (2) themes.governance_status and theme_holdings.governance_status carry the
-- same DEFAULT 'approved' from migration 0035 and the same laundering risk;
-- filed separately, one concern per migration.
--
-- Expand-only and reversible by a forward migration: re-adding the default is one
-- ALTER. No data is read or written, no row changes, no constraint is added or
-- relaxed -- the CHECK and the NOT NULL both stand exactly as 0033 wrote them.

ALTER TABLE theses
    ALTER COLUMN governance_status DROP DEFAULT;

COMMENT ON COLUMN theses.governance_status IS
    'draft | evidence_complete | pending_review | approved | rejected | retired. '
    'NO COLUMN DEFAULT (migration 0059): an INSERT must state it. The DEFAULT '
    '''approved'' from 0033 laundered eleven unreviewed auto-seeded rows into the '
    'status every brief collector trusts, with 0 governance_events rows to show '
    'for it. Transitions go through approve_object / reject_object / retire_object '
    'in asxos/domain/theses/service.py, each of which writes the governance_events '
    'row the 0034 BEFORE UPDATE trigger requires, in that order.';
