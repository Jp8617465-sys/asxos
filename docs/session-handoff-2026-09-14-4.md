# Session handoff — 2026-09-14, fourth session (overnight Routines)

**Status:** current
**Read priority:** read first for anything about the overnight Routines; then
`docs/session-handoff-2026-09-14-3.md` (the product sprint that ran in parallel) and `-2` (the
merge train). Same interactive session as `-2`, continued after James's next ask.

## What James asked for

"Build some Claude routines to fire overnight. They can be issues reviews. Live testing,
security, or even product building if we have a roadmap and we can automate a session a day."
Then: "Red team plan, assess approach, outcomes and reconfigure for optimisation in reaching
those outcomes whilst being scalable and reliable." His four answers to the plan's questions:
full arbi authority ("arbi must be involved"); three routines in v1; Fable 5.1 for product,
Sonnet 5 for steward and security; the `Default` environment.

## What shipped — every figure measured this session

| PR | What | Class | State |
|---|---|---|---|
| #272 | `docs/ops/routines/` — preamble, three routine docs, registry, pin test; P1-row ruling, roadmap line, `CLAUDE.md` rule 2 | Green | merged `d6536bd` |
| #274 | first-fire findings, scheduler handover, preamble §0 "nobody answers questions" | Green | merged `f61bf1e` |
| #273 | `.claude/commands/ship.md` step 4 — merges are arbi's | Green, `.claude/**` | **OPEN — YOURS** |
| this PR | registry row updated with the proven run and its cost; this handoff | Green | — |

Pinned issues: **#270** routines ledger (START/END per fire), **#271** daily digest — which
already carries its first real `## 2026-09-15` block, written by the proof run below.

Plan v1 was red-teamed (`arbi-red-team`: CHALLENGE) and architecture-reviewed before v2. The
findings that changed the design: a wake a day with a build only on condition (not a handoff
PR every fire); a START/END ledger as the artefact that means "ran"; a `nightly-check` proof
after every merge so the 06:30 brief is never the first test; the Saturday collision with
`weekly-research` (product moved to 17:30 UTC); no migrations in a routine session while the
five-hour rate window is shared; a `HALT:`-titled issue as a kill switch that works from a
phone.

## Online — how the scheduler was bound (2026-09-15, after James: "need this routines online")

A trigger created from an arbi session stores **no repository and no connectors**
(`sources: []`, `mcp_servers: []`; the tool also refuses the `connectors` parameter for this
organisation). Its fires wake without the repo and go idle: two fires, 21:19 and 21:24 UTC,
US$0.34 and US$0.26, no trace anywhere, both recorded `SUCCEEDED` by the scheduler. Both
triggers were deleted. The third (`weekly-security`) was refused by the auto-mode classifier.

What the tool *can* do is fire into an existing session, and a session created from an arbi
session with the repo attached inherits the GitHub and Supabase read-only tools — the
end-to-end proof below ran in exactly such a session. So each routine is now **bound to its
own repo-attached session** (`docs/ops/routines/README.md`, "Bound path"): steward
`trig_01AP9VyuN8JSNt5x6eyysiMx` → the session that proved the doc; product
`trig_01TLku22ZdzveWG7iQ1ybXFE` → a Fable session that reported "GitHub + supabase-ro tools
live" on its readiness turn; security `trig_01FTd3jWG9JbdLEWT2g4soTz` → a Sonnet session,
same. First scheduled fires: product 2026-09-15 17:35 UTC (03:35 AEST), steward 19:45 UTC
(05:45 AEST), security Sunday 2026-09-20 12:00 UTC. Two consequences are written in the
README: context accumulates in a bound session (recreate and rebind past ~700k tokens), and
the scheduler sends no push notifications for bound routines — the ledger #270 and the digest
#271 are the observation. Creating the Routines in the claude.ai UI remains the upgrade path
(fresh context per fire, push notifications), not a prerequisite.

## What is proven

The docs run unattended. After #274 merged, a fresh session with the repo attached and only
the three-line pointer ran `nightly-steward.md` end to end: START 21:43, END 21:47 UTC,
`outcome=ran`; all seven production workflows healthy; the §12 digest on #271 with nine merges
classed, five Yours items, four risks and one contained incident (it found the earlier silent
trigger fire on the ledger itself); one duplicate issue closed; `deadman=unset`. Five minutes
of a 45-minute budget, US$2.22 on Sonnet 5. Product and security are unproven until their
first UI-created fire; product will cost more (Fable, up to 120 minutes).

Three lessons, encoded in the README and the preamble so the next attempt does not repeat
them: a verification prompt that asks for token-shaped probes is refused as injection (the §2
rule working — good); a session with no human at the other end will still stop to ask
(preamble §0 now says a turn ending on a question is the silent failure); and the four
sessions before the proof cost ≈US$1.40 for zero ledger comments, because the repo-less
condition was invisible from the session record until compared against a repo-attached one.

## Yours

1. Read the digest on #271 tomorrow morning (07:00 AEST) — it will say what product shipped at
   03:35 AEST or which gate stopped it. Subscribe to #271 in GitHub for one notification per
   digest, since bound Routines send none themselves. Optional upgrade: create the Routines in
   the claude.ai UI (README "Bound path", last bullet).
2. Nothing under `.claude/**` is waiting: #273 (`ship.md`) and #264 (`reversible-work-window`)
   both merged 2026-09-15 under your ruling (recorded in the parallel session's #277).
3. Optional, within the week: one Healthchecks check per routine and its ping URL as
   `HC_ROUTINE_<NAME>_URL` in the `Default` environment — the deadman for the watchdog. Every
   run so far reports `deadman=unset`.
4. The `AUTONOMY` repository variable is still unverified (no `gh`, proxy 403s
   `/actions/variables`). Nothing is blocked behind it.
5. Two test sessions from tonight are parked at a question nobody answered (the first-fire
   attempts before the preamble fix); they can be archived from the session list.

## Follow-ups arbi owns

- The digest's own Risks line: `regulatory_events` 11 days stale with every `ingest_regulatory`
  run `success` — a data-quality gap for the next product fire to look at.
- #228 is half-closed by design (#266 stopped the read; the write still fabricates cash and
  needs a migration) — a product one thing, not a routine's.
- The live-testing routine James named is deferred: it needs `DATABASE_URL` and
  `ASXOS_PERSONAL_USE=1` in a dedicated environment (his), and the pin test refuses it in
  `Default` by design.

## Verification

- `tests/test_routine_docs.py`: 7 passed on every head; full suite green on the #272 head
  (4329 passed, 1 skipped) and CI green on #274.
- `list_triggers` after cleanup: only the parallel session's one-shot daily-brief reminder.
- #270 carries exactly one START/END pair; #271 carries the `## 2026-09-15` block.
