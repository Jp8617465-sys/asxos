# 01 — Current State and Recovery Gates

> **Status: factual snapshot + gate definitions. The production loop is NOT
> proven recovered. Do not treat anything below as a green light.**

## 1. Where ASXOS actually is

ASXOS is a mature M1–M14 single-user investment-intelligence platform whose
**codebase is well ahead of its running production surface**. The repository
contains full ingestion, a LightGBM signal engine, a Decimal-pure
portfolio/tax/CGT stack, and a landed-but-dark-launched V2 thesis layer.
Production, by contrast, runs a **minimal 13-service loop** that has **not**
been validated since the DATABASE_URL recovery.

The strategic risk is the one named in `docs/foundation/phase-b-failure-postmortem.md`:
**breadth shipped faster than operational verification.** The predecessor died
reporting "healthy" while every dependency was dead. ASXOS encodes the fixes
(hard-fail startup, no feature flags, render.yaml as source of truth) — but the
monitoring tier that would *prove* health is currently **not deployed**.

## 2. What is fixed (merged to main, ancestors of `2c3e50b`)

| Fix | Commit | Date (UTC) |
|---|---|---|
| `generate_signals` `as_of` handling | `c5f920b` | 2026-06-09 |
| Phase 2A stop-the-line (date-cast bugs, regime fabrication, brief staleness) | `dfd6fe5` | 2026-06-12 21:10 |
| Cron pool init before job monitor (`test_cron_pool_init.py`) | `766dfb9` | 2026-06-13 07:29 |
| Backup cron build fix — remove `apt-get` (`test_render_backup_build.py`) | `2c3e50b` | 2026-06-13 09:25 |

## 3. What is proven (post-deploy production evidence)

| Proven | Evidence |
|---|---|
| `asxos-api` starts on corrected DB credential | "Application startup complete" 2026-06-14 05:46 UTC; hard-fail lifespan means a clean start *is* a DB-connectivity proof |
| Backup pipeline works end-to-end | `asxos-2026-06-13.sql.gz` pushed to `Jp8617465-sys/asxos-backups` @ `1917b3e`; backup uses raw `pg_dump "$DATABASE_URL"`, bypassing the Pydantic round-trip |
| 11 services carry correct DB fp `a07ca95a44` | fresh Render env-var audit 2026-06-14 (api + sync_prices/fundamentals/universe + snapshot + generate_signals + ingest_sentiment/news/regulatory + compose_brief + backup) |
| Healthcheck deadman coverage | every live cron has its `HEALTHCHECK_URL_*` **except** `ingest_sentiment` |

## 4. What remains UNPROVEN

| Unproven | Why it matters |
|---|---|
| The daily loop produces fresh signals | Signals last known frozen at **2026-05-20**. No live cron window has run on the corrected credential yet. |
| `generate_signals` date-cast fix works in prod | Fixed in code (`c5f920b`/`dfd6fe5`); never observed succeeding in production. |
| `ingest_sentiment` ever succeeds | 0 lifetime successes; also missing its healthcheck var. |
| `compose_brief` delivers a correct brief | Brief content is not persisted to DB/API; only observable in the operator inbox. |
| `snapshot_portfolio` runs clean post-rollout | Gated on `sync_prices`; unverified. |
| The loop survives a full day unattended | The cron-liveness monitor (`check_cron_health`) is **not live**. |

## 5. The minimal production loop

```
13:30 UTC daily      backup_irreplaceable     (raw pg_dump → asxos-backups; NO job_runs row)
18:00 UTC daily      sync_fundamentals        (per-symbol UPSERT)
20:30 UTC Sun–Thu    sync_prices              (bulk-by-date; one EODHD call)  ── GATE source
20:40 UTC Sun–Thu    snapshot_portfolio       (GATE: sync_prices ok)
20:50 UTC Sun–Thu    generate_signals         (GATE: sync_prices ok)
20:55 UTC daily      ingest_regulatory        (RSS — chronically failing)
20:57 UTC Sun–Thu    ingest_news
21:00 UTC Sun–Thu    compose_brief            (Resend email ~07:00 AEST)
21:02 UTC Sun–Thu    ingest_sentiment         (0 successes; missing healthcheck var)
```

(Schedules per `.claude/rules/job-conventions.md`. AEST = UTC + 10h. DST shift
is accepted noise.)

## 6. Recovery gates before strategic work resumes

| Gate | Definition | Status |
|---|---|---|
| **G1 — core loop green** | `sync_prices`, `snapshot_portfolio`, `generate_signals`, `compose_brief` all `status='success'` for the current `as_of` in `job_runs` | PENDING |
| **G2 — signal freshness** | `MAX(signals.as_of) >= CURRENT_DATE - 1` | PENDING (frozen 2026-05-20) |
| **G3 — five-day stability** | G1 holds for 5 consecutive trading days | PENDING |
| **G4 — monitoring deployed** | `check_cron_health` live (with expected-set trimmed to live jobs) | NOT STARTED |
| **G5 — backup observability** | backup writes a `job_runs` row so G4 can see it | NOT STARTED |

Lane A (production cleanup) opens after **G1** is GREEN. Lane B (strategy)
opens only after **G3**.

## 7. What must NOT be touched until verification

- `generate_signals`, `ingest_sentiment`, `compose_brief`, `retrain_model_a`,
  `track_signal_outcomes` — do not run.
- `asxos-build-portfolio` — do not restart; do not roll its DB credential yet.
- `asxos-retrain-model-a` — do not unsuspend.
- Thresholds, tax logic, signal architecture — frozen.
- V2 / parallel engine — stays dark.
- env groups, missing-service creation, cron delete/recreate, migration
  recovery — all blocked.

## 8. How to interpret the verification verdict

| Verdict | Definition | Action |
|---|---|---|
| **GREEN** | G1 + G2 both hold; core loop succeeded for current `as_of`, signals fresh | Open Lane A batch 1 (see `02-roadmap-tracks.md` §Lane A). Still require per-item approval. |
| **YELLOW / MIXED** | Core path green but peripherals red (`ingest_regulatory`, `ingest_sentiment`), OR core path green one day but not yet 5 days | Declare **core** status independently of peripheral noise. Log peripherals as Lane A items. Do not start Lane B. Continue daily checks toward G3. |
| **RED** | Any core-path job failed for current `as_of`, or signals still stale | Diagnose in dependency order (Prompt 3). One fix at a time. No batches, no Lane A, no Lane B. |
| **UNKNOWN** | No cron window has run yet, or `job_runs` inconclusive | Wait for the window. Do not infer health from `asxos-api` being up — the API proves DB connectivity, not that the *crons* ran. |

**Critical interpretation rule:** `asxos-api` being healthy is **not** loop
recovery. The API proves the DB credential works for *one* asyncpg consumer; it
says nothing about whether the scheduled crons fired and wrote fresh rows. Only
`job_runs` + signal/price freshness prove the loop.
