# Model A reference manifest — the retirement contract

**Status:** current · frozen contract for mission P1-02 · **reconciled 2026-08-13 by mission
P1-05** against the merged P1-02/03/04 tree — see
[P1-05 reconciliation](#p1-05-reconciliation--2026-08-13)
**Scope:** every Model A reference in the repo, classified so that P1-02 (remove runtime/API/job
dependencies) can proceed without silently disarming rule #11
**Last verified:** 2026-08-13 against pinned base SHA `fad62159f5d6585588d47bbac763687da55f0002`
(`origin/main`, observed 2026-08-12T21:29:56Z)
**Re-verified:** 2026-08-13 by mission P1-05 against
`6327a61793927b078d69460562477a04751257ae` (`origin/main`, after PR #100 `P1-02`, #101 `P1-03`,
#102 `SB0-01`, #103 `P1-04`, #104 `P2-01`). **Every `ENFORCEMENT_KEEP` citation was re-checked
line by line**; corrections are marked `CORRECTION (P1-05 reconciliation, 2026-08-13)` in place.
**Produced by:** mission P1-01 — exploration + contract-freeze. **No retirement edits were made;
this file is the only file the mission created or changed.**
**Challenged:** 2026-08-12 by an independent `security-engineer` review. **Seven corrections plus
one framing softening were applied in place**, marked `CORRECTION (independent challenge,
2026-08-12)` throughout. See
[Independent challenge](#independent-challenge--security-engineer-review-2026-08-12) for the
verification record and what the review confirmed unchanged.
**Owner:** arbi maintains; James governs the retirement decision
**Superseded by:** N/A as a whole. Two *sections* are superseded: **Finding 2's `make check-drift`
remedy** (by `docs/product/scheduler-inventory-2026-08-13.md`, mission P1-03) and **the S1 counts**
(now dated historical measurements — see the S1 section).

---

## P1-05 reconciliation — 2026-08-13

> **Read this before trusting any `file:line` citation below.** Missions P1-02 (#100) and
> P1-04 (#103) moved code. This section is the verification record; the corrected citations are
> applied inline in the rows themselves.

### What was re-verified, and the result

| Row | Cited site | Result at `6327a61` |
|---|---|---|
| **E1** | `build.py:184-189` | **MOVED → `:209-214`.** Corrected in all four places it appears. The block itself is byte-identical: P1-04 deliberately left it untouched and added a `DO NOT DELETE` comment above it naming this manifest row. |
| **E2** | `production_gate.py:47-87` | **Unchanged** — `:47` is still `def resolve_production_model`; the file is exactly 87 lines. |
| **E3** | `production_gate.py:20-34` | **Unchanged** — `:20` is still `class ModelGateDormant(RuntimeError):`; its docstring closes at `:34`. |
| **E4** | `job_monitor.py:124-134` | **Unchanged** — `:131-132` still map `ModelGateDormant` → `'blocked'`. |
| **E5** | `decision_engine/types.py:56-62` | **Unchanged** — `_MODEL_A_RE` still opens at `:56`. |
| **E6** | `decision_engine/types.py:524-528` | **Unchanged** — the `quarantined from the decision basis` raise is still `:528`. |
| **E7** | `decision_engine/types.py:45-53` | **Unchanged** — `UNIVERSAL_CONSTRAINTS` at `:45`, `"model_a_quarantine"` at `:48`. |
| **E8** | `decision_engine/types.py:631-635` | **Unchanged** — the exactly-once/blocking/pass check still at `:634-635`. |
| **E9** | `theses/schemas.py:216,227,263,338,380,388` | **Unchanged** — file untouched. (`:216` carries `Model A`, not `monitor_only`, which is why a `monitor_only`-only grep appears to miss it. It is correct as cited.) |
| **E10** | `theses/discipline.py:15-24` | **Unchanged.** |
| **E11** | `screening/types.py:10` | **Unchanged.** |
| **E12** | `decision_engine/demo.py:256-261, 492-497` | **Unchanged.** |
| **E13** | `scripts/alpha_eval.py:33,93` | **Unchanged.** |
| **E14** | `research/alpha_loader.py:32-61, :24, :69` | **Unchanged.** |
| **E15** | `research/alpha_eval.py` | **Unchanged.** |
| **T1** | `test_production_gate.py:33-40, 42-49, 52-62` | **Unchanged.** |
| **T2** | `test_portfolio_build.py:64-67, 70-83` | **MOVED and EXTENDED** — see the corrected T2 row. |
| **T3** | `test_job_monitor.py:23, 101, 112-113` | **Unchanged.** |
| **T4** | `test_decision_engine_prototype.py:357-378, …` | **Unchanged.** |
| **T5** | `test_screening_evaluator.py:115-133` | **Unchanged.** |
| **T6** | `test_thesis_discipline.py:302-336` | **Unchanged.** |
| **T7** | `test_thesis_proposal_schema.py:126-137, 243-256` | **Unchanged.** |
| **T8** | `test_thesis_service.py:938-951` | **Unchanged.** |
| **T9** | `test_brief_compose.py:548-578, 582-607, 139-166, 644` | **SUBJECT REMOVED; REWRITTEN by P1-04** — see the corrected T9 row. |
| **T10** | `test_active_theses_signals.py:105-115, 117-129, 49` | **SUBJECT REMOVED; REWRITTEN by P1-04** — see the corrected T10 row. |

**Method.** `git diff --stat fad6215 HEAD -- asxos/ tests/ jobs/ scripts/ models/` produced the
changed-file set; every `ENFORCEMENT_KEEP` file *outside* that set is unchanged by construction
and its citations hold without re-reading. The four that were *inside* it (`build.py`,
`test_portfolio_build.py`, `test_brief_compose.py`, `test_active_theses_signals.py`) were read
directly and re-cited. **13 of 15 code rows and 8 of 10 test rows needed no correction.**

### The structural finding P1-05 wants on the record

**T9 and T10 did not merely move — their subject stopped existing.** Both asserted a
*conditional* property: *under a quarantine (0 or >1 approved models), the display path skips its
Model A surface.* P1-04 removed the display path's model gate outright, so "what does it do under
a quarantine" is no longer a question that can be asked of that code. Their replacements assert
the **unconditional** property — the composer and the collector issue **no** `model_versions`
query and **no** `signals` query in *any* gate state — which is strictly stronger and, unlike the
original, cannot be satisfied by a gate that is still present but mis-wired.

That is the right direction of travel, and it carries a documentation consequence worth naming:
**a manifest row whose *assertion* was replaced cannot be reconciled by editing a line number.**
Both rows are rewritten below with the superseded citation retained in strike, so a reader
working from an older copy sees the change rather than the original.

### Cross-mission supersessions

- **Finding 2's remedy is void.** It instructs P1-02 to run `make check-drift` before removing
  R22/R24/R25. James ruled on 2026-08-12 that **Render was deleted** and explicitly forbade
  probing it; mission P1-03 then answered Finding 2's question *without* the probe. See the
  corrected Finding 2.
- **Finding 3 is still OPEN** and is now formally P1-05's hand-off to James — see the corrected
  Finding 3.
- **The S1 counts are dated.** They are a measurement at `fad6215`, not a current state; the
  corpus has since grown. Re-derived at `6327a61` in the S1 section.
- **The denominator has confirmed false negatives.** SB0-01 (#102) found two capital-adjacent
  docs asserting a live Model A path with **zero Model A tokens**. Recorded under
  [Token-blind documentation](#token-blind-documentation--the-denominators-false-negatives).

---

## Why this document exists

Rule #11's **mechanical enforcement point contains zero Model A tokens.**

`asxos/domain/portfolio/build.py:209-214` is the code that actually stops Model A from reaching
real capital.

> **CORRECTION (P1-05 reconciliation, 2026-08-13).** This citation read `build.py:184-189` — the
> location at `fad6215`. Mission P1-04 (#103) removed the `FROM signals` candidate query that sat
> immediately below the gate and replaced it with a call into
> `asxos/domain/portfolio/candidates.py`, shifting the gate down 25 lines. **The gate block itself
> is byte-identical** — P1-04 left it deliberately untouched and added a `DO NOT DELETE` comment
> above it that names this manifest row. A stale citation on *this* row is the worst possible
> staleness in this document, since it is the row every other mission is told to protect. It queries `model_versions WHERE is_active = TRUE AND approved_for_allocation =
TRUE` and passes the result to `resolve_production_model()`, which raises `ModelGateDormant` on
zero approved rows. Because `approved_for_allocation` was revoked for `model_a`/`v1_5` on
2026-07-11, that query returns **0 rows** and the allocator **refuses to run**. That is the
quarantine, in code.

A `git grep` for `model_a|Model A|MODEL_A|model-a` returns **0 hits in `build.py`** and **2 hits
in `tests/test_portfolio_build.py`**. A token-driven retirement would therefore delete the *test*
and keep the *enforcer* — or, worse, delete the enforcer as "Model A plumbing" and leave rule #11
with no teeth and no failing test to announce it.

That is not a hypothetical edge case. **Seven of the most load-bearing sites in this manifest are
completely invisible to the token search**, including the enforcer above, the artefact loader, the
signal threshold ladder, the weekday cron that still produces Model A signals, and the single
`import` line that keeps every `asx` command runnable without `joblib`.

> **CORRECTION (independent challenge, 2026-08-12).** This paragraph said *six*. The seventh is
> `asxos/cli/main.py:21` — see [the token-blind table](#the-seven-token-blind-sites-s1-cannot-see-these)
> and Finding 4.

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

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — every count in this section is a DATED
> HISTORICAL MEASUREMENT, not current state.** They are correct **at `fad6215` only** and are
> retained as the frozen baseline the CI assertion was specified against. Re-derived at
> `6327a61793927b078d69460562477a04751257ae` (`origin/main`, post-P1-02/03/04):
>
> | Pattern | At `fad6215` (frozen baseline) | At `6327a61` (P1-05 re-derivation) | Δ |
> |---|---:|---:|---:|
> | Loose — files | 207 | **210** | **+3** |
> | Loose — lines | 989 | **1,166** | **+177** |
> | Boundary-aware — files | 203 | **207** | **+4** |
> | Boundary-aware — lines | 969 | **1,143** | **+174** |
>
> **The count went UP while the retirement was executing, and that is not a regression.** P1-02
> deleted seven Model-A-consuming modules and three jobs, yet the corpus grew — because
> `P1-01`…`P1-05` and `SB0-01` *themselves* wrote ~2,800 lines of new prose whose subject is
> Model A: this manifest (1,074 lines), `doc-truth-map-2026-08-13.md`,
> `scheduler-inventory-2026-08-13.md`, and `finance-capability-matrix-2026-08-13.md`. Per-area,
> `docs/` went 99 files / 524 lines → **106 files / 767 lines** while `asxos/` went 26 → **25
> files** and `jobs/` went 6 → **3 files**.
>
> **The consequence for the CI assertion is direct and was not anticipated by the original
> design.** A tripwire whose trip condition is "the token count rose" would have fired on the
> retirement's own paperwork. The assertion must be **allowlist-difference**-based (a *new
> unallowlisted file* appeared), never count-based — and the allowlist must cover the retirement's
> own artifacts. `docs/product/` is **not** a directory prefix in the drafted allowlist, so all
> four new documents above are currently unallowlisted survivors, on top of the 56 the independent
> challenge already measured. See [Allowlist completeness](#allowlist-completeness--measured-not-estimated).

### Why not filesystem grep

| Method | Files | Lines |
|---|---:|---:|
| `git grep` (tracked only) — **the declared S1** | 207 | 989 |
| `grep -rI .` (working tree) | 600 | 2,764 |
| — of which under `.claude/worktrees/**` (untracked) | — | 1,773 |

Filesystem grep inflates the count ~2.8x by re-counting agent worktree checkouts of the same
repo. Any count quoted from `grep -r` is not reproducible and must not be used.

### Per-area breakdown

**At `fad6215` (frozen baseline) · with the P1-05 re-derivation at `6327a61` alongside.**

| Area | Files @`fad6215` | Lines @`fad6215` | Files @`6327a61` | Lines @`6327a61` |
|---|---:|---:|---:|---:|
| `docs/` | 99 | 524 | **106** | **767** |
| `tests/` | 32 | 217 | 32 | **164** |
| `asxos/` | 26 | 99 | **25** | 99 |
| `.claude/` | 27 | 79 | 27 | 79 |
| `jobs/` | 6 | 33 | **3** | **20** |
| `migrations/` | 7 | 17 | 7 | 17 |
| root (`.env.example`, `CLAUDE.md`, `README.md`, `render.yaml`) | 4 | 13 | 4 | 13 |
| `.github/` | 3 | 4 | 3 | 4 |
| `scripts/` | 2 | 2 | 2 | 2 |
| `models/` | 1 | 1 | 1 | 1 |
| **Total** | **207** | **989** | **210** | **1,166** |

> **Reading the deltas (P1-05, 2026-08-13).** `jobs/` 6→3 and `asxos/` 26→25 are P1-02's
> removals landing. `tests/` holds at 32 files but drops 53 lines: P1-02/04 deleted ML test
> files while T9/T10's rewrites *added* model-independence assertions in the same files.
> `docs/` +7 files / +243 lines is the retirement programme documenting itself. **The
> `docs/` growth is the only line in this table that is not evidence of progress**, and it is
> why the counts must not be read as a health metric.

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

**S2 = 65 cited sites.** This is above the 15-40 the mission anticipated, and the overshoot is
itself a finding: the quarantine is expressed in **one live enforcement layer plus three forward
contracts**. The live layer is the allocator gate and its operational surround (E1/E2/E4) — the
only path that gates a real capital decision today. The decision-engine manifest rejection, the
thesis-schema `monitor_only` guard, and the screening field whitelist are contracts that bind
*future* paths: each has its own tests, each is correctly `KEEP`, and none of them gates a
production decision at this SHA. Enforcement *tests* are counted as sites because deleting them
is the silent-weakening path this manifest exists to block.

> **CORRECTION (independent challenge, 2026-08-12).** This paragraph claimed **four independent
> enforcement layers**. That overstates live coverage. `asxos/api/main.py:55` mounts only
> `health_router`; the decision engine is reachable *only* from `asxos/prototype/app.py`
> (`make decision-demo`, port 8790) and its tests. The decision-engine constraints (E5-E8) are
> ratified architecture (`docs/product/target-architecture.md`, PR #87) and must be kept — but
> they are a **forward contract**, not a live gate. Reading them as a live layer invites the
> inverse mistake too: treating the allocator gate as "one of four" and therefore individually
> less critical. It is not one of four. **It is the one.**

| Category | Sites |
|---|---:|
| `ENFORCEMENT_KEEP` | 25 (15 code + 10 tests) |
| `ACTIVE_REMOVE` | 26 |
| `ADAPT` | 11 |
| `MIGRATION_KEEP` | 3 |
| `HISTORICAL_KEEP` | 0 in S2 — `docs/**` is classified at file granularity below |
| **Total** | **65** |

> **CORRECTION (independent challenge, 2026-08-12) — counts restated.** Was 61 sites
> (21 `ENFORCEMENT_KEEP` / 26 `ACTIVE_REMOVE`). Four sites were added and one reclassified:
> **E12** `asxos/domain/decision_engine/demo.py` (added — a fifth inverse-polarity ban the
> original manifest missed entirely); **E13** `scripts/alpha_eval.py` (**reclassified** from
> `ACTIVE_REMOVE` R20); **E14** `asxos/domain/research/alpha_loader.py` and **E15**
> `asxos/domain/research/alpha_eval.py` (both added); **R13b** `asxos/cli/main.py:21` (added —
> the seventh token-blind site). R20 is retired as an entry.

### The seven token-blind sites (S1 cannot see these)

| Site | Category | Why it matters | Status @`6327a61` |
|---|---|---|---|
| `asxos/domain/portfolio/build.py:209-214` (was `:184-189`) | **ENFORCEMENT_KEEP** | **The rule #11 enforcer.** | **KEPT, moved** (P1-05) |
| `asxos/domain/models/cache.py` | ACTIVE_REMOVE | The joblib artefact loader; also the *ungated* version resolver. | **REMOVED** by P1-02 |
| `asxos/domain/signals/thresholds.py` | ACTIVE_REMOVE | The signal threshold ladder / `classify_batch`. | **STILL PRESENT** — see the ACTIVE_REMOVE status column |
| `render.yaml:276-296` (`asxos-generate-signals`) | ACTIVE_REMOVE | The weekday cron that **produces** Model A signals. | Declared-but-dead; disposed by P1-03 |
| `asxos/cli/main.py:21` — `from asxos.cli.predict import predict` | ACTIVE_REMOVE (with R13) | **Added 2026-08-12.** Zero Model A tokens. Import-time chain into `joblib`; **the whole `asx` CLI dies if the `[ml]` extra goes first.** See Finding 4. | **REMOVED** by P1-02 |
| `asxos/cli/signal.py:27`, `asxos/cli/journal.py:43`, `jobs/compute_opportunity_cost.py:47` | ADAPT | Three `FROM signals` readers. | **ALL THREE STILL READ `FROM signals`** |
| `tests/test_job_monitor.py:23,101,112` | **ENFORCEMENT_KEEP** | Pins `ModelGateDormant` → `'blocked'`. | **KEPT, unchanged** (P1-05) |

> **CORRECTION (independent challenge, 2026-08-12).** This table listed six sites. The seventh
> (`asxos/cli/main.py:21`) was missed because R14 cites `asxos/cli/main.py:17,46` — the `model_app`
> lines, which this manifest *itself* documents as an over-match of the S1 pattern. The token
> search found the noisy lines in that file and the manifest recorded those; the silent,
> load-bearing line two rows below them has no token at all.

---

### `ENFORCEMENT_KEEP` — code (15)

> Deleting any row here weakens rule #11. None of it is kept for sentiment or history.

| # | Site | Tok | What it enforces | What breaks if removed |
|---|---|---:|---|---|
| **E1** | `asxos/domain/portfolio/build.py:209-214` ~~`:184-189`~~ | **0** | The allocator's `model_versions WHERE is_active AND approved_for_allocation` query + `resolve_production_model(model_rows)` at `required=True` | **Rule #11 loses its teeth.** This is the single point where a revoked approval becomes a refusal to allocate. Delete it and the allocator runs against whatever candidate source replaces signals with no approval gate at all. |
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
| **E12** | `asxos/domain/decision_engine/demo.py:256-261, 492-497` | 4 | **Inverse-polarity reference — added 2026-08-12.** Two `ConstraintResult(name="model_a_quarantine", status="pass", blocking=True, …)` constructions — the exact constraint E8 requires present exactly once, blocking and passing | **See the E12 failure scenario below.** A token sweep deletes both blocks; `build_demo_brief()` then raises and the error points at E8 — so the cheapest fix is to delete E7 *and* E8. |
| **E13** | `scripts/alpha_eval.py:33,93` | 1 | **Reclassified from `ACTIVE_REMOVE` R20 on 2026-08-12.** Rule #11's *exit instrument* — the CLI that runs `alpha_eval.evaluate()` over the decay panel | Rule #11's literal exit condition ("a new model version passes a pre-registered decay bar") becomes unmeasurable. See the E13-E15 note below. |
| **E14** | `asxos/domain/research/alpha_loader.py:32-61` (`_PANEL_SQL`), `:24` (`HORIZONS`), `:69` (`load_panel`) | 0 | The **sole** code that reconstructs the decay panel from `signal_outcomes.ml_prob` / `ml_expected_return` | The retained `signal_outcomes` rows become unreadable in practice — evidence with no reader. |
| **E15** | `asxos/domain/research/alpha_eval.py` | 0 | The statistics layer the decay bar is expressed in (`evaluate()` and its horizon/IC machinery) | The bar itself is gone; a successor model could only be assessed against a re-implemented, unreviewed method. |

> **E12 — the failure scenario, written out.** `demo.py` is **live code, not a fixture**: imported
> by `asxos/domain/decision_engine/__init__.py:8` and by `asxos/prototype/app.py:16`, which is what
> `make decision-demo` (`Makefile:24`) serves. It has **4 S1 token hits and appeared nowhere in the
> original manifest** — the single worst gap the challenge found, because an unclassified file with
> Model A tokens in it is precisely what a P1-02 token sweep treats as fair game. If P1-02 greps
> `model_a` and deletes both `ConstraintResult` blocks, `build_demo_brief()` raises
> `ValueError("the blocking Model A quarantine constraint must pass exactly once")`. The traceback
> points at `types.py:631-635` — **E8** — so the path of least resistance for whoever is holding
> the failing build is to delete that check and drop `"model_a_quarantine"` from
> `UNIVERSAL_CONSTRAINTS` (`types.py:45-53`). That is **deleting E7 and E8 to fix a symptom in a
> file the manifest never classified.** The ban is removed, the demo goes green, and nothing
> announces it.

> **E13-E15 — why the decay instrument is `ENFORCEMENT_KEEP`, not `ACTIVE_REMOVE`.**
> `scripts/alpha_eval.py` is the **only** caller of `alpha_loader.load_panel`
> (`jobs/eval_alpha_factors.py:27,74` imports only `load_factor_panel` — the factor path —
> verified). `load_panel`'s `_PANEL_SQL` is the only code that rebuilds the decay panel from
> `signal_outcomes`. That chain is the instrument that produced
> `docs/model-a-decay-analysis-2026-07-11.md`, and rule #11's literal exit condition is *"a new
> model version passes a pre-registered decay bar"* — a bar measured by `evaluate()` over exactly
> this panel. **Failure scenario:** P1-02 deletes the script as dead ML tooling; a later dead-code
> pass then removes `load_panel` / `_PANEL_SQL` / `HORIZONS` as unreferenced. Rule #11 is left with
> a preserved verdict, preserved evidence rows, and **no reproducible way to re-run the test or to
> measure a successor model against the same bar.** The quarantine becomes permanent by accident
> rather than by evidence.
>
> This also resolves an internal inconsistency: [Limit #3](#limits-of-this-manifest) argues the
> `signal_outcomes` **rows** must be retained "because dropping them would destroy the ability to
> re-verify the finding," while the original manifest classified the **tool that reads them** as
> `ACTIVE_REMOVE`. Retaining evidence and deleting its only reader is not retention.

> **E5-E8 are ratified architecture.** `docs/product/target-architecture.md` (rows RATIFIED
> 2026-08-12, PR #87) binds the manifest regex rejection and the blocking `model_a_quarantine`
> constraint as architectural requirements — they are not incidental prototype code.

> **Same file, two classifications.** `build.py:184-189` is `ENFORCEMENT_KEEP` (E1) while
> `build.py:191-215` (the `FROM signals` fetch) is `ADAPT` (A1). **P1-02 must split this file at
> the line level**, not delete or keep it wholesale.
>
> **CORRECTION (P1-05 reconciliation, 2026-08-13) — this split HAPPENED, and it is the single
> best evidence that the E1/A1 distinction was the right call.** P1-04 (#103) did exactly what
> this note demanded: the `FROM signals` fetch (A1) and its staleness hard-fails (A2) were lifted
> out into `asxos/domain/portfolio/candidates.py` behind one seam that raises
> `CandidateSourceUnavailable`, while **the gate above it was left byte-identical.** The gate is
> now at **`build.py:209-214`**; the code that replaced A1/A2 is the
> `load_allocation_candidates(...)` call directly beneath it.
>
> Three properties of the result are worth pinning, because they are what a future reader needs
> and none of them is obvious from a diff:
>
> 1. **The gate no longer has a consumer for its return value's original purpose.** It resolved a
>    model name so the signals query could filter `WHERE model = $1`. That query is gone, yet the
>    gate still runs first and still hard-fails — `production_model` is now threaded into the
>    unavailability message only. **This is deliberate**, is stated in `build.py`'s own comment,
>    and is pinned by `test_model_gate_runs_before_the_candidate_source`. A future reader who
>    notices the gate "isn't used for anything" and deletes it as dead scaffolding disarms rule
>    #11 — that is precisely the failure this manifest exists to prevent, and it is now *more*
>    likely than before P1-04, not less, because the gate's original justification has evaporated.
> 2. **`candidates.py` is NOT rule #11's enforcement point** and its own module docstring says so
>    in as many words. Two independent hard-fails now sit on the capital path (`ModelGateDormant`,
>    then `CandidateSourceUnavailable`); **both must survive**, and satisfying the second does not
>    substitute for the first.
> 3. **`CandidateSourceUnavailable` is not yet in E4's `'blocked'` tuple** — a known, documented
>    gap carried in `candidates.py`'s docstring. Latent only because E1 raises first while zero
>    models are approved. It goes live the moment any model earns `approved_for_allocation`, and
>    must be fixed **in the same change** that wires a real candidate source.

---

### `ENFORCEMENT_KEEP` — tests (10)

> These prove the quarantine still works. Deleting one removes the alarm, not just the coverage.

| # | Site | Tok | Load-bearing assertion | What breaks if removed |
|---|---|---:|---|---|
| **T1** | `tests/test_production_gate.py:33-40, 42-49, 52-62` | 8 | `pytest.raises(ModelGateDormant)` on 0 rows; `assert not isinstance(exc, ModelGateDormant)` on >1; `required=False` returns `None` | The 0-vs->1 exception-type split collapses. `ModelGateDormant` could degrade to a bare `RuntimeError` (breaking E4), or a >1 misconfig could be reclassified as "dormant" and stop paging. |
| **T2** | `tests/test_portfolio_build.py:74-80, 83-95, 157-171, 174-211, 213-225` ~~`:64-67, 70-83`~~ | 2 | `pytest.raises(RuntimeError, match="approved_for_allocation")` (`:74-80`); `match="multiple models"` (`:83-95`); **NEW** `test_model_gate_runs_before_the_candidate_source` (`:157-171`) asserts the ordering *as a test* rather than a comment; **NEW** `test_candidates_module_is_model_independent` (`:174-211`) source-inspects `candidates.py` imports + AST-strips docstrings before scanning for `signals` SQL; **NEW** `test_build_issues_no_signals_query` (`:213-225`) walks every query `build()` actually issued | **The allocator's capital-safety hard-fail becomes untested.** `build()` could start silently picking an arbitrary model. This is E1's alarm. |
| **T3** | `tests/test_job_monitor.py:23, 101, 112-113` | **0** | `pytest.raises(ModelGateDormant, match="approved_for_allocation")`; `assert update_call.args[1] == "blocked"` | **Highest-value blind spot.** `test_production_gate.py:36-38` names this file as the *reason* `ModelGateDormant` must stay a distinct type — the two are a mutually-referencing pair, and a token sweep keeps one and drops the other. |
| **T4** | `tests/test_decision_engine_prototype.py:357-378, 380-400, 386-388, 292-297` | 15 | Parametrized rejection of `model_a`, `model_a_ml`, `model_a_v2`, `Model-A`, `model a`, `v1_5` → `match="quarantined"`; dropping `model_a_quarantine` → `match="Model A quarantine constraint"` | Model A could re-enter a decision brief's manifest unchallenged. **Single point of failure:** this is the *only* file testing `_MODEL_A_RE`, `UNIVERSAL_CONSTRAINTS`, and `verify_content_hash` — treat as non-retirable in full, do not prune test-by-test. |
| **T5** | `tests/test_screening_evaluator.py:115-133` | 5 | Parametrized whitelist rejection of `signal_label`, `prob_up`, `expected_return`, `shap_factors` → `match="unknown field"` | The screening rule DSL's field whitelist loses its rule #11 coverage; a screen could reach ML columns. (Same test also carries the SQL-injection-via-field-name case.) |
| **T6** | `tests/test_thesis_discipline.py:302-336` | 2 | `test_module_imports_are_model_independent` — reads `discipline.py`, asserts no import contains `signals`, `models`, `model_a`, `production_gate`, `shap`, `predict`, `cache` | E10's only mechanical enforcement. Without it the contract is docstring-only. |
| **T7** | `tests/test_thesis_proposal_schema.py:126-137, 243-256` | 5 | `monitor_only=True` in a basis section → `ValidationError`; a Model A figure may never be `target_price`/`stop_price`/`entry_band_*` | A Model A number could become the actual trade lever inside a thesis. |
| **T8** | `tests/test_thesis_service.py:938-951` | 2 | `pytest.raises(ValueError, match="monitor_only")` on `add_report_section` | The service write path could bypass `schemas._check_monitor_placement`; this test exists to prove reuse, not reimplementation. |
| **T9** | `tests/test_brief_compose.py:203-215, 250-259, 262-281, 284-300, 303-316` ~~`:548-578, 582-607, 139-166, 644`~~ | 10 | **REWRITTEN by P1-04 — assertion replaced, not relocated.** `test_collect_never_queries_model_versions_or_signals` (`:676-726`) is parametrized over **zero / one / multiple** approved models and asserts collect() issues no `model_versions`, no `FROM signals`, no `shap_factors` query in *any* of the three; `test_brief_data_has_no_model_fields` (`:250-259`) asserts `regime`/`signal_changes`/`latest_signal_date`/`model_shelved` are **gone from the dataclass**, not merely unused; `test_compose_module_imports_are_model_independent` (`:262-281`) is a source-level import contract that matches `line.strip()` so a *function-local* re-import cannot slip past; `test_brief_template_source_has_no_model_references` (`:284-300`) reads the `.j2` directly; `test_rendered_brief_contains_no_model_vocabulary` (`:203-215`) renders four brief states | Either the brief starts hard-failing under a standing quarantine (pressure to lift it), or model-derived sections leak through while quarantined. |
| **T10** | `tests/test_active_theses_signals.py:111-129, 131-139, 141-153` ~~`:105-115, 117-129, 49`~~ | 12 | **REWRITTEN by P1-04 — assertion replaced, not relocated.** `test_collector_issues_only_the_theses_query` (`:111`) asserts the collector's *entire* query set is the theses query; `test_no_model_vocabulary_on_any_card` (`:131`); `test_card_carries_no_trade_direction` (`:141`). Cards now carry a four-state review status (`asxos/domain/review/status.py`) in place of the Model A label. **The filename is retained deliberately** — the file's own docstring says so, because it is cited as T10 here and a rename would dangle this row | The display-only thesis card path could hard-fail, or keep printing a Model A driver line while quarantined. |

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — T9 and T10 are the two rows this
> reconciliation could not fix by renumbering.** Their original assertion was *conditional*
> ("under 0 or >1 approved models, the display path skips its Model A surface"). P1-04 deleted
> the display path's model gate, so the condition has no subject: there is no configuration of
> `model_versions` that re-enables a model surface, because no model surface remains. The
> replacements assert the *unconditional* property instead — **no `model_versions` query and no
> `signals` query in any state** — which is strictly stronger and cannot be satisfied by a gate
> that is present but mis-wired.
>
> **What must not be lost in the swap.** The old T9 set included
> `test_brief_compose.py:139-166`, which rendered real HTML and asserted the shelved-model
> strings were absent — the mitigation the independent challenge identified for A6's
> silent-`Undefined` failure mode. P1-04 did not merely keep that guard, it **closed the
> underlying hole**: `compose.brief_env()` now passes `undefined=jinja2.StrictUndefined`, and
> `test_template_environment_is_strict_about_undefined_names` (`:303-316`) asserts it on the real
> environment `render_html` uses. **A6's silent-failure class is now structurally impossible in
> this template, not merely covered by a string assertion.** That test is `ENFORCEMENT_KEEP` for
> the same reason the rest of T9 is.
>
> **Both files remain non-retirable in full.** Neither carries a Model A *dependency* any more —
> what they carry is the *proof of absence*, which is the only thing standing between a future
> change and a silent reintroduction.

---

### `MIGRATION_KEEP` — applied SQL, never edited (3)

| # | Site | Tok | Note |
|---|---|---:|---|
| **M1** | `migrations/0032_model_versions_allocation_gate.sql:22` | 2 | `ADD COLUMN approved_for_allocation BOOLEAN NOT NULL DEFAULT FALSE` — **the schema of the enforcement gate.** Also functionally `ENFORCEMENT_KEEP`: drop this column and E1/E2 cannot express the invariant. Applied; never edit. |
| **M2** | `migrations/0003_model_a_v1_5_seed.sql:1-3` | 3 | Seeds the `model_a`/`v1_5` `model_versions` row. Applied. The row must stay (with `approved_for_allocation = FALSE`) — **deleting the row is not the retirement mechanism**, and would make the gate's 0-row state ambiguous. |
| **M3** | `migrations/0001_initial.sql`, `0030_drop_non_asxos_schema.sql`, `0031_thesis_disposal_return_and_benchmark_seed.sql`, `0037_security_kind.sql`, `0038_screening_evaluator_wiring.sql` | 1/3/1/3/4 | Incidental Model A mentions in applied SQL (5 files, 12 lines). Applied; never edit. |

---

### `ACTIVE_REMOVE` — live Model A consumption, deleted by P1-02/03/04 (25)

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — the heading overstates what happened.
> P1-02/04 removed roughly half of this set; the other half is still on disk at `6327a61`.**
> Verified by direct filesystem check, not by reading the PR descriptions.
>
> **REMOVED (10 rows):** R1 (`api/main.py` model warm) · R2/R3 (`domain/models/cache.py`, whole
> file) · R4 (`domain/models/model_a.py`, whole file) · R11 (`domain/signals/writer.py`, whole
> file) · R13 (`cli/predict.py`, whole file) · R13b (`cli/main.py:21,37`) · R15
> (`jobs/generate_signals.py`) · R17 (`jobs/check_model_staleness.py`) · R18
> (`jobs/track_signal_outcomes.py`).
>
> **STILL PRESENT (12 rows) — the training chain and the artefacts:** R5
> (`domain/models/train.py`) · R6 (`training_config.py`) · R7 (`validation.py`) · R8
> (`metadata.py`) · R9 (`domain/signals/feature_engine.py`) · R10 (`domain/signals/loader.py`) ·
> R12 (`domain/signals/thresholds.py`) · R14 (`cli/model.py`) · R16
> (`jobs/retrain_model_a.py`) · R19 (all four `models/*.pkl`/`.json` artefacts) · R21
> (`config.py` healthcheck field) · R26 (`README.md:22`). R22-R25 are `render.yaml` crons —
> declared-but-dead, disposed by P1-03, and `render.yaml` is an authority path.
>
> **This remainder is coherent, not an oversight, and it is one connected component.**
> `jobs/retrain_model_a.py` imports R5, R6, R7, R8, R9 and R10 directly; it is the only importer
> of most of them. So the surviving set is *the training pipeline plus the artefacts it writes* —
> exactly the part P1-02's brief did not cover (it removed **runtime/API/job dependencies**; the
> retrain job is not on any runtime path and, per P1-03, is invoked by no executing workflow).
>
> **Two consequences P1-05 will not paper over:**
>
> 1. **R19 + `tests/test_model_artifact_contract.py` remain a same-commit constraint.** That test
>    still reads the real `models/` directory with pure stdlib, so it runs in the sandbox lane.
>    Deleting the artefacts without deleting the test in the same commit turns `make check` red.
>    The constraint has not expired — it has simply not been reached yet.
> 2. **The `[ml]` extra is still declared** (`pyproject.toml:42-47`, `lightgbm==4.5.0`,
>    `joblib==1.4.2`). Finding 4's *ordering* hazard is **discharged** — R13/R13b are gone, so
>    `asx` no longer imports `joblib` at startup — but the dependency itself survives because
>    `jobs/retrain_model_a.py` still needs it. **Removing the `[ml]` extra is now gated on R5-R10
>    and R16, not on the CLI.** Finding 4's step-5 precondition is therefore *not* satisfied.

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
| R13 | `asxos/cli/predict.py:11,20,50` | 3 | `asx predict` — runs Model A for one date, prints SHAP. **Import-order-critical:** `:11` is `from asxos.domain.models.model_a import predict_with_shap`, the head of the chain into `joblib`. See Finding 4. |
| R13b | `asxos/cli/main.py:21` — `from asxos.cli.predict import predict`, and `main.py:37` (`app.command()(predict)`) | **0** | **Added 2026-08-12. Token-blind.** The CLI entrypoint's unconditional import of R13. Removing R13 without this line breaks `asx` entirely; removing the `[ml]` extra without *both* breaks `asx` entirely. See Finding 4. |
| R14 | `asxos/cli/model.py:11-101` + `asxos/cli/main.py:17,46` | 9 + 2 | `asx model activate\|list`, defaulting `--model model_a`. `model.py:14-101` is the **sole `is_active = TRUE` flip** in the codebase. **Note (2026-08-12):** the cited `main.py:17,46` are the `model_app` lines — an over-match of the S1 pattern, and cosmetic here. The consequential line in that file is `:21` (R13b), which carries no token. |
| R15 | `jobs/generate_signals.py:26-27,277,283` | 5 | The daily producer: `get_cache().get("model_a")` → `predict_with_shap` → writes `model="model_a"` rows. |
| R16 | `jobs/retrain_model_a.py:1-290` | 18 | Weekly retrain; `joblib.dump()` of new artefacts. Inserts inactive, never activates. |
| R17 | `jobs/check_model_staleness.py:66,70-71` | 7 | `SELECT MAX(as_of) FROM signals WHERE model = 'model_a'`. |
| R18 | `jobs/track_signal_outcomes.py:28,44` | 1 | `_MODEL = "model_a"`; matures `signals` rows into `signal_outcomes`. |
| R19 | `models/model_a_v1_5_classifier.pkl`, `_regressor.pkl`, `_features.json`, `_metrics.json` | 1 | The tracked binary artefacts loaded by R2. **Remove after R1** — see Finding 1. **Same-commit constraint (2026-08-12):** `tests/test_model_artifact_contract.py:25` reads the real `models/` directory using pure stdlib, so it runs in the sandbox lane too (no `joblib`/`lightgbm` needed). Deleting the artefacts without deleting that test in the *same commit* breaks `make check`. |
| ~~R20~~ | ~~`scripts/alpha_eval.py:5`~~ | — | **RECLASSIFIED 2026-08-12 → `ENFORCEMENT_KEEP` E13.** It is rule #11's exit instrument, not disposable ML tooling. Retained as a struck row so a P1-02 reader working from an older copy of this manifest sees the change rather than the original verdict. |
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

These follow R1-R21 mechanically (R20 excepted — it is now E13). Listed for completeness; not
counted as S2 sites because they carry no independent decision.

> **CORRECTION (independent challenge, 2026-08-12) — one of these is NOT free-floating.**
> `test_model_artifact_contract.py:25` opens the real `models/` directory with pure stdlib, which
> is why it runs in the sandbox lane where the `joblib`/`lightgbm` tests collection-error. It must
> be deleted in the **same commit** as R19's artefacts — not "with the ML tests, eventually" — or
> `make check` goes red between the two commits.

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

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — status at `6327a61`.**
>
> **DONE (5):** **A1/A2** — lifted into `asxos/domain/portfolio/candidates.py`; the seam raises
> `CandidateSourceUnavailable` and **nothing was substituted for the retired ranking**, which is
> the correct outcome under packet P1's non-goals (no like-for-like model swap, no fallback
> candidate set). **A3/A4** — `compose.py`'s gate call and all four `signals` reads are gone;
> this closes cleanup-backlog **R6**. **A5** — the V2 `active_theses` collector is
> model-independent and its cards render a four-state review status
> (`asxos/domain/review/status.py`) in place of the Model A driver line. **A6** — all five
> `model_shelved` references are gone from `brief.html.j2` *and* the field is gone from
> `BriefData`; the prescribed **template-first, field-second** order was followed, and the
> environment now uses `StrictUndefined` so the silent-failure class is closed structurally.
>
> **NOT DONE (4):** **A7** `asxos/cli/signal.py:27`, **A8** `asxos/cli/journal.py:43`, **A9**
> `jobs/compute_opportunity_cost.py:47` — **all three still issue `FROM signals`.** They query a
> table that **no longer has a writer** (R11 `signals/writer.py` was deleted by P1-02), so each
> now reads a frozen historical table that can only get staler. That is a different and quieter
> failure mode than the one this row was written for: not "a display leaks a live model figure"
> but "a live surface silently presents indefinitely-ageing data as current." **A9 in particular
> is a scheduled job**, so it will keep producing opportunity-cost numbers off a table nobody
> writes. Cleanup-backlog **R4** is therefore still open, and its rationale has changed.
> **A10** — the dated `check_cron_health` comments must stay until the crons are actually gone;
> P1-03 disposed them on paper but `render.yaml` is unchanged.
>
> **A11** (`.github/workflows/targeted-ml-tests.yml`) is an authority path and is untouched. It
> still gates ML tests whose subjects R5-R10/R16 still exist, so it is not yet retirable.

| # | Site | Tok | Consumer | Proposed destination |
|---|---|---:|---|---|
| **A1** | `asxos/domain/portfolio/build.py:191-215` | **0** | The allocator's candidate source (`FROM signals WHERE model = $1`, both branches) | A model-independent candidate source — the screening evaluator (`asxos/domain/screening/`) and/or thesis-driven targets. **Keep E1's gate above it:** the gate must outlive the signals query it currently feeds. |
| **A2** | `asxos/domain/portfolio/build.py:216-230` | **0** | Signal-emptiness + >2-day staleness hard-fails | Re-anchor the same hard-fail shape onto the replacement candidate source. Do not soften to a warning (rule #10). |
| **A3** | `asxos/brief/compose.py:242-256, 268-269` | 7 | Brief V1 `collect()` — `resolve_production_model(required=False)` | Remove the gate *call* together with the display reads it feeds (A4). **Do not remove `required=False` from E2's signature** — that overload is the R9 fix and must survive for any future display consumer. |
| **A4** | `asxos/brief/compose.py:284, 294, 372, 380` | — | `SELECT regime FROM signals`, `MAX(as_of) FROM signals`, two `FROM signals s` joins | Model-independent regime source, or drop the regime line. Closes cleanup-backlog **R6** (V1 reads `signals.regime` — a display-only leak). |
| **A5** | `asxos/domain/brief/collectors/active_theses.py:70-92` | 5 | V2 collector — same gate + `FROM signals` read | Same as A3/A4. The thesis cards themselves are already model-independent and **must keep rendering**. |
| **A6** | `asxos/brief/templates/brief.html.j2:31, 39, 52, 57, 96` + `asxos/brief/compose.py:202` (`BriefData.model_shelved`) | 5 | **Two of the five are copy; three are suppression logic.** `:31` and `:39` render the "Model A: shelved" wording. `:52` `{% if d.prices_stale or (d.signals_stale and not d.model_shelved) %}`, `:57` `{% if d.signals_stale and not d.model_shelved %}`, and `:96` `{% if not d.model_shelved %}` (which gates the entire "Signal changes on holdings" section) are **live state controlling what the brief shows.** | Rewrite as suppression that no longer depends on a model flag, then delete `model_shelved`. **Deleting the field first fails silently — see the note below.** |
| **A7** | `asxos/cli/signal.py:27` | **0** | `asx signal` — `FROM signals` reader. **Token-blind.** | Remove the command, or repoint at the replacement candidate source. |
| **A8** | `asxos/cli/journal.py:43` | **0** | Decision journal enriches entries `FROM signals`. **Token-blind.** | Drop the signal enrichment; the journal is otherwise model-independent. |
| **A9** | `jobs/compute_opportunity_cost.py:47` | **0** | `FROM signals` reader; weekly cron `render.yaml:566-585`. **Token-blind.** | Re-derive from realised prices, or retire the job. Closes cleanup-backlog **R4**. |
| **A10** | `jobs/check_cron_health.py:33, 47` | 1 | Already adapted — `generate_signals` and `check_model_staleness` commented out of `_EXPECTED_DAILY` | Keep the dated comments until the crons are actually gone, then convert to a clean deletion. **This file is the evidence for Finding 2.** |
| **A11** | `.github/workflows/targeted-ml-tests.yml:46, 61` | 2 | The fast ML test lane (`tests/test_model_artifact_contract.py` et al.) | Retire the lane with the ML tests it gates. **Authority path** — draft via reviewed PR, never edit directly. |

> **CORRECTION (independent challenge, 2026-08-12) — A6 was under-cited and mis-characterised.**
> The original entry cited `brief.html.j2:32,41` (two lines) and called the whole thing "stale
> phrasing, not a live state." There are **five** `model_shelved` references and three of them are
> suppression logic, as the corrected row above records.
>
> **The silent-failure property.** `asxos/brief/compose.py:892` builds
> `jinja2.Environment(loader=…, autoescape=True)` with the **default `Undefined`** — *not*
> `StrictUndefined`. (`asxos/domain/decision_engine/renderer.py:107` does pass
> `undefined=jinja2.StrictUndefined`; the brief environment does not.) So if P1-02 deletes
> `BriefData.model_shelved` (`compose.py:202`) and leaves the template alone, **every
> `d.model_shelved` evaluates to a falsy `Undefined` and the brief renders without raising**:
>
> - `:34` — the red "Regime: unavailable" line comes back
> - `:57` — the "Signals stale" banner comes back (permanently, since nothing writes signals)
> - `:96` — the "Signal changes on holdings" section header renders again
>
> No exception, no failing job, no alert. The brief just quietly starts advertising a signal
> engine that no longer exists. **Order: template first, field second.**
>
> **Mitigation that already exists.** `tests/test_brief_compose.py:139-166` renders real HTML and
> asserts those strings are absent, so **T9 catches this** — which is exactly why T9 is
> `ENFORCEMENT_KEEP` and must not be pruned alongside the ML test collateral.

---

## Findings P1-02 must not discover the hard way

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

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — FINDING 2 IS RESOLVED, AND ITS PRESCRIBED
> REMEDY IS VOID. Do not run `make check-drift`.**
>
> **The remedy is void on governor authority.** James ruled on 2026-08-12 (authority ladder level
> 0) that **Render was deleted**, and explicitly forbade requesting a key, probing, inspecting,
> mutating or recreating it (`docs/product/roadmap-state.md:165`). `make check-drift` reconciles
> against a platform that no longer exists. **Every instruction in this manifest to run it is
> superseded** — the affected passages are the `render.yaml` authority note under `ACTIVE_REMOVE`,
> this paragraph, the "Related" note below, and Limit #2.
>
> **The question it asked was nevertheless answered, without the probe.** Mission P1-03 (#101)
> produced `docs/product/scheduler-inventory-2026-08-13.md`, now **the single authoritative
> scheduler record, superseding `render.yaml` for every scheduling question.** It disposes all 29
> declared services (20 ADOPTED into GitHub Actions · 6 RETIRE, five of them Model A · 3 DECIDE)
> and **proves at `origin/main` that zero Model A jobs are invoked by any of the ten workflows** —
> a grep for `generate_signals|retrain_model_a|check_model_staleness|track_signal_outcomes|compute_opportunity_cost`
> across `.github/workflows/` returns no matches.
>
> **So Finding 2's worst case did not obtain.** The producer is not running unmonitored: it is not
> running at all, and as of P1-02 `jobs/generate_signals.py` no longer exists to run. R22/R24/R25
> are a **config cleanup of a dead manifest**, not a live-service removal — the opposite of what
> this Finding warned P1-02 to prepare for.
>
> **What is left is a documentation hazard, not an operational one.** `render.yaml` remains
> in-repo, still headed "source of truth", still declaring these crons. Removing it is the
> `RENDER-RETIRE` scope owned by P1-03/P3-01 and needs the draft-PR route (authority path).

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

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — this Finding is now OPEN AND OWNED, and it is
> the one P1 item that cannot be closed by any mission.** Both files are governance-set authority
> paths. P1-05 confirms the finding still holds verbatim at `6327a61` and hands it to James as a
> drafted amendment; SB0-01 independently reached the same conclusion
> (`docs/product/doc-truth-map-2026-08-13.md` §2.8).
>
> **The precise hazard, restated now that the retirement has actually happened.** Rule #11's
> literal text conditions its own removal on *"a **new** model version passes a pre-registered
> decay bar … AND earns `approved_for_allocation`"*. After a retirement there is no model, no
> candidate successor, and — once R5-R10/R16 go — no training pipeline to produce one. The exit
> condition becomes unreachable **in practice**, so a rubric that pins a P0 "until rule #11 lifts"
> pins it forever. **The failure mode is not that the quarantine is too strong. It is that a
> permanently-unsatisfiable P0 blocks the queue and creates standing pressure to "resolve" it —
> and the cheapest way to resolve an unsatisfiable blocker is to weaken its condition.** That is
> how a quarantine gets lifted by administrative fatigue rather than by evidence.
>
> **Rule #11 itself must not change, and P1-05 proposes no change to it.** Retirement
> *strengthens* the quarantine — removing the code is a superset of refusing to use it. What
> needs amending is the two rubrics' assumption that "lifted" is the only terminal state. The
> drafted wording is in P1-05's report: the third state is **RETIRED**, which satisfies the
> rubric's visibility requirement without asserting Model A was cleared.

### Finding 4 — the whole `asx` CLI transitively imports `joblib` (second removal-order constraint)

> **ADDED by the independent challenge, 2026-08-12.** The original manifest had one removal-order
> constraint (Finding 1). This is the second, and it is invisible to the token search.

`asxos/cli/main.py:21` is `from asxos.cli.predict import predict`. It contains **zero Model A
tokens** and sits four lines below `from asxos.cli.model import model_app` (`:17`) — one of this
manifest's own documented over-matches, and the line R14 actually cites. The token search saw the
noisy line and missed this one.

The import chain, all at module load time:

```
asxos/cli/main.py:21        from asxos.cli.predict import predict
  -> asxos/cli/predict.py:11    from asxos.domain.models.model_a import predict_with_shap
    -> asxos/domain/models/model_a.py:17   (-> domain/models/cache.py)
      -> asxos/domain/models/cache.py:25   import joblib     # module level, not lazy
```

Because `main.py` builds the Typer app by importing every command module up front, **`joblib` is
imported before Typer has parsed a single argument.**

**The constraint:**

> **R13 (`asxos/cli/predict.py`) and R13b (`asxos/cli/main.py:21`, plus the `app.command()(predict)`
> registration at `:37`) MUST be removed BEFORE any change to the `[ml]` extra in
> `pyproject.toml:42-47` or to Render's `buildCommand: pip install -e ".[ml]"`.**

Violate that order and **every `asx` command dies at import with
`ImportError: No module named 'joblib'`** — not just the ML ones. That includes precisely the
model-independent commands the shelf strategy is built on: `asx tax-view`, `asx tax-action`,
`asx thesis …`, `asx portfolio …`, `asx import-holdings`, `asx brief`. The failure is total,
immediate, and its error message names `joblib` rather than anything a reader would connect to a
Model A retirement.

This is the same class of trap as Finding 1 (delete the artefacts before the loader → the API
won't boot), one layer up: **delete the dependency before the importer → the CLI won't start.**

**Combined removal order across both findings:**

| Step | Remove | Because |
|---:|---|---|
| 1 | R1 (`api/main.py` model warm) | Or the API won't boot without the `.pkl` files |
| 2 | R13 + R13b (`cli/predict.py`, `cli/main.py:21,37`) | Or the CLI won't start without `joblib` |
| 3 | R2/R3 (`domain/models/cache.py`) | Now unreferenced |
| 4 | R19 (`models/*.pkl`) **+ `tests/test_model_artifact_contract.py` in the same commit** | Or `make check` goes red |
| 5 | `pyproject.toml:42-47` `[ml]` extra, Render `buildCommand` | Safe only once 1-4 are done |

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — steps 1-3 are DONE; steps 4-5 are NOT, and
> step 5's precondition has changed.**
>
> **Steps 1-3 complete.** P1-02 removed R1, then R13 + R13b, then R2/R3 (`cache.py` and
> `model_a.py` are both gone as whole files). **Both removal-order traps were avoided.** The
> `asx` CLI no longer imports `joblib` at startup, and `tests/test_cli_model_independence.py`
> (new, 176 lines) now pins that property — so Finding 4's hazard is not merely discharged, it is
> **regression-guarded**, which the original finding asked for only implicitly.
>
> **Step 4 not done.** All four `models/*` artefacts are still tracked, and
> `tests/test_model_artifact_contract.py` still reads them. The same-commit constraint is
> unexpired.
>
> **Step 5's gate MOVED.** The `[ml]` extra (`lightgbm==4.5.0`, `joblib==1.4.2`) is still
> declared, and it is no longer the CLI that holds it there: `jobs/retrain_model_a.py` (R16) and
> the chain it imports (R5-R10) are the remaining consumers. **Finding 4 framed the CLI as the
> blocker on the `[ml]` extra; after P1-02 the blocker is the training pipeline.** A future reader
> who checks only Finding 4's stated condition ("R13 and R13b removed") would conclude step 5 is
> safe. It is not — removing the extra today breaks `retrain_model_a.py` at import. The Render
> `buildCommand` half of step 5 is moot: Render was deleted (see Finding 2's correction).

---

## `ORPHANED_BY_P1-04` — modules with no production caller (added by P1-05, 2026-08-13)

**A new category, because neither `ACTIVE_REMOVE` nor `ENFORCEMENT_KEEP` describes these
honestly.** P1-04 removed their last production caller without removing them. Each is now
reachable only from tests. **An unclassified module with no caller is what a dead-code sweep
deletes**, and in both cases below that would be wrong for a *different* reason — so both are
recorded here rather than left to a future reader's judgement.

| # | Module | Reachable from | Disposition | Why it must not be swept |
|---|---|---|---|---|
| **O1** | `asxos/domain/brief/shap.py` | `tests/test_brief_shap.py` only | **ACTIVE_REMOVE — but not yet, and not silently** | Its two documented callers (`compose.py::_signal_changes` and the V2 `active_theses` collector) were both removed by P1-04. Its whole purpose is formatting `signals.shap_factors`, a Model A output column with no writer left. **It is genuinely dead Model A display code** and belongs in `ACTIVE_REMOVE`. It was **unclassified in the original manifest** — the same profile as E12, and the reason it is being named now rather than discovered by a sweep. Delete it **with `tests/test_brief_shap.py` in the same commit**. Note it is already named in the `banned` import tuple of *two* enforcement tests (`test_brief_compose.py:278`, `test_portfolio_build.py:191`) — **those tuples must keep naming it after the file is gone**, since their job is to stop it coming back. |
| **O2** | `asxos/domain/portfolio/volatility.py` | `tests/test_volatility.py`, `tests/test_portfolio_allocator.py` | **KEEP — required by the replacement candidate source** | Never Model A code. It is Decimal-only realised-vol estimation (`annualised_vol_from_prices`, `load_vols_for_symbols`) and it is **the sizing input the allocator cannot work without**: `allocator.py:170-172,212` divides by `candidate.daily_vol` to build inverse-vol weights. It lost its production caller only because `build.py`'s candidate loading moved into `candidates.py`, whose docstring **explicitly carries the 60-day-vol obligation forward** to whatever real source is wired in. **Deleting it as dead code would silently remove the risk-sizing leg of the allocator** and force whoever wires the replacement to re-implement Decimal-only vol from scratch, against `.claude/rules/portfolio-conventions.md`'s no-numpy invariant. |

> **The asymmetry is the point.** Both modules look identical to a dead-code tool: zero production
> importers, tests only. One should go and one must stay, and **nothing in the code distinguishes
> them** — the distinction lives in `candidates.py`'s docstring (an obligation) and in this table.
> That is exactly the failure mode this manifest was created for, reproduced at a smaller scale by
> the retirement itself.

---

## Token-blind documentation — the denominator's false negatives

**Added by P1-05, 2026-08-13, from SB0-01's finding (#102,
`docs/product/doc-truth-map-2026-08-13.md` §6.1).**

This manifest's S1 denominator matches `model_a|Model A|MODEL_A|model-a`. The manifest already
proves this is blind to *code* (seven token-blind sites). **It is equally blind to prose, and
SB0-01 found two confirmed misses — both capital-adjacent, both asserting a live Model A path,
both with zero Model A tokens:**

| Doc | Line | The false claim | Why the token search cannot see it |
|---|---|---|---|
| `docs/maintenance/guards-backlog.md` | `:107` | *"signals are generated on stale prices … Tomorrow's `build_portfolio` reads them and proposes trades against yesterday's reality … **production trading proposals on stale inputs**."* | Names `generate_signals` and `build_portfolio`, never Model A. **Worse: this file auto-attaches to `system-architect`**, so the framing reaches architecture work unprompted. |
| `docs/maintenance/paper-portfolio-monitoring.md` | `:106`, `:21` | *"`expected_return` is uncalibrated (**treat `prob_up` as the conviction signal**)"* — advice to trust the exact quantity the decay analysis found **inverted at the top**. | Names only `prob_up` / `expected_return` / `signal_label`. |

**Both are classified `LIVING` and both were corrected in place by P1-05** (banner by SB0-01,
line-level annotation by P1-05 — see each file). Neither was deleted: they are dated maintenance
records and the *non-Model-A* content of both is still valid.

**The finding that matters more than the two files.** The whole `docs/**` classification below —
99 files then, 106 now — is drawn from a denominator with known false negatives, so
**"58 HISTORICAL / 41 LIVING" is a partition of the *matched* corpus, not of the corpus that
makes Model A claims.** The two documents above were in neither number.

**Required change to the CI assertion design, before it is enabled.** The specification below
greps the boundary-aware pattern only. **An assertion built on this denominator will go green
while capital-adjacent misinformation persists** — the precise failure the CI step exists to
prevent. The denominator must become **claim-driven**: add at minimum
`prob_up|expected_return|shap_factors|signal_label|generate_signals|retrain_model_a` to the swept
pattern. That is SB0-01's recommendation and P1-05 adopts it. Note the cost is real and should be
stated: `prob_up` alone adds 29 files outside S1, so widening the pattern widens the allowlist
too — but an allowlist entry is a reviewed line, whereas a false negative is silent.

---

## `HISTORICAL_KEEP` — `docs/**`, at file granularity

**Default: every `docs/**` file matching S1 is `HISTORICAL_KEEP`.**

**Retention reason:** these are the evidence trail for the 2026-07-11 decay finding and the shelf
decision. `docs/model-a-decay-analysis-2026-07-11.md` is the *justification* for rule #11 —
destroying it leaves the standing policy unsourced, and the standing policy is what keeps capital
safe. **Line-level supersession is mission P1-05's job. Do not edit doc bodies in P1-02.**

**99 files / 524 lines**, splitting **41 LIVING / 58 HISTORICAL**.

| Subdirectory | Files | Lines | Files @`6327a61` | Lines @`6327a61` |
|---|---:|---:|---:|---:|
| `docs/` (root) | 23 | 148 | 23 | 148 |
| `docs/product/` (root) | 27 | 144 | **31** | **364** |
| `docs/proposals/` | 12 | 81 | 12 | 81 |
| `docs/foundation/` | 8 | 73 | 8 | **79** |
| `docs/research/` | 5 | 21 | 5 | **25** |
| `docs/product/memory/` (all depths) | 10 | 31 | 10 | 31 |
| `docs/product/evals/` | 3 | 9 | **4** | **10** |
| `docs/product/rubrics/` | 4 | 6 | 4 | 6 |
| `docs/maintenance/` — **absent from the original table** | 0 | 0 | **2** | **12** |
| `docs/assets/` · `docs/strategy/` · `docs/discovery-runs/` · `docs/product/runbooks/` · `docs/harden/` | 7 | 11 | 7 | 11 |
| **Total** | **99** | **524** | **106** | **767** |

> **CORRECTION (P1-05 reconciliation, 2026-08-13) — the corpus is now 106 files / 767 lines, and
> the LIVING/HISTORICAL split needs restating rather than recounting.**
>
> **Seven files entered the corpus, all of them written by this programme.** `docs/product/`
> gained `model-a-reference-manifest.md` (this file), `doc-truth-map-2026-08-13.md` (SB0-01),
> `scheduler-inventory-2026-08-13.md` (P1-03) and `finance-capability-matrix-2026-08-13.md`
> (P2-01); `docs/product/evals/` gained one fixture; and **`docs/maintenance/` appears for the
> first time with 2 files / 12 lines** — because SB0-01's banners put Model A tokens into two
> files that previously had none. **That subdirectory was missing from the original table
> entirely**, which is how its two capital-adjacent claims went unclassified; see
> [Token-blind documentation](#token-blind-documentation--the-denominators-false-negatives).
>
> **All seven are LIVING, and all seven are `HISTORICAL_KEEP` in the retention sense** — they are
> the retirement's own audit trail. **New LIVING total: 48.** The HISTORICAL set is unchanged at
> 58: no dated record was added, removed, or reclassified by P1-02/03/04/05.
>
> **`docs/foundation/` +6 lines and `docs/research/` +4 lines are SB0-01's supersession banners**
> (`BUILD_GUIDE.md`, `alpha-research-audit.md`), not new claims. A banner that says "this is
> superseded" necessarily adds Model A tokens — **the count rises as the documentation gets more
> truthful**, which is the second place in this manifest where the metric moves opposite to the
> outcome. Do not read either count as progress or regress.

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

> **P1-05 disposition of Tier 1 (2026-08-13).** This is the row-by-row record of what P1-05 did
> with the nine highest-leverage LIVING surfaces, and what it deliberately did not.
>
> | File | Disposition | Note |
> |---|---|---|
> | `docs/foundation/BUILD_GUIDE.md` | **CORRECTED — and a defect in the existing banner fixed** | SB0-01 added a `DO NOT EXECUTE` banner. **Every line number in that banner was wrong**, uniformly by +37 — the banner was written against the pre-banner file and then inserted at the top, shifting the whole document. Its citation of the reactivation seed pointed at `:1435`, which post-insert is *"Cancel Render `asx-weekly-features`"* — innocuous text — while **the actual seed sat unmarked**. All ten citations corrected, and an inline `DO NOT EXECUTE` marker placed **at the seed itself**, because a banner at the top of a 2,912-line file does not reach a reader who jumps to M6. |
> | `docs/product/roadmap-state.md` | **No P1-05 edit needed** | Already reconciled by P1-03 (defect row #4) and SB0-01 (§3.2). Its Render drift baselines are superseded by the scheduler inventory. |
> | `docs/product/target-architecture.md` | **Authority path — no edit** | Its `retrain_model_a → RETIRE` disposition is now *executed on paper* by P1-03 and is consistent. E5-E8 remain bound as ratified architecture. |
> | `docs/product/north-star.md` | **Authority path — no edit** | Charter §1's *"do NOT recommend acting on Model A output"* is **strengthened**, not invalidated, by retirement. No draft needed. |
> | `docs/README.md` | **AUTHORITY-GUARDED — drafted, not applied** | Exact replacement text is in P1-05's report; it supersedes SB0-01 §5.1(c) for the BUILD_GUIDE row. |
> | `docs/product/cleanup-backlog.md` | **Partially closed by P1-04** | **R6 is closed** (V1's `signals.regime` read is gone). **R4 is NOT** — `jobs/compute_opportunity_cost.py:47` still reads `FROM signals`, and its rationale has changed: the table now has no writer, so the job reads indefinitely-ageing data. See the `ADAPT` correction. |
> | `docs/product/risk-register.md` | **No P1-05 edit needed** | R8's drafted-not-built follow-up landed as E4; R9's `required=True`/`required=False` split survived P1-04 intact (the `required=False` overload is retained in `production_gate.py` for future display consumers even though its only two callers were removed). |
> | `docs/next-session-backlog.md` | **Stale claim stands, but is now harmless** | Its claim that 0032 grandfathered `model_a/v1_5` is wrong (revoked 2026-07-11). Reference-only by `docs/README.md:30`, so it cannot set priority. Left for `SB0-02`. |
> | `docs/product/runbooks/claude-execute.md` | **Authority path — no edit** | "No Model A in any decision" remains correct and is now trivially satisfied. |

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
(regenerated by `scripts/product_health.py` — see the correction immediately below for what that
script actually grades)

> **CORRECTION (independent challenge, 2026-08-12) — `scripts/product_health.py:77` was
> misattributed.** The original text said line 77 "currently FAILs on `retrain_model_a`". **The
> string `retrain_model_a` appears nowhere in that file.** Line 77 is the `signal_outcomes`
> non-empty gate — it emits `"EMPTY — blocks Model A decay automation"` when the table has zero
> rows, and PASSes otherwise. It grades *evidence availability*, not a job. Retiring
> `retrain_model_a` does not change line 77 at all; **retiring it while keeping the
> `signal_outcomes` rows (Limit #3, E13-E15) keeps this check PASSing, which is the correct
> outcome.**
>
> **The real consequence, which the original manifest missed.** Job grading lives in `_cron_reality`
> (`:81-96`), which is entirely DB-driven: `SELECT job_name … FROM job_runs GROUP BY job_name`. It
> grades **whatever job names exist in `job_runs`**. Historical `retrain_model_a` rows persist after
> the job is retired, so the scorecard will keep grading a job that no longer exists — **forever**,
> degrading as its `last_as_of` ages. **No code change to `product_health.py` fixes this.** It needs
> either a `job_runs` exclusion list (a retired-job filter the script consults) or a data decision
> about the historical rows. That is a real, unowned P1-02/P1-05 follow-up, not a line edit.

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
  **The reason is noise reduction, and only that:** the loose-minus-boundary delta is **exactly 6
  files**, all pure noise, none of them a ban —
  `.github/workflows/targeted-ml-tests.yml`, `asxos/cli/main.py`,
  `asxos/jobs/utils/job_monitor.py`, `docs/audit-2026-06-27.md`,
  `docs/backlog-test-coverage.md`, `docs/strategy/M-THESIS-0_FEATURE_PLAN.md`. Six fewer files to
  allowlist for no analytic loss.

  > **CORRECTION (independent challenge, 2026-08-12) — the original argument for this bullet was
  > false.** It claimed the loose pattern "would fail the build on `model_and_prompt_manifest`,
  > which is the decision engine's Model A **ban**," and called getting that backwards "the single
  > most likely way to build an assertion that fights the quarantine." **Measured:**
  > `asxos/domain/decision_engine/types.py` matches **both** patterns (9 boundary hits — it
  > contains `_MODEL_A_RE` and the literal `"model_a_quarantine"`) and is **file-allowlisted under
  > either pattern**, so it never fails the build either way. The stated failure mode cannot occur.
  > **The conclusion is unchanged — use the boundary pattern — but a contract should not carry a
  > rationale that does not survive being run.**
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
`joblib.load()`, a new `model_versions` consumer. **Seven of this manifest's most important sites
would be invisible to it.** No grep closes that gap, which is why the companion assertions below
matter more than the grep does.

> **CORRECTION (independent challenge, 2026-08-12) — the "Catches" claim is narrower than stated.**
> The second half ("a Model A token added to a currently-clean file") holds only for files that are
> *not already allowlisted*. **The allowlist is FILE-granular on all 6 enforcement modules and all
> 10 enforcement tests.** Those 16 files are therefore permanently exempt from the grep. A new
> active Model A reference added **inside** `asxos/domain/theses/schemas.py`,
> `asxos/domain/screening/types.py`, `asxos/domain/decision_engine/types.py`, or any enforcement
> test is **invisible to the assertion** — and those are exactly the files where an inverse-polarity
> ban could be quietly turned into a use, because they are the files that already legitimately
> contain the token.
>
> This is a structural consequence of a file-granular allowlist, not a fixable bug in the pattern:
> the same entry that stops the ban from failing the build also stops a new use inside it from
> failing the build. It is a further argument for the **companion assertions** below, which are
> content-aware, over the grep, which is not. Do not read "Catches" as coverage of the enforcement
> files.

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

> **CORRECTION (independent challenge, 2026-08-12) — THIS BLOCK IS INCOMPLETE. Do not ship it as
> written.** The block below is a **starting draft, not a working allowlist.** It is missing 56
> files. See [Allowlist completeness](#allowlist-completeness--measured-not-estimated) immediately
> after the block for the measurement, the consequence, and the required remedy. **Enabling the CI
> step against this block as-is fails the build on day one.**

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

### Allowlist completeness — measured, not estimated

> **CORRECTION (independent challenge, 2026-08-12).** The original text here read: *"Immediately
> after P1-02/03/04, the allowlist above should cover roughly all remaining matches."* **It does
> not.** This was the manifest's own proposed remedy, and it is the part of the manifest that
> fails.

**Measurement.** The review built the allowlist from the fenced block above and ran the
boundary-aware pattern at `fad62159f5d6585588d47bbac763687da55f0002`:

| | Files |
|---|---:|
| Match the boundary pattern | **203** |
| Covered by the allowlist above | **147** |
| **Matched and NOT allowlisted** | **56** |

**These survive P1-02/03/04 by this manifest's own classification and are still unallowlisted.**
They are not leftovers a retirement sweeps up — the manifest says to keep them:

| Unallowlisted survivor | Why it survives |
|---|---|
| `asxos/domain/decision_engine/demo.py` | **E12** — `ENFORCEMENT_KEEP` (added by this challenge) |
| `asxos/domain/theses/service.py:496` | Live service code, not classified `ACTIVE_REMOVE` |
| `asxos/cli/holdings.py:52` | Live CLI, model-independent |
| `asxos/ingestion/universe.py:24,27,44,68` | Live ingestion, model-independent |
| `jobs/sync_prices.py:141` | Live job, model-independent |
| `jobs/check_cron_health.py:33,47` | **A10 explicitly says keep those dated comments** |
| `scripts/product_health.py:77` | The `signal_outcomes` gate — see the Tier 4 correction |
| `asxos/brief/compose.py` | **A3-A6** — adapted, not deleted |
| `asxos/domain/brief/collectors/active_theses.py` | **A5** — adapted, not deleted |
| The 8 files under "Incidental mentions" | Explicitly *not* removed |
| `docs/market-trends-report-2026-08-05.md` | Classified `HISTORICAL` — **matched by no allowlist glob** |
| `docs/pr2a-supabase-ro-provisioning-plan-2026-07-05.md` | Classified `HISTORICAL` — **matched by no allowlist glob** |

The last two are the clearest demonstration that the glob set is under-built: both are already
classified `HISTORICAL_KEEP` in this document, and neither `docs/audit-*.md`,
`docs/*-audit-*.md`, `docs/session-handoff-*.md` nor any directory prefix catches them.

**Consequence, stated plainly.** The CI step goes **red on day one**. Whoever is holding that red
build is under time pressure and the cheapest green is a **directory prefix** — `asxos/`,
`tests/`, `docs/`. Each of those is one line, takes seconds, and looks like housekeeping. It is
also **exactly the mutation the design note above tells reviewers to be suspicious of**: adding
`asxos/` allowlists the enforcement modules by prefix, and the tripwire is disarmed in week one by
a well-intentioned person doing something that looks like tidying. **A tripwire that is red on
first use does not get fixed; it gets silenced.**

**Required remedy — both parts.**

1. **Complete the allowlist to all 56 files BEFORE the CI step is enabled.** Re-run the boundary
   pattern against the candidate allowlist and require a **zero** unallowlisted count on a clean
   tree. A tripwire is only credible if it is green the moment it is switched on.
2. **Enabling the assertion is P1-02+ work, not P1-01's.** P1-01 produced a specification; the
   allowlist cannot be finalised until P1-02/03/04 have actually removed the `ACTIVE_REMOVE` set
   and its test collateral, because the surviving file set is not known until then. **Do not merge
   the CI step and the retirement in the same change.**

**Expected steady state.** After P1-05 corrects the living-doc prose, the "living governance docs"
block should shrink substantially — and each removal from the allowlist is a small, verifiable
win. That remains true. What is *not* true is that the block as drafted is close to complete
today.

---

## Limits of this manifest

Stated plainly, because a manifest that oversells its coverage is worse than none.

> **P1-05 update (2026-08-13) — which limits have moved.**
>
> - **Limit #2 (no live-state verification) is PARTLY DISCHARGED and its remedy is void.** P1-03
>   established the executing inventory from `.github/workflows/` at `origin/main`, so Finding 2's
>   contradiction is resolved by repository evidence. **`make check-drift` must not be run** —
>   Render was deleted (governor ruling, 2026-08-12).
> - **Limit #4 (docs classified at file granularity only) is DISCHARGED for the Tier 1 set** —
>   P1-05 read those files and dispositioned them line-level. It **stands for Tiers 2-4 and the
>   58 HISTORICAL files**, which remain filename/header judgements.
> - **Limit #5 (counts frozen at one SHA) is CONFIRMED, harder than written.** The counts did not
>   merely drift — they moved *upward* while the retirement succeeded. See the S1 correction.
> - **Limit #7 (no test executed) is DISCHARGED for P1-05:** the full suite was run at
>   `6327a61` + this documentation change. **2,085 passed · 1 skipped · 2 xfailed**; `ruff` and
>   `mypy` clean. **P1-05 changed no code**, so this is a baseline confirmation, not a proof of
>   the documentation's correctness — prose cannot be unit-tested, which is exactly why the
>   citation re-verification above was done by hand, file by file.
> - **Limit #8 (S2 is a floor, not a boundary) is CONFIRMED AGAIN, by this mission.** P1-05 found
>   two more unclassified modules (**O1** `brief/shap.py`, **O2** `portfolio/volatility.py`) that
>   no seed reached, and two capital-adjacent documents the token denominator structurally cannot
>   see. **Four misses across two independent reviews of the same manifest.** Treat any future
>   claim that S2 is complete as unsupported.

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
   **Corrected 2026-08-12:** the *code* that reads those rows is now in scope and is
   `ENFORCEMENT_KEEP` — **E13-E15** (`scripts/alpha_eval.py`,
   `asxos/domain/research/alpha_loader.py`, `asxos/domain/research/alpha_eval.py`). The original
   manifest argued for retaining the rows while classifying their only reader as `ACTIVE_REMOVE`;
   retained evidence with no reader is not retained evidence.
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
   **Demonstrated, not hypothetical (2026-08-12):** the independent challenge found three real
   misses of exactly these shapes — `demo.py` (a *token-bearing* file that no seed reached),
   `cli/main.py:21` (a token-blind import edge), and the `signal_outcomes` consumer chain
   (E13-E15) that Limit #3 itself predicted. **Treat S2 as a floor, not a boundary.**

---

## Independent challenge — `security-engineer` review, 2026-08-12

An independent `security-engineer` review was run against this manifest with a mandate to falsify
it. Its findings are applied in place above; this section is the verification record, so a reader
can tell what was checked, what held, and what did not.

### What reproduced exactly

| Claim | Result |
|---|---|
| S1 loose pattern = **207 files / 989 lines** at `fad6215` | **Reproduced exactly** |
| S1 boundary pattern = **203 files / 969 lines** at `fad6215` | **Reproduced exactly** |
| Finding 1 removal order (R1 → R2/R3 → R19) | **Confirmed verbatim** |
| Four declared inverse-polarity bans (E5-E8) | **All four confirmed** |

### What it found

**A fifth inverse-polarity ban** the manifest missed entirely:
`asxos/domain/decision_engine/demo.py` — now **E12**. This is the finding with the worst blast
radius, because the file carries 4 S1 tokens and *no classification at all*, which is the exact
profile a token sweep treats as safe to delete.

**Seven corrections** (H1-H3, M1-M3, L1), plus one framing softening (L2) — all applied above:

| # | Correction | Where |
|---|---|---|
| **H1** | The proposed allowlist is missing **56 files**; the CI step would be red on day one, and the cheapest green disarms the tripwire | [Allowlist completeness](#allowlist-completeness--measured-not-estimated) |
| **H2** | `decision_engine/demo.py` missing entirely — a fifth Model A **ban** | **E12** |
| **H3** | A seventh token-blind site (`cli/main.py:21`) and a second removal-order constraint | **R13b**, Finding 4 |
| **M1** | R20 reclassified — `alpha_eval.py` is rule #11's **exit instrument**, not disposable tooling | **E13-E15** |
| **M2** | A6 under-cited (5 refs, not 2) and silently-failing under non-strict Jinja | **A6** + note |
| **M3** | The CI pattern rationale was fabricated; conclusion kept, argument replaced | CI Mechanism §1 |
| **L1** | `scripts/product_health.py:77` misattributed to `retrain_model_a` | Tier 4 note |
| **L2** | "Four independent enforcement layers" overstates live coverage | S2 preamble |

### Spot-checks that came back sound

The review sampled the `ACTIVE_REMOVE` set for false positives — sites classified for deletion
that actually carry enforcement value. Two were checked in depth and **both confirmed correctly
classified**:

- **R14 (`asxos/cli/model.py`)** removes **no quarantine control.** It is the `is_active` flip;
  `approved_for_allocation` — the column the quarantine actually turns on — has no CLI writer at
  all. Deleting `asx model activate|list` does not weaken the gate.
- **R21 (`asxos/config.py` healthcheck env var)** is safe to remove out of order.
  `asxos/config.py:10` sets `extra="ignore"` on the settings model, so a Render service still
  carrying `HEALTHCHECK_URL_RETRAIN_MODEL_A` in its environment will **not** fail to start after
  the field is deleted.

### Side observation — the gate's armed state is not visible anywhere

**No CLI surface anywhere in the repo displays `approved_for_allocation`.** `asx model list`
shows `is_active` only. The single column that determines whether rule #11 is mechanically armed
is verifiable **only by raw SQL** against `model_versions`.

That is not a retirement blocker and no correction above depends on it. It is recorded because it
is the operational counterpart to this manifest's opening argument: the enforcement point has no
Model A token *and* no human-readable status surface, so "is the quarantine actually on right
now?" cannot be answered by anyone who is not willing to open a SQL console. Worth a one-line
addition to `asx model list` whenever that command is next touched — or worth noting as
permanently lost if R14 removes the command outright.
