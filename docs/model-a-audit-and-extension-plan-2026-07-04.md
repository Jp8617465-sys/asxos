# Model A reliability audit plan + targeted-extension RFC (2026-07-04)

**Status:** current
**Scope:** whole repo — Model A audit design, agent DB role scoping, Rust/Go strategy, docs cleanup hardening
**Last verified:** 2026-07-04 against live DB (`gxjqezqndltaelmyctnl`) + repo @ `claude/live-readiness-audit-plan-ajfipv`
**Read priority:** read first (with `docs/session-handoff-2026-07-04.md` and `docs/live-readiness-audit-plan-2026-07-04.md`) until Part A is executed
**Session type:** read-only planning. No code, migrations, DB writes, Render, or Healthchecks changes were made. Every proposed edit is proposed, not applied.

This plan was produced by routing the work through the repo's subagent policy (`CLAUDE.md` delegation tables). Nine subagents were consulted advisory/read-only; the full **Agent Consultation Log** is §7. The headline deliverable (Part A) is the Model A audit that substitutes for James's ChatGPT audit, which was **not available to read this session** (`docs/session-handoff-2026-07-04.md:14-16,53-54`).

---

## 0. TL;DR

1. **Model A audit (Part A):** the ChatGPT audit is unavailable, so build an in-house one. The honest structural finding: **the horizons the dispute is actually about (weeks-to-months) cannot yet be measured on live signals** — prices end 2026-07-02, signals start 2026-05-20, so only ~30 trading days of forward returns exist. 63-day+ forward IC on live signals = unmeasurable today; 21-day has an effective sample of 2. The audit therefore runs on two datasets (live short-horizon now; bias-labeled pre-training long-horizon), produces its verdict through `alpha_eval.py::evaluate()` (not ad-hoc SQL), and returns **INCONCLUSIVE** for the decision horizons until ~late Aug 2026 (21d) / Q4 2026 (63d). **CLAUDE.md rule #11 stays.**
2. **Rust/Go (Part C):** unanimous across five agents — **no Rust/Go kernel is justified for v1; reject a full rewrite.** Every live blocker (Model A dispute, empty factor panel, docs drift, agent DB scoping) is a correctness/data/security problem, not a performance one. Measured: every candidate hot path is weekly-trivial or already native (LightGBM C++, numpy). The first *defensible* Rust kernel (covariance for a risk report) is gated behind three preconditions that are all currently false.
3. **Agent DB role scoping (Part B):** the §7 read-only-MCP design holds up under independent security review, with three additions — a recurring **runtime canary** (because misprovisioning fails OPEN and CI can't detect it), a `SECURITY DEFINER` CI guard, and asserting error `42501` (grant-based) not `25006` (transaction-flag). Still a P0 before Phase 2c.
4. **Docs cleanup (Part D):** the §3–§6 plan in `docs/live-readiness-audit-plan-2026-07-04.md` is sound but **omits the two docs CLAUDE.md itself designates read-first** (`BUILD_GUIDE.md`, `phase-b-failure-postmortem.md`) — a fresh self-contradiction. Fix that, add a CI header-lint with a 90-day rot rule, reorder the commits, and decouple from PR #15.
5. **Incidental finding (Part E):** `build.py:230` computes vol for ~1,700 symbols not the ~30 buys (comment at `:228` says "buys only") → ~4.7s/build vs documented ~0.1–0.4s. Cheap Decimal-safe fix; flagged, not applied.

---

## Part A — Model A reliability audit plan

*(This is the headline: the study that replaces the unavailable external audit. Design refined against the `requirements-analyst` acceptance-criteria mini-spec — §7.)*

### A.0 The dispute as falsifiable sub-claims

James: *"[Model A signals] greatly diminish after 5 days and completely swing around at 21 days"* (`docs/session-handoff-2026-07-04.md:12-14`). The product worry is a **horizon mismatch**: a 0–5-day-edge model cannot underwrite months-long theses (HUBS: 365-day timeline, `:29`). Sub-claims:

- **C1 (decay):** predictive info peaks short and declines with horizon.
- **C2 (reversal):** IC crosses zero / negative by ~21 days.
- **C3 (horizon mismatch — the one that matters):** no decision-grade predictive info at the weeks-to-months horizons the system holds for, net of cost.
- **C4 (fragility, 2026-06-22 audit):** any edge is illiquid-concentrated, poorly calibrated absolutely, and `expected_return` is non-predictive (`docs/research/alpha-research-audit.md` TL;DR, `:44-48,93,112`).

The question is **not** "is there a signal" — the 2026-06-22 audit already found a real 5-day edge (rank-IC +0.1335, t≈3.01, `alpha-research-audit.md:44-48`). It is: **is `prob_up` decision-grade over real holding horizons, net of cost, at a cadence the system can run?**

### A.1 Data inventory and the binding power constraint (live-verified 2026-07-04)

- **signals** (`model_a`/`v1_5`): 25,514 rows, 15 `as_of` dates 2026-05-20 → 2026-07-02, ~1,700 symbols/date. Regimes: `neutral` 10 dates / `bear` 5 dates — **no `bull` observed** (live query). All 15 dates post-date the 2026-05-21 training snapshot → genuinely OOS.
- **prices**: 2025-01-02 → 2026-07-02, 381 trading days, 1,896 symbols (live query).
- **THE CEILING:** from the oldest signal date (2026-05-20) only ~30 trading days (~43 calendar days) of *forward* prices exist. **63-/126-/252-day forward IC on LIVE signals is not measurable today — the forward prices do not exist.** This is the single most important fact in the dispute and easy to miss: the horizons the product cares about (months) are exactly the ones we currently cannot measure from realized returns.
- **Effective independent observations** (overlap-corrected, the discipline `alpha_eval.py:105-123` enforces): 5d ≈ 8–9; 21d ≈ **2**; ≥63d = **0** on live data.

### A.2 The two datasets (the key methodological move)

1. **Live post-training signals (2026-05-20 →):** true OOS, unbiased, but only short horizons measurable now and thin. Grows ~1 date/week — the clean dataset, not yet powered.
2. **Pre-training walk-forward OOS predictions (2025-01 → 2026-05, ~16 months):** long horizons (63/126/252d) *are* measurable, but the data carries survivorship + price-adjustment bias (`alpha-research-audit.md:111`) and is the period the reversal was already found in. Reconstruct only if the walk-forward OOS predictions are reproducible from `asxos/domain/models/train.py:88-111` (`walk_forward_split`); label results **indicative, not decision-grade**. This is the only way to say anything about the multi-month horizon before ~2027.

### A.3 Test battery — all read-only, all through `alpha_eval.py::evaluate()`

Per `requirements-analyst`: the decision artifact **must** be the frozen `AlphaReport` from `alpha_eval.py::evaluate()` (`horizons=(5,10,21,63)`, `:263`), not a parallel ad-hoc SQL verdict (SQL is fine for reproduction/appendix only). Every threshold below maps to an existing `AlphaReport` field. Run per dataset, per horizon (capped by available forward prices):

1. **IC-decay curve** — per-`as_of` Spearman rank-IC(prob_up, fwd total return), aggregated with **naive AND effective t** (`ICSummary`, `alpha_eval.py:39-49`; effective-N `:105-123`). Quote the **effective** t always (`:16-18`). Plot IC vs h → adjudicates C1/C2.
2. **Signal rank persistence (autocorrelation)** — already run in §1 of the sibling audit (ρ≈0.95 @1–2d → ρ≈0.77 @19–23d, no sign flip). Separates "model keeps saying the same thing" from "model is right."
3. **Decile long-short spread + monotonicity** (`DecileResult`, `:61,193-198`): `spread_pct>0`, `monotonic_frac≥0.6`, `top_minus_upper_mid_pct≥0`.
4. **Calibration / Brier** (`CalibrationResult`, `:202-224`) — informational unless `prob_up` is used for *sizing* (then gate `miscalibration≤0.10`); today it is a rank, not a probability (`alpha-research-audit.md:93,140`).
5. **Liquidity split** (`LiquiditySplit`, `:227-252`, `min_price=0.20`, `min_dollar_vol=100_000`): is the edge only in untradable names? (2026-06-22: yes.)
6. **Regime stratification** (`AlphaReport.regimes`, `:279-281`): neutral vs bear — **bull unavailable, note the gap, do not extrapolate.**
7. **`expected_return` validation** — monotone in realized returns at any h, or non-functional as previously found?
8. **Cost/turnover overlay (the bridge from horizon to cadence)** — net-of-cost decile spread at cadences {5d,10d,21d,monthly,quarterly} under a realistic ASX cost model; find the cadence, if any, at which the edge survives costs. This is what actually answers C3.
9. **Multiple-testing hygiene** — one model today, but log every threshold/variant; note deflated-Sharpe/PBO/FDR are absent from the codebase (P1 registry).

### A.4 Acceptance criteria (from `requirements-analyst`, adopted)

**Data-sufficiency gate, evaluated FIRST** (per horizon, to be eligible for PASS/FAIL rather than INCONCLUSIVE): `effective_n ≥ 8` (above the engine's own `≥5` floor at `:293-296`, because the 2026-06-22 window was a single mild-down regime — 5 near-identical draws ≠ robustness); `≥2` regimes; `≥30` valid names/date; total-return basis (`adj_close`, not raw `close`). If the gate fails at 21d/63d → **INCONCLUSIVE, full stop.**

Decision horizon = **21d and 63d** (5d is diagnostic only — it proves the signal exists and reconciles with 2026-06-22, but does not clear a buy-and-hold book).

| Verdict | Definition (at BOTH 21d and 63d, tradable subset) | Rule #11 | Action |
|---|---|---|---|
| **PASS** | `mean_ic≥0.03` & `significant` (`|eff_t|≥2`); tradable-IC survives with enough tradable names to build the book; decile spread positive+monotonic; **no sign flip across 5/21/63d**; IC-sign stable across ≥2 regimes | **Lift** #11 | Clears allocator + thesis basis; unblocks Phase 2c + real capital (still subject to Part B) |
| **FAIL-A (horizon mismatch)** | 5d passes but 21d/63d IC insignificant or negative | **Keep** for buy-and-hold | Escalate to `system-architect`/`backend-architect`: faster cadence, or retrain to 21/63d labels + re-audit. Do not re-tune-and-reship the same shape (`session-handoff:63-69`) |
| **FAIL-B (no edge)** | No horizon (incl. 5d) clears `mean_ic≥0.03` on the tradable set | **Keep** | Retire Model A from allocator/thesis; paper/redesign only |
| **INCONCLUSIVE** | Data-sufficiency gate fails at 21d/63d (current state: `eff_n=2` @21d) | **Keep unchanged** | Re-run this exact spec as history accrues (§A.5) |

Any verdict that lifts/narrows #11 requires a **persisted, reproducible `AlphaReport`** (all `warnings` verbatim, `:95,275`) + the §A.6 reconciliation record.

### A.5 Data-sufficiency timeline (current ~1-date/week cadence)

21d minimally powered (`eff_n≈8–10`) ≈ **late Aug 2026**; 63d ≈ **Q4 2026**; 252d not until **mid-2027**. ⇒ A full multi-month verdict from live forward returns is a late-2026-to-2027 proposition. Until then the only levers on the horizon that matters are the bias-labeled pre-training study (A.2 #2) and James's external audit.

### A.6 Reconciliation harness for James's ChatGPT audit (when it arrives)

A one-page table so the two studies compare apples-to-apples; any differing axis makes them **non-comparable, not contradictory** (the two 2026 studies already differ on period: pre-training backtest vs live post-training). Axes to declare for each: **period; train/test boundary; universe (survivorship); IC definition (rank vs pooled); effective-N method; horizons; return basis (close vs adj_close); cost model; NULL handling; verdict.** A bare "signals swing around at 21 days" without these axes cannot on its own move rule #11 — it can only corroborate or contradict a properly-gated in-house run.

### A.7 Delivery mechanism + do-not

- Deliver as a read-only `jobs/audit_model_a.py` (or committed notebook) emitting an `AlphaReport` per horizon per dataset, re-runnable monthly, wired to **no** decision path. Design-only here; building it must not un-quarantine anything.
- **Do not** retrain, un-suspend `asxos-retrain-model-a`, or lift #11 on any short-horizon/preliminary result; **do not** present pre-training long-horizon numbers as decision-grade; **do not** treat the §1 preliminary check (which weakened the 21-day-reversal claim on n≈2) as a clean bill of health.

---

## Part B — Agent DB role scoping: hardened design (P0, before Phase 2c)

The read-only-MCP design in `docs/live-readiness-audit-plan-2026-07-04.md §7` (second `supabase-ro` MCP instance, per-agent frontmatter scoping, CI grep guard, live-fire battery) **holds up under independent security review** (`security-engineer`, §7). Confirmed premises: 6 agents carry write-capable `mcp__Supabase__execute_sql` (each file `:4`); the governance bypass is real (`transitions.py:66-88` emits the exact INSERT-then-UPDATE the BEFORE-UPDATE triggers authenticate by *shape*, not author — `migrations/0033:181`, `0034:99-105`, `0036:37-43,70-76,104-111`); **no `SECURITY DEFINER` functions exist today** (verified), which is *why* a read-only role is sufficient. Additions the review requires:

1. **Runtime canary (the most important addition).** Misprovisioning fails **OPEN**: a `supabase-ro` accidentally created *without* `--read-only` works fine and the CI grep (which only checks the tool-name string) cannot detect it. Add a small recurring job that runs `SELECT current_user` + attempts a harmless INSERT via the `-ro` tool and **alerts (Healthchecks/Resend) if the INSERT succeeds**. Converts an undetectable fail-open into an alerting condition.
2. **Assert the right error code.** Grant-based denial raises `42501` (`insufficient_privilege`) — the strong model you want. `25006` (`read_only_sql_transaction`) means enforcement is only a transaction flag and `SET TRANSACTION READ WRITE` becomes load-bearing. The identity probe must read the role's grants / `rolsuper` / `rolbypassrls`, not accept `transaction_read_only` alone.
3. **`SECURITY DEFINER` CI guard.** The read-only guarantee silently dies the day someone adds a privileged `SECURITY DEFINER` mutating function a read-only caller can invoke. Add a CI grep over `migrations/*.sql`: no new `SECURITY DEFINER` without security review.
4. **Broaden the CI guard to an allowlist + egress ban.** Assert each analysis/discovery agent lists *exactly* `mcp__supabase-ro__execute_sql` and no other DB tool, and **bans `Bash|WebFetch|WebSearch`** on them (today egress-free by convention, not check). Enumerate *all* `.claude/agents/*.md` so a new Phase 2c agent can't slip the net.
5. **Main-loop discipline (the larger residual now).** Role-scoping the sub-agents pushes untrusted RSS text up to the write-capable main loop. Document as load-bearing: the main loop must treat agent output as **data**, parse only the fenced JSON deterministically (via `asx agent-run log`, which writes `agent_runs` at `pending_review` only — never a governance transition), and never issue a raw governed-status write on agent prose. If that weakens, the Candidate-C PreToolUse SQL gate on the *write* server becomes necessary.
6. **Verify the mutating management tools are actually gone** (don't assume `--read-only` removed `apply_migration`/branch/deploy — probe them), and add filesystem/command-exfil probes (`COPY … TO/FROM PROGRAM`, `pg_read_server_files`, `lo_import/lo_export`, `CREATE FUNCTION`) to the battery.

**`asxosctl` (Go ops CLI) DB access** — if it is ever built (Part C says probably not): it must **not** reuse the read-only MCP path and must **not** reuse the write path. As an out-of-band operator binary it can open a direct pooler connection the sandbox can't, so it connects as a dedicated **`asxosctl_ro` Postgres role** (Candidate B — rejected for agents because the sandbox has no wire access, but *correct here*). Grant SELECT only on the ops/re-derivable tables (`job_runs`, `portfolio_daily_snapshots`, `rs_*`), **omit** the irreplaceable PII set (`backup_irreplaceable.sh:49-57`). Never give it `DATABASE_URL` or a write-capable Render/Supabase token; it reports drift, humans fix via git (non-negotiable #2).

**Honest ceiling (write into §7.5):** the repo can *detect* divergence (via the canary) but can never *guarantee* the out-of-repo server config. That asymmetry is the design's ceiling.

---

## Part C — Rust/Go targeted-extension RFC

**Unanimous verdict across `system-architect`, `tech-stack-researcher`, `performance-engineer`, `portfolio-invariant-guard`, `tax-spec-conformance`: NO Rust/Go for v1. Reject a full rewrite. Keep Python as orchestration/ML/governance/CLI/API/explanation.**

### C.1 Why not now (decisive)

Every live blocker is a correctness/data/security problem Rust cannot touch: Model A dispute (statistical, needs history), empty factor panel (data-pipeline), docs drift (docs), agent DB scoping (permissions). `performance-engineer` **measured** every candidate:

| Candidate | Measured cost | Cadence | Verdict |
|---|---|---|---|
| Portfolio vol / covariance | 2.7 ms/symbol; 30 names = 81 ms; 1,700 = 4.69 s | weekly build | NO — weekly; fixable in Python (Part E); Decimal-bound |
| Tax-lot optimizer (`lots.py:73-107`) | 224 µs at the size-6 cap; FIFO above | on-demand, per-disposal | NO — already bounded trivial |
| Backtest/sim loop | LightGBM **C++** fits dominate; Python glue is ~5 iterations | retrain (suspended) | NO — can't out-Rust the C++ core |
| Corp-action / total-return | I/O-bound (HTTP fan-out, `corporate_actions.py:196-197`) | weekly | NO — network-bound, Rust irrelevant |

None clears the pass bar (Python baseline must first *miss* a cadence budget on Render — none does). Sequencing risk compounds it: the sandbox already can't build its native deps (16 collection-errors, CLAUDE.md "Known test environment gaps"); every guardrail (`make check`, review-gate, conformance agents) is Python-shaped and blind to Rust/Go on day one; and the postmortem's core lesson (mock-invisible governance bug found only by live-fire) says re-expressing money/governance logic in a second language reopens that whole bug class.

### C.2 If/when a kernel earns its place — the seams (from `system-architect`)

Only when **all three** hold: (a) the factor panel actually exists (research chain resolved); (b) a real risk layer is scoped as v2 (`m14_candidate_beta_cap`), giving a genuine O(n²) covariance problem over ~2,382 names; (c) profiling shows a user-felt bottleneck. First clean candidate = `asxos-riskkernel` covariance/beta (new code, dimensionless output).

Layout: Rust crates in a `rust/` Cargo workspace **outside** the Python tree; Python facade is a leading-underscore `_kernel.py` submodule **inside the owning package** (not a new `kernels/` package — a kernel is an implementation detail, not an entity); optional `[kernels]` extra mirroring `[ml]` with a **pure-Python fallback** so `make check` stays green without a toolchain; build stays setuptools, Rust ships as a separate maturin wheel installed on Render only.

**The Decimal/f64 line (system-architect + portfolio-invariant-guard + tax-spec-conformance, in agreement):** the boundary is **money vs dimensionless statistic**, plus a **determinism contract**.
- **f64-legal (never ledgered):** covariance/correlation/beta, Monte-Carlo percentiles, rank-IC/decile/calibration, sector-neutral z-scores, and the vol *estimate* — **provided** the facade quantizes to `Decimal` at NUMERIC(18,6) before the value enters any weight/money path, the kernel guarantees deterministic reduction (fixed summation order, no `--ffast-math`), and the facade hard-fails on non-finite (`NaN`/`inf`) output (a new failure mode f64 introduces that Decimal never had).
- **Decimal-only, never Rust:** all `asxos/domain/tax/*` (spec-cited §8, exact-fraction 1/3, calendar §5.1 — a Rust date subtraction silently reintroduces the 365-day day-count bug §5.1 forbids); cost bases; any weight once normalized to a dollar delta (`allocator.py:202-219`); the constraint waterfall; governance transition ordering; model inference (LightGBM is already C++; a Rust reimpl duplicates the 22-feature contract and reintroduces train/serve skew).
- Moving `volatility.py` to a kernel requires an **explicit amendment** to the "Decimal-only arithmetic" convention via `system-architect` + `portfolio-invariant-guard` — not a quiet edit. Until then `volatility.py` stays pure Decimal and out of scope.

**Risk report invariants (portfolio-invariant-guard), whether or not Rust is used:** the documented silent-omit of thin-history symbols is correct for the *allocator* but **must invert to loud coverage reporting in a risk report** (a report that silently drops names understates concentration — the exact blind spot it exists to expose); both firewall gates apply (`_require_personal_use()` + `ASXOS_PORTFOLIO_BRIEF_ENABLED` if it reaches the brief — precedent: the position-monitor HIGH finding, `docs/harden/position-monitor-harden.md:11,64`); one-way import dependency (`portfolio/*` must never import `asxos.domain.risk`) enforced by a test; compute-never-enforce (a risk number may be displayed, never multiplied into a weight — no allocator change in v1). Persist a risk table only when a *history-consuming* second consumer exists (the `portfolio_daily_snapshots` precedent, `migrations/0011:2`); otherwise compute on-demand, no migration; if persisted, it goes in the re-derivable/**not**-backed-up set.

**Tax-lot optimizer (tax-spec-conformance):** buildable research-only, but **f64 may rank candidates, never produce a ledgered/spec-cited number**; the richer objective (costs, opportunity cost, boundary value, wash-sale/Part-IVA *flags*) needs a **spec amendment first** (new numbered section + TC rows, the §5.4/v1.3 precedent) — "it's only research" is not an exemption; §5.1 eligibility must be computed in Python (`is_discountable`) and passed to any kernel as an opaque boolean; the wash-sale flag carries the verbatim TR 2008/1 / Part IVA disclaimer and must **flag, never assess**; and beware the FIFO-fallback-above-6-lots trap (`lots.py:87-88`) hiding a new term as "tested" while it's dead in production.

### C.3 Go ops CLI — reject; prefer a Python subcommand

`tech-stack-researcher`: a Go `asxosctl` duplicates what `make check-drift` + Render/Supabase MCP already do (non-negotiable #2), adds a second toolchain + CI lane + distribution story for a single-user weekly chore, and bypasses the `*.py`-scoped review gate. If programmatic reconciliation is ever genuinely wanted, add an **`asx ops drift` Python subcommand** (reuses `httpx`/`asyncpg`/Typer, tested in the existing lane) — strictly dominates Go here.

### C.4 The one adopt: `uv` as the CI installer

`tech-stack-researcher`'s highest value-per-complexity item: switch `full-check.yml` and `targeted-ml-tests.yml` to `uv pip install -e ".[ml,dev]"` — drop-in, reversible, no runtime/format change, ~7–10× faster cold install of the `shap`/`llvmlite`/`sklearn` stack. Defer `uv.lock`/project mode. **Reject** DuckDB/Polars/Arrow for now (data is <100k rows; forks the Postgres source of truth; breaks NUMERIC(18,6) + backup conventions).

### C.5 Supply-chain preconditions before ANY Rust/Go merges (`security-engineer`)

Ordered, all build-failing CI gates: committed lockfiles + enforced `--locked`/`-mod=readonly`; pinned toolchains (`rust-toolchain.toml`, Go version); `cargo audit` + `cargo deny` + `govulncheck`; native build job with **no secrets, `contents: read`**, Rust `--offline` against vendored deps (build-time `build.rs`/proc-macro code execution is the top Rust vector — S1); per-dependency human review; `CGO_ENABLED=0` and **prefer an out-of-process Go binary over an in-process Rust PyO3 extension** for anything near DB creds/PII (a PyO3 extension links in-process with the FastAPI app holding `DATABASE_URL`/`RESEND_API_KEY`); SBOM + vendoring; no insecure-fetch env overrides (proxy TLS intact).

---

## Part D — Docs cleanup: hardening deltas (technical-writer)

The §3–§6 plan in `docs/live-readiness-audit-plan-2026-07-04.md` is directionally sound but needs these corrections before it ships:

1. **The map omits the two CLAUDE.md read-first docs** — `docs/foundation/BUILD_GUIDE.md` and `docs/foundation/phase-b-failure-postmortem.md` are absent from both §3 and the proposed `docs/README.md` read-first list, *creating a fresh contradiction between entry points* — the exact disease the plan cures. Add both (current, read-first). Also add `docs/db-shared-project-audit-2026-06-28.md` (its §2 `pg_depend` pre-`ALTER`/`DROP` check is mandatory; records the 43-tables-in-a-shared-~165-table-project hazard) and classify the auto-activating `docs/strategy/*` docs (widest blast radius — they attach agents via `auto_activate:` frontmatter). Reword §3's "every major doc" claim (`:80-81`) — it classifies ~20 of ~40; make `docs/README.md` the exhaustive index instead.
2. **Reorder the commits:** land content fixes + banners first, then `docs/README.md` **last** over a settled tree (commit 1 currently forward-references banners added in commits 4–5). **Merge commit 7 into the map commit** and make it *reconcile* CLAUDE.md's read-first list with the map (don't append a second, divergent list). Expand commit 6's header scope to the full inventory.
3. **Add a CI header-lint (new commit 8)** — `scripts/lint_doc_headers.py` + test. Standardize on **one** machine-readable format (YAML frontmatter; the repo already has three conventions). Add `Supersedes:` (reciprocal of `Superseded-by:`) and anchor `Last verified: <date> against <sha|live-DB|render.yaml>`. **Fail CI if `status: current` and `last_verified` > 90 days** — this is what actually stops the twice-observed rot. Ratchet the allowlist so it can only shrink.
4. **Branch-only handling — remove "leave unmerged" as an option.** Any doc a future session must read has to be on `main` (the lost-handoff lesson, `docs/research/session-handoff.md:6-9`). Verify PR #15 is docs-only before merging (don't merge code as a side effect of a docs cleanup — §8); **decouple the cleanup PR from PR #15's disposition** (else this plan itself sits branch-only, re-running the failure); after landing, close the source branches; encode "handoffs live on `main`" into `docs/README.md` + CLAUDE.md.

---

## Part E — Incidental live finding (flagged, NOT fixed — read-only session)

`performance-engineer` measured that `asxos/domain/portfolio/build.py:230` computes volatility for **all ~1,700 signal symbols**, not the ~30 ranked buys, despite the `build.py:228` comment "vol for buys only (plan H.2 QUICK-WIN-6)." Real per-build vol cost ≈ **4.7 s sandbox / ~15–40 s Render**, ~50× the `~0.1–0.4s` documented in `.claude/rules/portfolio-conventions.md` ("Decimal-only arithmetic"). This is either a stale comment or a scoping miss. **Fix = scope vol to the ranked buy set (→ ~80 ms) or vectorize; pure Python, no new language, no determinism risk.** Route through `backend-architect`/`performance-engineer` in an implementation session; also reconcile/refresh the stale timing estimate in the conventions doc. Not touched here.

---

## §7. Agent Consultation Log

Nine subagents consulted, all advisory/read-only, per `CLAUDE.md` delegation policy. Six required + three optional (portfolio-invariant-guard, tax-spec-conformance, requirements-analyst — required because the plan touches risk/portfolio, tax, and unspecced features respectively).

### system-architect — CONSULTED
- **Asked:** Rust/Go extension module boundaries; PyO3 seam layout respecting one-package-per-entity + Decimal-only; Go ops CLI placement; replatform-vs-kernel vs current blockers; what must not move.
- **Key findings:** Rust/Go as leaf extensions only, lazily; full rewrite rejected (blockers are correctness not perf); Decimal/f64 line = money vs dimensionless + determinism contract, quantize at facade; `_kernel.py` submodule + `[kernels]` extra + Python fallback; first kernel = covariance for a risk layer that doesn't exist yet.
- **Accepted:** all (Part C.2). **Rejected/deferred:** nothing. **Uncertainty:** could not read the branch-only language-strategy doc §6 to reconcile — noted as a reconciliation item; I have that context and confirm no conflict.

### backend-architect — CONSULTED (continued from the §7 read-only-MCP design)
- **Asked:** `asxosctl` DB role/credential; migration-vs-no-migration boundary for a risk report.
- **Key findings:** `asxosctl` → dedicated `asxosctl_ro` direct-connection role (Candidate B, correct for an out-of-band binary), SELECT on ops/re-derivable tables only, never a write token; risk report → **no migration** until a history-consuming second consumer exists (the `portfolio_daily_snapshots`/`migrations/0011:2` precedent); if persisted, excluded from `backup_irreplaceable.sh`.
- **Accepted:** all (Part B, C.2). **Rejected/deferred:** persisting the risk report now. **Uncertainty:** where the existing Supabase MCP is provisioned (operator must locate).

### tech-stack-researcher — CONSULTED
- **Asked:** Rust/PyO3/maturin, Go CLI, uv/DuckDB/Polars/Arrow tradeoffs; dependency/build/CI impact.
- **Key findings:** Rust NO for v1 (no valid hot path; vol is Decimal-bound; maturin backend + toolchain + .pyi stubs + sandbox blast radius); Go NO (duplicates MCP; prefer `asx ops drift` Python subcommand); **uv YES** (drop-in CI installer, highest value/complexity); DuckDB/Polars/Arrow NO (tiny data, forks source of truth).
- **Accepted:** all (Part C.3–C.4). **Rejected/deferred:** DuckDB/Polars now; `uv.lock` deferred. **Uncertainty:** branch-only §6 not readable (same note).

### performance-engineer — CONSULTED (ran measurements)
- **Asked:** where Rust/Go would actually help; hot-path ID; benchmark plan; kernel candidates.
- **Key findings:** all four candidates measured weekly-trivial or already-native → none clears the pass bar; **incidental finding: `build.py:230` vols all ~1,700 symbols not the 30 buys** (~4.7s, ~50× the documented estimate) — cheap Python fix; blunt verdict: no kernel now, doubly wrong given sequencing.
- **Accepted:** all (Part C.1, Part E). **Rejected/deferred:** every kernel. **Uncertainty:** numbers are sandbox-local not Render, but verdicts hold under an 8× penalty.

### security-engineer — CONSULTED
- **Asked:** review the §7 agent-DB design; Rust/Go supply-chain/build risk.
- **Key findings:** design sound; misprovisioning fails OPEN and CI can't detect it → add a runtime canary; assert `42501` not `25006`; add a `SECURITY DEFINER` CI guard; broaden the guard to an allowlist + egress ban; main-loop laundering is the larger residual now; Rust `build.rs` code-execution is the top supply-chain vector; prefer out-of-process Go over in-process Rust near creds.
- **Accepted:** all (Part B, Part C.5). **Rejected/deferred:** nothing. **Uncertainty:** whether Supabase read-only is grant-based (`42501`) or transaction-flag (`25006`) — the battery must determine it.

### technical-writer — CONSULTED
- **Asked:** review/harden the §3–§6 docs cleanup plan.
- **Key findings:** map omits the two CLAUDE.md read-first docs (self-contradiction); reorder commits (map last); merge commit 7 + reconcile; add a CI header-lint with a 90-day rot rule (a template alone is decorative); remove "leave unmerged" and decouple from PR #15.
- **Accepted:** all (Part D). **Rejected/deferred:** nothing. **Uncertainty:** none material.

### portfolio-invariant-guard — CONSULTED (optional, required: plan proposes a risk module / Rust risk kernel)
- **Asked:** guard portfolio invariants against a risk report + Rust f64 kernel.
- **Key findings:** Decimal-only line = terminal statistic (f64 OK) vs money-path (Decimal); silent-omit **must invert to loud coverage reporting** in a risk report; both firewall gates apply; non-finite kernel output must hard-fail; one-way import + compute-never-enforce + behaviour-invariance test.
- **Accepted:** all (Part C.2). **Rejected/deferred:** any allocator behaviour change in v1. **Uncertainty:** noted the audit doesn't literally contain a "Rust track" (correct — this plan adds it); answered on merits regardless.

### tax-spec-conformance — CONSULTED (optional, required: plan proposes a tax-lot optimizer)
- **Asked:** can tax math move to Rust f64; does a richer objective need a spec amendment; §5.1 + disclaimer preservation; untested-hides-unimplemented vectors.
- **Key findings:** f64 may **rank**, never **ledger**; richer objective needs a **spec amendment first** (§5.4/v1.3 precedent); §5.1 eligibility stays Python (`is_discountable`), passed to any kernel as opaque bool (day-count in Rust reintroduces the forbidden 365-day bug); wash-sale = flag-not-assess with verbatim disclaimer; FIFO-fallback-above-6-lots hides new terms as "tested."
- **Accepted:** all (Part C.2). **Rejected/deferred:** does not approve any deviation — routes through spec amendment. **Uncertainty:** none material.

### requirements-analyst — CONSULTED (optional, required: Model A audit + Rust/Go lack written specs)
- **Asked:** acceptance criteria for the Model A audit and for Rust/Go go/no-go.
- **Key findings:** audit must run through `alpha_eval.py::evaluate()`, not ad-hoc SQL; data-sufficiency gate (`eff_n≥8`, ≥2 regimes) first; PASS/FAIL-A/FAIL-B/INCONCLUSIVE mapped to `AlphaReport` fields; current state = INCONCLUSIVE (`eff_n=2` @21d); reconciliation template; every Rust/Go candidate NO-GO until a persisted `performance-engineer` measurement clears its budget.
- **Accepted:** all (Part A.3–A.6, Part C global rule). **Rejected/deferred:** nothing. **Uncertainty:** self-noted it did not run the audit/profiling — these are criteria for runs still to happen.

**All six required agents (+ three conditionally-required optional agents) were consulted.** No required agent was skipped, so no stop-before-recommending condition applies.

---

## §8. Recommended session sequence + model/effort

Per James's own guidance (condensed): planning sessions on **Opus @ xhigh**; approved doc/code edits on **Sonnet @ high** or **opusplan @ high**; `ultrathink` only for one-off architecture calls; avoid `max` as default.

1. **Docs cleanup** (Opus @ xhigh → doc-only PR): execute Part D over the §3–§6 plan.
2. **Research-store verification** (after tonight's chain; a check-in is already armed for 18:00 UTC): the §2 checklist in the sibling audit.
3. **Model A audit build** (`jobs/audit_model_a.py`, read-only): implement Part A; expect INCONCLUSIVE at decision horizons until ~late Aug 2026; keep #11.
4. **Agent DB role scoping** (backend-architect + security-engineer): execute Part B incl. the runtime canary — before Phase 2c.
5. **`uv` CI adopt** (Part C.4) — small, high-leverage.
6. **Only after** Model A resolves and the factor panel populates: revisit the first Rust kernel against Part C.2's three preconditions and C.5's supply-chain gates. Not before.

## §9. Do-not-change list

- No code/migrations/DB-writes/Render/Healthchecks changes in any docs-cleanup or planning PR.
- Do not build any Rust/Go kernel now; do not adopt DuckDB/Polars; do not open a Go/sibling-repo track.
- Do not move tax, governance, Decimal money, or model inference to Rust/Go — ever, per the conformance boundaries.
- Do not lift CLAUDE.md #11, retrain, or un-suspend `asxos-retrain-model-a` on any preliminary/short-horizon result.
- Do not persist a risk-report table until a history-consuming consumer exists; do not let a risk report change allocator behaviour in v1.
- Do not fix the `build.py:230` vol-scope finding in a planning session — flag it for an implementation session (Part E).
- Do not treat this plan (or the two branch-only audits) as safe while unmerged — land them on `main`.
