# 07 — Scaling Scenarios

> **Status: stress-test analysis. Speculative.** None of this is work to start.
> The point is to know *where* ASXOS breaks so we do not scale into a wall.

Common context that shapes every scenario:
- Render free/Starter tier ≈ 512MB per worker. `generate_signals` already
  batches 300 symbols to stay ~100MB/batch; the predecessor hit OOM on feature
  computation (postmortem).
- EODHD is the sole price source; free-tier quota/rate is the external ceiling.
- ~22 jobs as individual crons → drift is the dominant operational failure.
- The cron-liveness monitor is **not deployed** — most "observability gap"
  entries below trace back to this.

| # | Scenario | What breaks first | Likely bottleneck | Observability gap | Governance gap | Redesign before scaling | Don't build yet |
|---|---|---|---|---|---|---|---|
| 1 | ASX only, daily bars | Nothing structural — loop just unproven | `generate_signals` memory | cron-liveness monitor absent | — | deploy monitoring tier | new signals |
| 2 | ASX + US equities | Symbol-suffix join contract (`.AU`/`.US`) + session timing | `universe` suffix normalisation; dual sessions in `sync_prices` | per-market freshness | per-market trading-day calendar | symbol normalisation + dual schedules | US execution |
| 3 | 2,000 symbols | EODHD quota/rate; feature memory | `sync_fundamentals` (per-symbol), `generate_signals` (300-batch) | per-symbol success ratio (no aggregate threshold live) | partial-success thresholds (guards P0-1) | land P0-1; tune batch | real-time prices |
| 4 | 10,000 symbols | OOM + cron wall-clock | FeatureEngine, `prices` write volume | memory/duration telemetry | backpressure policy | off free tier / chunked workers / columnar store | master orchestrator prematurely |
| 5 | fundamentals + news + events | Ingest fan-out fragility | 4 resilient-gather jobs (no aggregate threshold deployed) | aggregate success ratio | P0-1 threshold (designed, unbuilt) | land P0-1; boundary Pydantic models (guards P2-2) | event-driven engine |
| 6 | one signal | Fine | — | realised IC (`track_signal_outcomes` absent) | promotion gate | deploy outcome tracking | ensemble |
| 7 | ten signals | Storage + attribution explosion | `signals` schema (model/version PK), brief surface | per-signal IC/turnover | promotion/kill registry | research harness (Track C) | auto-promotion |
| 8 | ML ensemble | Retrain memory; cache TTL | `retrain_model_a` (OOM), `models/` artefacts | drift/calibration metrics | model retirement policy | memory budget + drift monitor | live ensemble before single-model gates |
| 9 | paper portfolio | Decision/outcome reconciliation | `paper_trade.py`, `decisions` | P&L attribution | override log | decision-ledger provenance (guards P3-3) | live trading |
| 10 | tax-aware live decision ledger | CGT boundary correctness at volume | `tax_overlay`, `holding_lots` | per-lot audit trail | wash-sale / Part IVA disclaimers (info-only) | provenance view; ledger schema | auto-execution |
| 11 | 12 months daily operation | Table growth + cron drift creep | `prices` (~644k → millions), `job_runs` retention | long-horizon dashboard | retention/archival policy | partitioning/retention | — |
| 12 | multiple portfolios | Single-active-profile invariant | `profiles` (exactly-one-active), portfolio build | per-portfolio health | profile isolation **without** user_id/RLS | profile model redesign (no auth) | multi-tenant anything |
| 13 | broader event ingestion | RSS fragility (already failing) | `ingest_regulatory`, `asx_announcements` | per-feed health | source SLA policy | feed abstraction + thresholds | NLP pipeline at scale |
| 14 | automatic review generation | No event substrate | `ops_events`/`review_queue` (absent) | review lineage | human-approval gate | Track F design first | autonomous mutation |
| 15 | master orchestrator | New single point of failure | orchestrator + `job_runs` semantics | orchestrator-level telemetry | restart/idempotency contract | topology decision (Track G) | until loop stable ≥1 month |

## Cross-cutting first-breakers (the real ceilings)

1. **Memory** on Render's 512MB tier — already hit historically; the binding
   constraint for symbol-count and ML scaling.
2. **EODHD free-tier quota** — the external ceiling beyond ~2,000 symbols.
3. **Cron fan-out drift** — more services = more drift; the operational ceiling.
4. **Absent monitoring** — masks all of the above until something is visibly
   broken. **This is why the monitoring tier is the first thing to deploy.**

## Reading guide

- Scenarios 1–5 are *infrastructure* scaling — bounded by memory, quota, and
  drift. Solvable with tier upgrades, batching, and the monitoring/threshold
  work already designed (guards-backlog P0-1, P2-2).
- Scenarios 6–10 are *research/portfolio* scaling — bounded by the absence of a
  live feedback loop and promotion governance (Tracks C/D/E).
- Scenarios 11–15 are *platform* scaling — bounded by topology and governance
  decisions (Tracks F/G), none of which should be made until the loop is stable.

**The honest summary:** ASXOS at scenario 1 is not yet proven. Every scenario
beyond it is premature until the minimal loop runs green for a sustained period
and the monitoring tier exists to prove it.
