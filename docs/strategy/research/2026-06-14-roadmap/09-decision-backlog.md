# 09 — Architecture Decision Backlog

> **Status: open decisions. Nothing is decided here.** Each row carries a
> *recommended default* (the conservative, least-change-during-recovery option)
> and the *risk of deciding too early*. Owner is "James" for anything
> product/architecture/governance; "Claude+James" where Claude can prepare
> evidence but James approves.

Format: decision · owner · why it matters · evidence needed · when to decide ·
options · recommended default · risk of deciding too early.

---

## D-01 — Many Render crons vs master daily orchestrator
- **Owner:** James · **When:** after loop stable ≥1 month.
- **Why:** the fan-out is the dominant drift surface (24/13/11).
- **Evidence needed:** 1 month of `job_runs`; per-job memory headroom; counted
  drift incidents.
- **Options:** (a) keep crons + enforce check-drift; (b) master orchestrator;
  (c) hybrid (orchestrated loop + independent backup/weekly).
- **Recommended default:** **(a)** — the drift is a *process* problem, not an
  architecture problem.
- **Early-decision risk:** an orchestrator becomes a new single point of failure
  before the loop is even green.

## D-02 — Render cron vs DB queue worker
- **Owner:** James · **When:** at > ~2,000 symbols or when prioritization/
  backpressure is needed.
- **Why:** crons are time-triggered with no backpressure.
- **Evidence needed:** EODHD quota-exhaustion incidents; ingest durations vs the
  cron window.
- **Options:** (a) cron only; (b) DB queue worker; (c) both.
- **Recommended default:** **(a) cron now.**
- **Early-decision risk:** an always-on worker is a new failure surface answering
  a problem ASXOS doesn't have yet.

## D-03 — Env-group migration timing
- **Owner:** James · **When:** loop stable + a planned credential rotation
  upcoming.
- **Why:** the incident was partial credential propagation across service-level
  copies.
- **Evidence needed:** documented/tested Render group-link behaviour (the
  `fromService`-applies-at-creation footgun, guards P3-1).
- **Options:** (a) keep service-level; (b) migrate to a shared env group now;
  (c) migrate later.
- **Recommended default:** **(c) migrate later** (target state, deferred).
- **Early-decision risk:** a bad group value breaks every linked service at once;
  migrating during recovery adds churn to an unproven loop.

## D-04 — Missing Phase 2B service creation
- **Owner:** James · **When:** monitoring tier after G1; the rest after G3.
- **Why:** 11 declared services don't run; the monitoring tier is among them.
- **Evidence needed:** loop green; for each service, its upstream dependency
  satisfied.
- **Options:** (a) create all; (b) monitoring-first; (c) none.
- **Recommended default:** **(b) monitoring-first** (with `_EXPECTED_DAILY`
  trimmed to live jobs to avoid false MISSING).
- **Early-decision risk:** creating dependent services before their inputs are
  stable produces noise and false alarms.

## D-05 — Backup `job_runs` logging
- **Owner:** Claude+James · **When:** Lane A batch 2.
- **Why:** backup is invisible to `check_cron_health`.
- **Evidence needed:** none — clear gap.
- **Options:** (a) wrap shell in `JobMonitor`; (b) lightweight post-run SQL
  insert; (c) parse the healthcheck.
- **Recommended default:** **(b) lightweight insert** — keep the shell script,
  add one row.
- **Early-decision risk:** over-engineering a working DR script.

## D-06 — Custom connector vs Render MCP / Supabase MCP
- **Owner:** James · **When:** Track G.
- **Why:** recovery used read-only REST + Supabase MCP effectively.
- **Evidence needed:** recurring operations worth wrapping; MCP coverage gaps.
- **Options:** (a) MCP where available; (b) custom connector; (c) raw REST as
  today.
- **Recommended default:** **(a) MCP where available**, raw REST otherwise.
- **Early-decision risk:** building a connector before the need is proven.

## D-07 — Event-driven review queue
- **Owner:** James · **When:** Lane B design phase.
- **Why:** scales operator attention without autonomy.
- **Evidence needed:** the set of recurring incident types worth queueing.
- **Options:** (a) build; (b) design-only now; (c) skip.
- **Recommended default:** **(b) design-only** (see `06-automation-and-review.md`).
- **Early-decision risk:** automation before governance reintroduces silent
  mutation.

## D-08 — Strategy backlog storage location
- **Owner:** Claude · **When:** now (cheap).
- **Why:** keep strategy out of code paths; avoid scope creep.
- **Evidence needed:** none.
- **Options:** (a) `docs/strategy/research/` (this pack); (b) GitHub issues;
  (c) a single backlog file.
- **Recommended default:** **(a) `docs/strategy/research/`** — note the
  task-referenced `docs/strategy/backlog/2026-06-13-strategic-brain-dump.md`
  **does not exist**; this pack is the home.
- **Early-decision risk:** none material.

## D-09 — Paper book / decision ledger
- **Owner:** James · **When:** Track E (Lane B).
- **Why:** the bridge from backtest to trust; auditability is the product.
- **Evidence needed:** loop green; shadow-book scaffolding exercised.
- **Options:** (a) extend `decisions`; (b) new tables; (c) provenance view first.
- **Recommended default:** **(c) provenance view first** (guards P3-3), then
  decide schema.
- **Early-decision risk:** schema churn before the workflow is understood.

## D-10 — V2 / parallel engine: adopt vs quarantine
- **Owner:** James · **When:** Lane B, after loop + research maturity.
- **Why:** two brief engines coexist (V1 active, V2 dark); reshape touches every
  section.
- **Evidence needed:** loop stable; brief reshape scoped; symbol-suffix and
  section-collector blockers resolved (per V2 audit).
- **Options:** (a) adopt V2; (b) keep dark; (c) retire V2.
- **Recommended default:** **(b) keep dark** until the loop and research are
  mature.
- **Early-decision risk:** a mid-recovery reshape that touches every brief
  section is exactly the parallel-improvement-storm the postmortem warns against.

## D-11 — ML retraining policy
- **Owner:** James · **When:** Track D (Lane B).
- **Why:** `retrain_model_a` paused on OOM/M12 risk.
- **Evidence needed:** retrain memory budget for Render; drift baseline.
- **Options:** (a) weekly; (b) drift-triggered; (c) manual.
- **Recommended default:** **(c) manual** until memory + drift are solved.
- **Early-decision risk:** OOM during recovery; retraining without a drift
  baseline.

## D-12 — Signal promotion gates
- **Owner:** James · **When:** Track C (Lane B).
- **Why:** no live realised-IC feedback today.
- **Evidence needed:** `track_signal_outcomes` deployed; IC/quintile/turnover on
  PIT, survivorship-free, net-of-cost data.
- **Options:** (a) IC/quintile gates; (b) paper P&L gates; (c) both + written
  kill criteria.
- **Recommended default:** **(c) both, pre-registered.**
- **Early-decision risk:** promoting on noise / overfit metrics.

## D-13 — `build_portfolio` restart criteria
- **Owner:** James · **When:** after loop green.
- **Why:** building on stale signals proposes trades against yesterday.
- **Evidence needed:** G1 + G2 (signals fresh).
- **Options:** (a) restart immediately on green; (b) after 5 green days + DB roll.
- **Recommended default:** **(b)** (see `05-portfolio-risk-tax.md` §11).
- **Early-decision risk:** trades proposed on unproven/stale inputs.

## D-14 — `track_signal_outcomes` replacement vs retirement
- **Owner:** James · **When:** Track C (Lane B).
- **Why:** absent; it is the feedback loop.
- **Evidence needed:** whether the existing job's labels/horizons match the
  research design.
- **Options:** (a) deploy as-is + verify; (b) redesign; (c) retire.
- **Recommended default:** **(a) deploy + verify**, redesign later if needed.
- **Early-decision risk:** discarding a working feedback loop, or deploying one
  whose labels silently mismatch the research definition.

## D-15 — `asxos-build-portfolio` DATABASE_URL update timing
- **Owner:** Claude+James · **When:** Lane A batch 1 (gated on loop green).
- **Why:** stale fp `fca87bb5cc`; downstream writer.
- **Evidence needed:** core loop green.
- **Options:** (a) roll now; (b) roll after loop green.
- **Recommended default:** **(b)** — don't activate a downstream writer on an
  unproven loop.
- **Early-decision risk:** enabling portfolio builds before signals are proven.

## D-16 — `cleanup-conversations` quarantine / delete
- **Owner:** James (operator-only) · **When:** Lane A batch 3.
- **Why:** ungoverned legacy cron writing daily to the prod Supabase project.
- **Evidence needed:** confirm nothing current depends on it; confirm its target
  tables remain empty/legacy.
- **Options:** (a) suspend; (b) delete; (c) leave.
- **Recommended default:** **(a) suspend** after confirming no shared dependency.
- **Early-decision risk:** deleting something still load-bearing for legacy data
  recovery.

## D-17 — `ingest_regulatory` repair priority
- **Owner:** Claude+James · **When:** Lane A early (investigate now).
- **Why:** chronic daily failure (ATO + Treasury feeds dead).
- **Evidence needed:** current live feed URLs; whether sources moved/retired.
- **Options:** (a) fix/replace feed URLs; (b) lower the 0.5 threshold;
  (c) drop the dead sources.
- **Recommended default:** **(a) fix/replace feed URLs.**
- **Early-decision risk:** lowering the threshold masks real staleness (a silent
  failure — exactly what the postmortem forbids).

## D-18 — Render native runtime vs Docker (esp. backup, ML)
- **Owner:** James · **When:** if a native-image dependency failure recurs, or ML
  retraining moves to Render.
- **Why:** the backup cron broke on a missing system dep (`apt-get` removed in
  `2c3e50b`; native `pg_dump` now relied upon).
- **Evidence needed:** a reproducible native-image dependency failure for a
  specific job.
- **Options:** (a) native runtime; (b) Docker per service.
- **Recommended default:** **(a) native** (the backup fix aligned to native);
  Docker only if ML libs force it.
- **Early-decision risk:** adopting image build/registry overhead before any job
  needs it.

---

## Decisions safe to make now vs gated

| Safe now | Gated on verification |
|---|---|
| D-08 (storage location) | D-04, D-13, D-15 (service creation / build_portfolio) |
| D-17 (investigate regulatory — read-only) | D-16 (orphan disposition — operator) |
| Documenting D-05 design | D-01, D-02, D-03 enactment |
| Recommended defaults above (as *positions*, not actions) | everything that mutates Render/DB/code |
