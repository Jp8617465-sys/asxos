# `derive_fundamentals_pit` — derivation job scope (BUILT + validated)

**Date:** 2026-06-24 · **Status:** BUILT, validated end-to-end on real data. The fourth
research-store job and the one that **uses** the leak guard. Pure DB-to-DB: reads raw
`rs_financial_statements` (yearly) + `rs_corporate_actions`, writes `rs_fundamentals_pit`
— the point-in-time factor INPUTS for Layer-1 alpha. No EODHD.

## What it computes (`compute_pit_factors`)

Per (symbol, fiscal year): joins the income + balance-sheet rows and the trailing-12-month
dividends, and derives:
- ratios: `roe`, `roa`, `gross_margin`, `operating_margin`, `book_value_ps`, `eps_ttm`
- absolutes: `revenue_ttm`, `net_income_ttm`, `total_equity`, `shares_outstanding`, `net_debt`
- income: `dividend_ttm` (sum), `franking_avg_pct` (mean of franked %)
- **`knowledge_date`** = `derive_knowledge_date(period_end, report_date, filing_date, as_of)`
  — the guarded PIT key (drops future/scheduled disclosure dates). This is the PK
  component, so the table is queryable knowledge-date-safe by construction.

v1 derives one snapshot per **fiscal year** from yearly statements (the annual figure IS
the TTM at year end). Quarterly-rolling TTM is a v2 refinement. Ratios are NULL where an
operand is missing/zero.

## Schema fix forced by validation — migration 0028

Validating on real data caught a schema bug before populating: `NUMERIC(18,6)` caps below
10¹², but bank/large-cap raw line items exceed it (CBA total assets ≈ A$1.35e12). Migration
0028 widens the **absolute-dollar** columns (rs_financial_statements + rs_fundamentals_pit +
rs_factor_scores.market_cap_aud) to `NUMERIC(24,6)`; ratios/per-share stay `18,6`. A forced,
documented deviation from CLAUDE.md #5 (banks physically don't fit). `REQUIRED_MIGRATIONS` → 82.

## Validated end-to-end (2026-06-24, real EODHD data via Supabase MCP)

Populated the full chain for CBA/BHP/WTC/CSL/GMG using the **real** repo transforms +
`compute_pit_factors`. Result `rs_fundamentals_pit` (ranked by ROE):

| symbol | ROE | gross margin | franking | revenue | disclosure lag |
|---|---|---|---|---|---|
| BHP | 19.5% | 71.7% | 100% | $51.3B | 49d |
| CSL | 15.5% | 51.5% | 0% (offshore) | $15.4B | 49d |
| CBA | 12.8% | 41.1% | 100% | $69.7B | 43d |
| WTC | 11.8% | 86.2% (software) | 100% | $1.18B | 58d |
| GMG | 7.1% | 64.2% | 0% (trust) | $2.21B | 52d |

Factor profiles match the businesses; **disclosure lags 43–58d are all real reportDates —
no future-date leakage**; the franking spread (100% vs 0%) is captured; CBA's A$1.35e12 total
assets stored without overflow. The validation slice (5 names, latest year) is left in place;
full survivorship-free population is the cron's job.

## Acceptance criteria — met

Idempotent UPSERT on (symbol, knowledge_date) · reads only the research store, writes only
`rs_fundamentals_pit` · ratios NULL-safe · guarded knowledge_date · hard-fail if
`rs_financial_statements` is empty. **9 unit tests** (ratios, the guard in context, dividend
window, orchestrator).

## Cadence

Weekly Sat 17:10 UTC (Sun 03:10 AEST), after the statements + corporate-actions jobs.
Next in the sequence: `rs_factor_scores` — sector-neutral z-scores over these inputs (the
Layer-1 alpha signal). Only then does the value×quality **candidate** get tested.
