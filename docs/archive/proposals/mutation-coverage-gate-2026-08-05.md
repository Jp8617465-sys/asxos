# Proposal — a mutation-observation gate for regression-coverage claims

**Status:** draft proposal · **Owner of the decision:** James (edits an authority file + a hook)
**Origin:** `docs/product/memory/dream-candidates/2026-08-05-dream.md` RM-1 / L-cand-05.1
**Scope:** one added check in `.claude/hooks/review-gate.sh`, plus a convention line. No code
behaviour change, no runtime effect, no capital surface.

---

## 1. The problem this exists to solve

`approved-lessons.md` already carries the lesson, three times:

- **L7** — live-verify the emitted statement sequence, not hand-written SQL
- **L11** — a green suite, a mocked connection, or hand-written SQL is not proof
  (*and L11's own text records itself as "Third instance of the L7 pattern"*)
- **L12** — a framing is a hypothesis, not truth

The 2026-08-05 window produced instances **four and five**, in a subsystem with no database
triggers involved — so the pattern is not about Postgres. It is about **accepting a proxy for
evidence**. Concretely, in one session:

| Artifact | The claim | What was actually true |
|---|---|---|
| `tests/test_ingest_news_job.py` threshold tests (pre-existing) | the 0.75 threshold is guarded | fakes *raised*; the real worker never raises. Passed green for the whole life of the defect. |
| 2 of 3 newly-written "regression" tests | "these pin the distinction the old predicate could not make" | both **passed against the buggy code**. Zero coverage. |
| An 8-line comment on the CWE-117 scrub | the scrub prevents forged log lines | nothing tested it; removing the scrub left all 57 tests green. |
| The request-side half of the symbol fix | shipped as fixed | reverting `eodhd_symbol()` left all 52 news tests green. |

Each was invisible to reading and detectable in seconds by running. **The lesson did not fail
for want of clarity; it failed because advisory memory does not gate behaviour.** A fourth
prose copy is predicted to fail the same way.

---

## 2. What is proposed

Extend the existing `review-gate.sh` deny with **one additional condition**, on the same staged
diff it already inspects.

**Trigger.** The staged diff adds or modifies a test function whose *name or docstring* contains
`regression`, `pins`, `pinned`, or `guard` — i.e. the author is making a coverage claim.

**Requirement.** A mutation observation must exist for that claim before the marker may be
written: a file `.claude/.mutation-observed-<sha>` recording, per claimed test, that it was seen
to **fail** with the fix reverted.

**Deny message** (mirrors the existing one's shape):

```
Staged tests claim regression coverage (name/docstring matches regression|pins|guard).
A coverage claim must be OBSERVED, not asserted: revert the fix, confirm the named test
FAILS, restore, confirm it passes. Record it:
  echo "<test_name> FAILS without <file>:<line> fix" >> .claude/.mutation-observed-<sha>
then retry. Two claimed guards on 2026-08-05 provided zero coverage
(docs/product/memory/dream-candidates/2026-08-05-dream.md RM-1).
```

**Sketch** — inserted after the existing `staged_py` computation (`review-gate.sh:93-99`):

```bash
# --- mutation-observation gate (proposal) -------------------------------------
# Only fires when the diff makes a coverage CLAIM; silent otherwise.
claims="$(git diff --cached -U0 -- '*.py' 2>/dev/null \
  | grep -E '^\+' \
  | grep -Ei '(def test_[a-z0-9_]*(regression|pin|guard))|"""[^"]*(regression|pins|guard)' \
  || true)"
if [ -n "$claims" ] && [ ! -f ".claude/.mutation-observed-${sha}" ]; then
  deny "…"   # message above
fi
```

Keyed to the same `${sha}` as the review marker, so any further edit re-arms both.

---

## 3. Honest limits — read before adopting

1. **The marker is forgeable, by design.** `.claude/hooks/review-gate.sh:11,27,37` says so
   explicitly. This raises the floor; it does not close the hole. It converts "I believe this
   test guards X" into "I performed an observation and recorded it" — a *deliberate* step, the
   same standard the existing gate sets.
2. **Regex over a diff is crude.** It will miss a claim phrased without those words, and will
   fire on a test that merely mentions them. The false-positive cost is one `echo`; the
   false-negative cost is the status quo.
3. **It adds friction to every test-bearing commit** that uses the trigger words. Mitigation:
   the trigger is deliberately narrow — an ordinary test asserting behaviour is untouched. Only
   tests *claiming to pin a regression* are gated.
4. **It cannot verify the observation was real** — same limitation the review marker has.
5. **This edits an authority file** (`.claude/hooks/review-gate.sh`) and therefore is James's
   call alone. arbi drafts; it does not apply.

---

## 4. Counter-argument worth weighing

The cheaper alternative is a **convention line only** in `.claude/rules/job-conventions.md` —
"a test claiming regression coverage must have been observed failing without the fix" — with no
hook change. It costs nothing and adds no friction.

**Argument against the cheaper option:** that is precisely what L7, L11 and L12 already are, and
the recurrence count is now five. The dream's evidence is that another advisory line is the
option most likely to fail. If the friction is judged too high, the honest choice is to accept
the risk explicitly and record it in the risk register — not to add a fourth copy and assume it
will bind where three did not.

---

## 5. What would have been caught

Applied to the 2026-08-05 session, this gate fires on:

- `test_all_symbols_failing_hard_fails` (docstring: "The regression this pins…") — **hollow**
- `test_genuine_zero_news_day_succeeds` — **hollow** as originally claimed
- `test_parse_drops_bare_tag_for_a_holding_that_was_not_requested` ("negative control") —
  **mis-scoped**, passed under the mutation it claimed to guard
- the CWE-117 comment — no test existed at all

Four of the session's errors, all detected before commit rather than after. It would **not** have
caught the two causal overclaims in the report (those are prose, not tests) — L12 remains the
only control there, and remains advisory.
