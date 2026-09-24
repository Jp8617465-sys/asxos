# Session handoff — 2026-09-24, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-23-routine.md`.

**STOP — read first.** Rule #11 stands; nothing here read `signals`.

1. **Read `pipeline-health`'s 2026-09-24 22:14 UTC run first.** A falsifiable prediction is on
   #327 saying it goes **green** with no further change. If it is green, **close #327**. If it
   is red, the prediction was wrong — say so plainly and re-diagnose rather than re-explain.
2. **#368 works.** Last night's red run was *not* the fix failing — see below. Do not re-fix it.
3. **#327 is deliberately still open**, on a run rather than on an argument.

## What fired

Fire **2026-09-24T17:32:13Z**, budget 120 min, `doc_sha=f7143dd`. START at **T+1**, PR opened at
T+5, merged well inside the window.

| gate | result |
|---|---|
| halt | clean |
| (a) `nightly-check` on `main` | **`success`** — `36020563525`, scheduled, head `f7143dd` |
| (b) no open `incident` issue | **FAILED — #327**, taken as the one thing |
| (c) dangling START | clean |
| (d).1 / (d).2 | no `claude/routine-*` PR → picker exit 0, eligible 5, pick **A-51**; roadmap block agreed (Amendment K) |

## The proof run came back red, and the diagnosis is the opposite of the obvious one

`pipeline-health` **35927183062** ran on `f7143dd` — the head carrying #368 and #369 — and
concluded **`failure`**. The obvious reading is "the fix didn't work". It is wrong.

| evidence | |
|---|---|
| both flagged rows | `as_of=2026-09-22` — written **before** the fix existed |
| check 4's window | `started_at > NOW() - INTERVAL '36 hours'` — history, not current state |
| when those rows aged out | written ~09-22 20:36 UTC → left the window **~08:36 UTC on 09-24** |
| the first run on the fixed head | `daily-brief` **35917018303**, 09-23 20:35 UTC, **`success`** — and the 22:14 watchdog flagged **no `as_of=2026-09-23` row at all** |

So the post-fix rows carry no note. **#368 works.**

**The general fact, which will recur:** a fix to a note-producing job cannot *show* green until
the pre-fix rows age out of the watchdog's lookback, however correct it is. Budget 36 hours
before treating such a fix as unproven.

**And what I did not do:** close #327 on that reasoning. The closing condition I set was a green
run. Reasoning my way to "it would have been green" is the same move that made the 09-21 close
wrong — the argument is much stronger this time, and it is still an argument. The prediction is
on the issue, dated, so tonight's run either confirms it or falsifies it.

## The one thing — A-51, whose blocker made the job smaller

The row gated generalising the `security_kind` reconcile on *"a rule for which transitions are
safe… since the out-of-band `us_equity`/`index` rows are hand-set and must survive."*

**Opening the code falsified the gate.** `incoming` is built from the EODHD **AU** exchange list,
so every key is a `.AU` symbol — `HUBS.NYSE` and `AXJO.INDX` are never iterated at all. They were
already unreachable by the loop's domain, not by A-49's narrowness.

Shipped as **#370**:

- **`_VENDOR_OWNED_KINDS` is the rule** — overwrite a stored kind only when it is one EODHD's own
  `Type` field can produce. A feed with no opinion about a row is not evidence about it.
- **The guard is kept despite being redundant today**, because the suffix argument is non-local:
  it depends on `_to_symbol` and on this staying a single-exchange ingest. Its test deliberately
  puts a hand-set row **into** `incoming`, so the guard is what is tested.
- **Auto-apply, not queue-for-a-human** — on A-49's measured asymmetry: *"never update"* produced
  permanent silent wrongness on six live rows. Following the vendor is reversible next run,
  counted, and logged at WARNING when it is not the already-understood LIC correction.
- `classify_kind` still applies the curated override **after** the type map, so EODHD typing an
  ASX LIC as "Common Stock" cannot undo A-49 weekly.

**Mutation-checked three ways** — drop the guard → 1 red (its failure output prints the exact
damage, `AXJO.INDX index -> au_equity`); revert to A-49's narrow branch → 2 red; stop the
override winning → 5 red.

## L61 has fired five consecutive fires and is no longer news

#327's remedy, A-34's `paths:`, A-35's `paths:`, E-30's framing and `paths:`, and now A-51's
blocker. **Three of the five made the job smaller.** That is the part worth holding onto: opening
the named files first is not defensive caution, it is how the work gets cheap. It is the standing
first action on any picked row; a fire that skips it is the deviation, and this handoff stops
reporting it as a recurring surprise.

## Verification

- `make check`: **4832 passed / 19 skipped** (4828 → 4832 is four new tests), ruff + mypy clean
  on 239 source files.
- Migrations untouched. No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **C-13** — still the highest-value item in the repo and still arbi-impossible.
- **Tonight's `pipeline-health` reading** — the only thing blocking #327.
- **#355**, **#346**, **#319** — open for you.
- **The Routine binding.** MCP rebuild path is closed (`create_trigger` stores no connectors);
  needs the claude.ai Routines UI.
- **K-08** — `deadman=unset`, sixth fire running.

## Next fire

Read the `pipeline-health` run, close #327 if green. Then the queue: **E-20** → **E-21** →
**E-27**.
