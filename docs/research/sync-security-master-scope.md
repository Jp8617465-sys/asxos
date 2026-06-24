# `sync_security_master` — ingestion job scope (design only)

**Scope date:** 2026-06-22 · **Status:** SCOPE — **conditionally next**. No code written. This is the reviewable design for the **first** research-store ingestion job. It populates `rs_security_master` (migration 0027, applied-empty: 0 rows). Review this before any code lands.

Security master is first because it is the research-store source with the **strongest** core availability and **zero production blast radius**: `exchange-symbol-list/AU` returns active names and `?delisted=1` returns the delisted set (1,986 symbols), and it touches no production table. Every later job (`sync_corporate_actions`, `sync_financial_statements`) iterates over this table's `symbol` list, so it is the dependency root and the cheapest place to prove the ingestion pattern (idempotent UPSERT + `JobMonitor` + resumability) before spending the EODHD call budget on 35-year financials.

**Gate (not "no open questions"):** the *core* (active + delisted lists) is verified, but the **enrichment fields are not closed** — the `?delisted=1` delisted-date field name and the `security_type` value set are unconfirmed (§6). Proceed only after a tiny read-only **source-closure probe** confirms them, **or** explicitly accept the v1 fallback (ingest delisted symbols with `delisted_date = NULL`). This job is **unblocked**; `sync_financial_statements` is **not** (the `reportDate` PIT hazard — see `research-store-schema.md` Blockers).

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

## 5. Acceptance criteria (must ALL pass before the job is "done")

These are the gate. Code that doesn't satisfy every line is not merged.

1. **Active + delisted coverage.** Active symbols → `is_active = TRUE`, `delisted_date = NULL`; delisted symbols → `is_active = FALSE` (with `delisted_date` where supplied, else NULL per the v1 fallback).
2. **Stable security identity key.** `symbol` PK; the `.AU` suffix mapping (`_to_symbol`) is documented and **spot-checked for collisions** on the delisted set (two distinct securities must not map onto one PK).
3. **Idempotent UPSERT.** A second consecutive run writes 0 net changes (`rows_written` may report touched rows, but no column value changes). Proven by a rerun diff.
4. **Does NOT mutate production `universe`.** The job reads nothing from and writes nothing to `universe`. Asserted in a test (no `universe` in the job's SQL).
5. **Source + timestamp recorded.** Every row carries `source='eodhd'` and a fresh `updated_at`.
6. **Delisted status recorded.** `is_active` + `delisted_date` populated per §2; re-listing flips `is_active` back to TRUE while **preserving** the prior `delisted_date` via COALESCE (§4), and is flagged in the return dict, not silently overwritten.
7. **Symbol/name changes handled if the payload supports them.** If EODHD exposes a prior-ticker/identifier, record it; if not, a changed `name` updates in place and the change is flagged — **never** silently drop history.
8. **Sample-insert / dry-run validation.** Before the first live run, a dry-run inserts a handful of known symbols (e.g. CBA.AU active, a known delisted name) and the rows are inspected against EODHD by hand.
9. **Safe-rerun / rollback.** Re-running after a partial failure converges (UPSERT, no duplicates); the job is resumable and leaves no half-state. Document how to revert (e.g. `DELETE FROM rs_security_master WHERE source='eodhd'` is safe because the table is research-only and re-derivable).
10. **Tests for duplicate symbols and missing identifiers.** Unit tests cover: a symbol appearing in both active and delisted lists (precedence rule), a row with a missing/blank `Code`, and a duplicate `Code` within one payload.

---

## 6. Source-closure questions (resolve with a read-only probe BEFORE coding)

These are the gate referenced in the header. The job is **conditionally next** until #1–#2 are closed or the v1 fallback is accepted.

1. **Delisted-date field name & granularity.** The `?delisted=1` list confirms *which* symbols delisted (1,986), but the per-symbol `delisted_date` field name/availability in that payload is unconfirmed. If absent, fetching a date per delisted symbol would be ~1,986 extra calls — **v1 fallback: ingest delisted symbols with `delisted_date = NULL`** and backfill dates only if a research query needs them.
2. **`security_type` taxonomy.** Confirm the exact `Type` values EODHD emits for AU so downstream filters (e.g. exclude ETFs/funds from single-name factor work) key off real strings, not guesses.
3. **Duplicate / suffix collisions.** Some EODHD AU codes carry class suffixes; confirm the `.AU` mapping doesn't collide two distinct securities onto one PK. `_to_symbol` is proven for the active set; spot-check it on the delisted set.

---

## 7. Forward note — tradability filter (NOT this job; specified so it isn't reinvented)

A later **investability filter** (used to decide which `rs_security_master` names are actually tradable for the long book, and to replace the crude `price≥$0.20 & $vol≥100k` shell filter used to seed theses) MUST use, at minimum:

- **Rolling 20d / 60d ADV** (average daily volume) — window function over `prices.volume`.
- **Median dollar volume** over the window — robust to single-day spikes (mean is not).
- **Minimum price** floor (penny-stock / sub-tick exclusion).
- **Market cap** where available (shares-outstanding × price from the research store).
- **Spread / slippage estimate** where available.
- **Max participation rate** (target trade size vs ADV) — caps position size by liquidity.
- **Suspension / stale-price checks** — exclude names with stale or gapped recent prices.

**Reuse, do not reinvent:** `asxos/domain/research/alpha_eval.py:226` `liquidity_split()` already buckets by `price` and `dollar_volume`; `alpha_loader.py:38` already computes `dollar_volume = close*volume`; `jobs/validate_price_data.py` already has stale/anomalous-price detection. The `prices` table (`close, volume, adj_close, dt`) supplies everything needed for ADV/dollar-volume. The filter should be a shared utility, not a per-job copy.

---

## 8. Cadence & wiring (after code review)

- **Schedule:** weekly, alongside `sync_universe` (Sat 16:00 UTC). Security master changes slowly; daily is wasteful.
- **render.yaml:** add `asxos-sync-security-master` cron + `HEALTHCHECK_URL_SYNC_SECURITY_MASTER`. Change via `render.yaml` + push + `make check-drift` — never the dashboard (CLAUDE.md #2).
- **No pipeline gate.** Nothing downstream runs on the same cadence yet; this is a standalone research backfill until `sync_corporate_actions` lands and gates on it.
- **Healthchecks.io:** one new UUID, deadman ping on success via `JobMonitor` (standard).

---

## 9. What this is NOT

Not written. Not scheduled. Not a commitment to the rest of the backfill — each subsequent job (`sync_corporate_actions`, `sync_financial_statements`, the leak-critical `rs_fundamentals_pit` derivation) gets its own scope doc and review. This job exists to prove the ingestion pattern cheaply on the source with the strongest core availability and zero production blast radius — **after** its source-closure questions (§6) are settled — and to give the later jobs a `symbol` list to iterate.
