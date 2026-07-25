# Model A runtime decommission and evidence-retention plan

**Status:** recommended target state; product/runtime execution requires a
separate James-approved mission and reviewed PR
**Decision owner:** James
**Programme owner:** Arbi
**Applies to:** Model A `v1_5`, its signal pipeline, allocator dependencies, and
Model-A-dependent product/review surfaces
**Does not authorise:** destructive data deletion, production configuration changes,
migration apply, deploy, model revival, or broker activity

## Recommendation

Completely decommission Model A from the live application runtime, capital path,
and investment-engine evidence path. Do not destroy its history. Preserve model
artifacts, configurations, signals, outcomes, and the 2026-07-11 decay analysis
as a checksummed, read-only audit archive.

If James ratifies DEC-025 in S01 M02, this target supersedes the current
passive-monitor state. Until that signed record and its authority amendment
exist, `CLAUDE.md` and `docs/product/ml-engine-shelf-2026-07-11.md` remain the
runtime authority; this dossier alone changes no job or product surface. The
recommended end state is simpler:

- no scheduled Model A training, inference, outcome-refresh, staleness, signal
  allocation, or signal-ranked opportunity-cost work;
- no Model A CLI, brief, review, agent, health, or default product surface;
- no imports, queries, payload fields, feature flags, or fallbacks from the new
  investment engine into Model A tables or packages;
- read-only evidence retained for audit, reproduction, and perturbation-isolation
  tests; and
- any future model enters as a new, separately named evidence programme. Model A
  `v1_5` never revives or silently becomes an allocator dependency.

## Why this is the north-star-positive choice

The repository's direct evidence is already decision-grade for retirement:

- `docs/model-a-decay-analysis-2026-07-11.md` records 19,032 matured
  `model_a_ml` signals;
- pooled `ml_prob` correlation was approximately `+0.032` at five days and
  `-0.030` at 21 days;
- the strongest long label underperformed the neutral label at 21 days; and
- rule #11 was made standing policy because the model had no usable,
  monotonic capital edge.

Keeping that model operational does not add governed capital coverage or
prospective engine evidence. It does add failure surfaces and ambiguous product
authority.

| North star | Positive effect | Proof |
|---|---|---|
| Capital Under Discipline | Removes an unapproved input, allocator, and review influence from every governed holding path. | Static import/query/payload denial plus bit-identical perturbation test. |
| Material-event latency | Removes unrelated Model A cron failures/staleness from the alerting signal-to-noise budget. | Scheduler inventory shows zero enabled Model A jobs and no Model A deadman dependency. |
| Prospective investment result | Prevents historical Model A outcomes from being mixed with the pre-registered thesis-engine cohort. | Evaluator config and origin manifests reject Model A data classes and hashes. |

Decommissioning does not claim alpha. It protects the validity of the new
engine's evidence and directs operating attention to the thesis, review,
monitoring, construction, risk, tax, accounting, and paper-evaluation system
that can move the north star.

## Scope inventory to resolve before any change

The implementation mission must refresh this repository-derived inventory
against the deployed scheduler, database, secrets/configuration, and current
`main`. Absence from this table is not evidence of absence.

### Scheduled and batch surfaces

| Repository surface | Target treatment |
|---|---|
| `render.yaml` / `jobs/generate_signals.py` | Disable the schedule; deny unattended and attended writes for Model A. |
| `render.yaml` / `jobs/retrain_model_a.py` | Keep disabled; remove from active health and operating runbooks. |
| `render.yaml` / `jobs/build_portfolio.py` | Disable the legacy signal-driven build; do not redirect it to the new engine. |
| `render.yaml` / `jobs/compute_opportunity_cost.py` | Disable the signal-ranked job and remove it from current product health. |
| `render.yaml` / `jobs/check_model_staleness.py` | Disable Model A staleness checking; archive historical job evidence. |
| `render.yaml` / `jobs/track_signal_outcomes.py` | Stop new Model A outcome writes after the final archive watermark. |

The deployed scheduler is authoritative. The implementation mission must record
the deployed service/job identifier, repository command, enabled state, last
successful/failed run, healthcheck/deadman, upstream/downstream dependencies,
and the exact attended change used to disable each job.

### Product and agent surfaces

| Surface | Target treatment |
|---|---|
| `.claude/commands/pm-review.md` | After the approved M-A2 authority amendment, disable the legacy command in M-A3; S04/S05 introduce the independent replacement rather than mutating this path in place. |
| `.claude/agents/thesis-coherence-guard.md` | Retire the SHAP/signal reviewer; preserve in Git history and the archive manifest. |
| `.claude/agents/portfolio-coherence-reviewer.md` | Remove Model A queries and replace the role only through the new immutable review contract. |
| `asxos/cli/model.py`, `asxos/cli/signal.py` | Remove from default/help product surfaces or make invocation fail closed with `MODEL_A_DECOMMISSIONED`. |
| Brief, API, and view readers | Remove signal/model fields and fallback reads; an empty Model A state must not degrade the new product. |
| `asxos/domain/portfolio/*` legacy allocator path | Make unreachable from active routes/jobs; do not wrap it as thesis-led construction. |
| Model/signal packages and loaders | Deny from new engine dependency graphs; later code deletion is optional after reachability proof. |

### Data and artifact surfaces

The mission must inventory, without mutating them:

- Model A model/version/configuration rows and artifact files;
- `signals` rows attributable to Model A;
- `signal_outcomes` rows attributable to Model A;
- allocator/rebalance/opportunity-cost records derived from Model A;
- `job_runs`, logs, healthcheck history, and deployed schedule evidence;
- relevant migrations, training code, feature definitions, thresholds, and
  production gates; and
- the decay-analysis source queries or reproducible result bundle.

Before disabling the final writer, produce and validate
[`model-a-archive-manifest-v1`](contracts/model-a-archive-manifest-v1.md), then
complete an attended non-production
[`model-a-archive-restore-evidence-v1`](contracts/model-a-archive-restore-evidence-v1.md)
drill. M02 may seal an integrity-complete archive while the quarantined writer is
still active; sealing is not a shutdown claim. The machine manifest includes:

```text
archive_id
created_at
created_by = James | attended-operator
baseline_sha
deployment_environment
source_snapshot_started_at
source_snapshot_completed_at
dataset_or_artifact_class
locator
model_identity
row_count_or_file_count
minimum_observed_at
maximum_observed_at
source_schema_or_media_type
canonicalization
sha256
writer_state_at_snapshot = ACTIVE | DISABLED | UNKNOWN
writer_disabled_at = null | pre-existing disable timestamp
retention_class = READ_ONLY_AUDIT
access_policy_ref
notes
```

`writer_disabled_at` is optional/nullable and may be populated only when
`writer_state_at_snapshot=DISABLED` before M-A1 began. A sealed M-A1 manifest
proves deterministic export integrity, not shutdown; M-A1 performs no source,
scheduler, writer, deployment, or configuration mutation.

For database data, the digest input is a documented, deterministically ordered
export with explicit column order, null representation, timestamp zone, Decimal
encoding, and newline rules. For files, hash raw bytes. Secrets and credentials
are never exported into the archive.

The restore evidence must resolve the exact manifest ID/root hash, compare the
same class set, counts, ranges and raw/canonical hashes, recompute every
producer-supplied match boolean, and return `NOT_READY` on any mismatch or
unsafe environment. A filename, prose checklist or unchecked producer `PASS`
does not satisfy M02.

## Twelve-week placement

This is one controlled decommission thread through the accepted programme, not a
thirteenth feature sprint.

### S01 — quarantine, inventory, archive, and runtime-off proposal

- Ratify this target or record `NOT APPROVED`; no implicit approval.
- If ratified, amend in one reviewed authority change every current document
  that prescribes the passive monitor or legacy `/pm-review` path, including
  `CLAUDE.md`, the ML shelf, portfolio-manager charter, portfolio policy,
  recommendation schema, Arbi permission model, north star, and portfolio
  conventions. The stricter current text wins until that change is approved.
- Capture current `main`, deployed schedules, readers/writers, healthchecks,
  routes, commands, data classes, model artifacts, and last-run watermarks.
- Produce the archive manifest and reproducibility packet.
- Close the bounded 12-hour M02 after read-only inventory, archive,
  restore/reproduction, and the approval decision. Do not combine shutdown or a
  naturally elapsed no-write observation into that mission.
- If approved, open separate M-A2/M-A3 mission/change sets to amend authority,
  disable the six jobs above, make legacy Model A command/route invocation fail
  closed, and observe a formerly scheduled window.
- Remove Model A health failures from current product-health denominators only
  after the corresponding job is proven disabled in M-A3.
- Preserve existing rows and artifacts; apply no destructive migration.

### S04–S05 — independent review replacement

- Build `review-context-v1` without Model A queries, fields, or tools.
- Replace the two Model-A-coupled reviewer roles with blind, immutable,
  evidence-based review roles.
- Do not alias the new reviewer output to old SHAP/signal semantics.
- Prove deleting or randomising the complete Model A archive leaves context,
  assessment eligibility, and hashes bit-identical.

### S08–S11 — evidence isolation

- `evaluator-config-v1` links immutable dependency-isolation evidence.
- Evaluation origins reject Model A snapshot classes, fields, and source hashes.
- Cohort statistics use only pre-registered prospective thesis-engine records.
- Model A historical outcomes may be reproduced as an archive audit but cannot
  enter a promotion denominator, benchmark, counterfactual, or feature.

### S12 — reachability and handoff proof

- Generate a dependency graph proving no active investment-engine code imports
  Model A packages.
- Run SQL/query tracing proving no active engine command or paper job reads
  Model A tables.
- Always prove no investment-engine job, CLI default, brief, reviewer, or
  staged-package renderer depends on Model A. If DEC-025 was approved and M-A3
  closed, additionally prove no Model A scheduler or product-health requirement
  remains enabled; otherwise report the separate decommission lane `NOT
  COMPLETE` without weakening engine isolation.
- Record whether unreachable runtime code is retained or removed. Git history
  and the read-only evidence archive remain in either case.

## Required implementation missions

The dossier itself changes documentation and executable dossier validation only.
Production decommission requires separate attended missions:

1. **M-A1 — inventory and archive:** read-only discovery, deterministic export,
   manifest, checksums, restore/reproduction drill, James review.
2. **M-A2 — authority amendment and retirement authorisation:** land the
   James-approved authority changes that make runtime retirement and the
   `/pm-review` tombstone non-contradictory. This mission changes authority; it
   does not claim that a writer has stopped.
3. **M-A3 — runtime and surface retirement:** only after M-A2, disable the exact
   deployed jobs and writers, update deadmen/health, fail closed or remove
   legacy CLI/agent/brief/API entry points, observe at least one formerly
   scheduled window, capture no-write proof, and prove unrelated
   thesis/tax/monitoring paths remain healthy.
4. **M-A4 — isolation certification:** static dependency graph, runtime query
   trace, archive perturbation, evaluator-origin denial, and independent review.
5. **M-A5 — optional unreachable-code removal:** only after M-A4; ordinary
   reviewed deletion with regression tests, never database evidence deletion.

Each mission is one reviewed PR/change set with exact baseline/head,
environment, owner, deployed identifiers, tests, observations, rollback,
approval, and a clean close verdict. Arbi prepares and coordinates; James alone
approves merge, deploy, production configuration, and any data-policy change.
Elapsed evidence clocks may outlive the active 8/12-hour work window; the mission
records the start and returns only after the real scheduled window elapses. It
never fabricates elapsed time or folds multiple change sets into one recipe.

## Acceptance and circuit breakers

The decommission is complete only when all predicates are true:

- `0` enabled deployed Model A schedules;
- `0` successful new writes to Model A signal/outcome/allocation tables after
  the recorded shutdown watermark;
- `0` active investment-engine imports, runtime queries, payload fields, prompt
  inputs, or fallbacks referring to Model A;
- `0` Model A jobs in current product-health or deadman denominators;
- every archived class has count/range/schema/hash and a successful attended
  restore or reproduction check;
- randomising or removing archive access leaves the new engine's canonical
  outputs bit-identical;
- archived Model A data is read-only to application writers;
- the legacy allocator cannot be reached by an active command, route, job, or
  feature flag;
- the replacement review/evaluator paths pass without Model A services; and
- an independent reviewer verifies the evidence packet.

Stop and return `NOT READY` if deployed inventory is incomplete, a downstream
job still requires fresh Model A state, archive hashes cannot be reproduced,
the new engine reads a Model A class, or disabling a job would weaken an
unrelated operational control. Do not keep a writer alive merely to avoid
repairing a false dependency.

## Rollback and retention

Rollback restores product availability, not Model A capital authority.

- A scheduler rollback may temporarily restore a read-only archive/export
  utility after James approval; it may not restore inference, allocation, or
  investment-engine inputs.
- A surface rollback may restore a tombstone/help message, not old signal-driven
  recommendations.
- If an unexpected consumer appears, disable that consumer or return
  `NOT READY`; do not silently reactivate Model A.
- No twelve-week migration drops Model A tables, erases outcomes, deletes model
  artifacts, or rewrites historical records.
- A later retention/deletion decision requires a separate data-governance
  proposal with legal, audit, backup, restore, and reproducibility analysis.

## Future models

A future quantitative model is not “Model A fixed.” It must have a new identity,
pre-registered hypothesis, dataset and feature lineage, frozen evaluation
policy, leakage controls, prospective cohort, independent review, and explicit
James promotion decision. It starts outside the capital path. No archive reader,
compatibility alias, or `approved_for_allocation` flag may revive `v1_5`.
