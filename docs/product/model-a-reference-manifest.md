# Model A reference manifest — the retirement contract

**Status:** current · frozen contract for mission P1-02
**Scope:** every Model A reference in the repo, classified so that P1-02 (remove runtime/API/job
dependencies) can proceed without silently disarming rule #11
**Last verified:** 2026-08-13 against pinned base SHA `fad62159f5d6585588d47bbac763687da55f0002`
(`origin/main`, observed 2026-08-12T21:29:56Z)
**Produced by:** mission P1-01 — exploration + contract-freeze. **No retirement edits were made;
this file is the only file the mission created or changed.**
**Owner:** arbi maintains; James governs the retirement decision
**Superseded by:** N/A

---

## Why this document exists

Rule #11's **mechanical enforcement point contains zero Model A tokens.**

`asxos/domain/portfolio/build.py:184-189` is the code that actually stops Model A from reaching
real capital. It queries `model_versions WHERE is_active = TRUE AND approved_for_allocation =
TRUE` and passes the result to `resolve_production_model()`, which raises `ModelGateDormant` on
zero approved rows. Because `approved_for_allocation` was revoked for `model_a`/`v1_5` on
2026-07-11, that query returns **0 rows** and the allocator **refuses to run**. That is the
quarantine, in code.

A `git grep` for `model_a|Model A|MODEL_A|model-a` returns **0 hits in `build.py`** and **2 hits
in `tests/test_portfolio_build.py`**. A token-driven retirement would therefore delete the *test*
and keep the *enforcer* — or, worse, delete the enforcer as "Model A plumbing" and leave rule #11
with no teeth and no failing test to announce it.

That is not a hypothetical edge case. **Six of the most load-bearing sites in this manifest are
completely invisible to the token search**, including the enforcer above, the artefact loader, the
signal threshold ladder, and the weekday cron that still produces Model A signals.

This manifest declares two sets: a reproducible mechanical token set (**S1**) and an
import/call-graph closure set (**S2**), and classifies every S2 site into five categories — one of
which, `ENFORCEMENT_KEEP`, exists purely to name the code that must survive *because it enforces
the quarantine*.

---

## S1 — the mechanical set (reproducible, falsifiable)

### The committed pattern

```
model_a|Model A|MODEL_A|model-a
```

### The committed commands

Run from the repo root. `git grep` is used deliberately — it scans **tracked files only**, which
excludes the untracked `.claude/worktrees/**` agent checkouts by construction, with no exclude
list to maintain.

```bash
# S1 file count  -> 207
git grep -lE 'model_a|Model A|MODEL_A|model-a' fad62159f5d6585588d47bbac763687da55f0002 | wc -l

# S1 line count  -> 989
git grep -cE 'model_a|Model A|MODEL_A|model-a' fad62159f5d6585588d47bbac763687da55f0002 \
  | awk -F: '{s+=$NF} END{print s}'
```

**S1 = 207 files / 989 matching lines** at the pinned SHA. (`git grep -c` counts matching
*lines*, not occurrences; a line with two matches counts once.)

### Why not filesystem grep

| Method | Files | Lines |
|---|---:|---:|
| `git grep` (tracked only) — **the declared S1** | 207 | 989 |
| `grep -rI .` (working tree) | 600 | 2,764 |
| — of which under `.claude/worktrees/**` (untracked) | — | 1,773 |

Filesystem grep inflates the count ~2.8x by re-counting agent worktree checkouts of the same
repo. Any count quoted from `grep -r` is not reproducible and must not be used.

### Per-area breakdown

| Area | Files | Lines |
|---|---:|---:|
| `docs/` | 99 | 524 |
| `tests/` | 32 | 217 |
| `asxos/` | 26 | 99 |
| `.claude/` | 27 | 79 |
| `jobs/` | 6 | 33 |
| `migrations/` | 7 | 17 |
| root (`.env.example`, `CLAUDE.md`, `README.md`, `render.yaml`) | 4 | 13 |
| `.github/` | 3 | 4 |
| `scripts/` | 2 | 2 |
| `models/` | 1 | 1 |
| **Total** | **207** | **989** |

### Precision caveat — the pattern over-matches

`model_a` has **no trailing word boundary**, so it also matches identifiers that have nothing to
do with Model A:

| Over-matching token | Lines | Note |
|---|---:|---|
| `model_and_prompt_manifest` | 14 | Decision-engine field name — *the thing that bans Model A* |
| `model_activate` / `_run_model_activate` | 8 | CLI function name |
| `model_app` | 6 | Typer app object |

Also matching but unrelated in prose: `model-assisted`, and every citation of
`docs/research/operating-model-architecture.md`.

A boundary-aware pattern mirroring the codebase's own `_MODEL_A_RE`
(`asxos/domain/decision_engine/types.py:56-62`) yields **203 files / 969 lines** — about 20 lines
of noise removed:

```bash
git grep -cE '(^|[^A-Za-z0-9])[Mm][Oo][Dd][Ee][Ll][ _-]?[Aa]($|[^A-Za-z0-9])|MODEL_A($|[^A-Za-z0-9])' \
  fad62159f5d6585588d47bbac763687da55f0002 | awk -F: '{s+=$NF} END{print s}'
```

**S1 stays at the four declared patterns** (207/989) so the number matches the mission brief and
stays trivially reviewable. **The boundary-aware pattern is what the CI assertion should use** —
see the CI design section.

### Pattern-extension probe (why S1 was NOT extended)

Candidate additional tokens, tested for files they would add *beyond* the base pattern:

| Candidate token | Files matching | Files **not** already in S1 |
|---|---:|---:|
| `prob_up` | 68 | 29 |
| `joblib` | 34 | 13 |
| `lightgbm` | 28 | 12 |
| `signal_outcomes` | 35 | 5 |
| `v1_5` | 73 | 4 |
| `ml_prob` | 22 | 3 |
| `LightGBM` | 24 | 3 |
| `approved_for_allocation` | 37 | 2 |
| `resolve_production_model` | 12 | 1 |
| `ModelGateDormant` | 4 | 1 |
| `ModelA` / `modela` / `MODEL_ARTIFACT` | 0 | 0 |

**Decision: do not extend.** Folding ~50 graph-reachable code sites into a count whose only job is
to be a stable tripwire baseline would make it less reviewable, not safer. Those sites belong in
S2, classified individually. The probe is recorded here as *evidence for why S2 must exist*:
29 files consume Model A's headline output column (`prob_up`) without ever naming Model A.

---

## S2 — the safety set (import/call-graph closure)

Derived by tracing importers and callers of the declared seeds — not by token match. Every entry
cites `file:line`. The **Tok** column is that file's S1 token count; **`0` means S1 is blind to
it.**

**S2 = 61 cited sites.** This is above the 15-40 the mission anticipated, and the overshoot is
itself a finding: the quarantine is enforced in **four independent layers**, not one. Beyond the
allocator gate there is a decision-engine manifest rejection, a thesis-schema `monitor_only`
guard, and a screening field whitelist — each with its own tests. Enforcement *tests* are counted
as sites because deleting them is the silent-weakening path this manifest exists to block.

| Category | Sites |
|---|---:|
| `ENFORCEMENT_KEEP` | 21 (11 code + 10 tests) |
| `ACTIVE_REMOVE` | 26 |
| `ADAPT` | 11 |
| `MIGRATION_KEEP` | 3 |
| `HISTORICAL_KEEP` | 0 in S2 — `docs/**` is classified at file granularity below |
| **Total** | **61** |

### The six token-blind sites (S1 cannot see these)

| Site | Category | Why it matters |
|---|---|---|
| `asxos/domain/portfolio/build.py:184-189` | **ENFORCEMENT_KEEP** | **The rule #11 enforcer.** |
| `asxos/domain/models/cache.py` | ACTIVE_REMOVE | The joblib artefact loader; also the *ungated* version resolver. |
| `asxos/domain/signals/thresholds.py` | ACTIVE_REMOVE | The signal threshold ladder / `classify_batch`. |
| `render.yaml:276-296` (`asxos-generate-signals`) | ACTIVE_REMOVE | The weekday cron that **produces** Model A signals. |
| `asxos/cli/signal.py:27`, `asxos/cli/journal.py:43`, `jobs/compute_opportunity_cost.py:47` | ADAPT | Three `FROM signals` readers. |
| `tests/test_job_monitor.py:23,101,112` | **ENFORCEMENT_KEEP** | Pins `ModelGateDormant` → `'blocked'`. |

---

### `ENFORCEMENT_KEEP` — code (11)

> Deleting any row here weakens rule #11. None of it is kept for sentiment or history.

| # | Site | Tok | What it enforces | What breaks if removed |
|---|---|---:|---|---|
| **E1** | `asxos/domain/portfolio/build.py:184-189` | **0** | The allocator's `model_versions WHERE is_active AND approved_for_allocation` query + `resolve_production_model(model_rows)` at `required=True` | **Rule #11 loses its teeth.** This is the single point where a revoked approval becomes a refusal to allocate. Delete it and the allocator runs against whatever candidate source replaces signals with no approval gate at all. |
| **E2** | `asxos/domain/models/production_gate.py:47-87` | 3 | `resolve_production_model()` — the gate condition and both hard-fail messages, in one place | The gate condition disappears; `build.py` and any future consumer drift apart on the invariant. The `required=True`/`required=False` split (risk-register R9) that lets the quarantine harden without breaking the brief is lost. |
| **E3** | `asxos/domain/models/production_gate.py:20-34` | — | `class ModelGateDormant(RuntimeError)` — the *distinctly named* dormant exception | Dormancy becomes indistinguishable from a crash. `JobMonitor` can no longer classify it (E4), so the deliberate quarantine pages as `failure` — creating standing pressure to "fix" it by re-approving the model. |
| **E4** | `asxos/jobs/utils/job_monitor.py:124-134` | 1 | Maps `ModelGateDormant` (by `exc_type.__name__`) to `job_runs.status='blocked'`, **not** `'failure'`; Healthchecks is not pinged for blocked runs | The weekly `build_portfolio` dormancy alerts every Saturday forever — the alert-fatigue failure mode that gets quarantines quietly reverted. |
| **E5** | `asxos/domain/decision_engine/types.py:56-62` | 12 | `_MODEL_A_RE` — boundary-aware regex matching `model a` / `model_a` / `model-a` / `v1.5` / `v1_5`, case-insensitive | **Inverse-polarity reference.** This token appears in code whose *purpose is to ban Model A*. A naive "delete Model A references" pass removes the ban itself. |
| **E6** | `asxos/domain/decision_engine/types.py:524-528` | — | Rejects any decision whose `model_and_prompt_manifest` mentions Model A or v1_5: `raise ValueError("Model A and v1_5 are quarantined from the decision basis")` | The decision engine would accept a recommendation built on Model A provenance — rule #11 enforced at the *decision record* layer, independent of the allocator. |
| **E7** | `asxos/domain/decision_engine/types.py:45-53` | — | `UNIVERSAL_CONSTRAINTS` includes `"model_a_quarantine"` as a mandatory constraint name | The quarantine stops being a universally required constraint on every decision. |
| **E8** | `asxos/domain/decision_engine/types.py:631-635` | — | Requires exactly one `model_a_quarantine` constraint, `blocking=True`, `status="pass"` | A decision could be emitted with the quarantine constraint absent, non-blocking, or failing. |
| **E9** | `asxos/domain/theses/schemas.py:216,227,263,338,380,388` | 6 | `monitor_only` guard — bars a rule #11 Model A datapoint from a thesis basis section or from acting as a capital lever (`target_price`/`stop_price`/`entry_band_*`) | Model A figures could re-enter the written investment case through the thesis schema — the exact laundering path the quarantine closes. |
| **E10** | `asxos/domain/theses/discipline.py:15-24` | 1 | Module contract: never reads `signals`/`shap_factors`/`prob_up`/`expected_return`/`signals.regime`, never calls `resolve_production_model()`, never invokes `thesis-coherence-guard` | The discipline layer — the model-independent moat — loses its written isolation contract and can drift back into model reads. |
| **E11** | `asxos/domain/screening/types.py:10` | 1 | Module contract: no screening path may reach a Model A / SHAP / signal value | Same drift risk for the Tier 2a screening evaluator. |

> **E5-E8 are ratified architecture.** `docs/product/target-architecture.md` (rows RATIFIED
> 2026-08-12, PR #87) binds the manifest regex rejection and the blocking `model_a_quarantine`
> constraint as architectural requirements — they are not incidental prototype code.

> **Same file, two classifications.** `build.py:184-189` is `ENFORCEMENT_KEEP` (E1) while
> `build.py:191-215` (the `FROM signals` fetch) is `ADAPT` (A1). **P1-02 must split this file at
> the line level**, not delete or keep it wholesale.

---

### `ENFORCEMENT_KEEP` — tests (10)

> These prove the quarantine still works. Deleting one removes the alarm, not just the coverage.

| # | Site | Tok | Load-bearing assertion | What breaks if removed |
|---|---|---:|---|---|
| **T1** | `tests/test_production_gate.py:33-40, 42-49, 52-62` | 8 | `pytest.raises(ModelGateDormant)` on 0 rows; `assert not isinstance(exc, ModelGateDormant)` on >1; `required=False` returns `None` | The 0-vs->1 exception-type split collapses. `ModelGateDormant` could degrade to a bare `RuntimeError` (breaking E4), or a >1 misconfig could be reclassified as "dormant" and stop paging. |
| **T2** | `tests/test_portfolio_build.py:64-67, 70-83` | 2 | `pytest.raises(RuntimeError, match="approved_for_allocation")`; `match="multiple models"`; comment at `:8-13` pins gate-before-signals ordering | **The allocator's capital-safety hard-fail becomes untested.** `build()` could start silently picking an arbitrary model. This is E1's alarm. |
| **T3** | `tests/test_job_monitor.py:23, 101, 112-113` | **0** | `pytest.raises(ModelGateDormant, match="approved_for_allocation")`; `assert update_call.args[1] == "blocked"` | **Highest-value blind spot.** `test_production_gate.py:36-38` names this file as the *reason* `ModelGateDormant` must stay a distinct type — the two are a mutually-referencing pair, and a token sweep keeps one and drops the other. |
| **T4** | `tests/test_decision_engine_prototype.py:357-378, 380-400, 386-388, 292-297` | 15 | Parametrized rejection of `model_a`, `model_a_ml`, `model_a_v2`, `Model-A`, `model a`, `v1_5` → `match="quarantined"`; dropping `model_a_quarantine` → `match="Model A quarantine constraint"` | Model A could re-enter a decision brief's manifest unchallenged. **Single point of failure:** this is the *only* file testing `_MODEL_A_RE`, `UNIVERSAL_CONSTRAINTS`, and `verify_content_hash` — treat as non-retirable in full, do not prune test-by-test. |
| **T5** | `tests/test_screening_evaluator.py:115-133` | 5 | Parametrized whitelist rejection of `signal_label`, `prob_up`, `expected_return`, `shap_factors` → `match="unknown field"` | The screening rule DSL's field whitelist loses its rule #11 coverage; a screen could reach ML columns. (Same test also carries the SQL-injection-via-field-name case.) |
| **T6** | `tests/test_thesis_discipline.py:302-336` | 2 | `test_module_imports_are_model_independent` — reads `discipline.py`, asserts no import contains `signals`, `models`, `model_a`, `production_gate`, `shap`, `predict`, `cache` | E10's only mechanical enforcement. Without it the contract is docstring-only. |
| **T7** | `tests/test_thesis_proposal_schema.py:126-137, 243-256` | 5 | `monitor_only=True` in a basis section → `ValidationError`; a Model A figure may never be `target_price`/`stop_price`/`entry_band_*` | A Model A number could become the actual trade lever inside a thesis. |
| **T8** | `tests/test_thesis_service.py:938-951` | 2 | `pytest.raises(ValueError, match="monitor_only")` on `add_report_section` | The service write path could bypass `schemas._check_monitor_placement`; this test exists to prove reuse, not reimplementation. |
| **T9** | `tests/test_brief_compose.py:548-578, 582-607, 139-166, 644` | 10 | 0 approved → brief renders, `regime is None`, `model_shelved is True`; >1 approved → `model_shelved is False` ("misconfig, NOT the shelf"); `:152-158` proves shelving doesn't suppress a genuine model-independent warning | Either the brief starts hard-failing under a standing quarantine (pressure to lift it), or model-derived sections leak through while quarantined. |
| **T10** | `tests/test_active_theses_signals.py:105-115, 117-129, 49` | 12 | 0 approved → `status == SectionStatus.ok` and `"Model A:" not in message`; >1 approved → same skip | The display-only thesis card path could hard-fail, or keep printing a Model A driver line while quarantined. |

---

### `MIGRATION_KEEP` — applied SQL, never edited (3)

| # | Site | Tok | Note |
|---|---|---:|---|
| **M1** | `migrations/0032_model_versions_allocation_gate.sql:22` | 2 | `ADD COLUMN approved_for_allocation BOOLEAN NOT NULL DEFAULT FALSE` — **the schema of the enforcement gate.** Also functionally `ENFORCEMENT_KEEP`: drop this column and E1/E2 cannot express the invariant. Applied; never edit. |
| **M2** | `migrations/0003_model_a_v1_5_seed.sql:1-3` | 3 | Seeds the `model_a`/`v1_5` `model_versions` row. Applied. The row must stay (with `approved_for_allocation = FALSE`) — **deleting the row is not the retirement mechanism**, and would make the gate's 0-row state ambiguous. |
| **M3** | `migrations/0001_initial.sql`, `0030_drop_non_asxos_schema.sql`, `0031_thesis_disposal_return_and_benchmark_seed.sql`, `0037_security_kind.sql`, `0038_screening_evaluator_wiring.sql` | 1/3/1/3/4 | Incidental Model A mentions in applied SQL (5 files, 12 lines). Applied; never edit. |

---

### `ACTIVE_REMOVE` — live Model A consumption, deleted by P1-02/03/04 (26)

| # | Site | Tok | What it does |
|---|---|---:|---|
| R1 | `asxos/api/main.py:13,44` | 1 | `await get_cache().get("model_a")` inside the **hard-fail lifespan**. See Finding 1 — highest-risk removal in P1-02. |
| R2 | `asxos/domain/models/cache.py:81-110` | **0** | `_artefact_paths()` + `_load_artefacts()`; `joblib.load()` of `_classifier.pkl` / `_regressor.pkl`. **Token-blind.** |
| R3 | `asxos/domain/models/cache.py:50-60` | **0** | Version resolution via `model_versions WHERE model=$1 AND is_active=TRUE` — **no `approved_for_allocation` predicate.** See Finding 1. |
| R4 | `asxos/domain/models/model_a.py:17-25` | 2 | `predict_with_shap` / `top_shap_factors` — the inference entry point. |
| R5 | `asxos/domain/models/train.py:20,114,149` | 2 | `train_model_a()`; LightGBM `LGBMClassifier`/`LGBMRegressor` imports. |
| R6 | `asxos/domain/models/training_config.py:105-136` | 17 | `MODEL_A_V1_5_CONFIG` / `MODEL_A_V1_6_CONFIG` recipes + `_CONFIGS_BY_VERSION`. |
| R7 | `asxos/domain/models/validation.py:2` | 1 | Retraining gates (MIN_ROC_AUC 0.65, MAX_DEGRADATION 5%, MIN_SAMPLES 1000). |
| R8 | `asxos/domain/models/metadata.py:2,20` | 2 | v1_6 self-describing artefact contract. |
| R9 | `asxos/domain/signals/feature_engine.py:22,60,96` | 4 | `MODEL_A_FEATURES` (the 22-feature contract) + `FeatureEngine`. |
| R10 | `asxos/domain/signals/loader.py:78,102,115` | 4 | Loads the price+fundamentals panel and computes Model A features. |
| R11 | `asxos/domain/signals/writer.py:39,71` | 2 | `INSERT INTO signals (...)` — **the only writer of the `signals` table**. |
| R12 | `asxos/domain/signals/thresholds.py` | **0** | `classify_batch`, the signal threshold ladder, `confidence_from_prob_up`. **Token-blind.** |
| R13 | `asxos/cli/predict.py:11,20,50` | 3 | `asx predict` — runs Model A for one date, prints SHAP. |
| R14 | `asxos/cli/model.py:11-101` + `asxos/cli/main.py:17,46` | 9 + 2 | `asx model activate\|list`, defaulting `--model model_a`. `model.py:14-101` is the **sole `is_active = TRUE` flip** in the codebase. |
| R15 | `jobs/generate_signals.py:26-27,277,283` | 5 | The daily producer: `get_cache().get("model_a")` → `predict_with_shap` → writes `model="model_a"` rows. |
| R16 | `jobs/retrain_model_a.py:1-290` | 18 | Weekly retrain; `joblib.dump()` of new artefacts. Inserts inactive, never activates. |
| R17 | `jobs/check_model_staleness.py:66,70-71` | 7 | `SELECT MAX(as_of) FROM signals WHERE model = 'model_a'`. |
| R18 | `jobs/track_signal_outcomes.py:28,44` | 1 | `_MODEL = "model_a"`; matures `signals` rows into `signal_outcomes`. |
| R19 | `models/model_a_v1_5_classifier.pkl`, `_regressor.pkl`, `_features.json`, `_metrics.json` | 1 | The tracked binary artefacts loaded by R2. **Remove after R1** — see Finding 1. |
| R20 | `scripts/alpha_eval.py:5` | 1 | Measures whether Model A's signal contains tradable short-horizon information. |
| R21 | `asxos/config.py:19,54` + `.env.example:35` | 2 + 1 | `healthcheck_url_retrain_model_a` / `HEALTHCHECK_URL_RETRAIN_MODEL_A`. |
| R22 | `render.yaml:276-296` — `asxos-generate-signals`, `schedule: "50 20 * * 0-4"` | **0** | **Token-blind.** The cron that *produces* Model A signals every weekday. See Finding 2. |
| R23 | `render.yaml:427-449` — `asxos-retrain-model-a`, `schedule: "0 16 * * 6"` | 3 | Weekly retrain cron; `buildCommand: pip install -e ".[ml]"`. |
| R24 | `render.yaml:781-800` — `asxos-check-model-staleness`, `schedule: "5 21 * * *"` | **0** | **Token-blind.** Daily Model A monitor, still declared. |
| R25 | `render.yaml:813-831` — `asxos-track-signal-outcomes`, `schedule: "0 3 * * 0"` | **0** | **Token-blind.** Weekly outcome-maturation cron, still declared. |
| R26 | `README.md:22` | 1 | "LightGBM Model A producing daily signals with inline SHAP factors" — the repo's front-door claim. |

> `render.yaml` is an **authority path**. P1-02 may draft changes to it via a reviewed PR; it may
> not edit it directly, and every change must go through `render.yaml` + `git push` +
> `make check-drift` (CLAUDE.md non-negotiable #2).

#### Test collateral — removed *with* their subjects, not independently

These follow R1-R21 mechanically. Listed for completeness; not counted as S2 sites because they
carry no independent decision.

**ML machinery (15 files, 141 lines):** `test_model_cache.py`:34 · `test_training_config.py`:24 ·
`test_retrain_dry_run_guard.py`:13 · `test_model_a_predict.py`:12 · `test_cli_predict.py`:9 ·
`test_cli_model.py`:8 · `test_retrain_wiring.py`:7 · `test_train_walk_forward.py`:7 ·
`test_signals_writer.py`:7 · `test_signals_loader.py`:6 · `test_model_artifact_contract.py`:5 ·
`test_api_main.py`:3 · `test_feature_engine.py`:2 · `test_build_target_price_basis.py`:2 ·
`test_signal_correctness_contract.py`:1

> **Three assertions inside this set are quarantine-adjacent and should be re-homed, not
> deleted:** `test_training_config.py:113-140` (`test_retrain_job_inserts_inactive_and_never_activates`,
> `test_activation_lives_only_in_explicit_cli_command`) and `test_retrain_wiring.py:75-77`
> (`test_job_never_activates`) are defence-in-depth on the activation lever. If the retrain job
> goes away they become moot — but if any future model is added, the "training never
> self-activates" invariant must be re-asserted somewhere.

**Incidental mentions (8 files, 15 lines):** `test_cli_journal.py`:4 · `test_ingestion.py`:3 ·
`test_cli_thesis.py`:2 · `test_monitor_loader_load.py`:2 · `test_unattended_guard_secperf.py`:2 ·
`test_cli_signal.py`:1 · `test_cli_macro_thesis.py`:1 · `test_holdings_security_kind.py`:1

---

### `ADAPT` — must survive, rewritten model-independently (11)

| # | Site | Tok | Consumer | Proposed destination |
|---|---|---:|---|---|
| **A1** | `asxos/domain/portfolio/build.py:191-215` | **0** | The allocator's candidate source (`FROM signals WHERE model = $1`, both branches) | A model-independent candidate source — the screening evaluator (`asxos/domain/screening/`) and/or thesis-driven targets. **Keep E1's gate above it:** the gate must outlive the signals query it currently feeds. |
| **A2** | `asxos/domain/portfolio/build.py:216-230` | **0** | Signal-emptiness + >2-day staleness hard-fails | Re-anchor the same hard-fail shape onto the replacement candidate source. Do not soften to a warning (rule #10). |
| **A3** | `asxos/brief/compose.py:242-256, 268-269` | 7 | Brief V1 `collect()` — `resolve_production_model(required=False)` | Remove the gate *call* together with the display reads it feeds (A4). **Do not remove `required=False` from E2's signature** — that overload is the R9 fix and must survive for any future display consumer. |
| **A4** | `asxos/brief/compose.py:284, 294, 372, 380` | — | `SELECT regime FROM signals`, `MAX(as_of) FROM signals`, two `FROM signals s` joins | Model-independent regime source, or drop the regime line. Closes cleanup-backlog **R6** (V1 reads `signals.regime` — a display-only leak). |
| **A5** | `asxos/domain/brief/collectors/active_theses.py:70-92` | 5 | V2 collector — same gate + `FROM signals` read | Same as A3/A4. The thesis cards themselves are already model-independent and **must keep rendering**. |
| **A6** | `asxos/brief/templates/brief.html.j2:32, 41` | 2 | "Model A: **shelved** — signal engine paused (rule #11)" copy | Once the engine is gone this is stale phrasing, not a live state. Replace with the model-independent header or delete the line. |
| **A7** | `asxos/cli/signal.py:27` | **0** | `asx signal` — `FROM signals` reader. **Token-blind.** | Remove the command, or repoint at the replacement candidate source. |
| **A8** | `asxos/cli/journal.py:43` | **0** | Decision journal enriches entries `FROM signals`. **Token-blind.** | Drop the signal enrichment; the journal is otherwise model-independent. |
| **A9** | `jobs/compute_opportunity_cost.py:47` | **0** | `FROM signals` reader; weekly cron `render.yaml:566-585`. **Token-blind.** | Re-derive from realised prices, or retire the job. Closes cleanup-backlog **R4**. |
| **A10** | `jobs/check_cron_health.py:33, 47` | 1 | Already adapted — `generate_signals` and `check_model_staleness` commented out of `_EXPECTED_DAILY` | Keep the dated comments until the crons are actually gone, then convert to a clean deletion. **This file is the evidence for Finding 2.** |
| **A11** | `.github/workflows/targeted-ml-tests.yml:46, 61` | 2 | The fast ML test lane (`tests/test_model_artifact_contract.py` et al.) | Retire the lane with the ML tests it gates. **Authority path** — draft via reviewed PR, never edit directly. |

---

## Three findings P1-02 must not discover the hard way

### Finding 1 — the model cache is NOT quarantine-gated (removal order matters)

`ModelCache.get()` (`asxos/domain/models/cache.py:50-60`) resolves the artefact version with:

```sql
SELECT version FROM model_versions WHERE model = $1 AND is_active = TRUE
```

**There is no `approved_for_allocation` predicate.** The quarantine gate exists only on the
allocator/brief path (E1/E2). Consequences:

- `asxos/api/main.py:44` warms the Model A artefact on **every API boot, quarantine or not**, and
  by rule #1 (hard-fail lifespan) **the API does not start if the `.pkl` files are missing.**
  Deleting `models/*.pkl` (R19) before removing R1 will take the API down.
  **Required order: R1 → R2/R3 → R19.**
- The lifespan currently has three hard-fail gates: DB ping (`main.py:38-39`), migration drift
  (`:41`), model warm (`:44`). Removing the third must not leave a `try/except` or a softened
  check — rules #1 and #10 still bind whatever replaces it.
- Because the cache path is ungated, it is pure `ACTIVE_REMOVE`: there is **no enforcement value
  to preserve in it**, unlike E1. This is the cleanest way to state the asymmetry — the *gate* is
  keepable, the *loader* is not.

### Finding 2 — declared schedules and monitored schedules disagree

| Source | Says |
|---|---|
| `render.yaml:276-296` | `asxos-generate-signals` runs weekdays `"50 20 * * 0-4"` — **still declared** |
| `render.yaml:781-800`, `:813-831` | `check-model-staleness` (daily), `track-signal-outcomes` (weekly) — **still declared** |
| `jobs/check_cron_health.py:33` | `generate_signals` — "**RETIRED 2026-08-08** (governor decision: Model A monitors retired with Render)" |
| `jobs/check_cron_health.py:47` | `check_model_staleness` — "**RETIRED 2026-08-08** (same decision)" |
| `.github/workflows/weekly-research.yml:9-15` | `sync_fundamentals` moved off Render because it "fed Model A's feature engine. Model A is shelved (rule #11) and its monitors are retired" |
| `docs/session-handoff-2026-08-08.md:113` | "**Render decommission remains blocked.**" |
| `docs/session-handoff-2026-08-08.md:186` | "the **still-live** Render cron fleet" |
| `git log -- render.yaml` | Last touched **2026-07-21** (`9d8dd9d`) — *before* the 2026-08-08 decision |

**The monitors were retired; the producer was not.** `render.yaml` has not been updated since
before the governor decision, so as declared, `asxos-generate-signals` still writes
`model="model_a"` rows every weekday — with its health expectation removed, so a failure *or* a
success is now equally invisible to `check_cron_health`.

This manifest **does not resolve** the contradiction: verifying live Render state is a production
probe, out of P1-01's scope. **P1-02 must run `make check-drift` first** (Render REST API,
`api.render.com/v1`, `$RENDER_API_KEY`) to establish whether these crons are live before removing
anything. If they are live, R22/R24/R25 are a live-service removal, not a config cleanup.

Rule #11 is not violated either way — it bars *using* Model A output as a decision basis, not
generating rows. But a producer running unmonitored, whose output no approved consumer reads, is
exactly the drift this manifest exists to surface.

*Related:* `docs/product/roadmap-state.md` records Render drift baselines expecting
`asxos-retrain-model-a = SUSPENDED`. A retirement makes that service **absent**, not suspended —
the drift baseline itself needs updating or `make check-drift` will report a false positive.

### Finding 3 — two governance rubrics assume the quarantine is *lifted*, not *retired*

Retirement is a third state neither rubric anticipates, and both are read on every arbi run:

- `docs/product/rubrics/arbi-roadmap-update.md` — must "keep P0 (Model A) pinned in §Blocked
  **until rule #11 lifts**."
- `docs/product/arbi-harness.md` — "Model A quarantine stays visible **until lifted**."

If Model A is *removed* rather than *cleared*, rule #11 never "lifts" and these rubrics would
keep a permanently-unsatisfiable P0 pinned. **Only James can amend these** (governance set —
arbi may draft, not edit). Flagging as a P1-05 / governor dependency, not a P1-02 blocker.

---

## `HISTORICAL_KEEP` — `docs/**`, at file granularity

**Default: every `docs/**` file matching S1 is `HISTORICAL_KEEP`.**

**Retention reason:** these are the evidence trail for the 2026-07-11 decay finding and the shelf
decision. `docs/model-a-decay-analysis-2026-07-11.md` is the *justification* for rule #11 —
destroying it leaves the standing policy unsourced, and the standing policy is what keeps capital
safe. **Line-level supersession is mission P1-05's job. Do not edit doc bodies in P1-02.**

**99 files / 524 lines**, splitting **41 LIVING / 58 HISTORICAL**.

| Subdirectory | Files | Lines |
|---|---:|---:|
| `docs/` (root) | 23 | 148 |
| `docs/product/` (root) | 27 | 144 |
| `docs/proposals/` | 12 | 81 |
| `docs/foundation/` | 8 | 73 |
| `docs/research/` | 5 | 21 |
| `docs/product/memory/` (all depths) | 10 | 31 |
| `docs/product/evals/` | 3 | 9 |
| `docs/product/rubrics/` | 4 | 6 |
| `docs/assets/` · `docs/strategy/` · `docs/discovery-runs/` · `docs/product/runbooks/` · `docs/harden/` | 7 | 11 |
| **Total** | **99** | **524** |

### LIVING (41) — `HISTORICAL_KEEP` for P1-02, but **P1-05 must update the claim**

These carry a *currently-asserted* Model A claim. P1-02 must not touch them; P1-05 owns the edits.

**Tier 1 — highest-leverage surfaces**

| File | Lines | Claim a retirement invalidates |
|---|---:|---|
| `docs/foundation/BUILD_GUIDE.md` | **40** | **Largest single surface.** Still an *executable manual for building and running Model A*: M5 feature engine, M6 "Model A loaded, predictions and SHAP", M9 `retrain_model_a.py` + `asx model activate`, migration 0005 seeding `('model_a','v1_5',…,TRUE)`, Makefile `retrain` target, Render cron + systemd timer. Header says `current`, `Last verified: 2026-07-04` — predates both the shelf and the mechanical quarantine. |
| `docs/product/roadmap-state.md` | 26 | The live queue: P1-01/P1-02 mission definitions, F4's "no Model A capital input" gate, §Blocked P0 header, Render drift baselines (see Finding 2). |
| `docs/product/target-architecture.md` | 19 | CANONICAL. §Retire scope; **rows RATIFIED 2026-08-12 (#87) bind E5-E8 as architecture**; cron table already marks `retrain_model_a` → RETIRE. (6 of 19 hits are `model_and_prompt_manifest` / `model-assisted` false positives.) |
| `docs/product/north-star.md` | 12 | Charter §1 "Model A is quarantined … do NOT recommend acting on Model A output". |
| `docs/README.md` | 8 | Source-of-truth index: routes "Model A / alpha evidence"; the STOP row "Act on a Model A signal → rule #11"; calls rule #11 *standing*, not retired. |
| `docs/product/cleanup-backlog.md` | 5 | Open items **R4** (suppress the `compute_opportunity_cost` Model A read → A9) and **R6** (V1 reads `signals.regime` at `compose.py` → A4) that this retirement closes. |
| `docs/product/risk-register.md` | 4 | R1, R8 (quarantine is MECHANICAL), R9. R8 carries a drafted-not-built follow-up that E4 has since landed. |
| `docs/next-session-backlog.md` | 4 | Stale claim that migration 0032 grandfathered `model_a/v1_5` — revoked 2026-07-11 per R8. |
| `docs/product/runbooks/claude-execute.md` | 2 | Harness guard wording: "no Model A in any decision". |

**Tier 2 — standing governance / operating contracts (all `Status: current`)**
`arbi-harness.md`:8 · `arbi-permission-model.md`:8 · `portfolio-policy.md`:5 ·
`arbi-autonomy-loop.md`:4 · `arbi-authority.md`:3 · `arbi-evals.md`:3 ·
`portfolio-manager-charter.md`:3 · `arbi-scorecard.md`:2 · `arbi-managed-agent-spec.md`:2 ·
`recommendation-schema.md`:2 · `data-contracts.md`:2 · `dark-launch-exit-plan.md`:2 ·
`arbi-constitution.md`:1 · `arbi-promotion-gate.md`:1 · `security-perf-mission-loop.md`:1
*(all under `docs/product/`)*

> `data-contracts.md` defines `signals` as "Model A output" with the allocator hard-fail as its
> failure symptom, and `signal_outcomes` as the decay/calibration base — **both consumers change.**

**Tier 3 — graders, fixtures, promoted memory (read on every arbi run)**
`docs/product/memory/approved-lessons.md`:9 (**L14** is the standing verdict) ·
`docs/product/evals/fixture-001-model-a-quarantined.md`:7 (the fixture *is* the quarantine test;
the filename encodes `model-a`) · `docs/product/memory/playbooks/product-reality-sweep.md`:3 ·
`docs/product/rubrics/arbi-daily-brief.md`:2 · `docs/product/rubrics/arbi-roadmap-update.md`:2
(**Finding 3**) · `docs/product/rubrics/arbi-safety-boundary.md`:1 ·
`docs/product/rubrics/arbi-dream-promotion.md`:1 · `docs/product/evals/README.md`:1 ·
`docs/product/evals/fixture-005-capital-impacting-request.md`:1 ·
`docs/product/memory/authority-lessons.md`:1 ·
`docs/product/memory/rejected-candidates.md`:1 (anti-memory **RC1** "Model A blocks the whole
product" — must not be re-litigated by the retirement)

**Tier 4 — append-only living ledgers (append; never rewrite)**
`docs/product/decision-log.md`:5 · `docs/product/portfolio-outcome-ledger.md`:3 ·
`docs/product/arbi-run-ledger.md`:1 · `docs/product/product-health-scorecard.md`:9
(regenerated by `scripts/product_health.py`; currently FAILs on `retrain_model_a` and calls it
"correctly dormant under rule #11" — **retiring the job changes the grading target**, so
`scripts/product_health.py:77` must change with it)

**Flagged**
`docs/research/alpha-research-audit.md`:9 — undated filename, header `Status: current`, cited by
`docs/README.md:43`. Content is historical; the *status header and index linkage* are live. ·
`docs/backlog-test-coverage.md`:1 — LIVING doc, but the sole match is the `model_activate` false
positive; nothing to update.

### HISTORICAL (58) — preserve as-is, no edits in any mission

**`docs/` root (20):** `asxos-live-readiness-audit-2026-07-04.md`:12 · `audit-2026-06-27.md`:1 ·
`db-shared-project-audit-2026-06-28.md`:2 · `executable-roadmap-2026-07-04.md`:12 ·
`live-readiness-audit-plan-2026-07-04.md`:19 · `market-trends-report-2026-08-05.md`:2 ·
`model-a-audit-and-extension-plan-2026-07-04.md`:17 · `model-a-decay-analysis-2026-07-10.md`:4 ·
**`model-a-decay-analysis-2026-07-11.md`:13 — the authoritative evidence for rule #11; preserve
verbatim** · `pr2a-supabase-ro-provisioning-plan-2026-07-05.md`:2 ·
`session-handoff-2026-07-04.md`:9 · `-07-13`:4 · `-07-16`:10 · `-07-18`:3 · `-07-21`:2 ·
`-07-24`:3 · `-08-08`:4 · `-08-11`:5 · `-08-12`:7 · `session-review-2026-08-05.md`:4

**`docs/proposals/` (12, all dated):**
`asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`:22 (**largest historical
hit — likely the source packet defining P1-01/P1-02; read-only reference**) ·
`governance-first-architecture-2026-06-30.md`:13 ·
`arbi-outcome-programme-convergence-sprint-2026-08-08.md`:9 ·
`multi-instrument-expansion-2026-07-11.md`:8 · `thesis-coverage-framework-2026-07-11.md`:6 ·
`personal-advice-firewall-amendment-2026-07-18.md`:6 ·
`asxos-research-to-decision-live-slice-brief-2026-08-10.md`:5 ·
`broker-report-rubric-2026-07-18.md`:4 · `portfolio-team-visibility-2026-07-12.md`:4 ·
`macro-workflow-automation-2026-07-21.md`:2 · `arbi-dream-automation-2026-07-15.md`:1 ·
`macro-thesis-learning-loop-2026-07-21.md`:1

**`docs/foundation/` (7):** `phase-4-architecture-system-architect.md`:9 (explicitly
`Status: historical / superseded`) · `phase-5-milestones.md`:8 · `phase-1-audit.md`:5 ·
`phase-c-calendar.md`:4 · `phase-2-survives-the-fire.md`:3 · `phase-3-product-redefinition.md`:3 ·
`phase-b-failure-postmortem.md`:1

**`docs/research/` (4):** `claude-fundamentals-audit-handoff-2026-07-04.md`:5 ·
`repo-navigation-audit-and-plan-prompt-2026-07-04.md`:4 · `build-readiness-audit.md`:2 ·
`alpha-signal-verification.md`:1

**`docs/product/` root (3):** **`ml-engine-shelf-2026-07-11.md`:8 — the shelve decision record;
cited as authoritative, preserve** · `arbi-full-auto-activation-2026-07-15.md`:3 ·
`session-handoff-2026-07-17.md`:2

**`docs/product/memory/` non-living (6):** `dream-candidates/archive/2026-07-15-dream.md`:8 ·
`dream-candidates/2026-08-05-dream.md`:3 · `dream-candidates/2026-07-21-dream.md`:1 ·
`working/2026-07-11-pmreview-hubs-cba.md`:3 · `working/2026-07-11-branch-closeout.md`:1 ·
`working/2026-07-11-etf-phase1-build.md`:1

**Other (6):** `docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md`:2 ·
`docs/strategy/M-THESIS-0_FEATURE_PLAN.md`:1 (false positive — `model_app`) ·
`docs/discovery-runs/2026-07-16-energy-dryrun.md`:1 ·
`docs/discovery-runs/2026-07-22-workflow-automation-build.md`:1 ·
`docs/harden/position-monitor-harden.md`:1 · `docs/assets/market-trends-report-2026-08-05.html`:3
(generated artifact)

---

## `.claude/` — authority tree, 27 files / 79 lines

Not classified into the five categories: **arbi may not edit `.claude/**` at all**, only draft
changes for James. Recorded here so P1-02 knows the surface exists and does not attempt it.

Largest holders: `.claude/agents/arbi.md`:14 · `.claude/commands/feature-add.md`:11 ·
`.claude/commands/model-experiment.md`:6 · `.claude/rules/ml-conventions.md`:6 ·
`.claude/agents/README.md`:4 · `.claude/commands/arbi-run.md`:3 ·
`.claude/commands/signal-pipeline.md`:3 · `.claude/agents/portfolio-coherence-reviewer.md`:3 ·
`.claude/agents/thesis-coherence-guard.md`:3 · `.claude/rules/portfolio-conventions.md`:3 ·
plus 17 files at 1-2 each.

`.claude/rules/ml-conventions.md` is the ML pipeline's rule file and would be retired wholesale.
`.claude/agents/thesis-coherence-guard.md` describes an agent **whose entire purpose is reading
Model A SHAP** — that agent has no function after retirement.
`CLAUDE.md`:7 (root, authority) carries rule #11 itself and the Model A read-first pointer.

---

## Proposed CI assertion design (specified, NOT implemented)

**Goal:** fail the build when a *new* active Model A reference appears outside a reviewed
historical allowlist.

### Mechanism

Two tracked files plus one CI step.

**1. `scripts/check_model_a_references.sh`** — the S1 command, frozen.

- **Greps:** `git grep -lE '<BOUNDARY_PATTERN>' HEAD` where `<BOUNDARY_PATTERN>` is the
  boundary-aware pattern from the precision caveat above — *not* the loose four-token pattern.
  Using the loose pattern would fail the build on `model_and_prompt_manifest`, which is the
  decision engine's Model A **ban**. Getting this backwards is the single most likely way to
  build an assertion that fights the quarantine instead of protecting it.
- **Excludes:** every path (or path prefix) listed in the allowlist file. Nothing else — no
  `--exclude-dir` list, because `git grep HEAD` already sees tracked files only, which is what
  keeps `.claude/worktrees/**` out.
- **Exits** non-zero, printing each file that matched but is not allowlisted, plus the line
  numbers, plus a pointer to this manifest.

**2. `docs/product/model-a-allowlist.txt`** — the reviewed historical allowlist (contents below).
One path or path-prefix per line; `#` comments permitted. Changing it is a reviewed diff, and
that is the entire point: a new Model A reference can still land, but only by someone explicitly
adding the file to the allowlist in a PR where a human sees it.

**3. CI step** — a job in `.github/workflows/full-check.yml`, the existing gate on PRs to `main`
and `claude/**` pushes. Runs *before* `make check`; needs no Python env, no DB, no secrets, so it
fails in seconds. **Not** in `targeted-ml-tests.yml`, which is itself scheduled for retirement
(A11).

### What it catches and what it does not

**Catches:** a new file reintroducing a Model A token; a Model A token added to a currently-clean
file (e.g. someone re-adding `get_cache().get("model_a")` to `api/main.py`).

**Does not catch:** token-blind reintroduction — a new `FROM signals` reader, a new
`joblib.load()`, a new `model_versions` consumer. **Six of this manifest's most important sites
would be invisible to it.** No grep closes that gap, which is why the companion assertions below
matter more than the grep does.

### Companion assertions (these close the real gap)

- **Enforcement-presence test** — a pytest asserting the enforcement still exists:
  `resolve_production_model` is importable; `ModelGateDormant` is a `RuntimeError` subclass;
  **`build.py` still calls the gate at `required=True`** (source-inspect, in the style of the
  existing `tests/test_thesis_discipline.py:302-336`); `JobMonitor` still maps `ModelGateDormant`
  → `'blocked'`. This fails loudly if P1-02 deletes the enforcer — which the grep assertion
  structurally cannot do. `test_production_gate.py` and `test_job_monitor.py` already cover most
  of it; **the gap is an explicit assertion that `build.py` calls the gate.**
- **Signals-writer singleton test** — assert `asxos/domain/signals/writer.py` is the only
  `INSERT INTO signals` site (or, post-retirement, that there are none), so a new writer cannot
  appear silently.
- **Decision-engine coverage** — `tests/test_decision_engine_prototype.py` is the *sole* test of
  `_MODEL_A_RE`, `UNIVERSAL_CONSTRAINTS`, and `verify_content_hash`. A single-point-of-failure
  worth splitting, or at minimum marking non-retirable.

---

## Proposed historical allowlist

Contents of `docs/product/model-a-allowlist.txt`. Everything else matching the boundary-aware
pattern becomes a build failure.

```
# ============================================================
# Model A reference allowlist
# Rationale for every entry: docs/product/model-a-reference-manifest.md
# Adding a line here is a deliberate, reviewed act. Do not add
# a path to silence a build failure without reading the manifest.
# ============================================================

# --- Evidence for rule #11: the decay finding and the shelf decision ---
docs/model-a-decay-analysis-2026-07-11.md
docs/model-a-decay-analysis-2026-07-10.md
docs/product/ml-engine-shelf-2026-07-11.md
docs/product/model-a-reference-manifest.md    # this file
docs/product/model-a-allowlist.txt            # the allowlist names the token

# --- ENFORCEMENT: Model A tokens whose PURPOSE is to ban Model A. ---
# --- Removing any of these weakens rule #11. See manifest E1-E11.  ---
asxos/domain/models/production_gate.py
asxos/domain/decision_engine/types.py
asxos/domain/theses/schemas.py
asxos/domain/theses/discipline.py
asxos/domain/screening/types.py
asxos/jobs/utils/job_monitor.py

# --- ENFORCEMENT TESTS. See manifest T1-T10. ---
tests/test_production_gate.py
tests/test_portfolio_build.py
tests/test_job_monitor.py
tests/test_decision_engine_prototype.py
tests/test_screening_evaluator.py
tests/test_thesis_discipline.py
tests/test_thesis_proposal_schema.py
tests/test_thesis_service.py
tests/test_brief_compose.py
tests/test_active_theses_signals.py

# --- Applied migrations: never edited, by rule. ---
migrations/

# --- Authority tree: arbi may draft but never edit. ---
CLAUDE.md
.claude/
.github/

# --- Dated history: append-only or frozen. P1-05 owns any line edits. ---
docs/proposals/
docs/foundation/
docs/research/
docs/discovery-runs/
docs/harden/
docs/strategy/
docs/assets/
docs/product/memory/
docs/product/evals/
docs/product/rubrics/
docs/session-handoff-*.md
docs/session-review-*.md
docs/audit-*.md
docs/*-audit-*.md
docs/executable-roadmap-2026-07-04.md
docs/product/arbi-full-auto-activation-2026-07-15.md
docs/product/session-handoff-2026-07-17.md

# --- Living governance docs. Listed so the assertion does not fire ---
# --- during the P1-05 window while their prose is still being     ---
# --- corrected. REVIEW THIS BLOCK once P1-05 completes: several    ---
# --- should drop off once the Model A prose is gone.               ---
docs/README.md
docs/next-session-backlog.md
docs/backlog-test-coverage.md
docs/foundation/BUILD_GUIDE.md
docs/product/roadmap-state.md
docs/product/target-architecture.md
docs/product/north-star.md
docs/product/risk-register.md
docs/product/cleanup-backlog.md
docs/product/decision-log.md
docs/product/portfolio-outcome-ledger.md
docs/product/arbi-run-ledger.md
docs/product/product-health-scorecard.md
docs/product/portfolio-policy.md
docs/product/portfolio-manager-charter.md
docs/product/recommendation-schema.md
docs/product/data-contracts.md
docs/product/dark-launch-exit-plan.md
docs/product/security-perf-mission-loop.md
docs/product/arbi-constitution.md
docs/product/arbi-authority.md
docs/product/arbi-permission-model.md
docs/product/arbi-autonomy-loop.md
docs/product/arbi-harness.md
docs/product/arbi-scorecard.md
docs/product/arbi-promotion-gate.md
docs/product/arbi-managed-agent-spec.md
docs/product/arbi-evals.md
docs/product/runbooks/
```

**Design note on granularity.** Directory prefixes are used only where the whole tree is
append-only history (`migrations/`, `docs/proposals/`) or an authority path arbi cannot edit
anyway (`.claude/`, `.github/`). The **file-level entries are the ones that carry weight** — the
enforcement code and its tests. A future reviewer should be suspicious of any PR that converts a
file-level entry into a directory prefix.

**Expected steady state.** Immediately after P1-02/03/04, the allowlist above should cover roughly
all remaining matches. After P1-05 corrects the living-doc prose, the final "living governance
docs" block should shrink substantially — and each removal from the allowlist is a small,
verifiable win.

---

## Limits of this manifest

Stated plainly, because a manifest that oversells its coverage is worse than none.

1. **S2 is a static graph closure, not a runtime trace.** It follows imports and literal SQL
   strings. It cannot see dynamic dispatch, string-built SQL, or a Model A read arriving through
   an LLM agent prompt. Agents under `.claude/agents/` that query Supabase directly —
   `thesis-coherence-guard` reads SHAP *by design* — are governed by prompt text, not code.
   `.claude/` is an authority path this mission may not edit, and it was inventoried but **not
   audited for runtime effect**.
2. **No live-state verification.** No DB query, no Render API call, no workflow-run inspection was
   performed (mission constraint). Every claim about what *runs* is read from `render.yaml`,
   `.github/workflows/**`, and dated docs — and **Finding 2 shows those sources disagree with each
   other.** P1-02 must establish live state itself via `make check-drift`.
3. **The `signals` table's contents are out of scope.** This manifest classifies *code that reads
   or writes* `signals`; it says nothing about whether the ~19,032 matured `signal_outcomes` rows
   should be retained, archived, or dropped. That is a separate decision with its own evidence
   value — the decay analysis that justifies rule #11 was computed from exactly those rows, so
   dropping them would destroy the ability to re-verify the finding.
4. **`docs/**` is classified at file granularity only**, per mission scope. The LIVING/HISTORICAL
   split (41/58) is a judgement from filenames, paths, and status headers — not a full read of
   all 99 files. Which *lines* inside living docs assert a now-false claim is P1-05's work.
5. **Counts are frozen at one SHA** and will drift immediately. Re-run the committed commands
   rather than trusting the tables. Every number here is reproducible at
   `fad62159f5d6585588d47bbac763687da55f0002`.
6. **The five categories are a judgement, not a proof.** `ENFORCEMENT_KEEP` in particular is an
   *argument* that deleting a site would weaken rule #11 — reviewers should challenge each row
   rather than accept the label. **E10 and E11 are the weakest:** they are module contracts
   expressed in docstrings, enforceable only by review (E10 has a real test, T6; E11 has none
   directly on the module contract).
7. **No test was executed and no code was changed.** `make check` was not run; this mission made
   no code change to verify. The only file created is this manifest.
8. **S2 is not proven complete.** It terminates on the import/call graph from the declared seeds.
   A Model A dependency reachable only from a seed *not* in the declared list would be missed —
   for example, a consumer of `signal_outcomes` (rather than `signals`), or a reader of the
   `shap_factors` JSONB column through a path that names neither. The `prob_up` probe (29
   non-S1 files) is the best available upper bound on what a wider seed set might add.
