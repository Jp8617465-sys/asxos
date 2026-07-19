# Proposal: repoint 6 agent frontmatter files to the read-only Supabase connector

**Status:** proposed — arbi cannot apply this directly (`.claude/agents/` is authority-guarded;
`Edit`/`Write`/`MultiEdit` are denied unconditionally by `authority-guard.sh` regardless of
operating latitude granted in-session). James applies by hand or via an explicit future
authority-maintenance mode.
**Why now:** closes `m14_candidate_agent_db_role_scoping` / risk-register R2 — the last mechanical
step of the agent-DB-read-only-role precondition. Migration 0039 is applied, `asxos_agent_ro`
exists, `supabase-ro` MCP is live. Only the frontmatter pointer was never flipped.
**Honest caveat (found live this session, not theoretical):** `mcp__supabase-ro__execute_sql`
itself aborted 4/4 times this session with `AbortError: Tool permission stream closed before
response received`, despite being allow-listed (risk-register R16). This repoint is still correct
to make — it's the right connector even if its current reliability is poor — but do not treat it
as "agent reads now work end-to-end." R16 is a separate, likely session-harness-level issue, not
fixable by this repoint.

## Exact diff — 6 files, one line each (frontmatter `tools:`)

```diff
--- a/.claude/agents/thesis-coherence-guard.md
+++ b/.claude/agents/thesis-coherence-guard.md
@@ -1,5 +1,5 @@
 ---
-tools: Read, Glob, Grep, mcp__Supabase__execute_sql
+tools: Read, Glob, Grep, mcp__supabase-ro__execute_sql
```

```diff
--- a/.claude/agents/thesis-milestone-monitor.md
+++ b/.claude/agents/thesis-milestone-monitor.md
@@ -1,5 +1,5 @@
 ---
-tools: Read, Glob, Grep, mcp__Supabase__execute_sql
+tools: Read, Glob, Grep, mcp__supabase-ro__execute_sql
```

```diff
--- a/.claude/agents/macro-economist.md
+++ b/.claude/agents/macro-economist.md
@@ -1,5 +1,5 @@
 ---
-tools: Read, Glob, Grep, mcp__Supabase__execute_sql
+tools: Read, Glob, Grep, mcp__supabase-ro__execute_sql
```

```diff
--- a/.claude/agents/market-context-narrator.md
+++ b/.claude/agents/market-context-narrator.md
@@ -1,5 +1,5 @@
 ---
-tools: Read, Glob, Grep, mcp__Supabase__execute_sql
+tools: Read, Glob, Grep, mcp__supabase-ro__execute_sql
```

```diff
--- a/.claude/agents/portfolio-coherence-reviewer.md
+++ b/.claude/agents/portfolio-coherence-reviewer.md
@@ -1,5 +1,5 @@
 ---
-tools: Read, Glob, Grep, mcp__Supabase__execute_sql
+tools: Read, Glob, Grep, mcp__supabase-ro__execute_sql
```

```diff
--- a/.claude/agents/benchmark-performance-analyst.md
+++ b/.claude/agents/benchmark-performance-analyst.md
@@ -1,5 +1,5 @@
 ---
-tools: Read, Glob, Grep, mcp__Supabase__execute_sql
+tools: Read, Glob, Grep, mcp__supabase-ro__execute_sql
```

## Secondary, cosmetic (same files + README, body prose — not functional, just accuracy)

- `macro-economist.md:126` and `market-context-narrator.md:82`: "Although `mcp__Supabase__execute_sql`
  can write, you run **read-only**..." → update the tool name in the sentence to
  `mcp__supabase-ro__execute_sql` (the sentence's *point* — SELECT-only discipline — no longer
  needs the caveat once the connector itself can't write; simplify or keep as defense-in-depth
  documentation, James's call).
- `.claude/agents/README.md:100,147`: same cosmetic tool-name update.

## After applying

Have `security-engineer` (or a follow-up mission) add the CI policy test recommended in the
dossier reconciliation: fail CI if any file under `.claude/agents/` matching the
discovery/analysis agent set references `mcp__Supabase__execute_sql` (write-capable) instead of
`mcp__supabase-ro__execute_sql`. That test lives in `tests/` (not authority-gated) and IS something
arbi can build and land as a normal draft PR — planned as a near-term follow-up, separate from this
frontmatter change itself.
