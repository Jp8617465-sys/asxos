# Shelving the ML engine — how it plays out in the product

**Status:** current · **Decision:** James, 2026-07-11 — *"shelve the ML engine; PM Arbi, define
how this plays out."* **Definition + product direction:** arbi (this doc).
**Basis:** `docs/model-a-decay-analysis-2026-07-11.md` (v1_5 has no usable edge on 19,032
matured signals). **Owner:** James governs the decision; arbi owns the product shape it implies.

---

## The decision, in one line

**Model A is demoted from "the product's alpha engine" to a dormant, passive monitor.** ASXOS's
value is now, explicitly and solely, the **model-independent moat** — disciplined thesis
investing, tax intelligence, theme stewardship, and multi-instrument (ETF) support. No ML
signal drives any capital decision. This is not a temporary state pending a fix; it is the
product's shape until a *new* model earns its way back (conditions below).

## What "shelve" means here (precise — not "delete", not "keep iterating")

| Component | Before | After (shelved) |
|---|---|---|
| **`retrain_model_a`** (weekly walk-forward) | iterating v1_5 | **stays SUSPENDED** (already suspended on Render since ~June). v1_5 is not iterated further. |
| **`generate_signals`** (daily inference) | product signal source | **kept running as a passive signal-quality MONITOR only** — feeds `signal_outcomes` so any future model (or v1_5 drift) is always measurable at ~zero cost. NOT product-critical; nothing acts on it. |
| **`track_signal_outcomes`** | (broken — `signal_outcomes` stale past 2026-03-25) | **FIX COMMITTED** (branch `claude/wake-up-arbi-jeww8p` / PR #26), **pending merge + Render deploy — NOT live in prod yet.** Root cause: the Phase 2B init-pool ordering bug (`init_pool()` inside the `JobMonitor` block → silent crash in `__aenter__`, no `job_runs` row written, `signal_outcomes` frozen from 2026-04-15); the fix restores the canonical init_pool-before-JobMonitor structure and lifts the test quarantine. The weekly cron (Sun 03:00 UTC) only resumes writing **post-deploy** — and even then the ~2026-03-26..04-11 signal window has aged past the job's 90-day lookback and never backfills. Once live this is what makes the monitor lane real and turns the decay check into a one-query standing check. |
| **Signal-driven allocator** (`build.py`) | gated on `approved_for_allocation` | **stays DORMANT.** `approved_for_allocation` stays 0; rule #11's gate (0 approved → allocator refuses) is now permanent policy, not a temporary block. Allocation is conviction/rules/discipline-driven, not signal-driven. |
| **Daily brief** | had a Model A driver line | **fully model-independent** already (R9 made the model reads best-effort; with the shelf they're permanently omitted). Thesis/tax/discipline/regulatory cards are the brief. |
| **`compute_opportunity_cost`** (signal ranking) | peripheral Model A read | dormant / label non-authoritative (cleanup R4). |

**Why keep `generate_signals` running instead of killing it:** it is cheap, its output is
already non-actionable (rule #11 standing), and keeping it feeding `signal_outcomes` preserves
the ability to answer *"does any model have edge?"* for free — which is exactly what let us
resolve the P0 today. Suspending it would also risk stale-signal hard-fails in downstream crons
(`PortfolioService.build()` raises on >2-day-old signals). So the shelf **demotes** the engine
rather than ripping it out — dormant on the critical path, alive as a monitor, iterated by no one.

## What the product IS now (the model-independent product)

The north-star's three-layer moat — none of which needs Model A:

1. **Discipline scaffolding (the wedge):** every position a structured thesis (entry/stop/
   target/timeline/invalidation), with discipline events (stop breach, revisit-due, target hit)
   surfaced *before* they cost money. This works today (the HUBS stop breach fired 2026-07-03).
2. **Tax intelligence:** CGT (calendar 12-month rule), Div 296, franking — spec-governed,
   Decimal-exact, instrument-agnostic.
3. **Theme stewardship + multi-instrument:** themes → holdings mapping; and now ETFs/LICs as
   first-class held/valued/taxed instruments (`security_kind`, Phase 1 Slice 1 shipped).

The "signal" the product runs on is **James's own conviction + the discipline/tax/analysis
layer + the evidence agents (`/pm-review`)** — not an ML probability. That is the product that
was always authoritative; the shelf just makes it the *whole* product, not a placeholder while
ML matured.

## Phase 2c — reframed (this is how the shelf unblocks it)

Phase 2c was "blocked on a trusted signal engine." There is no trusted signal engine and we are
not waiting for one. **Phase 2c is redefined as the model-independent discovery + discipline
expansion:** the macro-economist / theme-researcher / instrument-selector agents (which propose
*content for human review*, never signals), deeper thesis discipline, and the ETF/multi-
instrument build — all of which sit outside the ML engine and outside rule #11. The blocker is
removed by *descoping the ML dependency*, not by fixing Model A.

## The revival condition (so "shelved" ≠ "forbidden forever")

Model A can return to the product only via a **new model version** that, before it may ever
influence capital:

1. passes a **pre-registered decay bar** on matured `signal_outcomes` — at minimum a
   **positive, monotonic** conviction→21d-return relationship and `corr(ml_prob, 21d) ≳ 0.05`
   (v1_5 scored −0.03 and inverted — the bar is what it failed); AND
2. earns `approved_for_allocation` via an explicit, separate human action.

**v1_5 itself never revives** — it is the version this analysis retired. The monitor lane keeps
the door measurable, not open.

## Unchanged (load-bearing invariants the shelf does not touch)

The s766B personal-advice firewall; single-user (no auth/RLS/user_id); Decimal-only domain
arithmetic + NUMERIC(18,6); rule #11 (now *standing*, not temporary); the discipline/tax product.

## Next actions this implies (arbi drives; capital/merge stay James's)

1. **`track_signal_outcomes` — FIX COMMITTED, pending merge + Render deploy** (branch
   `claude/wake-up-arbi-jeww8p` / PR #26). The init-pool ordering fix is on the branch, not yet
   in prod; the monitor lane goes live only once PR #26 merges and the weekly cron
   (Sun 03:00 UTC) next fires post-deploy. `signal_outcomes` stays frozen (last populated
   2026-04-15) until then, and the ~2026-03-26..04-11 gap has aged past the 90-day lookback and
   will not backfill.
2. **ETF Slice 2** (ingest VGS/VAS + passive mandates) — the model-independent product's next build.
3. **Fix the broken monitoring crons** the health scorecard surfaced (`check_cron_health`,
   `check_model_staleness`).
4. Retire/relabel the stale "V2 needs a trusted signal engine" framing in `docs/strategy/*`.
