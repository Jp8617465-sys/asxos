# ASXOS Roadmap Research Pack — 2026-06-14

> **Status: PARKED / PLANNING — NOT approved for implementation.**
>
> This pack is strategy documentation. Creating it does **not** authorize any
> code change, migration, Render mutation, job run, or env-var change. Every
> item here is gated behind production-recovery verification and explicit
> per-item approval.

## What this is

A structured research and roadmap pack produced during ASXOS production
recovery. Its purpose is to let us continue strategic thinking **without**
strategy work becoming immediate scope creep. It captures the current platform
state, the recovery gates, roadmap tracks, trade-offs, scaling stress-tests,
quant/ML research direction, portfolio/risk/tax direction, automation ideas,
tech debt, the decision backlog, and pasteable future prompts.

## The one binding gate

The **scheduled production verification window** is the next hard gate. Until a
live cron window proves the minimal loop is running on the corrected
DATABASE_URL, the production loop is **NOT** considered recovered. Nothing in
this pack starts before that gate, and most items need explicit approval even
after it.

**The current minimal production loop (unproven post-recovery):**

```
prices → validate/freshness → snapshot → generate_signals → ingest_sentiment → compose_brief → backup
```

## Current recovery facts (as of 2026-06-14)

| Fact | State |
|---|---|
| Phase 2A (`dfd6fe5`), Phase 2B (`766dfb9`), backup fix (`2c3e50b`) | merged to `main`, all ancestors |
| `asxos-api` canary after DATABASE_URL correction | succeeded |
| 9/9 approved active crons rolled to DB fp `a07ca95a44` | done (11 services total at correct fp incl. api + backup) |
| Backup externally verified | `asxos-2026-06-13.sql.gz` → `Jp8617465-sys/asxos-backups` @ `1917b3e` |
| Signals last known frozen | 2026-05-20 (NOT proven current) |
| `asxos-retrain-model-a` | paused / quarantined (stale DB) |
| `asxos-track-signal-outcomes` | not live — quarantined by absence |
| `asxos-build-portfolio` | live but stale DB — excluded from rollout |
| Production loop recovered? | **UNKNOWN until verification** |

## Index

| File | Contents |
|---|---|
| [`01-current-state-and-recovery-gates.md`](01-current-state-and-recovery-gates.md) | Recovery state, what's fixed/proven/unproven, gates, GREEN/YELLOW/RED/UNKNOWN interpretation |
| [`02-roadmap-tracks.md`](02-roadmap-tracks.md) | Tracks A–I with objective / why / state / near-term / later / deps / risks / metric |
| [`03-architecture-tradeoffs.md`](03-architecture-tradeoffs.md) | Topology, env, observability, and automation trade-offs |
| [`04-quant-research-and-ml.md`](04-quant-research-and-ml.md) | Labels, IC, walk-forward, promotion/kill gates, ML lifecycle, leakage, drift |
| [`05-portfolio-risk-tax.md`](05-portfolio-risk-tax.md) | Decision ledger, position monitor, tax overlay, CGT, firewall, restart criteria |
| [`06-automation-and-review.md`](06-automation-and-review.md) | `ops_events`/`review_queue` design, severity, human-approval gates |
| [`07-scaling-scenarios.md`](07-scaling-scenarios.md) | 15 stress-tests: what breaks first, bottleneck, gaps, don't-build-yet |
| [`08-tech-debt-register.md`](08-tech-debt-register.md) | Identified debt with severity, evidence, timing, verification gating |
| [`09-decision-backlog.md`](09-decision-backlog.md) | Architecture decisions with owner, evidence, recommended default |
| [`10-future-prompts.md`](10-future-prompts.md) | 10 pasteable, scoped, constraint-bearing prompts |

## How to use this pack

1. Wait for the scheduled production verification. Use Prompt 1 in
   `10-future-prompts.md`.
2. Read the verdict against `01-current-state-and-recovery-gates.md`
   (GREEN / YELLOW / RED / UNKNOWN).
3. Pick the next batch from `02-roadmap-tracks.md` Lane A only.
4. Keep Lane B (strategic) parked until the loop is stable ≥5 trading days.

## Provenance

Grounded in read-only inspection of the repo (`origin/main` @ `2c3e50b`),
read-only Render API inspection, and SELECT-only DB queries performed during
the recovery sessions of 2026-06-13/14. No production mutations were made to
produce this pack. A `docs/strategy/backlog/2026-06-13-strategic-brain-dump.md`
was referenced by the task brief but **does not exist** in the repo; this pack
supersedes the need for it.

A pre-existing tech-debt registry exists at
[`docs/maintenance/guards-backlog.md`](../../../maintenance/guards-backlog.md)
(16 items, P0–P3). This pack extends and cross-references it; it does not
replace it.
