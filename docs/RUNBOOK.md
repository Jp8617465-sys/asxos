# RUNBOOK

What to do when an alert fires. One entry per alert. Kept in-repo so it versions
with the code that emits the alerts rather than drifting into a stale wiki.

**Scope:** this documents *response*, not detection. Every alert path below
already exists and already fires; this is the missing half.

**Golden rule:** every scheduled job in this repo is idempotent (`ON CONFLICT`
upserts across 20 files). **Re-running a failed job is safe.** Manual
`workflow_dispatch` is safe at any time. That makes "dispatch it again and watch"
the correct first move for most alerts, and it is why almost nothing here
requires a decision at 6am.

---

## The schedule, in one table

All times UTC. Sydney is +10 (AEST) or +11 (AEDT).

| Time | Workflow | What it does | Alerts by |
|---|---|---|---|
| 06:00 daily | `migration-drift` | applied ledger vs `migrations/` on disk | red run |
| 13:30 daily | `backup` | dump + rebuild-from-migrations + row-count verify | red run |
| 15:17 daily | `nightly-check` | full suite on `main` | red run + Healthchecks deadman |
| 20:30 Sun–Thu | `daily-brief` | the 9-step pipeline below | email + Healthchecks + red run |
| 21:30 Mon–Fri | `us-positions` | US holdings check | email + Healthchecks |
| 22:00 daily | `pipeline-health` | watchdog over `job_runs` | email + red run |
| 16:00 Sat | `weekly-research` | weekly research pass | Healthchecks |

`daily-brief` step order **is** the dependency graph — a failed step blocks
everything below it:

```
sync_prices → validate_price_data → snapshot_portfolio → ingest_market_context
  → ingest_underlyings → ingest_regulatory → ingest_news → ingest_sentiment
  → compose_brief
```

So "the brief didn't arrive" usually means *an upstream step failed*, not that
the email broke. Read the pipeline top-down, not bottom-up.

---

## ALERT: the morning brief did not arrive

**Means:** any of the nine `daily-brief` steps failed, or the send failed.

1. **Actions tab → `daily-brief`.** Did it run at all?
   - **Never ran** → GitHub's scheduler delayed or dropped it. `schedule:` is
     best-effort and only fires from the default branch. Dispatch it manually.
   - **Ran and is red** → open the log; the *first* red step is the cause. Steps
     below it never ran, so ignore them.
2. **Ran green but no email** → the send path. Check `RESEND_API_KEY` has not
   been rotated and Resend is up. `send_brief` raises on missing config rather
   than swallowing, so a green run with no email is genuinely unusual — the run
   log will say.
3. **Safe action:** re-dispatch `daily-brief`. Idempotent.
4. **Do NOT:** hand-edit production tables, or re-run migrations to "fix" data.

---

## ALERT: pipeline-health found issues (22:00)

`jobs/check_cron_health.py` emails **and** raises, so you get both an email and
a red run. It detects exactly four things — the email names which:

| Finding | Means | Action |
|---|---|---|
| Job stuck `running` >2h | process died before `__aexit__`; the `job_runs` row was never closed | check that job's last Actions run; re-dispatch |
| Expected-daily job with no `success` inside its window (36h; 80h for the weekday-only `check_us_positions`) | the job is silently not running | check its workflow's schedule and last run. A Monday-UTC `MISSING` for a Mon–Fri job was a structural false positive until 2026-09-02 (`jobs/check_cron_health.py` `_EXPECTED_DAILY`) |
| 2+ consecutive `failure` | a real, persistent break | read that job's log; this is the one that usually needs a code fix |
| `success` **with a degraded note** | the run cleared its threshold while a source hard-failed | read `job_runs.error_message`; a green cron is hiding a dead feed |

That last one is the subtle one. It exists because a partial success that passes
its threshold would otherwise be invisible.

---

## ALERT: price validation anomalies

`jobs/validate_price_data.py`, inside `daily-brief`. Three checks: >25% daily
moves on stocks ≥ $0.02, active symbols missing an `as_of` row, and any close
≤ 0 in the last 7 days.

Severity is by count, deliberately:

- **1–10 anomalies** → email, run still records success and pings Healthchecks.
  Review when convenient; usually real corporate actions.
- **>10 anomalies** → email **and** raise. The pipeline stops here, so no brief.
  This is the tier that means "something is systematically wrong with the feed."

The $0.02 floor is load-bearing: at a $0.001 tick a single tick is 25–100%+, so
sub-cent nano-caps flagged 14-of-14 false positives and hard-failed the job daily
before the floor was added. **Do not lower it** without re-reading that history.

---

## ALERT: migration drift (06:00)

`scripts/check_migration_drift.py`. Exit codes: **0** agree · **1** drift ·
**2** `DATABASE_URL` missing.

It is a **name-set diff**, not a count, and reports two directions:

- **`applied_not_in_repo`** — someone applied a migration to production out of
  band. This is the serious one: production carries schema this repo cannot
  reconstruct. Recover the DDL (`pg_get_indexdef` / `pg_dump --schema-only`),
  write it into a numbered file, and confirm the restore drill rebuilds it.
  **Investigate before the next migration PR merges.**
- **`in_repo_not_applied`** — a file exists that was never applied. Usually a
  pending migration; confirm it is intentional.

Migration `0042` is **parked and must never be applied.**

A red run here can also just be a Supabase blip — this workflow deliberately
does not sit inside `full-check` so a brief outage cannot redden unrelated PRs.
Re-dispatch once before treating it as real drift.

---

## ALERT: backup failed (13:30)

The workflow is more than a dump: it verifies source identity, asserts `pg_dump`
can dump the server, **rebuilds a clean schema from the repo's migrations**, then
restores the dump and verifies every table's row count.

So a red backup means one of: the dump failed, **or the repo's migrations no
longer rebuild the production schema.** That second case is the same class of
problem as `applied_not_in_repo` above — check migration drift first, they often
fire together.

---

## ALERT: Healthchecks deadman fired (no ping)

A check went from up to down because a ping never arrived. This is the only alert
that catches **"the job never ran at all"** — a dropped schedule, a disabled
workflow, or a runner that died before any code executed. Nothing inside the job
can report this, which is the whole point.

`JobMonitor` maps three states, and the middle one matters:

| Outcome | `job_runs` | Healthchecks |
|---|---|---|
| success | `success` | ping |
| `UpstreamBlocked` / `ModelGateDormant` | `blocked` | **no ping** |
| any other exception | `failure` | ping `/fail` |

`blocked` is not a crash — it means upstream was not ready, or rule #11's model
quarantine is doing its job. It deliberately does not ping, so a long-running
`blocked` state *will* eventually fire the deadman. Check `job_runs.status`
before assuming a break.

If `HEALTHCHECK_URL_*` (or `HC_NIGHTLY_URL`) is unset, the ping is skipped
silently and this alert can never fire for that job.

---

## ALERT: nightly-check failed (15:17)

The full suite went red on `main` without anyone pushing. Two likely causes,
and they are distinguishable:

- **A transitive dependency resolved differently.** Nothing in git changed. The
  run log's install step shows the versions; compare against the last green run.
- **A date-dependent test.** 15:17 UTC puts the UTC date and the Sydney date on
  different calendar days year-round — that is deliberate, and it is exactly the
  bug class this run exists to surface. Bare `date.today()` is banned in
  `asxos/`, `jobs/` and `scripts/` by an AST guard
  (`tests/test_no_bare_date_today.py`) that fails CI on any new call; every
  former call site goes through `asxos/clock.py::today()`, which resolves the
  date in `settings.asxos_tz` (Sydney) rather than on the UTC runner. So if a
  failure here involves a wall-clock date, ask which side of that line the code
  is on: something is reaching the UTC runner's day (`date.today()`, or a
  `datetime.now()` without a zone) where it should be reaching `clock.today()`.
  The only permitted bare calls are the two tax allow-list sites,
  `asxos/domain/tax/positions.py` and `asxos/domain/tax/cgt.py` — the sweep
  stopped at `asxos/domain/tax/` by ADR constraint, and each is a
  `today = today or date.today()` injectable default that every caller
  overrides and every test pins, so no test exercises the bare path. They are
  not harmless (a CGT disposal evaluated a day early can flip the 12-month
  discount, spec §5.1); converting them needs a tax-spec review, not a sweep,
  and the guard fails if an allow-listed site is converted without being
  removed from the list.

---

## Escalation

There isn't any. One operator, no secondary. An alert during an absence waits —
no tooling changes that. This runbook *is* the escalation path: it exists so the
person reading it six months from now does not have to re-derive any of the above.

## When something here is wrong

Fix it in the same PR as the behaviour change. An entry that has drifted from the
code is worse than no entry, because it will be trusted at 6am.
