# The agent read-only role is inert, and every design targeting it aims at the wrong principal

**Status:** current · finding + corrected design
**Scope:** `m14_candidate_agent_db_role_scoping` · risk-register **R2** · `arbi-permission-model` precondition (2) · CLAUDE.md rule **#11**
**Supersedes (on the principal question only):** `docs/proposals/agent-db-readonly-role-design-2026-07-11.md`
**Measured:** 2026-08-22, live production, read-only probes
**Owner:** James — every remedy below is migration-approval or infra class; nothing here is agent-executable
**Superseded by:** N/A

---

## The finding

`migrations/0039_agent_readonly_role.sql` creates `asxos_agent_ro`. Its header says
`DRAFT — NOT APPLIED`. **The role exists in production.** Measured:

```sql
SELECT current_user, session_user,
       (SELECT count(*) FROM pg_roles WHERE rolname='asxos_agent_ro') AS agent_ro_exists,
       has_table_privilege(current_user,'signals','SELECT')           AS can_read_signals;
-- → supabase_read_only_user | supabase_read_only_user | 1 | true
```

Three things follow, and the third is the one that matters.

**1. `0039` is a third false migration header.** It joins `0043` ("PRODUCTION-READY — still
unapplied", applied 2026-08-12) and `0044` ("DRAFT - NOT APPLIED", applied 2026-08-21). The
2026-07-18 queue entry in `roadmap-state.md` already recorded "0039 applied + supabase-ro
live"; the file was never updated to match. `0045`'s DRAFT header, by contrast, is **correct**.

**2. The MCP does not authenticate as that role.** `current_user` is
**`supabase_read_only_user`** — a Supabase-managed role, not `asxos_agent_ro`. This is exactly
the contingency `0039`'s own header names at lines 21-25:

> **NECESSARY-BUT-NOT-SUFFICIENT:** this does nothing until the agent MCP session actually
> authenticates AS this role (infra step James owns — design doc deliverable 2+5: Supavisor
> pooler connection string).

That infra step was never completed. The migration landed; the step that makes it load-bearing
did not.

**3. Therefore the control is inert, and has been since `0039` was applied.** Every document
that reports "0039 applied + supabase-ro live" reads as though agent DB access is now
role-scoped. It is not. The role exists, holds whatever grants `0039` gave it, and **nothing
connects through it.**

### Why this is worse than "not done yet"

A control that was never built is a known gap. A control that exists, is recorded as applied,
and is bypassed by the actual connection path is a gap that **looks closed on inspection**.
`risk-register` R2, `arbi-permission-model` precondition (2), and the Phase 2c prerequisite all
point at `m14_candidate_agent_db_role_scoping` as the thing to finish — and a reader checking
"is the role applied?" gets `yes`.

Meanwhile `signals` holds **64,189 rows**, latest `as_of` **2026-08-05**, and is `SELECT`-able
by the connecting role right now. The 2026-08-21 handoff already named the honest limit:

> Every control here is prompt-level. `mcp__supabase-ro__execute_sql` permits any SELECT, so
> the frozen table stays reachable and *not reading it* is the control. `REVOKE SELECT ON
> signals` for the agent role is the only mechanical control that would survive a prompt edit.

**That REVOKE, written against `asxos_agent_ro`, would have changed nothing.** It would have
been applied, recorded as the mechanical enforcement of rule #11, and left the actual read path
untouched — a fix that closes the leak in the report and not in the product. That failure mode
has now occurred twice in this repo in eight days (PR #149's Patch 2 named one leaking agent
when there were two); this would have been the third.

---

## The corrected design

### Branch A — complete the infra step, then REVOKE from `asxos_agent_ro` (the only viable path)

Point the agent MCP session at the role `0039` already created, via the Supavisor pooler
connection string, then revoke the frozen Model A surface from it.

- **Pro:** `asxos_agent_ro` is *ours*. Revoking from it cannot affect any Supabase-managed
  path, the dashboard, PostgREST, or another tool. The blast radius is exactly the agents.
- **Pro:** it makes `0039` load-bearing for the first time, closing R2 and
  `arbi-permission-model` precondition (2) genuinely rather than nominally.
- **Con:** requires the infra step (out-of-repo; role password set out-of-band, never
  committed) that has been outstanding since 2026-07.
- **Order matters:** repoint first, verify `current_user = asxos_agent_ro`, *then* REVOKE.
  Revoking first would be inert and would look like success.

### Branch B — REVOKE from `supabase_read_only_user`: **NOT VIABLE** (measured)

This was drafted as the quick alternative. A direct probe closes it:

```sql
SELECT rolname, rolbypassrls, rolconnlimit,
       ARRAY(SELECT b.rolname FROM pg_auth_members m
             JOIN pg_roles b ON m.roleid=b.oid WHERE m.member=r.oid) AS member_of
FROM pg_roles r WHERE rolname IN ('asxos_agent_ro','supabase_read_only_user');
```

| role | `rolbypassrls` | `member_of` | conn limit |
|---|---|---|---|
| `asxos_agent_ro` | `false` | `{}` | 10 |
| `supabase_read_only_user` | **`true`** | **`{pg_monitor, pg_read_all_data}`** | unlimited |

`pg_read_all_data` is a **built-in Postgres role that grants SELECT on every table**. So
`REVOKE SELECT ON signals FROM supabase_read_only_user` **cannot work** — the privilege is
inherited through role membership, not held as a direct grant, and a REVOKE does not remove an
inherited one. The only way to cut it is to drop the membership, which removes *all* of that
role's read access and would break whatever else authenticates through it.

`rolbypassrls = true` closes the fallback too: RLS on `signals` would not constrain this role
either.

**Branch A is therefore the only viable path, not merely the preferred one.** And note what
Branch B would have looked like if shipped without this probe: a migration applied, recorded
as rule #11's mechanical enforcement, that changed nothing measurable. The same
closes-the-leak-in-the-report failure the finding above warns about.

`asxos_agent_ro`'s row is the encouraging half — no memberships, no RLS bypass, a sane
connection limit. It is a correctly-built role that nothing uses.

### What to revoke

The frozen Model A surface, not "signals" alone:

```sql
REVOKE SELECT ON TABLE signals          FROM asxos_agent_ro;
REVOKE SELECT ON TABLE signal_outcomes  FROM asxos_agent_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM asxos_agent_ro;
-- then re-grant SELECT explicitly on the tables agents legitimately read,
-- so a future table does not auto-grant the way 0039's ALTER DEFAULT PRIVILEGES arranged.
```

The `ALTER DEFAULT PRIVILEGES` line is the half that is easy to miss: `0039` deliberately set
future tables to auto-grant. Leaving that in place means any future Model A-adjacent table is
readable the day it is created.

### Acceptance probe — run as the agent principal, not as owner

```sql
SELECT current_user,                                          -- must be asxos_agent_ro
       has_table_privilege(current_user,'signals','SELECT'),  -- must be false
       has_table_privilege(current_user,'theses','SELECT');   -- must be true
```

Both halves are required. A probe that only checks `signals` cannot distinguish "correctly
revoked" from "revoked everything and broke the agents".

**Pre-apply:** capture the full grant set for the principal so the rollback is exact.
**Rollback:** re-`GRANT SELECT` the captured set.

---

## What this does not fix

Rule #11's other enforcement point — `resolve_production_model()`'s
`approved_for_allocation` gate (`asxos/domain/models/production_gate.py`) — is untouched by
any of this and remains correct. This is about *reads of frozen evidence*, not about the
allocator.

And a REVOKE does not make the agents correct; it makes them *unable to be incorrect in one
specific way*. The model-independent amputations in PR #149 remain the substantive fix.

---

## A second, independent instance of the same class, found the same day

The five investment-analysis agents declare `mcp__supabase-ro__execute_sql` in **static
frontmatter**. During this session that MCP server disconnected and reappeared under a rotated
**UUID** name — twice. Any agent dispatched across that boundary has no DB tool at all — it
does not error, it simply has no way to query, and will answer from the repo or from memory.

This is the R5/R16/R17 MCP-ID-rotation defect, and it is not hypothetical: the owed
`/pm-review HUBS.NYSE` verification could not be produced this session partly for this reason,
and had it been produced it would have been **blind and false-clean**. The main loop hit the
same wall — the rotated tool name is not allowlisted, so further probes were unavailable.

The fix is structural (a stable MCP alias, or dynamic tool resolution in the agent frontmatter),
not a re-run. Until then, **any agent output that cites no live figure should be treated as
"could not query", not as "found nothing"** — and the two are indistinguishable in the output
as it stands today.

---

## Handed to James

| Item | Class |
|---|---|
| **Complete the Supavisor repoint to `asxos_agent_ro`** — Branch A, the only viable path | Infra / credentials — hard stop for agents. Nothing else here works until this does |
| Apply the REVOKE migration, *after* verifying `current_user` changed | Migration approval. Applied before the repoint it is inert and looks like success |
| Correct `0039`'s `DRAFT — NOT APPLIED` header (and `0043`'s, `0044`'s) | `migrations/**` is Edit-denied to agents |
| Stable MCP alias or dynamic agent tool resolution | Harness — blocks the owed `/pm-review` artifact |
