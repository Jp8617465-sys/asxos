# Research data store — schema proposal (design only)

**Date:** 2026-06-22 · **Status:** PROPOSAL. DDL in `migrations/0027_research_store_PROPOSAL.sql` is **NOT applied**. No ingestion code exists. Review this before agreeing the backfill.

The research store is the **point-in-time, survivorship-free** foundation for long-horizon factor research (Layer-1 alpha in the operating-model architecture). It is **separate** from the production tables (`signals`, `rebalance_runs`, `theses`) so research is reproducible and leak-free. Building it is the audit's #1 prerequisite — without it, value/quality factor research is fitting one month of half-empty data.

## The one discipline that makes it leak-free

Every fundamentals/factor row carries **two dates**:
- `as_of` — the data's own date (statement period end).
- `knowledge_date` — when that data became *publicly usable* (filing/disclosure date).

**All research queries filter on `knowledge_date <= test_date`, never on `as_of`.** This is what prevents look-ahead: on 2025-03-01 you may only use fundamentals disclosed on or before 2025-03-01, even though the statement's period end was 2024-12-31. The existing ML loader's 45-day lag is the crude version of this; the research store makes it explicit and exact (filing_date where available).

## Tables (see the migration for full DDL)

| Table | Holds | PIT key |
|---|---|---|
| `rs_security_master` | every security ever listed (incl. delisted) | `listed_date` / `delisted_date` |
| `rs_corporate_actions` | splits, dividends, franking | `ex_date` |
| `rs_financial_statements` | raw historical BS/IS/CF (the source) | `filing_date` |
| `rs_fundamentals_pit` | derived factor inputs (ROE, book value, margins…) | `knowledge_date` |
| `rs_factor_scores` | computed sector-neutral z-scored factors (the Layer-1 input) | `as_of` (knowledge-safe) |
| `rs_index_membership` | ASX200/300 history (survivorship + benchmark) | `effective_from/to` |
| `rs_estimates` | analyst target/EPS (snapshot-only) | `as_of` |

## EODHD → table mapping (availability VERIFIED 2026-06-22, read-only probe)

| Need | EODHD source | Verified? |
|---|---|---|
| Security master + delistings | `exchange-symbol-list/AU` (+ `?delisted=1` → 1,986) | ✅ |
| Splits / dividends | `/splits`, `/div` | ✅ (franking field TBD) |
| Historical financials (35yr) | `/fundamentals` → `Financials.{Balance_Sheet,Income_Statement,Cash_Flow}.{yearly,quarterly}` | ✅ |
| Quality/growth factors (ROE, margins, revenue) | `/fundamentals` → `Highlights` + `Financials` | ✅ (NULL in our DB today — ingestion gap) |
| Shares outstanding history | `/fundamentals` → `outstandingShares.annual` | ✅ (36yr) |
| Analyst target | `/fundamentals` → `Highlights.WallStreetTargetPrice` | ✅ (current snapshot; AU ratings sparse) |
| Index membership history | — | ❌ **not in this API — source TBD** |

**Critical nuance:** `Highlights` ratios are a *current snapshot only*. True PIT fundamentals (`rs_fundamentals_pit`) must be **computed from `rs_financial_statements` lagged to `filing_date`** — not ingested from Highlights. That computation is where look-ahead risk lives; it is the heart of the backfill.

## Build sequence (after this schema is agreed — none of it written yet)

1. Apply the migration (review first).
2. `sync_security_master` job — ingest active + delisted AU symbols.
3. `sync_corporate_actions` job — splits/divs/franking.
4. `sync_financial_statements` job — historical BS/IS/CF (~1,885 symbols × statements; the probe showed 100k/day limit → feasible, confirm).
5. Derive `rs_fundamentals_pit` from statements + filing dates (pure transform; the leak-critical step).
6. Compute `rs_factor_scores` (sector-neutral z-scores) — the Layer-1 input.
7. Wire `alpha_eval` to load `rs_factor_scores` and test value/quality/momentum/low-vol at 63/126/252d — **only now** does the value×quality candidate get tested.

## Open questions (must resolve before ingestion)
1. **Index-membership history source** (ASX200/300) — EODHD doesn't provide it here. Options: S&P licensed data, manual reconstruction, or a proxy (top-N by market cap). Until resolved, survivorship for index-relative work is approximate.
2. **Franking** in EODHD AU dividends — verify the `/div` object carries franking before relying on the AU yield factor.
3. **Statement `filing_date`** — confirm EODHD financial-statement objects carry a disclosure date per period; if not, fall back to `period_end + conservative lag` and flag it.
4. **Backfill cost** — ~1,885 symbols × full history; confirm it fits the EODHD plan's daily call budget and design idempotent, resumable ingestion.

## What this is NOT
Not applied. Not ingestion code. Not a commitment to value×quality (that's tested *after* the store exists). The 5-day ML signal stays quarantined and paper-only throughout; this store is what would let a long-horizon sleeve eventually be *measured* rather than assumed.
