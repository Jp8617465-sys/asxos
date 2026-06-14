# 08 — Tech Debt Register

> **Status: inventory. Recording an item here does not authorize fixing it.**
> Severity S1 (operational risk now) → S4 (cosmetic). "Safe before
> verification" = read-only/non-mutating analysis is OK now. "Blocked until
> verification" = the *fix* must wait for the gate.
>
> Cross-reference: a pre-existing tech-debt registry lives at
> `docs/maintenance/guards-backlog.md` (P0–P3). Items below note overlap.

| ID | Issue | Category | Sev | Evidence | Risk if ignored | Fix complexity | Safe before verify? | Blocked until verify? | Recommended timing |
|---|---|---|---|---|---|---|---|---|---|
| TD-01 | Monitoring tier absent — `check_cron_health` etc. declared-but-not-live | Observability | **S1** | 11 declared services absent on Render incl. all `check_*` | System cannot detect its own cron death (the Phase B failure) | Med (create services) | ✅ plan | ✅ fix gated | Lane A batch 1 |
| TD-02 | `ingest_regulatory` chronic failure | Reliability | **S1** | ATO + Treasury RSS dead; 1/3 sources < 0.5 threshold = hard fail | Daily red; regulatory section perpetually stale | Low–Med (feed URLs / threshold) | ✅ investigate | ⚠️ fix after | Lane A early |
| TD-03 | Backup lacks `job_runs` observability | Observability | S2 | `backup_irreplaceable.sh` uses `pg_dump` directly, no `JobMonitor` | `check_cron_health` blind to backup; silent backup death | Low (post-run insert) | ✅ design | ✅ fix gated | Lane A batch 2 |
| TD-04 | `asxos-build-portfolio` stale DATABASE_URL | Config | S2 | env audit: fp `fca87bb5cc` | Saturday build fails `InvalidPasswordError` | Trivial (single-key PUT) | ✅ | ✅ (after loop green) | Lane A batch 1 |
| TD-05 | `ingest_sentiment` missing healthcheck env var | Observability | S2 | env GET: `HEALTHCHECK_URL_INGEST_SENTIMENT` absent | Deadman blind; 0 successes hidden | Trivial | ✅ | ⚠️ after root-cause | Lane A batch 2 |
| TD-06 | Render config drift (24 declared / 13 live / 11 absent) | Config | S2 | this session's inventory | Confusion; phantom services; false-MISSING from monitor | Med (reconcile) | ✅ inventory done | ✅ fix gated | Lane A batch 2 |
| TD-07 | Stale direct DATABASE_URL values (general) | Config | S2 | 2 of 13 live services stale; recovery used per-service single-key PUT | Recurrence on next rotation; partial propagation | Low per service | ✅ audit | ✅ | Lane A / B |
| TD-08 | Env-group architecture not implemented | Config | S3 | only legacy "ASX Portfolio OS" group, ineffective | Rotation drift recurs (root incident class) | Med | ✅ plan | ✅ | Lane B (deferred; see TO-4) |
| TD-09 | Missing Phase 2B Render services (`render.yaml` ⊅ Render) | Config | S2 | 11 declared-but-absent incl. `validate_price_data`, `track_signal_outcomes`, monitoring tier | Declared features simply don't run; no `job_runs` ever | Med (create) | ✅ plan | ✅ | Lane A (monitoring) / Lane B (rest) |
| TD-10 | Live services absent from `render.yaml` (orphans) | Config | S2 | ~28 legacy non-`asxos-*` services on Render | Ungoverned services; one writes to prod DB (TD-11) | Med (decide keep/prune) | ✅ analysis done | ⚠️ operator | Lane A batch 3 |
| TD-11 | `cleanup-conversations` legacy orphan on prod DB | Safety | S2 | targets Supabase `gxjqezqndltaelmyctnl`, distinct cred `39a6c97cca`, daily 02:30 UTC, DELETE intent; target tables (`advisor_conversations`, `assistant_conversations`) exist but **empty** | Ungoverned daily writer/deleter against prod DB | Low (suspend) but **operator-only** | ✅ analysis done | ⚠️ operator decision | Lane A batch 3 |
| TD-12 | `retrain_model_a` paused / OOM risk | ML/Reliability | S3 | suspended on Render; stale DB | Model staleness; cannot retrain safely | Med (memory plan) | ✅ plan | ✅ | Lane B (Track D) |
| TD-13 | `track_signal_outcomes` quarantined / absent | Quant | S3 | not live on Render | No realised-IC feedback → no promotion gates | Med (deploy) | ✅ plan | ✅ | Lane B (Track C) |
| TD-14 | API health observability thin | Observability | S3 | single `/health` route (`SELECT 1`) | Limited prod introspection | Med | ✅ | ✅ | Lane A/B |
| TD-15 | Email delivery / content not observable | Observability | S3 | brief not persisted to DB; `brief_runs` minimal | "brief stopped and I didn't notice" | Med (footer + brief_runs) | ✅ | ✅ | Lane A/B (guards P0-3, P1-3) |
| TD-16 | Optional ML deps absent in sandbox (joblib/lightgbm/sklearn) | Test env | S4 | CLAUDE.md known-gaps; 4 collection errors + 1 runtime | Sandbox test noise only; pass on Render | None (env-only) | ✅ | n/a | Do-not-chase (per CLAUDE.md) |
| TD-17 | Migration / source-of-truth (DB is ~150-table legacy superset) | Data | S3 | DB has ~150 tables; ASXOS uses ~15–30; `universe_history*`, legacy `model_*` etc. coexist | Confusion; accidental cross-write; backup scope ambiguity | Med (document boundary) | ✅ document | ✅ | Lane A/B |
| TD-18 | Pydantic `PostgresDsn` special-character round-trip risk | Code/Config | S2 | `config.py:26` `database_url: PostgresDsn`; `db.py:13` `str(settings.database_url)`; conftest uses trivial `test:test`, **no special-char test** | Next password rotation could break asyncpg while raw `pg_dump` survives | Low (add unit test) | ✅ test design | ✅ | Lane A batch 2 |
| TD-19 | Schedule / timezone complexity (DST, `0-4` weekday) | Ops | S4 | `job-conventions.md` ("DST shift is acceptable noise") | Edge-day misfires (Fri AEST = Sat UTC) | Low (accepted) | ✅ | ✅ | Deferred |
| TD-20 | No single job-health dashboard | Observability | S3 | only raw `job_runs` SELECTs | Manual SQL each check; slow triage | Med (read-only view/API) | ✅ design | ✅ | Lane A/B |
| TD-21 | `job_completions` (legacy) vs `job_runs` (canonical) confusion | Data | S3 | `job_completions` has 15 rows; `job-conventions.md` states it is the **old** system; `job_runs` (103 rows) is canonical | Querying the wrong table gives wrong health picture | Low (document; never read legacy) | ✅ document | ✅ | Lane A (doc) |
| TD-22 | Two brief engines (V1 active `asxos/brief/` vs V2 dark `asxos/domain/brief/`) | Code | S3 | both present; V2 collector-based dark-launched | Drift, double-maintenance, reshape touches every section | High (reshape) | ✅ | ✅ | Lane B (Track H) |

## Notes on overlap with `docs/maintenance/guards-backlog.md`

| guards-backlog item | Relation here |
|---|---|
| P0-1 aggregate failure threshold | mitigates TD-02 (and scaling scenarios 3/5) |
| P0-3 compose_brief fallback email | mitigates TD-15 |
| P1-3 stale-section footer | mitigates TD-15 |
| P1-4 `check_cron_health` | **built** (`jobs/check_cron_health.py`) but **service not deployed** → exactly TD-01 |
| P3-1 Render `fromService` gotcha doc | informs TD-06/TD-08 (env-group timing footgun) |

## Priority read

The S1 items (**TD-01 monitoring absent**, **TD-02 regulatory failing**) are the
only two that represent active operational risk *right now*. Everything else is
S2 or below and can be sequenced. TD-01 is the single highest-leverage fix once
the loop is green; TD-02 is independent of the DB-auth incident and can be
investigated (read-only) immediately, fixed after.
