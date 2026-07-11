# Data contracts — the tables ASXOS depends on

**Status:** current · **Owner:** arbi maintains; the owning job owns the data
**Scope:** for each load-bearing table/view — purpose, required freshness, minimum rows,
owning job, downstream consumers, failure symptom, health query, recovery. This is what
`scripts/product_health.py` grades against, and what lets arbi say *"X is empty → this
blocks Y"* instead of assuming a table is populated.
**Last verified:** 2026-07-11 (live)

A table silently going empty/stale is the #1 way this product breaks without any test
failing. These contracts turn that class of hidden failure into a graded scorecard row.

---

| Table | Purpose | Fresh ≤ | Min rows | Owner job | Consumers | Failure symptom | Recovery |
|---|---|---|---|---|---|---|---|
| `prices` | OHLCV, the valuation + feature base | 4d (weekend-tolerant) | 100k | `sync_prices` | signals, snapshots, vol, discipline crons, brief | stale marks; no signals | re-run `sync_prices --as-of` |
| `signals` | Model A output (model, prob_up, expected_return, …) | 4d | 1k | `generate_signals` (gate: sync_prices ok) | allocator, brief driver, pm-review | brief §Model-A line skipped (R9); allocator hard-fails | re-run `generate_signals` |
| `signal_outcomes` | realised fwd returns per signal — **the decay-check + calibration base** | rolling | **>0** | `track_signal_outcomes` (scheduled Sun 03:00 UTC; init-pool crash fix committed on PR #26, pending merge + deploy) | Model A decay/calibration | decay must be recomputed from prices (slow, what happened 2026-07-10) | run the outcomes job |
| `market_context` | regime + breadth + macro (avix, aud, rba, …) | 4d | 1 | `ingest_market_context` | market-context-narrator, regime, brief | narrator/regime data-thin; NULL rba/iron/vix | fix feed IDs (RC3), re-run |
| `portfolio_daily_snapshots` | daily MV/cash/benchmark, re-derivable | 4d (Sun–Thu) | 1 | `snapshot_portfolio` (gate: sync_prices ok) | benchmark analyst, performance view, brief | performance view blank; benchmark cols NULL | re-run; needs AXJO.INDX prices |
| `fundamentals` | per-symbol fundamentals, ML features | 8d | 1k | `sync_fundamentals` | loader/features, screening | features stale; signals degrade | re-run `sync_fundamentals` |
| `job_runs` | cron lifecycle (status/as_of/error) | — | grows | every job (JobMonitor) | this scorecard, `/arbi`, deadman | can't tell what ran | n/a (self-populating) |
| `theses` | per-symbol structured thesis (entry/stop/target/…) | — | ≥1 active | human/CLI + agents | discipline crons, pm-review, brief cards | no discipline coverage | `asx thesis open` |
| `holding_lots` / `current_holdings` | lot-level positions (CGT base, AUD) | — | James's real book | `asx holdings add` | tax, allocator, discipline, brief | portfolio not represented | James enters lots |
| `agent_runs` / `agent_evidence` | discovery-agent audit trail (governance) | — | grows | `asx agent-run log` | governance review, `/discover-macro` | proposals lost | n/a |
| `regulatory_events` | RBA/Treasury RSS ingest | 4d | grows | `ingest_regulatory` (flaky — 9/43) | brief regulatory card, narrator | regulatory card empty (only 2 rows live) | fix RSS feed reliability |

## How arbi uses these

- `scripts/product_health.py` reads each contract's health query → a PASS/WARN/FAIL row.
- When a contract fails, arbi states the **downstream blast radius** from the "Consumers"
  column: e.g. *"`signal_outcomes` populated (24,454) → the decay automation the 2026-07-10
  check had to fake from prices is now runnable"* or *"`market_context.rba_cash_rate` NULL →
  the bank rate-cycle thesis has no macro trigger."*
- New load-bearing table → add a row here + a check in `product_health.py` in the same change.
