# arbi run ledger — the immutable audit trail

**Status:** current
**Scope:** the append-only record of every arbi run, its score, and its outcome
**Last verified:** 2026-07-10
**Owner:** arbi appends (I2, command-invoked); James audits
**Superseded by:** N/A

Every arbi run leaves a row here. This is the audit trail the scorecard trends over, the
promotion gate reads, and James audits. **Append-only — never edit or delete a past row.** A
correction is a new row that references the old one.

---

## What a run record captures

One row per run (`/arbi`, `/arbi-close`, a scheduled brief, a dispatched task):

```yaml
run_id:            # monotonic or timestamp-derived
date:
trigger:           # manual | scheduled | github-event | ci-failure
goal:              # the one thing this run was for
task_type:         # daily-brief | roadmap-update | pr-review | session-close | dream | ...
authority_level:   # tier acted at (0-1 today)
hard_gate_passed:  true/false
episode_score:     # from arbi-scorecard.md, if gates passed
one_thing:         # the ranked #1 action arbi named
dispatched_to:     # specialist agent(s), if any (none at I0-I1)
artifacts:         # PRs/issues/docs touched (paths/links)
outcome:           # done | partial | deferred | superseded | blocked
did_it_work:       # known result, or "pending"
penalties:         # any from the scorecard
notes:             # short; contradictions or lessons go to working memory
```

## The ledger vs the decision log

- **`arbi-run-ledger.md`** (this file) = *every run*, with score + outcome. The audit trail.
- **`decision-log.md`** = the subset that were *governance/prioritisation decisions* (the
  "one thing" calls and their outcomes) — arbi's learning memory, read first each wake.
- **`roadmap-state.md`** = current reconciled state (not history).

A run always writes the ledger; it writes the decision log only when it made a rankable call.

## Rows (append below)

| run_id | date | trigger | task_type | tier | gate | score | outcome |
|---|---|---|---|---|---|---|---|
| _(none yet — first scored run appends here)_ | | | | | | | |

## Today vs the platform

Today this is a markdown table appended by `/arbi` / `/arbi-close`. On Managed Agents it
becomes the agent's **persistent event history** + structured run records, with the scorecard
computed by the outcomes grader. Same audit purpose; this file is the portable spec and the
current substrate.
