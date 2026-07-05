# PR 2A — `supabase-ro` provisioning-route decision (2026-07-05)

**Status:** current
**Scope:** agent DB read-only scoping — provisioning-route decision only (no implementation)
**Last verified:** 2026-07-05 against repo @ `claude/supabase-ro-connector-check-jizp49` + the live-fire battery run this session
**Read priority:** read first (with `docs/live-readiness-audit-plan-2026-07-04.md` §7 and `docs/model-a-audit-and-extension-plan-2026-07-04.md` Part B) until the §4 feasibility questions are answered and a route is chosen
**Superseded by:** N/A

Governs the **route/provisioning** half of `m14_candidate_agent_db_role_scoping`
(`.claude/rules/portfolio-conventions.md`). The **enforcement design** is unchanged and
still lives in `docs/live-readiness-audit-plan-2026-07-04.md` §7 (Candidate A) and
`docs/model-a-audit-and-extension-plan-2026-07-04.md` Part B — this document only
decides *which transport/provisioning route* carries that design, because the route
first tried is transport-unstable.

---

## 0. Why this exists

PR 2 moves six read-only investment/discovery agents — `macro-economist`,
`market-context-narrator`, `thesis-coherence-guard`, `thesis-milestone-monitor`,
`portfolio-coherence-reviewer`, `benchmark-performance-analyst` — off the
**write-capable** `mcp__Supabase__execute_sql` they still carry
(`.claude/agents/*.md:4`, all six) onto a server-side-enforced read-only path. This
closes a real governance-bypass surface: an injected/misbehaving agent can today emit
the `governance_events`-INSERT-then-`UPDATE … governance_status='approved'` pair
(`asxos/domain/governance/transitions.py:66-88`) that the `BEFORE UPDATE` audit
triggers (`migrations/0034`, `0036`) authenticate by transaction **shape, not author**
— reaching `approved` with no human in the loop.

A live-fire enforcement battery was started against a hosted/custom `supabase-ro`
connector (provisioned in the claude.ai connector layer — there is no in-repo
`.mcp.json`, and `.claude/settings.json` has no MCP config):

| Group | Result | Evidence |
|---|---|---|
| **1 — identity + txn escape** | **PASS** | `current_user = supabase_read_only_user`; `transaction_read_only = on`; `SET TRANSACTION READ WRITE` flips the txn flag but INSERT still fails **`42501`** (grant floor); session/default overrides fail `25006`; no write succeeded |
| **2 — write/DDL denial** | **PASS** | UPDATE / DELETE / CREATE TABLE all denied (`25006`); `to_regclass(...)` NULL — no residue |
| **3 — escape/exfil shapes** | **INCOMPLETE** | connector dropped at the **transport** layer on `SET ROLE postgres` ("permission stream closed before response received" — no SQLSTATE). Same failure mode that blocked the prior session. |

**Cross-agent finding** (routed per the CLAUDE.md delegation policy: `system-architect`
lead; `backend-architect`, `security-engineer`, `tech-stack-researcher`; 2 Explore
passes): the database **enforcement model is probably sound** (grant-based `42501`,
observed on plain INSERT); the failure is **transport / proxy / session instability**
on the claude.ai custom-connector path, traced to open Anthropic defects on
`mcp-proxy.anthropic.com`:
- OAuth token never refreshed on the proxy path (claude-ai-mcp#228 — fixed for Claude
  Code's *direct* path, never ported to the web-proxy path);
- stale `Mcp-Session-Id` after any upstream restart (claude-code#48557 — no workaround);
- permission-stream idle abort (claude-code#60042).

These are **not tunable into reliability** on that path. The decision below is therefore
a *route* change, not a retry.

---

## 1. Decision

**Do not** keep retrying Group 3 on the current hosted/custom connector, and **do not**
flip the six frontmatters onto it. Choose the provisioning route by the §4 feasibility
answers, re-run the full §5 battery on the chosen route, and only then proceed to PR 2B.

**Route ranking:** 1 local-stdio (recommended) → 2 direct-HTTP (fallback) → 3 hosted
custom (retire) → 4 direct Postgres role (reject for agents; use for the canary).

---

## 2. Route evaluation

Legend per route: **stability** (does it fix the drop?) · **enforcement** (grant `42501`
vs escapable `25006`) · **secret/PAT exposure** · **versionable config / restores
source-of-truth** · **risks** · **operator steps**.

### Route 1 — local-stdio `supabase-ro` — RECOMMENDED (conditional on §4)
- **Stability:** fixes the drop *by construction* — no HTTP/SSE/OAuth/`Mcp-Session-Id`.
  The server subprocess reaches Supabase over the **Management API (HTTPS)** using the
  PAT + `--project-ref` (not raw Postgres wire), so it needs only the HTTPS egress this
  environment already has. #228 / #48557 / idle-abort are all inapplicable.
- **Enforcement:** strong — same `@supabase/mcp-server-supabase` package; `--read-only`
  selects the managed `supabase_read_only_user` (grant-based `42501`). **Must be
  re-probed** — the `42501` floor was measured only on the hosted connector and does not
  transfer by assumption.
- **Secret/PAT exposure:** PAT in `env` only, as a `${SUPABASE_ACCESS_TOKEN}` reference.
  Failure mode to prevent: a *literal* token inlined into a checked-in `.mcp.json` or a
  `Read`-reachable `.env`. Mitigate with `${VAR}` refs only + a `Read` deny-glob.
- **Versionable / source-of-truth:** **yes, uniquely** — a checked-in `.mcp.json` is
  reviewable + drift-checkable, restoring CLAUDE.md non-negotiable #2 that the invisible
  hosted connector violates.
- **Risks:** (a) supply chain — `npx` fetches/executes the server at launch → **pin an
  exact version, never `@latest`** on a security-boundary component; (b) the sandbox
  must support subprocess spawn *and* honor a repo `.mcp.json` (§4 #1/#2); (c) **naming
  trap** (claude-code#21368): a server named literally `supabase` is forced back onto
  SSE — `supabase-ro` is safe, do not rename it.

### Route 2 — platform-managed / Claude Code **direct-HTTP** — FALLBACK
- **Stability:** partial — the direct-HTTP path gets the token-refresh fix missing from
  the proxy path, but stays SSE-class (idle timeout; OAuth reconnect edge cases). Only
  better if registered as **Claude Code direct HTTP**, *not* as a claude.ai custom
  connector (which re-inherits #228/#48557).
- **Enforcement:** strong (`?read_only=true` → same managed role); re-probe.
- **Secret/PAT exposure:** OAuth, no PAT to hold (good) — but the interactive OAuth flow
  may be hard/impossible to complete headless in the sandbox.
- **Versionable:** URL can live in `.mcp.json`; OAuth state stays off-repo.
- **Risks:** SSE idle drops persist; OAuth-in-sandbox feasibility; `?read_only=` query
  param is the top fail-open surface (one char → read-write; the canary is the only
  detector).

### Route 3 — current hosted/custom connector — REJECT / RETIRE
- Structurally broken (proxy defects above), not operator-fixable; invisible
  connector-layer state with no drift check. Do not flip frontmatters onto it; do not
  keep probing it.

### Route 4 — direct Postgres read-only role, no MCP — REJECT for agents; USE for the canary
- Strongest floor (native GRANTs, `42501` by construction, fails **closed** on
  misprovision) — but **agents have no Postgres wire access** (HTTPS-only egress via the
  agent proxy), so they cannot open a raw connection; a generic Postgres MCP in front
  just reintroduces the transport question.
- **Where it is right:** the **runtime canary** (PR 2C) and any future `asxosctl_ro`
  run on **Render** with real egress and *can* open a direct connection as the
  read-only role. A role + `GRANT` is not RLS, so this does not touch non-negotiable #4.

---

## 3. Recommended `.mcp.json` shape (if Route 1 is viable)

```json
{
  "mcpServers": {
    "supabase-ro": {
      "command": "npx",
      "args": [
        "-y", "@supabase/mcp-server-supabase@<PINNED_EXACT_VERSION>",
        "--read-only",
        "--project-ref=gxjqezqndltaelmyctnl",
        "--features=database"
      ],
      "env": { "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}" }
    }
  }
}
```

Rules baked in: **pin an exact version** (never `@latest`); **`${VAR}` token reference
only** (never a literal token in this file); **name it `supabase-ro`** (never
`supabase`); `--features=database` strips non-DB management surface. The write-capable
`Supabase` server stays configured for the main loop / human CLI only (the documented
`apply_migration` + manual `approved_for_allocation` path).

---

## 4. Feasibility questions James must answer (gates the route)

1. **Can Claude Code Web / this sandbox honor a repo `.mcp.json`?** (project-scoped MCP
   config read at session start.) → decides whether config can be versioned in-repo.
2. **Can this environment spawn a local stdio server via `npx`?** (node/npx present,
   subprocess launch allowed.) Check `claude mcp list` / `/mcp`, and whether the current
   write `supabase` server is *itself* already stdio-via-npx (strong signal). → decides
   Route 1 vs Route 2.
3. **Can the PAT be injected as an env var that agents cannot `Read`?** Confirm
   `SUPABASE_ACCESS_TOKEN` lives in env only, not in any `Read`-reachable file — the six
   agents hold `Read` and `.claude/settings.json` currently has no permission scoping.
4. **Can `supabase-ro` be pre-approved** (auto-allow) to remove the per-call
   permission-approval round-trip? (The most us-addressable root cause; safe for a
   read-only tool because the DB enforces read-only regardless of the prompt.)

**Decision rule:** if questions 1, 2 and 3 all hold → **Route 1** (local-stdio);
otherwise → **Route 2** (direct-HTTP). Question 4 (pre-approval) applies to whichever
route is chosen.

---

## 5. Live-fire battery to re-run on the CHOSEN route

The `42501` floor was observed **only** on the hosted connector and does **not** transfer
by assumption — re-run everything through the real `mcp__supabase-ro__execute_sql`, all
writes in rolled-back transactions.

**P0 (all must pass before any frontmatter flip):**
1. **Identity:** read-only role; from `pg_roles`, `rolsuper = false` AND
   `rolbypassrls = false`.
2. **Denial code:** writes are refused with **`42501`, not `25006`**, on *every* refused
   shape. A `25006`-only result is WARN / do-not-ship (escapable via `SET TRANSACTION
   READ WRITE`).
3. **Governance pair:** `INSERT governance_events …; UPDATE macro_theses SET
   governance_status='approved' …` fails **at the INSERT** (`42501`) — one layer before
   the trigger evaluates.
4. **Escape shapes denied:** `SET ROLE postgres/service_role`; `SET TRANSACTION READ
   WRITE` / `SET default_transaction_read_only=off` / `RESET ALL`; write-in-CTE
   (`WITH w AS (INSERT … RETURNING 1) SELECT …`); `DO $$ … UPDATE … $$`;
   `SELECT set_active_profile(<id>)` (an INVOKER function — its internal UPDATE must
   fail under the read-only caller).
5. **`SECURITY DEFINER` inventory empty:** `SELECT proname FROM pg_proc WHERE prosecdef;`
   on the **shared** DB (repo grep already clean; the project shares ~165 tables, so the
   live catalog must be checked, not just the repo).
6. **Management tools absent:** confirm `mcp__supabase-ro__apply_migration` /
   create_branch / deploy are **not registered** — the `-ro` boilerplate still advertises
   `apply_migration`, so verify, don't assume.
7. **Exfil surface refused:** `COPY … TO/FROM PROGRAM`, `pg_read_server_files()`,
   `lo_import/lo_export`, `CREATE FUNCTION`.
8. **Vault probe:** the read-only role **cannot** `SELECT vault.decrypted_secrets` (if it
   can, exfil escalates from financial data to actual secrets — a different severity
   class). Record what it *can* see of `supabase_migrations` / system catalogs.

**Operational gate:** the connector must survive its **own battery in one session with
zero transport drops**, and survive a repeated 5-agent concurrent fan-out. "Stable" =
"runs the burst to completion, repeatedly."

**Regression:** replay the governance pair via the **write** server in `BEGIN; … ROLLBACK;`
— it must still succeed, proving the read-only addition did not perturb the human path.

---

## 6. Stop / go gate

**No frontmatter flip until the chosen route passes the full §5 battery.** Groups 1–2
alone do **not** clear it, and evidence from the hosted connector does **not** count for a
different route. Fixed order:

```
register supabase-ro (chosen route)
  → live-fire §5 (P0 all pass, 42501 not 25006, zero transport drops)
  → runtime canary live (PR 2C)
  → PR 2B (single, atomic): flip the six .claude/agents/*.md:4 lines to
      mcp__supabase-ro__execute_sql AND land the CI allowlist guard in the SAME PR
      — the guard is red until the flip (it fails while any agent still grants the
      write tool), so the two cannot be sequenced across PRs; they land together
```

**Never** add a write-tool fallback path (falling back to `mcp__Supabase__execute_sql`
on an RO failure silently reopens the exact bypass this closes).

---

## 7. Separate tickets discovered during the investigation (NOT PR 2 blockers)

1. **Backup fix — PRIORITISE (ahead of everything except the `supabase-ro` gate).**
   `scripts/backup_irreplaceable.sh:49-57` backs up 9 tables (`holding_lots`,
   `decisions`, `screening_rules`, `model_versions`, `profiles`, `themes`, `theses`,
   `thesis_revisions`, `theme_holdings`) but **omits** `macro_theses`, `agent_runs`,
   `agent_evidence`, `governance_events` — all four labelled *irreplaceable* in
   `CLAUDE.md`. Those governance tables are currently **not backed up**. Own PR.
2. **`/pm-review` tool-error vs data-absent semantics.** `.claude/commands/pm-review.md`
   treats a missing agent result as ordinary absence (`:33-35` "record that gap"; `:77-78`
   downgrade to "evidence-thin" only if **≥2** report no data). A connector drop is
   indistinguishable from legitimate absence, so one dropped agent can yield a *confident*
   GOOD-HOLD / EXIT-CANDIDATE verdict on 4 of 5 inputs, unflagged. Prose-only fix:
   transport/tool error → abort loudly and re-run; genuine absence → synthesize around.
   Own PR (mirror in `discover-macro.md`).
3. **Runtime canary design (→ PR 2C).** Render cron `jobs/check_read_only_canary.py`,
   reusing `JobMonitor` (`asxos/jobs/utils/job_monitor.py`) + the Healthchecks deadman +
   the `jobs/check_cron_health.py` Resend `_send_alert`; opens a **separate** connection
   **as the RO principal** (not the write pool); asserts identity / `is_superuser` and
   that a rolled-back INSERT raises **`42501`** (alert if it *succeeds* OR if it is
   `25006`). Add `healthcheck_url_check_read_only_canary` to `asxos/config.py`; add a new
   `type: cron` in `render.yaml` modeled on `asxos-check-cron-health`. Runs on Render
   (egress), not the sandbox. **Honest ceiling:** it catches the role *gaining write
   grants*; it cannot see the server *re-registered without `--read-only`* — that still
   requires re-running §5 after any MCP-config change.
4. **CI tool-allowlist guard (→ PR 2B).** A pytest over `.claude/agents/*.md` frontmatter
   that fails if any of the six grants `mcp__Supabase__execute_sql` or any DB tool other
   than `mcp__supabase-ro__execute_sql`, and bans `Bash|WebFetch|WebSearch` on them —
   enumerating *all* agents so a Phase 2c agent can't slip the net. Model on
   `tests/test_cron_pool_init.py` (glob+parse) / `tests/test_migration_0029_market_cap.py`
   (regex-grep); runs via `.github/workflows/full-check.yml`. Necessary but weak (string,
   not runtime) — the canary covers what it can't. Optional sibling: a `SECURITY DEFINER`
   grep over `migrations/*.sql` (starts green).

---

## 8. Recommended PR split

| PR | Contents | Gate |
|---|---|---|
| **PR 2A** (this doc) | Provisioning-route decision — routes, `.mcp.json` shape, §4 questions, §5 battery, §6 gate, ticket list. **Docs only.** | now |
| **PR 2B** | Stable-route full-battery evidence + six frontmatter flips + CI allowlist guard + prose updates (retire "SELECT-only convention" → "technically enforced") | after §6 gate passes |
| **PR 2C** | Runtime canary job + `config.py` field + `render.yaml` cron + test | after route chosen; **live before the §6 flip** |
| **Backup fix** | Add the 4 governance tables to `backup_irreplaceable.sh` | now, separate, **prioritised** |
| **PM-review fix** | Tool-error vs data-absent semantics in `pm-review.md` (+ `discover-macro.md`) | now, separate |

---

## 9. Out of scope for PR 2A (do not do here)

Register any server; run any live-fire probe; flip any frontmatter; use the write-capable
`mcp__Supabase__execute_sql`; call `apply_migration`; or edit any code. PR 2A is this
decision doc and nothing else. Group 3 was **not** retried on the hosted connector, and
the §6 gate blocks PR 2B until a chosen route passes the full §5 battery.
