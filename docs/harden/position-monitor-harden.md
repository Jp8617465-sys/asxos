# Harden Report — M-Position-Monitor
Date: 2026-06-02
Branch: `claude/thesis-building-progress-1HPS9`

---

## Security Findings

| Severity | File:Line | Issue | Fix |
|---|---|---|---|
| HIGH | `asxos/cli/position.py` (all entry points) | `position_app` commands (`monitor`, `history`) do not call `_require_personal_use()`. Per portfolio-conventions.md Part 0 Q1 and CLAUDE.md, every CLI entry point touching portfolio/position data must call this gate (s766B Corporations Act 2001 / Westpac v ASIC boundary). | Add `_require_personal_use()` as the first line of both `monitor()` and `history()` typer commands, matching the pattern in `asxos/cli/portfolio.py`. |
| LOW | `asxos/domain/models/cache.py:97–98` | `joblib.load()` deserialises pickled model artefacts. Pickle is insecure by design if the file can be replaced by a third party. Risk here is low because artefacts are written by the internal `retrain_model_a` job and stored in the local models dir controlled by settings, not sourced from the network. | Accept risk with comment; add a note that `asxos_models_dir` must be writable only by the process owner. Already documented in the ML conventions. No change needed unless model artefacts are ever fetched remotely. |
| INFO | `asxos/brief/email.py:14` | `settings = BriefSettings()` at module level hard-fails on import when `BRIEF_*` env vars are absent. This is intentional (CLAUDE.md non-negotiable #10) but causes import-time failure in any test that patches `asxos.brief.email` without pre-setting env vars — the module can't even be imported to apply the patch. This is a test-harness coupling issue, not a runtime security risk. | In the test harness only: either set stub env vars in `conftest.py` before the module is imported, or refactor `fallback_email.py` to avoid importing `asxos.brief.email` at patch time. The production code is correct as-is. |
| PASS | All files | Secrets scan: no `sk-`, `github_pat_`, raw `EODHD_API_KEY=` values, or `hc-ping.com` UUID URLs found in source, tests, migrations, or scripts. | — |
| PASS | All files | SQL injection: all `conn.execute/fetch/fetchrow/fetchval` calls in `asxos/` and `jobs/` use positional `$N` parameters. No f-string or `.format()` interpolation of user-controlled values detected. | — |
| PASS | All files | Log leakage: no `log.info/warning/error/debug` calls emit `DATABASE_URL`, `ASXOS_API_TOKEN`, `RESEND_API_KEY`, or `BACKUP_GITHUB_TOKEN`. | — |
| PASS | `asxos/api/routes/` | Bearer token: the only route is `/health` (returns 200). No other routes are exposed in this branch. No token enforcement gap. | — |
| PASS | All files | `eval`/`exec`: no dangerous `eval()` or `exec()` calls found in production or job code. (Grep hits are all function names containing those substrings, e.g. `evaluate`, `execute`.) | — |

---

## Performance Findings

| Area | Finding | Impact | Fix |
|---|---|---|---|
| `fetch_macro_data()` — serial fetch | VIX and HY OAS are fetched **serially**, not concurrently. The tuple unpacking `vix_obs, hy_obs = (await fred.get_series(...), await fred.get_series(...))` evaluates each `await` in sequence. This is **not** `asyncio.gather`. | ~2× latency for FRED I/O on each `asx position monitor` run (~200–500ms wasted per call). Acceptable at weekly CLI cadence but sub-optimal. | Replace with `vix_obs, hy_obs = await asyncio.gather(fred.get_series(_SERIES_VIX, ...), fred.get_series(_SERIES_HY_OAS, ...))`. |
| `_monitor_async()` — double pool init/close | When `not no_save`, `init_pool()` and `close_pool()` are called **twice**: once at line 92–106 (load context) and again at line 155–161 (save run). A second `init_pool()` call creates a new pool without closing the first, since `db.py`'s `close_pool()` sets `_pool = None` before the second `init_pool()` — so the first pool is leaked if the second init raises. | Pool connection leak (up to 15 connections on each "monitor + save" run if the save path raises between init and close). Under the happy path, the first pool is properly closed, but re-opening costs a connection handshake. | Merge into a single `await init_pool()` / `finally: await close_pool()` block, or refactor `_monitor_async` to pass the already-open conn to `save_run`. |
| Migration 0019 — composite index gap | `position_monitor_runs` has one index: `(symbol, as_of DESC)`. Both `get_last_sentiment_inputs` and `list_runs` queries use `ORDER BY as_of DESC, created_at DESC` and `LIMIT N`. The index covers `symbol` + `as_of` but the tie-break sort on `created_at` requires a heap fetch for any `as_of` tie. | Negligible at single-user weekly cadence (< 52 rows/year per symbol). Would matter only if bulk backfilling introduces same-day duplicate rows. | Add `created_at` to the index: `CREATE INDEX ON position_monitor_runs (symbol, as_of DESC, created_at DESC)`. Low priority; acceptable at current volume. |
| N+1 queries | No loop-per-iteration DB queries found in `position_monitor/service.py`. `load_position_context` issues one `JOIN` query. `list_runs` issues one `fetch` call. `get_last_sentiment_inputs` issues one `fetchrow`. | No N+1 risk. | — |
| `SELECT *` | No `SELECT *` found anywhere in `asxos/domain/position_monitor/`. All queries enumerate columns explicitly. | No issue. | — |
| EODHD in API path | `fetch_price_data()` and `fetch_macro_data()` are not called from any FastAPI route. The only route is `/health`. | No EODHD-in-API-path risk. | — |

---

## Failing Tests — Root Cause Categorisation

All 27 failures are pre-existing (declared in the task brief). None are introduced by this branch's M-Position-Monitor commits. Detailed root causes below.

| Test File | Count | Root Cause | Risk Level |
|---|---|---|---|
| `tests/test_brief_fallback.py` | 9 | `asxos/brief/email.py` calls `BriefSettings()` at **module import time** (line 14). The tests use `patch("asxos.brief.email._send_via_resend")` which triggers an import of `asxos.brief.email` — but the import hard-fails because `BRIEF_*` env vars are not set in the test environment. The mock can never be applied because the module never successfully imports. This is a **test-environment coupling** issue: the production hard-fail behaviour is correct (CLAUDE.md #10); the tests need to either set stub env vars in `conftest.py` before import, or the patch target needs to be the lazy-import path in `fallback_email.py` (`asxos.jobs.utils.fallback_email` rather than `asxos.brief.email`). | TEST_MAINTENANCE |
| `tests/test_brief_v2_sections.py` — `TestCollectMarketContext`, `TestCollectWatchlist`, `TestCollectNewIdeas`, `TestCollectThemeDashboard`, `TestCollectOpportunityCost` | 18 | Tests use `asyncio.get_event_loop().run_until_complete(coro)`. When `pytest-asyncio` manages the event loop and a prior test's async teardown closes the loop, `get_event_loop()` raises `RuntimeError: There is no current event loop in thread 'MainThread'`. The tests pass in isolation (when run as the only file) but fail in the full suite because another test file (specifically `test_brief_fallback.py`, which triggers `asyncio.run()` internally) closes the loop before these tests run. The inner `_run_test` coroutines are left unawaited, triggering `RuntimeWarning: coroutine was never awaited`. Fix: replace `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()` or mark the test methods `@pytest.mark.asyncio` and declare them `async def`. | TEST_MAINTENANCE |

**Note:** No failing test exposes a security or data-integrity defect in production code. All 27 failures are test-harness wiring problems.

---

## Summary

- CRITICAL: 0
- HIGH: 1 (missing `_require_personal_use()` gate on `position` CLI — s766B regulatory firewall)
- MEDIUM: 0
- LOW: 1 (joblib.load, accepted risk)
- PERF-MEDIUM: 1 (serial FRED fetch — 2× latency, fix with `asyncio.gather`)
- PERF-LOW: 1 (double pool init/close — connection leak risk on save-path exception)
- PERF-INFO: 1 (composite index gap — negligible at current volume)
- TEST: 27 (all TEST_MAINTENANCE — no security or data-integrity impact)
- Total security/perf findings: 4 (1 HIGH, 1 LOW, 2 PERF)

---

## Verdict

**BLOCK on HIGH finding**: The `asx position monitor` and `asx position history` commands output position-level investment data without the s766B personal-use firewall (`_require_personal_use()`). Per portfolio-conventions.md Part 0 Q1 this gate is non-negotiable before any portfolio surface is merged.

**Test failures** are all TEST_MAINTENANCE and do not block merge on security grounds, but the 27 pre-existing failures should be resolved as a follow-up sprint item before the branch reaches main.

### Required fix before merge

In `asxos/cli/position.py`, add `_require_personal_use()` to both command functions:

```python
# line 1 of monitor() body:
_require_personal_use()

# line 1 of history() body:
_require_personal_use()
```

And add `_require_personal_use` to the import from `asxos.cli._common`.

### Recommended (non-blocking)

1. `fetch_macro_data()` in `fetcher.py`: use `asyncio.gather` for concurrent VIX + HY OAS fetch.
2. `_monitor_async()` in `position.py`: collapse double `init_pool`/`close_pool` into a single pool lifecycle.
3. Migration 0019: add `created_at` to the composite index if same-day backfill is ever planned.
4. `test_brief_v2_sections.py`: replace `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()`.
5. `test_brief_fallback.py`: set BRIEF_* stub env vars in conftest.py or refactor patch targets.
