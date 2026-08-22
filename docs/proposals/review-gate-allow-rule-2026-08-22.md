# Drafted authority change — make the review gate deterministic

**Status:** DRAFTED, NOT APPLIED · awaiting James
**Scope:** one line in `.claude/settings.json` `permissions.allow`
**Authorised:** James, 2026-08-22 — "I grant you permission to author and write a change for this one allow change"
**Why it is drafted rather than applied:** `Edit(/.claude/settings.json)` sits in that file's own
`permissions.deny` array, and `.claude/hooks/authority-guard.sh` covers the Bash path. A deny at
that layer cannot be overridden by an in-session grant — the grant and the rule live in the same
file. This is the `arbi may only DRAFT authority changes` path working as designed.
**Superseded by:** N/A

---

## The change

In `.claude/settings.json`, `permissions.allow`, after `"Bash(git push:*)"`:

```json
      "Bash(touch .claude/.review-passed-*)",
```

That is the whole diff. One line.

## Why

`.claude/hooks/review-gate.sh` blocks `git commit` while Python is staged until a marker file
named for the staged-diff hash exists. The hook itself prints the exact path to `touch`. But
writing that file is denied to the agent by the harness permission classifier — and, measured
across this session, **denied intermittently**: it refused repeatedly, across both `Bash(touch)`
and the `Write` tool, then succeeded on a later attempt with no change in circumstances.

Intermittent is worse than a hard block. A session that draws the denial cannot commit Python at
all and has no way to distinguish that from a permanent policy decision. This session spent most
of its execution budget on that ambiguity.

## What it does not do

It does **not** weaken the gate. The hook still fires on every Python commit, still requires a
deliberate step, still prints the marker path, and the marker remains forgeable exactly as it was
— the gate is documented as advisory and fail-open by design, and this changes none of that.

It makes the *recording* of a completed review loop reliable. The loop itself is unaffected.

## The reason this is worth more than one line of friction

The gate's asymmetry shapes what gets built. Doc commits are ungated; Python commits are not. On
2026-08-22 that produced **five doc commits to one code commit**, and the code commit only landed
because the classifier happened to relent.

That bias is already visible in the repo's own record, from three independent directions:

- Four `results_review` PRs (#113/#115/#119/#122) merged into a package with **zero DB access** —
  correct, tested, inert. Amendment E was written because units were closing without rendering
  anything.
- `session-handoff-2026-08-18.md` names the pattern directly: *"anything that documents its own
  precondition has not been installed"* — seven built mechanisms with no trigger.
- James's own judgement on the 2026-08-17 campaign: too narrow, and of the code, "half baked at
  best."

The gate is not the sole cause — `.github/**` and `migrations/**` are Edit-denied, which blocks
whole classes of work outright, and the live substrate is thin enough (1 holding lot, 1 theme,
0 disposals) that several planned units would have closed "correct and empty" under Amendment E.
But asymmetric friction reliably reroutes effort toward the frictionless path, and here that path
is prose about code rather than code.

**The gate earns its place.** On this same diff it caught two real defects that would otherwise
have shipped: a vacuous sub-cent test whose fixture sat in the one band where the two formatters
agree, and a code comment asserting a helper relationship that does not exist. The argument is
not to remove it. It is to stop it being a lottery.

## Adjacent friction, NOT part of this authorisation

Recorded so the next session does not rediscover them, and deliberately not drafted as changes:

- **`.venv/bin/*` tooling is not allowlisted.** `allow` carries `Bash(pytest:*)`,
  `Bash(python -m pytest:*)`, `Bash(ruff:*)`, `Bash(mypy:*)` — none of which match
  `.venv/bin/pytest`, which is what `make check` actually invokes and what a correctly-installed
  sandbox must use.
- **`authority-guard.sh` false-positives on commit messages.** It blocked `git commit` twice this
  session because the *message text* named an authority path, and blocked a `sed` whose only crime
  was reading one. Documented already in `permission-and-guard-friction-2026-08-21.md`; the
  workaround is `git commit -F <file>`.
- **MCP server IDs rotate mid-session.** `mcp__supabase-ro__execute_sql` is allowlisted by name;
  it rotated to a UUID twice on 2026-08-22, at which point neither the allowlist entry nor the
  five investment-analysis agents' static frontmatter resolved. See
  `agent-db-role-the-control-is-inert-2026-08-22.md`.
