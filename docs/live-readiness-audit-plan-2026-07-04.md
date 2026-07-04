# Live-readiness audit — follow-up plan and fresh live checks (2026-07-04, ~06:00 UTC)

**Status:** current (point-in-time — live-state sections dated to the hour)
**Scope:** whole repo — docs cleanup plan + Model A decay check + research-store live state + agent DB role-scoping design
**Session type:** read-only planning. No code, migrations, DB writes, Render, or Healthchecks changes. No doc edits applied — §6 contains the proposed diffs for review.
**Read priority:** read first (alongside `docs/session-handoff-2026-07-04.md`) until its P0 items are executed, then background
**Inputs:** `docs/session-handoff-2026-07-04.md` (main); `docs/asxos-live-readiness-audit-2026-07-04.md` (branch `claude/fundamentals-live-readiness-audit-2026-07-04`); `docs/research/claude-fundamentals-audit-handoff-2026-07-04.md` + `docs/research/repo-navigation-audit-and-plan-prompt-2026-07-04.md` (branch `claude/fundamentals-audit-report-2026-07-04`, PR #15 — **still open/draft/unmerged as of this session**)

---

## 0. Headline results of this session's fresh live checks

1. **Model A decay check (P0, run live this session): the "completely swings around at 21 days" claim is NOT visible in the live signals history — but the sample is far too thin to settle the dispute, and the quarantine (CLAUDE.md rule #11) should stay.** Signal rankings self-persist strongly (Spearman ≈0.77 at 19–23 days, no sign flip); out-of-sample predictive rank-IC at 5 days is weakly positive on average (+0.045, 8 of 11 dates positive); the only two dates observable at 21 days show *positive* 21-day IC, and their day-5→21 window IC is *more* positive than their day-0→5 IC — the opposite shape of the claimed decay-then-reversal. Effective independent observations: ~4–6 at the 5-day horizon, exactly **2** at the 21-day horizon. Full numbers, method, and caveats in §1.
2. **The research-store chain has NOT yet re-run.** This session ran at ~06:00 UTC 2026-07-04; the weekly chain fires **tonight** 16:10–17:30 UTC (the handoff that framed it as already-fired was written for a later session). All `rs_*` counts are byte-identical to the 05:30 UTC audit: statements still crash-truncated at 344 rows / 8 symbols, `rs_factor_scores` = 0, factor-panel join = 0 rows, `eval_alpha_factors` cannot run meaningfully. §2 has the verification checklist for after 17:30 UTC.
3. **The repo-navigation theory is confirmed** — evidence in §3. The fix is a docs-only PR (a docs map + status headers + four stale-doc corrections), planned commit-by-commit in §5 with exact proposed diffs in §6.
4. **Agent DB role scoping design** (before Phase 2c) is in §7.
5. **Pending James, unchanged:** the ChatGPT-based Model A audit (this session could not obtain it — nothing was on file to read); the Healthchecks.io API key (13 crons still without deadman URLs); HUBS lock-window end date and acquisition FX rate; review of `agent_runs` #3/#4.

---

## 1. Model A decay check (live, 2026-07-04 ~06:00 UTC)

**Data:** `signals` for `model_a`/`v1_5`: 25,514 rows, 15 distinct `as_of` dates (2026-05-20, then 2026-06-10 → 2026-07-02 near-daily), ~1,700 symbols/date — matching the handoff's live-verified description (`docs/session-handoff-2026-07-04.md:39-41`). All 15 dates are **after** the model's 2026-05-21 training snapshot, so every test below is out-of-sample with respect to training. `prices` coverage ends 2026-07-02, which caps the 21-day horizon at signal dates ≤ ~2026-06-11 — only 2026-05-20 and 2026-06-10 qualify.

### Test 1 — signal rank self-persistence (the handoff's prescribed test, `session-handoff-2026-07-04.md:55-62`)

Pairwise Spearman rank correlation of each date-pair's common symbols, all 105 date pairs, bucketed by calendar gap:

| Gap | Date pairs | Avg symbols | ρ(prob_up) mean [min–max] | ρ(expected_return) mean | signal_label agreement |
|---|---|---|---|---|---|
| 1–2d | 16 | 1,695 | **0.947** [0.872–0.969] | 0.844 | 75.9% |
| 3–4d | 11 | 1,697 | 0.924 [0.810–0.963] | 0.790 | 70.7% |
| 5–7d | 23 | 1,694 | **0.907** [0.801–0.946] | 0.747 | 67.9% |
| 8–14d | 29 | 1,690 | 0.844 [0.772–0.916] | 0.561 | 55.2% |
| 15–18d | 8 | 1,682 | 0.782 [0.758–0.861] | 0.400 | 45.8% |
| 19–23d | 5 | 1,683 | **0.769** [0.753–0.805] | 0.431 | 46.0% |
| 24d+ | 13 | 1,674 | 0.715 [0.683–0.798] | 0.410 | 42.7% |

**Reading:** the model's own rankings decay *gently and monotonically* — no sign flip, no collapse. At the 19–23-day gap the prob_up ranking is still ρ≈0.77 with its day-0 self (minimum 0.753 across all five such pairs). `expected_return` rankings churn faster (0.43 at 19–23d) and labels flip for ~54% of names by then — real churn, but "completely swing around" (which would be ρ near zero or negative) is not what the data shows. Caveat: self-persistence says the model *keeps saying the same thing*, not that what it says is *right* — that's Test 2.

### Test 2 — out-of-sample predictive rank-IC (the substance of the claim)

Per signal date: Spearman rank correlation between `prob_up` and realized forward return (adjusted close, first trading day ≥ as_of+h, tolerance +4d), computed over ~1,700 symbols/date:

| Horizon | Dates usable | Per-date rank-IC |
|---|---|---|
| 0→5d | 11 | −0.081 (05-20), −0.074 (06-10), +0.053, +0.058, +0.067, −0.004, +0.090, +0.079, +0.108, +0.074, +0.129 (06-15→06-26) — **mean +0.045, median +0.067, 8/11 positive** |
| 0→21d | **2** | +0.126 (05-20), +0.033 (06-10) — **both positive** |
| 5→21d window | **2** | +0.168 (05-20), +0.098 (06-10) — **both positive, and larger than the same dates' 0→5 ICs (−0.081, −0.074)** |

**Reading, stated plainly:**

- **The claimed shape (edge at 0–5d that dies and reverses by 21d) does not appear in this sample.** On the only two dates where 21 days are observable, the 21-day IC is positive, and the *later* window (day 5→21) carried more IC than the first five days — the opposite of decay-then-reversal. If anything, on those two dates the model's ranking paid off late, not early.
- **This is nowhere near conclusive.** Two dates at the 21-day horizon is an effective sample of two market-regime draws — `alpha_eval.py`'s own effective-N discipline would refuse to quote a t-statistic on it. The eleven 5-day ICs overlap heavily (nine of them span an 11-day cluster), so the effective independent count is roughly 4–6, and the two oldest dates were *negative* at 5 days — sign instability is real.
- **Reconciliation with the 2026-06-22 alpha audit:** `docs/research/alpha-research-audit.md`'s 5d-edge/21d-reversal finding was measured on the pre-training backtest history. This check is the first one run on the live post-training `signals` table, and it does not reproduce the reversal. Both can be true (different periods, different regimes) — which is exactly why neither settles the dispute.
- **Verdict: the dispute stays OPEN and CLAUDE.md non-negotiable #11 stays in force.** This check *weakens* the specific "reverses at 21 days" formulation against live data but cannot refute the underlying reliability concern on n≈2. Two things unblock a real verdict: (a) **James's ChatGPT audit** — nothing was available to read this session; it remains the top ask (`session-handoff-2026-07-04.md:53-54`), and its methodology/period should be compared against the numbers above; (b) **more history** — every additional week of `generate_signals` output adds one more independent 21-day observation. At the current cadence, a minimally decent 21-day sample (≥8–10 non-overlapping-ish dates) exists around **late August 2026**. Re-run this exact check then (the SQL shape is reproducible from this doc's description; both tests are pure read-only SELECTs).

---

## 2. Research-store live state (queried 2026-07-04 ~06:00 UTC) — chain fires TONIGHT

Row counts and job history are **unchanged** from the 05:30 UTC audit (`docs/asxos-live-readiness-audit-2026-07-04.md` §3): `rs_security_master` 4,370 · `rs_corporate_actions` 41,456 · `rs_financial_statements` 344 (**8 symbols** — crash artifact) · `rs_fundamentals_pit` 43 · `rs_factor_scores` **0** · `rs_index_membership` 0 · `rs_estimates` 0. `job_runs` for the research jobs still shows only the single 2026-06-27 chain (statements marked `failure` manually 2026-07-02; `compute_factor_scores` has never run).

**Timing correction to the handoff:** the "first weekly chain run including compute_factor_scores fired 2026-07-04 16:10–17:30 UTC" premise is a future event as of this session (~06:00 UTC). Consequences:

- `eval_alpha_factors` **cannot** run meaningfully — the factor-panel join is trivially 0 rows (`rs_factor_scores` is empty; `jobs/eval_alpha_factors.py:77-86` fails loudly by design). No factor conclusions were drawn, none should be until the panel exists.
- **Post-17:30 UTC verification checklist** (any session, read-only):
  1. `job_runs` for `sync_security_master` (16:10), `sync_corporate_actions` (16:30), `sync_financial_statements` (16:50 — the crash retry; watch for a repeat of the SIGKILL/OOM-class death), `derive_fundamentals_pit` (17:10), `compute_factor_scores` (17:30 — first run ever).
  2. `rs_financial_statements`: expect distinct symbols ≈ active universe (~2,382), not 8.
  3. `rs_fundamentals_pit`: expect multi-year depth per name, not 43 rows.
  4. `rs_factor_scores`: expect > 0 at `fs_v1`; then the panel join count.
  5. Only if the panel is populated: run `jobs/eval_alpha_factors.py` read-only and report its warnings **verbatim** (expect underpower warnings — ~18 months of prices gives ~1–2 independent 252d windows; `docs/research/session-handoff.md:32-35`).
  6. Watch the known chain-ordering defect: on 6/27, corporate actions ran 100 minutes into a 20-minute slot and PIT fired mid-upstream (`docs/asxos-live-readiness-audit-2026-07-04.md` §3). A full statements fan-out will likely overrun its slot again tonight — if PIT/factors consume partial upstream data, that is the fixed-offset defect, not a new bug. Design dependency gating; do not hotfix tonight.
- A scheduled check-in was armed from this session to re-run these queries after tonight's chain completes and report the outcome.

---

## 3. Current documentation map (orchestration-prompt deliverable 1)

Theory confirmed: the repo has multiple plausible entry points, current/stale/branch-only docs interleaved with no status metadata, and a root README that actively misdirects (8 crons/10 tables vs 28 crons/~40 tables; phase-4 presented as "the chosen architecture"). Classification of every major doc, with evidence:

| Path | Status | Scope | Read priority | Evidence | Contradictions / risk |
|---|---|---|---|---|---|
| `CLAUDE.md` | current, 2 stale spots | agent guide, whole repo | **read first** | Rule #11 quarantine `:24`; read-first pointer to handoff `:8` | `:125-127` "TC-20 … unimplemented" contradicted by `asxos/domain/tax/positions.py:117,155-160,191-203` + `tests/test_tax_positions.py:354-392`; `:122` cites "spec v1.4" while `docs/foundation/spec/tax-alpha.md:3` is v1.5 ("v1.5 implements TC-20") |
| `docs/session-handoff-2026-07-04.md` | **current — newest authority** | session state, Model A dispute | **read first** | Dispute + action list `:10-81`; pending-James list `:152-168` | Time-sensitive by design; `:5` "backlog … accurate line-by-line" is overstated (see backlog row) |
| `docs/next-session-backlog.md` | partially stale (top half current, bottom half 2026-06-28-era) | backlog | read after handoff | Current: P(-1) `:5-14`, provisioning update `:181-194`, agent-scoping finding `:234-254`, Healthchecks `:202-208`. Stale: TC-20 "unimplemented" `:293-296`; entire TC-20 kickoff `§:343-393`; `:226-228` names six alert jobs but calls them "five" | A session that starts at `:343` would re-implement shipped, tested code |
| `README.md` | partially stale | repo intro | background only | `:11` "Eight Render cron services", `:41` "Eight cron services, ten tables" vs 28 `type: cron` entries in `render.yaml` and ~40 tables (`CLAUDE.md:39`); `:22` phase-4 doc as "the chosen architecture" | Misdirects a fresh agent toward the abandoned VPS design |
| `docs/next-session-kickoff.md` | **stale — dangerous entry point** | old session prompt | archive / banner | `:3` "Paste the block below verbatim"; `:10` old branch; `:22` `REQUIRED_MIGRATIONS = 84` vs 90 (`asxos/api/main.py:15`) | Pasting it re-anchors a session three migration-epochs back |
| `docs/foundation/phase-4-architecture-system-architect.md` | **historical/superseded, unmarked** | architecture | background only | `:11` local Postgres "Loser: Supabase"; `:13` systemd "Loser: … Render cron"; `:15` Hetzner VPS "Loser: Render" — the live stack is the "loser" column three times | No supersede banner in 293 lines; README `:22` endorses it |
| `docs/foundation/spec/tax-alpha.md` | **current** | tax source of truth | read if touching tax | v1.5 header `:3` ("v1.5 implements TC-20"); §13 changelog | None found — matches `asxos/domain/tax/` |
| `docs/research/session-handoff.md` | domain handoff, partially stale | research store | read if research-store work | Provenance note `:6-9` (a prior handoff was lost to a branch — the exact failure mode PR #15 is now repeating); row-count table `:17-25` superseded by live DB; `:82` HEALTHCHECK claim superseded (15/28 now set) | Date-limited (2026-06-25) |
| `docs/research/research-store-schema.md` | honest point-in-time, header now misleading | research store | read if research-store work | `:1-3` "APPLIED — EMPTY … All rs_* tables hold 0 rows" was true 2026-06-22; 4/7 tables now populated | Needs a "superseded by live DB" pointer, not a rewrite |
| `docs/research/operating-model-architecture.md` | prescriptive core current; state snapshots stale | research strategy | background / read if factor work | Multiple-testing warnings still unimplemented in code (deflated Sharpe/PBO/FDR absent repo-wide) | Its "factor_scores absent" snapshot is now false |
| `docs/research/alpha-research-audit.md` | evidence current, next-steps executed | Model A / alpha evidence | read with the dispute | TL;DR 5d/21d finding — the origin of the live dispute; note §1's live check does **not** reproduce the reversal out-of-sample | Pre-training-period measurement; do not treat as live-signal truth |
| `docs/backlog-test-coverage.md` | heavily stale | test backlog | verify before use | Its P0 (`api/main.py` lifespan, `:10-11`) is now covered by `tests/test_api_main.py`; CLI P1 block covered by `tests/test_cli_*.py` | Sending a coverage sprint here would re-write existing tests |
| `docs/audit-2026-06-27.md` | dated audit, stale on TC-20 | audit snapshot | background only | `:42`, `:54` "cost_base_div296 … never read" — now consumed (`positions.py:197-203`) | Historical record; banner, don't rewrite |
| `.claude/agents/tax-spec-conformance.md` + `.claude/agents/README.md` | stale on TC-20 | agent prompts | n/a (agent-facing) | `tax-spec-conformance.md:9,28`, `README.md:71` still cite "TC-20 … unimplemented" as the canonical drift example | An *agent prompt* teaching the wrong current state — worst kind of drift |
| `docs/proposals/governance-first-architecture-2026-06-30.md` | current (hardened, self-labeling) | governance | read if governance work | Explicit [CURRENT]/[PLANNED]/[HISTORICAL] labels — the local-hygiene model the repo should adopt globally | None |
| `docs/research/claude-fundamentals-audit-handoff-2026-07-04.md` | **branch-only** (PR #15, open/draft) | whole-repo audit | read with PR #15 | Verified this session: not on `main`; PR #15 open, draft, mergeable-clean | One session out of date on Model A dispute + Render provisioning (superseded on those two by the 2026-07-04 handoff) |
| `docs/research/repo-navigation-audit-and-plan-prompt-2026-07-04.md` | **branch-only** (PR #15) | docs IA audit | consumed by this plan | Same branch; this document executes its §5 prompt | Becomes stale the moment the cleanup PR lands — fold into PR #15 disposition |
| `docs/asxos-live-readiness-audit-2026-07-04.md` | **branch-only** (`claude/fundamentals-live-readiness-audit-2026-07-04`) | live-state audit | read first until merged | Verified: single-commit branch off `main`@6b99face | Third branch-only audit artifact — same lost-handoff risk (`docs/research/session-handoff.md:6-9`) |

---

## 4. Source-of-truth proposal (deliverable 2)

| Area | Authoritative source | Notes |
|---|---|---|
| Repo overview | `README.md` **after** the §6.3 rewrite | Stable identity + pointers only; no counts that rot |
| Claude session entry | `CLAUDE.md` → `docs/session-handoff-<latest>.md` → `docs/README.md` (new) | One path, in that order; kickoff doc retired |
| Live deployment | `render.yaml` + live Render state via MCP (`make check-drift`) | No Blueprint is connected — render.yaml is reconciliation-target IaC, not auto-applied (`docs/next-session-backlog.md:219-223`) |
| Schema / migrations | `migrations/` + live `supabase_migrations.schema_migrations` (count 90 = `asxos/api/main.py:15`) | `public.schema_migrations` (87 rows) is a legacy leftover — never read it |
| Tax math | `docs/foundation/spec/tax-alpha.md` (v1.5) | Non-negotiable #8; code cites section numbers |
| Governance | `docs/proposals/governance-first-architecture-2026-06-30.md` + `.claude/rules/portfolio-conventions.md` | The proposal doc self-labels current/planned/historical |
| Research store | `migrations/0027` (+0028) for schema; **live DB** for state; `docs/research/session-handoff.md` for build rationale | The schema doc's "applied-empty" header is a historical snapshot |
| Model A / alpha evidence | `signals` + `alpha_eval.py` output + §1 of this doc; `docs/research/alpha-research-audit.md` for the pre-training-period diagnosis | Dispute open; rule #11 governs until resolved |
| Portfolio / risk | `.claude/rules/portfolio-conventions.md` + code under `asxos/domain/portfolio/` | v1 is risk-blind by documented design; no risk layer exists yet |
| Backlog / session state | `docs/next-session-backlog.md` **after** the §6.4 fixes + newest `docs/session-handoff-*.md` | Handoff outranks backlog on priority; backlog outranks handoff on itemized detail |

---

## 5. Cleanup PR plan (deliverable 3) — docs-only, small commits

One PR, branch off `main` after PR #15's disposition is decided. Every commit is doc-only (no `*.py` staged → review gate does not arm). Proposed sequence:

1. **Commit 1 — add `docs/README.md`** (the docs map; full proposed content in §6.1). The single highest-leverage artifact.
2. **Commit 2 — root `README.md` rewrite** (§6.3): drop the stale counts (8 crons/10 tables → point to `render.yaml`/`migrations/`), reframe phase-4 as historical, point to `CLAUDE.md` + docs map + current handoff.
3. **Commit 3 — stale banner on `docs/next-session-kickoff.md`** (§6.5). Banner, not deletion — the conventions section is still correct; the state block is poison.
4. **Commit 4 — TC-20 truth sweep** (§6.2, §6.4, §6.6): `CLAUDE.md:125-127` rewrite + `:122` v1.4→v1.5; `docs/next-session-backlog.md:293-296` mark CLOSED + `§:343-393` completion banner; `.claude/agents/tax-spec-conformance.md:9,28` + `.claude/agents/README.md:71` reword to past-tense example; `docs/audit-2026-06-27.md` dated-snapshot banner.
5. **Commit 5 — supersede banner on `docs/foundation/phase-4-architecture-system-architect.md`** (§6.7).
6. **Commit 6 — status headers** (Status / Scope / Last verified / Read priority / Superseded-by) on: `docs/session-handoff-2026-07-04.md`, `docs/next-session-backlog.md`, `docs/research/session-handoff.md`, `docs/research/research-store-schema.md`, `docs/research/alpha-research-audit.md`, `docs/research/operating-model-architecture.md`, `docs/backlog-test-coverage.md` (plus retire its two now-covered entries).
7. **Commit 7 — `CLAUDE.md` pointer** to `docs/README.md` in "Read first".

**PR #15 disposition (decide before or with this PR):** merge it (it is `mergeable_state: clean`), then the docs map lists both audit docs with an "superseded on Model A dispute + Render provisioning by `docs/session-handoff-2026-07-04.md`" annotation. Same for `claude/fundamentals-live-readiness-audit-2026-07-04` and this plan's branch. Leaving any of the three unmerged repeats the exact lost-handoff failure `docs/research/session-handoff.md:6-9` documents. If James prefers not to merge draft audits, the alternative is copying them to `docs/research/archive/` in commit 1 — but merging is simpler and preserves history.

---

## 6. Proposed exact file edits (deliverable 5 — NOT applied; for review)

### 6.1 New file: `docs/README.md`

```markdown
# asxos docs map

Status labels: current | historical | superseded | stale | branch-only.
If a doc contradicts this map, trust the map's "authoritative source" column and fix the doc.

## Read first, in order
1. `../CLAUDE.md` — agent guide + non-negotiables (note temporary rule #11: Model A quarantine)
2. `session-handoff-2026-07-04.md` — the live Model A reliability dispute (P0, unresolved)
3. `next-session-backlog.md` — itemized backlog (top half current; 2026-06-28 half partially stale — see banners)
4. `live-readiness-audit-plan-2026-07-04.md` — latest live-state numbers + this cleanup plan

## Authoritative sources by area
- Runtime/deployment: `../render.yaml` + live Render via MCP (`make check-drift`). No Blueprint connected — render.yaml is the reconciliation target, not auto-applied.
- Schema: `../migrations/` + live `supabase_migrations.schema_migrations` (must equal `REQUIRED_MIGRATIONS` in `asxos/api/main.py`). `public.schema_migrations` is a dead legacy table.
- Tax: `foundation/spec/tax-alpha.md` (v1.5 — TC-20 is implemented; spec-first per non-negotiable #8)
- Governance: `proposals/governance-first-architecture-2026-06-30.md` + `../.claude/rules/portfolio-conventions.md`
- Research store: `migrations/0027` for schema; the live DB for state (the schema doc's "applied-empty" header is a 2026-06-22 snapshot)
- Model A / alpha evidence: live `signals` + `asxos/domain/research/alpha_eval.py`; dispute status in `session-handoff-2026-07-04.md`
- Portfolio invariants: `../.claude/rules/portfolio-conventions.md`

## Historical / background (do not treat as current)
- `foundation/phase-*.md` — rebuild history. phase-4 describes an abandoned VPS/systemd/local-Postgres design (superseded by Render/Supabase — see its banner).
- `audit-2026-06-27.md`, `strategy/*` — dated snapshots.

## Stale — do not use as a session entry point
- `next-session-kickoff.md` — references a three-epochs-old branch/migration state (see its banner).
```

### 6.2 `CLAUDE.md`

- Line 122: `(spec v1.4, §5.2,` → `(spec v1.4 amendment, current spec v1.5, §5.2,` (or simply cite v1.5).
- Lines 125–127, replace:

```markdown
- **Div 296 TC-20 (cost-base reset, s 296-50) is unimplemented**, not merely
  untested. `div296_reset_date` is a config field nothing consumes yet. Building
  it is a spec-governed change (non-negotiable #8 — requires a spec amendment).
```

  with:

```markdown
- **Div 296 TC-20 (cost-base reset, s 296-50) is IMPLEMENTED and tested** (spec
  v1.5 §6.4/§6.5). Election path computes Div 296 earnings from
  `cost_base_div296` gains; non-election falls back to ordinary NCG; data-driven
  depreciated-lot warnings included. See `asxos/domain/tax/positions.py:117,155-170,191-213`
  and `tests/test_tax_positions.py` TC-20 section (`:354-413`).
```

- "Read first" section: add `docs/README.md` as the docs map pointer (commit 7).

### 6.3 `README.md`

- Line 11: `- Eight Render cron services driving the daily pipeline, monitored by Healthchecks.io.` → `- Render cron services driving the daily/weekly pipelines (see render.yaml for the authoritative list), monitored by Healthchecks.io.`
- Line 22: `- \`phase-4-architecture-system-architect.md\` — the chosen architecture` → `- \`phase-4-architecture-system-architect.md\` — the original architecture evaluation (HISTORICAL: it chose a VPS/systemd/local-Postgres design later superseded by Render/Supabase — see the banner in that file)`
- Line 41: `8. **Smaller stack.** Eight cron services, ten tables, one email provider, one monitoring deadman switch.` → `8. **Smaller stack.** One email provider, one monitoring deadman switch, one hosting platform. (The original "eight crons, ten tables" target has grown with the system — render.yaml and migrations/ are the live counts; the principle that survives is: no component without an owner and a deadman.)`
- Add under Quickstart: a "Current operating guide" block pointing to `CLAUDE.md`, `docs/README.md`, `docs/session-handoff-2026-07-04.md`, `render.yaml`, `migrations/`.

### 6.4 `docs/next-session-backlog.md`

- Lines 293–296, replace the TC-20 P1 item with:

```markdown
- ~~**TC-20 Div 296 cost-base reset (s 296-50)**~~ — **CLOSED** (spec v1.5,
  2026-06-29 session). Implemented in `positions.py` (election path via
  `div296_realised_gains` from `cost_base_div296`), tested in
  `tests/test_tax_positions.py` TC-20 section. The kickoff plan below (§ "TC-20
  kickoff") is retained as a historical record only.
```

- Line 343, insert immediately after the `## TC-20 kickoff (next session)` heading:

```markdown
> **COMPLETED — HISTORICAL RECORD.** This kickoff was executed in the 2026-06-29
> session (spec v1.5). Do not re-run. Kept for the worked example and process shape.
```

- Line 225: `the five alert jobs` → `the six alert jobs` (six are listed at `:226-228`).

### 6.5 `docs/next-session-kickoff.md`

Insert at line 1:

```markdown
# ⚠️ STALE — do not paste into a new Claude session

This kickoff reflects 2026-06-28 state: branch `claude/edmund-yong-subagent-wecr3g`,
migrations 0029/0030, `REQUIRED_MIGRATIONS = 84`. Current: migrations through 0036,
`REQUIRED_MIGRATIONS = 90` (`asxos/api/main.py:15`). Session entry is now
`CLAUDE.md` → `docs/session-handoff-2026-07-04.md` → `docs/README.md`.
The "Conventions to honor" section below remains broadly correct; everything in
"Branch / PR state" and "Already-applied DB state" is superseded.
```

### 6.6 Agent-prompt TC-20 fixes

- `.claude/agents/tax-spec-conformance.md:9`: `(a §7 omission hiding as "untested", TC-20/21 unimplemented)` → `(a §7 omission hiding as "untested"; TC-20/21 — both since implemented — were then-unimplemented items hiding as "untested")`
- `.claude/agents/tax-spec-conformance.md:28`: replace the `(e.g. TC-20 cost-base reset s 296-50; TC-21 …)` example with a generic phrasing or an explicitly past-tense one — an agent prompt must not teach a false current state.
- `.claude/agents/README.md:71`: same past-tense correction.
- `docs/audit-2026-06-27.md`: prepend one line: `> Dated snapshot (2026-06-27). TC-20 findings (:42, :54) since resolved — cost_base_div296 is now consumed (positions.py). Do not action from this file.`

### 6.7 `docs/foundation/phase-4-architecture-system-architect.md`

Insert at line 1:

```markdown
> **HISTORICAL — SUPERSEDED (banner added 2026-07-04).** This document evaluated
> and chose a Hetzner-VPS / systemd-timers / local-Postgres architecture. The
> system as built runs on **Render cron services + Supabase Postgres** — i.e., the
> options this document scored as "losers" (§1). The *principles* (hard-fail
> startup, drift-visible scheduling, one source of truth for what runs) carried
> forward and live in CLAUDE.md; the *stack decisions* here are history. Current
> deployment truth: `render.yaml` + CLAUDE.md.
```

### 6.8 Status-header template (commit 6, applied to the docs listed in §5)

```markdown
**Status:** current | historical | superseded | stale | branch-only
**Scope:** whole repo | research store | governance | tax | portfolio | operations | session handoff
**Last verified:** YYYY-MM-DD
**Read priority:** read first | read if touching <area> | background | archive
**Superseded by:** <path> | N/A
```

---

## 7. Agent DB role scoping — design (P0.4, design-only, backend-architect pass 2026-07-04)

**Scope:** closes `m14_candidate_agent_db_role_scoping` (`.claude/rules/portfolio-conventions.md`; finding writeup at `docs/next-session-backlog.md:234-254`) before Phase 2c adds `theme-researcher` and `instrument-selector`. Design only — nothing here has been executed.

### 7.1 Problem statement (verified against the repo)

- Six agents carry the write-capable grant `mcp__Supabase__execute_sql` in their frontmatter `tools:` line: `.claude/agents/macro-economist.md:4`, `market-context-narrator.md:4`, `thesis-coherence-guard.md:4`, `thesis-milestone-monitor.md:4`, `portfolio-coherence-reviewer.md:4`, `benchmark-performance-analyst.md:4`. Their tool lists are otherwise `Read, Glob, Grep` only — no Bash, no web tools.
- The "SELECT-only" constraint is prose, not enforcement: `.claude/agents/macro-economist.md:126-127`, `market-context-narrator.md:82`.
- `macro-economist` reads externally-sourced untrusted text (`regulatory_events.title`/`summary`, `macro-economist.md:129-133`) — a prompt-injection conduit adjacent to a governed table.
- The governance triggers (`migrations/0034…sql:90-139`, `migrations/0036…sql:31-127`) authenticate the *transaction shape*, not the *author*: an injected agent emitting the exact `governance_events`-INSERT-then-UPDATE pair (`asxos/domain/governance/transitions.py:49-57`) in one `execute_sql` call satisfies every trigger and bypasses human approval.
- `.claude/settings.json:1-15` has only the Bash review-gate hook — zero MCP tool scoping. No `.mcp.json` exists in-repo; the "Supabase" MCP server is provisioned outside the repo.

**Key investigation result:** the official Supabase MCP server has no per-*session* role switching. Role selection is per-*server-instance*: `--read-only` (local stdio) / `read_only=true` (hosted `https://mcp.supabase.com/mcp`) makes `execute_sql` run as a read-only Postgres user enforced **server-side at the database-permission level**, and disables `apply_migration` and all other mutating management tools. Claude Code's per-agent restriction mechanism is exactly the frontmatter `tools:` allowlist — so "agents read-only, main loop write" is expressed as **two server instances with distinct tool names**, selected per agent via frontmatter.

### 7.2 Candidate designs

**Candidate A — second Supabase MCP server instance in read-only mode; agents get only its tool (RECOMMENDED).**

1. Register a second MCP server `supabase-ro`, same project, read-only, `--features=database`. Local-stdio shape (preferred, checked-in `.mcp.json` if the sandbox honors it):

```json
{
  "mcpServers": {
    "supabase-ro": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase@latest",
               "--read-only", "--project-ref=gxjqezqndltaelmyctnl", "--features=database"],
      "env": { "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}" }
    }
  }
}
```

   Hosted alternative: `"type": "http", "url": "https://mcp.supabase.com/mcp?read_only=true&project_ref=gxjqezqndltaelmyctnl&features=database"` (OAuth — verify feasibility in the sandbox first).
2. Flip the six agent frontmatters to `mcp__supabase-ro__execute_sql` (one line each). The write-capable server stays configured for the main loop only (`apply_migration`, the documented manual `approved_for_allocation` ops path).
3. Phase 2c agents are born with only `mcp__supabase-ro__execute_sql`.
4. Rewrite the "SELECT-only" prose blocks as "technically enforced, retained as defense-in-depth"; update `.claude/agents/README.md`, `portfolio-conventions.md`, `next-session-backlog.md:234-254`.
5. Hardening: a small pytest greps `.claude/agents/*.md` frontmatter and fails if any file grants `mcp__Supabase__execute_sql` — future re-grants become a red CI check instead of silent drift.

*Pros:* enforcement below the LLM and below repo-editable config, at Postgres permission level; injected writes fail loudly (`permission denied`) — non-negotiable #10 satisfied; zero schema changes, zero RLS (non-negotiable #4 untouched), no `REQUIRED_MIGRATIONS` bump; no change to the live-verified human write path; strips management tools agents never needed.

*Cons / failure modes:* config lives partly outside the repo (drift risk — mitigated by the CI grep + re-running the live-fire battery after any MCP config change); **misconfiguration fails in the wrong direction** — a `supabase-ro` created *without* `--read-only` works fine and protects nothing, which is why §7.4's identity probe is mandatory (same lesson class as the UPDATE-then-INSERT trigger bug: assumed semantics don't count); the read-only user can read everything (exfiltration-via-SELECT untouched, §7.5); the PAT remains write-capable and must never sit in an on-disk file agents' `Read` tool could reach.

**Candidate B — dedicated Postgres role (`asxos_agent_ro`) + generic Postgres MCP server, or prompt-mandated `SET ROLE` (REJECTED).** B1 violates the stated constraint (Supabase MCP is the only DB path from the sandbox; no Postgres wire access). B2 (`SET ROLE` by instruction) is exactly as prompt-level as today's constraint — an injected agent omits it. B's only virtue (per-table grants) buys almost nothing in a single-user DB where every table is equally sensitive. Do not build; do not apply its role SQL.

**Candidate C — PreToolUse hook SQL gate on `mcp__Supabase__execute_sql` (defense-in-depth complement only, NOT primary).** Regex SQL classification is a losing game (writes hide in CTEs, `SELECT … INTO`, chained statements, `DO` blocks, side-effecting functions); hook payloads don't reliably identify the calling subagent; hooks are repo-editable config. Optional later layer *on the write-capable server* to catch main-loop accidents. Never a substitute.

### 7.3 Recommendation

**Candidate A + the CI frontmatter-grep guard**, Candidate C optional later. It is the only option that puts enforcement below both the prompt layer and repo-editable config; it requires no schema change and errors loudly; it makes read-only the *default posture* for every discovery/analysis agent — the write-capable tool becomes something an agent must be deliberately, visibly granted. Same architectural move as migration 0034's trigger: reify a convention that held only by good behavior into a database-level guarantee.

### 7.4 Rollout sequence (design only)

- **Step 0 (James):** locate where the current "Supabase" MCP server is provisioned in the remote sandbox (not in-repo) — decides local-stdio vs hosted, and where `supabase-ro` gets registered.
- **Step 1 (James):** register `supabase-ro` per §7.2-A. Don't touch agent files yet.
- **Step 2 — live-fire enforcement battery via the new tool** (portfolio-conventions verification lesson applies verbatim — only real server behavior counts):
  1. Identity probe: `SELECT current_user, session_user, current_setting('transaction_read_only', true);` — if `current_user` is postgres/service-role, **STOP**: read-only is not engaged.
  2. Plain read succeeds (the macro-snapshot query from `macro-economist.md:31-37`).
  3. Plain INSERT into `regulatory_events` errors loudly (permission denied / `25006`), zero rows landed.
  4. The exact bypass payload is refused: replay the `apply_governance_transition()` statement shape (INSERT `governance_events` then UPDATE `macro_theses … governance_status='approved'`) in `BEGIN; … ROLLBACK;` — expected failure at the INSERT, one layer *before* the 0036 trigger evaluates.
  5. Escape attempts each refused: `COMMIT; INSERT…`, `SET TRANSACTION READ WRITE`, `SET ROLE postgres`, write-in-CTE (`WITH w AS (INSERT … RETURNING 1) SELECT…`), `DO $$ … UPDATE … $$`, and `SELECT set_active_profile(<id>)` (no `SECURITY DEFINER` functions exist in `migrations/` — verified by grep — so function-body writes must fail under the read-only caller).
  6. System-surface probe: what can the role see of `vault.decrypted_secrets` / `supabase_migrations.schema_migrations`? Record reality, not assumption.
- **Step 3:** regression-check the human path — same governance pair via the write-capable server in `BEGIN; … ROLLBACK;` still succeeds.
- **Step 4:** flip the six frontmatters; update prose/docs; add the CI grep test (arms the review gate — fine).
- **Step 5:** end-to-end smoke: `/discover-macro` unchanged in shape; one deliberate in-agent write attempt surfaces a loud tool error.
- **Step 6:** Phase 2c gate — new discovery agents list `mcp__supabase-ro__execute_sql` only; CI enforces.

### 7.5 What this design does NOT protect against

1. **Exfiltration via SELECT** — the role reads the whole DB; egress is limited to the transcript (agents have no Bash/web), residual risk accepted (fixing it would require data-confinement grants contradicting the single-user/no-RLS posture).
2. **Advisory poisoning** — read-only doesn't fix corrupted judgment; the human-approval gate + speculative-evidence hard-fail + replayable snapshots remain the defense.
3. **Denial of service** — `pg_sleep`/cartesian joins still run; bounded by management-API timeouts; loud, single-user blast radius; accepted.
4. **Main-loop compromise** — the write-capable server still exists for the main loop; Candidate C is the partial answer if this ever moves from theoretical to observed.
5. **Config drift / misprovisioning** — a re-granted write tool or a `supabase-ro` recreated without the flag silently reopens the hole; hence the CI guard + re-running the identity probe after any MCP config change.
6. **PAT exposure** — the PAT is write-capable regardless of the server flag; environment-only, never on disk.

### 7.6 Operator (James) actions required

1. Locate current Supabase MCP provisioning; register `supabase-ro` (`--read-only`, `--project-ref=gxjqezqndltaelmyctnl`, `--features=database`). Nothing in-repo can do this if config is externally managed.
2. Provide the `SUPABASE_ACCESS_TOKEN` to the second server's env (PAT reuse acceptable — the guarantee comes from the server-side read-only role, not the token), or complete the hosted OAuth flow if that path is chosen.
3. Witness the §7.4 Step-2 live-fire battery (especially the identity probe and bypass-payload replay) against production, rolled-back where applicable.
4. No Supabase dashboard changes and no migration are required for the recommended design.

---

## 8. Do-not-change list (deliverable 4)

Reaffirmed from both audits, extended by this session:

- **No code changes, no migrations, no DB writes, no Render changes, no Healthchecks changes** as part of the docs-cleanup PR — it is banners, headers, and pointer text only.
- **Do not rewrite historical docs beyond banners/status headers** (phase-4, audit-2026-06-27, strategy/*, the executed TC-20 kickoff). They are records, not bugs.
- **Do not delete any doc** — banner or archive-move only, after approval.
- **Do not reimplement TC-20** (implemented + tested; §3), rebuild `alpha_eval`, the research-store schema, `factor_scores`, the paper monitor, or JobMonitor.
- **Do not touch Model A** — no retrain, no re-tune, no un-suspending `asxos-retrain-model-a`, and no removal of CLAUDE.md rule #11 — until James's audit is read and the decay question has enough history to answer (≈ late August at current signal cadence, per §1).
- **Do not run factor conclusions** before tonight's chain populates `rs_factor_scores` and `eval_alpha_factors`' warnings are captured verbatim.
- **Do not treat §1's results as clearing Model A** — they weaken one specific formulation of the claim on a tiny sample; they do not establish reliability over multi-month holding horizons (which no amount of 44-day history can).
- **Do not start Phase 2c** before the Model A dispute resolves AND agent DB role scoping (§7) ships or is explicitly risk-accepted.
- **Do not build the beta/risk layer, DecisionEvidence, or purged CV as part of any of the above** — they are P1 items with their own sessions; this plan only sequences them.

---

## 9. Ranked next actions (carried forward, updated by this session)

**P0**
1. **James: ChatGPT audit of Model A** — still the top blocker; §1's numbers are the in-house half of the comparison.
2. **Tonight after 17:30 UTC: verify the research-store chain** (§2 checklist); if statements crash again, diagnose the fan-out before anything else touches the research track.
3. **Ship the docs-cleanup PR** (§5/§6) — small, high-leverage, unblocks every future session's navigation.
4. **Agent DB role scoping** (§7) — before Phase 2c.
5. **Healthchecks:** 13 missing URLs + API key (James); confirm the two watchdogs' first-ever runs (tonight 21:05/22:00 UTC).

**P1** (unchanged, preconditions verified): read-only risk report → DecisionEvidence spec → experiment-only purged/embargoed split → hypothesis registry → opportunity-cost delta producer.

**P2/P3** (unchanged): property tests; shared escaped alert helper (six, not five, call sites); tax-lot objective research; config.py healthcheck vocabulary sync; CI realism framing.
