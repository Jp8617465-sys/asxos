# asxos executable roadmap (2026-07-04)

**Status:** current
**Scope:** whole repo — turns the three 2026-07-04 audits into one sequenced roadmap + the smallest safe next PRs
**Last verified:** 2026-07-04 against repo @ `claude/live-readiness-audit-plan-ajfipv` + live DB (`gxjqezqndltaelmyctnl`)
**Read priority:** read first (with `docs/session-handoff-2026-07-04.md`) until PR 1 lands
**Session type:** read-only planning + sequencing. No code, migrations, DB writes, Render, or Healthchecks changes. Every edit below is *proposed*, not applied. Nothing implements until reviewed and approved.
**Supersedes:** N/A (consolidates, does not replace, `docs/live-readiness-audit-plan-2026-07-04.md` and `docs/model-a-audit-and-extension-plan-2026-07-04.md` — those hold the verbatim Model A / DB-scoping / Rust-Go detail; this is the sequencer)

Routed through the `CLAUDE.md` subagent policy — nine agents consulted this session (advisory/read-only), incremental to their prior-turn analysis. Full **Agent Consultation Log** is §B.

**Required-reading status (branch-only recorded, not substituted):** present on this branch — CLAUDE.md, session-handoff-2026-07-04, next-session-backlog, live-readiness-audit-plan-2026-07-04, foundation/{BUILD_GUIDE, phase-b-failure-postmortem, phase-4-architecture, spec/tax-alpha}, .claude/agents/README, .claude/rules/portfolio-conventions, render.yaml, pyproject.toml, alpha_eval.py, monitor.py, lots.py, job_monitor.py. **ABSENT (branch-only, off `main`):** `docs/research/claude-fundamentals-audit-handoff-2026-07-04.md` + `docs/research/repo-navigation-audit-and-plan-prompt-2026-07-04.md` (branch `claude/fundamentals-audit-report-2026-07-04`, PR #15) and `docs/asxos-live-readiness-audit-2026-07-04.md` (branch `claude/fundamentals-live-readiness-audit-2026-07-04`). All three were read via `git show` and are represented faithfully here.

---

## A. Executive decision

**Fix navigation first, then enforce it, then do the product work — and build nothing new in Rust/Go.** Concretely: docs/source-of-truth cleanup is the P0 that unblocks every future session; agent DB read-only scoping is the parallel P0 security gate before Phase 2c; agent-routing hardening is a *lightweight process layer* that lands after docs cleanup stabilizes `CLAUDE.md` (it transcribes those tables) and must not become a side-quest; the Model A quarantine stays; research-store factor conclusions wait for a populated panel; and Rust/Go stay unbuilt (every measured hot path is weekly-trivial or already native — the one >1s cost is a pure-Python fix, Part E). `uv` as the CI installer is the single highest-ROI tech upgrade.

**System-architect's one structural correction to the starting order:** agent-routing hardening *cannot* precede docs cleanup, because its artifact (`.claude/agent-routing.json`) is a machine transcription of `CLAUDE.md`'s delegation tables — and docs cleanup edits `CLAUDE.md`. Author routing first and it pins tables that then move underneath it. So the anti-side-quest framing is structurally true, not just discipline.

---

## B. Agent Consultation Log

Nine agents, all advisory/read-only, incremental to their prior-turn consultation this session. Six required + three conditionally-required (portfolio-invariant-guard, tax-spec-conformance, requirements-analyst — required because this plan touches portfolio/risk, tax, and unspecced features). **All nine consulted; no stop-condition applies.**

### system-architect — CONSULTED
- **Asked:** confirm/correct the executive sequence across the five workstreams + agent-routing; ordering hazards; does routing-as-gate fit the architecture.
- **Findings:** confirm 1→8 with **2 parallel to 1** and **3 pinned after 1's CLAUDE.md edits settle**; routing lint + DB-scoping frontmatter grep must share **one agent-manifest test harness** (DB-scoping lands it, routing extends it); land uv before/with 2–3; routing-as-gate is the same reify-a-convention move the repo already makes 3× (review-gate, migration 0034 trigger, DB-scoping grep) — keep it declarative/advisory and state the honest limit (a lint can't prove a human consulted).
- **Accepted:** all — this is the spine of §C. **Rejected/deferred:** nothing. **Uncertainty:** none material.

### backend-architect — CONSULTED (continued)
- **Asked:** where the routing lint runs (CI vs hook vs both); composition with review-gate.sh; migration/DB implications.
- **Findings:** **CI authoritative** (own `agent-routing.yml` workflow, `fetch-depth: 0`, diff against `origin/<base>…HEAD`, `permissions: contents: read`, **fail-closed** on parse error), local hook optional fast-feedback only (review-gate is fail-open/forgeable, `review-gate.sh:9-12`); keep **disjoint** from review-gate (different trigger/subject/marker-namespace, don't chain on the forgeable marker); override must be **CI-visible/logged**, not a silent `touch`; **no migration, no DB access** — pure git-diff + parse.
- **Accepted:** all (§E). **Rejected/deferred:** bolting it onto full-check.yml. **Uncertainty:** none material.

### tech-stack-researcher — CONSULTED (continued)
- **Asked:** confirm uv as its own PR + sequencing; does the routing config's parsing add a dependency.
- **Findings:** uv = standalone PR, land **first & independent**, no `uv.lock` yet; **use JSON not YAML** for the routing file (`json`/`tomllib` are stdlib; **PyYAML is not a current dependency** and would add a C-extension for one dev-only lint) — **rename to `.claude/agent-routing.json`**.
- **Accepted:** all — **this overrides the `.claude/agent-routing.yml` filename in the brief; the roadmap uses `.json`.** **Rejected/deferred:** YAML. **Uncertainty:** none material.

### performance-engineer — CONSULTED (continued, traced the flow)
- **Asked:** classify the build.py vol-scope finding; minimal fix; test/benchmark; confirm no Rust PR now.
- **Findings:** **stale comment + real over-computation, NOT a correctness bug** — vol for ~1,670 non-buy names is computed, wrapped into candidates, then discarded inside `allocate()` (`allocator.py:187-201`); output is already correct. Fix = **Shape 1** (hoist the buy-eligibility predicate above `build.py:230`), no `allocator.py` change; prove with an **exact-equality allocation-parity test** + micro-benchmark (~4.7s→~80ms @1700→30); **no Rust** — the fix removes the only >1s cost and preserves Decimal determinism.
- **Accepted:** all (§I / PR "Later-A"). **Rejected/deferred:** Shape 2 (allocator-signature change); any Rust kernel. **Uncertainty:** numbers sandbox-local, hold under Render penalty.

### security-engineer — CONSULTED (continued)
- **Asked:** threat-model the routing lint; DB-scoping rollout order.
- **Findings:** it is a **process control, not a security boundary** — design for *visible bypass*, not prevention. Add a **self-referential guard** (edits to the routing config/lint/hooks/agents route to security-engineer) + **CODEOWNERS** on those paths (enforced outside the tree — the one "who guards the guard" control that isn't self-editable); **diff-key** each consultation entry (stale/forged = auto-invalid per diff); override = structured committed token with `justification`+`follow_up`, appended to a countable `.claude/routing-overrides.log`, fail-open on infra errors. **DB-scoping order:** prove `supabase-ro` + green canary **before** the six-agent frontmatter flip (collapses the fail-open window to zero); canary must log ≥1 real drift-detection cycle **before** Phase 2c.
- **Accepted:** all (§D, §E). **Rejected/deferred:** trying to make the lint unbypassable. **Uncertainty:** whether Supabase RO is grant-based (`42501`) vs transaction-flag (`25006`) — the live-fire battery must determine it.

### technical-writer — CONSULTED (continued)
- **Asked:** draft the agent-routing docs surface (CLAUDE.md policy, consultation template, PR template) + confirm docs-cleanup commit order.
- **Findings:** the policy **extends** (not replaces) the existing "Subagents — delegation policy", inserted after the "Review gate" subsection; exact wording + "non-trivial" definition provided (§E.1); `.claude/consultations/TEMPLATE.md` fields with an explicit "**Implementation permission**" field (agents are advisory, not sign-off); PR template warning-only first; **agent-routing lands in a SEPARATE process-hardening PR after docs cleanup** (avoids muddying the doc-only diff; the policy edit is itself non-trivial and wants its own log). Prior docs-cleanup order stands (banners first, map last, CLAUDE.md-pointer merged into the map commit).
- **Accepted:** all (§C, §E). **Rejected/deferred:** same-PR landing of routing + docs cleanup. **Uncertainty:** none material.

### portfolio-invariant-guard — CONSULTED (continued)
- **Asked:** confirm the routing-matrix entry for portfolio.
- **Findings:** `asxos/domain/portfolio/**` → `portfolio-invariant-guard` + `performance-engineer` is right; **route to me additionally:** `tests/test_portfolio_*.py`, portfolio-table migrations, and `asxos/domain/risk/**` from day one; **don't over-route performance-engineer** — it belongs only on `volatility.py` + `asxos/domain/risk/**` (the genuine hot paths), not `constraints.py`/`profile.py`/`types.py`/orchestration.
- **Accepted:** all (§E.2 matrix). **Rejected/deferred:** perf-engineer on non-hot portfolio paths. **Uncertainty:** none.

### tax-spec-conformance — CONSULTED (continued)
- **Asked:** confirm the routing-matrix entry for tax.
- **Findings:** `asxos/domain/tax/**` + `tests/test_tax_*.py` → `tax-spec-conformance` is right, **but the glob must also catch `docs/foundation/spec/tax-alpha.md` (spec-first is the earliest drift-catch point, #8), `asxos/domain/portfolio/tax_overlay.py`, and `rebalance.py`** (out-of-tree spec-cited tax math — §5.1 boundary-defer, loss-harvest disclaimer); make **`requirements-analyst` conditional** — required only when the diff adds/changes a spec section or §11 TC row, not on every tax test edit.
- **Accepted:** all (§E.2 matrix). **Rejected/deferred:** requirements-analyst on every tax edit. **Uncertainty:** none.

### requirements-analyst — CONSULTED (continued)
- **Asked:** acceptance criteria for the agent-routing enforcement system.
- **Findings:** full mini-spec (§E.3): honest-limit criterion (proves *declared*, not *ran*); detections D1–D7; PASS/FAIL/exit contract (fail-closed on parse error once blocking); two-stage rollout gate with fixed-before-start thresholds (≥15 clean PRs, ≥20-PR audited sample, zero false pos/neg, coverage, tested escape hatch); override "louder than compliance" or it's a bypass; add `.claude/agent-routing.json` itself to the D4 sensitive class (self-weakening must be caught).
- **Accepted:** all (§E.3). **Rejected/deferred:** nothing. **Uncertainty:** thresholds are proposed defaults to fix with James before Stage 1.

---

## C. Workstream hierarchy (the mental model)

```
Docs map            = where truth lives          → PR 1 (P0, docs-only)
Agent DB scoping    = what agents may DO          → PR 2 (P0, config/docs + James)
Agent routing       = who must REVIEW  (process)  → PR 3 (after PR 1 settles CLAUDE.md)
Model A audit       = whether the signal is usable → PR 5 (INCONCLUSIVE until ~late Aug)
Research-store       = whether the data works      → PR 4 (after tonight's chain)
Rust/Go strategy    = whether new tech earns a place → deferred; uv (PR 6) is the yes
```
Agent routing sits **above** the five workstreams as process-hardening. It is not the product destination and must not block PR 1.

---

## D. Recommended sequence

| # | Workstream | P | Kind | Comes where / why | Blockers | Required agents |
|---|---|---|---|---|---|---|
| 1 | Docs/source-of-truth cleanup | **P0** | docs-only | **First** — stabilizes `CLAUDE.md` that everything else transcribes; highest-leverage navigation fix (review-gate does not arm — no staged `*.py`) | none | technical-writer (+ system-architect for the map shape) |
| 2 | Agent DB read-only scoping | **P0** | config/docs + **James** | **Parallel to 1**; critical path is James (register `supabase-ro`, witness live-fire), not file edits; hard precondition for Phase 2c | James registers RO server; canary green | backend-architect, security-engineer |
| 3 | Agent-routing hardening | P1 | config/CI/docs | **After 1** (transcribes settled CLAUDE.md tables) and **extends 2's** shared agent-manifest test harness | PR 1 merged; PR 2's manifest-grep harness | system-architect, technical-writer, security-engineer, backend-architect, requirements-analyst |
| 4 | Research-store verification | P1 | read-only DB | **When tonight's chain fires** (time-gated, independent of 1–3) | scheduled chain completes | backend-architect (read-only) |
| 5 | Model A audit job | P1 | code (read-only job) | after data exists; verdict INCONCLUSIVE at 21d/63d until ~late Aug 2026 | James's ChatGPT audit; live history | requirements-analyst; ml via `alpha_eval.py` (no ML agent by policy) |
| 6 | uv CI installer | P1 | CI-only | **before/with 2–3** so new grep/lint tests run under the intended installer; orthogonal, land early | none | tech-stack-researcher, security-engineer |
| 7 | Risk report / DecisionEvidence | P2 | design→code | after risk/evidence preconditions; no allocator change | Model A + factor panel | system-architect, backend-architect, portfolio-invariant-guard, performance-engineer |
| 8 | Rust/Go revisit | P2 | none now | only on a **proven** bottleneck after 5+7 | measured budget miss on Render | system-architect, tech-stack-researcher, performance-engineer, security-engineer |

Model A quarantine (CLAUDE.md #11) stays throughout. Phase 2c does not start before #2 ships (server proven + canary logged ≥1 cycle + CI guard merged).

---

## E. PR plan (smallest safe next PRs)

Full verbatim edit blocks for PRs 1–2 already live in `docs/live-readiness-audit-plan-2026-07-04.md §6/§7` and `docs/model-a-audit-and-extension-plan-2026-07-04.md` Parts A/B/D. This section adds the **new** artifacts (agent-routing) and the per-PR contract.

### PR 1 — docs/source-of-truth cleanup (P0, docs-only)
- **Purpose:** one navigable entry point; kill the branch-only/stale/contradiction problem.
- **Files:** `docs/README.md` (new map — **must include `docs/foundation/BUILD_GUIDE.md` + `phase-b-failure-postmortem.md` in read-first**, the two CLAUDE.md designates that the earlier §3 map omitted), `README.md`, `CLAUDE.md` (pointer merged into the map commit; TC-20 block `:125-127` + spec-version `:122`), `docs/next-session-kickoff.md` (stale banner), `docs/foundation/phase-4-architecture-system-architect.md` (supersede banner), `docs/next-session-backlog.md` (TC-20 `:293-296` + `§:343-393`; "six not five" `:225`), `.claude/agents/{tax-spec-conformance.md:9,28, README.md:71}`, status headers on the key docs, optional header-lint plan.
- **Commit order (technical-writer, confirmed):** content fixes + banners first → status headers → `docs/README.md` map **last** over a settled tree, with the CLAUDE.md pointer merged into that commit.
- **Required agents:** technical-writer (owns), system-architect (map shape). **Tests/checks:** none (docs-only); optional header-lint added as its own commit.
- **Do-not:** touch code/migrations/Render; delete any doc (banner/header/archive only); forward-reference the routing policy (leave a stub, add the real pointer in PR 3).
- **Approval:** James approves the map + README rewrite before apply.

### PR 2 — agent DB read-only scoping (P0)
- **Purpose:** technical read-only enforcement for the 6 execute_sql agents before Phase 2c.
- **Files:** MCP config (out-of-repo, James), `.claude/agents/*.md:4` (frontmatter flip — **only after** the server is proven), `.claude/rules/portfolio-conventions.md`, `docs/next-session-backlog.md:234-254`, new CI guard (frontmatter allowlist + egress ban + `SECURITY DEFINER` grep) as the **shared agent-manifest test harness** PR 3 will extend, canary job.
- **Order (security-engineer):** (1) register `supabase-ro` + run the live-fire battery [assert `42501` not `25006`; confirm mutating mgmt tools gone; COPY/`pg_read_server_files`/`CREATE FUNCTION` probes]; (2) stand up the canary, prove it alerts on a write-capable test server, then point at real RO; (3) flip the six frontmatters + land CI guard; (4) regression-check the human write path.
- **Required agents:** backend-architect, security-engineer. **Tests/checks:** the live-fire battery (rolled-back), the CI frontmatter guard, canary green ≥1 cycle.
- **Do-not:** flip frontmatters before the server is proven; start Phase 2c before all four steps green.
- **Approval:** James registers the server and witnesses the battery (steps require operator action).

### PR 3 — agent-routing hardening (P1, process — **after PR 1**, extends PR 2's harness)
- **Purpose:** make "who must review" a lightweight, visible, enforceable gate.
- **Files (new):** `.claude/agent-routing.json` (**JSON, not YAML** — tech-stack), `scripts/lint_agent_routing.py`, `.claude/consultations/TEMPLATE.md`, `.github/pull_request_template.md`, `.github/workflows/agent-routing.yml` (own workflow, `fetch-depth: 0`, `permissions: contents: read`), `CODEOWNERS` (on `.claude/agent-routing.json`, the lint, `.claude/hooks/`, `.claude/agents/`), `CLAUDE.md` ("Agent Routing Plan" subsection), `.claude/routing-overrides.log`.
- **Required agents:** system-architect, technical-writer, security-engineer, backend-architect, requirements-analyst.
- **Tests/checks:** the lint's self-consistency (D5/D6); a fixture PR that exercises PASS, a missing-agent FAIL, and a valid override. **Rollout:** warning-only first; flip to blocking only when requirements-analyst's Stage-1 gate is met (§E.3).
- **Do-not:** add PyYAML; fail-open on parse errors once blocking; let it spawn agents or grow dispatch logic (stays declarative); block PR 1.
- **Approval:** James fixes the Stage-1 thresholds before Stage 1 begins.

### PR 4 — research-store verification report (P1, read-only) — see §G. PR 5 — Model A audit job (P1) — see §F. PR 6 — uv CI installer (P1) — see §H.4.
### Later-A — build.py vol-scoping fix (Python-only, own small PR) — see §I. Later-B — risk report/DecisionEvidence; Later-C — Rust only if benchmark gates pass (§H).

---

## F. Model A audit plan

Unchanged from `docs/model-a-audit-and-extension-plan-2026-07-04.md` Part A (the full design). Recap of the binding facts and criteria (requirements-analyst, adopted):

- **Falsifiable claims:** C1 decay / C2 reversal-by-21d / C3 horizon-mismatch (the one that matters) / C4 fragility.
- **Data + the ceiling:** 15 `as_of` dates 2026-05-20→07-02, ~1,700 syms, regimes neutral(10)/bear(5), **no bull**; prices end 2026-07-02 → **only ~30 trading days forward exist**, so **63d+ forward IC is unmeasurable on live signals today**; effective obs 5d≈8–9, 21d≈**2**, ≥63d=**0**.
- **Two datasets:** live post-training (short horizons, unbiased, thin) + bias-labeled pre-training walk-forward (long horizons, indicative not decision-grade).
- **Decision artifact:** `alpha_eval.py::evaluate()` `AlphaReport`, **not ad-hoc SQL**. Data-sufficiency gate first (`effective_n≥8`, ≥2 regimes) → else INCONCLUSIVE.
- **Verdicts:** PASS (lift #11) / FAIL-A (horizon mismatch → cadence redesign) / FAIL-B (no edge → retire) / **INCONCLUSIVE (current state)** — all mapped to `AlphaReport` fields in the Part-A table.
- **Timeline:** 21d powered ≈ late Aug 2026; 63d ≈ Q4 2026; 252d ≈ mid-2027.
- **Reconciliation template** for James's external audit (period/boundary/universe/IC-def/effective-N/horizons/return-basis/cost/NULLs/verdict).
- **Do-not:** retrain, un-suspend, lift #11 on any preliminary/short-horizon result; present pre-training long-horizon numbers as decision-grade.

---

## G. Research-store verification plan (read-only, after the scheduled chain)

Row counts:
```sql
SELECT COUNT(*) FROM rs_security_master;
SELECT COUNT(*) FROM rs_corporate_actions;
SELECT COUNT(*) FROM rs_financial_statements;
SELECT COUNT(*) FROM rs_fundamentals_pit;
SELECT COUNT(*) FROM rs_factor_scores;
SELECT COUNT(*) FROM rs_index_membership;
SELECT COUNT(*) FROM rs_estimates;
```
Factor-set + panel:
```sql
SELECT factor_set_version, COUNT(*), MIN(as_of), MAX(as_of) FROM rs_factor_scores GROUP BY factor_set_version;
```
Job history for `sync_security_master`, `sync_corporate_actions`, `sync_financial_statements`, `derive_fundamentals_pit`, `compute_factor_scores` (status/started/finished/rows_written/error).

- **Success:** `sync_financial_statements` distinct symbols ≈ active universe (~2,382, not 8); `rs_fundamentals_pit` multi-year; `rs_factor_scores > 0` at `fs_v1`; factor-panel join (`rs_factor_scores × prices`) > 0.
- **Partial/crash artifact:** `sync_financial_statements` truncated (the 6/27 crash left 344 rows/8 symbols); `derive_fundamentals_pit` "success" on partial upstream (garbage-in — don't trust the flag). The known fixed-offset chain-ordering defect means PIT/factors may again consume incomplete upstream — a design item, not a hotfix.
- **`jobs/eval_alpha_factors.py` allowed to run ONLY when the panel join > 0** (`jobs/eval_alpha_factors.py:77-86` fails loudly on empty). Then **quote its warnings verbatim**; do not overstate; classify the sleeve exploratory/candidate/rejected — never approved. (Sandbox has no `DATABASE_URL`; from the sandbox, report join-based readiness and say so.)
- A self check-in was armed for 18:00 UTC 2026-07-04 to run this after tonight's chain.

---

## H. Rust/Go/uv/performance strategy

**Position:** No full Rust replatform. No Rust/Go kernel for v1 unless benchmarks prove need. Python stays orchestration/ML/governance/API/CLI/explanation. Rust may *later* own deterministic dimensionless kernels. Go is rejected now (prefer a Python `asx ops drift` subcommand). **uv CI installer is the highest-ROI upgrade.**

### H.1 Rust candidate map
| Candidate | Python source | Bottleneck | Rust benefit | now/later/avoid | Decimal/f64 | may touch money/ledger/governance? |
|---|---|---|---|---|---|---|
| Risk covariance/beta/stress/CVaR | none (risk layer unbuilt) | O(n²) over ~2,382 names — but layer doesn't exist | real, once built | **later** (after risk layer scoped v2) | f64 OK (dimensionless) quantize at facade, deterministic reduction, NaN/inf hard-fail | **no** |
| Tax-lot optimizer | `lots.py:73-107` | size-6-capped, 224µs | ~0 (already trivial) | **avoid** | f64 may **rank**, never ledger; §5.1 stays Python | **no** — flag-not-assess, spec amendment first |
| Backtest/sim loop | `train.py:114-191` | LightGBM **C++** dominates | ~0 (Python glue only) | **later/avoid** | f64 OK if built | **no** |
| Corp-action/return reconstruction | `corporate_actions.py:157-205` | **I/O-bound** (HTTP fan-out) | ~0 (network-bound) | **avoid** | n/a | **no** |

**Boundaries (locked):** f64-legal = correlation/beta/covariance/z-scores/IC/deciles/calibration/vol *estimates*, terminal & quantized at the facade. Decimal-only = money, cost basis, weights-after-normalization-to-dollar-deltas, tax ledger values, tax eligibility day-counts (`is_discountable`), allocator decisions, governance transitions. Every kernel needs a benchmark (Python must first miss a Render cadence budget) + an exact/within-tol parity test; supply-chain gates (cargo-audit/deny, govulncheck, no-secrets build job, pinned lockfiles) precede any merge; prefer out-of-process Go over in-process PyO3 near creds.

### H.2 Go candidate map
| Candidate | Recommendation |
|---|---|
| Go ops CLI | **reject** — 2nd toolchain/CI/distribution for a single-user weekly chore; bypasses the `*.py` review gate |
| **Python `asx ops drift` subcommand** | **preferred** if programmatic reconciliation is ever wanted (reuses httpx/asyncpg/Typer, existing test lane) |
| Render drift / Healthchecks audit / job_runs live-readiness | covered today by `make check-drift` + Render/Supabase MCP; fold into `asx ops` only if MCP proves insufficient |

If ever built out-of-band, `asxosctl` connects as a dedicated **`asxosctl_ro`** direct Postgres role (SELECT on ops/re-derivable tables only, never a write token) — Candidate B from the DB-scoping design, correct for an operator binary.

### H.3 uv CI installer
Switch `full-check.yml:37-40` + `targeted-ml-tests.yml:36-40` to `uv pip install -e ".[ml,dev]"` (+ `astral-sh/setup-uv`). **Benefit:** ~7–10× faster cold install of the shap/llvmlite/sklearn stack. **Risk:** ~none (no runtime/format change). **Rollback:** revert two workflow lines. **Defer `uv.lock`** (separate reproducibility decision). Land **first & independent** — de-risks CI on every later PR.

### H.4 Avoid list
Full Rust rewrite; Django replatform; C++; DuckDB/Polars/Arrow (data <100k rows, forks the Postgres source of truth, breaks NUMERIC(18,6)+backup conventions); Kubernetes; Spark/Ray/Dask; Redis/Celery.

---

## I. Incidental performance finding

`asxos/domain/portfolio/build.py:229-230` passes all ~1,700 `signal_symbols` to `load_vols_for_symbols` despite the `:228` comment "vol for buys only (plan H.2 QUICK-WIN-6)."

- **Classification (performance-engineer):** **stale comment + genuine over-computation, NOT a correctness bug** — vol for the ~1,670 non-buy names is built into candidates and then discarded inside `allocate()` (`allocator.py:187-201`). Output is already correct; it's just ~4.7s (sandbox) / ~15–40s (Render) of wasted work vs the ~0.1–0.4s the conventions doc documents (~50×).
- **Fix (Shape 1, Python-only):** hoist the buy-eligibility predicate (label/exclusion/market-cap, matching `filter_buy_universe`) above `:230` and load vol only for that set → ~80ms; no `allocator.py` change.
- **Tests/benchmark:** **exact-equality** allocation-parity test (identical `targets`: symbol/`target_weight`/`inv_vol_score`/`signal_label`/order/`constraint_log`) + a guard case (STRONG_BUY with thin history → identical silent-omit) + a micro-benchmark N∈{30,100,500,1700} on Render hardware (~4.7s→~80ms).
- **Docs to refresh:** the "~0.1–0.4s / 30 names" estimate in `.claude/rules/portfolio-conventions.md` ("Decimal-only arithmetic") is stale — update alongside the fix.
- **Required agents (implementation):** performance-engineer + portfolio-invariant-guard (+ backend-architect if the query shape changes). **Own small PR.** **Not fixed here.**

---

## J. Do-not-change list

- No code/migrations/DB-writes/Render/Healthchecks changes until a plan is approved.
- Do not let agent routing (PR 3) block or precede the docs cleanup (PR 1).
- Do not author `.claude/agent-routing.json` before PR 1 stabilizes `CLAUDE.md`; do not use YAML/PyYAML — JSON, stdlib.
- Do not flip agent frontmatters before `supabase-ro` is live-fire-proven and the canary is green; do not start Phase 2c before PR 2 is fully green + canary logged ≥1 cycle.
- Do not lift CLAUDE.md #11 / retrain / un-suspend on any preliminary result; do not treat pre-training long-horizon numbers as decision-grade.
- Do not run `eval_alpha_factors` conclusions before the factor panel populates; quote its warnings verbatim when it does.
- Do not build Rust/Go now; do not adopt DuckDB/Polars; do not open a Go/sibling-repo track.
- Do not fix the build.py vol-scope issue in a planning session; do not move tax/governance/Decimal-money/model-inference to Rust/Go ever.
- Do not delete docs; banner/header/archive only. Do not merge PR #15's code as a side effect of a docs cleanup; land branch-only docs on `main`.

---

## K. Questions / approvals needed from James

1. **Approve PR 1's docs map + README rewrite shape** (esp. adding BUILD_GUIDE + postmortem to read-first, and merging vs archiving the three branch-only audit docs).
2. **Register `supabase-ro`** and witness the live-fire battery (PR 2 cannot complete without this operator action); provide the Healthchecks.io API key for the canary + the 13 missing deadman URLs.
3. **The ChatGPT Model A audit** — still the top blocker; §F's reconciliation table is ready for it.
4. **Fix the Stage-1 routing thresholds** (default: ≥15 clean PRs, ≥20-PR audited sample, 7-day override window) before Stage 1 begins; confirm `.claude/agent-routing.json` (JSON) over the brief's `.yml`.
5. **Confirm the sequence** (docs → DB-scoping ∥ → routing → research-store → Model A → uv), and that agent routing stays a lightweight process layer, not a product workstream.
6. Lower-priority, unchanged: HUBS lock-date + acquisition FX; review of `agent_runs` #3/#4.
