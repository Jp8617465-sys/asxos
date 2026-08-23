-- 0039_agent_readonly_role.sql  (Renumbered from the design doc's 0038 — that
-- number is taken by 0038_screening_evaluator_wiring.sql.)
--
-- Source of truth: docs/proposals/agent-db-readonly-role-design-2026-07-11.md
-- (pre-apply checks §Pre-apply, acceptance test §Post-apply, rollback §Rollback).
--
-- m14_candidate_agent_db_role_scoping / risk-register R2 / arbi-permission-model
-- precondition (2). A real read-only Postgres LOGIN role so agent MCP sessions
-- physically cannot write -- replacing the prompt-only "SELECT-only" instruction
-- that is today the ONLY thing stopping a prompt-injected agent (fed untrusted
-- RSS text via regulatory_events.title/summary) from hand-writing the
-- governance_events INSERT + governed-table UPDATE pair the 0034/0036 triggers
-- require, bypassing the human-approval gate.
--
-- LOAD-BEARING CONTROL = the privilege system (no INSERT/UPDATE/DELETE/TRUNCATE
-- grant + role is not a table owner + no superuser/CREATEROLE + no membership in
-- any privileged role). default_transaction_read_only is a GUARDRAIL only --
-- it is USERSET/session-overridable, NOT a boundary.
--
-- NECESSARY-BUT-NOT-SUFFICIENT: this does nothing until the agent MCP session
-- actually authenticates AS this role (infra step James owns -- design doc
-- deliverable 2+5: Supavisor pooler connection string,
-- asxos_agent_ro.gxjqezqndltaelmyctnl). This file MUST NOT contain the role's
-- password (it is committed to git); James sets it out-of-band.
--

BEGIN;

-- 1. The role. LOGIN, no password here, no privileged attributes/memberships.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'asxos_agent_ro') THEN
        CREATE ROLE asxos_agent_ro
            LOGIN
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS NOREPLICATION
            CONNECTION LIMIT 10;   -- covers /pm-review's 5-way fan-out + macro/context; tunable
    END IF;
END
$$;

-- 2. Guardrail (NOT a boundary): default every txn to read-only.
ALTER ROLE asxos_agent_ro SET default_transaction_read_only = on;

-- 3. Read surface: USAGE on public + SELECT on everything now (tables AND views).
GRANT USAGE ON SCHEMA public TO asxos_agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO asxos_agent_ro;

-- 4. Future tables/views auto-grant SELECT. FOR ROLE postgres is REQUIRED --
--    default privileges only apply to objects created by the named role; every
--    migration is applied as postgres (confirm via pre-check #3). Add a second
--    FOR ROLE line if the pre-check shows a different creator role.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT ON TABLES TO asxos_agent_ro;

-- 5. Default-deny writes. A fresh non-owner role has none of these anyway; this
--    is explicit intent + defends against any PUBLIC grant or future accidental
--    group membership (e.g. the GRANT ALL ... TO anon/authenticated/service_role
--    on stock_universe, migration 0029:63 -- harmless only while this role joins
--    none of those).
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON ALL TABLES IN SCHEMA public FROM asxos_agent_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM asxos_agent_ro;

-- 6. No sequence writes (this -- not "REVOKE EXECUTE on nextval/setval" -- is the
--    real control): grant no sequence privileges, revoke any.
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM asxos_agent_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM asxos_agent_ro;

-- 7. Functions: deliberately NOT globally REVOKE EXECUTE ... FROM PUBLIC (would
--    risk the human/CLI app role if it is a non-owner role). Not needed: the only
--    Postgres writer fn, set_active_profile() (0005:97), and the governance
--    trigger fns (0034/0036) are all SECURITY INVOKER, so the agent role running
--    them writes with its own (nil) privileges and fails. The one class that
--    could escalate is SECURITY DEFINER writer fns owned by a privileged role --
--    pre-check #2 confirms there are none.

-- 8. No grants on auth/vault/storage/supabase_migrations schemas -- omitting them
--    is the control (a fresh role has no USAGE on them). Do NOT add any.

COMMIT;
