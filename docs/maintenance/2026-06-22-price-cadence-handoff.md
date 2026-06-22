# Session handoff — 2026-06-22: sync_prices cadence fix + open follow-ups

Durable record of the price-cadence work and what remains. (The working plan lived in
an ephemeral session container; this note is the persisted version.)

## Shipped this session — live on `main` (`89814c8`)

| Commit | What |
|---|---|
| `89814c8` | **sync_prices cadence fix.** Default run now self-heals **forward** from `MAX(prices.dt)+1` through today (skip weekends, idempotent UPSERT), capped at `_MAX_AUTO_BACKFILL_DAYS=10`. Fixes the bug where Thursday/Friday ASX closes were never ingested (`target=today-1` + Sun–Thu cron). Closed the live gap — 06-18 (1,845) and 06-19 (1,839) now present. |
| `b21defe` | Populate `universe.sector` from EODHD so the constraint-waterfall sector cap converges. |
| `d0fba41` | Propagate `fundamentals.market_cap` into the `universe` cache the allocator reads. |
| `ddcbacf` | Brief anchors regime/signals on the latest complete trading day. |

All committed + pushed; `origin/main == 89814c8`; prod deploys live. Ruff clean;
`tests/test_ingestion.py` + `tests/test_fundamentals_ingestion.py` = 42 passed
(use `.venv/bin/python` — system Python lacks `httpx`).

## Data state at handoff

- **prices** (EOD daily): 1,884 symbols, 2025-01-02 → **2026-06-19**. (06-22 not yet
  published at run time; tonight's cron ingests it.)
- **fundamentals**: through 2026-06-21. **universe**: 1,870 active, 1,832 w/ market_cap,
  1,844 w/ sector.

## Outstanding work

1. **EODHD live probe** (read-only). `eodhd.com` was added to the environment egress
   allowlist, but egress applies at container start — needs a **fresh session**. Pull
   `EODHD_API_KEY` from **only** `asxos-sync-prices` (single targeted read), never print it,
   then GET `/user` (subscriptionType, dailyRateLimit, apiRequests) + `/eod`, `/real-time`,
   `/intraday`, `/fundamentals`, `/news`, `/sentiments` for `CBA.AU` to confirm plan +
   whether intraday/real-time are entitled.

2. **Interior price-hole backfill** (approved, not yet run). Seven missing trading days —
   all Thu/Fri; everything older is a verified ASX holiday:
   `2026-05-22, 05-28, 05-29, 06-04, 06-05, 06-11, 06-12`. The forward-only self-heal
   can't reach them (10-day cap), so run a one-off `asxos-sync-prices` with command override
   `python jobs/sync_prices.py --from 2026-05-22` (unbounded idempotent backfill, ~22 bulk
   calls). The agent is blocked from prod writes → **user triggers**, agent verifies.

3. **Gated downstream — first paper-trade build.** After the backfill, regenerate signals at
   the latest complete date → dry-run `build_portfolio` → persist
   (`ASXOS_PERSONAL_USE=1 python jobs/build_portfolio.py --as-of <date>`). **Do not** persist
   on pre-backfill signals (they rest on incomplete lookback windows).

## Reference

- Supabase project `gxjqezqndltaelmyctnl`.
- Render: sync-prices `crn-d883b0mk1jcs73eaf0r0`, api `srv-d883akkm0tmc738bu9c0`,
  generate-signals `crn-d883ba0js32c73enghmg`, build-portfolio `crn-d88obs6l51nc73fnml8g`,
  sync-fundamentals `crn-d883b577f7vs73e1bfk0`.
- Interior-gap scan (verifies no non-holiday gaps remain):

```sql
WITH days AS (SELECT DISTINCT dt FROM prices),
r AS (SELECT dt, lag(dt) OVER (ORDER BY dt) prev_dt FROM days)
SELECT prev_dt AS gap_after, dt AS next_observed, (dt - prev_dt) AS span
FROM r
WHERE prev_dt IS NOT NULL AND (dt - prev_dt) > 1
  AND EXISTS (SELECT 1 FROM generate_series(prev_dt + 1, dt - 1, interval '1 day') g(d)
              WHERE extract(dow FROM g.d) BETWEEN 1 AND 5)
ORDER BY prev_dt DESC;
```
