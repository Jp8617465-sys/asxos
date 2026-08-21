# Data contracts — the tables ASXOS depends on

**Status:** current · **Owner:** arbi maintains; the owning job owns the data
**Scope:** for each load-bearing table/view — purpose, required freshness, minimum rows,
owning job, downstream consumers, failure symptom, health query, recovery. This is what
`scripts/product_health.py` grades against, and what lets arbi say *"X is empty → this
blocks Y"* instead of assuming a table is populated.
**Last verified:** 2026-08-19 (live; `signals`/`signal_outcomes` rows updated for the Model A retirement)

A table silently going empty/stale is the #1 way this product breaks without any test
failing. These contracts turn that class of hidden failure into a graded scorecard row.

---

| Table | Purpose | Fresh ≤ | Min rows | Owner job | Consumers | Failure symptom | Recovery |
|---|---|---|---|---|---|---|---|
| `prices` | OHLCV, the valuation + feature base | 4d (weekend-tolerant) | 100k | `sync_prices` | signals, snapshots, vol, discipline crons, brief | stale marks; no signals | re-run `sync_prices --as-of` |
| `signals` | Model A output (model, prob_up, expected_return, …) — **frozen 2026-08-19**: no writer since Model A's retirement; kept as historical record only, no active owner job or consumer | — | 0 | none (retired) | none — every reader was removed alongside the writer | n/a — not a health metric; excluded from `scripts/product_health.py`'s FRESHNESS list | n/a; a future model's producer would need to be rebuilt from scratch, not "re-run" |
| `signal_outcomes` | realised fwd returns per signal — the archived decay-check + calibration base for Model A's 2026-07-11 resolved verdict | — | **>0** | none (retired; frozen at ~60,072 rows, backed up with checksums 2026-08-16) | evidence for any future model's pre-registered decay-bar evaluation | presence-only check in the scorecard (row count, not age) | n/a — never re-run; this table is the permanent record, not a live feed |
| `market_context` | regime + breadth + macro (avix, aud, rba, …) | 4d | 1 | `ingest_market_context` | market-context-narrator, regime, brief | narrator/regime data-thin; NULL rba/iron/vix | fix feed IDs (RC3), re-run |
| `portfolio_daily_snapshots` | daily MV/cash/benchmark, re-derivable | 4d (Sun–Thu) | 1 | `snapshot_portfolio` (gate: sync_prices ok) | benchmark analyst, performance view, brief | performance view blank; benchmark cols NULL | re-run; needs AXJO.INDX prices |
| `fundamentals` | per-symbol fundamentals, ML features | 8d | 1k | `sync_fundamentals` | loader/features, screening | features stale; signals degrade | re-run `sync_fundamentals` |
| `job_runs` | cron lifecycle (status/as_of/error) | — | grows | every job (JobMonitor) | this scorecard, `/arbi`, deadman | can't tell what ran | n/a (self-populating) |
| `theses` | per-symbol structured thesis (entry/stop/target/…) | — | ≥1 active | human/CLI + agents | discipline crons, pm-review, brief cards | no discipline coverage | `asx thesis open` |
| `holding_lots` / `current_holdings` | lot-level positions (CGT base, AUD) | — | James's real book | `asx holdings add` | tax, allocator, discipline, brief | portfolio not represented | James enters lots |
| `agent_runs` / `agent_evidence` | discovery-agent audit trail (governance) | — | grows | `asx agent-run log` | governance review, `/discover-macro` | proposals lost | n/a |
| `regulatory_events` | RBA RSS ingest only (Treasury retired 2026-07-18 — deterministic gov.au WAF 403, no code-level fix exists) | 4d | grows | `ingest_regulatory` | brief regulatory card, narrator | regulatory card thin if RBA itself is slow/down; fail-loud since 2026-07-18 (solo-source threshold=1.0 hard-fails instead of degrading silently) | re-run `ingest_regulatory`; check RBA's own feed health — Treasury is no longer a recovery path |

## How arbi uses these

- `scripts/product_health.py` reads each contract's health query → a PASS/WARN/FAIL row.
- When a contract fails, arbi states the **downstream blast radius** from the "Consumers"
  column: e.g. *"`signal_outcomes` frozen at 60,072 rows (checksummed 2026-08-16) → the
  permanent evidence base for Model A's resolved 2026-07-11 decay verdict; only relevant
  again if a future model needs the same pre-registered bar"* or *"`market_context.rba_cash_rate`
  NULL → the bank rate-cycle thesis has no macro trigger."*
- New load-bearing table → add a row here + a check in `product_health.py` in the same change.
