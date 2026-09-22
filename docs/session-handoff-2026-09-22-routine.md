# Session handoff — 2026-09-22, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-21-routine.md`.

**STOP — read first.** Rule #11 stands; nothing here read `signals`.

1. **PR #368 is open, green and unmerged BY DESIGN.** It is not abandoned work. §4 forbids
   merging past T+90 and this fire ended at T+299. It sits on `claude/routine-*` so the next
   fire picks it up under gate (d).1 — that is exactly what that gate is for. **Finish it
   first.**
2. **Yesterday's close was wrong and this handoff corrects it.** #327's nightly page was not
   fixed by my #366 partition. Do not repeat the claim.
3. **#327 stays open.** Remaining half is **E-30** (`route=build`).

## What fired

`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`, fire
**2026-09-22T17:32:25Z**, budget 120 min. START at **T+2**. **Third consecutive fire not held
in plan mode** — and it still went 2.5× over budget, for a different reason.

| gate | result |
|---|---|
| halt | clean |
| (a) `nightly-check` on `main` | **`success`** — `35747511169`, head `a3e3e96` |
| (b) no open `incident` issue | **FAILED — #327.** Taken as the one thing |
| (c) dangling START | clean |
| (d) | not reached |

**The budget failure has moved.** The first four fires were held in plan mode before starting.
This one started on time, ran its gate at T+2, and was then **suspended ~4h45m between turns**,
resuming at 22:23Z / **T+291**. Being released on time is necessary and not sufficient; nothing
in the repo controls either mechanism.

## The correction — and it is the most important thing here

**On 2026-09-21 I closed saying #327's nightly false page was "fixed and proven". Both halves
were false.**

| claim | what was actually true |
|---|---|
| **"proven"** | cited a green `nightly-check`, which does not exercise this path. `pipeline-health` **`35661594310`** ran on **`a3e3e96`** — the merge commit carrying the fix — and concluded **`failure`** |
| **"fixed"** | **#352 retired HUBS at 2026-09-20 10:11 UTC, 31 hours before the partition merged at 2026-09-21 17:41 UTC.** `build_decision_packets` had already stopped saying it. The partition is correct, is mutation-checked, and **has never once fired in production** |

The code stays — it is right, and it will matter the first time an approved thesis names a
symbol the vendor does not cover. Only the claim about it was wrong.

**The missing check, written down:** *before crediting a fix for a symptom's disappearance,
confirm the symptom's precondition was still present when the fix landed.* A symptom that stops
is not evidence; a symptom that stops **for your reason** is. Distinguishing them costs one
timestamp comparison.

## The one thing — two more notes that are not degradations

Having established what was actually red, the answer was two notes neither of which reports a
fault:

| job | note | what it is |
|---|---|---|
| `build_decision_packets` | "no approved theses — nothing to challenge" | the **designed** state after #352's governance sweep — 0 approved, 3 `pending_review`, 10 `rejected`, 13 `retired` |
| `observe_decision_outcomes` | "nothing to record: every packet has its t0 and no horizon is due" | **the healthy case**, announced through an alerting channel |

`monitor.note` is an alerting channel (`job_monitor.py:139` → `check_cron_health.py:152`). Both
`elif` branches removed. The two tests that pinned them were **rewritten to assert
`monitor.note is None`**, not deleted — one renamed `..._is_a_noted_success` →
`..._is_a_QUIET_success`, and the rename *is* the change.

**Nothing is lost:** `rows_written = 0` on a `success` row records each quiet pass losslessly,
and the brief's candidates card shows the pending queue.

**Mutation-checked in the direction that matters.** Silencing the genuine-failure notes directly
above both edits turns **3 tests red across the two jobs** — so the change provably removes
steady-state noise only, and cannot be widened into a mute button without going red.

## The risk worth naming — read this before shipping a third one

**Two nights running I have shipped a change that makes a watchdog quieter, and neither has yet
been observed working in production.** Both are mutation-checked correctly. But a mutation check
proves the guard *can* fail; it does not prove the page *stops*. Last night I mistook the second
for the first.

#368 is the first claim of this shape that is **checkable**: the 22:00 UTC `pipeline-health` run
after it merges either goes green, or the remaining cause gets named rather than assumed. **If a
third quieting change comes up before that one is observed, stop and observe instead.**

## Also done this fire

`main` moved five commits (#367, #365, #345, #363, #364) while #368 sat open, conflicting it on
the append-only `decision-log.md`. Resolved by **merge** (`fc24060`, not a rebase, so any
checkout stays valid), keeping **every row from both sides** in date order.

## Verification

- `make check` on the merged tree: **4814 passed / 19 skipped**, ruff + mypy clean on 238 source
  files. (4811 → 4814 is main's three new tests, not mine.)
- Migrations untouched. No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **C-13** — still the highest-value item in the repo and still arbi-impossible.
- **#342**, **#334**, **#319** — `.claude/`, drafted for you.
- **The permission mode / Routine binding.** The MCP rebuild path is **closed**: `create_trigger`
  stores no connectors, so a fresh-session Routine would fire with no GitHub and no Supabase.
  The remedy is the claude.ai Routines UI.
- **K-08** — `deadman=unset`, fourth fire running.

## Next fire

**Gate (d).1 should pick up #368** — it is on `claude/routine-*`, green, conflict-free and ready.
Merge it, then **watch the 22:00 UTC `pipeline-health` run** and record what it actually
concluded. That observation is owed from this fire and is the honest close of the #327 work.

If gate (b) fails on #327 again, **E-30 is the buildable answer**. Otherwise the queue is
**A-51** → **E-20** → **E-21**.
