# 05 — Price Completeness & Data Durability Plan

*Category-1 facts + Category-5 recommendation.*

## Current state (proven)
- Latest complete price date: **2026-06-15** (1849 rows) — advanced from the stuck 2026-06-10.
- **Missing trading days: 2026-06-04, 06-05, 06-11, 06-12** (two Thursday/Friday gaps). 06-08 absent = legitimate King's Birthday ASX holiday.
- `latest_complete_trading_day` is computed **dynamically** each run (`cf5d974`); `sync_prices` **logs** a completeness verdict (`fe406d8`) but does **not persist** it to the DB.
- The recency gate (`a719b3c`) safely handles staleness (blocks rather than regenerating stale signals) — so the gaps are a **completeness** problem, not a correctness/stability one.

## What the 06-04/05 and 06-11/12 gaps mean
- Two clean **Thu/Fri pairs** missing suggests a *systematic* cause (a provider/backfill failure on specific days during/after the recovery), not random loss. Root cause is **UNKNOWN** and worth a read-only diagnostic.
- Impact: the 450-day feature lookback has internal holes. The model still produced 1703 signals on 2026-06-15 (features tolerate gaps), so impact is **degraded feature quality, not failure**. Compounds with the adj_close issue (`04`).

## Recommendation: durable `price_coverage` metadata (design, not yet implement)
A small table written by `sync_prices`, capturing per-date completeness as **history** rather than recomputing it:
- `price_coverage(dt PK, au_equity_rows INT, status TEXT /* complete|partial|no_equity_data */, classified_at TIMESTAMPTZ)`.
- Populated from the existing `classify_sync_completeness` verdict (already computed, just not stored).
- A **gap detector**: flag expected trading days (weekday, non-holiday) with no `complete` row — would have surfaced 06-04/05/11/12 automatically.
- `latest_complete_trading_day` can then read this table (auditable) instead of recomputing.

This is **design-only** here; implementation is a migration + `sync_prices` change (gated; needs approval).

## Sequencing vs P0 signal correctness
**P0 signal correctness (`04`) outranks `price_coverage` metadata.** Rationale:
- The recency gate already makes stale/partial data *safe* (it blocks). So missing-day metadata is an **observability/durability** improvement, not a safety fix.
- The P0 risks are **confirmed correctness defects** that make the *labels the user sees* mis-specified — higher harm.
- `price_coverage` design is **read-only and can run in parallel** with P0 work; its *implementation* should follow the P0 fix.

**Verdict:** run the `price_coverage` **design** prompt in parallel (read-only); do **not** implement it before the P0 fix. Also run a read-only **gap root-cause diagnostic** (why are Thu/Fri 06-04/05/11/12 missing?) — cheap and parallel.
