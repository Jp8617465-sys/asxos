# Session handoff — 2026-09-25, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-24-routine.md`.

**STOP — read first.** Rule #11 stands; nothing here read `signals`.

1. **#327 is closed.** `pipeline-health` **36066252575** went green on `246dcf7`, matching the
   prediction. **Gate (b) now passes** — the first time in five fires. Do not reopen it.
2. **One measurement is owed, and tonight's `daily-brief` takes it.** #371 instrumented
   `ingest_regulatory`; the 20:30 UTC run logs `N new, M re-touched (P parsed)` and warns on any
   dropped feed item. **E-20 closes when you quote that line.** Read it before picking anything.
3. **E-20 is deliberately still open** at half done. The shipped half is `rows_written`; the
   blocked half is the live-feed count.

## What fired

Fire **2026-09-25T17:32:35Z**, budget 120 min, `doc_sha=246dcf7`. START at **T+1**, PR opened at
T+9, merged inside the window.

| gate | result |
|---|---|
| halt | clean |
| (a) `nightly-check` on `main` | **`success`** — `36154485184`, scheduled, head `246dcf7` |
| (b) no open `incident` issue | **PASSED — 0 open.** First time in five fires |
| (c) dangling START | clean |
| (d).1 / (d).2 | no `claude/routine-*` PR → picker exit 0, eligible 4, pick **E-20**; roadmap agreed |

## #327 closed, and what it cost to get right

`pipeline-health` **36066252575** concluded **`success`** on `246dcf7` — first green since 09-19,
exactly as the dated prediction on the issue said, with no further change. Closing condition met.

**Three lessons, each of which cost a wrong claim first:**

1. **A symptom that stops is not evidence *your* fix stopped it.** On 09-21 I credited #366 for a
   note that #352 had silenced 31 hours earlier.
2. **A green `nightly-check` is not a green `pipeline-health`.** Different code paths; I used the
   first as proof of the second.
3. **A fix to a note-producing job cannot *show* green for up to 36 hours**, because check 4's
   window is deliberately historical. This one misled me **twice, in both directions** — first
   into claiming a fix worked, then into reading a red run as the fix failing.

## The one thing — E-20, half shipped, half named as blocked

`rows_written` for `ingest_regulatory` came from `upsert_events` returning `len(rows)`: events
**presented** to the statement, not rows written. So a feed re-serving the same item reported
`rows_written=1` every night while `regulatory_events` did not grow — 7 rows total,
`max(ingested_at)` 2026-09-03, a `rows_written=1` success row every night 09-07 to 09-14.

**Nothing was broken.** The number meant "touched"; every reader takes `rows_written` as "work
done". **That is the third instance this week of one defect class: a channel with an established
meaning carrying something else.** So the re-touch count goes to INFO, not `monitor.note` — a
feed's cadence is a fact about the feed, not about the job's health.

Two things found on the way, neither in the row's `paths:`:

- **`upsert_events` had no tests at all.** That is why replacing `executemany` with a single
  `RETURNING` statement broke nothing visible. Seven added; that file goes 15 → 22.
- **The batch form needs a `(source, url)` dedupe.** One statement cannot touch the same conflict
  target twice — Postgres raises — where per-row `executemany` quietly applied both.

Mutation-checked four ways: report presented instead of inserted → 2 red; drop the dedupe → 1 red;
stop `RETURNING (xmax = 0)` → 1 red; silence the dropped-item warning → 1 red.

## The measurement I could not take — and did not guess

E-20 also asks for *"a stated count of items in the live RBA RSS vs items parsed"*. **Blocked from
an agent session, three ways:**

- the egress proxy **denies `www.rba.gov.au`** (`connect_rejected`, organization policy);
- every workflow that fetches it carries `RESEND_API_KEY`/`EODHD_API_KEY` on a schedule, so it is
  James's to dispatch;
- the repo's RBA fixture is **synthetic**, so it cannot say what the real feed carries.

Rather than estimate, the instrumentation shipped: the job logs `N new, M re-touched (P parsed)`,
and `parse_rss` logs a WARNING for **every item it drops** for a missing title or link, naming
which leg was missing. **Silent skipping is exactly what made the question unanswerable.**

**E-20 stays open, `route=build`** — reading a workflow log needs no human, so this is next-fire
work, not attended work.

## Verification

- `make check`: **4839 passed / 19 skipped** (4832 → 4839 is seven new tests), ruff + mypy clean
  on 239 source files.
- Migrations untouched. No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **C-13** — still the highest-value item in the repo and still arbi-impossible.
- **#355**, **#346**, **#319** — open for you.
- **The Routine binding.** MCP rebuild path is closed (`create_trigger` stores no connectors);
  needs the claude.ai Routines UI.
- **K-08** — `deadman=unset`, seventh fire running. Worth noting it has now been listed every
  fire for a week without moving; if it is not going to be done, it is worth saying so and
  dropping the line rather than carrying it.

## Next fire

**Read the `ingest_regulatory` log line from tonight's `daily-brief` run first** and close E-20
with it quoted. Then **E-21** → **E-27**.
