# 10 — Future Pasteable Prompts

> **Status: ready-to-paste prompts for future sessions.** Each is scoped,
> carries hard constraints, lists tasks, names a deliverable, and has a stop
> condition. They are *convenience scaffolding*, not authorizations — a human
> still approves any mutation.
>
> Shared constraint block (referenced as **[SAFE-RO]** below):
> *Do not edit files/code/render.yaml/migrations/CLAUDE.md. Do not commit. Do
> not write to the DB. Do not run migrations. Do not trigger jobs/Render/blueprint
> sync. Do not modify Render services or env vars. Do not create/delete/enable/
> disable/pause services. Do not send emails. Do not expose or print secret
> values. Do not run generate_signals / ingest_sentiment / compose_brief /
> retrain_model_a / track_signal_outcomes. Do not touch V2 / parallel engine /
> thresholds / tax logic / migration recovery / env groups / signal architecture.
> Read-only repo + read-only Render API + SELECT-only DB allowed.*

---

## Prompt 1 — Scheduled production verification
- **Scope:** confirm whether the minimal loop is actually recovered.
- **Hard constraints:** [SAFE-RO].
- **Tasks:** (1) source identity check (repo/remote/branch/origin-main HEAD/clean
  tree; confirm `dfd6fe5`,`766dfb9`,`2c3e50b` ancestors). (2) SELECT `job_runs`
  status+error for `as_of >= CURRENT_DATE-2` for sync_prices, snapshot_portfolio,
  generate_signals, ingest_news, ingest_sentiment, ingest_regulatory,
  compose_brief. (3) signal freshness `MAX(signals.as_of)` vs `CURRENT_DATE`.
  (4) price freshness `MAX(prices.dt)`. (5) note backup writes no `job_runs` row.
  (6) verdict GREEN/YELLOW/RED/UNKNOWN for the CORE loop separately from
  peripherals, per `01-current-state-and-recovery-gates.md`.
- **Deliverable:** a verification report with the verdict and, if GREEN, the
  unblocked Lane A batch-1 items listed for approval.
- **Stop:** after the report. Make no changes.

## Prompt 2 — If active loop is GREEN, next cleanup batch
- **Scope:** plan Lane A batch 1 (no execution).
- **Hard constraints:** [SAFE-RO], plus: single-key env PUT only if/when later
  approved (never bulk replace).
- **Tasks:** produce an ordered, approval-gated plan for (1) `build_portfolio`
  DATABASE_URL roll; (2) deploy `check_cron_health` with `_EXPECTED_DAILY`
  trimmed to live jobs (avoid false MISSING); (3) backup `job_runs`
  observability design; (4) `ingest_sentiment` root-cause then healthcheck var;
  (5) Render drift reconcile decision. For each: exact change, rollback,
  verification SQL/probe, risk.
- **Deliverable:** the batch-1 plan, per-item approval-gated.
- **Stop:** after the plan. Execute nothing.

## Prompt 3 — If generate_signals fails, targeted diagnostic
- **Scope:** root-cause a `generate_signals` failure.
- **Hard constraints:** [SAFE-RO]. Do not run generate_signals.
- **Tasks:** read-only inspect `jobs/generate_signals.py` + `asxos/domain/signals/*`;
  SELECT `job_runs` (error_message), `signals` (MAX as_of), `prices` (MAX dt);
  check the `_upstream_ok` gate (sync_prices success within 5 days), the `as_of`
  date-cast fix (`c5f920b`/`dfd6fe5`), and the 300-symbol feature-batch memory
  ceiling.
- **Deliverable:** exact failing stage, root cause, minimal fix proposal (not
  implemented), and whether it is upstream (sync_prices) vs internal.
- **Stop:** after the diagnostic report.

## Prompt 4 — Render drift cleanup planning
- **Scope:** plan reconciliation of declared vs live vs orphan services.
- **Hard constraints:** [SAFE-RO]. Read-only Render API only.
- **Tasks:** (a) per declared-but-absent service: create-vs-defer recommendation
  + dependency order; (b) per legacy orphan: keep/suspend/delete recommendation
  (operator-only flagged), noting `cleanup-conversations` writes to the prod
  Supabase project and `realflow-api` is unrelated; (c) the safe creation
  sequence for the monitoring tier that avoids false-MISSING storms.
- **Deliverable:** a drift-cleanup plan.
- **Stop:** after the plan. Mutate nothing.

## Prompt 5 — Master orchestrator vs multiple crons strategy review
- **Scope:** Track G topology decision memo.
- **Hard constraints:** [SAFE-RO]. Read-only repo.
- **Tasks:** compare (a) keep crons + enforce check-drift, (b) master daily
  orchestrator, (c) hybrid. For each: failure modes, observability,
  idempotency/restart contract, migration cost, the trigger condition that makes
  it necessary. Use `03-architecture-tradeoffs.md` TO-1/TO-2/TO-3 as the base.
- **Deliverable:** a recommendation + revisit trigger.
- **Stop:** after the memo. Implement nothing.

## Prompt 6 — Quant research harness review
- **Scope:** Track C design (research only).
- **Hard constraints:** [SAFE-RO]. Do not change thresholds or add signal
  families. Do not approve any signal.
- **Tasks:** using `04-quant-research-and-ml.md`, design label/horizon
  definitions, point-in-time + survivorship-free data handling, rank-IC +
  quintile-spread + turnover/cost computation on the existing ~24k
  `signal_outcomes` rows, walk-forward methodology, shadow paper book, and
  pre-registered promotion/kill gates as committed verdict files.
- **Deliverable:** the harness design + a sample verdict-file template.
- **Stop:** after the design. Build nothing.

## Prompt 7 — ML lifecycle review
- **Scope:** Track D design (no retraining).
- **Hard constraints:** [SAFE-RO]. Do not retrain. Do not run retrain_model_a.
- **Tasks:** leakage/label/feature audit checklist; Render retrain memory
  budget; calibration + drift metric design; `check_model_staleness` deployment
  plan; model retirement/quarantine policy; simple-baseline-first rule.
- **Deliverable:** the ML lifecycle design + the `check_model_staleness` rollout
  outline.
- **Stop:** after the design.

## Prompt 8 — Event-driven review queue design
- **Scope:** Track F design (no schema applied).
- **Hard constraints:** [SAFE-RO]. No migrations. No automation built. No
  autonomous remediation.
- **Tasks:** finalize the `ops_events`/`review_queue`/`review_decisions`/
  `review_artifacts`/`review_prompts`/`review_outcomes` design from
  `06-automation-and-review.md`; define the severity model, the event sources,
  and the human-approval gate; output DDL as a PROPOSAL only.
- **Deliverable:** the review-queue design + proposed (not applied) DDL.
- **Stop:** after the design.

## Prompt 9 — Portfolio decision ledger / tax overlay design
- **Scope:** Track E design.
- **Hard constraints:** [SAFE-RO]. Do not change tax logic. Respect CGT §5.1
  calendar arithmetic and the loss-harvest info-only disclaimer.
- **Tasks:** design the decision-ledger provenance view (signal row +
  model_version + profile + data freshness); the manual-override log; the
  position-monitor deployment plan; where a beta-cap (v2 candidate) would slot;
  the `build_portfolio` restart criteria checklist.
- **Deliverable:** the portfolio/ledger design as a proposal.
- **Stop:** after the design.

## Prompt 10 — Top 1% hedge-fund lean translation review
- **Scope:** Track I doctrine review.
- **Hard constraints:** [SAFE-RO].
- **Tasks:** for data, research, model governance, portfolio construction,
  execution/costs, monitoring, incident response, automation, and review
  cadence — state what an elite systematic fund does, then translate each into a
  lean ASXOS equivalent and map it to the relevant track. Be explicit about what
  such a fund would *refuse to trust* in ASXOS's current state (unmonitored loop;
  signal with no live realised-IC gate).
- **Deliverable:** the doctrine translation table + the top 3 disciplines to
  adopt first.
- **Stop:** after the review.
