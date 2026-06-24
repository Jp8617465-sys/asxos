# `sync_financial_statements` — ingestion job scope (BUILT)

**Date:** 2026-06-24 · **Status:** BUILT (code + tests; not scheduled/populated). The
third research-store ingestion job and the **leak-critical** one. Populates
`rs_financial_statements` (raw BS/IS/CF, yearly + quarterly) for every symbol in
`rs_security_master` — the source from which point-in-time factors are later derived.

## The leak guard — `derive_knowledge_date()` (the centerpiece)

The point-in-time protection is **not** in this table — it stores `filing_date` and
`report_date` **raw** — but in a pure, tested function the downstream
`rs_fundamentals_pit` derivation MUST apply:

```
knowledge_date = max(d for d in (report_date, filing_date)
                     if d is not None and period_end < d <= as_of)
                 else period_end + LAG_DAYS
```

- `d <= as_of` drops scheduled/future disclosure dates → **no look-ahead** (removes the
  e.g. period 2026-06-30 / reportDate 2026-08-11 forecast row the 2026-06-24 probe found).
- `period_end < d` drops a field that defaulted to `period_end` (no real lag — BHP/CBA).
- fallback `period_end + LAG_DAYS` (≥75d annual / ≥60d quarterly) covers both-defaulted.

Implemented + tested **now** (6 dedicated tests incl. the exact future-date-drop case),
even though it is consumed by the next job, because the disclosure-date semantics live
here. In practice raw statement rows never carry a future `report_date` anyway — future
scheduled earnings have no statement to attach to — but the guard protects the derivation's
edge cases.

## What it ingests (structure verified on a real payload, 2026-06-24)

`Financials.{Income_Statement,Balance_Sheet,Cash_Flow}.{yearly,quarterly}[period]` → one
row per (symbol, period_end, period_type, statement_type). Each row:
- `filing_date` (raw), `report_date` (joined from `Earnings.History` by period end, raw),
- promoted scalar columns per statement type — income: `total_revenue`, `net_income`;
  balance sheet: `total_assets`, `total_equity`, `total_debt` (shortLongTermDebtTotal),
  `shares_diluted` (period-end shares, a documented proxy),
- the **full raw statement** in `line_items` JSONB,
- statements with `period_end > as_of` (unreported future) are skipped (safety net).

## Acceptance criteria — met

Idempotent UPSERT on the 4-part PK (rerun = no-op) · does **not** touch `universe`/`prices`
· per-symbol error tolerance · `report_date` COALESCEd (a later NULL never wipes a known
value) · hard-fail on empty `rs_security_master`. **19 unit tests pass** (incl. the leak guard).

## Validated on the live schema (2026-06-24, Supabase MCP)

Real HUBS 2025-12-31 rows across all 3 statement types upserted twice → **3 rows not 6**
(4-part-PK idempotency); promoted NUMERICs correct; **`line_items` JSONB queryable**
(`->>'freeCashFlow'`); `report_date` stored. Samples deleted — table back to empty.

## Cadence & open items

- **Schedule:** weekly Sat 16:50 UTC (Sun 02:50 AEST), after `sync_security_master`.
- **Call budget:** one `/fundamentals` call per symbol (heavy payload); within the EODHD
  100k/day budget. `--active-only` / `--limit` / `--symbols` bound smoke runs.
- **Deploy:** provision the Render service + `HEALTHCHECK_URL_SYNC_FINANCIAL_STATEMENTS`.

## What this is NOT

Not scheduled, not populated. Not the PIT factor table — it stores raw statements; the
leak-critical `knowledge_date` is applied when **`rs_fundamentals_pit`** is derived (the
next job), using `derive_knowledge_date()` from this module.
