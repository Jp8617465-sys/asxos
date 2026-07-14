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

One row per run (`/arbi`, `/arbi-close`, a scheduled brief, a dispatched task, an
`/arbi-mission` execution):

```yaml
run_id:            # monotonic or timestamp-derived
date:
trigger:           # manual | scheduled | github-event | ci-failure
goal:              # the one thing this run was for
task_type:         # daily-brief | roadmap-update | pr-review | session-close | dream | mission | ...
                   # (mission = an /arbi-mission run; also record its task-graph size + readiness verdict in notes)
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
| wake-2026-07-11 | 2026-07-11 | manual (/arbi "wake up") | daily-brief + state-refresh | I0-I2 | passed | — | done — baseline snapshot recorded; PR #25 reconciled; queue re-ranked (monitoring lane = THE ONE THING); red-team PASS w/ scope caveat |
| autonomy-2026-07-11 | 2026-07-11 | manual (James granted 8h reversible-work autonomy) | build-loop (attended) | I2-I3 (reversible; draft-PR-only) | passed | — | in progress — PR #26: check_model_staleness shelf-aware, track_signal_outcomes revived, validate_price_data $0.02 floor (prod-verified 15→5), sync_financial_statements 512Mi-OOM fix (bounded-worker pool). Dispatched: backend-architect (agent DB read-only role), deep-research (competitive gap analysis). Hard lines held (no merge/deploy/DB-write/Render/capital/Model-A/self-edit). Hourly loop trig_01M5mWFrgZBmqbinLK12F6iU armed to ~20:08Z; stand-down trig_01Qg9BPG3KYvAeKQRxmYAMPA @20:18Z |
| wake-2026-07-13 | 2026-07-13 | manual (/arbi "wake up") | daily-brief + state-refresh + build | I0-I6 (per-action James-gated) | passed | — | done — monitoring lane fixes (cast/snapshot/OOM) shipped as PR #30, **merged to main by James** (first arbi-executed I6, per-action instruction). HUBS 10/20 decision recorded; PR #31 (Guilfoyle mission-control + thesis-as-broker-report reframe) drafted for James |
| overnight-2026-07-13 | 2026-07-13 | manual (James `/goal` 8h reversible overnight window) | build-loop (attended, self-paced) | I0-I4 (reversible; draft-PR ceiling) | passed | — | in progress — arbi picked THE ONE THING (batch sync_financial_statements writes; red-team PASS w/ 2 conditions, both met: --limit 200 smoke measured 77min/32,095 rows → ~15h full-run confirmed the deadline-kill risk). **PR #32** (batch UPSERTs, deadline 3600→5400) + **PR #33** (R12 s766B firewall gate on theme.py's 7 commands) — both draft, review-loop clean, CI green, readiness READY. Findings logged: R13 (review-gate compound-commit bypass), R14 (firewall convention not path-attached to cli/). Hard lines held (no merge/deploy/DB-write/Render/capital/Model-A). No JAMES_NEEDED blockers hit beyond the pre-existing inbox items |

## Today vs the platform

Today this is a markdown table appended by `/arbi` / `/arbi-close`. On Managed Agents it
becomes the agent's **persistent event history** + structured run records, with the scorecard
computed by the outcomes grader. Same audit purpose; this file is the portable spec and the
current substrate.
