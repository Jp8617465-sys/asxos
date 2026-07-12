# backend-architect transcript recovery — agent DB read-only role design (2026-07-11)

**Transcript file:** `/root/.claude/projects/-home-user-asxos/297b3357-cc67-5e3c-95d2-2b0024c4d68e/subagents/agent-af3a272d707eb38d7.jsonl`
**Subagent:** `backend-architect` (model `claude-opus-4-8`), dispatched to design the agent DB read-only Postgres role scoping (`m14_candidate_agent_db_role_scoping`, risk-register R2, roadmap PR2, `arbi-permission-model.md` precondition 2).

## Executive summary

**The agent finished cleanly and produced a real, usable, implementable design.** It is not stuck, not truncated, and did not error out — the transcript's last message (line 79 of 79) is a complete ~17.9k-character design doc that ends on a natural closing "Sources" section, not mid-sentence. It includes a full draft migration (`0038_agent_readonly_role.sql`, `CREATE ROLE asxos_agent_ro` + GRANT/REVOKE set), a clear explanation of how an MCP session would actually connect as that role (with an honestly-stated limitation), pre-apply/post-apply checks, a rollback script, and an explicit split of what James must do via migration vs. via out-of-band infra config. This is ready to hand to James as a draft PR with no further recovery work needed — the only reason the main session never saw a completion notification appears to be a lost/dropped notification, not a stuck or failed agent.

---

## 1. Did it reach a real conclusion? — Yes. Full recovered design below.

The final assistant message (transcript line 79, message id `msg_011CcvFgbcV7NUeGa48TAtJP`, timestamp `2026-07-11T12:19:05.429Z`) is the complete deliverable. Key extracted content:

### Control model / reasoning

> "The governance bypass the security review flagged requires a **write**: the `BEFORE UPDATE` triggers (`migrations/0034_governance_audit_trigger_and_revision_provenance.sql:98-112`, and the three siblings in `migrations/0036_phase2_governance_audit_triggers.sql`) demand a matching `governance_events` INSERT in the *same transaction* (`pg_current_xact_id()` equality) before they'll let a `governance_status` UPDATE through... That means a default-deny-on-writes role closes the hole **structurally and completely**."

It made two corrections to the original brief's suggested approach (both explicitly flagged as load-bearing):
1. `approve_object`/`reject_object` are **Python**, not Postgres functions — nothing to `REVOKE EXECUTE` on. The only Postgres writer function in the repo, `set_active_profile()` (migration 0005:97), is `SECURITY INVOKER`, so it's blocked automatically by the table-level revoke, not a function grant.
2. `nextval`/`setval` are `pg_catalog` built-ins — the real sequence control is granting no sequence privileges (not "revoke execute on nextval").

It also explicitly distinguished the **boundary** (privilege revocation) from a mere **guardrail** (`SET default_transaction_read_only`, which is session-overridable and therefore not trustworthy alone).

### Draft migration — `migrations/0038_agent_readonly_role.sql`

Full SQL recovered verbatim (next available migration number after 0037):

```sql
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

-- 4. Future tables/views auto-grant SELECT. FOR ROLE postgres is REQUIRED.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT ON TABLES TO asxos_agent_ro;

-- 5. Default-deny writes.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON ALL TABLES IN SCHEMA public FROM asxos_agent_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM asxos_agent_ro;

-- 6. No sequence writes.
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM asxos_agent_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM asxos_agent_ro;

-- 7. Functions: deliberately NOT globally REVOKE EXECUTE ... FROM PUBLIC
--    (would risk the human/CLI app role). Not needed -- see reasoning above.

-- 8. No grants on auth/vault/storage/supabase_migrations schemas -- omitting
--    them is the control.

COMMIT;
```

(Full file includes an extensive header comment citing the exact bypass this closes, the load-bearing-control statement, and the "necessary but not sufficient" caveat about MCP re-pointing — see the file text captured in full in the raw transcript, section headed "## 1. The role + grants".)

`GRANT SELECT ON ALL TABLES` (not a hand-picked subset) was a deliberate choice: enumerating a subset "invites 'agent legitimately needs table X but wasn't granted' breakage," and reading is judged harmless — only writes were ever the risk.

### Connection-story / honest limitation (deliverable 2)

This is the most important nuance in the whole design. It distinguishes two possible shapes of the `supabase-ro` MCP tool and says plainly that it could not determine from inside the session which one is actually in use:

- **Connection-string MCP** (self-hosted, takes a `DATABASE_URL`): point it at the pooler using username format `role.project_ref` (`asxos_agent_ro.gxjqezqndltaelmyctnl`) — here the DB privilege system is the real boundary. **Recommended.**
- **Hosted Supabase MCP** (`mcp.supabase.com`, PAT auth): the platform manages the connection and does **not** accept a custom role — its `read_only=true` is a platform-level toggle, not `asxos_agent_ro`. If this is what's actually mounted, the new role is *dormant defense-in-depth only* and the live control stays exactly the "prompt/config-enforced, not mechanical" class the original security review objected to.

It explicitly rejected `SET ROLE` as a mechanism ("the agent controls the SQL text and could `RESET ROLE` back... the connection must *authenticate as* the role, not switch into it").

### Coexistence, ordering, pre-checks, rollback (deliverables 3-4)

- Human/CLI/API/cron path is untouched — separate login role, not RLS (correctly ties back to CLAUDE.md rule #4, single-user/no-RLS).
- Migration number: `0038` (repo was through `0037_security_kind.sql` at the time).
- 5 pre-apply checks specified, including a `SECURITY DEFINER` audit (confirmed via grep: none exist in the repo's own migrations, but flagged that the DB is a shared project so out-of-band objects are possible).
- A 5-line post-apply acceptance test, including deliberately trying `SET default_transaction_read_only=off` before a write to prove the *privilege* boundary holds even with the guardrail defeated.
- A full rollback script (`DROP OWNED BY` + `DROP ROLE IF EXISTS`, with a `pg_terminate_backend` note for live sessions).

### Migration vs. infra split (deliverable 5)

Cleanly separated: everything in `0038` is migration (James applies via `mcp__supabase__apply_migration`, I5 tier). Password-setting, MCP re-pointing, and running the acceptance test are flagged explicitly as **infra, NOT in git**, owned by James outside the repo.

It closed by naming the residual risk not solved by this design: "the read surface still feeds untrusted RSS text (`regulatory_events`) into the agent — the role caps the *consequence* to read-only; it does not sanitize the *input*."

---

## 2. Where the transcript ends

It does **not** end mid-tool-call or mid-reasoning in any concerning sense — the final content block is a complete, well-formed markdown document ending in a "Sources:" list of three citations. One structural quirk to be aware of: every message in this transcript (all 79 lines, checked programmatically) has `stop_reason: None` — this is a property of how this particular transcript format logs streamed content blocks as separate JSONL lines under a shared message id, not a truncation signal specific to the final turn. The final two lines (78 = thinking block, 79 = text block) share message id `msg_011CcvFgbcV7NUeGa48TAtJP`, i.e. they're one assistant turn, and the text block is internally complete and coherent throughout (verified by reading start-to-finish).

There is no user/tool-result turn after line 79 — which is expected and correct for a subagent transcript: the final assistant message *is* the return value handed back to the orchestrating (main) session. The most likely explanation for "no completion notification" is that the notification itself was dropped somewhere in the harness, not that the agent failed to finish.

---

## 3. What it actually did along the way

Roughly linear, no dead-end thrashing. Sequence of research:

1. Read `docs/product/risk-register.md` (R2 definition), `.claude/rules/api-conventions.md` (migration conventions), `migrations/0034_governance_audit_trigger_and_revision_provenance.sql` (the trigger that is the actual attack surface), `docs/product/arbi-permission-model.md` (precondition 2 / autonomy gating).
2. Read `.claude/settings.json` (confirmed the agent tool allow-list only exposes `mcp__supabase-ro__execute_sql`, not the read-write tool).
3. `Glob migrations/*.sql` to see the full migration set; read `docs/next-session-backlog.md` around the R2 backlog entry.
4. Two `Glob` calls for `**/.mcp.json` and `**/mcp*.json` — both returned "No files found" (a genuine dead end: it was trying to find the MCP server config file to determine which of the two Supabase-MCP shapes is actually mounted, and the repo simply doesn't contain that config).
5. `Grep` across `migrations/0005_portfolio.sql` and the whole `migrations/` directory for `FUNCTION|TRIGGER|SEQUENCE` patterns, then read `set_active_profile()` directly to confirm it's `SECURITY INVOKER`.
6. `Grep` + `Read` on `asxos/db.py` to understand the app's own asyncpg connection path.
7. **Tool-availability probing:** tried `mcp__supabase-ro__execute_sql` twice (different queries — table list, then function/security-definer audit) and `mcp__supabase__execute_sql` twice (same two queries) — all four calls returned `<tool_use_error>Error: No such tool available</tool_use_error>`. This is the one place the agent hit a wall: **neither Supabase MCP tool was actually mounted in this subagent's session**, despite being referenced in `.claude/settings.json`'s allow-list. It recognized this after two attempts each (not an infinite retry loop) and explicitly said so in its next text block: "Both Supabase tools are unavailable in this session, so I'll ground the design in the migration files directly."
8. Pivoted cleanly to static grounding: broad `Grep` across all migrations for `CREATE TABLE|CREATE VIEW|GRANT|REVOKE|CREATE ROLE|ALTER DEFAULT PRIVILEGES` patterns (this is the existing precedent search — found the `stock_universe` view's `GRANT ALL ... TO anon, authenticated, service_role` pattern in migration 0029, which it later cited as a "watch out" in the design).
9. Read `asxos/config.py` (DB connection settings), migration 0029 (existing grant pattern), migration 0035 (`governed_active_theses` view), and grepped migration 0033 for the `governance_events` table shape.
10. `WebSearch` for "Supabase MCP server --read-only flag how it works" — this is where it went to compensate for the DB tools being unavailable and for not finding an MCP config file in-repo.
11. Two `WebFetch` calls: one to a GitHub Supabase discussion (succeeded, yielded the `role.project_ref` pooler username format it later cited), one to `supabase.com/docs/guides/ai-tools/mcp` (returned **HTTP 403 Forbidden** — a real failure, but non-blocking; it had already gotten what it needed from the GitHub discussion fetch).
12. Final confirmation greps: `REQUIRED_MIGRATIONS` value in `asxos/api/main.py` (91, informing the migration-numbering guidance) and a repo-wide grep for `SECURITY DEFINER` (no matches — informing the pre-apply-check #2 guidance that no such functions exist in-repo).
13. Wrote the final design (line 79).

No thrashing, no repeated identical calls, no going back to re-read the same file twice with the same args. The two genuine "dead ends" (missing `.mcp.json`, missing Supabase MCP tools, one 403'd WebFetch) were each recognized in 1-2 tries and the agent adapted its research strategy rather than looping.

---

## 4. Turn/tool-call count and loop check

- **79 total JSONL lines** (1 initial user task prompt + the rest assistant/user turns for tool round-trips and final text).
- **Tool calls: ~24** — `Read` ×11, `Glob` ×3 (one for migrations, two dead-end config searches), `Grep` ×9, `mcp__supabase-ro__execute_sql` ×2 (both errored — tool not mounted), `mcp__supabase__execute_sql` ×2 (both errored — tool not mounted), `WebSearch` ×1, `WebFetch` ×2 (one 403).
- **No looping / no stuck-agent red flags.** The only repeated-pattern calls are the 2×2 Supabase-tool probes, and those used *different queries* each time (table listing, then function/security-definer audit) rather than blindly repeating the same failing call — a reasonable "confirm it's really unavailable, not a fluke" pattern, and the agent stopped after 4 tries total and pivoted.
- Total elapsed wall-clock time in the transcript: `12:11:17.795Z` → `12:19:05.429Z`, roughly **7.5 minutes**.

---

## Bottom line for the orchestrating session

Nothing further needs to be recovered or re-run. The design is complete enough to become the draft `0038_agent_readonly_role.sql` migration and an accompanying design-doc PR for James, exactly as the original task requested. The one open engineering question the design itself surfaces (and which James/the main session should resolve before or alongside applying the migration) is **which shape `supabase-ro` actually is** — connection-string vs. hosted-PAT — since that determines whether this migration becomes the real security boundary or stays inert defense-in-depth until the MCP session is re-pointed.
