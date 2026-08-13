# Finance capability matrix — KEEP / ADAPT / PARK / REJECT

**Status:** current · frozen input for mission `P2-02`
**Scope:** every finance-analysis capability present in or proposed for ASXOS — the external
finance-skill methods named in the programme packet, the `.claude` agent/skill/command surfaces,
the decision-engine contracts, the research store, the tax module, the portfolio/allocator
surfaces, the brief collectors, and the theses/themes/governance layer
**Last verified:** 2026-08-13 against `origin/main` @ `5c67fe0`
(`docs(arbi): SB0-01 — current/historical/superseded truth map…` (#102))
**Produced by:** mission `P2-01` — "Compare finance skills against ASXOS consumers"
(`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md` §7).
**Docs-only. No code, schema, DB, scheduler or production change was made; this file is the only
file the mission created.**
**Owner:** arbi maintains; James governs every amendment flagged in §7
**Superseded by:** N/A

---

## 0. Why this document exists, and the one rule it applies

`P2` builds the ASX Results-to-Thesis Review slice. The failure mode it is most exposed to is
**building finance capability that nothing consumes** — an audit-support module with no reviewer,
a variance engine with no thesis to move, a factor panel nobody reads. The packet names that
failure twice: its skill table bars *"SOX-specific ceremony with no product consumer"* and
*"Entire workflows unless a later accounting consumer is proven"*
(`…execution-plan-2026-08-12.md:280-283`), and its kill conditions bar *"a generic memory platform
without a named consumer"* (`:915`). James's standing posture, restated when this mission was
issued, is the same rule in one line: **do not build infrastructure without an identified
production consumer.**

This matrix is that rule applied once, exhaustively, before `P2-02` freezes anything.

### The consumer test

| Class | Test |
|---|---|
| **KEEP** | A named ASXOS consumer reads this capability's output **today**, cited by file. It survives into the results-review slice unchanged. |
| **ADAPT** | A named destination exists, but the capability must change to reach it. **The destination is named in the row.** No destination → not ADAPT. |
| **PARK** | Real value, **no consumer identified**. Retain the artifact; build nothing on it. Parking is not deletion — it is a refusal to invest. |
| **REJECT** | The premise is void (Model A basis, a fourth vocabulary, an orphaned dependency) or it crosses a hard boundary. |

**A capability with no identified consumer is PARK or REJECT, never KEEP.** This is not a new
standard — the repo has already applied it once, in the executing scheduler:

> `compute_factor_scores` is deliberately NOT here: retired with the research quant lane
> (degenerate 0.000 output, **no production reader**) — revive as its own workflow if a real quant
> lane returns.
> — `.github/workflows/weekly-research.yml:16-18`

### Standing constraints this matrix operates under

1. **Rule #11 stands.** Model A is retired from active operation (`P1-02`, commit `6fa2b21`).
   Nothing here proposes Model A output as a decision basis. `model_independence` is a mandatory
   `Literal[True]` assertion (`asxos/domain/decision_engine/types.py:466`), and the manifest regex
   at `:56-62` / `:521-528` rejects `model a` / `v1_5` mechanically.
2. **The canonical contract split (governor ruling (c), 2026-08-12).** `types.py` owns validator
   strictness, hashing, temporal enforcement and internal structure. **Appendix B owns which
   artifacts exist, which fields are mandatory, and the ruled semantic tables.** Adding a field or
   a ruled-table row is a **governor amendment** (`docs/product/target-architecture.md` B.4) —
   every such case in this matrix is flagged in §7, never assumed.
3. **Personal-advice firewall (s766B / Westpac v ASIC).** Nothing in this matrix produces a
   recommendation, a rating, a price target, an order, or a position-size instruction. Evidence and
   analysis only. The results-review artifact returns `complete` / `revise` / `abstain`
   (`…execution-plan-2026-08-12.md:305-306`).
4. **No production write.** `P2` is a read-only analysis path. Persistence of any thesis revision
   requires a separate work order (`:310-311`).

---

## 1. The denominator

**70 capabilities** were inventoried and classified. Every row carries a file citation; no row is
left unclassified.

| Group | Rows | Source of the inventory |
|---|---|---|
| A. External finance-skill methods | 6 | packet §P2 skill-integration table (`…execution-plan-2026-08-12.md:276-283`) |
| B1. Investment-analysis agents | 5 | `.claude/agents/` |
| B2. Discovery agents | 3 | `.claude/agents/` |
| B3. Local skills + finance-relevant commands | 9 | `.claude/skills/`, `.claude/commands/` |
| B4. Decision-engine contracts + surfaces | 12 | `asxos/domain/decision_engine/`, `asxos/prototype/` |
| B5. Research store | 8 | `migrations/0027_research_store.sql`, `asxos/domain/research/` |
| B6. Tax module | 7 | `asxos/domain/tax/` |
| B7. Portfolio / allocator | 9 | `asxos/domain/portfolio/`, `asxos/domain/models/production_gate.py` |
| B8. Brief collectors + sections | 5 | `asxos/domain/brief/collectors/`, `asxos/brief/compose.py` |
| B9. Theses / themes / governance / screening | 6 | `asxos/domain/{theses,themes,macro_theses,governance,screening}/` |
| **Total** | **70** | |

### Three findings reframe many rows below

**(i) Nothing writes the `signals` table any more.** `P1-02` deleted `jobs/generate_signals.py`
(repo-wide: no `INSERT INTO signals` remains). Every surviving `signals` reader is therefore not
merely "Model A shaped" — it is **already reading a table whose last write is frozen in the past**:
`asxos/domain/brief/collectors/active_theses.py:92`; `asxos/brief/compose.py:284,294,372,380`;
`jobs/compute_opportunity_cost.py:47`; `asxos/domain/portfolio/build.py:197,209,211`;
`asxos/cli/signal.py:27`; `asxos/cli/journal.py:43`. Those rows classify on evidence, not on
policy alone. Dispositioning them is **`P1-04`'s** scope (`Rewrite agent/review/brief semantics`,
not yet run — merge order is `P1-01 → P1-02 → P1-03 → P1-04 → P1-05`,
`docs/product/roadmap-state.md:88`); this matrix records the classification `P1-04` should land.

**(ii) No finance capability has an API consumer.** The only route in the application is `/health`
(`asxos/api/routes/health.py:12`, mounted `asxos/api/main.py:51`). Every consumer cited in this
matrix is a CLI command, a scheduled job, or a brief collector. Any `P2` surface must be one of
those three; proposing an API route would be new infrastructure with no precedent consumer.

**(iii) The tax aggregator is wired but never fed.** `asx tax-view` hardcodes `dividends=[]` and
`realised_gains=[]` at `asxos/cli/tax.py:93,99`. The franking, Medicare, Div 296, 45-day and
net-capital-gain layer is therefore *reachable* but computes over empty inputs in **every real
invocation** — the rendered table only ever shows lots plus `days_to_discount`. The functions are
correct and spec-tested; the input path does not exist. This is why B6 is not the uniform KEEP it
looks like, and it is the direct cause of gap **G7**/**G12**.

---

## 2. Part A — the external finance-skill methods

**Finding first: there are no finance skills in this repository.** `.claude/skills/` contains four
process skills only — `agent-team-mission`, `arbi-mission`, `pr-readiness`,
`reversible-work-window`. The six capabilities in the packet's skill table are **external methods
to borrow, not local artifacts to port.** That is consistent with the packet's own rule — *"borrow
methods, not authority… The local implementation must not require a runtime plugin to remain
available. The durable value is the source policy, deterministic adapter, local tests, and
evaluation rubric"* (`…execution-plan-2026-08-12.md:274,285-287`).

So Part A classifies **methods**, and every KEEP/ADAPT names the local artifact that will carry the
method. None of these creates a plugin dependency.

| # | Finance capability | Class | Local destination (the artifact that carries the method) |
|---|---|---|---|
| A1 | **Financial-statement analysis** — statement relationships, statutory/underlying separation, period and unit discipline | **ADAPT** | The results-review adapter's frozen-input contract (`P2-02`), sitting over `rs_financial_statements` (`migrations/0027_research_store.sql:68-89`, which already carries `period_end`, `period_type`, `statement_type`, `currency`, `line_items` JSONB). **Statutory/underlying separation and units have no column today — see §6 gaps G3/G4.** |
| A2 | **Variance analysis** — revenue/margin/cash/guidance bridges, driver decomposition | **ADAPT** | The deterministic Decimal delta engine of the results-review adapter, feeding `ThesisVersion.scenarios` / `catalysts` / `falsifiers` (`asxos/domain/decision_engine/types.py:287-290`). Bridges are computed in Python from frozen inputs; **no LLM produces a number** (packet `:283`). Guidance has no store — gap **G5**. |
| A3 | **Reconciliation** — conflicting-source resolution, tie-out procedures | **ADAPT** | The source-hierarchy policy `P2-02` must freeze (packet `:288-291`), expressed as `DecisionPacket.missing_or_uncertain_inputs` (`types.py:464`) plus `ChallengeFinding` rows (`:310-314`). ASXOS already has one live conflict class to tie out: vendor `filing_date` *"often defaults to period_end"* (`migrations/0027_research_store.sql:73`) vs the announcement's real release timestamp. |
| A4 | **Audit support** — evidence lineage, completeness, control exceptions, reviewer independence | **KEEP (already native)** | Four of the five are already contract-enforced, not aspirational: lineage → `EvidenceItem.source_uri`/`observed_at`/`known_at` (`types.py:214-231`) and `thesis_evidence.snapshot_data`/`snapshot_hash` (`migrations/0033_governance_schema_core.sql:117-125`); completeness → `DecisionCase`'s cited-evidence-must-resolve-inside-the-frozen-packet validator (`types.py:598-614`); control exceptions → `ConstraintResult` + `UNIVERSAL_CONSTRAINTS` (`:341-345`, `:45-53`); reviewer independence → `ChallengeResult.independent_of_author: Literal[True]` (`:327`). |
| A5 | **Data validation / statistics** — numeric exactness, missingness, outlier and reproducibility checks | **KEEP (already native) + ADAPT one part** | Exactness and reproducibility are already structural: float input is rejected repo-wide at the contract boundary (`types.py:66-73,129-134`), and content hashing gives byte-level reproducibility (`:113-116,145-160`). Missingness is `missing_or_uncertain_inputs` gating action states (`:508-509`). **ADAPT:** outlier/plausibility checks on results arithmetic have no home — destination is the `P2-03` adapter's numeric test suite. |
| A6 | **Journal entry / close management** | **REJECT** | The packet already rules it *"Little direct value for investment review"* (`:282`). ASXOS has no accounting close, no ledger write path, and no accounting consumer. `asxos/domain/journal/` is a **decision journal**, not a general ledger — the name collision is the only connection. Rejecting it now prevents a plausible-sounding but consumerless import. |

**Part A counts: KEEP 2 · ADAPT 3 · PARK 0 · REJECT 1.**

---

## 3. Part B — the local ASXOS capability matrix

### B1 — Investment-analysis agents (`.claude/agents/`)

Their only orchestrator is `/pm-review` (`.claude/commands/pm-review.md:25-31`).

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B1.1 | `thesis-coherence-guard` — "does SHAP evidence support the thesis?" | **REJECT** | Its entire premise is Model A. It reads `signals … WHERE model = 'model_a'` and interprets `shap_factors` (`.claude/agents/thesis-coherence-guard.md:20-21,27-28,42-44`). Rule #11 bars the basis, **and** the table has had no writer since `P1-02`. The *question* it asks — "does current evidence still support the written thesis?" — is exactly what the results-review artifact answers; the agent is the wrong instrument for it. Disposition owner: `P1-04`. |
| B1.2 | `thesis-milestone-monitor` — target/timeline trajectory | **KEEP** | Model-independent: reads `theses`, `prices`, `holding_lots` only, and defers its math to `asxos/domain/theses/trajectory.py` (`.claude/agents/thesis-milestone-monitor.md:14-25`). Consumer: `/pm-review` step 1. Also the natural supplier of the "changed since prior" input to `DecisionCase.changed_since_prior` (`types.py:549`). |
| B1.3 | `benchmark-performance-analyst` — XJO total-return relative | **KEEP** | Model-independent: `portfolio_daily_snapshots`, `paper_portfolio_run_metrics`, `holding_lots`, `prices`; math deferred to `asxos/domain/benchmark/returns.py` (`.claude/agents/benchmark-performance-analyst.md:14-29`). Consumer: `/pm-review`. Supplies `DecisionPacket.benchmark_id` context (`types.py:458`). It already refuses to invent a backdrop when data is missing (`:33-38`) — the abstention behaviour `P2` needs. |
| B1.4 | `portfolio-coherence-reviewer` — conviction vs size, caps, framework fit | **ADAPT** | Model-independent **except** one join: `signals … WHERE model='model_a'` for a `signal_label` column (`.claude/agents/portfolio-coherence-reviewer.md:23,37,45-46,115`). **Destination:** drop the signal join; the remaining conviction/cap/sector logic is the direct evidence supplier for `PortfolioAssessment.constraints` / `marginal_risk` / `opportunity_cost` (`types.py:375-377`). Disposition owner: `P1-04`. |
| B1.5 | `market-context-narrator` — regime + one macro driver | **KEEP** | Model-independent: `market_context_current`, `regulatory_events`, `signal_sentiment` (`.claude/agents/market-context-narrator.md:14-23`). Consumer: `/pm-review`. Its stop-on-missing-row rule (`:34-35`) is the required behaviour. |

### B2 — Discovery agents

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B2.1 | `macro-economist` — 1-5 regime-tagged macro theses | **KEEP** | Consumer chain is complete and human-gated: `/discover-macro` → `asx agent-run log` → `agent_runs` → `asx macro-thesis open --from-agent-run` → `asx macro-thesis approve` (`asxos/cli/macro_thesis.py`, `asxos/cli/agent_run.py`, registered `asxos/cli/main.py:56-57`). Read-only against the DB. |
| B2.2 | `theme-researcher` — macro-conditioned themes | **KEEP** | Consumer: `/discover-theme`. Explicitly model-independent by its own contract — *"You read no signals, no ml_prob… from Model A output"* (`.claude/agents/theme-researcher.md:180-182`). |
| B2.3 | `sector-screener` — bottom-up coverage-driven candidates | **KEEP** | Consumer: `/discover-sector`. **Doc-rot note:** `CLAUDE.md` still describes `theme-researcher` and `instrument-selector` as "planned in Phase 2c" and counts 22 subagents; the directory holds 24 agents and both discovery siblings are built, while no `instrument-selector` exists. Not this mission's to fix — recorded for `P1-05`/`SB0`. |

### B3 — Local skills and finance-relevant commands

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B3.1 | `.claude/skills/` — `agent-team-mission`, `arbi-mission`, `pr-readiness`, `reversible-work-window` | **KEEP (out of finance scope)** | Process skills consumed by `/arbi-team` and `/arbi-mission`, procedure documented at `docs/product/runbooks/agent-team-mission.md` and `docs/product/runbooks/reversible-work-window.md`. **None is a finance skill.** Recorded so the denominator is honest: the answer to "which local finance skills do we keep?" is *there are none* (gap **G1**). |
| B3.2 | `/pm-review` | **ADAPT** | Today it fans out five agents including the rejected `thesis-coherence-guard`, and its worked example cites *"Model A BUY 0.68, top driver earnings_yield+0.31"* (`.claude/commands/pm-review.md:47`). **Destination:** it is already named as the render surface of the memo view (`docs/product/recommendation-schema.md:39-40`), and its verdict vocabulary is *exactly* `MemoVerdict` (`types.py:26`). Adapt it into the `memo_verdict_for()` render surface — **subject to the vocabulary collision in §7 A2.** |
| B3.3 | `/discover-macro`, `/discover-theme`, `/discover-sector` | **KEEP** | Consumers of B2.1-B2.3. Each persists only through `asx agent-run log` (`asxos/cli/agent_run.py`) and reaches `approved` only through a human `asx macro-thesis approve` / `asx theme approve` (`asxos/cli/macro_thesis.py`, `asxos/cli/theme.py`, registered `asxos/cli/main.py:55-57`) — never a DB write by the agent. |
| B3.4 | `/tax-optimise` | **KEEP** | Drives the tax module through `asx tax-view` / `asx tax-action` (`asxos/cli/tax.py`, registered `asxos/cli/main.py:42-43`). |
| B3.5 | `/signal-pipeline` | **REJECT** | Orchestrates `jobs/generate_signals.py`, deleted by `P1-02`. Owner: `P1-04`/`P1-05`. |
| B3.6 | `/model-experiment` | **REJECT** | Model A training/experiment loop. Rule #11: a new model would need a pre-registered decay bar and `approved_for_allocation`, which is a governor action, not a command. |
| B3.7 | `/regime-detection` | **REJECT** | Reads `signals.regime`, now unwritten. The model-independent regime read that survives is `market_context_current` (B1.5). |
| B3.8 | `/feature-add` | **REJECT** | Adds features to the Model A feature engine. |
| B3.9 | `asx signal <SYMBOL> --shap-n` — the CLI signal viewer | **REJECT** | **Still registered and reachable** (`asxos/cli/main.py:40`), but it selects `signal_label, prob_up, shap_factors` from the unwritten `signals` table (`asxos/cli/signal.py:26`), renders SHAP drivers (`:44-56`), and its empty-result message instructs the user to *"Run `python jobs/generate_signals.py` first"* (`:40`) — a job `P1-02` deleted. A live command that surfaces Model A output and points at a deleted producer is the clearest remaining active-surface residue. Owner: `P1-04`. **Found by this mission's cross-check, not carried from the manifest** — recorded here rather than fixed, since `.claude`/CLI retirement is `P1-04`'s scope, not `P2`'s. |

### B4 — Decision-engine contracts and surfaces

**Isolation confirmed:** `asxos/domain/decision_engine/` is imported only by `asxos/prototype/app.py`,
launched only by `make decision-demo` (`Makefile:23-24`) on 127.0.0.1:8790. It is not imported by
`asxos/api/main.py`, any `asxos/cli/` module, any `jobs/` script or any brief collector; it has no
migration and no table. Its consumer today is **the architecture itself** — and `P2` is the mission
that gives it a real one.

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B4.1 | `EvidencePacket` / `EvidenceItem` (`types.py:214-260`) | **KEEP** | **Destination: the results-review evidence adapter (`P2-03`).** Its `known_at <= knowledge_cutoff` gate (`:249-251`) and `data_mode` split (`:225`) are precisely the point-in-time discipline a results review needs. |
| B4.2 | `ThesisVersion` (`:273-307`) | **KEEP** | Destination: the review artifact's thesis-pillar output. Its `scenarios` triple summing to exactly 100 (`:298-302`) and `catalysts`/`falsifiers` are the packet's required work items 4 (`…plan:298-299`). |
| B4.3 | `ChallengeResult` / `ChallengeFinding` (`:310-338`) | **KEEP** | Destination: the independent finance challenger (`P2-04`). `independent_of_author: Literal[True]` (`:327`) and blocking-cannot-pass (`:331-333`) are the abstention machinery the acceptance gates demand. |
| B4.4 | `PortfolioAssessment` / `ConstraintResult` / `SizeRange` (`:341-399`) | **KEEP** | Destination: the thin portfolio adapter. Zero-size-and-zero-loss-budget on non-action states (`:390-394`) is the firewall in code. |
| B4.5 | `TaxAssessmentReference` (`:402-420`) | **KEEP** | Destination: a typed handle onto the existing tax module (B6). **Nothing produces one today — gap G7.** |
| B4.6 | `DecisionPacket` (`:443-543`) | **KEEP** | The aggregate. `model_independence: Literal[True]` (`:466`) makes non-independence unrepresentable. |
| B4.7 | `DecisionCase` (`:546-674`) | **KEEP** | The cross-artifact gate chain (`:616-671`). |
| B4.8 | `TradingSessionCalendar` (`:163-195`) | **ADAPT** | **Mandatory and real-calendar-shaped, but the only instance in the repo is synthetic** (`demo.py`). Destination: a real ASX session-calendar adapter. **This is a hard prerequisite for any real packet** — `resolve_expiry` raises when the calendar lacks enough sessions after the cutoff (`:190-194`). See gap **G6**. |
| B4.9 | `DecisionBrief` (`:683-704`) | **ADAPT** | Hard-locked to `mode: Literal["synthetic_prototype"]` (`:686`) with a validator rejecting non-synthetic evidence (`:700-701`). **James pre-approved widening this** (`target-architecture.md` B.5) **on the condition it lands inside the results-review mission, with a consumer and tests, and preserves the all-synthetic-or-all-real non-mixing invariant.** Destination: `P2-05`'s rendered review. See §7 A1. |
| B4.10 | `demo.py` — `_ready_case()` / `_blocked_case()` (`:75`, `:347`, `:583`) | **KEEP** | Destination: the positive/negative controls the `P2-04` eval suite extends. Do not delete when real cases arrive — the synthetic negative control is what proves the gates still bite. |
| B4.11 | `renderer.py` + `asxos/prototype/app.py` | **ADAPT** | Destination: `P2`'s requirement that *"JSON and Markdown render from the same validated artifact"* (`…plan:303`) with identical hashes (`:308`, `P2-05`). Today it renders HTML from a synthetic brief only. |
| B4.12 | `tests/test_decision_engine_prototype.py` (621 lines, 30 tests) | **KEEP** | The **sole** test of `_MODEL_A_RE`, `UNIVERSAL_CONSTRAINTS` and `verify_content_hash`; explicitly non-retirable (`docs/product/model-a-reference-manifest.md:290,781`). Destination: extended, never replaced, by `P2-04`. |

### B5 — Research store

Executing chain (`.github/workflows/weekly-research.yml`, Saturday 16:00 UTC, ordered blocking
steps): `sync_universe` → `sync_security_master` → `sync_corporate_actions` →
`sync_financial_statements` → `derive_fundamentals_pit` → `sync_fundamentals`.

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B5.1 | `rs_security_master` (4,415 rows; `migrations/0027…:34`) | **KEEP** | Live consumer: `jobs/sync_financial_statements.py::_load_symbols` iterates it every Saturday (`weekly-research.yml:63`). Its only *analytic* reader, `factor_scores.py:278` (`gics_sector`), is retired. **Destination: it is the `security_id` source named by Appendix B.3 amendment 1** — the fix for `ThesisVersion` identity being ticker text. |
| B5.2 | `rs_corporate_actions` (`:52`) | **KEEP** | Real consumer: `asxos/ingestion/fundamentals_pit.py:183` reads it for dividends/franking. |
| B5.3 | `rs_financial_statements` (`:68`) | **ADAPT** | Written weekly by `jobs/sync_financial_statements.py`; read by `fundamentals_pit.py`. **Destination: the numeric substrate of the results review** — it already carries `period_end`, `period_type`, `statement_type`, `filing_date`, `report_date`, `currency` and full `line_items` JSONB. Adapt = give it a document identity and unit discipline it does not have (gaps **G2/G3/G4**). |
| B5.4 | `rs_fundamentals_pit` — **53,624 rows / 3,357 symbols** (`:92`, PK `(symbol, knowledge_date)`) | **ADAPT** | **Its only reader, `compute_factor_scores`, is retired from the executing scheduler** (`weekly-research.yml:16-18`). So this table is *written weekly and read by nothing.* It is the clearest ADAPT in the matrix: its `knowledge_date` column **is** an `EvidenceItem.known_at` (`types.py:223`), and the PIT-correct prior-period comparison a results review needs is exactly what it stores. **Destination: the `P2-03` evidence adapter. This mission gives the research store its first production consumer.** |
| B5.5 | `rs_factor_scores` — 3,308 symbols, `fs_v1` (`:117`) | **PARK** | Producer retired by the repo's own consumer test (`weekly-research.yml:16-18`); its only reader, `asxos/domain/research/alpha_loader.py:117`, is called only by the manual, "writes nothing; blesses nothing" `jobs/eval_alpha_factors.py:5-16`. No CLI, API, job, cron or collector reads it. **PARK, not REJECT** — the schema and history cost nothing and a real quant lane may return. Building the results-review slice on it would be building on a dead end. |
| B5.6 | `rs_index_membership`, `rs_estimates` (`:136`, `:146`) | **PARK** | **Zero writers, zero readers** — schema only. `rs_estimates` is the natural home for consensus, but the packet permits consensus *"only when provenance and rights are explicit"* (`…plan:289-290`); there is no licensed feed. Do not populate it inside `P2`. |
| B5.7 | `alpha_eval.py` / `alpha_loader.load_factor_panel` / `factor_scores.py` | **PARK** | Pure, tested statistics (`tests/test_alpha_eval.py`, `tests/test_factor_scores.py`) with no product consumer. Retain; build nothing on them in `P2`. |
| B5.8 | `alpha_loader.load_panel` (`alpha_loader.py:69`) — the `signal_outcomes` panel | **REJECT** | Model A outcome panel; **fully orphaned** — no importer anywhere, and its source table lost its writer when `P1-02` deleted `jobs/track_signal_outcomes.py`. Owner: `P1-05`. |

### B6 — Tax module

The tax *math* is the strongest asset in the repo: spec-anchored (CLAUDE.md rule #8), Decimal-only,
and covered by cited test cases. The tax *input path* is the weakest. Finding (iii) above splits
this group three ways.

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B6.1 | `cgt.py` — `days_to_eligibility` (`:38`), `cgt_discount_rate` (`:45`), `cgt_break_even_price` (`:112`) | **KEEP** | The most widely consumed tax surface in the repo, and the only one that reaches the **emailed** brief: `asxos/brief/compose.py:444`, `asxos/domain/brief/collectors/tax_operational.py:37`, `asxos/domain/brief/opportunity_cost.py:55`, `asxos/domain/portfolio/build.py:107`, `asxos/domain/position_monitor/display.py:245`, `jobs/compute_opportunity_cost.py:117`, `asxos/cli/tax.py:107,176`. |
| B6.2 | `positions.py` — `tax_view_individual` (`:44`) / `tax_view_smsf` (`:107`) | **ADAPT** | Consumer: `asx tax-view` only (`asxos/cli/tax.py:47,93,99`). **Adapt = give it real inputs.** Its sole caller passes `dividends=[]` and `realised_gains=[]`, so the aggregator's rich outcome layer never executes against data. **Destination: the `TaxAssessmentReference` producer (G7)** — this is the function that should emit `{applicability, readiness}`, and it cannot honestly emit `readiness="pass"` until it is fed. |
| B6.3 | The outcome layer — `net_capital_gain` (`cgt.py:53`), `medicare.py:21`, `div_296.py:22`, `franking.py:15,32`, `dividends.py:27,47,79` (45-day s 207-145) | **ADAPT** | Reachable **only** through B6.2, therefore only ever exercised with empty input. Correct and test-covered (`tests/test_tax_positions.py` TC-11/TC-20/TC-21/TC-24) but not exercised in production. **Destination: the same real-input path as B6.2.** `dividends.grossed_up_amount` (`:74`) has no consumer at all — its own docstring says *"Useful for tests."* |
| B6.4 | `lots.py` — `select_fifo` (`:35`), `select_lifo` (`:54`), `select_min_cgt` (`:73`) | **PARK** | **Zero consumers in production code.** Grep across `asxos/`, `jobs/`, `scripts/` returns only `tests/test_tax_lots.py:11`. Nothing in `asx tax-view`, `asx propose-trades`, `build.py` or any collector selects lots. Real capability, no consumer → PARK. **`P2` produces analysis, not disposals, so it must not wire this.** |
| B6.5 | `fx_gain.py` — `fx_capital_gain` (`:32`), `is_de_minimis` (`:75`) (Div 775 forex) | **PARK** | **Zero consumers**; only `tests/test_fx_gain.py`. Deliberately unwired — its own docstring instructs *"Do NOT add `fx_capital_gain()` to the equity CGT gain from `positions.py`"* (`:19`) — but nothing else wired it either. Relevant only if `P2` reviews a foreign-currency reporter; out of scope for an ASX results review. |
| B6.6 | `import_csv.py:41 parse_csv` | **KEEP** | `asx import-holdings` (`asxos/cli/holdings.py:23,25`). |
| B6.7 | **Decimal-only determinism + the no-runtime-tax-LLM rule** | **KEEP** | A structural NO on any in-product tax LLM agent (CLAUDE.md, delegation policy). **This is the standing answer to any proposal that an LLM compute a tax number inside the results review** — the packet independently bars *"LLM-generated capital numbers"* (`…plan:281`). |

### B7 — Portfolio / allocator

The brief (`docs/proposals/asxos-research-to-decision-live-slice-brief-2026-08-10.md:229-231`) is
already explicit: *"Existing allocator is Model-A-shaped and cannot enter the capital path
unchanged… reuse its Decimal, constraint, portfolio, and tax mechanics, but replace the candidate
merit/ranking input."* This matrix splits it along exactly that line.

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B7.1 | `production_gate.py` — `resolve_production_model()` | **KEEP** | **Rule #11's mechanical enforcement point.** Zero approved rows → `ModelGateDormant` → the allocator refuses to run (`model-a-reference-manifest.md:22-30`). It contains no Model A token, which is precisely why the manifest classifies it `ENFORCEMENT_KEEP`. **Do not remove it as "Model A plumbing."** |
| B7.2 | `volatility.py` — Decimal inverse-vol | **KEEP** | Model-independent by construction (`Decimal.ln()` only, `.claude/rules/portfolio-conventions.md` §Decimal-only). **Destination: reusable sizing input to `PortfolioAssessment.size_range`.** |
| B7.3 | `constraints.py` — the constraint waterfall | **ADAPT** | Decimal, model-independent, hard-fails on non-convergence. **Destination: the thin read-only constraint adapter the live-slice brief asks for (`:207,:213`), emitting `ConstraintResult` rows (`types.py:341-345`) including the five `UNIVERSAL_CONSTRAINTS` (`:45-53`).** Adapt = expose results as typed constraint rows rather than mutating weights. |
| B7.4 | `tax_overlay.py` + `rebalance.py` §5.1 boundary-defer | **ADAPT** | Model-independent CGT-eligibility logic on disposals. **Destination: the `TaxAssessmentReference` producer (G7)** — this is the closest existing thing to a decision-time tax readiness check. |
| B7.5 | `allocator.py` + `build.py` — the weekly allocator | **PARK** | **Mechanically dormant already, on three independent counts.** (a) `build.py:184-188` calls the gate `required=True`; with nothing holding `approved_for_allocation` it raises `ModelGateDormant` (`production_gate.py:73`) — which `asxos/jobs/utils/job_monitor.py:131` maps to `job_runs.status='blocked'`, i.e. deliberate dormancy, not a crash. (b) Even past the gate, `build.py:216` raises on missing signals and `:225` rejects signals >2 days old — and the producer is deleted. (c) No scheduler invokes `jobs/build_portfolio.py`; disposition is `DECIDE` (`docs/product/scheduler-inventory-2026-08-13.md:154`), which warns re-scheduling *"would alert every Saturday forever."* **PARK: do not revive it inside `P2`** — `P2` produces analysis, not allocation. |
| B7.6 | `paper_trade.py` | **PARK** | Live only as `asx portfolio paper-review` / `signoff` (`asxos/cli/portfolio.py:322,393`) over historical runs. Packet places paper intent at `P5`, after James's capital/risk calibration (`…plan:112`, `P5-01`). |
| B7.7 | `profile.py` + the `_require_personal_use()` / `ASXOS_PORTFOLIO_BRIEF_ENABLED` firewall | **KEEP** | The regulatory firewall, CLI-wide (`.claude/rules/portfolio-conventions.md` §Regulatory firewall). Any results-review CLI surface must call it. **Note the double gate is real and off:** `asxos/brief/compose.py:671,673` require both env vars, and `.github/workflows/daily-brief.yml:60-62` sets only `ASXOS_PERSONAL_USE`. |
| B7.8 | `asxos/domain/position_monitor/` + `asxos/domain/brief/cross_layer.py` | **KEEP** | Model-independent discipline (stops, break-even, regime-vs-thesis cross-layer). `position_monitor` is consumed by `asx position` (`asxos/cli/position.py:19-21`, registered `asxos/cli/main.py:53`). `cross_layer.py` is a pure, I/O-free function with **two** live consumers: `position_monitor/service.py:24,159` and the V2 collector `asxos/domain/brief/collectors/underlying_drivers.py:18,95`. |
| B7.9 | `portfolio/monitor.py` + `monitor_loader.py` — ~1,000 lines of NAV series, attribution, drawdown, turnover | **PARK** | **No CLI, no job, no collector.** Sole consumer is `scripts/monitor_paper_portfolio.py:37-38`, a hand-run script in no workflow and no Makefile target. Genuinely valuable measurement code that Appendix C will eventually need — but it has no consumer today, so `P2` builds nothing on it. |

### B8 — Brief collectors and sections

The V2 collector architecture **executes** every weekday but its render is dark
(`ASXOS_V2_BRIEF_ENABLED` unset; fork at `asxos/domain/brief/composer.py:94`), deferred by James to
canonical Stage 6 with a KEEP-DARK expiry of 2026-09-30
(`docs/product/roadmap-state.md`, defect 7). `P2` must not enable it to clear a gate.

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B8.1 | Model-independent V2 collectors — `wealth_state`, `tax_operational`, `market_context`, `watchlist`, `underlying_drivers`, `new_ideas`, `theme_dashboard`, `section_health` | **KEEP** | Executing weekday via `jobs/compose_brief.py`; persisted to `brief_runs`. Destination at Stage 6: the packet-first renderer (`P6-01`) consuming admitted packets instead of recomputing logic. |
| B8.2 | `active_theses.py` collector | **ADAPT** | Model-A-coupled and **untouched by `P1-02`**: `resolve_production_model(required=False)` at `:82`, `signals` read at `:92`, `shap_factors` → `format_top_factors` at `:137`. Best-effort by design (R9), so it degrades rather than fails. **Destination: replace the SHAP card with the results-review artifact's thesis-pillar output.** Owner: `P1-04`. |
| B8.3 | `asxos/domain/brief/shap.py` + V1 `_signal_changes` / regime sections (`asxos/brief/compose.py:284,294,364,372,380`) | **REJECT** | Pure Model A display over a table with no writer. Owner: `P1-04`. |
| B8.4 | `opportunity_cost` collector + `jobs/compute_opportunity_cost.py` | **ADAPT** | Doubly dead: the job reads the unwritten `signals` table at `:47`, **and** it is scheduled by no workflow — so `opportunity_cost_scenarios` is never refreshed, while the V2 collector (`collectors/opportunity_cost.py:53`) reads it every weeknight. Already classified **ADAPT, not RETIRE** by `P1-03` — *"re-derive from realised prices, or retire the job"* (`scheduler-inventory-2026-08-13.md:158`). Not `P2` scope; recorded so `P2` does not adopt it as-is. |
| B8.5 | News / sentiment brief section | **PARK** | Ship-condition (a) **VOIDED 2026-08-05** with no fresh verdict, while still marked SHIPPED (`docs/product/roadmap-state.md`, "Carried forward, not acted on"). The packet ranks news as *"contextual and never load-bearing"* (`…plan:290`). **Do not make news load-bearing in the results review.** |

### B9 — Theses / themes / governance / screening

| # | Capability | Class | Consumer today / local destination |
|---|---|---|---|
| B9.1 | Governance spine — `governance_events` + the four BEFORE-UPDATE audit triggers (`migrations/0033_governance_schema_core.sql`, `migrations/0036…`), `apply_governance_transition()` (`asxos/domain/governance/transitions.py`), `agent_runs`, `agent_evidence` | **KEEP** | Live and human-gated via `asx thesis/theme/macro-thesis approve` (`asxos/cli/main.py:54-57`); the INSERT-then-UPDATE order is trigger-enforced. `agent_evidence` already carries the verified/inferred/speculative tiering that `EvidenceTier` (`types.py:27`) matches — this is why the contract chose that vocabulary. |
| B9.2 | `theses` + `thesis_revisions` + `trajectory.py` | **KEEP** | Consumed by `asx thesis`, B1.2, and the `active_theses`/`watchlist` collectors. **Destination: the object a results review revises** — but note the packet's stop condition: `P2` produces the artifact and **a separate work order authorises any thesis-revision persistence** (`…plan:310-311`). |
| B9.3 | `thesis_evidence` table (`migrations/0033…:103-129`) | **ADAPT** | **Built, shaped almost exactly right, and holding 0 rows** (`target-architecture.md:1252`). It already has `tier`, `snapshot_data`, `snapshot_hash` (sha256, CHECK-constrained), `source_as_of`, `retrieved_at`, `superseded_at`, and an `external_url` source type explicitly *"reserved for a future web-sourcing agent; unused today (no current agent has WebFetch/WebSearch)"* (`:114-116`). **Destination: the persistence shape for results-review evidence — in a later work order, not in `P2`, which writes nothing.** |
| B9.4 | `themes` / `theme_holdings` / `macro_theses` + `screening` evaluator | **KEEP** | Screening is model-independent by CHECK constraint (`source_method = 'curated_composite'`, `migrations/0038…:54`) and consumed by `asx screen list` / `asx screen run` (`asxos/cli/screen.py:35-36,62-69`). Themes and macro-theses each have a **working** agent→governance→approval loop (`themes/service.py:588`, `macro_theses/service.py:115`). Candidate-admission substrate for Stage 3, not for `P2`. |
| B9.5 | `ThesisProposal` (`theses/schemas.py:344`) + `create_thesis_from_agent_run` (`theses/service.py:745`) | **REJECT** | **Built end-to-end and guaranteed to raise.** `service.py:793` raises unconditionally, its own docstring (`:757`) admits *"currently UNREACHABLE… it will always raise ValueError below,"* the schema class is imported by nothing, and `governance/agent_run_service.py:60` deliberately omits `'thesis'` from the proposal-schema map. `asx thesis open --from-agent-run` (`cli/thesis.py:247`) always fails. **Consequence for `P2`: there is no agent→thesis route.** See gap **G11**. |
| B9.6 | `macro_thesis_outcomes` — the macro learning ledger | **PARK** | Written by `jobs/score_macro_theses.py:299` (scheduled, `daily-brief.yml:109`); **read by nothing** — zero `SELECT … FROM macro_thesis_outcomes` in the repo. A write-only ledger is the packet's own kill-condition shape ("no named consumer"). Retain the rows; build nothing on them in `P2`. |

---

## 4. Counts

| Group | KEEP | ADAPT | PARK | REJECT | Rows |
|---|---|---|---|---|---|
| A. External finance-skill methods | 2 | 3 | 0 | 1 | 6 |
| B1. Investment-analysis agents | 3 | 1 | 0 | 1 | 5 |
| B2. Discovery agents | 3 | 0 | 0 | 0 | 3 |
| B3. Skills + commands | 3 | 1 | 0 | 5 | 9 |
| B4. Decision-engine contracts + surfaces | 9 | 3 | 0 | 0 | 12 |
| B5. Research store | 2 | 2 | 3 | 1 | 8 |
| B6. Tax module | 3 | 2 | 2 | 0 | 7 |
| B7. Portfolio / allocator | 4 | 2 | 3 | 0 | 9 |
| B8. Brief collectors | 1 | 2 | 1 | 1 | 5 |
| B9. Theses / themes / governance | 3 | 1 | 1 | 1 | 6 |
| **Total** | **33** | **17** | **10** | **10** | **70** |

*(B3.1 bundles the four local process skills as one row, so 70 rows cover 73 named artifacts.
A5 is a hybrid — "KEEP (already native) + ADAPT one part" — and is counted once, as KEEP.
Every group total is reproducible by counting the classed rows in §3 above it; these totals were
recomputed mechanically from the rendered table, not carried forward by hand.)*

**Every one of the 17 ADAPT rows names a destination. No row is KEEP without a cited consumer.**

The shape of the result is worth stating plainly: **10 PARK + 10 REJECT = 29% of the inventory has
no consumer or a void premise.** That is not a defect count — most of those artifacts are correct,
tested code. It is the measure of how much finance capability this repo already built ahead of
demand, and it is exactly the pattern `P2` must not repeat.

---

## 5. What the results-review slice actually consumes

Reading the matrix forward, the `P2` slice has exactly one live substrate and one live contract:

```text
rs_financial_statements ─┐
rs_corporate_actions ────┼─→ rs_fundamentals_pit (53,624 rows, knowledge_date = known_at)
rs_security_master ──────┘            │
                                      ↓
                          [G2] ASX announcement document  ← DOES NOT EXIST
                                      ↓
                          P2-03 deterministic adapter (Decimal, frozen cutoff)
                                      ↓
   EvidencePacket → ThesisVersion → ChallengeResult [G9] → PortfolioAssessment
                                      ↓                          ↑
                       TaxAssessmentReference [G7/G12]   constraints.py (B7.3)
                                      ↓
                        DecisionPacket → DecisionCase → DecisionBrief [G6 calendar, A1 mode]
                                      ↓
                          complete / revise / abstain  (never a rating or an order)
```

Everything else in the matrix is either enforcement that must survive (B7.1, B6.7, B7.7), evidence
the review cites (B1.2 / B1.3 / B1.5), or parked. **Five of the eleven boxes above are gaps** — the
slice is a real build, not an assembly of existing parts.

---

## 6. Gaps — what the slice needs and does not have

These are the capabilities `P2` requires that **no row above could be classified for**, because
they do not exist. Each is stated with the packet requirement it blocks.

| # | Gap | Blocks | Evidence |
|---|---|---|---|
| **G1** | **No local finance skill of any kind.** | Nothing directly — but it settles the mission's framing: Part A is a method-borrow, not a port. | `.claude/skills/` holds four process skills only. |
| **G2** | **No ASX announcement document acquisition.** There is no ingestion path for the results announcement itself. `parse_json_announcements` exists but is dead — *"announcements (JSON) is a stretch goal once an authenticated endpoint exists"* — and `migrations/0030` dropped the legacy `asx_announcements` table. | **The whole of `P2` required-work item 1** — *"Freeze the document, security identity, reporting period, currency, units, knowledge cutoff, source hashes"* (`…plan:294-295`). Without a document there is nothing to freeze or hash. | `asxos/ingestion/regulatory.py:11-12,105-106`; `migrations/0030_drop_non_asxos_schema.sql:48` |
| **G3** | **No statutory-vs-underlying separation.** `rs_financial_statements` stores one vendor-normalised set. The "underlying"/adjusted figures a company reports exist only in the announcement. | `P2` required-work item 3 — *"Reconcile statutory versus underlying metrics and explain every adjustment"* (`:297`) — and Part A row A1. | `migrations/0027_research_store.sql:68-88` (no adjustment columns) |
| **G4** | **No units/scale field.** The table carries `currency` but not scale (thousands vs millions). Unit discipline is asserted in the method, not enforced by the schema. | `P2` item 1's *"units"*; A1's period-and-unit discipline. | `migrations/0027_research_store.sql:77` |
| **G5** | **No guidance store.** Nothing records company guidance, so a guidance *change* cannot be computed. | `P2` item 4 — *"guidance changes"* (`:298`) — and A2's guidance bridge. | no `guidance` column or table in `migrations/` |
| **G6** | **No real trading calendar.** `TradingSessionCalendar` is mandatory on every `DecisionPacket` (`types.py:449`) and `resolve_expiry` raises when sessions run out (`:190-194`), but the only instance in the repo is the demo's, labelled synthetic. | **Any real packet at all.** This is a hard prerequisite, not a polish item. | `asxos/domain/decision_engine/types.py:163-195,449`; `demo.py` |
| **G7** | **No `TaxAssessmentReference` producer.** Nothing emits the typed `{applicability, readiness}` handle the contract requires, and unresolved readiness blocks every action state. | `DecisionPacket` construction; B4.5; B6.2. | `types.py:402-420,512-516`; no producer in `asxos/domain/tax/` |
| **G8** | **`filing_date` is not a release timestamp.** The schema itself warns it *"often defaults to period_end"* and that `report_date` *"MAY be future/scheduled"*. Deriving `EvidenceItem.known_at` from vendor dates alone is approximate. | The `known_at <= knowledge_cutoff` gate (`types.py:249-251`) — the packet's *"no post-cutoff evidence"* acceptance gate (`:307`) is only as strong as this date. | `migrations/0027_research_store.sql:73-76` |
| **G9** | **No independent-challenger surface exists.** `ChallengeResult.independent_of_author: Literal[True]` is enforced by the contract, but no agent, command or skill produces one. | `P2` item 5 and `P2-04`. | `.claude/agents/` — no challenger agent; `types.py:327` |
| **G10** | **No prompt-injection defence for externally-sourced text.** The results announcement is untrusted attacker-controllable input, and the known `m14_candidate_agent_db_role_scoping` gap means an agent's "SELECT-only" instruction is prompt-level only, with an unrestricted `execute_sql` grant beneath it. | `P2`'s *"prompt-injection resistance"* acceptance gate (`:308`). | `.claude/rules/portfolio-conventions.md` §Known gap |
| **G11** | **No agent→thesis route exists.** The macro-thesis and theme paths work end to end; the thesis path is built and **guaranteed to raise** (B9.5). So even after `P2` produces a review artifact, there is no existing mechanism by which it becomes a governed thesis draft. | Not `P2` itself (which persists nothing), but **the "separate work order" the packet defers thesis-revision persistence to** (`…plan:310-311`). Naming it now stops that work order being scoped as "just call the existing path." | `theses/service.py:745,757,793`; `theses/schemas.py:344`; `governance/agent_run_service.py:60` |
| **G12** | **The tax module has no real input path.** Its only caller hardcodes `dividends=[]` and `realised_gains=[]`, so franking, Medicare, Div 296, the 45-day rule and net capital gain have never run against production data. | **G7 directly.** A `TaxAssessmentReference` with `readiness="pass"` cannot be honestly produced today. | `asxos/cli/tax.py:93,99` |

**G2 is the load-bearing one.** Every other gap is solvable inside the slice; G2 determines whether
the slice can run on a real announcement at all, or must run on a **manually supplied, hashed
document fixture**. `P2-02` must decide this explicitly rather than discover it.

**G6, G7 and G12 together are the honest ceiling on this slice.** Without a real trading calendar
no packet validates; without a fed tax module no packet can carry `readiness="pass"`. That is not a
blocker — the contract already has the right answer for it (`readiness="unknown"` +
`missing_or_uncertain_inputs`, which mechanically forces a non-action state). It does mean the
truthful outcome of the first real results review is very likely **`abstain` or `revise`, not
`complete`** — and per the standing governor posture on mission scoping, **abstention is a success,
not a failure.**

---

## 7. Requires a governor amendment — flagged, not assumed

Per `target-architecture.md` **B.4**: adding or removing a field, or a row in a ruled table, is a
**governor amendment**; tightening a validator is not. Three items in this matrix cross that line.

### A1 — `DecisionBrief.mode` widening — **PRE-APPROVED, conditions attached**

James pre-approved widening `mode` beyond `Literal["synthetic_prototype"]`
(`target-architecture.md` B.5). **No fresh ruling is needed**, but the conditions are binding and
belong in `P2-02`'s freeze: it lands **inside** the results-review mission with a real consumer and
tests; the all-synthetic-or-all-real non-mixing invariant is preserved; a synthetic case must never
become renderable as real evidence. Rows affected: **B4.9**.

### A2 — the review-surface verdict vocabulary — **NEEDS A FRESH RULING**

There is a live collision between two governed instructions:

- **Appendix B.3** rules the state→verdict map and Appendix B.2 states **"No fourth definition may
  be created"**; `MemoVerdict = ADD | TRIM | EXIT-CANDIDATE | REVIEW | GOOD HOLD` is mechanised at
  `types.py:26,85-99`, and `recommendation-schema.md:24-27` binds every memo surface to it —
  naming `/pm-review` as the surface (`:39-40`).
- **The packet's `P1-04`** directs that review surfaces be rewritten so that *"Valid states are
  `CLEAR`, `ATTENTION`, `BLOCKED`, and `EVIDENCE_THIN`, not a synthetic buy/add/trim/exit signal"*
  (`…execution-plan-2026-08-12.md:250-252`).

`/pm-review` today emits the B.3 vocabulary (`.claude/commands/pm-review.md:43`). Under `P1-04` it
would emit a second one. Both readings are defensible — they may be **different altitudes**
(evidence-health status vs decision verdict) rather than rivals — but that is exactly a **ruled-table
question**, and B.4 reserves it to the governor.

**Ask:** does the CLEAR/ATTENTION/BLOCKED/EVIDENCE_THIN set become a **new ruled row in Appendix B**
as a distinct evidence-health vocabulary (with an explicit statement that it is not a verdict), or
does `P1-04` adopt the existing B.3 memo vocabulary? Rows affected: **B3.2, B1.4, B8.2**. Owner of
the consequence: `P1-04`, which has not yet run.

### A3 — `security_id` as canonical identity — **ALREADY RULED; recorded for sequencing**

Appendix B.3 amendment 1 requires replacing symbol-as-identity with a canonical `security_id` from
`rs_security_master`, with `symbol`/`exchange` as display attributes only. `types.py:275-277`
already carries `security_id`, `symbol` and `exchange` as separate fields, so the contract shape is
in place. **No new ruling needed** — but `P2-02` must state which column of `rs_security_master`
*is* the `security_id`, because nothing in the repo asserts that binding today. Rows affected:
**B5.1, B4.2**.

**Nothing else in this matrix adds or removes a field or a ruled row.** Every other ADAPT is an
adapter, a consumer, or a validator-level change.

---

## 8. What `P2-02` must freeze

`P2-02` is "Freeze results evidence and artifact contracts", with completion proof
*"Schema/fixture review and source hierarchy"*. This matrix says it must freeze **eight** things,
and explicitly **not** freeze a ninth.

1. **The document-acquisition decision (G2).** Real feed, or a manually supplied hashed document
   fixture? Everything downstream depends on this and nothing in the repo answers it. If fixture:
   freeze the fixture's identity, its hash algorithm, and the rule that a fixture can never be
   labelled `data_mode="real"` without a real acquisition path.
2. **The source hierarchy, verbatim and ranked.** ASX announcement and audited statements first;
   issuer presentation second; complete transcript where lawfully available; reconciled ASXOS PIT
   records; licensed consensus only with explicit provenance and rights; news contextual and
   never load-bearing (`…plan:288-291`). Freeze it with `rs_estimates` (B5.6) explicitly
   **out of scope** — there is no licensed consensus feed.
3. **The frozen-input tuple.** Document identity + hash · `security_id` (§7 A3) · reporting period
   · `period_type` · currency · **units/scale (G4)** · `knowledge_cutoff` · the ASXOS evidence
   snapshot identity. This is `P2`'s required-work item 1, and three of its eight elements have no
   column today.
4. **The `known_at` derivation rule (G8).** State explicitly how `EvidenceItem.known_at` is derived
   when `filing_date` defaults to `period_end` and `report_date` may be a scheduled future date.
   An approximate `known_at` silently weakens the no-post-cutoff-evidence gate.
5. **The statutory/underlying reconciliation contract (G3).** How an adjustment is represented,
   and the rule that **every** adjustment carries an explanation and an evidence citation. Freeze
   the representation even though no column exists yet — the schema follows the contract.
6. **The trading-calendar source (G6).** Which ASX session calendar, versioned how
   (`calendar_id` + `calendar_version`, `types.py:172-173`), and what happens when it runs short of
   sessions after a historical cutoff. **A real packet cannot be built without this.**
7. **The `TaxAssessmentReference` producer contract (G7 + G12).** Which function emits
   `{applicability, readiness}` — B6.2's `tax_view_*` is the only sane candidate — and, critically,
   the rule that a results review whose tax consequence is unknown emits `readiness="unknown"`,
   which mechanically forbids any action state (`types.py:512-516`). **Freeze `unknown` as the
   default, not `pass`**: the aggregator has never been fed real dividends or realised gains
   (`asxos/cli/tax.py:93,99`), so `pass` would be an unearned assertion. **UNKNOWN is a valid,
   successful outcome, not a failure.**
8. **The abstention and injection fixtures.** The negative controls: incomplete evidence must force
   abstention (`:308`), and an adversarial document must not move a number or a citation (G10).
   Extend `demo.py`'s `_blocked_case()` (B4.10) rather than inventing a parallel fixture set.

**What `P2-02` must NOT freeze:**

- **Any persistence schema.** `P2` writes nothing (`…plan:310-311`). `thesis_evidence` (B9.3) is the
  eventual destination, but designing its writer inside `P2-02` would be the exact
  build-without-a-consumer failure this matrix exists to prevent. The agent→thesis route it would
  need does not exist either (**G11**).
- **The allocator's re-entry (B7.5).** Parked. `P2` produces analysis, not allocation.
- **Lot selection or forex gain (B6.4, B6.5).** Both are zero-consumer today and both are
  *disposal* mechanics. A results review analyses; it does not sell.
- **`rs_factor_scores` or any quant lane revival (B5.5, B5.7).** Parked by the repo's own consumer
  test; reviving it inside `P2` would be a second, unasked-for programme.
- **`portfolio/monitor.py`'s attribution engine (B7.9).** Appendix C will need it at `P7`; it has no
  consumer now.
- **The `P1-04` vocabulary question (§7 A2).** That is the governor's, and it is upstream of
  `P2-02` only if `P2`'s artifact is rendered through `/pm-review`. If `P2-05` renders through its
  own surface, `P2-02` can proceed and A2 stays with `P1-04`.

---

## 9. Boundaries — what this document does not do

- It **authorises no implementation.** Every row is a classification; every build still needs its
  own approved work order.
- It **changes no contract.** `types.py` and Appendix B are unmodified; §7 flags three amendment
  questions and answers none of them by fiat.
- It **proposes no capital action, rating, price target, position size or order.** s766B firewall.
- It **proposes no Model A output as a decision basis**, and does not weaken rule #11's enforcement
  point (B7.1).
- It **deletes nothing.** PARK and REJECT are dispositions for later, owned by `P1-04`/`P1-05`; the
  only artifact this mission created is this file.
