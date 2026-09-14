# Session handoff — 2026-09-14, second session (merge-train)

**Status:** current
**Read priority:** read first — then `docs/session-handoff-2026-09-14.md` (the same day's
earlier grants-settlement session; its residue list, quoted below, is still live).

**Filename note:** `docs/session-handoff-2026-09-14.md` was already claimed by that earlier
session by the time this one closed. This file is the second session of the same calendar day.

## What James asked for

"@arbi I need you to run a triage of all open PR's, decide what is ready to merge, and create
the plan to execute a merge train so that we can start a new session clean with all changes
updated." No `/arbi` wake in the usual ranked-queue sense — the triage and its plan (red-teamed
by `arbi-red-team`, verdict CHALLENGE-narrow, three findings folded in) were the session's one
thing, executed start to finish in plan mode then build mode.

## Outcome — every figure measured this session, not inferred

**21 open PRs → 0** (plus one more, #259, that this session's own work caused to exist and
closed in turn — see below). **10 open issues → 1** (`#228`, the one live product defect, kept
open on purpose).

**7 merged**, in this order:

| PR | What | Class |
|---|---|---|
| #255 | dependabot: python group, 8 bumps (`resend` is the live send path) | Amber |
| #230 | retire `issue-snapshot.yml` — closes standing §7 incident A-24 (red daily since 09-06) | Amber |
| #248 | execute the nightly-triage shell instead of grepping it — 44 tests, re-verified green against the post-rollout workflow with zero changes needed | Green |
| #229 | C1 paper book + F-VAL/r0 valuation store — migrations `0053`/`0054` | Amber |
| #258 | **unplanned** — `id-token: write` missing from three agent lanes | Amber |
| #214 | dependabot: `claude-code-action` bump, sequenced last per the red-team's finding | Amber |
| #259 | **unplanned, agent-authored** — the first weekly-toolwatch report, produced by #258's own live re-verification dispatch and reviewed/merged in turn | Green |

**16 closed, not merged:** 14 PRs implementing the ACP / `asxos-control` programme that
Amendment N (2026-09-10) withdrew undelivered, plus 9 ACP-era issues `not_planned`. Each carries
a comment citing `docs/product/roadmap-state.md:668`. The control-plane stack (#232→#233→#238,
~3.6k lines, tested, never admitted) is a `DECISION/TAKING/REVERSAL` row in the decision log:
closed per `CLAUDE.md` rule 3, branches kept (`claude/closed-loop-item{2,3,4}`), reopenable on
one click if the Findings-log idea is wanted later.

## The one real finding this session surfaced — read this even if nothing else

**Three of the four agent lanes could not authenticate at all**, and no prior session could have
caught it: `weekly-toolwatch.yml`, `nightly-triage.yml` and `backlog-roll.yml` had **0 runs
ever** before this session's first-dispatch proof (Wave 4 of the merge-train plan). The first
real dispatch of `weekly-toolwatch.yml` failed in 20 seconds, before Claude even started —
`claude-code-action`'s OIDC token exchange failed three times:

```
Unable to get ACTIONS_ID_TOKEN_REQUEST_URL env variable
Attempt 3 failed: Could not fetch an OIDC token. Did you remember to add `id-token: write`
to your workflow permissions?
```

`claude-execute.yml` already had `id-token: write`, with the comment
`# required by claude-code-action's OIDC token exchange`. That fix was written once and never
carried to the other three lanes when Amendment N collapsed each to one job on 2026-09-10.
Fixed as #258 (three-line diff, Amber, `AGENTS.md` §6), merged, then **live re-verified end to
end**: the re-dispatched `weekly-toolwatch` run (`34846052898`) cleared the OIDC step, ran Claude
for the first time, and **completed successfully in 11m49s** (12:55:02–13:06:51 UTC) — well
inside its 45-minute budget. (This session's own polling of the run repeatedly misread it as
"still running past its timeout" due to GitHub Actions API read staleness on in-progress jobs,
corrected each time by a fresh job-level query; the actual wall-clock time was unremarkable.)

The run did real, well-sourced work: it wrote the lane's first substantive report
(`docs/research/toolwatch/2026-09-14.md`, 223 lines — the only prior fire was a bare `failure`
heartbeat with nothing to diff against) and opened **#259**, which this session reviewed and
**merged** (`8e6c52c`) — Green class, docs-only, one file, every version/CVE claim cited against
a primary source (`gh api` against `anthropics/claude-code-action`, not a blog summary), and an
honest self-critique of its own untested diff sketch. Its one finding worth carrying forward:
all four agent lanes are pinned to a `claude-code-action` commit 19 CLI releases behind tip,
missing both a Containment Escape auto-mode hardening (2.1.257) and `--permission-prompts none`
(2.1.259, converts an unattended unanswerable-prompt hang into an explicit deny). Landing that
bump is a separate PR — this session did not build it, since #259 itself named it as future
work outside the lane's own docs-only constraint.

**The same two silent-failure unknowns the 09-10 handoff named were never actually tested by
this fix.** This session's dispatch proved auto mode engaged and `secrets-guard.sh` resolved
`CLAUDE_PROJECT_DIR` (the "Install user-level Claude settings for auto mode" step and the
research step both ran) — so those two are now also answered, not just the OIDC gap. All three
first-dispatch unknowns from the 09-10 handoff are closed as of this session.

## #229's other finding — a real, currently-unreachable security gap, fixed

Dispatched `security-engineer` (Tier A review, this repo's own policy for `asxos/**` diffs) on
#229's paper-book/valuation code. One real finding: `_source()`, the broker-report renderer's
inert-rendering fallback, wraps untrusted evidence text in a single backtick span. A `source_uri`
containing a literal backtick would close that span early and let the remainder re-enter live
Markdown as an unchecked `[text](scheme:...)` link — the exact bypass class the report's own
`http`/`https` scheme allowlist exists to prevent, reached through the "inert" branch instead of
the "linkable" one. **Not reachable** by any producer this PR ships (every `source_uri` and
`decision_packet_id` is built from a regex-validated symbol/id), but the Pydantic fields carrying
these values place no character restriction on them. Fixed in the same PR: `_markdown()` now
also escapes backtick to `&#96;`, with a regression test reproducing the exact break-out.

## Migrations applied

`migrations/0053_paper_book_snapshots.sql` (`20260914123901`) and
`migrations/0054_equity_valuation.sql` (`20260914123930`), via the `AGENTS.md` §8 sequence in
one sitting: `migration-integration.yml` green on the final head, `backup.yml` dispatched and
its run (`34844339116`) **read to `conclusion: success`** before applying, both migrations
applied, the two now-stale `EXPECTED_UNAPPLIED` entries removed from `asxos/schema_drift.py`
(following the exact 0049/0050/0051 historical-comment precedent), `CLAUDE.md`'s schema
paragraph updated. `schema_migrations` now **106 rows** (was 104 at the 2026-09-06 count),
verified clean against the live ledger with the module's own post-epoch comparison, simulated
locally.

**Timing note for the next migration:** the daily `migration-drift.yml` cron (`0 6 * * *` UTC)
had already fired hours before this session started, giving 17+ hours of clearance; today being
Monday meant the weekly Sunday `backup.yml` restore drill (`0 15 * * 0`) wasn't a factor either.
Check both before starting the next migration sequence — see `AGENTS.md` §8.

## Also fixed in passing

- `CLAUDE.md:38` — "Postgres 16 (existing project, free tier)" corrected to "Postgres 17
  (existing project, Pro tier)", per the earlier-today grants session's own read-only
  verification (`get_organization`/`get_project`), which found this but left the fix for
  whichever wake next touched that file.
- `pyproject.toml`'s `click<8.6` comment corrected from a stale `typer 0.12.5` reference to the
  actual pinned `typer 0.27.2` — named as a follow-up in the original 2026-09-07 dependency
  audit and never done until now.
- Backlog row **A-24** (issue-snapshot red since 09-06) marked `done`, citing #230.

## What this session did NOT touch, and why — carried forward, in priority order

These are the same items the earlier 2026-09-14 session named as its own next-wake queue; this
session's mandate was the merge train specifically, not a general `/arbi` wake, so they were
left exactly as found:

1. **`.github/runner/claude-user-settings.json:16`** still grants `.claude/` edits to the
   headless lanes — written by #254, missed by #256's reservation. `.github/**` is arbi's; this
   is a five-minute Green fix, and it is the first thing worth doing.
2. **`asxos/backlog.py`'s `DENIED_FILES`** still lists three deleted `arbi-*` docs
   (`arbi-constitution.md`, `arbi-authority.md`, `arbi-permission-model.md`), which blocks the
   `backlog-roll` lane's picker from seeing most of what arbi now owns. Over-restrictive fails
   safe, but it is blocking, not cosmetic.
3. **`.claude/skills/reversible-work-window`** still instructs draft-only behaviour —
   behavioural, not just a stale citation, and `.claude/**` so arbi drafts and James merges it.
4. **The thesis-in-the-same-sitting pairing** item named in the 09-10 handoff, still open.
5. **Dark-launch surfaces**: #1/#4 have been `EXPIRED` since 2026-08-31, unruled; #3 is due
   2026-09-30.
6. **The `AUTONOMY` repository variable.** Measured `STANDING` on 2026-09-08 by James's own hand;
   Amendment N deleted every reader of it, so it is inert regardless of value, but this session
   had no tool to check whether the variable itself still exists in GitHub's Actions settings —
   the `github` MCP server here exposes no `repos/actions/variables` endpoint, and `gh` CLI is
   unavailable in this environment. Check with `gh variable list --repo Jp8617465-sys/asxos` (or
   the equivalent web UI) at the next wake with shell/`gh` access, and delete it if present.
7. **A real `/arbi` wake** — the first genuinely ranked one since 2026-09-06. The 09-06 queue is
   still open per the grants-session's own note.

## Follow-ups named in merged PR bodies

- **Watch the first scheduled `daily-brief`** after #255 (cron `30 20 * * 0-4`, ~22:11 UTC):
  `resend` 2.39→2.43 is the live send path and is mocked in every test, so this is its first
  real exercise. A red run is a §7 incident.
- **`A-22` is still open, still James's** — no `schedule:` is armed on any of the three
  now-fixed lanes, since arming requires a decision about cadence, not just a working
  credential. This session only proved the credential path works.
- **#259's ADOPT item**: all four agent lanes' pinned `claude-code-action` commit is 19 CLI
  releases behind tip, missing a Containment Escape auto-mode hardening and
  `--permission-prompts none` — a diff sketch is in `docs/research/toolwatch/2026-09-14.md`,
  untested against this repo's own hooks. Landing it is a separate, not-yet-opened PR.

## Verification

- `list_pull_requests state=open` → `[]` after this PR merges.
- Open issues → `[#228]`.
- `.venv/bin/pytest tests -q` on the final `main`: 4294 passed, 1 skipped, before this closing
  PR's own doc-only changes (which touch no test).
- `mcp__supabase-ro__list_migrations` shows `0053_paper_book_snapshots` and
  `0054_equity_valuation` at the tail of the ledger.
