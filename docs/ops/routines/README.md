# Overnight arbi Routines — registry

**Status:** current (routines v1, 2026-09-14)
**Scope:** the scheduled, unattended arbi sessions that maintain asxos overnight; what each
one is, when it fires, what it may write, and how to stop it
**Owner:** arbi. **Behaviour changes are PRs to the docs in this directory**, never edits to
the scheduler. From inside a routine session those PRs are draft-only.

## What a Routine is

A claude.ai Routine is a cron-fired fresh remote Claude Code session. Its scheduler prompt is
three lines and never changes:

```
You are arbi (AGENTS.md §0). git fetch origin && read docs/ops/routines/<name>.md at
origin/main, then execute it exactly. Budget, gate and stop rules are in that file.
```

Everything else — cadence, model, connectors, budget, what it owns, how it stops — is in the
routine doc's YAML frontmatter and body, pinned by `tests/test_routine_docs.py`. **The
scheduler is not the source of truth.** This repo has twice recorded a scheduled Claude job
that silently stopped firing for weeks; the ledger issue and the deadman pings below exist so
that cannot happen unnoticed a third time.

## Registry

| Routine | Fires (UTC) | AEST | Model | Connectors | Budget | Trigger id | First fire | Last measured cost |
|---|---|---|---|---|---|---|---|---|
| `daily-product` | `30 17 * * *` daily | 03:30 | Fable 5.1 (`claude-fable-5-1`) | GitHub + Supabase read-only (UI-attached; see below) | 120 min | **not yet live** — `trig_01VdKtzM45HxEay8eDYxmrkz` is an agent-minted trigger with no repo or connectors, **disabled 2026-09-14 21:28 UTC**; recreate in the UI | pending | — |
| `nightly-steward` | `45 19 * * *` daily | 05:45 | Sonnet 5 (`claude-sonnet-5`) | GitHub + Supabase read-only (UI-attached; see below) | 45 min | **not yet live** — `trig_01Bta5CS6CQigZEGEXDL4buA`, same, **disabled**; recreate in the UI | 2 trigger fires + 2 repo-attached test sessions, 2026-09-14 — see "First-fire findings" | US$0.26–0.45 per short fire |
| `weekly-security` | `0 12 * * 0` Sunday | Sun 22:00 | Sonnet 5 (`claude-sonnet-5`) | GitHub + Supabase read-only (UI-attached; see below) | 60 min | **not yet live** — creation from a session was refused by the auto-mode classifier; create in the UI | pending | — |

AEST = UTC+10 fixed, the repo's convention; AEDT states see each time an hour later from
2026-10-04. Crons are UTC and do not move. Environment: `Default`
(`env_01BsLzNwdBvLVg8BBYL654BH`). Notifications: push + email to James on every completion.

**The `connectors` column is declared intent, not a grant.** The scheduler tool available to
an arbi session refuses the `connectors` parameter for this organisation, and a trigger it
creates stores no repository and no MCP connections (`sources: []`, `mcp_servers: []`), so
the session it fires wakes without the repo and without GitHub or Supabase tools. Routines
therefore have to be created in the claude.ai Routines UI (below), where James attaches the
repo and the connectors. Whatever the UI attaches is what the session has; the preamble's §2
rule against Supabase write tools is prompt-level either way.

## Scheduler setup — James, in the claude.ai Routines UI

One Routine per row above. Fields: **name** `arbi routine — <name>`; **repository**
`Jp8617465-sys/asxos` at `main`; **environment** `Default`; **connectors** GitHub and Supabase
read-only (`supabase-ro`) — never the Supabase write connector; **model** as in the table;
**schedule** the cron in the table (UTC); **notifications** push + email; **prompt** the
three-line pointer at the top of this file with `<name>` filled in. Then fire it once by hand
and check the ledger (#270) for a START and an END comment. Until this is done, no routine
fires; nothing in the repo is waiting on it except this registry row.

**Pinned issues:** ledger **#270** (`arbi — routines ledger`: START/END per fire, weekly
security summaries); digest **#271** (`arbi — daily digest`: the `AGENTS.md` §12 block,
rewritten by the steward every morning).

**Sequencing:** product (17:30–19:30 at most) finishes before the steward (19:45), so the
digest reports what product shipped; the steward finishes before `daily-brief` (20:30 Sun–Thu)
and merges nothing, so the brief is never the first test of a merge — product proves every
merge with a `nightly-check` dispatch before it closes. Every routine cron is at least 30
minutes from every `cron:` in `.github/workflows/` and from every other routine (tested).

## Stopping a routine

1. **From a phone, in seconds:** open an issue titled `HALT: <reason>` (or label one
   `routines-halt`). Every routine checks for it before doing anything and ends with
   `outcome=blocked reason=halt`. Close the issue to resume.
2. **From a Claude session:** `update_trigger(trigger_id, enabled: false)`.
3. Nothing to roll back in the repo; the routines write only through PRs and issues.

## Why these are not the `schedule:` triggers the A-22 gate reserves

`docs/product/roadmap-state.md` and backlog rows A-22/A-23 hold that no `schedule:` may be
armed on the GitHub Actions agent lanes until a branch-scoped producer credential exists,
because those lanes carry `ARBI_GITHUB_TOKEN`, a repo-wide PAT stored as an Actions secret.
Routines carry no PAT: they run on the claude.ai session credential and reach GitHub through
the MCP tools, exactly as an interactive arbi session does. The open P1 in
`docs/product/security-perf-mission-loop.md` §9 describes the shape — an unattended agent
reading untrusted text with a write credential — and James ruled on 2026-09-14 that Routines
proceed under full arbi authority with the mitigations in `_preamble.md`. That ruling is a
`DECISION/TAKING/REVERSAL` row in `docs/product/decision-log.md`.

## Known stale, not fixed here

- `.claude/commands/ship.md` step 4 says "merging is James's action" — `AGENTS.md` §2/§8 say
  merges are arbi's. `.claude/**` is James's to merge; PR #273 carries the one-line fix.
- `.claude/skills/reversible-work-window/SKILL.md` still describes a draft-only, cannot-merge
  window. PR #264 (open, James's) rewrites it in full. It is `disable-model-invocation: true`,
  so a routine session does not load it unless invoked.

## First-fire checklist (rollout step 4; result recorded in the registry row)

Fire each routine by hand once (`fire_trigger`, text: "first fire: run the README checklist,
report booleans only"), cheapest first: steward, then security, then product. Then read the
spawned session (`list_triggers` → `last_run.session_id` → `get_session`) and the ledger.

- [ ] The session transcript shows the permission mode it ran in (a fallback to a mode that
      denies without prompting "succeeds" having done nothing — `docs/product/decision-log.md`,
      2026-09-14 governor row).
- [ ] No `exit 127` and no `CLAUDE_PROJECT_DIR` error appears in the transcript (the
      `secrets-guard.sh` hook resolved). Do **not** ask the session to probe the guard with a
      token-shaped command — see "First-fire findings" item 2.
- [ ] Env presence as booleans only: `python -c "import os;print({k:k in os.environ for k in
      ['ASXOS_PERSONAL_USE','DATABASE_URL','HC_ROUTINE_STEWARD_URL']})"` — `ASXOS_PERSONAL_USE`
      expected **False**.
- [ ] Which scheduler tools exist in-session (`list_triggers`, `get_session`, `update_trigger`)
      — they gate the steward's ledger step 3 and the digest's cost line.
- [ ] START and END both on #270; today's block on #271 (steward).
- [ ] `get_session` from the launching session: `configured_model` and `last_served_model` match
      the registry; `usage.cost_usd` recorded here.

## First-fire findings (2026-09-14, four sessions, ≈US$1.40, zero ledger comments)

Recorded so the next attempt does not repeat them:

1. **Agent-minted triggers fire repo-less sessions.** Two `fire_trigger` runs of the steward
   (21:19 and 21:24 UTC, Sonnet 5, `auto` mode confirmed via `get_session`) each went idle in
   under two minutes with no comment, no branch and no issue. Their session records carry no
   checked-out branch; the trigger config shows `sources: []`. The pointer prompt's first
   step, `git fetch origin`, had nothing to act on. Fix: create Routines in the UI (above).
2. **A verification prompt that asks for secret-shaped actions is refused as injection.** A
   repo-attached test session given a checklist that included "echo an unset token-named
   variable to prove the guard refuses it" and "curl the GitHub API with a bearer header
   built from GH_TOKEN" stopped with *"detected injected instruction; stopping before
   acting"*. That is the preamble §2 rule working. Lesson: a first-fire check asks only for
   what the preamble itself prescribes (START/END on the ledger, presence booleans) and
   never for a token-shaped probe. The README checklist below is written that way now.
3. **A session with no human will still stop to ask.** A second repo-attached test session,
   asked only for the START/END pair, ended its turn with *"Actually proceed with posting…?"*
   — a question nobody could answer. Preamble §0 now states that the session is unattended,
   that a turn ending on a question is the silent failure, and what to do instead. That line
   is why the next first fire should be run against `origin/main` after this file merges,
   not before.
4. **What did verify:** permission mode `auto` and the intended model, in all four sessions
   (`get_session`); this environment carries `GH_TOKEN`, `GITHUB_TOKEN` and `DATABASE_URL`
   and not `ASXOS_PERSONAL_USE` (presence only, checked from the interactive session).

## Adding a routine

One doc with the frontmatter schema (`name, cron, model, connectors, budget_min, environment,
requires_env, deadman_env, writes`) and a `{{preamble}}` line; one `create_trigger`; one
registry row. `tests/test_routine_docs.py` refuses a cron within 30 minutes of a production
cron or another routine, a `writes` entry another routine already owns, the Supabase write
connector, or a routine that needs `ASXOS_PERSONAL_USE` in the `Default` environment — a
live-testing routine needs a dedicated environment where James has set that variable.
