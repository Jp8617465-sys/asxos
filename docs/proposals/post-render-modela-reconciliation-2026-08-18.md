# Work order — reconcile the repo to the post-Render / post-Model-A reality

**Status:** draft work order (advisory) · **Date:** 2026-08-18 · **Owner to ratify/apply:** James
**Basis:** `docs/session-handoff-2026-08-18.md` (merged, PR #139) + live verification this session
**Why draft:** every item below touches a James-gated surface — an authority file
(`.claude/settings.json` deny set), a production workflow, or a DB write. An agent may
*draft* these; only James applies them. Nothing here has been applied.

---

## The gap

Render was deleted 2026-08-12 and jobs now run as GitHub Actions workflows; Model A's
producer was deleted and `signals` is a dead table (handoff 2026-08-18). But `origin/main`
still ships the old world, verified this session:

- `render.yaml` is still present and still the "live deployment source" that `docs/README.md`
  and `README.md` point to.
- Model A is still fully wired: `jobs/retrain_model_a.py`, `models/model_a_v1_5_*.{pkl,json}`
  (4 artifacts), `migrations/0003_model_a_v1_5_seed.sql`, and live references in
  `asxos/domain/portfolio/build.py`, `asxos/domain/models/*`, `asxos/cli/model.py`,
  `asxos/config.py`, `.env.example`, `scripts/backup_irreplaceable.sh`.
- `CLAUDE.md` rule #2 still mandates managing "Render via its REST API"; the `Makefile`
  `deploy` / `check-drift` / `logs` targets still call Render.

Consequence (already observed in the handoff): every new agent session reconstructs the
dead Render + Model-A world from these docs. This is the largest single source of drift.

---

## Items

Each item is tagged **[gated]** (James applies — authority file / prod / DB) or
**[agent-reversible]** (an agent may do it on a branch to a draft PR).

### R1 — retire `render.yaml` **[gated: authority file + `.github` deny set]**
Delete `render.yaml`; update the `Makefile` `deploy`/`check-drift`/`logs` targets (they
name Render); grep for `RENDER_API_KEY` / `api.render.com` references and remove or replace
with the GitHub Actions equivalent.

### R2 — rewrite `CLAUDE.md` rule #2 and the deployment prose **[gated: authority file]**
"Manage Render via its REST API" → "Jobs run as GitHub Actions workflows
(`.github/workflows/`); config lives in git, secrets in repo Actions secrets." Keep the
"no dashboard clicks / config in git" principle — it now points at Actions, not Render.

### R3 — reword rule #11 / Model-A framing (do NOT weaken the quarantine) **[gated]**
Model A is *deleted*, not merely shelved: the producer is gone and `signals` has no writer.
Rule #11 (no capital-facing use of `signals`/`model_versions`/`shap_factors`/`prob_up`/
`expected_return`) **stands** as resolved policy; update `CLAUDE.md` + `README.md` +
`north-star.md` to say "deleted + quarantined," not "shelved/disputed."

### R4 — Model-A code/artifact disposition **[mixed]**
- **[agent-reversible]** delete `jobs/retrain_model_a.py`, `models/model_a_v1_5_*.{pkl,json}`,
  and the now-dead references in `asxos/cli/model.py`, `asxos/domain/models/*`,
  `asxos/config.py` (the `healthcheck_url_retrain_model_a` field), `.env.example`.
- **[gated]** `migrations/0003_*` and `0032_model_versions_allocation_gate.sql` cannot be
  deleted (migrations are immutable, `REQUIRED_MIGRATIONS = 96`): add a superseding note, not
  a deletion. The enforcement site in `asxos/domain/portfolio/build.py` (the
  `is_active AND approved_for_allocation` fetch, marked DO-NOT-DELETE) needs an explicit
  ruling now that the quarantine subject is gone — keep as a standing guard, or replace with
  a hard "no signals table" assertion.

### R5 — `docs/README.md` source-of-truth index **[gated: authority file]**
Repoint "live deployment source" from `render.yaml` to `.github/workflows/`.

---

## Operational finding — `pipeline-health` is red on a stale row (not a new defect)

`pipeline-health` has failed the last 3 scheduled runs (08-15/16/17; latest
`32076081365`). Root cause, from the failed-step log: it correctly detects
`STUCK: sync_financial_statements as_of=2026-08-15 … running for >4h`. That is the orphaned
`job_runs` row left by the **cancelled** 08-15 `weekly-research` run (timed out mid-step);
nothing reconciled it, so the watchdog re-alarms daily. Two-part fix:

- **[gated: DB write]** reconcile the orphaned row (mark the 08-15 `sync_financial_statements`
  `running` row failed/cancelled). One-off; James / a scoped write.
- **[agent-reversible]** harden `jobs/check_cron_health.py`: treat a `running` row older than
  the same job's latest *completed* run as **orphaned/stale**, a distinct kind from a live
  stuck job — and/or add a cancellation-cleanup step so a cancelled workflow marks its
  in-flight `job_runs` row failed. This is another instance of the handoff's "built, but the
  thing that reconciles it doesn't exist" pattern.

The 08-18 *manual* `weekly-research` dispatch already passed (`32099973966`, 24m6s); the next
*scheduled* Saturday run is the on-schedule proof. `daily-brief`, `us-positions`, `backup`
are green.

---

## Cron coverage — confirm keep/drop (no silent omission)

The daily/weekly chains were bundled into `daily-brief.yml` (12 steps) and
`weekly-research.yml` (6 steps). Former Render crons with no Actions home:

- **Deliberately retired with Model A (confirm):** `generate_signals`, `retrain_model_a`,
  `compute_factor_scores`, `compute_opportunity_cost`, `build_portfolio`, and the ML monitors
  (`track_signal_outcomes`, `check_model_staleness`).
- **Need an explicit keep/drop ruling:** `detect_theme_stages` (was a daily Render cron) and
  `monitor_paper_portfolio` (paper-trade evaluator — ties to the dark-surface expiry decision
  due 2026-08-28).

---

## Suggested order

1. Reconcile the map (R1–R5) — highest leverage; stops daily agent misdirection.
2. `check_cron_health` hardening + clear the stale row — turns `pipeline-health` green and
   closes the cancellation-cleanup gap.
3. Cron-coverage ruling (theme-stages, paper-portfolio).
