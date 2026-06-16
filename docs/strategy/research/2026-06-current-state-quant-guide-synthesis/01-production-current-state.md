# 01 — Production Current State (after scheduled-cron recovery)

*Category-1 verified facts. Source: SELECT-only queries against project `gxjqezqndltaelmyctnl`, 2026-06-16 ~23:00 UTC. Render MCP not available this session → relied on `job_runs`.*

## Source identity
Repo `Jp8617465-sys/asxos`; `origin/main` HEAD `a719b3c`; all key commits ancestors of main (`dfd6fe5`, `766dfb9`, `2c3e50b`, `cf5d974`, `fe406d8`, `dcb0461`, `a719b3c`). No production mutation performed.

## Latest scheduled window (job_runs, started ≥ 2026-06-16 18:00 UTC)
| job | as_of | status | rows | started UTC |
|---|---|---|---|---|
| sync_prices | 2026-06-16 | success | 1864 | 20:30 |
| snapshot_portfolio | 2026-06-15 | success | 1 | 20:40 |
| generate_signals | 2026-06-15 | **success** | 1703 | 20:50 |
| ingest_regulatory | 2026-06-16 | **failure** | 0 | 20:55 |
| compose_brief | 2026-06-16 | success | 10 | 21:00 |
| ingest_sentiment | 2026-06-16 | success | 0 | 21:02 |

`ingest_regulatory` error: `only 1/3 succeeded (33.3% < 50% threshold) — first failing: ['ATO','Treasury']` — the **known** RSS-feed issue, not a regression.

## Price coverage (dt ≥ 2026-06-01)
Present: 06-01 (1845), 06-02 (1842), 06-03 (1845), 06-09 (1848), 06-10 (1852), **06-15 (1849)**.
**Missing trading days: 06-04, 06-05, 06-11, 06-12** (two Thu/Fri gaps). 06-08 absent = legitimate (King's Birthday ASX holiday). Latest complete price date = **2026-06-15** (full ASX coverage, ~1849 rows).

## Signal freshness
Latest signal date **2026-06-15** (1703 rows); distinct signal dates = 3 (2026-05-20, 2026-06-10, 2026-06-15). **Advanced beyond the stuck 2026-06-10.** Aligns with latest complete price date.

## GREEN / YELLOW / RED / UNKNOWN

**GREEN (proven):**
- Scheduled automation (all crons fire on schedule, write `job_runs`).
- DB auth recovery (no `InvalidPasswordError` / auth failures anywhere).
- Externally-verified backup.
- `asxos-api` live.
- `sync_prices` → full trading day captured (06-15, 1849 rows; prior residue gone).
- `generate_signals` → ran on new code, `as_of=2026-06-15`, recency-gate **fresh-path** + `latest_complete_trading_day` anchor proven live.
- `snapshot_portfolio`, `compose_brief`, `ingest_sentiment` succeeded.

**YELLOW (data quality / known):**
- 4 missing trading days (06-04/05/11/12) — recurring Thu/Fri gap pattern; root cause unknown.
- No durable `price_coverage` metadata (completeness computed dynamically; `sync_prices` logs but does not persist the verdict).
- `ingest_regulatory` ATO/Treasury feed failing (known, isolated).
- Brief content honesty post-06-15 — operator email inspection still pending.

**RED (signal correctness — contained; not a production-stability issue):**
- `expected_return` units mismatch — **CONFIRMED** (see `04`).
- raw `close` vs `adj_close` — **CONFIRMED** (see `04`).
- These mean **signals are not portfolio-ready**, but the production loop is stable.

**UNKNOWN:**
- Exact deployed commit SHA / container logs (no Render MCP).
- Brief email wording (operator-only).
- Root cause of the Thu/Fri price gaps.
- Final code-confirmation that the persisted `model_a_v1_5` regressor artefact was trained with the `×10_000` line (strongly inferred from the data distribution in `04`).

## Verdict
**Core production loop is operationally GREEN and proven across two windows (Mon 06-15 full 8-cron run; Tue 06-16 real-trading-day run).** The open issues are *signal correctness* (RED, contained) and *data completeness* (YELLOW) — not stability.
