# Research data store — schema (APPLIED — EMPTY, PENDING DATA VALIDATION)

**Schema applied:** 2026-06-22 · **Source-availability probe:** 2026-06-24 · **Status:** DDL in `migrations/0027_research_store.sql` is applied (`schema_migrations` count=81). **All `rs_*` tables hold 0 rows.** The schema is **not validated with populated data** — constraints, idempotent UPSERTs, identity keys, and sample inserts have not been exercised. Treat this as *applied-empty*, **not** "done" or "closed".

The research store is the **point-in-time, survivorship-free** foundation for long-horizon factor research (Layer-1 alpha in the operating-model architecture). It is **separate** from the production tables (`signals`, `rebalance_runs`, `theses`) so research is reproducible and leak-free. Building it is the audit's #1 prerequisite — without it, value/quality factor research is fitting one month of half-empty data.

## The one discipline that makes it leak-free

Every fundamentals/factor row carries **two dates**:
- `as_of` — the data's own date (statement period end).
- `knowledge_date` — when that data became *publicly usable* (disclosure date).

**All research queries filter on `knowledge_date <= test_date`, never on `as_of`.** This is what prevents look-ahead: on 2025-03-01 you may only use fundamentals disclosed on or before 2025-03-01, even though the statement's period end was 2024-12-31. The existing ML loader's 45-day lag is the crude version of this; the research store is meant to make it explicit and exact.

### ⚠ The PIT-anchor problem is UNRESOLVED (do not treat `reportDate` as proven)

EODHD financial-statement objects carry `filing_date`, but it **frequently defaults to the period end** (no real disclosure lag). `Earnings.History[].reportDate` was floated as a better anchor — **it is a candidate, not a resolved one.**

**Confirmed hazard (probe 2026-06-24, current date 2026-06-24):** for CBA.AU, `Earnings.History` returned `reportDate 2026-08-11` for period end `2026-06-30` — **both dates in the future**. `Earnings.History` mixes **scheduled/forecast** earnings dates with historical ones. The earlier "genuine ~6-week lag" framing was wrong: that is a *forward schedule*, not a historical disclosure lag. Ingesting `reportDate` as `knowledge_date` without guarding would teach the store about an announcement that has not happened — textbook look-ahead leakage.

Before any statement ingestion uses `reportDate`, a fresh read-only probe of **historical** `Earnings.History` entries must confirm: (a) past `reportDate <= today` and ≈ actual disclosure; (b) how restatements appear; (c) same-day-availability cases; (d) how forecast/future entries are flagged. Ingestion MUST hard-filter `report_date <= as_of/test_date` and fall back to `period_end + conservative lag` when `reportDate` is future or missing. **PIT statement ingestion is BLOCKED until this probe lands (see Blockers).**

## Tables (see the migration for full DDL)

| Table | Holds | PIT key |
|---|---|---|
| `rs_security_master` | every security ever listed (incl. delisted) | `listed_date` / `delisted_date` |
| `rs_corporate_actions` | splits, dividends, franking | `ex_date` |
| `rs_financial_statements` | raw historical BS/IS/CF (the source) | guarded `report_date` (≤ test_date) › `filing_date` › `period_end + lag` — **unresolved, see above** |
| `rs_fundamentals_pit` | derived factor inputs (ROE, book value, margins…) | `knowledge_date` |
| `rs_factor_scores` | computed sector-neutral z-scored factors (the Layer-1 input) | `as_of` (knowledge-safe) |
| `rs_index_membership` | ASX200/300 membership | `effective_from/to` |
| `rs_estimates` | analyst target/EPS (snapshot-only) | `as_of` |

## EODHD → table mapping (probe 2026-06-24; see `evidence-log.md`)

| Need | EODHD source | Status |
|---|---|---|
| Security master + delistings | `exchange-symbol-list/AU` (+ `?delisted=1` → 1,986) | ✅ verified (core); enrichment fields unconfirmed |
| Splits / dividends | `/splits`, `/div` | ✅ verified present |
| Franking | `/div` → `franking` field (one sample: `"100%"`, a **string**) | ⚠ **available in probe (1 symbol) — coverage + semantics validation required** |
| Historical financials (35yr) | `/fundamentals` → `Financials.{Balance_Sheet,Income_Statement,Cash_Flow}.{yearly,quarterly}` | ✅ verified present |
| Statement disclosure date (PIT) | `/fundamentals` → `Earnings.History[].reportDate` / `filing_date` | ⚠ **UNRESOLVED — probe returned a future/scheduled date; PIT semantics unproven (see Blockers)** |
| Quality/growth factors (ROE, margins, revenue) | `/fundamentals` → `Highlights` + `Financials` | ✅ available (NULL in our DB today — ingestion gap) |
| Shares outstanding history | `/fundamentals` → `outstandingShares.annual` | ✅ (36yr) |
| Analyst target | `/fundamentals` → `Highlights.WallStreetTargetPrice` | ✅ (current snapshot; AU ratings sparse) |
| Index membership — **current** | `AXJO.INDX` → `Components` (199 names) | ✅ current snapshot only |
| Index membership — **history** | — | ❌ **not in this API — source TBD (survivorship risk)** |

**Critical nuance:** `Highlights` ratios are a *current snapshot only*. True PIT fundamentals (`rs_fundamentals_pit`) must be **computed from `rs_financial_statements` lagged to a *validated* disclosure date** — not ingested from Highlights, and not from an unvalidated `reportDate`. That computation is where look-ahead risk lives; it is the heart of the backfill and is gated on the PIT-anchor probe above.

## Index membership — proxy, not "ASX 200"

EODHD provides only **current** index membership (`AXJO.INDX` → 199 components). **Historical reconstitutions are unavailable from this API.** Therefore any v1 backtest that selects names by cap-rank / top-N is a **proxy-universe test, NOT a historical ASX 200 test**, and must be labeled as such in every result. Survivorship for index-relative work is approximate until a true historical-membership source is obtained.

## Revised build sequence (schema applied-empty; ingestion written one job at a time, each gated)

1. ~~Apply the migration (review first).~~ **Done — applied 2026-06-22; tables empty, not yet data-validated.**
2. `sync_security_master` — **conditionally next** (see `sync-security-master-scope.md`). Proceed only after a tiny read-only *source-closure probe* confirms the `?delisted=1` delisted-date field name and the `security_type` value set. v1 fallback: ingest delisted symbols with `delisted_date = NULL`. Touches no production table.
3. **Franking/dividend coverage probe** (read-only, representative ASX sample incl. an unfranked and a partially-franked name) **before** any `sync_corporate_actions` code — confirm the `franking` string→numeric mapping and null/absent behavior.
4. **`reportDate` semantics probe** (read-only, historical `Earnings.History` across several past periods/symbols) — **gate for step 5**.
5. `sync_financial_statements` — **BLOCKED** until step 4 resolves. Must hard-filter `report_date <= as_of` and fall back to `period_end + lag`.
6. Derive `rs_fundamentals_pit` from statements + the *validated* disclosure date (the leak-critical transform).
7. Compute `rs_factor_scores` (sector-neutral z-scores) — the Layer-1 input. Pick and **label** the index/universe choice (true history / forward-snapshot / cap-rank proxy / broad ASX tradable) before any index-relative claim.
8. Wire `alpha_eval` to load `rs_factor_scores` and test value/quality/momentum/low-vol at 63/126/252d — **only now** does the value×quality **candidate** get tested. It is not an approved production replacement.

## Blockers before financial-statement ingestion

- **B1 (hard):** `reportDate` future/scheduled-date semantics unresolved → fresh historical-period probe required.
- **B2:** schema is applied-empty — constraints, idempotent UPSERTs, identity keys, sample inserts not validated with real data.
- **B3:** franking coverage/semantics unproven beyond one example.
- **B4:** historical index membership unavailable → survivorship handling undecided (proxy universe required for v1, labeled as such).

## Open questions

1. **Index-membership history source** (ASX200/300) — unavailable here; options: S&P licensed data, manual reconstruction, or a labeled cap-rank/broad-tradable proxy. **Unresolved.**
2. **Franking semantics** — `/div` carries a `franking` field, but on one sample only (`"100%"` string). Coverage across symbols, the string→numeric parse, and partial/unfranked/null behavior are **unvalidated**.
3. **PIT disclosure date** — `filing_date` commonly defaults to period_end; `reportDate` can be a future/scheduled date. **Unresolved** — requires the historical-period probe before use.
4. **Schema populated-data validation** — exercise constraints, idempotent UPSERTs, identity keys, and sample inserts on real rows before declaring any table "done".
5. **Backfill cost** — ~1,885 symbols × full history; confirm it fits the EODHD plan's daily call budget; design idempotent, resumable ingestion.

## What this is NOT
Not validated with data. Not ingestion code. Not a commitment to value×quality (a **candidate sleeve**, tested *after* the store is populated and factors computed — never an approved replacement on present evidence). The 5-day ML signal stays **quarantined / paper-only** throughout; this store is what would let a long-horizon sleeve eventually be *measured* rather than assumed.
