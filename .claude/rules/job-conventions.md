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

## Daily Pipeline (UTC, per render.yaml)

```
13:30 daily          asxos-backup-irreplaceable   (pg_dump → asxos-backups repo)
18:00 daily          asxos-sync-fundamentals      (per-symbol; ~3 min on free EODHD)
20:30 Sun-Thu UTC    asxos-sync-prices            (bulk-by-date; one API call)
20:40 Sun-Thu UTC    asxos-snapshot-portfolio     (GATE: sync_prices ok; UPSERT portfolio_daily_snapshots)
20:50 Sun-Thu UTC    asxos-generate-signals       (GATE: sync_prices ok)
20:55 daily          asxos-ingest-regulatory      (RSS pull)
20:57 Sun-Thu UTC    asxos-ingest-news            (news articles for holdings)
21:00 Sun-Thu UTC    asxos-compose-brief          (Resend email at 07:00 AEST)
21:02 Sun-Thu UTC    asxos-ingest-sentiment       (aggregates news → signal_sentiment)
20:00 Sat            asxos-build-portfolio        (weekly; section 6 of brief)
16:00 Sat            asxos-sync-universe          (weekly)
16:00 Sat            asxos-retrain-model-a        (weekly walk-forward)
```

Mon-Fri AEST anchors; UTC offset 10h. DST shift is acceptable noise.

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

## Environment Variables (per job)

`DATABASE_URL` and `PYTHON_VERSION=3.12.13` everywhere; the rest are
service-specific (see `render.yaml`):

- `EODHD_API_KEY` — sync_universe, sync_prices, sync_fundamentals
- `RESEND_API_KEY`, `BRIEF_FROM_EMAIL`, `BRIEF_TO_EMAIL` — compose_brief
- `BACKUP_GITHUB_TOKEN`, `BACKUP_REPO` — backup_irreplaceable
- `HEALTHCHECK_URL_<JOB>` — every job, one Healthchecks UUID per job

The web service `asxos-api` owns the canonical copies. Crons created via
MCP store local copies (drift documented; not blocking).
