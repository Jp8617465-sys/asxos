# Playbook — Product Reality Sweep

**Type:** playbook (reusable procedure) · read-only reference
**Run via:** `/arbi-run product reality sweep` (attended) — arbi plans, main loop dispatches
**Goal:** find what **claims to work but doesn't** — then ship / fix / quarantine / delete

Lessons are memory; **playbooks are procedures.** This is arbi's recurring truth-pruning
sweep. The reward is NOT "# of PRs" — it is: fewer fake-green surfaces · fewer stale data
dependencies · more product paths that actually run · more brief sections rendering from
current data · fewer docs contradicting the source-of-truth map · lower time-to-detect a
broken cron · more risks closed with evidence.

---

## Inputs (read-only)
`render.yaml` · live Render service list (`mcp__render__list_services`) · `job_runs` ·
latest `prices.dt` / `signals.as_of` / `market_context_current` (via `mcp__supabase-ro__*`) ·
Healthchecks status · `risk-register.md` · `cleanup-backlog.md` · `roadmap-state.md` ·
`docs/README.md` · the newest handoff.

## The eight reality checks (dispatch owners in parens)
1. **Cron reality** (`backend-architect`) — `render.yaml` vs live Render vs `job_runs` vs
   Healthchecks. Which crons exist but never ran; ran but wrote no useful rows.
2. **Supabase reality** (`backend-architect`) — required tables, row counts, latest
   timestamps; **empty-but-required** tables (e.g. `signal_outcomes`).
3. **Brief reality** (`system-architect`) — what actually renders; what's dark-launched
   (`ASXOS_*_ENABLED=0`); what fails/omits if Model A is quarantined (post-R9).
4. **Thesis reality** (`portfolio-invariant-guard`) — active theses; missing
   stops/targets/revisions; discipline-alert coverage (suffix holes: `.AU`/`.US` only).
5. **Model reality** (`backend-architect`) — Model A decay; `signal_outcomes` empty →
   `track_signal_outcomes` broken/not-run; fix so the decay check is one query.
6. **Research reality** (`backend-architect`) — research-store tables populated vs empty;
   `alpha_eval` freshness; factor-score jobs.
7. **Docs reality** (`technical-writer`) — stale `strategy/V2_*`; old roadmap claims;
   branch-only docs; assumptions contradicted by the source-of-truth map.
8. **Product pruning** (arbi synthesizes) — for each finding: **ship · fix · quarantine ·
   delete**.

## Output
- new `risk-register.md` rows (evidence-cited) · new `cleanup-backlog.md` rows ·
  the single ranked next action · a run-ledger row with the sweep's scorecard.
- A **live product-health scorecard** (target: `docs/product/product-health-scorecard.md`):
  `cron_success_rate · missing_job_runs · latest_prices_dt · latest_signals_as_of ·
  signal_outcomes_count · market_context_freshness · active_thesis_count ·
  holdings_without_thesis · alert_jobs_running · brief_sections_rendering ·
  dark_launch_gate_status · stale_docs_count · open_P0_P1_risks`.

## Boundaries
Read-only + reversible-doc output only. Any fix that touches code/DB/cron/infra is a
**proposal → James** (irreversible infra stays gated). Never act on Model A output for
capital (rule #11).
