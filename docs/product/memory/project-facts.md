# arbi project-facts memory

**Status:** current
**Scope:** durable facts arbi should know that outlive a session (`AGENTS.md` §10)

Two kinds of entry live here. The first is a **pointer index** — the fact already has an
authoritative home, and duplicating it would create a second editable copy. The real files
win over the pointer. The second is a **standing fact** that has no other home, usually
because the mechanism that used to encode it was retired.

## Durable repo facts (follow these)

- **The docs source-of-truth map:** `../../README.md`
- **Agent authority and operating contract:** `../../../AGENTS.md`
- **Agent guide + stack + schema overview + delegation policy:** `../../../CLAUDE.md`
- **Auto-attaching conventions:** `../../../.claude/rules/` (`api-`, `ml-`, `job-`, `portfolio-conventions.md`)
- **Specialist roster + the canonical owner→agent table:** `../../../.claude/agents/README.md`
- **Current program state (reconciled):** `../roadmap-state.md`
- **Live-state probes:** `/sprint-state` + `/catchup` (git/PR/CI · Supabase-ro · GitHub Actions)
- **Schema is the migrations:** `../../../migrations/` (canonical; check
  `supabase_migrations.schema_migrations` for what is live, never the directory listing)
- **Tax spec source of truth:** `../../foundation/spec/tax-alpha.md`
- **Known sandbox test gaps (do not chase):** `../../../CLAUDE.md` (## Known test environment gaps)
- **CI: `full-check` (ruff 0.7.0 + mypy + pytest) + `targeted-ml-tests`.** Pin dev ruff to
  **0.7.0** to match CI (`lessons.md` L3).

## Standing facts about the tooling

Both were found by the `security-engineer` review on 2026-08-12 (findings H1 and H2) and
verified live against the hook that then enforced them. That hook was retired on 2026-09-10
with the rest of the guard set, so these are now facts arbi carries rather than rules
anything blocks. They are the reason two convenient-looking commands are the wrong reach.

- **`gh run rerun` re-injects a prior run's secrets.** It re-executes a previous run with all
  of its secrets available again, for up to 30 days, on **any** workflow — a strictly wider
  reach than dispatching a named lane, and not "read-only" in any sense. Re-dispatch the lane
  explicitly instead: `gh workflow run <lane>.yml --ref <branch>`.
- **`gh workflow run` plus command substitution smuggles an inner dispatch.** Command
  substitution is not a segment separator, so
  `gh workflow run backup.yml $(gh workflow run daily-brief.yml)` fires the *inner* workflow
  first, and a prefix-matching allow rule only ever sees the outer string. Never build a
  dispatch command out of substituted output; name the workflow literally.

## Standing facts about the infrastructure (verified 2026-09-14)

Each line names the probe that produced it. Re-probe before trusting a date-stamped fact.

- **Supabase plan is `pro`** — `mcp__Supabase__get_organization` on org `dukwxpqbrpjctjyugcek`
  returned `"plan": "pro"` on 2026-09-14 (James upgraded that day). `CLAUDE.md:38` still says
  "free tier" — stale, in the residue sweep. `BUILD_GUIDE.md`'s "downgrade Pro → free at M1"
  lines are dated history and stay as written. Pro includes scheduled daily backups; **PITR
  is a separately-priced add-on, not included** — do not write "7-day PITR" into any runbook
  without confirming it in the dashboard, which arbi cannot read.
- **Postgres engine is 17** (`17.6.1.063`, release channel `ga`) — `mcp__Supabase__get_project`
  on `gxjqezqndltaelmyctnl`, 2026-09-14. `backup.yml:6` already says 17 (verified 08-10);
  `CLAUDE.md:38` says 16 — stale, same sweep.
- **Both Actions secrets now exist**, created by James on 2026-09-14: `ARBI_GITHUB_TOKEN`
  (fine-grained PAT, `asxos` only, Actions / Contents / Issues / Pull requests / Workflows
  read-write, 90-day expiry — **it expires silently; every lane fails at checkout with no
  other symptom**) and `SUPABASE_ACCESS_TOKEN` (scoped token, one project: Migrations RW,
  Database / Logs / Advisors / Project Settings R). No `schedule:` is armed yet (A-22).
- **Supabase personal access tokens are now scoped** (public alpha, on James's account) —
  the rollout's "all-or-nothing" framing is out of date. Permission→tool table:
  `https://supabase.com/docs/guides/platform/personal-access-tokens` (`apply_migration` =
  Migrations RW; `execute_sql` = Database R).
- **James's laptop has the writable Supabase MCP** via the hosted server
  (`https://mcp.supabase.com/mcp?project_ref=gxjqezqndltaelmyctnl`, OAuth, `--scope user`),
  alongside `supabase-ro`. Convention: reads through `supabase-ro`; the writable server only
  when the task needs a write. Verified against head `20260903025557` on 2026-09-14.
- **Drift:** `.github/runner/claude-user-settings.json:16` still grants "Editing files under
  `.claude/` and `.github/workflows/`" to the headless lanes — written in #254, missed by #256,
  which reserved `.claude/**`. `.github/**` is arbi's; first item on the next wake.

Update this file when a durable convention is added or moved, or when a fact like the two
above would otherwise be lost with the mechanism that encoded it.
