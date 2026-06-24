# Research data store — schema (APPLIED)

**Date:** 2026-06-22 · **Status:** APPLIED. DDL in `migrations/0027_research_store.sql` is **applied** (count=81). Tables are **empty** — no ingestion code runs until each source job is reviewed. `sync_security_master` is scoped as the first ingestion job in `docs/research/sync-security-master-scope.md`.

The research store is the **point-in-time, survivorship-free** foundation for long-horizon factor research (Layer-1 alpha in the operating-model architecture). It is **separate** from the production tables (`signals`, `rebalance_runs`, `theses`) so research is reproducible and leak-free. Building it is the audit's #1 prerequisite — without it, value/quality factor research is fitting one month of half-empty data.

## The one discipline that makes it leak-free

Every fundamentals/factor row carries **two dates**:
- `as_of` — the data's own date (statement period end).
- `knowledge_date` — when that data became *publicly usable* (filing/disclosure date).

**All research queries filter on `knowledge_date <= test_date`, never on `as_of`.** This is what prevents look-ahead: on 2025-03-01 you may only use fundamentals disclosed on or before 2025-03-01, even though the statement's period end was 2024-12-31. The existing ML loader's 45-day lag is the crude version of this; the research store makes it explicit and exact.

**PIT anchor priority (verified 2026-06-22):** EODHD financial-statement objects carry `filing_date`, but it **frequently defaults to the period end** (no real disclosure lag). The reliable disclosure signal is `Earnings.History[].reportDate` — e.g. period `2026-06-30` → `reportDate 2026-08-11` (a genuine ~6-week lag). `rs_financial_statements` therefore carries **both** columns: ingestion populates `report_date` from `Earnings.History.reportDate` where a matching period exists and uses it as the preferred `knowledge_date` source; `filing_date` is kept as the secondary signal; the conservative fallback (`period_end + lag`) applies only when neither is trustworthy.

## Tables (see the migration for full DDL)

| Table | Holds | PIT key |
|---|---|---|
| `rs_security_master` | every security ever listed (incl. delisted) | `listed_date` / `delisted_date` |
| `rs_corporate_actions` | splits, dividends, franking | `ex_date` |
| `rs_financial_statements` | raw historical BS/IS/CF (the source) | `report_date` › `filing_date` › `period_end + lag` |
| `rs_fundamentals_pit` | derived factor inputs (ROE, book value, margins…) | `knowledge_date` |
| `rs_factor_scores` | computed sector-neutral z-scored factors (the Layer-1 input) | `as_of` (knowledge-safe) |
| `rs_index_membership` | ASX200/300 membership | `effective_from/to` |
| `rs_estimates` | analyst target/EPS (snapshot-only) | `as_of` |

## EODHD → table mapping (availability VERIFIED 2026-06-22, read-only probe)

| Need | EODHD source | Verified? |
|---|---|---|
| Security master + delistings | `exchange-symbol-list/AU` (+ `?delisted=1` → 1,986) | ✅ |
| Splits / dividends | `/splits`, `/div` | ✅ |
| Franking | `/div` → `franking` field (e.g. `"100%"`) | ✅ **resolved** — field present |
| Historical financials (35yr) | `/fundamentals` → `Financials.{Balance_Sheet,Income_Statement,Cash_Flow}.{yearly,quarterly}` | ✅ |
| Statement disclosure date (PIT) | `/fundamentals` → `Earnings.History[].reportDate` | ✅ **resolved** — use reportDate; `filing_date` defaults to period_end |
| Quality/growth factors (ROE, margins, revenue) | `/fundamentals` → `Highlights` + `Financials` | ✅ (NULL in our DB today — ingestion gap) |
| Shares outstanding history | `/fundamentals` → `outstandingShares.annual` | ✅ (36yr) |
| Analyst target | `/fundamentals` → `Highlights.WallStreetTargetPrice` | ✅ (current snapshot; AU ratings sparse) |
| Index membership — **current** | `AXJO.INDX` → `Components` (199 names) | ✅ current-only |
| Index membership — **history** | — | ❌ **not in this API — source TBD (survivorship risk)** |

**Critical nuance:** `Highlights` ratios are a *current snapshot only*. True PIT fundamentals (`rs_fundamentals_pit`) must be **computed from `rs_financial_statements` lagged to `report_date`** — not ingested from Highlights. That computation is where look-ahead risk lives; it is the heart of the backfill.

## Build sequence (schema applied; ingestion still to be written one job at a time)

1. ~~Apply the migration (review first).~~ **Done — applied 2026-06-22.**
2. `sync_security_master` job — ingest active + delisted AU symbols. **Scoped** → `docs/research/sync-security-master-scope.md`. ← next
3. `sync_corporate_actions` job — splits/divs/franking (franking confirmed present).
4. `sync_financial_statements` job — historical BS/IS/CF (~1,885 symbols × statements; the probe showed 100k/day limit → feasible, confirm). Populate `report_date` from `Earnings.History`.
5. Derive `rs_fundamentals_pit` from statements + `report_date` (pure transform; the leak-critical step).
6. Compute `rs_factor_scores` (sector-neutral z-scores) — the Layer-1 input.
7. Wire `alpha_eval` to load `rs_factor_scores` and test value/quality/momentum/low-vol at 63/126/252d — **only now** does the value×quality candidate get tested.

## Open questions

1. **Index-membership history source** (ASX200/300) — EODHD provides only **current** membership (`AXJO.INDX` → 199 components). Historical reconstitutions are **not** in this API. Options: S&P licensed data, manual reconstruction, or a proxy (top-N by market cap). **Until resolved, survivorship for index-relative work is approximate.** This is the one unresolved gap.
2. ~~**Franking** in EODHD AU dividends.~~ **Resolved 2026-06-22** — `/div` objects carry a `franking` field (e.g. `"100%"`).
3. ~~**Statement `filing_date`**.~~ **Resolved 2026-06-22** — `filing_date` exists but commonly defaults to period_end; use `Earnings.History.reportDate` as the PIT anchor (`report_date` column added). Conservative `period_end + lag` fallback only when neither is trustworthy.
4. **Backfill cost** — ~1,885 symbols × full history; confirm it fits the EODHD plan's daily call budget and design idempotent, resumable ingestion. (Scoped per-job; see security-master scope for the pattern.)

## What this is NOT
Not ingestion code. Not a commitment to value×quality (that's tested *after* the store is populated and factors computed). The 5-day ML signal stays quarantined and paper-only throughout; this store is what would let a long-horizon sleeve eventually be *measured* rather than assumed.
