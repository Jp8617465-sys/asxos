# `sync_security_master` — ingestion job scope (design only)

**Date:** 2026-06-22 · **Status:** SCOPE. No code written. This is the reviewable design for the **first** research-store ingestion job. It populates `rs_security_master` (migration 0027, applied). Review this before any code lands.

Security master is deliberately first because it is the **only** research-store source the read-only probe verified as *fully* available with no open question: `exchange-symbol-list/AU` returns active names and `?delisted=1` returns the historical/delisted set (1,986 symbols). Every later job (`sync_corporate_actions`, `sync_financial_statements`) iterates over this table's `symbol` list, so it is the dependency root and the cheapest place to prove the ingestion pattern (idempotent UPSERT + `JobMonitor` + resumability) before spending the EODHD call budget on 35-year financials.

---

## 1. Goal & success criteria

Populate `rs_security_master` with **one row per security ever listed on ASX** — active and delisted — so downstream research is survivorship-free.

Done when:
- Every active AU common stock from `exchange-symbol-list/AU` has a row with `is_active = TRUE`, `delisted_date = NULL`.
- Every delisted AU symbol from `exchange-symbol-list/AU?delisted=1` has a row with `is_active = FALSE` and a `delisted_date` where EODHD supplies one.
- Re-running the job changes nothing (pure UPSERT; idempotent).
- A `job_runs` success row exists for `sync_security_master` with `rows_written` = symbols touched.

**Non-goal:** this job does **not** touch the production `universe` table. `rs_security_master` is the research mirror; `universe` stays the tradable production set. They diverge intentionally — `universe` is "what we trade", `rs_security_master` is "everything that ever existed, for backtests".

---

## 2. Source & verified availability (probe 2026-06-22)

| Field (rs_security_master) | EODHD source | Notes |
|---|---|---|
| `symbol` | `Code` + `.AU` suffix (reuse `_to_symbol`) | PK |
| `name` | `Name` | |
| `exchange` | const `'AU'` | |
| `currency` | `Currency` | |
| `security_type` | `Type` | 'Common Stock', 'FUND', 'ETF', 'PREFERRED' … — **store all types**, unlike `universe` which filters to Common Stock |
| `isin` | `Isin` | sparse on AU |
| `delisted_date` | from `?delisted=1` listing | EODHD field name to confirm at build (`Delisted`? per-symbol date may need a second call — see §5) |
| `is_active` | derived: active list → TRUE, delisted list → FALSE | |
| `listed_date` | **not in the symbol-list payload** | leave NULL in v1; backfill later from `/fundamentals` `General.IPODate` if needed |
| `gics_sector` / `gics_industry` | **not in the symbol-list payload** | leave NULL in v1; the symbol list carries a coarse `Sector`/`Industry` but not GICS — backfill from `/fundamentals` later |
| `source` | const `'eodhd'` | |
| `updated_at` | `now()` | |

**Two API calls total** (one active, one delisted) — both already within plan budget; this is the cheapest job in the build sequence.

---

## 3. Reuse vs. add

**Reuse:**
- `EODHDClient.exchange_symbols("AU")` — exists (`asxos/ingestion/eodhd.py:56`), returns the active list.
- `_to_symbol()` — exists (`asxos/ingestion/universe.py`), handles the `.AU` suffix.
- `JobMonitor` context manager, `init_pool`/`acquire`/`close_pool` — standard job scaffold (mirror `jobs/sync_universe.py` exactly).

**Add (small, surgical):**
1. `EODHDClient.exchange_symbols_delisted("AU")` — new method, one line: `self._get(f"/exchange-symbol-list/{exchange}", delisted=1)`. The existing `_get` already threads arbitrary params, so this is a thin wrapper.
2. `asxos/ingestion/security_master.py` — new module, `refresh_security_master(client, conn) -> dict[str,int]`, structured exactly like `refresh_universe`: fetch active + delisted, build the incoming map keyed by symbol, UPSERT each into `rs_security_master`. Returns `{"active": n, "delisted": n, "updated": n}`.
3. `jobs/sync_security_master.py` — new job script, a near-verbatim copy of `jobs/sync_universe.py` (swap the function, the job_name, and the healthcheck env var).

**No new env vars beyond the existing `EODHD_API_KEY` and `HEALTHCHECK_URL_SYNC_SECURITY_MASTER`.**

---

## 4. Idempotency & UPSERT contract

Single statement per symbol:

```sql
INSERT INTO rs_security_master
    (symbol, name, exchange, currency, security_type, isin, delisted_date, is_active, source, updated_at)
VALUES ($1, …, now())
ON CONFLICT (symbol) DO UPDATE SET
    name          = EXCLUDED.name,
    currency      = EXCLUDED.currency,
    security_type = EXCLUDED.security_type,
    isin          = COALESCE(EXCLUDED.isin, rs_security_master.isin),
    delisted_date = COALESCE(EXCLUDED.delisted_date, rs_security_master.delisted_date),
    is_active     = EXCLUDED.is_active,
    updated_at    = now();
```

`COALESCE(EXCLUDED.x, existing.x)` on `isin`/`delisted_date` so a later sparser payload never nulls a value we already learned. **Never** overwrite `listed_date`/`gics_sector` here — those are backfilled by a separate enrichment pass, and this job must not clobber them.

A symbol that appears in the active list but was previously delisted (re-listing — rare) flips `is_active` back to TRUE; `delisted_date` is intentionally **left** via the COALESCE (historical fact preserved). Flag this case in the return dict if it occurs; do not silently flip.

---

## 5. Open questions to resolve at build time (not now)

1. **Delisted-date field name & granularity.** The `?delisted=1` list confirms *which* symbols delisted (1,986), but the per-symbol `delisted_date` field name/availability in that payload is unconfirmed. If absent, fetching a date per delisted symbol would be ~1,986 extra calls — defer: ingest delisted symbols with `delisted_date = NULL` in v1 and backfill dates only if a research query needs them.
2. **`security_type` taxonomy.** Confirm the exact `Type` values EODHD emits for AU so downstream filters (e.g. exclude ETFs/funds from single-name factor work) key off real strings, not guesses.
3. **Duplicate / suffix collisions.** Some EODHD AU codes carry class suffixes; confirm the `.AU` mapping doesn't collide two distinct securities onto one PK. `_to_symbol` is proven for the active set; spot-check it on the delisted set.

---

## 6. Cadence & wiring (after code review)

- **Schedule:** weekly, alongside `sync_universe` (Sat 16:00 UTC). Security master changes slowly; daily is wasteful.
- **render.yaml:** add `asxos-sync-security-master` cron + `HEALTHCHECK_URL_SYNC_SECURITY_MASTER`. Change via `render.yaml` + push + `make check-drift` — never the dashboard (CLAUDE.md #2).
- **No pipeline gate.** Nothing downstream runs on the same cadence yet; this is a standalone research backfill until `sync_corporate_actions` lands and gates on it.
- **Healthchecks.io:** one new UUID, deadman ping on success via `JobMonitor` (standard).

---

## 7. What this is NOT

Not written. Not scheduled. Not a commitment to the rest of the backfill — each subsequent job (`sync_corporate_actions`, `sync_financial_statements`, the leak-critical `rs_fundamentals_pit` derivation) gets its own scope doc and review. This job exists to prove the pattern cheaply on the one source with zero open availability questions, and to give the later jobs a `symbol` list to iterate.
