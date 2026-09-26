---
name: daily-product
cron: "30 17 * * *"
model: claude-fable-5-1
connectors: [supabase-ro]
budget_min: 120
environment: Default
requires_env: []
deadman_env: HC_ROUTINE_PRODUCT_URL
writes:
  - docs/product/roadmap-state.md
  - docs/product/decision-log.md
  - docs/product/memory/lessons.md
  - docs/product/memory/project-facts.md
  - docs/session-handoff-*-routine.md
  - code and docs PRs on claude/routine-* branches
---

# daily-product — a wake a day, a build only on condition

**Status:** current (routines v1, 2026-09-14)
**Fires:** 17:30 UTC daily = 03:30 AEST, after `nightly-check` (15:17 UTC) has concluded and
clear of `weekly-research` (Saturday 16:00 UTC, 90-minute timeout). Finishes before
`nightly-steward` (19:45 UTC).
**Outcome it is measured on:** product advancing without James's attention, in the repo's own
completion test — every close carries exactly one of `renders:` / `captures:` / `defect:`
(Amendment E, `docs/product/roadmap-state.md`).

{{preamble}}

## 1. Gate — about two minutes, before the token-expensive wake

All five must hold, checked in this order — (a), (b), (c), (e), then (d). The first that
fails ends the fire with `outcome=noop reason=<letter>`; no handoff file, no PR, no roadmap
edit. (`(e)` is lettered rather than renumbered so five fires' worth of END comments citing
`reason=d` keep meaning what they said.)

- **(a) `main` is green.** The most recent `nightly-check` run on `main`
  (`actions_list(list_workflow_runs, resource_id="nightly-check.yml", perPage=1)`) concluded
  `success`. A `failure`/`cancelled`/`timed_out` is an incident (`AGENTS.md` §7): if no
  `incident`-labelled issue exists for it yet, open one (cause, evidence, blast radius,
  remedy) — that is tonight's one thing, go to §3 with it.
- **(b) No open `incident` issue** other than one this fire is about to take as its one thing.
- **(c) No other routine is running:** the ledger has no `status=START` in the last 3 hours
  without a matching `status=END`. Since 2026-09-26 `nightly-check.yml`'s `routine-ledger`
  job checks the same ledger mechanically and fails the run, so (a) failing on that job is
  this condition failing — read which job went red before diagnosing.
- **(e) `backlog-roll` has not already built today.** `AGENTS.md` §8a: *"a gate in the
  routine doc stops both from building on one day."* If `backlog-roll.yml` has a run today
  whose conclusion is `success`, this fire does not build — `outcome=noop reason=e`, and the
  close still happens. Two builders picking from one queue on one day is how two PRs end up
  touching the same declared paths, which the picker's overlap rule cannot prevent across
  lanes. `backlog-roll` is not armed yet (#355 is held on A-22, `HC_BACKLOG_URL` is unset),
  so today this passes by there being no run at all — check it anyway; the arming is James's
  and will not come with a note.
- **(d) A ready item exists**, first match wins:
  1. an open PR on a `claude/routine-*` branch — finish it (checks, merge, proof) or close it
     with a comment saying why;
  2. **`python scripts/issue_next.py` exits 0** — its pick is the item (exit 3 = nothing
     `ready`; exit 2 = schema/GitHub error → that is the item). This is Layer 4 of the build
     loop (`AGENTS.md` §8a, `asxos/backlog_issues.py`): **the queue is GitHub Issues.** It
     needs `GITHUB_REPOSITORY` and `ARBI_GITHUB_TOKEN` in the environment; a bound session
     may have an equivalent token under another name, in which case pass it to this one
     command rather than treating the gate as unrunnable.
     *Superseded:* this step read `scripts/backlog_next.py` until 2026-09-27. That picker
     still runs, but over `docs/product/backlog.yaml`, which #382 **archived as the queue** —
     "rows are not edited here any more; a row's state lives on its issue once filed." A fire
     following the old line would build a row whose real state is on an issue it never read.
  3. the ranked queue in `docs/product/roadmap-state.md` (the block headed "Live as of …")
     names an unblocked item **and** its "Live as of" date is 7 days old or less. Older → the
     one thing is a re-rank of that block against live state, not a build.

  **When (d).2 exits 3 — which is the normal case today, not an anomaly.** The Issues queue
  is empty until issues are filed and readied: `AUTO_READY` is off, and
  `scripts/backlog_to_issues.py` files the archive's eligible rows **from an attended
  session**. So a fire falls to (d).3 and builds from the roadmap block, which Amendment K
  keeps as the human queue and which is not archived. That is legitimate, and it is also the
  seam to watch: when (d).2 starts returning picks, (d).3 should stop being reached, and a
  fire still reaching it after that means issues are not being readied.

## 2. Wake — `/arbi` §1-3, surgically

Run the `/arbi` wake steps 1-3 with the preamble's tool map. Read `roadmap-state.md` by
section (the ranked-queue block and the newest "Last wake snapshot" fence), not end to end;
read the newest `docs/session-handoff-*.md` and the last five `decision-log.md` rows. A doc
that live state contradicts is stale: fix it in this fire's PR.

Dark-launch surfaces past expiry (`docs/product/dark-launch-exit-plan.md`, "How arbi uses
it") are candidates for the one thing — verdicts are arbi's (`AGENTS.md` §2) — not perpetual
re-raise lines.

## 3. Pick and build ONE THING

The pick is what §1(d) returned, re-checked against `AGENTS.md` §7 ("unblock before you
build; defensibility wins ties"). Not pickable from a routine: anything under `.claude/**` or
`docs/ops/routines/**` (draft PR, list under Yours), a migration (carry open, say so), capital,
the personal-use gate, a weakening change, Model A. A large call, or one that repeats a one
thing the decision log says did not land, goes to `arbi-red-team` first; CHALLENGE → take its
re-rank and say why in the log row.

Build per `AGENTS.md` §8 on `claude/routine-<AEST date>-<slug>`: `make check` green; PR ready
with class, reversal cost, the acceptance-criteria block (investment-output band), and the
Amendment E field; wait for `full-check` on the current head.

## 4. Land and prove — merge no later than T+90

1. `merge_pull_request(squash)`.
2. Dispatch `nightly-check.yml` on `main` (`actions_run_trigger`) and wait for its conclusion
   (25-minute timeout). This is the "first production run" of `AGENTS.md` §8 step 6; the
   06:30 AEST `daily-brief` must never be the first test of a merge.
3. `failure` → open and merge a `git revert` PR (Green), then an incident issue with the
   failing log. END carries `reverted=<sha>`.

T+90 is the latest merge because the proof needs 25 minutes and the close needs the rest.
No merge after T+90: leave the PR open, ready, and say so.

## 5. Close — `/arbi-close`, routine variant

- Decision-log row: the one thing, what was done, outcome (done/partial/deferred), the
  Amendment E field, `run ref = routine-<AEST date>`.
- `roadmap-state.md`: re-rank the live block; refresh the snapshot fence. Only those two
  regions.
- Handoff: `docs/session-handoff-<AEST date>-routine.md` — never the bare date, which is the
  interactive session's filename (same-day collisions are on record).
- All state edits ride the same PR as the code where possible; if the close is a separate PR
  it is Green and merged in this fire.
- Comment the close (the `/arbi` brief block) on the digest issue (`README.md`).

## Stop conditions

A §1 gate failing (noop); budget (over-budget, the section reached); an incident found at
wake (that is the one thing, not a stop); a pick needing a secret slot, a migration or a
`.claude/` edit (draft or carry, list under Yours, take the next item if time allows).
