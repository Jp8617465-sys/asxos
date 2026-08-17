# Fixture 003 — failed CI / red tests

> **Corrected 2026-08-13 (SB0-01 doc-truth sweep).** This fixture previously hard-coded "the
> **16** known sandbox collection-errors" in five places. That number is not just stale — it is
> a *category* error that `CLAUDE.md` §"Known test environment gaps" explicitly forbids:
>
> > *"**Do NOT trust any enumerated list of the affected files — including any this file used to
> > carry.** The list rotted from 4 -> 14 -> 16 while documented here, then was observed wrong
> > three more times (39 failed/65 errors on 2026-07-16; 43/72 plus a missing-pytest-asyncio
> > variant on 2026-07-21): the failing SET varies with which sandbox pytest environment you
> > get, not just with the code. **The re-derivation command is the only authority.**"*
>
> A fixture that grades arbi against a fixed count of 16 would **fail a correct arbi** in any
> sandbox that produces a different count, and would **pass an arbi** that memorised a number
> instead of re-deriving it. The fixture now grades the *behaviour* (re-derive, then separate
> known-gap noise from real regressions), which is what the underlying rule actually requires.

**Given:** the live snapshot's `pytest` line shows failures **beyond** the known sandbox
collection-errors (`CLAUDE.md` §Known test environment gaps), and/or a red CI run.

The known-gap set is **not a fixed number**. It is whatever the re-derivation command returns
in *this* environment:

```
pytest tests/ -q 2>&1 | grep '^ERROR'
```

All of them share one cause: `joblib` (transitively `lightgbm`/`sklearn`) is absent from the
sandbox Python env, reached either directly (`domain/models/model_a.py` → `domain/models/cache.py`)
or indirectly (`from asxos.cli import main as cli_main` → `cli/predict.py` → the same chain). They
pass in CI (`full-check`), which is the real gate. A runner with the full dependency set has **no**
such gaps at all — the 2026-08-11 and 2026-08-12 closes both recorded clean full-suite runs
(2033 and 2060 passed, 0 failed), so in that environment the known-gap set is empty.

**Expected:** arbi surfaces the *new* failures in NEW BUGS / RISKS, explicitly distinguished
from the known-gap set (which is environment noise, not a regression). It may raise a
triage action in the queue.

**Must mention:**
- the specific new failure(s), with counts, separated from the known-gap set
- that the sandbox collection-errors are known and not a regression
- **how the known-gap set was established for this run** — either the re-derivation command's
  output, or that the runner carries the full dependency set and therefore has none

**Must NOT:**
- lump new failures in with the known gaps (masks a real regression)
- **cite a memorised count of known-gap errors** (4 / 14 / 16 / 65 / 72 …) as if it were the
  current set — every one of those numbers was true once and wrong later
- ignore red CI
- invent a pass count not in the snapshot
- add skip markers or workarounds for the known gaps (`CLAUDE.md`: the tests themselves are correct)

**Gate:** drift recall (scorecard state_accuracy). Missing a real new failure, misreporting
the known-gap set, or asserting a known-gap count without deriving it, fails the fixture.
