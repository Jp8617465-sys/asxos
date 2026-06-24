# Research data store — schema (APPLIED — EMPTY, PENDING DATA VALIDATION)

**Schema applied:** 2026-06-22 · **Source-availability probe:** 2026-06-24 · **Status:** DDL in `migrations/0027_research_store.sql` is applied (`schema_migrations` count=81). **All `rs_*` tables hold 0 rows.** The schema is **not validated with populated data** — constraints, idempotent UPSERTs, identity keys, and sample inserts have not been exercised. Treat this as *applied-empty*, **not** "done" or "closed".

The research store is the **point-in-time, survivorship-free** foundation for long-horizon factor research (Layer-1 alpha in the operating-model architecture). It is **separate** from the production tables (`signals`, `rebalance_runs`, `theses`) so research is reproducible and leak-free. Building it is the audit's #1 prerequisite — without it, value/quality factor research is fitting one month of half-empty data.

## The one discipline that makes it leak-free

Every fundamentals/factor row carries **two dates**:
- `as_of` — the data's own date (statement period end).
- `knowledge_date` — when that data became *publicly usable* (disclosure date).

**All research queries filter on `knowledge_date <= test_date`, never on `as_of`.** This is what prevents look-ahead: on 2025-03-01 you may only use fundamentals disclosed on or before 2025-03-01, even though the statement's period end was 2024-12-31. The existing ML loader's 45-day lag is the crude version of this; the research store is meant to make it explicit and exact.

### The PIT anchor — RESOLVED as a GUARDED rule (probe 2026-06-24)

The historical-period probe (5 names, 197 `Earnings.History` entries; see
`probes/2026-06-24-eodhd-gate-closure.md`) settled this. Neither field is reliable alone:
`reportDate` is a real disclosure date for most names (median lag 41–55 days) **but
sometimes defaults to `period_end`** (BHP); `filing_date` carries a real lag on some
periods and defaults on others. Each symbol also has **exactly one future/scheduled entry**
(the upcoming FY result) — the original leakage hazard.

**The leak is closed by a guard, not by trusting one field:**
```
knowledge_date = max(d for d in (reportDate, filing_date) if d and period_end < d <= as_of)
                 else  period_end + LAG_DAYS          # conservative: ≥75d annual / ≥60d quarterly
```
- `d <= as_of` drops scheduled/future dates → **no look-ahead** (this is what removes the
  `2026-06-30 → 2026-08-11` forecast row).
- `period_end < d` drops the rows where a field defaulted to `period_end`.
- fallback `period_end + LAG_DAYS` covers the both-defaulted case; document the constant.

Ingestion populates `report_date` and `filing_date` raw and derives `knowledge_date` via the
rule above. **`sync_financial_statements` is unblocked** (it was the hard gate B1).

## Tables (see the migration for full DDL)

| Table | Holds | PIT key |
|---|---|---|
| `rs_security_master` | every security ever listed (incl. delisted) | `listed_date` / `delisted_date` |
| `rs_corporate_actions` | splits, dividends, franking | `ex_date` |
| `rs_financial_statements` | raw historical BS/IS/CF (the source) | `knowledge_date` = guarded max(`report_date`,`filing_date`) in (period_end, as_of] else `period_end + lag` — **resolved, see above** |
| `rs_fundamentals_pit` | derived factor inputs (ROE, book value, margins…) | `knowledge_date` |
| `rs_factor_scores` | computed sector-neutral z-scored factors (the Layer-1 input) | `as_of` (knowledge-safe) |
| `rs_index_membership` | ASX200/300 membership | `effective_from/to` |
| `rs_estimates` | analyst target/EPS (snapshot-only) | `as_of` |

## EODHD → table mapping (probe 2026-06-24; see `evidence-log.md`)

| Need | EODHD source | Status |
|---|---|---|
| Security master + delistings | `exchange-symbol-list/AU` (+ `?delisted=1` → 1,986) | ✅ verified (core); enrichment fields unconfirmed |
| Splits / dividends | `/splits`, `/div` | ✅ verified present |
| Franking | `/div` → `franking` field (7 names, >400 divs) | ✅ verified — string `"<float>%"` (incl. `25.03%`,`90.47%`); partials common; NULL on undeclared/sparse → **store NULL≠0%**; parse `Decimal(s.rstrip('%'))` |
| Historical financials (35yr) | `/fundamentals` → `Financials.{Balance_Sheet,Income_Statement,Cash_Flow}.{yearly,quarterly}` | ✅ verified present |
| Statement disclosure date (PIT) | `/fundamentals` → `Earnings.History[].reportDate` + `filing_date` | ✅ resolved — **guarded** `knowledge_date` (drop `d>as_of`, require `d>period_end`, else `period_end+lag`); both fields default to period_end on some periods |
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
2. `sync_security_master` — **approved next build** (source-closure probe done 2026-06-24: no delisted-date field → `delisted_date = NULL`; `Type` set enumerated; 0 code collisions). See `sync-security-master-scope.md`. Touches no production table; validates the schema on real rows (B2).
3. ~~Franking coverage probe~~ — **done 2026-06-24**. `sync_corporate_actions` — **BUILT** (dividends + splits → `rs_corporate_actions`; franking `"<float>%"`, NULL≠0; see `sync-corporate-actions-scope.md`). Not yet scheduled/populated.
4. ~~`reportDate` semantics probe~~ — **done 2026-06-24**; guarded `knowledge_date` rule defined above.
5. `sync_financial_statements` — **BUILT** (raw BS/IS/CF + `report_date`/`filing_date` raw; the leak-critical `derive_knowledge_date()` guard implemented + tested here; see `sync-financial-statements-scope.md`). Not yet scheduled/populated.
6. Derive `rs_fundamentals_pit` from statements + the *validated* disclosure date (the leak-critical transform).
7. Compute `rs_factor_scores` (sector-neutral z-scores) — the Layer-1 input. Pick and **label** the index/universe choice (true history / forward-snapshot / cap-rank proxy / broad ASX tradable) before any index-relative claim.
8. Wire `alpha_eval` to load `rs_factor_scores` and test value/quality/momentum/low-vol at 63/126/252d — **only now** does the value×quality **candidate** get tested. It is not an approved production replacement.

## Blockers — status after the 2026-06-24 probe

- **B1 (hard):** ~~`reportDate` semantics~~ **RESOLVED** — guarded `knowledge_date` rule closes the leakage; `sync_financial_statements` unblocked.
- **B2:** schema applied-empty — constraints, idempotent UPSERTs, identity keys, sample inserts still **unvalidated**; closed by running `sync_security_master` against its acceptance criteria.
- **B3:** ~~franking coverage/semantics~~ **RESOLVED** — `"<float>%"` string, partials common, NULL≠0%, deep coverage.
- **B4:** historical index membership **still unavailable** → survivorship handling undecided (labeled proxy universe required for v1). The one remaining open gap.

## Open questions

1. **Index-membership history source** (ASX200/300) — unavailable here; options: S&P licensed data, manual reconstruction, or a labeled cap-rank/broad-tradable proxy. **The one unresolved gap.**
2. ~~Franking semantics~~ — **resolved 2026-06-24** (string `"<float>%"`, partials common, NULL≠0%).
3. ~~PIT disclosure date~~ — **resolved 2026-06-24** (guarded `knowledge_date` rule).
4. **Schema populated-data validation** — exercise constraints, idempotent UPSERTs, identity keys, and sample inserts on real rows; closed by running `sync_security_master`.
5. **Backfill cost** — ~1,885 symbols × full history; confirm it fits the EODHD plan's daily call budget; design idempotent, resumable ingestion.

## What this is NOT
Not validated with data. Not ingestion code. Not a commitment to value×quality (a **candidate sleeve**, tested *after* the store is populated and factors computed — never an approved replacement on present evidence). The 5-day ML signal stays **quarantined / paper-only** throughout; this store is what would let a long-horizon sleeve eventually be *measured* rather than assumed.
