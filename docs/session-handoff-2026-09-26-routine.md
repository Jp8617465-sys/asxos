# Session handoff — 2026-09-26, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-25-routine.md`.

**STOP — read first.** Rule #11 stands; nothing here read `signals`.

1. **The gate you are about to run is wrong in the doc, and the fix is drafted as #392.** Gate
   (d).2 names `scripts/backlog_next.py`, which reads a queue #382 archived. Use
   **`scripts/issue_next.py`** (Layer 4). #392 is James's to merge — if it is still open, run
   the live picker and say so, as this fire did.
2. **A correction to yesterday's handoff, which was mine.** It said E-20's measurement would
   come from "tonight's `daily-brief`". That cron is `30 20 * * 0-4` — **Sun–Thu** — and
   2026-09-25 was a **Friday**. No run happened. The measurement lands **Sunday
   2026-09-27 20:30Z**. Read that run's `ingest_regulatory` log line and close E-20.
3. **The Issues queue is empty and that is expected**, not a fault. See below.

## What fired

Fire **2026-09-26T17:32:15Z**, budget 120 min, `doc_sha=433aaab`. START at **T+1**, first PR at
T+13, merged and closed well inside the window.

| gate | result |
|---|---|
| halt | clean |
| (a) `nightly-check` on `main` | **`success`** — `36251938518`, scheduled, head `433aaab` |
| (b) no open `incident` issue | **PASSED** — 0 open, second fire running |
| (c) dangling START | clean — and the `routine-ledger` job now checks this mechanically |
| (d).1 | no `claude/routine-*` PR (#387 touches `nightly-steward.md`, not this doc) |
| (d).2 | **`issue_next.py` → `ready: 0, eligible: 0`, exit 3** |
| (d).3 | roadmap block current; E-20 blocked until Sunday → **E-21** |

## The gate itself was the finding

Thirteen commits landed overnight. Two of them moved the ground under this doc:

- **#382** — `backlog.yaml` **archived as the queue**: *"rows are not edited here any more; a
  row's state lives on its issue once filed."*
- **#383** — **§8a**: GitHub Issues are the queue, with four layers and `asxos/backlog_issues.py`
  as the picker.

Gate (d).2 still called the old picker over the archive. A fire following it as written would
build a row whose real state is on an issue it never read.

**Drafted as #392** (`docs/ops/routines/**` is draft-only, so James merges it):

- **(d).2 repointed** at `scripts/issue_next.py`, with the superseded line kept as a dated note —
  a future reader who finds `backlog_next.py` still present and still exiting 0 deserves to know
  why it is not the gate. Its env requirement is stated too (`GITHUB_REPOSITORY`,
  `ARBI_GITHUB_TOKEN`); a bound session may hold an equivalent token under another name, and
  **passing it to the one command beats declaring the gate unrunnable**, which is what I nearly
  did.
- **A new (e):** `backlog-roll` must not have built today. §8a says outright *"a gate in the
  routine doc stops both from building on one day"* — **and no such gate existed.** Lettered (e)
  rather than renumbered, so five fires' worth of `reason=d` keep meaning what they said.
- **The note that (d).2 exiting 3 is normal**, below.

**This surfaced by running the gate, not by reading the doc.** That is the only way this class of
drift shows up, and it is an argument for running each condition rather than pattern-matching it.

## Why the Issues queue is empty, and what to watch

`AUTO_READY` is off, and `scripts/backlog_to_issues.py` files the archive's eligible rows **from
an attended session** — which has not happened yet. So (d).2 returns exit 3 and a fire falls to
(d).3, building from the roadmap block, which Amendment K keeps as the human queue and which is
**not** archived. That is legitimate.

**The seam to watch:** once (d).2 starts returning picks, (d).3 should stop being reached. A fire
still reaching (d).3 after that means issues are not being readied, and the queue has two
sources again.

## The one thing — E-21, merged `bc622f6`

Five "×detached" figures for CBA circulated — 3.4, 3.5, ~4, 2.449195, 2.471264 — and **none was
bad data**: three arithmetically-correct formulas plus one day's staleness.

The definition's home is now `detachment_ratio`'s own docstring: the formula, the
**exactly-0-inside-the-band** property, and **both rejected forms named with their figures**. A
definition living in a dated proposal is one somebody has to go looking for, which is how three
coexisted for months.

**Why the other two are wrong for this rule:** both measure the *price* against the band instead
of the *gap* against the band, so both are non-zero for a close sitting comfortably inside its own
entry band. At the midpoint, `close / midpoint` returns exactly **1.0 — the blocking threshold** —
for a thesis whose plan is working as written.

**Every figure was verified against the code before being attributed**, not reasoned about:
151.54 → 2.449195 / 3.367556 / 3.483678 (exactly the 09-17 dossier's three), 152.50 → 2.471264,
168 → 2.827586, inside band → 0.

The two wrong doc figures are **annotated** with dated corrections, not rewritten — the repo's
convention for a historical record. Mutation-checked three ways, including that **gutting the
docstring breaks the docs now pointing at it.**

## Verification

- `make check`: **4986 passed / 19 skipped**, ruff + mypy clean.
- `nightly-check` **36261089554** `success` on `bc622f6` (§4 step 2).
- Migrations untouched. No migration, no capital action, no Model A output, no Supabase write.

## Yours

- **C-13** — still the highest-value item in the repo and still arbi-impossible.
- **#392** — the routine-doc gate fix. Until it merges, every fire has to improvise around (d).2.
- **#387**, **#380**, **#372**, **#355**, **#346**, **#319** — open for you.
- **K-08 is no longer a standing ask.** #373/#374 built the mechanical half; the three
  healthchecks.io URLs are optional and the row says so. This list should stop carrying it.

## Next fire

**Read Sunday's `daily-brief` `ingest_regulatory` log line** and close E-20 with it quoted. Then
**E-27** → **E-28**. Check #392 first — if it merged, the gate is right and (d).2 is `issue_next.py`.
