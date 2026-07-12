# Agent read-only Postgres role — design (`m14_candidate_agent_db_role_scoping`, R2, roadmap PR2)

**Status:** proposed — draft migration included, NOT applied
**Scope:** closes risk-register R2 (agent SELECT-only enforcement is prompt-level only) and
autonomy precondition (2) in `docs/product/arbi-permission-model.md`
**Last verified:** 2026-07-11
**Owner:** `backend-architect` (drafted during James's 8-hour autonomy window); James applies the
migration and owns the infra re-point
**Depends on:** none — this is itself the prerequisite for Phase 2c and standing autonomy
**Superseded by:** N/A

Recovered verbatim from the agent's transcript after a dropped completion notification (see
`docs/product/memory/working/db-role-design-transcript-report-2026-07-11.md`).

---

## The control model (what actually stops the bypass)

The governance bypass the security review flagged requires a **write**: the `BEFORE UPDATE`
triggers (`migrations/0034_governance_audit_trigger_and_revision_provenance.sql:98-112`, and the
three siblings in `migrations/0036_phase2_governance_audit_triggers.sql`) demand a matching
`governance_events` INSERT in the *same transaction* (`pg_current_xact_id()` equality) before
they'll let a `governance_status` UPDATE through. So the injected agent needs to emit **both**
`INSERT INTO governance_events ...` **and** `UPDATE macro_theses SET governance_status='approved'
...`.

That means a default-deny-on-writes role closes the hole **structurally and completely**: deny
INSERT on `governance_events` *or* deny UPDATE on the four governed tables and the pair can never
form. No enumeration of attack SQL is needed — the write privilege is the single choke point.

Two precise corrections to the original brief's suggested approach, both load-bearing:

1. **`approve_object`/`reject_object` are Python** (`asxos/domain/theses/service.py`,
   `asxos/domain/macro_theses/service.py`), **not Postgres functions** — there is nothing to
   `REVOKE EXECUTE` on. They emit raw INSERT+UPDATE SQL, so they're blocked by the table-level
   write revoke, not a function grant. The only Postgres writer function in the repo is
   `set_active_profile()` (`migrations/0005_portfolio.sql:97`), and it is **SECURITY INVOKER**
   (no `SECURITY DEFINER` clause) — so when the agent role calls it, the inner `UPDATE profiles`
   runs with the agent's own (nil) write privileges and fails. `REVOKE EXECUTE` on it is
   therefore **not the control** and is a no-op while `PUBLIC` retains EXECUTE; globally
   revoking from `PUBLIC` would risk the human app role. Recommendation: *don't* touch function
   grants; rely on the privilege model + a SECURITY-DEFINER audit (pre-check #2 below).
2. **`nextval`/`setval` are `pg_catalog` built-ins** — you don't revoke EXECUTE on them.
   `setval`/`nextval` need `USAGE`/`UPDATE` **on the sequence**; a fresh role has neither. The
   real "no sequence writes" control is granting no sequence privileges, which is the default.

**Privilege revocation is the boundary. `SET default_transaction_read_only` is only a
guardrail** — it is `USERSET`/session-context, so the agent could `SET
default_transaction_read_only = off` in its own session. Keep it (defense-in-depth) but never
treat it as the boundary. The post-apply acceptance test explicitly flips it off and re-checks
that writes still fail, to prove the privilege system — not the guardrail — is doing the work.

---

## 1. The role + grants — draft `migrations/0038_agent_readonly_role.sql`

`LOGIN`, **not** `NOLOGIN`. The role must be a real connection principal because **`SET ROLE` is
not a boundary here**: the agent controls the SQL text and could `RESET ROLE` back. The only way
the role scopes anything is if the MCP session *authenticates as it*. It carries no privileged
memberships, so it cannot `SET ROLE` up either.

```sql
-- 0038_agent_readonly_role.sql  (DRAFT — NOT APPLIED. James applies via
-- mcp__supabase__apply_migration when ready.)
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
-- actually authenticates AS this role (infra step James owns -- deliverable 2+5).
-- This file MUST NOT contain the role's password (it is committed to git);
-- James sets it out-of-band.
--
-- Applied via mcp__supabase__apply_migration. After applying: bump
-- REQUIRED_MIGRATIONS in asxos/api/main.py (currently 91, main.py:15) to the
-- observed SELECT count(*) FROM supabase_migrations.schema_migrations.

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
```

`GRANT SELECT ON ALL TABLES` (not a hand-picked subset) is deliberate: the agent read surface is
wide and moving (`prices`, `fundamentals`, `signals`, `theses`, `macro_theses`,
`regulatory_events`, `market_context`, `portfolio_daily_snapshots`, `current_holdings`,
`agent_runs`/`agent_evidence`/`governance_events`, benchmark rows, …), and enumerating it invites
"agent legitimately needs table X but wasn't granted" breakage. Reading is harmless; only writes
were ever the risk. Views (`current_holdings` 0001:140, `governed_active_*` 0035:111-123,
`stock_universe`, `market_context_current`) are relations and are covered.

---

## 2. How an MCP session connects **as** the role — and the honest limit

There are two Supabase-MCP shapes, and which one `supabase-ro` currently is determines whether
this role becomes the real boundary or stays dormant defense-in-depth:

- **Connection-string MCP** (local/self-hosted Postgres MCP that takes a `DATABASE_URL`): point
  its connection string at the role via the Supavisor pooler. Custom-role username format is
  `role.project_ref` (confirmed by Supabase discussion #34455) — project ref is
  `gxjqezqndltaelmyctnl` (`api-conventions.md:46`):
  `postgresql://asxos_agent_ro.gxjqezqndltaelmyctnl:PASSWORD@aws-0-<region>.pooler.supabase.com:6543/postgres`
  Here `current_user = asxos_agent_ro` and the **DB privilege system is the actual boundary**.
  This is the strong option — recommend moving `supabase-ro` to this shape.
- **Hosted Supabase MCP** (`https://mcp.supabase.com/mcp?project_ref=...&read_only=true`):
  authenticates via a Supabase Personal Access Token; the **platform manages the DB connection
  and does not accept a custom Postgres role or connection string**. `read_only=true` enforces
  read-only at the *session/transaction* level using the platform's own role — **not**
  `asxos_agent_ro`.

**Honest limitation:** if `supabase-ro` is the hosted MCP, you **cannot** make
`asxos_agent_ro` the connection principal without infra James controls — the migration's role
sits dormant as defense-in-depth and the live control remains the platform's `read_only`
wrapper, which is a same-platform toggle (weaker than a privilege boundary, and exactly the
"prompt/config-enforced, not mechanical" class the security review objected to). The migration
alone is **necessary but not sufficient**; making the role load-bearing requires re-pointing the
agent MCP at the pooler as `asxos_agent_ro`, which is a change to the Claude-client MCP config
that lives outside this repo. `SET ROLE` is explicitly rejected as the mechanism — the agent
controls the SQL and can `RESET ROLE`, so the connection must *authenticate as* the role, not
switch into it. (Direct connection `db.<ref>.supabase.co:5432` also supports custom roles as a
fallback but is IPv6-only on current Supabase; the pooler is the reliable path — James should
validate Supavisor accepts the custom role.)

---

## 3. What stays writable, and coexistence (single-user, no RLS)

Nothing about the human/CLI/API/cron write path changes. The app connects via
`settings.database_url` (`asxos/config.py:26`, asyncpg pool `asxos/db.py:11-19`) as its existing
role, which keeps full read-write — this migration never touches that role's grants.
`approve_object`/`reject_object` (Python) and `set_active_profile()` keep working because they
run on the app role, which retains INSERT/UPDATE.

Separation is by **two distinct login roles**, not row policies — correct for
single-user/no-RLS (`CLAUDE.md #4`, `api-conventions.md:30`): agent sessions authenticate as
`asxos_agent_ro` (SELECT-only); human/CLI/cron/API authenticate as the app role (read-write).
Nothing shared, nothing to coordinate, no RLS needed. The read-write `mcp__supabase__*` stays
James's apply/migration tool; the agents' allow-list (`.claude/settings.json:4`) already exposes
only `mcp__supabase-ro__execute_sql` — keep the rw tool out of agent scope.

---

## 4. Ordering, pre-checks, rollback

**Next number: `0038`** (repo is through `0037_security_kind.sql`). Explicit `BEGIN`/`COMMIT`
matches house style (`0035` closes with `COMMIT`, line 125). After apply, bump
`REQUIRED_MIGRATIONS` (currently `91`, `asxos/api/main.py:15`) to the observed `SELECT count(*)
FROM supabase_migrations.schema_migrations` — not a guessed +1 (`api-conventions.md:48-49`).

**Pre-apply checks** (run via `mcp__supabase__execute_sql`):
1. Role absent: `SELECT rolname FROM pg_roles WHERE rolname='asxos_agent_ro';` → expect 0 rows
   (else the `DO` guard no-ops CREATE but grants still apply — fine, but know it).
2. **SECURITY DEFINER audit** (the one real escalation class): `SELECT n.nspname, p.proname,
   pg_get_function_identity_arguments(p.oid) FROM pg_proc p JOIN pg_namespace n ON
   n.oid=p.pronamespace WHERE p.prosecdef AND n.nspname='public';` → repo migrations define
   **none** (grep confirmed), but the DB is a shared project with out-of-band objects
   (`api-conventions.md:50-51`). Any hit that writes → add a targeted `REVOKE EXECUTE ... FROM
   PUBLIC` in 0038.
3. Confirm the apply-migration role for the `ALTER DEFAULT PRIVILEGES FOR ROLE` clause: `SELECT
   current_user;` → expect `postgres`; if not, adjust/duplicate the `FOR ROLE` lines.
4. Read-surface sanity: capture `SELECT count(*) FROM information_schema.tables WHERE
   table_schema='public';` and re-verify post-apply with `SELECT count(*) FROM
   information_schema.role_table_grants WHERE grantee='asxos_agent_ro' AND
   privilege_type='SELECT';`.
5. The `pg_depend` dependent-object check (`api-conventions.md:55-64`) is **N/A** — 0038 does no
   `ALTER`/`DROP COLUMN`/`DROP TABLE`. State that explicitly so the omission is intentional, not
   overlooked.

**Post-apply acceptance test** (from a real agent MCP session once re-pointed — this is the
sign-off):
- `SELECT current_user;` → `asxos_agent_ro`
- `SELECT count(*) FROM prices;` → succeeds
- `INSERT INTO governance_events(object_type,object_id,from_status,to_status,actor) VALUES
  ('macro_thesis',1,'pending_review','approved','x');` → **permission denied**
- `UPDATE macro_theses SET governance_status='approved' WHERE macro_thesis_id=1;` → **permission
  denied**
- `SET default_transaction_read_only=off; INSERT ...;` → **still permission denied** (proves the
  privilege boundary, not the guardrail)

**Rollback** (manual via `mcp__supabase__execute_sql`):
```sql
BEGIN;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE SELECT ON TABLES FROM asxos_agent_ro;
DROP OWNED BY asxos_agent_ro;   -- clears remaining grants + default-priv rows
-- terminate live sessions first, else DROP ROLE errors:
--   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename='asxos_agent_ro';
DROP ROLE IF EXISTS asxos_agent_ro;
COMMIT;
```
Roles are cluster-global and DROP is only blocked by owned objects/live sessions — this role
owns nothing (read-only, never creates), so `DROP OWNED BY` + session-kill is sufficient.

---

## 5. Migration (I5 — James applies) vs infra (dashboard/API — James configures)

**MIGRATION — `mcp__supabase__apply_migration` (I5, James approves each per
`arbi-permission-model.md:41`), then bump `REQUIRED_MIGRATIONS`:** everything in `0038` —
`CREATE ROLE` (no password), USAGE/SELECT grants, `ALTER DEFAULT PRIVILEGES`, write/sequence
revokes, `ALTER ROLE SET default_transaction_read_only`.

**INFRA — James, NOT in git:**
1. **Set the password** out-of-band: `ALTER ROLE asxos_agent_ro WITH PASSWORD '<generated>';`
   via the Supabase dashboard SQL editor or a `psql` session — **never committed** (the
   migration file is in git). Store it alongside `database_url` in the secrets store. Rotatable
   independently.
2. **Re-point the `supabase-ro` MCP** to authenticate as `asxos_agent_ro` — either the pooler
   connection string (connection-string MCP, the strong option) or, if it's the hosted MCP,
   confirm `read_only=true` and accept the deliverable-2 limitation. This edits the Claude-client
   MCP config outside the repo, so only James can do it. This step is what actually makes the
   migration load-bearing.
3. **Run the acceptance test** from an agent session (section 4).
4. Optionally validate/adjust the Supavisor pooler acceptance of the custom role and
   `CONNECTION LIMIT`.

---

## Why this is the roadmap unblocker

Landing this migration **and** the infra re-point mechanically satisfies precondition (2) in
`docs/product/arbi-permission-model.md:138` ("a read-only Postgres role so an unattended agent
physically cannot write"), which is the gate on standing autonomy for the reversible tiers and
on the PR 7b unattended `/arbi` path (`arbi-permission-model.md:110-113`). It also downgrades R2
(`docs/product/risk-register.md:21`) and the R5 "prompt-only enforcement" line
(`risk-register.md:24`) from prompt-enforced to mechanically-enforced for the DB-write class.
Note the residual it does **not** solve: the read surface still feeds untrusted RSS text
(`regulatory_events`) into the agent — the role caps the *consequence* to read-only; it does not
sanitize the *input*. That is the correct division of responsibility.

Files this design relies on: `migrations/0034_governance_audit_trigger_and_revision_provenance.sql`
(lines 98-112, trigger = same-txn INSERT requirement), `migrations/0036_phase2_governance_audit_triggers.sql`,
`migrations/0033_governance_schema_core.sql:164-184` (`governance_events`),
`migrations/0005_portfolio.sql:97` (`set_active_profile`, SECURITY INVOKER),
`migrations/0029_widen_market_cap_columns.sql:63` (existing Supabase role-grant pattern),
`asxos/config.py:26` + `asxos/db.py:11-19` (app write path), `asxos/api/main.py:15`
(`REQUIRED_MIGRATIONS`), `.claude/settings.json:4` (agent tool allow-list),
`.claude/rules/api-conventions.md:44-66` (migration conventions), `docs/product/risk-register.md:21`
(R2), `docs/product/arbi-permission-model.md:138` (precondition 2).

Sources:
- [Supabase MCP Server docs](https://supabase.com/docs/guides/ai-tools/mcp)
- [Supabase discussion #34455 — read-only user / pooler `role.project_ref` username format](https://github.com/orgs/supabase/discussions/34455)
- [Supabase discussion #34325 — MCP read-only mode](https://github.com/orgs/supabase/discussions/34325)
