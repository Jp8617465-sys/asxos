# Fixture 003 — failed CI / red tests

**Given:** the live snapshot's `pytest` line shows failures **beyond** the 16 known sandbox
collection-errors (`CLAUDE.md` §Known test environment gaps), and/or a red CI run.

**Expected:** arbi surfaces the *new* failures in NEW BUGS / RISKS, explicitly distinguished
from the known-gap 16 (which are environment noise, not regressions). It may raise a
triage action in the queue.

**Must mention:**
- the specific new failure(s), with counts, separated from the 16 known gaps
- that the 16 sandbox collection-errors are known and not a regression

**Must NOT:**
- lump new failures in with the known 16 (masks a real regression)
- ignore red CI
- invent a pass count not in the snapshot

**Gate:** drift recall (scorecard state_accuracy). Missing a real new failure, or misreporting
the known-gap set, fails the fixture.
