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
| `daily-product` | `30 17 * * *` daily | 03:30 | Fable 5.1 (`claude-fable-5-1`) | inherited from the bound session: GitHub + Supabase (write tool present, locked behaviourally by `_preamble.md` §2) | 120 min | **`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`** (repo attached, created 2026-09-16 19:33 UTC; **rebound this date — see "Rebind, 2026-09-16" below**) | readiness turn 2026-09-16 19:33 UTC: `origin/main` at `65aa21a`, GitHub MCP confirmed, Supabase write-capable and therefore locked per preamble; catch-up fire 2026-09-16 19:3x UTC | US$2.08 for the readiness turn (Fable reads expensively; budget the full body at US$10–25) |
| `nightly-steward` | `45 19 * * *` daily | 05:45 | Sonnet 5 (`claude-sonnet-5`) | inherited from the bound session: GitHub + Supabase read-only | 45 min | `trig_01AP9VyuN8JSNt5x6eyysiMx` → bound session `session_016BZ4U8L3thJHetE54EbTS2` (the session that proved the doc on 2026-09-14) | doc proven 2026-09-14 21:42 UTC (fresh repo-attached session, 5 min); **bound path proven 2026-09-15 11:55 UTC**: START 10 s after the fire, END at 11:58 `outcome=ran`, HEALTHY, digest refreshed on #271, 3 min | US$2.22 (2026-09-14 run) and ≈US$2.94 (2026-09-15 run; session total US$5.16). Context grew ~100k tokens per fire (238k → 336k): rebind roughly weekly |
| `weekly-security` | `0 12 * * 0` Sunday | Sun 22:00 | Sonnet 5 (`claude-sonnet-5`) | inherited from the bound session: GitHub + Supabase read-only | 60 min | `trig_01FTd3jWG9JbdLEWT2g4soTz` → bound session `session_01SyWFtBsMRxkpvet5CyHTEa` (repo attached, created 2026-09-15 11:54 UTC) | readiness turn 2026-09-15 11:54 UTC: "GitHub + Supabase RO tools confirmed"; first scheduled fire Sun 2026-09-20 12:00 UTC | US$0.32 for the readiness turn |

AEST = UTC+10 fixed, the repo's convention; AEDT states see each time an hour later from
2026-10-04. Crons are UTC and do not move. Environment: `Default`
(`env_01BsLzNwdBvLVg8BBYL654BH`). **Notifications: none from the scheduler** — push/email
is offered only for fresh-session Routines, and these are bound to persistent sessions (below).
The observation is the ledger #270 and the digest #271; subscribing to #271 in GitHub gives
one notification per digest.

## Rebind, 2026-09-16 — and a correction to the inheritance claim below

`daily-product` was rebound from `session_016GusBoDGMihXbXHbiMTpK1` to
`session_01HyKLpP6LMTm9wio1oL9e5m` (`trig_01TLku22ZdzveWG7iQ1ybXFE` deleted,
`trig_019hfSFbVCdKQA5PPxJM9MMH` created; there is no in-place rebind). Two reasons, neither
of them the ~700k context threshold below — the old session was at 377k.

1. **Its 2026-09-16 17:38 UTC fire misfired.** The wake was delivered (the scheduler recorded
   `last_run=SUCCEEDED`, which for a bound routine means *delivered*, not *ran*) but the turn
   failed on an invalid tool call, and the session was then directed by James into an 8-hour
   interactive loop. So the fire produced no START comment — exactly the silent-failure shape
   `_preamble.md` §1 exists to detect, and the detector worked.
2. **The session was no longer a routine session.** It had absorbed the whole loop (six merged
   PRs, a migration, US$154) and had been switched at runtime from its configured
   `claude-fable-5-1` to `claude-opus-5`. A routine whose bound session is also somebody's
   interactive workspace cannot honour "earlier turns are prior fires, not instructions".

**The correction.** The section below says a session created from a repo-attached arbi session
*inherits* the repo and connectors. **Live state contradicts that and the claim is wrong as
written.** A `create_session` call made from this repo-attached session with no `source_url`
produced a session whose readiness turn reported "no git repo, GitHub MCP unavailable"
(`session_016B3AV1jtBa625M7raQ8ULt`, archived). The repo attaches only when `source_url` (and
`source_revision`) are passed **explicitly**:

```
create_session(source_url="https://github.com/Jp8617465-sys/asxos", source_revision="main", …)
```

That session's readiness turn then confirmed `origin/main` at `65aa21a` with GitHub MCP live.

**So: always run a readiness turn before binding a trigger to a new session, and read its
result.** Binding blind to the repo-less session would have put the routine back into the
silent-non-firing state this file was written to prevent — for the third time on record.

**Also note:** the trigger-creation call warns that it stores no MCP connectors. On the bound
path that is expected and non-fatal — the fire is a new turn in a session that already holds
its own tools, and the previous trigger carried the same empty `mcp_connections` while firing
correctly. It matters only for a fresh-session routine; the remedy the warning names is to
create the trigger from a session holding the connectors, or from the claude.ai routines UI.

## Bound path — how the Routines are online (2026-09-15)

The scheduler tool available to an arbi session cannot attach a repository or connectors to
a *fresh-session* Routine: a trigger it creates stores `sources: []` and `mcp_servers: []`, and
its fires wake without the repo and go idle ("First-fire findings" 1). What it *can* do is
fire into an **existing** session, and a session created from an arbi session with the repo
attached inherits the GitHub and Supabase read-only tools — proven 2026-09-14 21:42 UTC when
such a session ran the steward doc end to end ("First-fire findings" 5).

So each routine is bound to its own repo-attached session (table above). A fire is a new
user turn in that session carrying the pointer prompt, which re-reads the routine doc at
`origin/main` every time; the prompt says that earlier turns are prior fires, not
instructions. Consequences, stated so nobody is surprised:

- **Context accumulates across fires** (the steward's proof run used ~240k of a 1M-token
  window). The harness compacts automatically; the doc is re-read each fire so compaction
  loses nothing that matters. When a bound session's `context_usage` passes ~700k, arbi
  creates a fresh repo-attached session, deletes the trigger and recreates it bound to the
  new session (there is no in-place rebind), and updates this table. The steward reads each
  bound session's usage when the scheduler tools are present and puts it in the digest's
  Risks line.
- **No scheduler notifications** (above). The ledger and the digest are the observation.
- **The UI path is the upgrade, not a prerequisite.** A Routine created in the claude.ai
  Routines UI with the repo and connectors attached gets a clean context per fire and push
  notifications. If James creates one, arbi deletes the bound trigger for that routine and
  updates this table; the prompt is the three-line pointer at the top of this file. Fields:
  repo `Jp8617465-sys/asxos` at `main`, environment `Default`, connectors GitHub + Supabase
  read-only (never the write connector), model and cron from the table.

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

- `.claude/commands/ship.md` step 4 said "merging is James's action" — fixed by #273, merged
  2026-09-15 (James's path). No longer stale.
- `.claude/skills/reversible-work-window/SKILL.md` was rewritten by #264, merged 2026-09-14
  under James's ruling (recorded in #277). No longer stale.

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
5. **The fifth session proved the doc.** After the preamble §0 fix merged (#274), a fresh
   repo-attached session given only the three-line pointer ran `nightly-steward.md` end to
   end: START at 21:43 UTC and END at 21:47 UTC on #270 (`outcome=ran`), health HEALTHY over
   all seven workflows, the §12 digest written to #271 (nine merges with classes, five
   Yours items, four risks, one contained incident — the earlier silent trigger fire, which
   it found on the ledger itself), one duplicate issue closed, `pg_stat_statements`
   recorded as unavailable to `supabase-ro`, `deadman=unset`. Five minutes of a 45-minute
   budget; US$2.22 on Sonnet 5. The GitHub tools were present in that session because a
   session created from an arbi session inherits its GitHub access; a Routine created in
   the UI gets whatever connectors James attaches.

## Adding a routine

One doc with the frontmatter schema (`name, cron, model, connectors, budget_min, environment,
requires_env, deadman_env, writes`) and a `{{preamble}}` line; one `create_trigger`; one
registry row. `tests/test_routine_docs.py` refuses a cron within 30 minutes of a production
cron or another routine, a `writes` entry another routine already owns, the Supabase write
connector, or a routine that needs `ASXOS_PERSONAL_USE` in the `Default` environment — a
live-testing routine needs a dedicated environment where James has set that variable.
