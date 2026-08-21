---
paths:
  - jobs/**
---

# Job & Cron Conventions — asxos

## Job Structure

- Every cron job uses the `JobMonitor` async context manager from
  `asxos/jobs/utils/job_monitor.py`. It writes lifecycle to `job_runs`
  (status, duration_ms, rows_written, error_message) and pings
  Healthchecks.io: base URL on success, URL + `/fail` on failure (explicit
  failure signal; also marks the check for deadman purposes), and
  deliberately nothing on 'blocked' (the deadman should miss so "upstream
  stuck" surfaces). Its stale-row heal in `__aenter__` is cross-`as_of`:
  any `running` row for the job older than 2 hours is failed, whatever
  date it was for.
- No Sentry wrapper. No `record_job_completion` / `job_completions` table —
  that was the old system.
- No `ALERT_WEBHOOK_URL` / `ALERT_EMAIL` — alerting is "Healthchecks.io
  notices a missed ping and emails me." Single user, single channel.

## Pipeline Guards

- Generate-signals gates on `sync_prices` having a `status='success'` row
  in `job_runs` for the target `as_of`. See `_upstream_ok` in
  `jobs/generate_signals.py`. Warns and continues on manual runs (when the
  guard fails, the operator is presumed to know what they're doing).
- No `pipeline_checks.is_asx_trading_day` helper — schedules are
  weekday-only in cron syntax (`0-4` day-of-week for the trading-day crons).
  Public-holiday handling is acceptable noise for a single-user system.

## Scheduled Pipelines (UTC, per `.github/workflows/`)

Jobs run as GitHub Actions workflows. **`.github/workflows/` is the source of
truth for every scheduling question** — read the workflow file, never a
schedule written down somewhere else (including here).

```
13:30 daily        backup.yml           (pg_dump → asxos-backups repo; restore drill on dispatch)
16:00 Sat          weekly-research.yml  (6 steps: universe → security master → corporate
                                         actions → financial statements → fundamentals PIT
                                         → fundamentals)
20:30 Sun-Thu      daily-brief.yml      (12 steps: prices → validate prices → snapshot
                                         portfolio → market context → underlyings →
                                         regulatory → news → sentiment → compose brief,
                                         then macro scoring → AU positions → thesis
                                         invalidations)
21:30 Mon-Fri      us-positions.yml     (alert-only; lands after the NYSE close on both
                                         sides of the US DST boundary)
22:00 daily        pipeline-health.yml  (watchdog; jobs/check_cron_health.py)
```

Within a workflow, **step order IS the dependency graph** — a failed step blocks
every step below it. Add a new job at the position that reflects what it depends
on; never express a dependency as a clock offset.

The post-send steps in `daily-brief.yml` sit deliberately *after* `compose_brief.py`
so a failure there cannot cost the brief itself. They still fail the run.

GitHub cron is best-effort: runs can start minutes late at busy hours. Fine for a
daily brief, not for market-microstructure timing. Mon-Fri AEST anchors; UTC
offset 10h. DST shift is acceptable noise.

`schedule:` only fires from `main`, so a schedule change goes live on merge.
`workflow_dispatch` works immediately on any ref, but dispatch is constrained:
only `full-check.yml`, `targeted-ml-tests.yml`, `migration-integration.yml`,
`backup.yml` and `claude-execute.yml` may be dispatched from a session.
Dispatching a production, secret-bearing job (`daily-brief`, `us-positions`,
`weekly-research`, `pipeline-health`) is denied and reserved to James.

## Idempotency

- All writes are UPSERTs (`ON CONFLICT (...) DO UPDATE`). Safe to re-run.

## NumPy + asyncpg

- asyncpg handles numpy types natively. No adapter registration needed
  for most jobs (`jobs/sync_prices.py`, etc.).
- Any job using psycopg2 must register adapters BEFORE any `executemany` /
  `execute` call with numpy values (CLAUDE.md non-negotiable #9):
  ```python
  for np_type, py_type in [(np.int64, int), (np.int32, int), (np.float64, float)]:
      psycopg2.extensions.register_adapter(np_type, lambda x, cast=py_type: AsIs(cast(x)))
  ```
  No job currently uses psycopg2 as of the 2026-08-19 Model A retirement
  (its last user, the training chain, was removed) — kept here as the
  reference snippet for the next one that does.

## Environment Variables (per workflow)

Secrets live in ONE store — the repo's Actions secrets — and reach a job through
the `env:` block of its workflow. That block is the authority for what a job
actually gets; read it rather than assuming.

`DATABASE_URL` is set in every workflow. Python is pinned to 3.12 by
`actions/setup-python`, not by an env var. The rest are workflow-specific:

- `EODHD_API_KEY` — `daily-brief`, `weekly-research`
- `FRED_API_KEY` — `daily-brief`
- `RESEND_API_KEY`, `BRIEF_FROM_EMAIL`, `BRIEF_TO_EMAIL` — `daily-brief`,
  `us-positions`, `pipeline-health`
- `BACKUP_GITHUB_TOKEN`, `BACKUP_REPO` — `backup`
- `ASXOS_PERSONAL_USE` — `daily-brief`, `us-positions`
- `ASXOS_TZ` — `daily-brief`, `weekly-research`

`HEALTHCHECK_URL_<JOB>` is currently set in **no** workflow, so the deadman ping
is silently skipped (JobMonitor's documented behaviour, above). Until those URLs
are added, the failure signal is the red run plus GitHub's own run-failure
notification, with `pipeline-health.yml` as the standing watchdog. Adding a job's
Healthchecks URL to its workflow `env:` block restores its deadman.
