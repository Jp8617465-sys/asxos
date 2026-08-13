# Scheduler inventory — executing vs declared (2026-08-13)

**Work order:** `P1-03` — "Reconcile executing and declared schedules"
(`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md:720`).
**Depends on:** `P1-01` (merged, `6360dbb`, PR #98).
**Completion proof required:** one scheduler inventory; no active Model A invocation.
**Scope label:** `RENDER-RETIRE` (shared with `P3-01`), per `docs/product/roadmap-state.md:116`.

This document is **the single authoritative answer** to "what actually runs, and when."
It supersedes `render.yaml`'s self-description as source of truth for every scheduling
question.

---

## 0. Method, and the one probe deliberately NOT run

Everything below is derived from three read-only sources, all at `origin/main` = `6360dbb`:

1. the ten files in `.github/workflows/` (read; never edited — authority-guarded);
2. `render.yaml` (read; never edited — authority-guarded);
3. `gh run list` observation of real run history.

**No Render probe was performed, by instruction.** `make check-drift` was not run, no
`$RENDER_API_KEY` was requested, `api.render.com` was not called, and no Render service was
inspected or recreated.

> **Superseded instruction.** `docs/product/model-a-reference-manifest.md:461` says
> *"P1-02 must run `make check-drift` first"* to establish whether the Model A crons are
> live, and repeats the requirement at `:344`, `:471`, and `:978`. **That instruction is
> void.** The governor ruled at authority-ladder level 0 on 2026-08-12 that **Render was
> deleted**, and explicitly forbade requesting a key, inspecting, mutating, or recreating
> Render — recorded at `docs/product/roadmap-state.md:116` (defect #4). The manifest was
> written before that ruling landed and could not have known it.
>
> P1-03 answers the manifest's open question by a **different and stronger route**: rather
> than asking whether the declared Model A crons are alive on a platform that no longer
> exists, it proves that the scheduler which *does* exist never invokes them (§3). That
> proof holds regardless of what Render's API would have said.

**Trust boundary, stated plainly.** "Render was deleted" is recorded as James's ruling, not
as a verified observation — the same caveat `roadmap-state.md:116` carries, and the reason
`docs/product/target-architecture.md:1535-1537`'s "UNVERIFIED" note stands unresolved *by
instruction*, not by omission. Nothing in this inventory depends on that ruling being true:
§3's proof is about GitHub Actions, and it would be equally valid if Render were still
running (it would then simply mean a second, unmonitored scheduler existed — see §4 gap G7).

---

## 1. The executing inventory — GitHub Actions

Ten workflows. Five are scheduled (the actual cron substrate), four are event-driven CI,
one is manual-only.

### 1a. Scheduled — the live cron fleet

| Workflow | Cron (UTC) | Cadence | What it runs | Last observed scheduled run | Result |
|---|---|---|---|---|---|
| `daily-brief.yml` | `30 20 * * 0-4` | Sun–Thu = Mon–Fri AEST | 12 steps in dependency order (see below) | 2026-08-12T21:12:49Z | success |
| `us-positions.yml` | `30 21 * * 1-5` | Mon–Fri, post-NYSE-close | `jobs/check_us_positions.py` | 2026-08-12T22:10:01Z | success |
| `pipeline-health.yml` | `0 22 * * *` | daily | `jobs/check_cron_health.py` | 2026-08-12T22:44:06Z | success |
| `backup.yml` | `30 13 * * *` | daily | `scripts/backup_irreplaceable.sh` (+ optional restore drill on dispatch) | 2026-08-12T14:35:03Z | success |
| `weekly-research.yml` | `0 16 * * 6` | Saturday | 6 research-store steps in order | 2026-08-08T16:38:49Z | **failure** (see G6) |

**`daily-brief.yml` step order** (`.github/workflows/daily-brief.yml:78-115`) — the order *is*
the dependency graph; a failed step blocks every step below it:

`sync_prices` → `validate_price_data` → `snapshot_portfolio` → `ingest_market_context` →
`ingest_underlyings` → `ingest_regulatory` → `ingest_news` → `ingest_sentiment` →
**`compose_brief`** → `score_macro_theses` → `check_au_positions` →
`check_thesis_invalidations`.

The three post-brief steps sit deliberately *after* the send, so a failure there can never
cost James the brief itself (`:105-106`).

**`weekly-research.yml` step order** (`:53-69`):
`sync_universe` → `sync_security_master` → `sync_corporate_actions --active-only` →
`sync_financial_statements --active-only` → `derive_fundamentals_pit` → `sync_fundamentals`.

### 1b. Event-driven CI — no schedule

| Workflow | Trigger | What it runs |
|---|---|---|
| `full-check.yml` | PR → `main`; push to `main` / `claude/**`; dispatch | `ruff .` + `mypy asxos` + full `pytest` |
| `targeted-ml-tests.yml` | PR → `main`; push to `main` / `claude/**`; dispatch | ruff + 11 targeted model-safety test files. **Runs ML *tests*; invokes no ML *job*.** |
| `migration-integration.yml` | PR/push touching `migrations/**`, backup script, or the two named workflows; dispatch | migration 0043 behavioural contract on PostgreSQL 17 |
| `pr-review-agent.yml` | PR opened/reopened/synchronize/ready; push to `main` | `scripts/pr_review_agent.py` (comment-only) |

### 1c. Manual-only

| Workflow | Trigger | What it runs |
|---|---|---|
| `claude-execute.yml` | `workflow_dispatch` **only** | `anthropics/claude-code-action@v1` under scoped `--allowedTools`, draft-PR ceiling. No automatic event triggers — by design, since repo events can carry untrusted text (`:22-24`). |

### 1d. Observed schedule drift — GitHub cron starts late, fleet-wide

`daily-brief` starting 31–44 min after its `30 20` cron is real, and it is **not specific to
that workflow**. Every scheduled workflow starts late; the observed range across the fleet is
**+31 to +67 minutes**:

| Workflow | Cron | Observed starts | Delay |
|---|---|---|---|
| `daily-brief` | 20:30 | 21:12:49, 21:13:59, 21:10:42, 21:01:31 | **+31m31s … +43m59s** |
| `us-positions` | 21:30 (new) | 22:10:01 | +40m01s |
| `us-positions` | 13:30 (old) | 14:36:32, 14:37:08 | +66m32s, +67m08s |
| `pipeline-health` | 22:00 | 22:44:06, 22:46:25, 22:40:29, 22:34:12, 22:32:09 | +32m09s … +46m25s |
| `backup` | 13:30 | 14:35:03, 14:34:57 | +64m57s, +65m03s |
| `weekly-research` | Sat 16:00 | 16:38:49 | +38m49s |

This is documented, expected GitHub behaviour — `daily-brief.yml:25-26` states it up front:
*"GitHub cron is best-effort: runs can start minutes late at busy hours. Acceptable for a
daily brief; not for market-microstructure timing."* The observation here is that "minutes"
is in practice **half an hour to an hour**, consistently.

**Practical consequences to hold in mind, not to fix here:**

- The brief targeted 06:30 AEST; it lands nearer **07:10–07:15 AEST**.
- `us-positions` at `30 21` was chosen with a deliberately thin margin — 21:30 UTC is only
  30 minutes past the 16:00 ET close under EST (`us-positions.yml:6-8`). A +40 min start
  turns that thin margin into a comfortable one, so the drift currently *helps*. Anyone
  later "fixing" the drift must re-check that margin rather than assume it.
- `backup`'s ~65 min drift is harmless (daily snapshot, no downstream timing dependency).

---

## 2. The declared-but-dead inventory — `render.yaml`

`render.yaml` declares **29 services: 1 web + 28 cron** (`render.yaml:8-22`). It is **stale,
non-authoritative dead config**: last touched 2026-07-21 (`9d8dd9d`), i.e. *before* both the
2026-08-08 Render→Actions migration and the 2026-08-12 deletion ruling. Its own header still
claims *"This file is the source of truth for what Render runs"* (`:3-4`) and still instructs
`make check-drift` (`:5-6`). **Both claims are false as of 2026-08-13.**

Disposition key: **ADOPTED** = the work migrated into a GitHub Actions workflow ·
**RETIRE** = deliberately not migrated, delete with the manifest · **DEFER/DECIDE** = needs
a governor call before it can be retired or re-homed.

| # | Declared service | Declared cron | Command | Disposition | Reasoning |
|---|---|---|---|---|---|
| 1 | `asxos-api` (web) | — | `uvicorn asxos.api.main:app` (`:43`) | **DECIDE** | The only non-cron service. A web service has no Actions equivalent; whether the API still needs a host at all is a governor question, not a scheduler one. Also the `fromService` env source for all 28 crons — deleting it is what makes every `fromService` block moot. |
| 2 | `asxos-sync-universe` | `0 16 * * 6` | `jobs/sync_universe.py` | **ADOPTED** | `weekly-research.yml:54`, step 1 |
| 3 | `asxos-sync-security-master` | `10 16 * * 6` | `jobs/sync_security_master.py` | **ADOPTED** | `weekly-research.yml:57`, step 2 |
| 4 | `asxos-sync-corporate-actions` | `30 16 * * 6` | `jobs/sync_corporate_actions.py --active-only` | **ADOPTED** | `weekly-research.yml:60`, step 3 |
| 5 | `asxos-sync-financial-statements` | `50 16 * * 6` | `jobs/sync_financial_statements.py --active-only` | **ADOPTED** | `weekly-research.yml:63`, step 4 |
| 6 | `asxos-derive-fundamentals-pit` | `10 17 * * 6` | `jobs/derive_fundamentals_pit.py` | **ADOPTED** | `weekly-research.yml:66`, step 5 |
| 7 | `asxos-compute-factor-scores` | `30 17 * * 6` | `jobs/compute_factor_scores.py` | **RETIRE** | Explicitly and deliberately not migrated: *"retired with the research quant lane (degenerate 0.000 output, no production reader) — revive as its own workflow if a real quant lane returns"* (`weekly-research.yml:16-19`) |
| 8 | `asxos-sync-prices` | `30 20 * * 0-4` | `jobs/sync_prices.py` | **ADOPTED** | `daily-brief.yml:79`, step 1 |
| 9 | `asxos-sync-fundamentals` | `0 18 * * *` (**daily**) | `jobs/sync_fundamentals.py` | **ADOPTED, cadence changed** | Moved daily → weekly (`weekly-research.yml:69`). Documented at `:9-14`: it ran daily only because it fed Model A's feature engine; the remaining model-independent consumer is the screening evaluator, for which weekly is sufficient. **Lift it back out if a daily consumer returns.** |
| 10 | `asxos-generate-signals` | `50 20 * * 0-4` | `jobs/generate_signals.py` | **RETIRE (Model A)** | The producer of `model="model_a"` rows. Manifest **R22** (`model-a-reference-manifest.md:336`), flagged token-blind. Not in any workflow — see §3. |
| 11 | `asxos-ingest-regulatory` | `55 20 * * *` | `jobs/ingest_regulatory.py` | **ADOPTED** | `daily-brief.yml:94` |
| 12 | `asxos-ingest-news` | `57 20 * * 0-4` | `jobs/ingest_news.py` | **ADOPTED** | `daily-brief.yml:97` |
| 13 | `asxos-ingest-sentiment` | `2 21 * * 0-4` | `jobs/ingest_sentiment.py` | **ADOPTED** | `daily-brief.yml:100` |
| 14 | `asxos-compose-brief` | `0 21 * * 0-4` | `jobs/compose_brief.py` | **ADOPTED** | `daily-brief.yml:103` — the pipeline's payload step |
| 15 | `asxos-retrain-model-a` | `0 16 * * 6` | `jobs/retrain_model_a.py --version v_auto_$(date +%Y%m%d)` | **RETIRE (Model A)** | Manifest **R23** (`:337`). Not in any workflow — see §3. |
| 16 | `asxos-build-portfolio` | `0 20 * * 6` | `ASXOS_PERSONAL_USE=1 jobs/build_portfolio.py` | **DECIDE** | The allocator. **Mechanically dormant already**: it calls the production gate `required=True`, which raises `ModelGateDormant` when no model holds `approved_for_allocation` — rule #11's enforcement point. Manifest **E4** (`:227`) warns that re-scheduling it would alert every Saturday forever, *"the alert-fatigue failure mode that gets quarantines quietly reverted."* Not a Model A artefact; a model-independent allocator is a real future. Governor call. |
| 17 | `asxos-snapshot-portfolio` | `40 20 * * 0-4` | `ASXOS_PERSONAL_USE=1 jobs/snapshot_portfolio.py` | **ADOPTED** | `daily-brief.yml:85` |
| 18 | `asxos-ingest-market-context` | `45 20 * * 0-4` | `jobs/ingest_market_context.py` | **ADOPTED** | `daily-brief.yml:88` |
| 19 | `asxos-ingest-underlyings` | `48 20 * * 0-4` | `jobs/ingest_underlyings.py` | **ADOPTED** | `daily-brief.yml:91` |
| 20 | `asxos-compute-opportunity-cost` | `5 20 * * 6` | `jobs/compute_opportunity_cost.py` | **RETIRE (service) / ADAPT (job)** | The *declared service* is dead and retires with the manifest. The *job* is manifest **A9** (`:389`) — ADAPT, not RETIRE: a `FROM signals` reader whose fix is *"re-derive from realised prices, or retire the job"*, closing cleanup-backlog **R4**. **Do not conflate**: retiring the dead cron declaration does not decide the job's fate. If it returns, it returns as a new workflow with the Model A read removed. |
| 21 | `asxos-detect-theme-stages` | `55 20 * * 0-4` | `jobs/detect_theme_stages.py` | **DECIDE** | Model-independent theme-lifecycle discipline (never writes user-confirmed `themes.stage`). Not Model A; not migrated either. The single clearest candidate for "should have been ADOPTED and was missed" — governor call. |
| 22 | `asxos-check-cron-health` | `0 22 * * *` | `jobs/check_cron_health.py` | **ADOPTED** | `pipeline-health.yml:45`, same `0 22` cron |
| 23 | `asxos-check-us-positions` | `30 13 * * 1-5` | `jobs/check_us_positions.py` | **ADOPTED, schedule disagrees** | `us-positions.yml:18` runs `30 21`. **Gap G1.** |
| 24 | `asxos-check-au-positions` | `5 21 * * 0-4` | `jobs/check_au_positions.py` | **ADOPTED** | `daily-brief.yml:112`, now an ordered post-brief step rather than its own clock |
| 25 | `asxos-check-thesis-invalidations` | `10 21 * * *` (**daily**) | `jobs/check_thesis_invalidations.py` | **ADOPTED, cadence narrowed** | `daily-brief.yml:115`. Daily → Sun–Thu, as a consequence of folding into the weekday brief chain. **Gap G4.** |
| 26 | `asxos-validate-price-data` | `33 20 * * 0-4` | `jobs/validate_price_data.py` | **ADOPTED** | `daily-brief.yml:82`, step 2 |
| 27 | `asxos-check-model-staleness` | `5 21 * * *` | `jobs/check_model_staleness.py` | **RETIRE (Model A)** | Manifest **R24** (`:338`), token-blind. Not in any workflow — see §3. |
| 28 | `asxos-track-signal-outcomes` | `0 3 * * 0` | `jobs/track_signal_outcomes.py` | **RETIRE (Model A)** | Manifest **R25** (`:339`), token-blind. Not in any workflow — see §3. |
| 29 | `asxos-backup-irreplaceable` | `30 13 * * *` | `bash scripts/backup_irreplaceable.sh` | **ADOPTED, schedules agree** | `backup.yml:20`, identical `30 13 * * *`. The only service whose declared and executing crons match exactly. |

### Disposition counts

| Disposition | Count | Services |
|---|---|---|
| **ADOPTED** (work migrated to Actions) | **20** | 2, 3, 4, 5, 6, 8, 9, 11, 12, 13, 14, 17, 18, 19, 22, 23, 24, 25, 26, 29 |
| **RETIRE — Model A** | **5** | 10, 15, 20, 27, 28 |
| **RETIRE — non-Model-A** | **1** | 7 (`compute-factor-scores`) |
| **DECIDE** (governor) | **3** | 1 (`asxos-api`), 16 (`build-portfolio`), 21 (`detect-theme-stages`) |
| **DEFER** | **0** | — |
| **Total declared** | **29** | 1 web + 28 cron |

Of the 20 ADOPTED, **17 migrated unchanged**, **2 changed cadence deliberately** (9, 25) and
**1 changed clock deliberately** (23, a bug fix).

---

## 3. Proof: the executing scheduler never invokes Model A

Run at `origin/main` = `6360dbb`, working tree verified clean against it
(`git diff --stat origin/main` → empty):

```
$ grep -rnE 'generate_signals|retrain_model_a|check_model_staleness|track_signal_outcomes|compute_opportunity_cost' .github/workflows/
grep exit status: 1
```

**Zero matches across all ten workflow files.** (`grep` exit status 1 = "no lines selected",
which is the intended result; status 2 would mean an error, and status 0 would mean a hit.)
Files searched: `ls -1 .github/workflows/ | wc -l` → **10**.

A second, broader check over the five *scheduled* workflows — the only ones that fire without
a human — returns zero for the token `signals` as well:

```
$ grep -rncE 'model_a|model-a|signals' .github/workflows/{weekly-research,pipeline-health,daily-brief,us-positions,backup}.yml
.github/workflows/weekly-research.yml:0
.github/workflows/pipeline-health.yml:0
.github/workflows/daily-brief.yml:0
.github/workflows/us-positions.yml:0
.github/workflows/backup.yml:0
```

**Conclusion.** No Model A producer, retrainer, or monitor is invoked by any scheduled
workflow, by any CI workflow, or by the manual harness. The five Model A crons (services 10,
15, 20, 27, 28) exist **only** as text in a dead manifest.

**Scope of this proof — what it does and does not cover.** It covers *scheduler invocation*.
It does **not** claim Model A code is absent from the repo — it is present and inventoried by
`P1-01` (`docs/product/model-a-reference-manifest.md`), and its removal is `P1-02`'s job.
Two live edges are deliberately in scope of the proof and pass:

- `targeted-ml-tests.yml` runs eleven ML **test** files (`:60-71`), including
  `test_retrain_wiring.py` and `test_train_walk_forward.py`. These exercise model code in a
  sandbox with no live database, no secrets, and no Render (`:7-9`). They are *assertions
  about* Model A, not *invocations of* it — no `job_runs` row, no `signals` write.
- `full-check.yml` runs the whole pytest suite, with the same property.

**Rule #11 status.** Unaffected and intact. Rule #11 bars *using* Model A output as a basis
for capital decisions; this inventory shows the stronger fact that nothing is even producing
that output on a schedule. The mechanical enforcement point (`approved_for_allocation` → the
production gate → `ModelGateDormant`) is untouched by this document.

---

## 4. Gap list — where declared and executing disagree

| # | Gap | Declared | Executing | Severity |
|---|---|---|---|---|
| **G1** | `check_us_positions` clock | `render.yaml:646` (comment) and `:654` — `30 13 * * 1-5`, i.e. US market **open** | `us-positions.yml:18` — `30 21 * * 1-5`, after the 16:00 ET close on both sides of DST | **Stale declaration only.** The executing side is correct and observed green (2026-08-12T22:10:01Z). This is roadmap-state defect #5's named residual. **`jobs/check_us_positions.py:5-8` is already correct** — its docstring reads "Runs Mon-Fri 21:30 UTC" and explains the prior bug. `render.yaml` is now the *sole* remaining carrier of the wrong time. |
| **G2** | `score_macro_theses` has no declaration | absent from `render.yaml` entirely | `daily-brief.yml:109` — runs every weekday | **Executing-only job.** The reverse of every other gap: it was wired straight into Actions and never existed on Render. `roadmap-state.md:419` still carries "wire the `score_macro_theses` Render cron" as an open item — **that item is satisfied, by a different substrate.** |
| **G3** | 8 declared jobs execute nowhere | services 7, 10, 15, 16, 20, 21, 27, 28 | no workflow | **5 are intentional** (Model A retirements: 10, 15, 20, 27, 28). **1 is intentional** (7, quant lane retired). **2 are unresolved** (16 `build-portfolio`, 21 `detect-theme-stages`) — see §6. |
| **G4** | `check_thesis_invalidations` cadence | `render.yaml:722` — `10 21 * * *` (7 days/wk) | `daily-brief.yml:115` — Sun–Thu only (5 days/wk) | **Silent narrowing.** A consequence of folding a daily job into a weekday chain, not a decision anyone recorded. Thesis invalidations are no longer checked Fri/Sat UTC. Low risk (markets closed), but it is an undeclared behaviour change. |
| **G5** | `sync_fundamentals` cadence | `render.yaml:259` — `0 18 * * *` (daily) | `weekly-research.yml:69` — Saturdays | **Intentional and documented** (`weekly-research.yml:9-14`). Listed for completeness; the reversal trigger is recorded ("if a daily consumer returns, lift the step back out"). |
| **G6** | `weekly-research` has never succeeded on schedule | — | one scheduled run ever: 2026-08-08T16:38:49Z, **failed at step `Derive fundamentals PIT`** | **Open, unverified.** The fix landed *after* the failure: `36b07fb` "fix(research): bound PIT derivation batches (#85)", 2026-08-11 — three days later. **The Saturday 2026-08-15 run is the first real test of that fix.** Until it goes green, the entire weekly research chain (6 jobs, incl. the fundamentals the screening evaluator reads) is unproven on the new substrate. |
| **G7** | `render.yaml` still calls itself source of truth | `:3-6` — "This file is the source of truth for what Render runs… `make check-drift` reconciles" | this document | **The root gap.** A manifest describing a deleted platform, instructing a probe that is forbidden, still parsed by a green test (§5). Anyone reading the repo cold is told the wrong thing by the file that most loudly claims authority. |
| **G8** | `make check-drift` is a dead target | `Makefile:62-63` — prints an instruction to reconcile against `api.render.com/v1` | nothing to reconcile against | **Actively harmful instruction.** CLAUDE.md non-negotiable #2 still mandates this flow. Following it today means requesting a forbidden key for a deleted platform. |
| **G9** | `pipeline-health` failed 4 consecutive scheduled runs | — | 2026-08-08, -09, -10, -11 all **failure**; 2026-08-12 **success** | **Closed, recorded for the record.** `check_cron_health.py` hard-fails when it finds stuck/missing/degraded `job_runs` — that exit 1 *is* the alarm working (`pipeline-health.yml:5-8`). The four reds are the watchdog correctly reporting the Render→Actions transition; the 08-12 green is the fleet settling. Do not "fix" the watchdog. |

**Not a gap:** `backup` (service 29) — `render.yaml:845` and `backup.yml:20` both say
`30 13 * * *`. The one exact agreement in the whole manifest.

---

## 5. DRAFT removal plan for `render.yaml` — for James

> **`render.yaml` is authority-guarded** (`.claude/hooks/authority-guard.sh:64`, alongside
> `CLAUDE.md` and `docs/README.md`). arbi may **draft** this plan; it may not execute it.
> Removal requires **a dedicated, tested PR opened and approved by James**. Nothing in this
> section has been performed. This is a proposal, not a changelog.
>
> Note the guard is broad by design: it blocks Bash commands whose *text* references an
> authority path alongside a write-capable utility, not merely direct edits. The removal PR
> must be authored with that in mind.

### 5.1 What the PR would do

**Delete:**
- `render.yaml` (859 lines, 29 service declarations).

**Delete or rewrite (`Makefile`):**
- `check-drift` target, `Makefile:62-63` — reconciles against a deleted platform (G8).
- `Makefile:1` `.PHONY` list — drop `check-drift`.
- `Makefile:54` and `:60` — `logs` / `deploy` targets that instruct Render REST API calls
  against `asxos-api`. These fall with service 1, and their disposition follows the
  **DECIDE** on `asxos-api` (§2 row 1), so they may need to survive if the API is re-homed.

**Rewrite (`CLAUDE.md` — also authority-guarded, same draft-PR route):**
- Non-negotiable rule **#2** currently mandates *"Manage Render via its REST API… every
  change goes through `render.yaml` + `git push` + `make check-drift`."* This must become
  the GitHub Actions statement, or rule #2 keeps instructing every future session to do the
  forbidden thing.
- The **Stack** table row *"Jobs (M12+) | Render cron services | Render REST API"* →
  GitHub Actions.
- The **Common commands** entry for `make check-drift`.

**Rewrite (`docs/README.md` — authority-guarded):** its deployment source-of-truth pointer.

**Rewrite (comments only, no behaviour change):**
- `jobs/build_portfolio.py:20` — *"Schedule: Saturday 20:00 UTC (render.yaml 0 20 * * 6)"*.
  Note this job is **DECIDE**, not ADOPTED — the honest replacement is "not currently
  scheduled," not a new cron reference.
- `jobs/check_thesis_invalidations.py:127`, `jobs/snapshot_portfolio.py:351`,
  `jobs/check_au_positions.py:152`, `jobs/check_us_positions.py:142`,
  `jobs/compute_opportunity_cost.py:171,174`, `asxos/jobs/_helpers.py:28` — all say the
  `ASXOS_PERSONAL_USE` in-code gate "fails loud rather than relying on `render.yaml` alone."
  The *reasoning is still exactly right*; only the named env source changes to the workflow
  `env:` blocks. **Do not weaken these gates while editing their comments.**
- `tests/test_jobs_personal_use_gate.py:6-7` — same substitution in the module docstring.

### 5.2 Tests that would need to change

**`tests/test_render_backup_build.py` — the blocker. All four tests break.**

The file hard-parses the manifest and asserts the backup service exists:

```python
RENDER_YAML = pathlib.Path(__file__).resolve().parent.parent / "render.yaml"   # :25
BACKUP_SERVICE = "asxos-backup-irreplaceable"                                  # :26

def _backup_service() -> dict:                                                 # :29-35
    doc = yaml.safe_load(RENDER_YAML.read_text())
    services = {s["name"]: s for s in doc["services"]}
    assert BACKUP_SERVICE in services, (
        f"{BACKUP_SERVICE} missing from render.yaml services"
    )
    return services[BACKUP_SERVICE]
```

Every test calls `_backup_service()`: `test_backup_build_command_has_no_apt_get` (:38),
`test_backup_build_command_still_installs_repo` (:48),
`test_backup_runtime_command_unchanged` (:56),
`test_backup_declares_expected_env_var_names` (:64).

**Recommended disposition: delete the file.** It is green assurance about a dead platform —
`roadmap-state.md:116` already names it as such. Its subject was a *Render-native-runtime*
bug (read-only `/var/lib/apt` breaking `apt-get` in the build step, `:4-10`) that **cannot
occur on GitHub Actions**, where `backup.yml:48-69` installs `postgresql-client-17` from PGDG
with `sudo apt-get` and works. The regression it guards is not reachable on the executing
substrate.

**What must be preserved, and where.** Three of its four assertions carry real intent that
should not evaporate with the file. Their executing-substrate equivalents already exist —
verify before deleting, and add the gap if absent:

| Original assertion | Intent | Where it lives on Actions |
|---|---|---|
| `command == "bash scripts/backup_irreplaceable.sh"` (:59) | the entrypoint is the script | `backup.yml:109` |
| `schedule == "30 13 * * *"` (:61) | drift guard on the clock | `backup.yml:20` |
| declares `DATABASE_URL`, `BACKUP_GITHUB_TOKEN`, `BACKUP_REPO` (:74) | required env is wired | `backup.yml:41-43` |
| `pip install -e .` in buildCommand (:51) | repo importable | n/a — the script runs via `bash`, not an installed entrypoint |

A small replacement test that parses `.github/workflows/backup.yml` for the same four
properties would preserve the drift-guard value at the same cost. **Recommended**, but it is
a scope call for the PR author, not a hard requirement.

**`tests/test_authority_guard_hook.py` — does NOT break.** It references `"render.yaml"` at
`:43`, `:119`, `:253`, but `:43` *writes its own* `tmp_path / "render.yaml"` fixture and never
reads the repo file. It tests the guard's path-matching, not the manifest. However: the
guard's protected list at `.claude/hooks/authority-guard.sh:64` would then name a file that
no longer exists. **Harmless but untidy** — a guard entry for a deleted path is inert. Leaving
it costs nothing and preserves the guard if the file ever returns; removing it means touching
the guard, its test's `:119` list, and `:253`. **Recommendation: leave the guard entry alone**
in this PR. It is a separate, smaller decision.

**`.github/workflows/targeted-ml-tests.yml:8`** mentions "no Render" in a comment. Cosmetic.

### 5.3 What must be preserved

1. **Every RETIRE/ADOPT/DEFER/DECIDE disposition in §2.** The manifest is the only surviving
   record of what 29 services were *for*. This document is its designated successor —
   `render.yaml` must not be deleted until §2 is merged, or the reasoning is lost with it.
2. **The three DECIDE rows.** `asxos-api`, `build-portfolio`, and `detect-theme-stages` are
   unresolved. Deleting the manifest deletes the only place they are still written down.
3. **The proven backup path.** `.github/workflows/backup.yml` — including the restore drill
   (`:111-236`, 14-table count verification) — is untouched by this PR.
4. **The `ASXOS_PERSONAL_USE` firewall.** Comment edits only; the in-code hard-fail gates
   stay exactly as they are (`.claude/rules/portfolio-conventions.md` §regulatory firewall).
5. **Rule #11 and the production gate.** Nothing in this PR touches
   `approved_for_allocation`, `resolve_production_model()`, or `ModelGateDormant`.
6. **The `sync_fundamentals` reversal trigger** (`weekly-research.yml:9-14`) — the only
   record of *why* a daily job became weekly.

### 5.4 Sequencing

This PR should land **after** `P1-02` (Model A runtime removal), not before. `P1-02` may want
to cite `render.yaml`'s R22–R25 declarations as it removes their subjects; deleting the
manifest first removes that evidence mid-flight. It is also **independent of `P3-01`**
(Dagster) — retiring dead config is not a scheduler cutover, and must not be bundled with one.

---

## 6. What needs James

Four items. Nothing below has been acted on.

1. **DECIDE — `asxos-detect-theme-stages` (service 21).** Model-independent theme-lifecycle
   discipline, ran weekdays under Render, migrated nowhere. The strongest candidate for
   "should have been ADOPTED and was missed" rather than "deliberately retired." Re-home it
   as a `daily-brief.yml` step, give it its own workflow, or retire it — but decide.
2. **DECIDE — `asxos-build-portfolio` (service 16) and `asxos-api` (service 1).** The
   allocator is mechanically dormant under rule #11 and re-scheduling it would produce a
   weekly dormancy alert forever (manifest E4) — so "leave it unscheduled" is probably right,
   but it should be a recorded decision, not an accident of migration. `asxos-api` is a
   hosting question, not a scheduler one.
3. **APPROVE — the `render.yaml` removal PR (§5).** Authority-guarded; needs James to open or
   authorise it. The key judgement call inside it is whether
   `tests/test_render_backup_build.py` is deleted outright or replaced with a
   `backup.yml`-parsing equivalent.
4. **AMEND — CLAUDE.md non-negotiable rule #2.** It currently instructs every future session
   to manage Render via its REST API and run `make check-drift`. That instruction now points
   at a deleted platform and a forbidden probe. CLAUDE.md is governance — arbi may draft the
   amendment, only James may make it. **This is the highest-leverage of the four**: every
   other item is cleanup, but rule #2 actively misdirects the next agent that reads it.

---

## 7. Provenance

- Branch `claude/p1-03-scheduler-reconciliation`, from `origin/main` = `6360dbb`.
- Evidence gathered read-only: `.github/workflows/` (10 files), `render.yaml` (859 lines),
  `gh run list` history, `git log -- jobs/derive_fundamentals_pit.py`.
- **Not run:** `make check-drift`, any `api.render.com` call, any workflow dispatch, any DB
  query, any production action. No file outside `docs/product/` was modified.
- Authority paths `render.yaml` and `.github/**` were read and cited, never edited.
