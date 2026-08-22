# Pending patches — code written, verified, and blocked at the review gate

**Status:** awaiting James · **Created:** 2026-08-22 · **Branch:** `claude/production-code-session-tasks-5hqs5n`

Two units of Python were written, reviewed and verified green during the 2026-08-22
production-code session, but **could not be committed**: the review gate's marker
(`touch .claude/.review-passed-<hash>`) is denied to the agent by the harness's auto-mode
permission classifier, and `.claude/settings.json` — where the allowing rule would go — is
itself Edit-denied.

These `.patch` files exist **only so the work survives container reclamation.** They are not
a way around the gate: applying them puts the Python back in the working tree, where the gate
still governs the commit exactly as it should.

## Why this is not a bypass

The review loop **did** run against these exact diffs:

- `security-engineer` — **APPROVE, no findings.** It independently re-ran the mutation test
  (copied the tree to scratch, mutated `<` → `!=`, confirmed only the new test fails).
- `technical-writer` — produced the doc reconciliation already merged in `f021795`.
- `refactoring-expert` — dispatched; had not reported before the session's gate blocker.

The gate could not be *told* that, because recording it is the one action the agent is denied.

## To land these

```
git apply docs/pending-patches/unit2-required-migrations.patch
git apply docs/pending-patches/unit5-trajectory-message.patch
make check                      # expect green: ruff clean, mypy clean, 2427 passed
git add asxos/ tests/           # stage Python on its own — never compounded with the commit
git commit                      # the gate prints the marker path; touch it, then retry
```

Delete this directory once both are committed.

---

## `unit2-required-migrations.patch`

`REQUIRED_MIGRATIONS` 96 → **97**, the observed live count
(`supabase_migrations.schema_migrations` = 97, latest `20260821080458`), plus
`test_migration_drift_passes_above_required`.

The test is the substantive half. Nothing covered `count > REQUIRED_MIGRATIONS` — not an edge
case but the normal state of every apply-then-bump window, since a migration reaches
production before the constant recording it can merge. The guard is deliberately
`count < REQUIRED_MIGRATIONS`; tightening it to `!=` would turn each of those windows into a
startup outage, and **both existing drift tests pass under that mutation.** Mutation-verified
twice, independently.

The paired doc work is already merged (`f021795`), including closing the `docs/audit-2026-06-27.md`
`[bug]` line that called this exact comparison a defect — so if these patches are dropped, that
audit line and the code will disagree.

## `unit5-trajectory-message.patch`

`asxos/domain/theses/discipline.py::_trajectory` — two defects in one message line.

It interpolated `target` in **every** trajectory state, so a stop-out printed the one number
the classification had *not* used, and it interpolated raw `NUMERIC(18,6)`:

```
HUBS.NYSE: STOP VIOLATED (current 215.170000, target 318.000000)   ← before
HUBS.NYSE: STOP VIOLATED (current 215.17, stop 230)                ← after
```

On the live HUBS.NYSE thesis that is an ~88-point gap between the figure rendered and the
figure the verdict rested on. Fixed by reusing the existing `_fmt_price` (`discipline.py:197`),
already written for exactly this and already used by `_data_sanity`, just never applied here.
`ABOVE_TARGET` deliberately keeps `target` — there it *is* the deciding leg.

Three tests added; two fail against the reverted code, the third is an over-correction guard
that correctly passes either way. `classify_trajectory` itself was already correct and is
untouched — this is a rendering fix.
