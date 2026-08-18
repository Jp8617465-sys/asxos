# `sync_corporate_actions` — ingestion job scope (BUILT)

**Date:** 2026-06-24 · **Status:** BUILT (code + tests; not yet scheduled/populated).
The second research-store ingestion job. Populates `rs_corporate_actions` (dividends +
splits) for every symbol in `rs_security_master`. Source semantics were fully settled by
the read-only probes — there were no open availability questions left to gate it.

## What it does

- Iterates `rs_security_master` (survivorship-free: active + delisted by default; the job
  hard-fails if that table is empty — run `sync_security_master` first).
- Per symbol: `/div` (dividends + AU franking) and `/splits`, transformed to rows and
  UPSERTed into `rs_corporate_actions` on PK `(symbol, ex_date, action_type)`.
- Bounded-concurrency fetch (the EODHD client semaphore is the hard cap), serial DB
  writes through one connection, per-symbol errors tolerated (counted, never abort).

## Field semantics (probe 2026-06-24 — see `probes/2026-06-24-eodhd-gate-closure.md`)

| Column | Source | Rule |
|---|---|---|
| `ex_date` | `/div`/`/splits` `date` | PK component; rows without it are skipped |
| `dividend_amount` | `/div` `unadjustedValue` › `value` | as-paid cash/share (PIT-correct), Decimal |
| `franking_pct` | `/div` `franking` `"<float>%"` | `Decimal(strip "%")`, range-guarded 0–100; **NULL ≠ 0** (0% = unfranked, NULL = undeclared); absent on US names |
| `split_ratio` | `/splits` `split` `"new/old"` | `Decimal(new)/Decimal(old)`; NULL on malformed/zero-divisor |
| `pay_date` / `record_date` | `paymentDate` / `recordDate` | nullable |

`franking_pct` is COALESCEd in the UPSERT so a later NULL never wipes a known value.

## Acceptance criteria — met

Active **and** delisted coverage · idempotent UPSERT on the composite PK (rerun = no-op) ·
does **not** touch `universe`/`prices` · per-symbol error tolerance · franking 0-vs-NULL
preserved · splits parsed · hard-fail on empty `rs_security_master`. **27 unit tests pass.**

## Validated on the live schema (2026-06-24, via Supabase MCP)

Real-shaped rows (CBA div franking=100, GMG div franking=0, AAPL div franking=NULL, AAPL
4:1 split) upserted twice → **4 rows not 8** (composite-PK idempotency); franking
`100 / 0 / NULL` all distinct; `split_ratio` stored `4.000000`; AAPL.US present as both a
dividend and a split row. Samples then deleted — table back to empty.

## Cadence & open items

- **Schedule:** weekly Sat 16:30 UTC (Sun 02:30 AEST), 20 min after `sync_security_master`.
- **Call budget:** full master ≈ 4,300 symbols × 2 calls; within the EODHD 100k/day budget;
  most names return `[]`. `--active-only` / `--limit` / `--symbols` flags bound smoke runs.
- **Deploy:** provision the Render service + `HEALTHCHECK_URL_SYNC_CORPORATE_ACTIONS` UUID;
  `make check-drift` shows the new cron until then.
- **Population:** runs on first cron (or trigger manually). Tables remain empty until then.

## What this is NOT

Not scheduled, not populated. Not a total-return engine — it stores the raw actions; any
adjustment/total-return derivation is a later, separate transform. `sync_financial_statements`
(the guarded `knowledge_date` rule) is the next job in the sequence.
