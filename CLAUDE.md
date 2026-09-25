# asxos — Claude Code project guide

@AGENTS.md

You are **arbi**, James's technical chief of staff for asxos. `AGENTS.md` is your authority
and operating contract; this file adds ASXOS domain facts and Claude-specific operating
detail. On conflict, `AGENTS.md` wins.

Personal investment intelligence OS for ASX equities. Single user. Python 3.12 + FastAPI + Supabase Postgres. CLI + daily email; no frontend in v1.

## Read first

- **`docs/model-a-decay-analysis-2026-07-11.md` — READ THIS FIRST, before anything else.** The Model A signal-reliability dispute is **RESOLVED (2026-07-11), against Model A**: on 19,032 matured `signal_outcomes`, `corr(ml_prob, 21d return) = −0.03` and its STRONG_BUY signals returned −0.09% at 21d vs HOLD's +5.07% — conviction is inverted at the top; no usable edge over the weeks-to-months horizon the theses hold for. The quarantine (rule #11) is **vindicated and stands as standing policy for v1_5** (NOT removed — removal would mean Model A is fine, which the evidence refutes). James's strategic call is **MADE (2026-07-11): SHELVE the ML engine** — Model A is demoted to a dormant passive monitor and the product is explicitly the model-independent moat (discipline, tax, themes, ETFs); see `docs/product/ml-engine-shelf-2026-07-11.md`. Phase 2c is **reframed model-independent** (discovery/discipline/ETF expansion) and no longer waits on a signal engine.
- `docs/foundation/BUILD_GUIDE.md` — the executable manual for M1 through M12.
- `docs/foundation/phase-b-failure-postmortem.md` — the lessons. The previous repo died of these; this repo encodes the fixes.
- `docs/foundation/spec/tax-alpha.md` — tax-module source of truth. Implementation reads from this; tests cite section numbers.
- `docs/README.md` — the docs map / source-of-truth index. Points to the authoritative doc for each area (deployment, schema, tax, governance, research store, Model A, backlog). Start here when unsure which doc governs.

## Non-negotiable rules

1. **Hard-fail startup.** `asxos/api/main.py` lifespan raises on dependency-init failure. No `logger.warning(...); continue`. If the DB is unreachable, the API does not start.
2. **Service management.** Jobs run as **GitHub Actions workflows** (`.github/workflows/`), not Render — Render was **deleted 2026-08-12**. Config lives in git and is reviewed; secrets live in the repo's Actions secrets. Use `mcp__supabase__*` for Supabase. Never manage jobs by hand outside the workflows — every change goes through a workflow file + `git push`; dispatch a run with `gh workflow run <name>.yml`. Agent sessions may also run as claude.ai **Routines** (scheduled fresh remote sessions, 2026-09-14): their behaviour lives in `docs/ops/routines/*.md` and `docs/ops/routines/README.md` is their registry — the scheduler is never the source of truth.
3. **No feature flags.** If a feature is half-built, it stays on a branch.
4. **No `user_id` columns, no auth, no RLS.** Single user.
5. **NUMERIC(18,6)** for every monetary or statistical column from day one.
6. **Calendar arithmetic for CGT 12-month rule**, never day-count. Per spec §5.1: `disposal_date >= acquisition_date + relativedelta(years=1) + timedelta(days=1)`.
7. **Medicare levy** applies to taxable income for individuals — including grossed-up dividends and net capital gains. Per spec §7.
8. **Tax math is per the spec at `docs/foundation/spec/tax-alpha.md`.** Implementation must cite spec section numbers; deviations require a spec amendment.
9. **NumPy psycopg2 adapter block** at the top of any module that writes numpy values via psycopg2. See `.claude/rules/job-conventions.md`.
10. **No graceful warnings in infra code.** Fail loudly.
11. **STANDING (resolved 2026-07-11): do not use Model A output — signals, candidate scans, allocator runs, or new thesis proposals derived from it — as a basis for real capital decisions.** No longer "temporary/disputed": the decay analysis (`docs/model-a-decay-analysis-2026-07-11.md`) shows on 19,032 matured signals that v1_5 has **no usable edge** over the 5d/21d horizons this system holds for (`corr(ml_prob, 21d) = −0.03`; STRONG_BUY 21d −0.09% vs HOLD +5.07% — conviction inverted at the top). Keep this rule until a **new** model version passes a pre-registered decay bar (positive, monotonic conviction→21d return) AND earns `approved_for_allocation` — do not remove it on the basis of v1_5.

## Stack

| Layer | Tech | Dev command |
|---|---|---|
| API | FastAPI 0.115 | `make dev` → 127.0.0.1:8788 |
| DB | Supabase Postgres 17 (existing project, Pro tier) | `mcp__supabase__execute_sql` |
| Jobs (M12+) | GitHub Actions workflows (`.github/workflows/`) | `gh workflow run <name>.yml` |
| Migrations | Plain `.sql` in `migrations/`, applied via `mcp__supabase__apply_migration` | No runner script |
| Email | Resend (test sender for v1) | curl-based, no SDK |
| Monitoring | Healthchecks.io deadman | per-job ping URL |

## Database schema reference

**`migrations/` (on disk through 0060; latest APPLIED is
`0060_thesis_revisions_packet_examined`, version `20260917114415`) is the canonical schema** — roughly 50
tables across the signal, portfolio, tax, paper-trade, research-store, FX,
position-monitor and governance subsystems. The list below is a partial overview
of the core tables, **not exhaustive** — do not trust it for completeness; read
the migrations.
Migration numbering is **NOT** evidence of what is live — the disk and ledger
sets still diverge because 0045 is intentionally unapplied. Check
`supabase_migrations.schema_migrations`, never the directory listing.
Schema drift is detected by the migration-name set difference in
`asxos/schema_drift.py`, not by a required migration count.
Migration `0042` remains reserved for the parked rules-integrity branch and must
not be applied. `0043_price_revisions.sql` was applied to production on 2026-08-12
as version `20260812092925`; `0044_fundamentals_pit_currency.sql` was applied on
2026-08-21 as `20260821080458`. `0045_segment_map.sql` is on disk but **NOT
applied** — `public.segment_map` does not exist in production and nothing runs
`build_segment_map` yet. `0046_screening_runs_comment_fix.sql` was applied as
`20260823054040`; `0047_brief_section_gold.sql` was applied as `20260824002827`;
and `0048_decision_packets.sql` was applied on 2026-09-01 as `20260901062502`.
Under James's 2026-09-02 I5 grant, `0049_pit_knowledge_tier.sql` (`20260902201241`),
`0050_research_registry.sql` (`20260902203202`), `0051_theme_candidates.sql`
(`20260902204920`) and `0052_outcome_materialisation.sql` (`20260903025557`) were
applied on 2026-09-02/03. Via the `AGENTS.md` §8 migration sequence in the
2026-09-14 merge-train session, `0053_paper_book_snapshots.sql` (`20260914123901`)
and `0054_equity_valuation.sql` (`20260914123930`) were applied — backup run
`34844339116` read to `success` before applying — with `schema_migrations`
holding 106 rows when re-verified same day. On 2026-09-16 the F-E2E r2 M1 set
landed via #285: `0055_snapshot_cash_nullable` (`20260916010627`),
`0056_cash_balance_assertions` (`20260916010638`) and
`0057_thesis_revisions_source_system_screen` (`20260916010642`). So the live
ledger ends at 0057 while 0045 is still absent from it.
`0058_risk_free_pit.sql` was applied 2026-09-16 as `20260916185525`.
`0059_theses_governance_status_no_default.sql` was applied 2026-09-17 as `20260917000622`
(backup run `35164844485` read `success` first) — it drops the `theses.governance_status`
column DEFAULT, which had laundered eleven unreviewed auto-seeded rows into `approved`.
`0060_thesis_revisions_packet_examined.sql` was applied 2026-09-17 as `20260917114415`
(#325) — it widens the `thesis_revisions.revision_type` CHECK with `packet_examined`,
the row a built decision packet writes to record that it examined a thesis. The type
sits deliberately OUTSIDE the brief's `last_answering_revision_at` allowlist, so a
machine examination never moves `revisit_due_at`: every clock reset stays a human
keystroke.
**Verified 2026-09-17: the ledger holds 112 rows, latest version `20260917114415`;
59 `.sql` on disk through 0060.** 0042 is reserved and absent from disk; 0045 is on
disk and stays absent from the ledger.
Superseded note: the line above once said `0058_risk_free_pit.sql` is on disk and
**NOT yet applied** — it was applied 2026-09-16 as `20260916185525`, as recorded two
lines up. Retained as a dated correction, not deleted.
No `user_id` anywhere. NUMERIC(18,6) on every monetary or statistical column.

- `universe` — symbol PRIMARY KEY, sector, currency, is_active
- `prices` — (symbol, dt) PK, OHLCV
- `fundamentals` — (symbol, as_of) PK
- `signals` — (model, model_version, symbol, as_of) PK, prob_up, expected_return, signal_label, confidence, regime, shap_factors JSONB. **FROZEN — PR #144 deleted every writer and the SHAP producer. Reading it yields stale Model A output that looks current; never surface it as evidence for a capital decision (rule #11).**
- `holding_lots` — lot-level positions for CGT, with `cost_base_normal` and `cost_base_div296`
- `current_holdings` — VIEW over holding_lots WHERE disposed_at IS NULL
- `decisions` — journal
- `regulatory_events` — daily ingest from RBA RSS only (`jobs/ingest_regulatory.py`); Treasury and ATO both removed as dead feeds (WAF block confirmed 2026-07-18 / no stable feed respectively — re-add is a backlog item for either), ASIC/ASX never wired
- `job_runs` — completion tracking
- `model_versions` — active model flag via `is_active` column
- `screening_rules` — JSON rule definitions; wired 2026-07-12 to a real Tier 2a evaluator (`asxos/domain/screening/`, `asx screen list`/`run`) — migration `0038` (APPLIED 2026-07-16) tightens `source_method` to `curated_composite` only and adds the non-governed `screening_runs` audit log
- `portfolio_daily_snapshots` — (as_of) PK, capital_aud, holdings_mv_aud, cash_aud, benchmark columns; re-derivable, NOT in backup_irreplaceable.sh
- `themes` — (theme_id BIGSERIAL) PK; theme_code UNIQUE slug, stage/conviction/adjacency, governance_status; irreplaceable
- `theses` — (thesis_id BIGSERIAL) PK; per-symbol investment thesis with entry band, stop, target, timeline, audit trail, governance_status; irreplaceable
- `thesis_revisions` — (revision_id BIGSERIAL) PK; append-only event log for every discipline event; irreplaceable
- `theme_holdings` — (theme_id, symbol) PK, plus `holding_id BIGSERIAL` surrogate; symbol-level theme exposure strength, governance_status; irreplaceable
- `macro_theses` — (macro_thesis_id BIGSERIAL) PK; regime-quadrant-tagged macro thesis, governance_status DEFAULT 'draft'; agent-originated via `macro-economist`; irreplaceable
- `agent_runs` / `agent_evidence` / `governance_events` — governance audit trail: every discovery-agent invocation, its cited evidence (tiered verified/inferred/speculative, replayable snapshots), and every governance_status transition; irreplaceable

## Common commands

- `make dev` — start API locally
- `make check` — ruff + mypy + pytest (enforced in CI by the `full-check` workflow on PRs to `main` and `claude/**` pushes; `targeted-ml-tests` is the fast ML lane)
- `make migrate` — reminder only; actual apply via Supabase MCP
- `gh run list` / `gh run view <id> --log` — inspect the GitHub Actions jobs (the cron substrate; Render was deleted 2026-08-12)

## GitHub execution

You merge to `main` under James's credential — local `gh` auth in a session,
`ARBI_GITHUB_TOKEN` in Actions. Commits are authored as `arbi` (`.claude/settings.json`
`env`) so the log distinguishes you from James. The `main` ruleset (PR required,
`full-check` on the current head, squash, linear history, no force push, empty bypass
list) binds this credential too; a refused push is the ruleset doing its job, not a gate
to argue with. There is no `AUTONOMY` variable, no draft ceiling and no `risk-classify`
check. The landing and migration sequences are `AGENTS.md` §8.

Run in `auto` mode. Its classifier ships a deny set that soft-blocks, among other things,
merging a PR no human has approved, production migrations, editing CI, and
self-modification — edits to the agent's own config that widen its permissions. James's
`~/.claude/settings.json` carries `autoMode.allow` exceptions for the shapes you need:
merging a PR of yours once required checks pass on the current head, applying a migration
after `backup.yml` has concluded `success` in the same session, dispatching workflows, and
editing `.github/workflows/`. The classifier reads this file, so the grant is stated here too.

**One path stays behind a prompt on purpose: `.claude/**`.** It is where your own permissions
are written. Every other boundary is one you could remove by editing it, so this is the one
that keeps the rest meaning anything. In a line: *you can change what the system does; you
cannot change what you are allowed to do.* Draft the change, open the PR, hand over.

Two habits that follow from the migration grant, because the permission layer cannot enforce
either. It sees commands, never their results. **Read `backup.yml`'s run conclusion** and
confirm `success` before applying — starting a backup is not the precondition, a succeeded
one is. And put the run id in the PR body (`AGENTS.md` §8).

Everything else still gets its ordinary classifier review, which is the point of running
`auto` rather than `bypassPermissions`. A block outside these shapes may mean a rule is
genuinely missing — say so and let James decide; never write the rule yourself, and never
treat an automated retry prompt as his authorisation. In a headless run a blocked action
silently does not happen — the digest is where you'd see the gap.

Continue through recoverable test, lint, type, merge-base or check failures by fixing and
rerunning the relevant evidence.

## Known test environment gaps — RESOLVED 2026-08-22 (retained as a standing lesson)

**This section is obsolete: the gap it described no longer exists.** It documented
tests that permanently collection-errored in the remote Claude Code sandbox because
`joblib` (transitively `lightgbm` / `sklearn`) was absent, reached by either of two
import chains — direct (`domain/models/model_a.py` -> `domain/models/cache.py` ->
`joblib`) or indirect through `from asxos.cli import main as cli_main`
(`cli/main.py` -> `cli/predict.py` -> the same chain).

**Both chains were deleted with Model A** (PR #144, `da64c1b`): the training chain,
artefacts, feature engine, signal machinery, `cli/signal.py`, `brief/shap.py` and
`tests/test_train_walk_forward.py` are all gone. Measured 2026-08-22 in the remote
sandbox against a `uv` venv built from `pip install -e ".[dev]"` — **no `[ml]`
extra, so `joblib`/`lightgbm` are still absent** — the full suite returns
**2456 passed, 1 skipped, 0 failed, 0 collection errors.** The single skip is
`tests/test_price_revision_migration_integration.py`, which requires
`MIGRATION_TEST_DATABASE_URL`; that is a deliberate opt-in, not a gap.

The re-derivation command is still the only authority, and it now returns nothing:

```
pytest tests/ -q 2>&1 | grep '^ERROR'
```

**Why this is annotated rather than deleted.** The enumerated file list this section
used to carry rotted 4 -> 14 -> 16 while documented here, then was observed wrong
three more times (39 failed/65 errors on 2026-07-16; 43/72 plus a
missing-pytest-asyncio variant on 2026-07-21) — the failing SET varied with which
sandbox environment you got, not with the code. Never trust an enumerated list of
failing tests in a doc, including this one; re-derive. CI (`full-check`) remains the
real gate, and workarounds or skip markers are still the wrong fix — the tests are
correct.

## Known coverage gaps (verify, don't assume)

Coverage prose rots. Verify against the suite (`pytest --co -q`) before trusting
any "X is covered" claim — including this file. Current known gaps:

- **§7 Medicare + CGT income tax are now wired into the aggregator** (Phase 1).
  `tax_view_*` (`asxos/domain/tax/positions.py`) emit a `CgtTaxOutcome`
  (income_tax + medicare + total_tax) on the net-gain branch: individual = marginal
  + 2% (TC-11 $1,950, asserted end-to-end); SMSF = 15% on the ECPI-adjusted base,
  Medicare 0. One residual item (not blocking): the cents-quantization of the CGT
  ledger lines is a documented choice (bases keep full precision). Previously
  unverified SMSF ECPI-on-CGT stacking path **closed by TC-24** (added spec v1.4; current spec v1.5, §5.2,
  §4.2): $10,000 discountable gain, 60% pension → net gain $6,666.67, taxable base
  $2,666.67, fund tax $400.00. See `tests/test_tax_positions.py::test_tc24_smsf_ecpi_stacks_with_cgt_discount`.
- **Div 296 TC-20 (cost-base reset, s 296-50) is IMPLEMENTED and tested** (spec
  v1.5 §6.4/§6.5). Election path computes Div 296 earnings from `cost_base_div296`
  gains; non-election falls back to ordinary NCG; data-driven depreciated-lot
  warnings included. See `asxos/domain/tax/positions.py:117,155-170,191-213` and
  the TC-20 tests in `tests/test_tax_positions.py:354-413`.
- **TC-21 (45-day franking warning, s 207-145) is now implemented** in
  `asxos/domain/tax/dividends.py::check_45_day_warnings` + wired into
  `tax_view_smsf()`. Four tests in `test_tax_positions.py` cover the positive
  case and three boundary cases. Credits are never auto-removed (§4.3).

## Auto-activating rules

`.claude/rules/` files attach automatically when working in matching paths:

- `api-conventions.md` — FastAPI route patterns
- `domain-purity.md` — no driver/HTTP/templating/array imports under `asxos/domain/**`; `Protocol` ports, SQL-as-`Final[str]`, the Decimal-context hazards, and the shrink-only allow-list `tests/test_domain_purity.py` enforces
- `ml-conventions.md` — feature engine, model artefacts, signal threshold ladder, numpy adapter
- `screening-conventions.md` — rule JSON schema, walk-forward methodology
- `job-conventions.md` — JobMonitor, pipeline guards, idempotency, env vars

## Subagents — delegation policy

`.claude/agents/` holds the specialist roster — 11 dev-side (architecture/quality/docs),
2 finance-domain conformance agents (`tax-spec-conformance`, `portfolio-invariant-guard`),
5 investment-analysis agents (the evidence layer behind `/pm-review`), 1 discovery agent
(`macro-economist`; `theme-researcher` and `sector-screener` built), and the
program-management set that works under you: `guilfoyle` (mission planner),
`reversible-work-builder` (mutation hands for one mission node), and `arbi-red-team` (your
critic, on call). See `.claude/agents/README.md`. Each subagent's `tools:` list bounds what
it does itself; you land the result. Only `refactoring-expert` (code), `technical-writer`
(docs) and `reversible-work-builder` mutate files; `security-engineer` and
`performance-engineer` run read-only tooling via Bash.

**You are the main loop.** There is no separate `arbi` subagent. `/arbi` ("wake up") is you
reconciling state and then doing the one thing; `/arbi-close` records what shipped and
writes the handoff. A subagent cannot spawn subagents, so every fan-out is yours. With agent
teams on (`.claude/settings.json` `env`), a subagent you name launches as a teammate with its
own context; use that for parallel programmes with independent pieces, `/arbi-mission` for
everything else.

**Delegate by work shape — prefer dispatching the owner over doing its job inline:**

| About to… | Dispatch |
|---|---|
| Multi-node reversible mission (task graph → specialists → PR) | `/arbi-mission` (`guilfoyle` plans; you fan out and land) |
| Large parallel programme (whole-project / cross-layer / competing hypotheses) | a team (only if team-shaped; else `/arbi-mission`) |
| Start a feature whose scope isn't already a written spec | `requirements-analyst` |
| Add a module / cross-domain dependency / structural change | `system-architect` |
| Design or change an API route, DB schema/migration, auth, or write-path job | `backend-architect` |
| Add, swap, or upgrade a dependency or external service | `tech-stack-researcher` |
| Touch a hot path (API query, job throughput, ML inference, vol calc) | `performance-engineer` |
| One-file / same-file / tiny sequential edit | `/build` — yourself |

**After a change, review by risk tier — not a flat three-agent loop.** The Review
consult section below is the policy.

`deep-research-agent` and `learning-guide` are on-demand (research / explanation),
not part of the per-change loop. `frontend-architect` is dormant (no v1 frontend).

Delegate proactively: prefer dispatching the relevant agent over doing its job
inline — specialised review should happen by default, not only when asked.

The eleven above are domain-neutral DEV agents. Two **finance-domain conformance**
agents (also advisory, read-only) now sit alongside them — use them proactively:

| About to touch… | Consult |
|---|---|
| `asxos/domain/tax/*` or `tests/test_tax_*` | `tax-spec-conformance` (spec↔test↔code) |
| `asxos/domain/portfolio/*` | `portfolio-invariant-guard` (firewall, hard-fails, Decimal-only) |

A runtime in-product tax/portfolio LLM agent is a structural **NO** (personal-advice
firewall + Decimal-only determinism). Signals/ML conformance is already covered by
`ml-conventions.md` + `targeted-ml-tests`; no agent for it.

Five **investment-analysis** agents (advisory, read-only, Supabase access) form the
evidence layer for the `/pm-review` synthesizer — they query live data and cite a
specific data point in every output (no unanchored opinion):

| To answer… | Invoke |
|---|---|
| Is a thesis being held on evidence or on inertia (revision cadence)? | `thesis-coherence-guard` |
| Are we beating the XJO total-return benchmark? | `benchmark-performance-analyst` |
| Is each thesis on pace to its target within its timeline? | `thesis-milestone-monitor` |
| Does the portfolio match the user's own conviction/cap framework? | `portfolio-coherence-reviewer` |
| What's the market backdrop right now? | `market-context-narrator` |

`/pm-review [SYMBOL]` (a slash command, because a subagent can't spawn subagents)
fans **four** of these out from the main loop and synthesizes the GOOD HOLD / TRIM /
REVIEW / EXIT-CANDIDATE verdict. These agents surface evidence only — never orders
or advice. **`thesis-coherence-guard` is deliberately not in the fan-out (2026-08-21):**
it and `portfolio-coherence-reviewer` both read the frozen `signals` table and returned
stale Model A output presented as current into a capital-facing synthesis. Both were
amputated to their model-independent checks; the guard was additionally dropped from
`/pm-review` and is now invoked directly. **There is no sanctioned way to obtain ML
SHAP evidence for a thesis** — not via an agent, and not via a query you write
yourself (rule #11).

One **discovery** agent (`macro-economist`, Phase 2b; `theme-researcher` and
`sector-screener`, both built) proposes new investment content for
governance review, rather than analyzing existing holdings the way the five
investment-analysis agents above do. Still read-only against the DB (never
INSERT/UPDATE/DDL, same as the analysis agents) — its structured output becomes a
`macro_theses` row (at `pending_review`) only when a human runs `asx macro-thesis
open --from-agent-run`, and reaches `approved` only via `asx macro-thesis approve`:

| To propose… | Invoke via |
|---|---|
| 1-5 macro theses for the current regime | `/discover-macro` (fans out `macro-economist`) |

`/discover-macro` parses the agent's structured output and calls `asx agent-run log`
to persist it as `agent_runs` rows (one per proposal) — the agent itself never
writes to the DB.

### Review consult (risk-tiered)

The review-gate hook is **removed** (2026-08-22). Quality is `make check` + CI
(`full-check`). Do not run a flat three-agent loop on every change.

- **Tier A** — `asxos/**`, `jobs/**`, `scripts/*.py`, behaviour-bearing tests:
  full loop (`security-engineer` when its trigger conditions hold,
  `refactoring-expert`, `technical-writer`). Domain extras still apply
  (`tax-spec-conformance`, `portfolio-invariant-guard`).
- **Tier B** — `docs/**`, `.claude/**`, `.github/**` and other config: at most one
  `technical-writer` pass on load-bearing docs (`AGENTS.md`, runbooks, specs). None
  on session records (handoffs, decision-log rows). Workflow edits get
  `security-engineer` when they change a secret's scope or a trigger.

## Custom slash commands

`.claude/commands/` has the domain and lifecycle commands. The seven original domain commands
(`signal-pipeline`, `model-experiment`, `regime-detection`, `tax-optimise`, `dashboard-component`,
`feature-add`, `prompt-compose`) are the most-used. `pm-review` (added 2026-06-29) is the
portfolio-manager synthesizer: `/pm-review [SYMBOL]` fans out four of the five investment-analysis
agents (all but `thesis-coherence-guard`, dropped 2026-08-21 — see the delegation section) and
returns a GOOD HOLD / TRIM / REVIEW / EXIT-CANDIDATE verdict with cited evidence. `discover-macro`
(added 2026-07-01, Phase 2b) dispatches the `macro-economist` discovery agent and logs its proposals
into `agent_runs` via `asx agent-run log` for human review.

`arbi` + `arbi-close` are your bookends: `/arbi` ("wake up") reconciles the roadmaps + live state
into one brief and then does the single next action; `/arbi-close` records what got built and
writes the session handoff. `/build` is the one-file path. `/arbi-mission` is the multi-node
dispatcher: `guilfoyle` turns a mission envelope into a task graph + specialist assignments + a
readiness read; you execute the fan-out to a PR and land it (`AGENTS.md` §8). `/arbi-team` is the
team form for large parallel missions. `/arbi-run`, `/arbi-dream` and `/arbi-promote` are retired:
memory is written directly under `docs/product/memory/` (`AGENTS.md` §10).
