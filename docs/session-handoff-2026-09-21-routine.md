# Session handoff — 2026-09-21, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-20-routine.md`.

**STOP — read first.** Rule #11 stands; nothing here read `signals`. **#327 is still open, and
deliberately so.** Its nightly false page is fixed, but a set-aside *approved* thesis has no
brief surface yet — so the issue itself is currently HUBS.NYSE's only visibility. That remaining
half is **E-30**, re-scoped tonight from attended to `route=build`. Do not close #327 until an
uncovered approved thesis shows up in the brief.

## What fired

`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`, fire
**2026-09-21T17:31:44Z**, `doc_sha=6c70ea1`, budget 120 min. START at T+1. **Second consecutive
fire not held in plan mode.**

**Gate (b) failed, and that is the headline.** #327 is open and `incident`-labelled — because
last night's fire labelled it, after the same probe had returned **0 for four consecutive fires**
while it sat open and unlabelled. The detector fix worked on its first firing and handed over the
right item.

| gate | result |
|---|---|
| halt | clean — 12 open issues, 0 `routines-halt`, 0 `HALT:`-titled |
| (a) `nightly-check` on `main` | **`success`** — `35619045183`, scheduled, head `6c70ea1` |
| (b) no open `incident` issue | **FAILED — #327.** Taken as the one thing |
| (c) dangling START | clean |
| (d) | not reached |

## The one thing — and the fix was already in the repo

**I opened `check_cron_health` before touching it, and that falsified my own E-30 from the night
before.** It is not a design ruling about watchdog semantics. Three things were already true:

1. **`build_decision_packets.py` already carries the exact partition needed, and its comment
   names issue #327 by number.** An approved thesis with no price plan is set aside *before* the
   builder is called, into `awaiting_plan`, which **deliberately sets no note** because it is
   *"a fact about James's review queue, not about this job's health"*.
2. `check_cron_health`'s own header names the alert-fatigue failure mode **twice**.
3. That file has already made the same move twice: `generate_signals` and `check_model_staleness`
   were dropped from `_EXPECTED_DAILY` with dated comments, and `check_us_positions` got a
   widened window with the measurement inline.

So the change was extending a shipped precedent to the **second** structural precondition: a
symbol the data layer has **never** held a statement for is set aside into `no_data_coverage`,
no note, before the builder is called.

### "Ever", not "at this cutoff" — the whole safety property

A partition that quiets builder failures is one bad predicate away from a mute button. The check
is *has the data layer **ever** held a statement for this symbol*. Zero-ever means the vendor does
not cover the name and no run will ever build it. A symbol **with** history whose cutoff yields
nothing admissible is a regression, stays in `failed`, and still pages.

**Mutation-checked in both directions**, which is what makes that claim worth anything:

| mutation | result |
|---|---|
| remove the partition | **2 red** — #327 re-breaks |
| widen it to quiet any builder failure | **3 red**, two of them *pre-existing* tests |

## What is NOT done

**#327 stays open.** Once a name stops paging it also stops being visible. `awaiting_plan` rows
have a home — the brief's candidates card renders them. A set-aside **approved** thesis has none,
so HUBS.NYSE's visibility today is the issue itself. **E-30** re-scoped to exactly that: one
discipline finding so an uncovered approved thesis appears in the brief (the card already carries
`incomplete_price_data` and `data_sanity`, so the shape exists), `route=build`. #327 closes when
that lands.

## The pattern worth naming — L53/L61, three fires running

Three nights in a row, a filed row described a shape the code did not have:

- **2026-09-19** — #327's own stated remedy (widen an `is_active` filter). Wouldn't have worked.
- **2026-09-19/20** — A-34's and A-35's `paths:`. Both under-named the surface.
- **2026-09-20** — E-30's framing as a design ruling. Falsified tonight.

Every one was caught by opening the consumers before building; every one would otherwise have
shipped something wrong. A row is written when a defect is *found*, by someone holding one or two
files; its shape is discovered when it is *built*. **Worth promoting from lesson to habit: the
first action on any picked row is to open the code it names and check the row against it, before
estimating or ranking.**

## Verification

- `make check`: **4811 passed / 19 skipped**, ruff + mypy clean.
- Three new tests, mutation-checked as above.
- Migrations untouched. No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **C-13** — still the highest-value item in the repo and still arbi-impossible.
- **#342**, **#334**, **#319** — `.claude/`, drafted for you.
- **The permission mode.** Two unheld fires in a row now, but nothing changed to make that so.
- **K-08** — `deadman=unset`.

## Next fire

Gate (b) will pass again once #327 is the only open incident and you judge it triaged — or it
will hand over #327 again, in which case **E-30 is now the buildable answer**. Otherwise the
queue is **A-51** → **E-20** → **E-21**.
