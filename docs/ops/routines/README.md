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
| `daily-product` | `30 17 * * *` daily | 03:30 | Fable 5.1 (`claude-fable-5-1`) | `supabase-ro` | 120 min | pending (rollout step 3) | pending | — |
| `nightly-steward` | `45 19 * * *` daily | 05:45 | Sonnet 5 (`claude-sonnet-5`) | `supabase-ro` | 45 min | pending (rollout step 3) | pending | — |
| `weekly-security` | `0 12 * * 0` Sunday | Sun 22:00 | Sonnet 5 (`claude-sonnet-5`) | `supabase-ro` | 60 min | pending (rollout step 3) | pending | — |

AEST = UTC+10 fixed, the repo's convention; AEDT states see each time an hour later from
2026-10-04. Crons are UTC and do not move. Environment: `Default`
(`env_01BsLzNwdBvLVg8BBYL654BH`). Notifications: push + email to James on every completion.

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
  merges are arbi's. `.claude/**` is James's to merge; a draft PR carries the fix.
- `.claude/skills/reversible-work-window/SKILL.md` still describes a draft-only, cannot-merge
  window. It is `disable-model-invocation: true`, so a routine session does not load it unless
  invoked; same draft PR.

## First-fire checklist (rollout step 4; result recorded in the registry row)

Fire each routine by hand once (`fire_trigger`, text: "first fire: run the README checklist,
report booleans only"), cheapest first: steward, then security, then product. Then read the
spawned session (`list_triggers` → `last_run.session_id` → `get_session`) and the ledger.

- [ ] The session transcript shows the permission mode it ran in (a fallback to a mode that
      denies without prompting "succeeds" having done nothing — `docs/product/decision-log.md`,
      2026-09-14 governor row).
- [ ] `secrets-guard.sh` is armed: a Bash command that echoes an unset variable whose name
      ends in `_TOKEN` is refused by the hook (the value is empty; the refusal is the proof);
      no `exit 127` and no `CLAUDE_PROJECT_DIR` error appears in the transcript.
- [ ] Env presence as booleans only: `python -c "import os;print({k:k in os.environ for k in
      ['ASXOS_PERSONAL_USE','DATABASE_URL','HC_ROUTINE_STEWARD_URL']})"` — `ASXOS_PERSONAL_USE`
      expected **False**.
- [ ] Which scheduler tools exist in-session (`list_triggers`, `get_session`, `update_trigger`)
      — they gate the steward's ledger step 3 and the digest's cost line.
- [ ] START and END both on #270; today's block on #271 (steward).
- [ ] `get_session` from the launching session: `configured_model` and `last_served_model` match
      the registry; `usage.cost_usd` recorded here.

## Adding a routine

One doc with the frontmatter schema (`name, cron, model, connectors, budget_min, environment,
requires_env, deadman_env, writes`) and a `{{preamble}}` line; one `create_trigger`; one
registry row. `tests/test_routine_docs.py` refuses a cron within 30 minutes of a production
cron or another routine, a `writes` entry another routine already owns, the Supabase write
connector, or a routine that needs `ASXOS_PERSONAL_USE` in the `Default` environment — a
live-testing routine needs a dedicated environment where James has set that variable.
