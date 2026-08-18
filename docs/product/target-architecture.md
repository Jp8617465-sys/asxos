# ASXOS research-to-decision investment engine — target architecture

**Status:** CANONICAL — the ratified target architecture for asxos (ratified 2026-08-10, digest
`d6d888a`, merged as `9ede7ad` via PR #79)
**Scope:** product objective, logical architecture, technology boundaries, brownfield migration, and acceptance gates
**Prepared:** 2026-08-10 (Australia/Brisbane) · **Governor:** James
**Observed repository base:** `main@1b471b60cdaa176692cc5f987e8399acfdab03d9`
**Last verified:** 2026-08-13 (Appendix B.6 added — the governor's review-state altitude ruling; **additive only**, B.1–B.5 and the §1–§23 body unchanged) · 2026-08-12 (Appendix B amended under the governor's source-of-truth ruling — B.1 rows ratified, B.2 corrected, B.4/B.5 added; §1–§23 body unchanged) · 2026-08-10 (ratification)
**Owner:** James ratifies; arbi drafts amendments via reviewed PR and never self-approves
**Superseded by:** N/A

**Authority ceiling:** this document defines the *target*. It authorises **no** code, migration,
deployment, production write, recommendation, order, or capital action. Implementation proceeds only
under a separately approved work order per stage (§15).

**Ratification flow.** James approves one exact PR commit SHA/digest; that approval permits merge;
the merged document is then canonical. Approval is of the digest, not of a document already on
`main`. **This flow completed on 2026-08-10** and governs every future amendment to this document.

**Standing constraints that this architecture does not relax:**
- **CLAUDE.md rule #11 — the Model A quarantine stands.** No Model A output may enter the
  capital-evidence path. The decay analysis (19,032 matured signals, `corr(ml_prob, 21d) = −0.03`,
  conviction inverted at the top) is the reason, and this architecture does not reopen it.
- **`migrations/0042_rules_integrity.sql` must not be applied.** It is not on `main`; it is preserved
  on the draft `claude/rules-integrity-build` branch in PR #80 and remains in the local worktree.
  Compatibility with this architecture is not authority to apply it.
- The **personal-advice firewall** (execution stays with James) and **Decimal-only domain
  arithmetic** are unchanged.

**What this document supersedes on merge:** `docs/proposals/arbi-outcome-programme-convergence-sprint-2026-08-08.md`
and `docs/proposals/asxos-research-to-decision-live-slice-brief-2026-08-10.md` (both untracked working
copies; their load-bearing content is carried in Appendices D and E). It **amends**
[`north-star.md`](north-star.md) and [`portfolio-policy.md`](portfolio-policy.md); those amendments
are James's to ratify on the same merge.

---

## 0. Errata — corrections applied at ratification

The body below (§1–§23) is the ratified architecture **as amended by these seven corrections**,
each verified against live repository and database state on 2026-08-10. Where the body and this
errata conflict, **the errata wins**.

**E1 — §19.2 / §19.3 overstate what is open; §19 understates what is open.**
`portfolio-policy.md:26` already declares an XJO **total-return** benchmark and `:23-25` a
**weeks-to-months** horizon. These settle *policy direction*. They do **not** settle the executable
contract — exact series/provider, global-exposure treatment, evaluation windows, expiry horizons and
the risk/loss mandate all remain open. See **Appendix F** for the eight bounded decisions.

**E2 — §8.5 `DecisionPacket` is not a new contract, and it is not `recommendation-schema.md` restated.**
Three definitions now exist: `docs/product/recommendation-schema.md` (a human memo/view contract, on
`main`), §8.5 of this document, and `asxos/domain/decision_engine/types.py` (a tested, branch-only
prototype preserved in PR #81, implementing a candidate canonical cross-domain aggregate).
**Appendix B** reconciles them
field-by-field and designates one canonical. No fourth definition may be created.

**E3 — §9.4's learning loop already exists and has already failed once, for a non-architectural reason.**
`docs/product/portfolio-outcome-ledger.md` is the loop; it holds two rows, both `_pending James_`
since 2026-07-11. `/pm-review` persists nothing. The failure mode was **unmechanised capture**, not
missing architecture. Any Stage 5 design whose disposition step is not ~one keystroke inherits the
same failure.

**E4 — §2.4's tax framing needs correcting in one direction only.**
Tax is **not** guaranteed alpha. It is a quantifiable implementation advantage and a decision
constraint **whose benefit must be measured, not asserted**. §2.4's demotion to "downstream
constraint" is nonetheless in tension with `docs/research/operating-model-architecture.md` on `main`
("the structural edges available are patience, tax (franking + CGT), low turnover"). The resolution
is the measurement contract in **Appendix C**, not a claim either way.

**E5 — §0 and §14 mislocate migration 0042.** It is not "on `main`, unapplied." It is absent from
`main`, preserved in draft PR #80, and retained in the local worktree. It also carries an irreversible
`ALTER TABLE theses DROP COLUMN invalidation_conditions` whose safety rests on a comment rather than
on the migration's own precondition assertions.

**E6 — §6.2's point-in-time requirement was violated in production. The capture gap is CLOSED
FORWARD as of 2026-08-12; the loss it already caused is permanent.**
*(Original wording, 2026-08-10: "already violated in production … the system cannot reconstruct
what it saw on any past date … the only finding where delay causes permanent, unrecoverable
loss." Re-verified against live production 2026-08-18; the finding is now **historical**, not
ongoing. Keep reading — it is not simply "done".)*

**Closed forward.** Migration `0043_price_revisions.sql`, applied to production 2026-08-12 as
version `20260812092925`, installs an append-only revision ledger. Verified live in the
production database on **2026-08-18** by direct catalogue query:

- triggers `prices_revision_capture` and `prices_reject_untracked_truncate` on `prices`;
- trigger `price_revisions_append_only` on `price_revisions`;
- function `_capture_price_revision()` present.

`asxos/ingestion/prices.py:51-59` still emits the same destructive
`ON CONFLICT (symbol, dt) DO UPDATE … adj_close = EXCLUDED.adj_close`. That is now **by
design**: the statement is unchanged, and the trigger — not the application — is what captures
the prior row. Do not "fix" the upsert; the capture point moved to the database.

**Three qualifications, all live-verified 2026-08-18. None of them are closed.**

1. **`price_revisions` holds 0 rows.** The ledger has never captured a single revision, so it is
   **unproven end-to-end in production**. A trigger that exists is not a trigger that has fired.
2. **There was no backfill, and none is possible.** Every `adj_close` rewrite before 2026-08-12
   is gone. History prior to that date remains **unreconstructible**, which is exactly the loss
   the original erratum warned about — it happened, and 0043 does not undo it. Stage 1's replay
   guarantee therefore cannot be claimed over pre-2026-08-12 price evidence (see E7).
3. **A second, distinct defect is live and unaddressed: `adj_close` is frozen at first ingest,
   so corporate actions never propagate backwards.** `jobs/sync_prices.py:278` calls
   `fetch_and_upsert_bulk(current, …)` only for weekdays from *the day after the latest observed
   price date* through today, so a past date is **never re-fetched**. When a consolidation or
   split re-bases the provider's series, only rows from that day forward carry the new basis and
   the stored series takes a raw step change instead of a back-adjusted one. Measured in
   production on 2026-08-18:

   | Symbol | `rs_corporate_actions` split | One-day `adj_close` step in `prices` | Observed ratio |
   |---|---|---|---|
   | `ID8.AU` | ex-date 2026-08-14, ratio `0.005` (1-for-200) | 2026-08-12 `0.003` → 2026-08-13 `0.800` | **266.7×** |
   | `SCP.AU` | ex-date 2026-08-06, ratio `0.016667` (1-for-60) | 2026-08-04 `0.056` → 2026-08-07 `2.600` | **46.4×** |
   | `CEL.AU` | ex-date 2026-07-29, ratio `0.05` (1-for-20) | 2026-07-27 `0.120` → 2026-07-28 `2.400` | **20.0×** |

   **35 distinct symbols** carry a one-day `adj_close` step greater than 5×. Corroborating the
   mechanism: `adj_close = close` on **2,318 of 2,319** rows at the latest price date
   (2026-08-17) and on 588,717 of 754,230 rows overall — the column is not carrying a
   back-adjustment at all, it is carrying the raw close as first seen. Any return, volatility or
   momentum computed across one of those step dates is wrong by the consolidation ratio.
   0043 does not detect this, because no historical row is ever rewritten — so there is nothing
   for the capture trigger to capture.

**Net.** E6's *capture* mechanism exists and is live; E6's *loss* is historical and permanent;
and the adjustment-propagation defect at (3) is new, open, and unowned. E7's Stage-1 reordering
still stands on (2) and (3).

**E7 — §15 Stage 1 ordering is reversed, and §11.3's object-store deferral is withdrawn as a default.**
Stage 1 contains future raw-evidence loss **first** (E6 plus raw provider payload retention), and
only then repairs and broadens `derive_fundamentals_pit`. Market-provider payloads are already raw
evidence, so "no document source yet" is not grounds to defer immutable raw storage. Any deferral
must be an explicit James ruling **and must revise the Stage 1 replay/lineage exit gate** — a replay
guarantee cannot be claimed over evidence that was never retained.

**Framing note on §7 / §15 Stage 2 (not an erratum).** A method-agnostic research registry is not
"Model A again." Its purpose is reproducibility, failed-variant retention, and protection from
self-deception across quantitative *and qualitative* research, including thesis underwriting. What
does carry forward is a scale limit: at weeks-to-months horizons over a handful of positions, ~10–30
decisions/year **cannot statistically prove alpha** and will not for years. **Stage 5 is therefore
initially a process audit plus descriptive outcome evidence**, and must be labelled as such.

---

## 1. Executive decision

ASXOS should be architected as a **research-to-capital-decision-to-learning engine**, not as
an agent that writes a morning brief.

The brief remains important, but it is an experience layer over an immutable investment
decision. It is not the product architecture and must not contain financial logic of its own.

The proposed north star is:

> Increase the probability of benchmark-relative, risk-controlled investment outperformance by
> identifying durable opportunities and emerging themes early, converting point-in-time evidence
> into falsifiable investment theses, allocating capital under uncertainty, protecting capital
> when evidence deteriorates, and learning from every decision.

The target system is:

> A Python modular monolith backed by an immutable analytical lake and an operational Postgres
> database, orchestrated as a versioned data-asset graph, and producing immutable investment
> decision packets that James receives, dispositions, and later evaluates.

The brownfield strategy is **preserve, adapt, retire, and add**:

- **Preserve:** useful ingestion knowledge, Supabase operational state, evidence/governance
  primitives, thesis event history, Decimal-exact financial logic, CLI/email delivery, and the
  human broker boundary.
- **Adapt:** jobs into data assets, the research-store schema into a populated point-in-time
  evidence system, themes into evidence-backed hypotheses, theses into versioned investment
  cases, and the brief into a pure renderer.
- **Retire:** Model A as a capital input, prompt-defined portfolio rules, production scheduling
  in GitHub Actions, duplicated scheduler ownership, document-only outcome ledgers, and the old
  signal-driven allocator path.
- **Add:** immutable raw storage, a hypothesis/strategy registry, rigorous research evaluation,
  a quantified theme engine, a portfolio-risk and capital engine, an immutable
  `DecisionPacket`, reliable delivery receipts, and a unified learning loop.

This is a brownfield convergence, not a full rewrite.

---

## 2. Product objective and measurement contract

### 2.1 Primary objective

The product objective is not feature completion, brief delivery, thesis count, alert count, or
agent activity. It is better investment decisions and outcomes relative to an appropriate
benchmark and risk budget.

For an ASX-first long-only portfolio, the default benchmark candidate is an S&P/ASX 200
**total-return** series, not a price-only series. An accumulation/total-return benchmark includes
reinvested dividends. If the investable universe expands materially beyond Australian equities,
the benchmark must become an explicit blended policy benchmark rather than silently retaining
XJO.

No single profitable decision, backtest, month, or paper case proves alpha.

### 2.2 Outcome hierarchy

The system should report four distinct kinds of success. They must never be collapsed into one
score.

| Dimension | What it answers | Candidate measures |
|---|---|---|
| **Investment outcome** | Did the portfolio add value? | Total return versus declared total-return benchmark; excess return after costs; hit rate by horizon; attribution by strategy/theme/thesis |
| **Capital protection** | What risk was taken to achieve it? | Maximum drawdown; downside capture; volatility; beta/factor/sector concentration; liquidity; loss to invalidation; turnover |
| **Decision process** | Was the decision defensible when made? | Evidence completeness; independent challenge; thesis adherence; sizing-rule adherence; explicit abstention; stale/missing data visibility |
| **System integrity** | Can the result be trusted and reproduced? | Data freshness; point-in-time validity; replay equality; delivery receipt; job reliability; restore proof; unresolved data-quality findings |

Raw P&L must not become the only reward signal. Optimising only for P&L encourages uncontrolled
risk and can reward a bad process that happened to get lucky. Process quality and financial
outcome remain separate but linked.

### 2.3 What “protect capital” means

The system cannot reliably guarantee that it will identify every losing investment in advance.
It can:

- refuse to decide when evidence is insufficient;
- estimate ranges rather than pretend to know point outcomes;
- size by loss budget, uncertainty, liquidity, and correlation;
- enforce portfolio and instrument constraints;
- monitor falsifiers and material events;
- distinguish a review requirement from an executable hard exit;
- surface deterioration before it becomes an unnoticed loss; and
- retire research whose paper/live behaviour fails its promotion contract.

### 2.4 Tax position

Tax is not the alpha engine. It is a downstream constraint and scenario overlay.

Research and gross investment merit should be evaluated before tax. Once a decision touches real
holdings, lots, disposals, FX, ESS restrictions, or CGT timing, applicable tax facts become a hard
decision-readiness requirement. Unknown tax applicability must produce a named refusal or range,
not a fabricated answer.

---

## 3. Assumptions and constraints

This architecture assumes:

- a single user and governor, James;
- ASX-first coverage with room for global securities and ETFs;
- long-only, no leverage by default, and retail execution;
- weeks-to-months investment horizons, with daily/EOD computation plus event-triggered refreshes;
- no requirement for high-frequency or real-time trading;
- James executes every real trade through his broker;
- Python and SQL remain the primary implementation languages;
- current scale is compatible with a modular monolith rather than microservices;
- cost and operational simplicity matter; and
- model and LLM outputs are decision inputs, never self-authorising capital actions.

Revisit the architecture if any of these assumptions changes materially.

---

## 4. Design principles

1. **Evidence before narrative.** Every material claim resolves to a source snapshot and
   knowledge cutoff.
2. **Point-in-time or not admissible.** Backtests and decisions may use only information the
   system could have known at that time.
3. **Separate alpha, construction, judgment, and presentation.** Predicting returns, selecting
   investments, sizing capital, challenging a case, and rendering a brief are different jobs.
4. **Research earns promotion.** A good story or backtest does not enter capital logic without
   out-of-sample and paper evidence.
5. **Uncertainty is first-class.** Ranges, confidence, missingness, and abstention are valid
   outputs.
6. **One immutable decision truth.** CLI, email, web, and future conversational surfaces render
   the same content-addressed decision object.
7. **Close the loop.** Every decision must be linkable to what was known, what James saw, what he
   decided, what happened, and what should change.
8. **Agents are replaceable workers.** They produce typed proposals; they do not own truth,
   governance transitions, calculations, delivery state, or capital.
9. **Deterministic financial kernels.** Money, tax, portfolio arithmetic, data-quality rules, and
   state transitions are code and database contracts, not prompt prose.
10. **Modular monolith first.** Introduce infrastructure only when it resolves a measured
    boundary or reliability problem.
11. **No autonomous execution.** The system can be analytical and opinionated while remaining
    non-executing.
12. **Fail visibly, not optimistically.** Missing, stale, conflicting, unparseable, or
    undelivered states must remain visible.

---

## 5. High-level architecture

```text
 MARKET AND COMPANY SOURCES
 prices · fundamentals · estimates · filings · ASX announcements
 news · macro · corporate actions · index membership · portfolio state
                            │
                            ▼
 ┌────────────────── EVIDENCE PLANE ─────────────────────┐
 │ Source adapters → immutable raw source objects        │
 │                  → point-in-time canonical facts      │
 │                  → security master + quality gates    │
 └──────────────────────────┬────────────────────────────┘
                            ▼
 ┌────────────────── RESEARCH PLANE ─────────────────────┐
 │ Features/factors · event extraction · theme evidence │
 │ Hypothesis registry → evaluation → strategy registry │
 │ Eligible strategies → candidate opportunity set      │
 └──────────────────────────┬────────────────────────────┘
                            ▼
 ┌────────────────── DECISION PLANE ─────────────────────┐
 │ EvidencePacket → ThesisVersion → ChallengeResult      │
 │                → PortfolioAssessment                  │
 │                → immutable DecisionPacket             │
 └──────────────────────────┬────────────────────────────┘
                            ▼
 ┌────────────── EXPERIENCE AND LEARNING PLANE ──────────┐
 │ Brief / CLI / web / email                             │
 │          → DeliveryReceipt                            │
 │          → James Disposition                          │
 │          → paper / reconciled actual Outcome          │
 │          → attribution and LearningReview             │
 │          → research promote / revise / pause / retire │
 └───────────────────────────────────────────────────────┘

 Cross-cutting control plane:
 lineage · data contracts · quality · permissions · model/prompt versions
 idempotency · governance events · transactional outbox · observability
 release identity · backup/restore · replay
```

The control plane does not create investment merit. It makes the other planes trustworthy.

---

## 6. Evidence plane

### 6.1 Dual storage model

The system needs two complementary stores.

#### Immutable analytical store

Use S3-compatible object storage for:

- original vendor payloads and files;
- ASX announcements and documents;
- immutable extraction artifacts;
- partitioned canonical Parquet data;
- research-run artifacts and model outputs; and
- rendered decision packets where exact bytes matter.

Suggested raw key structure:

```text
raw/{provider}/{dataset}/ingest_date=YYYY-MM-DD/run_id={uuid}/{content_hash}.{ext}
```

Raw objects are append-only. Corrections create new versions; they do not overwrite historical
evidence.

#### Operational system of record

Keep Postgres/Supabase for:

- instrument identities and current serving projections;
- pipeline and data-quality state;
- governance events and permissions;
- hypotheses and strategy metadata;
- themes, theses, challenges, and portfolio state;
- immutable decision identities and metadata;
- delivery outbox and receipts;
- James dispositions; and
- outcome and learning records.

Postgres is not the sole raw archive or the only analytical warehouse.

### 6.2 Canonical temporal contract

Every material financial fact must carry sufficient temporal and provenance information:

```text
fact_id
instrument_id
fact_type
effective_at       # when the fact applies economically
known_at           # when a market participant could first have known it
ingested_at        # when this system received it
source_id
source_revision
source_object_id
content_hash
quality_status
value / payload
```

Backtests and historical decision replays must apply `known_at <= decision_cutoff`. Statement
period end, provider retrieval date, and disclosure date are not interchangeable.

### 6.3 Security master

The security master must preserve:

- stable internal instrument IDs;
- current and historical tickers;
- listing, delisting, and suspension dates;
- exchange, currency, domicile, and instrument type;
- corporate actions and adjustment factors;
- historical sector/industry classification;
- historical index membership;
- ETF/fund composition versions where applicable;
- employer/ESS relationships and tradeability constraints; and
- source mappings across vendors.

Ticker text is an alias, not identity.

### 6.4 Data quality gates

Each materialised asset has blocking or warning checks for:

- schema drift;
- uniqueness and key integrity;
- missingness and coverage;
- freshness;
- temporal validity and future leakage;
- price/corporate-action reconciliation;
- currency consistency;
- universe and index-membership validity;
- cross-source disagreement;
- document extraction completeness; and
- source licence/availability.

Downstream decision assets cannot materialise from a failed blocking input.

---

## 7. Research plane

### 7.1 Research is a governed factory

The research system separates hypothesis generation from capital eligibility.

```text
research question
  → ResearchHypothesis
  → exact universe, horizon, and economic rationale
  → FeatureSetVersion
  → reproducible ResearchRun
  → cost/liquidity/turnover-aware evaluation
  → walk-forward and untouched holdout
  → paper shadow
  → eligible decision input or retired research
```

Candidate research types include:

- value, quality, momentum, low-volatility, and other factor hypotheses;
- earnings, corporate-action, regulatory, or announcement events;
- macro/regime hypotheses;
- theme/submarket diffusion and beneficiary hypotheses;
- instrument-selection hypotheses; and
- model-assisted extraction or ranking methods.

### 7.2 Research state machine

Recommended logical states:

```text
draft
  → reproducible
  → in_sample_evaluated
  → out_of_sample_evaluated
  → paper_candidate
  → paper_observed
  → decision_input_eligible
  → paused | retired
```

No automated transition grants capital authority. `decision_input_eligible` means the research
may inform a governed investment case; it does not create a recommendation or order.

### 7.3 Required research record

Each `StrategyVersion` records:

- hypothesis and economic mechanism;
- security universe and survivorship policy;
- investment and rebalance horizon;
- exact source, feature, code, configuration, and benchmark versions;
- every tested material variation, not only the winner;
- costs, slippage, liquidity, capacity, and turnover assumptions;
- in-sample, walk-forward, untouched holdout, and paper results;
- return, drawdown, exposure, calibration, and stability metrics;
- known failure regimes and falsifiers;
- promotion decision and approver; and
- retirement reason when applicable.

Repeated research selection creates backtest-overfitting risk. Multiple testing and the number
of attempted variants must be recorded rather than hidden.

### 7.4 Theme and emerging-trend engine

A theme is a versioned investment hypothesis, not a label.

`ThemeVersion` should contain:

- theme statement and scope;
- evidence cutoff;
- beneficiary, loser, supplier, customer, commodity, region, and instrument relationships;
- adoption/development stage;
- announcement and earnings-language acceleration;
- revenue, capex, customer, and order-book confirmation;
- estimate revisions;
- market breadth, relative strength, volume, and dispersion;
- attention versus fundamental-confirmation gap;
- investable instruments and purity of exposure;
- falsifiers and expiry; and
- confidence separated into evidence quality and expected investment edge.

LLMs may extract entities, cluster evidence, suggest submarkets, and draft a narrative. They may
not invent financial facts, theme strength, or portfolio thresholds. Deterministic measures and
source evidence remain authoritative.

Postgres relational tables are sufficient initially. A graph database is not justified until
measured query or maintenance requirements exceed the relational model.

### 7.5 Candidate generation

The candidate opportunity set is a snapshot, not a permanent stock ranking.

`CandidateSnapshot` contains:

- declared strategy/theme sources;
- as-of and knowledge cutoff;
- eligibility universe;
- factor/event/theme evidence;
- liquidity and data-quality state;
- expected horizon;
- preliminary uncertainty;
- disqualifiers; and
- the reason the candidate is worth underwriting now.

Candidates are research prompts. They are not portfolio instructions.

---

## 8. Decision plane

### 8.1 EvidencePacket

An `EvidencePacket` freezes the admissible research context for one investment question. It
contains exact fact, document, feature, strategy, theme, portfolio, and benchmark identities.

Every material claim in later thesis and challenge artifacts must resolve to this packet or to a
subsequently admitted revision packet. The packet has a canonical hash and expiry policy.

### 8.2 ThesisVersion

A thesis is a broker-report-quality investment case plus a discipline wrapper.

Required domains:

- investment question and instrument;
- variant view—what the market may be missing;
- business/asset/fund analysis;
- management and capital-allocation evidence where relevant;
- valuation method, assumptions, and sensitivity;
- bull/base/bear scenarios;
- expected payoff range and maximum plausible loss;
- catalyst, path, and horizon;
- falsifiers and invalidation semantics;
- entry framework, review conditions, and expiry;
- liquidity and tradeability;
- portfolio, sector, factor, market, and currency interactions;
- applicable tax uncertainty; and
- explicit `ABSTAIN / NOT DECISION READY` outcome.

Syntax-valid numbers are not the same as financially underwritten numbers.

### 8.3 Independent challenge

`ChallengeResult` is generated from the same frozen evidence context and must be capable of:

- identifying omitted evidence or conflicting facts;
- challenging valuation and scenario assumptions;
- presenting the strongest bear case;
- testing catalyst, horizon, and falsifiers;
- exposing portfolio and liquidity conflicts;
- forcing revision or abstention; and
- changing the final decision state.

The challenger is not scored for agreeing with the thesis author.

### 8.4 Portfolio and capital engine

Security selection and capital sizing are separate decisions.

Inputs:

- available capital, cash flows, and current holdings;
- eligible investment cases;
- expected-return and downside ranges;
- loss to invalidation;
- volatility, beta, correlation, and factor exposures;
- sector/theme/currency/employer concentration;
- liquidity, tradeability, and position locks;
- turnover and transaction costs;
- policy constraints; and
- applicable lot/tax considerations.

Outputs:

- `initiate`, `watch`, `avoid`, `add`, `trim`, `exit_review`, or `abstain`;
- a size **range**, not an unjustified precise weight;
- staged entry/exit framework where appropriate;
- marginal portfolio risk and exposure impact;
- loss budget and scenario behaviour;
- alternatives and opportunity cost;
- constraint results; and
- what evidence would change the assessment.

Conviction may constrain a sizing envelope. It must not directly determine size without loss,
uncertainty, correlation, liquidity, and portfolio context.

### 8.5 Immutable DecisionPacket

All user-facing surfaces consume the same immutable `DecisionPacket`.

Minimum logical fields:

```text
decision_packet_id
schema_version
as_of
knowledge_cutoff
expires_at
portfolio_snapshot_id
evidence_packet_id
thesis_version_id
challenge_result_id
portfolio_assessment_id
benchmark_id
recommendation_state
size_range
staging_framework
scenario_summary
risk_summary
constraints_checked
missing_or_uncertain_inputs
decision_ask
model_and_prompt_manifest
content_hash
created_at
```

The packet is append-only. A revision creates a new packet linked to the one it supersedes.
Renderers contain no investment, tax, or portfolio logic.

---

## 9. Experience and learning plane

### 9.1 Brief design

The brief should answer, in order:

1. What materially changed since the last accepted view?
2. What existing capital is newly at risk?
3. Which theses require review or revision?
4. What one to three decisions are actually ready?
5. Which new ideas or themes deserve research but not capital?
6. What information is missing, stale, or conflicting?
7. What does James need to decide?

The brief is assembled from admitted `DecisionPacket` and monitoring identities. It does not
recalculate verdicts or introduce new thresholds.

### 9.2 Reliable delivery

Capital-relevant delivery uses a transactional outbox:

```text
DecisionPacket/render transaction
  → outbox row committed
  → delivery worker claims idempotency key
  → provider send
  → DeliveryReceipt(message_id, render_hash, delivered/failed state)
  → retry until delivered or explicitly dead-lettered
```

A committed monitoring transition without a retryable delivery record is incomplete.

### 9.3 James disposition

`Disposition` is separate from the packet:

- accept;
- reject;
- defer;
- request revision;
- choose another option; or
- take no action.

It references the exact packet hash and records James’s reasoning. It cannot mutate the packet or
retroactively change what the system claimed.

### 9.4 Outcome and learning

Outcome records separate:

- process adherence;
- thesis correctness;
- sizing/timing contribution;
- benchmark-relative result;
- transaction cost and FX contribution;
- tax effects where reliably reconciled;
- factor/sector/theme attribution;
- counterfactual alternatives; and
- whether the research, thesis, or portfolio rule should be promoted, revised, paused, or retired.

The linked identity chain is:

```text
ResearchHypothesis
  → StrategyVersion / ThemeVersion
  → CandidateSnapshot
  → EvidencePacket
  → ThesisVersion
  → ChallengeResult
  → PortfolioAssessment
  → DecisionPacket
  → DeliveryReceipt
  → Disposition
  → PaperIntent or reconciled actual action
  → OutcomeObservation
  → LearningReview
```

---

## 10. Agent and LLM architecture

Agents are bounded analytical workers operating over typed contracts.

Candidate roles:

| Worker | Permitted role | Prohibited role |
|---|---|---|
| Source extractor | Convert a source object into typed claims/entities | Decide investment merit or write canonical facts without validation |
| Research analyst | Propose hypotheses and interpret governed evaluations | Promote its own strategy or hide failed variants |
| Theme analyst | Propose theme structure and beneficiary relationships | Invent theme strength or portfolio weights |
| Thesis author | Draft a case from an admitted EvidencePacket | Cite training knowledge as evidence or approve the thesis |
| Finance challenger | Produce an independent bear case and readiness findings | Optimise for agreement or mutate the thesis |
| Portfolio explainer | Explain deterministic portfolio/risk outputs | Calculate weights or override constraints in prose |
| Brief narrator | Summarise admitted packets and changes | Introduce new financial logic or action language |

Standing controls:

- read-only data access by default;
- typed structured output with unknown-field rejection;
- explicit evidence IDs for every material claim;
- model, prompt, tool, source, and code versions persisted;
- no direct writes to canonical investment tables;
- exactly-once governed materialisation through application services;
- deterministic validation before persistence;
- independent challenge uses a frozen evidence cutoff;
- Model A remains excluded from the capital-evidence path; and
- no agent may execute a trade.

An agent fleet is not a substitute for an orchestrator, database state machine, or financial
kernel.

---

## 11. Technology architecture

### 11.1 Recommended near-term stack

| Layer | Recommendation | Role |
|---|---|---|
| Language | Python 3.12 + SQL | Ingestion, orchestration, research, domain services, API |
| Operational database | Supabase Postgres | Governance, current serving state, investment objects, outbox, dispositions, outcomes |
| Immutable storage | S3-compatible object storage | Raw payloads, documents, Parquet, artifacts, exact renders |
| Analytical query | DuckDB over Parquet | Local and batch research analytics at current scale |
| Orchestration | Dagster preferred; managed or hosted deliberately | Asset graph, partitions, backfills, lineage, checks, retry state |
| Compute/serving | Render initially | FastAPI, workers, renderer, and optionally orchestrator services |
| Source and delivery lifecycle | GitHub | Source control, CI, review, release—not production scheduling |
| API | FastAPI | Read/query and governed command boundary |
| Delivery | Resend or equivalent behind an outbox worker | Email transport only |
| Retrieval | Postgres full text + `pgvector` if justified | Evidence discovery, never source-of-truth replacement |
| Observability | Structured event/job records plus error and asset monitoring | Freshness, failures, lineage, delivery, replay, restore evidence |

### 11.2 Current-stack disposition

#### Supabase

Keep it. It is appropriate for the operational relational domain. Do not require it to be the
only raw archive or the research compute engine. Database backups do not automatically protect
separate object-store content, so both stores require explicit backup and restore proof.

#### Render

Keep it as a compute and serving platform while workload and team size remain modest. Render cron
may remain as a transitional scheduler, but orchestration state and dependency logic should move
to the asset orchestrator. Render is not an investment source of truth.

#### GitHub Actions

Keep it for CI, tests, build verification, release, and manually invoked diagnostics. Retire it as
the owner of scheduled production market workflows. The same production job must not be owned by
both GitHub and Render.

#### Dagster

Use software-defined assets, time partitions, backfills, and blocking asset checks to represent
the evidence and research graph. If operating Dagster creates more burden than value during the
first vertical slice, preserve its interfaces and temporarily run the same idempotent partitioned
assets through one Render-owned scheduler. Do not retain permanent dual ownership.

#### DuckDB and Parquet

Use DuckDB for analytical reads over partitioned Parquet. Do not introduce Snowflake, Spark,
ClickHouse, or another warehouse until volume, concurrency, or latency demonstrates a need.

### 11.3 Explicit non-goals

Do not introduce now:

- microservices;
- Kubernetes;
- Kafka or a general event-streaming platform;
- a dedicated graph database;
- a separate vector database;
- a full Rust/Go rewrite;
- real-time trading infrastructure;
- autonomous brokerage execution; or
- multi-user/auth architecture.

---

## 12. Core logical records

These are logical contracts, not a command to create one table per row.

| Record | Purpose | Mutability |
|---|---|---|
| `SourceObject` | Original external payload/document identity | Append-only |
| `MarketFact` | Canonical point-in-time observation | Append-only/versioned |
| `FeatureSnapshot` | Reproducible derived feature set at a cutoff | Immutable |
| `ResearchHypothesis` | Economic question and falsifiable claim | Versioned |
| `ResearchRun` | Exact evaluated experiment | Immutable |
| `StrategyVersion` | Governed interpretation and promotion state | Append-only transitions |
| `ThemeVersion` | Evidence-backed theme/submarket hypothesis | Versioned |
| `CandidateSnapshot` | Time-bounded opportunity set | Immutable |
| `EvidencePacket` | Frozen evidence admitted to one case | Immutable |
| `ThesisVersion` | Broker-report-quality investment case | Immutable version |
| `ChallengeResult` | Independent challenge against frozen context | Immutable |
| `PortfolioAssessment` | Capital/risk implications and size range | Immutable |
| `DecisionPacket` | Canonical investment decision truth | Immutable |
| `DeliveryReceipt` | Exact rendered/delivered artifact identity | Append-only status |
| `Disposition` | James’s response to the exact packet | Append-only |
| `OutcomeObservation` | Paper/reconciled actual result at a horizon | Append-only by horizon |
| `LearningReview` | Process/outcome attribution and promotion decision | Immutable/versioned |

The architecture should minimise duplicate truth. Reuse existing tables where their contracts
can satisfy these roles without semantic ambiguity.

---

## 13. Comparison with current ASXOS

ASXOS is currently strongest in governance, discipline, operational jobs, and the delivery shell.
It is weakest in repeatable alpha research, risk-aware capital allocation, immutable decision
truth, and linked investment learning.

### 13.1 Preserve

- ingestion adapters and provider-specific knowledge;
- `migrations/0027_research_store.sql`’s direction: security master, PIT fundamentals, factor
  scores, estimates, and index membership;
- governance events, evidence tiering, and human approval;
- thesis revisions and monitoring concepts;
- Decimal-exact portfolio/tax kernels where verified;
- FastAPI, CLI, HTML/email rendering capabilities;
- paper portfolio and macro outcome concepts; and
- the no-broker/human-execution boundary.

### 13.2 Adapt

- ingestion jobs: raw immutable landing first, canonical facts second;
- research tables: populate, version, validate, and connect them to a research registry;
- themes: convert labels/narratives into evidence-backed versioned hypotheses;
- thesis schema: separate evidence, underwriting, discipline, challenge, and decision readiness;
- brief: become a pure renderer of admitted decision and monitoring objects;
- paper and macro scoreboards: connect them to originating research/thesis/decision identities;
- agent runs: become typed proposal provenance, not orchestration or truth; and
- Render jobs: become orchestrator-controlled assets with one scheduler owner.

### 13.3 Retire or quarantine

- Model A as a capital input;
- the signal-driven allocator and opportunity-cost path in their current form;
- hard-coded financial constants in prompts and renderer logic;
- production `schedule:` ownership in GitHub Actions;
- dual GitHub/Render scheduling;
- manual Markdown as the only decision/outcome ledger;
- financial logic inside email/CLI/brief collectors; and
- any direct agent-to-capital or agent-to-canonical-write path.

### 13.4 Build

- immutable object storage and source contracts;
- complete point-in-time ingestion and survivorship controls;
- a hypothesis/experiment/strategy registry;
- research evaluation and promotion gates;
- a quantified theme/submarket engine;
- evidence packet and thesis challenge contracts;
- portfolio-risk and capital-allocation assessment;
- immutable `DecisionPacket` and pure renderers;
- transactional alert/delivery outbox;
- linked disposition, outcome, attribution, and learning; and
- one exact operational data/decision asset graph.

ASXOS is therefore best described as:

> A sophisticated monitoring, governance, and briefing shell around an incomplete investment
> research and capital-decision engine.

The target is:

> An investment research and capital-decision engine that happens to deliver its output through
> a brief.

---

## 14. Disposition of the paused rules-integrity work

The work is valuable as a safety/control layer, but it must be reconciled to the target contracts.

| Paused item | Target placement | Proposed disposition |
|---|---|---|
| D1 invalidation state machine | Thesis monitoring and event history | Preserve design; add durable outbox and explicit delivery state |
| D2 authoring integrity | Thesis discipline validation | Preserve; ensure service and DB boundaries fail visibly for all states |
| D4 placeholder/underwritten attestation | Governance/readiness | Preserve concept; rename or narrow to `rules_attested` unless full underwriting fields are present |
| D5 output firewall | Decision admission and rendering | Preserve doctrine; implement once as a shared mechanical contract |
| R8 integrity sweep | Orchestrator asset checks | Preserve; add resolution state and independent scheduling/alerting semantics |
| D3 conviction/cap framework | Portfolio risk policy | Keep advisory; do not encode values before the portfolio/risk model and James’s rulings |
| D6 regime design | Research feature and market context | Separate conformance fixes from new investment policy; shadow-test design behaviour |
| D8 tax work | Tax decision overlay | Build in separately testable, spec-governed increments after gross case readiness |

Before any rules-integrity migration or merge:

1. ratify the target thesis/condition/readiness contracts;
2. replace destructive migration ordering with expand → generic backfill → dual-read/verify →
   contract;
3. prove zero lost legacy conditions;
4. revoke/review rule attestation after every material mutation;
5. add retryable, exactly-once alert delivery state;
6. restore the complete test suite;
7. prove backup and isolated restore; and
8. run a shadow replay before production application.

`migrations/0042_rules_integrity.sql` is not the target architecture and remains unapplied.

---

## 15. Brownfield migration sequence

### Stage 0 — Ratify objective and contracts

Deliverables:

- ratified north-star amendment;
- benchmark, horizon, and risk-measurement contract;
- logical data/decision record definitions;
- current-to-target reuse map;
- scheduler ownership decision;
- paused-work disposition; and
- one canonical programme queue.

Exit gate:

- James ratifies one exact digest;
- no competing roadmap or authority document is created; and
- no implementation is authorised merely by document existence.

### Stage 1 — Evidence foundation

Deliverables:

- immutable raw object storage;
- source-contract registry;
- stable security master identities;
- point-in-time canonical price, corporate-action, fundamental, estimate, announcement, and
  index-membership assets;
- partition/backfill contracts; and
- blocking data-quality checks.

Exit gate:

- one historical decision date can be replayed using only facts with `known_at <= cutoff`;
- raw-to-canonical lineage resolves exactly; and
- backup/restore is observed.

### Stage 2 — Research registry and evaluation

Deliverables:

- `ResearchHypothesis`, `ResearchRun`, and `StrategyVersion` contracts;
- reproducible cost/liquidity-aware backtest harness;
- walk-forward/holdout and multiple-testing records;
- benchmark and attribution service; and
- paper promotion state machine.

Exit gate:

- one hypothesis can be reproduced from raw data through evaluation;
- failed variants remain visible; and
- no research can self-promote into capital logic.

### Stage 3 — Theme and candidate engine

Deliverables:

- versioned `ThemeVersion` and relationship model;
- deterministic theme evidence measures;
- LLM extraction/synthesis boundary;
- candidate snapshot contract; and
- candidate quality and expiry checks.

Exit gate:

- one emerging theme/submarket and one security candidate can be reproduced from exact evidence
  without converting either into a recommendation.

### Stage 4 — One governed paper investment case

Use one ordinary ASX equity as the positive control. Do not use HUBS/ESS as the first positive
case; retain HUBS and CBA as negative-control fixtures for locks, tax uncertainty, detached
ladders, stale evidence, and born-violated conditions.

```text
one eligible research/theme input
  → CandidateSnapshot
  → EvidencePacket
  → ThesisVersion
  → independent ChallengeResult
  → PortfolioAssessment
  → immutable DecisionPacket
  → identical CLI/email render
  → DeliveryReceipt
  → James Disposition
  → paper intent
```

Exit gate:

- exact evidence, thesis, challenge, portfolio, packet, render, delivery, and disposition
  identities resolve;
- missing evidence forces abstention;
- renderers contain no financial logic;
- no Model A input enters the chain; and
- the process remains non-executing.

### Stage 5 — Outcome learning

Deliverables:

- horizon-based paper observations;
- declared total-return benchmark comparison;
- process-versus-P&L attribution;
- strategy/theme/thesis/sizing contribution records; and
- learning review with promote/revise/pause/retire states.

Exit gate:

- the case answers what was known, what was claimed, what James saw, what he decided, what
  happened, and what the system should change;
- replay is deterministic; and
- no alpha claim is made from one observation.

### Stage 6 — Portfolio scale and surface cutover

Only after the first complete learning episode:

- extend to a portfolio opportunity set;
- add robust correlation/factor/beta/liquidity constraints;
- make the production brief consume only admitted packet/monitoring views;
- retire duplicated legacy decision paths; and
- consider web/cockpit or cited conversational explanation over the same packet identity.

---

## 16. Reference vertical and programme definition of done

The target engine is proven only when one real James-visible, non-Model-A paper case completes:

```text
point-in-time evidence
  → validated opportunity
  → broker-report-quality thesis
  → independent challenge
  → portfolio-aware size range
  → immutable DecisionPacket
  → delivered brief
  → James disposition
  → benchmarked paper outcome
  → process and financial attribution
  → research/thesis learning decision
```

Tests, migrations, schemas, agents, prompts, commits, successful jobs, and delivered emails are
necessary evidence. None alone proves the engine.

---

## 17. Reliability, security, and operational requirements

### 17.1 Idempotency and replay

- Every asset materialisation is keyed by logical partition and version.
- Every governed materialiser has an idempotency key and atomic transaction.
- Retries create no duplicate canonical objects.
- Every decision can be rebuilt from exact source and code versions.
- Corrections append; they do not delete or rewrite observed history.

### 17.2 Delivery

- Alerts and packets use a transactional outbox.
- Send failure remains retryable and visible.
- Delivery success is observed from the provider, not inferred from job success.
- Dead-letter state requires explicit resolution.

### 17.3 Deployment identity

- Every production run records code SHA, configuration digest, schema version, data cutoff, and
  scheduler owner.
- There is one scheduler owner per production job.
- CI success is not production execution proof.

### 17.4 Backup and restore

- Operational Postgres and object storage have separate backup policies.
- Restore is tested into an isolated environment.
- A migration requiring destructive contract changes is blocked without current restore proof.

### 17.5 Secrets and permissions

- Analyst/agent paths are read-only by default.
- Canonical writes occur only through governed services.
- Source, delivery, and database credentials are least-privilege and independently rotatable.
- No broker credential or order tool is mounted.

---

## 18. Trade-offs and rejected alternatives

| Decision | Benefit | Cost / risk | Revisit trigger |
|---|---|---|---|
| Modular monolith | Low operational burden; clear in-process contracts | Requires disciplined module boundaries | Multiple teams, independent scaling, or deployment isolation becomes real |
| Object storage + Postgres | Durable raw lineage plus strong operational state | Two stores and restore procedures | Never remove; provider may change |
| DuckDB + Parquet | Low-cost analytical power at current scale | Limited concurrent service workload | Sustained concurrency/volume/latency exceeds measured budget |
| Dagster-style asset orchestration | Partitions, backfills, lineage, checks | New service and operating knowledge | Retain interfaces even if initial runner is transitional |
| Human execution | Preserves control and reduces regulatory/operational blast radius | No automated fills or reconciliation | Only revisit through a separate legal, security, and execution programme |
| LLMs as workers | Strong extraction and synthesis without making them truth | Nondeterminism and provider drift | Always retain typed contracts, evidence, and deterministic gates |

Rejected for the current horizon:

- a full rewrite before proving one vertical;
- agent-native orchestration;
- Postgres-only raw and analytical storage;
- a new monolithic “AI allocator”;
- prompt-based financial policy;
- microservices/Kubernetes/Kafka;
- a graph or vector database without a measured need;
- real-time trading infrastructure; and
- autonomous brokerage execution.

---

## 19. Decisions reserved for James

Before Stage 1 implementation, James must decide or explicitly delegate:

1. **North-star ratification:** adopt, amend, or reject the proposed research-to-decision reframe.
2. **Benchmark:** exact total-return benchmark and policy for global/non-ASX exposure.
3. **Investment horizon:** primary decision and evaluation horizons.
4. **Risk mandate:** acceptable drawdown/risk-budget framing and which measures are hard
   constraints versus reporting.
5. **First positive-control case:** ordinary ASX equity selected for the paper vertical.
6. **Scheduler target:** Dagster now, or a contract-compatible single-Render transitional owner.
7. **Object-store provider:** choose a provider after cost, region, access, backup, and portability
   review.
8. **Paused build:** approve extraction/rework under the target contracts or retire the branch.
9. **Canonical landing:** identify which existing product/architecture documents this proposal
   amends or supersedes after ratification.

No implementation agent may invent these decisions.

---

## 20. Instructions for Claude/Arbi on receipt

On receiving this document, Claude/Arbi should:

1. treat it as a proposed architecture, not implementation authority;
2. verify current `main`, live operational state, open PRs, and paused-worktree state;
3. challenge the architecture from finance, data, reliability, and product perspectives;
4. reconcile it with the current north star, convergence proposal, future-state work, research
   architecture, and authority model;
5. produce one current-to-target reuse/gap matrix;
6. identify the smallest contract pack required for Stage 0;
7. propose exactly one bounded first work order and its acceptance gates;
8. stop at a James decision packet; and
9. avoid creating another competing roadmap, applying migration 0042, mutating production,
   implementing the whole architecture, or treating document completion as engine completion.

The first useful response is a **challenge and ratification packet**, not code.

---

## 21. Local source material

- [`docs/product/north-star.md`](north-star.md)
- [`docs/product/portfolio-policy.md`](portfolio-policy.md)
- [`docs/product/recommendation-schema.md`](recommendation-schema.md)
- [`docs/product/portfolio-outcome-ledger.md`](portfolio-outcome-ledger.md)
- [`docs/research/operating-model-architecture.md`](../research/operating-model-architecture.md)
- [`docs/proposals/governance-first-architecture-2026-06-30.md`](../proposals/governance-first-architecture-2026-06-30.md)
- `docs/proposals/arbi-outcome-programme-convergence-sprint-2026-08-08.md` — **superseded by this
  document and never committed** (untracked working copy only); deliberately not linked
- [`migrations/0027_research_store.sql`](../../migrations/0027_research_store.sql)
- [`migrations/0033_governance_schema_core.sql`](../../migrations/0033_governance_schema_core.sql)
- [`asxos/domain/theses/schemas.py`](../../asxos/domain/theses/schemas.py)
- [`asxos/domain/theses/service.py`](../../asxos/domain/theses/service.py)
- [`asxos/domain/portfolio/paper_trade.py`](../../asxos/domain/portfolio/paper_trade.py)

## 22. External references

- [ASX — capitalisation and accumulation indices](https://www.asx.com.au/investors/learn-about-our-investment-solutions/indices/types/capitalisation-indices)
- [S&P Dow Jones Indices — S&P/ASX 200](https://www.spglobal.com/spdji/en/indices/equity/sp-asx-200/)
- [Bailey et al. — The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253)
- [Dagster — partitioned assets and backfills](https://op-graph-docs.dagster.dagster-docs.io/concepts/partitions-schedules-sensors/partitions)
- [Dagster — asset checks](https://master.dagster.dagster-docs.io/concepts/assets/asset-checks)
- [DuckDB — reading and writing Parquet](https://duckdb.org/docs/stable/data/parquet/overview)
- [GitHub — scheduled workflow behaviour](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Render — cron jobs](https://render.com/docs/cronjobs)
- [Supabase — database backups](https://supabase.com/docs/guides/platform/backups)

---

## 23. Final position

The most valuable parts of ASXOS are not wasted. They are downstream assets waiting for a better
upstream spine.

The architectural correction is:

```text
FROM:
data jobs → rules/agents → brief

TO:
point-in-time evidence
  → governed research
  → validated opportunity/theme
  → thesis and independent challenge
  → portfolio-aware capital assessment
  → immutable decision truth
  → brief and James disposition
  → benchmarked outcome and learning
```

Build the brain and learning loop through the existing shell. Do not discard the shell, and do
not let the shell continue to define the brain.

---

# Appendices — Stage 0 ratification packet

Prepared 2026-08-10. Every row was verified against live repository state, live Supabase state
(`mcp__supabase-ro`), or live GitHub Actions run history on that date. Claims that could not be
verified are marked **UNVERIFIED** rather than asserted.

---

## Appendix A — Current-to-target reuse/gap matrix

The purpose of this matrix is to convert "build an investment engine" into a bounded list of what is
genuinely missing. Row counts are live as at 2026-08-10.

| Target contract (§12) | State today | Verdict |
|---|---|---|
| `SourceObject` | No raw landing. Provider payloads are parsed and discarded. `prices` is still destructively upserted (`asxos/ingestion/prices.py:53-59`), but since migration 0043 (applied 2026-08-12) the `prices_revision_capture` trigger captures the prior row into `price_revisions` — **triggers verified live 2026-08-18, `price_revisions` = 0 rows, no backfill.** Raw provider payload retention is still absent | **BUILD — Stage 1 first** (E6/E7) |
| `MarketFact` (point-in-time) | `rs_fundamentals_pit.knowledge_date` is the **only** true bitemporal column in the database. Breadth is fixed: **63 rows / 11 symbols** at 2026-08-10 → **53,689 rows at 2026-08-18** (verified live), and `derive_fundamentals_pit` succeeded on the full chain in run `32099973966`. **But the column's meaning is not yet trustworthy — see the note below.** | **FIX + EXTEND** |
| `FeatureSnapshot` | `rs_factor_scores` 54 rows / 11 symbols; 9 of 11 carry `composite_score = 0.000`. Retired in `weekly-research.yml:16-18` as "degenerate output, no production reader" | **REBUILD** after PIT breadth |
| `ResearchHypothesis` / `ResearchRun` | Absent. `jobs/eval_alpha_factors.py` is a read-only evaluator, not a registry | **BUILD** (Stage 2) |
| `StrategyVersion` | `model_versions` (1 row) + the `approved_for_allocation` gate (`asxos/domain/models/production_gate.py`) | **ADAPT** — generalise beyond ML |
| `ThemeVersion` | `themes` 1 row · `theme_holdings` 1 row. Governance triggers exist (migrations 0035/0036) | **POPULATE + VERSION** |
| `CandidateSnapshot` | Evaluator built (`asxos/domain/screening/`); `screening_rules` **0** rows, `screening_runs` **0** rows — never used | **WIRE + RUN** |
| `EvidencePacket` | `agent_evidence` 40 rows with verified/inferred/speculative tiering; `thesis_evidence` **0** rows. Prototype adds content hash, `knowledge_cutoff` gate and expiry | **RECONCILE** (Appendix B) |
| `ThesisVersion` | `theses` 13 · `thesis_revisions` 13 · `report_sections` JSONB (migration 0040) · audit triggers. Prototype adds bull/base/bear scenarios, falsifiers and ABSTAIN | **STRONGEST REUSE + RECONCILE** |
| `ChallengeResult` | Absent from production. Prototype enforces author-independence and forbids `pass` with a blocking finding | **PROTOTYPED — disposition required** |
| `PortfolioAssessment` | `policy_check` / `risk_framing` specced in `recommendation-schema.md`; allocator dormant under rule #11. Prototype adds `SizeRange`, loss budget and constraint gating | **PROTOTYPED — disposition required** |
| `DecisionPacket` | `recommendation-schema.md` is spec-only (`recommendation_id` appears in **0** lines of `asxos/`, `jobs/`, `migrations/`). `decisions` table holds **1** free-text row with **zero** foreign keys in either direction. Prototype is a full aggregate with hashing and `supersedes_packet_id` | **DESIGNATE CANONICAL** (Appendix B) |
| `DeliveryReceipt` | `brief_runs` 46 rows. `asxos/domain/brief/composer.py:142-143` swallows all persistence exceptions (`except Exception: pass`) — violates CLAUDE.md #10 | **ADAPT** + transactional outbox |
| `Disposition` | Markdown only. Two rows, both `_pending James_` since 2026-07-11 | **BUILD — must be ~one keystroke** (E3) |
| `OutcomeObservation` | `signal_outcomes` 60,072 rows (ML lineage, **no** thesis FK). `macro_thesis_outcomes` 3 rows **with** a real FK to `macro_theses` — the one correct existing shape | **GENERALISE** the `macro_thesis_outcomes` pattern |
| `LearningReview` | Markdown ledger only | **BUILD** as process audit |

**A.0 note — `knowledge_date` can be in the future, which undermines Stage 1's replay gate**
(found and verified live 2026-08-18; new, not previously recorded anywhere).

**60 rows of `rs_fundamentals_pit`, across 60 distinct symbols, carry a `knowledge_date` of
2026-09-13 — a date that has not happened.** (Query: `knowledge_date > CURRENT_DATE`; min and
max are both 2026-09-13; all 60 sit at `as_of` 2026-06-30. Total table size 53,689 rows.)

**Mechanism.** `rs_financial_statements` has **no `knowledge_date` column** — its columns are
`symbol, period_end, period_type, statement_type, filing_date, report_date, currency, …`
(verified against `information_schema`). The derive step therefore falls back to the vendor's
`report_date`, and `report_date` is a *scheduled* announcement date: 10 rows in
`rs_financial_statements` already carry a `report_date` in the future, out to 2026-08-27. A
scheduled date is a forecast, not a knowledge event.

**Why it matters, and why it is not urgent.** It is **harmless to today's readers**: every PIT
consumer filters `knowledge_date <= as_of`, so a future date simply hides the row. It is
**not** harmless to Stage 1, whose replay/lineage exit gate depends on `known_at <= cutoff`
meaning "we actually knew this by then". If `knowledge_date` can be a vendor's diary entry,
that predicate is decorative, and a replay can be declared clean while resting on facts nobody
held at cutoff — the same class of defect as E7's "replay guarantee over evidence that was
never retained", arriving through the timestamp rather than through retention. Stage 1 must
either source a real `knowledge_date` (filing/receipt time) or record `report_date`-derived
rows as an explicitly lower-confidence tier; it must not silently keep both under one column.

### A.1 — What is already strong, and should not be rebuilt

The raw evidence base is real, ASX-scale and survivorship-free. This materially reduces Stage 1:

| Asset | Rows | Note |
|---|---|---|
| `rs_financial_statements` | 694,015 | 3,359 distinct symbols |
| `prices` | 740,350 (2026-08-10); **754,230 at 2026-08-18**, latest `dt` 2026-08-17 | still destructively upserted, now behind the 0043 capture trigger — see E6. **Two live caveats:** `price_revisions` = 0 rows and no pre-2026-08-12 backfill exists, and `adj_close` is frozen at first ingest so splits never propagate backwards (35 symbols carry a >5× one-day step; `adj_close = close` on 2,318 of 2,319 rows at the latest date). Verified 2026-08-18 |
| `rs_corporate_actions` | 42,501 | dividends incl. AU franking, splits |
| `rs_security_master` | 4,415 | survivorship-free (active + delisted) |

Also reusable: the governance trigger set (0033–0036), the shared transition helper
`asxos/domain/governance/transitions.py::apply_governance_transition`, the Decimal-exact tax and
portfolio kernels, and the CLI/email delivery shell.

### A.2 — The gap the matrix does not show

The engine has never run at breadth: `holding_lots` **1** · `decisions` **1** · `themes` **1** ·
`theme_holdings` **1** · `thesis_evidence` **0** · `screening_runs` **0** · `paper_portfolio_nav`
**0**. The V2 brief is built, tested and dark (`ASXOS_V2_BRIEF_ENABLED` is set nowhere, so
`composer.py:95-98` falls back to V1). Architecture is not the binding constraint on any of these.

---

## Appendix B — Decision-contract reconciliation (three sources → one canonical)

Per E2. The three definitions are at **different altitudes** and must not be merged naively:
`recommendation-schema.md` is a *human memo/view* contract; `types.py` is a *canonical cross-domain
aggregate*; §8.5 is a *logical sketch* of the latter.

### B.1 — Field-level mapping

| Field | `recommendation-schema.md` | §8.5 | `types.py` prototype | Disposition |
|---|---|---|---|---|
| identity | `recommendation_id` | `decision_packet_id` | `decision_packet_id` | prototype |
| schema version | — | `schema_version` | `schema_version` | prototype |
| as-of date | `date` | `as_of` | `as_of` | prototype |
| knowledge cutoff | — | `knowledge_cutoff` | `knowledge_cutoff` (validated `< expires_at`) | prototype |
| expiry | — | `expires_at` | `expires_at` | prototype |
| portfolio snapshot | — | `portfolio_snapshot_id` | `portfolio_snapshot_id` | prototype |
| evidence identity | `evidence[]` (inline, tiered) | `evidence_packet_id` | `evidence_packet_id` + separate `EvidencePacket` | prototype; memo renders the inline view |
| thesis identity | — (prose `rationale`) | `thesis_version_id` | `thesis_version_id` | prototype |
| challenge identity | — | `challenge_result_id` | `challenge_result_id` | prototype |
| portfolio assessment | `policy_check`, `risk_framing` | `portfolio_assessment_id` | `portfolio_assessment_id` + `PortfolioAssessment` | prototype; memo fields become render views |
| benchmark | — | `benchmark_id` | `benchmark_id` | prototype |
| state / verdict | `verdict`: GOOD HOLD·TRIM·ADD·REVIEW·EXIT-CANDIDATE | `recommendation_state` | `RecommendationState`: initiate·watch·avoid·add·trim·exit_review·abstain | **CONFLICT — see B.2** |
| sizing | `sizing` (point value) | `size_range` | `SizeRange(min,max)` + zero-on-abstain rule | **CONFLICT — prototype wins** |
| staging | — | `staging_framework` | `staging_framework` | prototype |
| scenarios | — | `scenario_summary` | `scenario_summary` + `Scenario` triple summing to 100 | prototype |
| risk | `risk_framing` | `risk_summary` | `risk_summary` | prototype |
| constraints | `policy_check` | `constraints_checked` | `constraints_checked` + `ConstraintResult` with gating | prototype |
| uncertainty | `confidence` (+ falsifier) | `missing_or_uncertain_inputs` | `missing_or_uncertain_inputs` + gate blocking capital states | prototype; falsifier moves to `ThesisVersion.falsifiers` |
| decision ask | `decision_ask` | `decision_ask` | `decision_ask` | all three agree |
| model manifest | — | `model_and_prompt_manifest` | `model_and_prompt_manifest` | prototype |
| content hash | — | `content_hash` | `content_hash` (SHA-256 validated) | prototype |
| revision identity | — | (supersession described in prose) | `supersedes_packet_id` | prototype |
| tax | `tax_implications` | (via constraints) | **ABSENT** | **GAP — must be added** |
| **rule #11 assertion** | `model_independence` | (prose only) | **ABSENT** | **GAP — must be added** |
| standing disclaimer | `not_this` | — | — | render-layer concern; keep in memo view |
| outcome | `outcome` (filled later) | — | — | belongs to `OutcomeObservation`, not the packet |
| **trading calendar** | — | — | `trading_calendar: TradingSessionCalendar`, required (`types.py:449`; contract `:163-195`) | **RATIFIED 2026-08-12 (#87)** — F3's horizons are trading-day counts, so the calendar is part of the contract, not an implementation detail |
| **upstream artifact hashes** | — | — | `upstream_hashes: UpstreamArtifactHashes` — five mandatory lowercase SHA-256 digests (`:428-441`; field at `:457`) | **RATIFIED 2026-08-12 (#87)** — closes I.2 finding 4 (hashes previously validated format, not content) |
| **expiry reason** | — | — | `expiry_reason` (`:451`) with the strictly-earlier-than-default validator (`:504-507`) | **RATIFIED 2026-08-12 (#87)** — an event-driven expiry may only *shorten* the F3 default, never extend it |
| **manifest components** | — | `model_and_prompt_manifest` | mandatory `{composition, llm, market_data, code_contract}` plus an adversarial regex rejecting `model a` / `v1_5` (`:56-62`, `:521-528`) | **RATIFIED 2026-08-12 (#87)** — rule #11 enforced mechanically in the manifest, not by prose |
| **universal constraints** | `policy_check` | (F4 prose) | `UNIVERSAL_CONSTRAINTS` — the five F4 hard gates, with `model_a_quarantine` required present, **blocking**, and **passing exactly once** (`:45-53`, `:631-646`) | **RATIFIED 2026-08-12 (#87)** — F4's non-deferrable gates become a validator |
| **cross-artifact gating** | — | — | `DecisionCase` validators (`:616-671`) | **RATIFIED 2026-08-12 (#87)** — blocking/revise challenge forces abstain; portfolio and decision state/size must agree; `constraints_checked` reconciles exactly; shared `as_of`/cutoff and created-at chain order |

**The six rows above were added by PR #87 (commit `7aa8507`) and ratified into this table on
2026-08-12.** They are requirements the merged contract enforces *beyond* what Appendix B
originally specified, recorded here so this appendix remains the complete statement of which
fields are mandatory. Per **B.4**, adding or removing a field row here — or a row in a ruled
semantic table — is a governor amendment; tightening a validator is not.

### B.2 — Designated canonical, and *when* it becomes canonical

**Governor ruling (2026-08-10, Appendix F decision 8): the `types.py` contract *design* is selected
as the target implementation contract**, subject to the mandatory amendments in B.3.

**Timing is load-bearing and must not be overstated:**

| Stage | What is canonical |
|---|---|
| **At ratification (2026-08-10)** — *superseded 2026-08-12; retained as the dated record* | **Appendix B is the canonical *logical* contract.** `asxos/domain/decision_engine/types.py` is **preserved only on the draft PR #81 branch and is not on `main`** — it is the selected design, not a canonical artifact. |
| **On merge of a later reviewed prototype/adoption PR** | `types.py` (as amended per B.3) becomes the **executable canonical contract**. |
| **Now (from 2026-08-12)** | ✅ **That merge condition is MET.** The reviewed engine merged to `main` at commit **`7aa8507`** (PR #87), so `asxos/domain/decision_engine/types.py` **is** the executable canonical contract. Appendix B remains authoritative for artifact inventory, mandatory fields and the ruled semantic tables — see the **B.4 boundary clause**. |

~~**Do not describe `types.py` as already canonical on `main`.** It is not on `main`. Until the
adoption PR merges, any implementation question resolves against Appendix B, not against the
branch-only prototype.~~ **SUPERSEDED 2026-08-12 by commit `7aa8507` (PR #87)** — retained rather
than deleted, because it was correct from ratification until that merge. `types.py` **is** on
`main` and **is** the executable canonical contract; implementation questions now resolve through
the **B.4** boundary clause below, which states which source governs which kind of question.

Rationale for selecting the design: it is the only one of the three that is executable, tested, and
enforces its own invariants — content hashing, the `known_at <= knowledge_cutoff` gate,
author-independence of the challenge, zero-size-on-abstain, and a full identity-chain validator
rejecting any claim citing evidence outside the frozen packet.

Consequent dispositions:
- `docs/product/recommendation-schema.md` → **ADAPTED** to the human memo/render view *derived from*
  a `DecisionPacket`. It is not a rival contract and must carry a header saying so.
- §8.5 of this document → **SUPERSEDED** by Appendix B as the field-level source of truth.
- **No fourth definition may be created.**

### B.3 — Mandatory amendments before the design can carry a real decision

Governor-directed (Appendix F decision 8). These are contract changes, not code changes; **no code
belongs in this PR.**

1. **Replace symbol-as-identity with a canonical `security_id`** drawn from the security master
   (`rs_security_master`, 4,415 rows). Retain `symbol` and `exchange` as **display attributes
   only**. This also closes the live defect that `ThesisVersion.symbol`'s `^[A-Z0-9]+\.(AU|US)$`
   pattern cannot express `HUBS.NYSE` or `AXJO.INDX` — ticker text is an alias, not identity (§6.3).
2. **Separate two concerns currently conflated in one enum.** The prototype's
   `quality: verified | inferred | synthetic` mixes evidential strength with data provenance. Split
   into:
   - `evidence_tier: verified | inferred | speculative` — matches `recommendation-schema.md` and the
     live `agent_evidence` tiering;
   - `data_mode: real | synthetic` — so a synthetic demo case can never be mistaken for real
     evidence.
3. **Add explicit `model_independence`** (the rule #11 assertion). A memo without it is VOID under
   `portfolio-policy.md` while the quarantine stands.
4. **Add a typed tax-assessment reference** — a structured reference to a tax assessment artifact,
   **not free-form tax prose**.
5. **Define the exact mapping** from `DecisionPacket.recommendation_state` to the human memo
   `verdict`, so no surface can invent a third vocabulary:

   | `recommendation_state` | memo `verdict` |
   |---|---|
   | `initiate` | ADD (new position) |
   | `add` | ADD |
   | `trim` | TRIM |
   | `exit_review` | EXIT-CANDIDATE |
   | `watch` | REVIEW |
   | `avoid` | REVIEW (with a do-not-act note) |
   | `abstain` | REVIEW (not decision-ready) |
   | *(no state)* | GOOD HOLD — the absence of a live packet on a held position |

   `GOOD HOLD` deliberately has no `recommendation_state`: it is the steady state, not a decision.

### B.4 — Boundary clause: which source governs which question (James, 2026-08-12)

**Governor ruling, 2026-08-12 — option (c), the hybrid.** Appendix B is not demoted to history by
the adoption merge, and `types.py` is not merely an implementation of it. The two are authoritative
over *different questions*:

1. **B.2's merge condition is MET** as of commit **`7aa8507`** (PR #87), so
   `asxos/domain/decision_engine/types.py` **is** the executable canonical contract.
2. **Appendix B remains authoritative for:** which artifacts exist; which fields are mandatory; and
   the ruled semantic tables — B.3's state→verdict map, F3's evaluation horizons and expiry
   defaults, F4's five universal gates, and the **no-fourth-definition** rule.
3. **`types.py` is authoritative for:** validator strictness, the hashing scheme, temporal
   enforcement, and internal structure.
4. **Amendment rule:** adding or removing a **field**, or a **row in a ruled table**, is a
   **governor amendment** to this appendix. **Tightening a validator is not.** PR #87 did both —
   its added fields are ratified into B.1 above by this same 2026-08-12 ruling, and any future
   field or ruled-row change needs a fresh one.

Where the two ever conflict inside the other's domain, the owner above wins and the loser is a
defect to be fixed — not a fourth definition to be tolerated.

**This clause resolves the source-of-truth question only. It authorises no implementation**; every
stage still requires its own approved work order (§15), and the merged engine remains read-only and
synthetic.

### B.5 — Pre-approved amendment (James, 2026-08-12): `DecisionBrief` real-data mode

`DecisionBrief` pins `mode: Literal["synthetic_prototype"]` (`types.py:686`) and its validator
rejects any case whose evidence is not synthetic (`:700-701`). That is correct for the adopted
read-only engine, and it is the reason the merged contract cannot silently render real evidence.

**James has PRE-APPROVED widening `mode` to admit a real-data brief** — recorded here so the change
does not need a second governor decision when it is built. Conditions:

- **It is implemented inside the queued ASX results-review mission**, where it has a real consumer
  and tests — not as an isolated contract edit. A widened `mode` with no consumer is an
  unexercised capital-path surface.
- **The synthetic/real non-mixing invariant must be preserved.** A brief may be all-synthetic or
  all-real; one brief must never mix the two, and a synthetic case must never become renderable as
  real evidence. The current validator's *intent* survives the widening — only its single-mode
  literal is lifted.
- B.4 still applies: this is a **field-domain change**, so it is a governor amendment —
  pre-approved here for this one change, not delegated in general.

### B.6 — Ruled clarification (James, 2026-08-13): review states and memo verdicts are different altitudes

**The question.** Mission P1-04 made every portfolio/thesis **review surface** emit one of four
review states — `CLEAR` / `ATTENTION` / `BLOCKED` / `EVIDENCE_THIN`
(`asxos/domain/review/status.py`). B.3 rules the state→verdict map
(`GOOD HOLD` / `ADD` / `TRIM` / `EXIT-CANDIDATE` / `REVIEW`) and B.2 closes with
**"No fourth definition may be created."** Both P1-04 and P2-01 flagged the apparent collision and
asked for a governor ruling before either vocabulary was changed to accommodate the other.

**The ruling: they are different ALTITUDES, not rivals.** Review surfaces emit the four review
states. **B.3's map is untouched and remains the decision engine's.**

| | Decision states / memo verdicts | Review states |
|---|---|---|
| **Question answered** | "What should James consider doing about this position?" | "Can we say anything reliable about this position right now?" |
| **Vocabulary** | `RecommendationState` → `MemoVerdict` (B.3) | `CLEAR` · `ATTENTION` · `BLOCKED` · `EVIDENCE_THIN` |
| **Definition site** | `asxos/domain/decision_engine/types.py:85-99` (`memo_verdict_for()`) | `asxos/domain/review/status.py` (`ReviewStatus`, `classify()`) |
| **Producer** | the decision engine's memo path — synthetic-only behind the `DecisionBrief` lock (`types.py:686`, `:700-701`) | review surfaces: `/pm-review`, the five investment-analysis agents, the brief's review header and thesis cards |
| **Describes** | an action under consideration | the state of the **evidence** |

**Neither vocabulary maps onto the other, and no conversion function between them may be written.**
There is no `review_status_for(state)` and no `memo_verdict_for(review_status)`. An `ATTENTION` is
not a weak `TRIM`; a `CLEAR` is not a `GOOD HOLD`. Anything that pairs them mechanically re-creates
the collision this clause resolves, and is a defect under B.4's "the owner wins and the loser is a
defect" rule.

**Reasoning of record:**

1. **B.3 answers an action question.** `memo_verdict_for()` (`types.py:85-99`) maps a canonical
   **decision state** to a **human-memo verdict**. It belongs to the decision engine's memo path
   and is reachable today only through a brief that pins `mode: "synthetic_prototype"` and rejects
   any non-synthetic evidence (`types.py:686`, `:700-701`).
2. **The four review states answer an evidence question.** They describe whether the inputs were
   present, fresh and sufficient — not what to do about the answer.
3. **This ENFORCES an existing rule rather than creating one.** Packet P1's required-work item 4
   already rules that review surfaces emit the four states, *"not a synthetic buy/add/trim/exit
   signal"*. B.6 records that ruling in the appendix that governs the vocabulary question; it
   introduces no new obligation.
4. **It is the safer side of the s766B personal-advice firewall.** A review surface emitting
   `TRIM` is materially closer to an instruction than one emitting `ATTENTION`. The five
   investment-analysis agents are chartered as evidence-only, never orders
   (`.claude/rules/portfolio-conventions.md`, "Regulatory firewall").
5. **No fourth definition of the DECISION CONTRACT is created.** B.2's ban is on rival definitions
   of the decision contract. A review-state vocabulary is a *different concept* with a different
   producer and a different consumer, so it is not a rival definition — and the two are kept
   separate precisely so neither drifts into the other.

**ADDITIVE — nothing is superseded.** B.3's table and `memo_verdict_for()` are **unchanged**.
Nothing in `types.py` changes. `RecommendationState`, `MemoVerdict` and the eight-row map keep
exactly the meanings ratified on 2026-08-10 and reaffirmed on 2026-08-12. This clause adds a
boundary statement; it removes and rewrites nothing.

**Amendment status under B.4.** This adds no field and changes no row of a ruled table, so it is
not a B.4 field-domain amendment. It is a governor clarification of scope, recorded here because
B.2's no-fourth-definition rule is the sentence that made the question ambiguous.

---

## Appendix C — Measurement contract

Per James's ruling: **after-tax, cash-flow-adjusted, benchmark-relative**. Per E4, tax is measured,
not asserted. Five quantities, computed and reported separately — never collapsed into one score.

| Quantity | Purpose |
|---|---|
| **After-cost portfolio TWR** | selection/process skill, neutral to contribution timing |
| **After-tax portfolio TWR** | skill net of the tax consequences of the decisions taken |
| **Money-weighted return / IRR** | the actual wealth outcome, which contribution timing does affect |
| **Benchmark-relative result** | excess vs the declared benchmark |
| **Tax / franking / FX bridge** | the reconciliation that explains the gap between the above |

**Conventions that must be fixed before any number is computed** (a figure without these is not
comparable to anything):
- external-flow timing — start- or end-of-day, and the sub-period breaking rule on contribution days;
- valuation cutoff — which close, in which timezone;
- realised vs unrealised tax treatment;
- franking-credit treatment — gross-up basis and refundability assumption;
- **whether the benchmark is compared pre-tax or under a stated tax assumption** — the comparison is
  meaningless until this is fixed, and it is Appendix F decision 1;
- FX convention for non-AUD holdings, per the `cost_base_normal` AUD-base rule in
  `.claude/rules/portfolio-conventions.md`.

**Known data constraint (blocking).** `portfolio-policy.md:26` declares an "XJO **total-return**"
benchmark. The repository benchmarks `AXJO.INDX` (`asxos/domain/portfolio/monitor_loader.py:34`),
which is EODHD's **price** index — it excludes reinvested dividends. **The declared benchmark is not
computable as written.** Options are in Appendix F decision 1. Until resolved, no benchmark-relative
figure may be published under a "total return" label.

Report the four §2.2 outcome dimensions (investment outcome · capital protection · decision process ·
system integrity) separately. Raw P&L must not become the sole reward signal.

---

## Appendix D — Scheduler ownership: decision request and per-job manifest

Per E-none/governor point 4: this appendix **requests a decision and records evidence**. It does not
authorise execution, and it does not adopt jobs into GitHub Actions — §11.2 reserves the
Dagster-vs-single-Render-transitional-owner choice for James, and moving production scheduling into
GitHub would contradict §11.2's "GitHub is CI/release, not production scheduling."

### D.1 — Verified live evidence (2026-08-10)

`job_runs` alone cannot establish scheduler ownership. This was cross-referenced against
`.github/workflows/*` `schedule:` blocks and actual `gh run list` history.

**Scheduled workflow health — 3 of 5 are failing:**

| Workflow | Cron (UTC) | Last scheduled run | Result |
|---|---|---|---|
| `daily-brief.yml` | `30 20 * * 0-4` | 2026-08-09 | success |
| `weekly-research.yml` | `0 16 * * 6` | 2026-08-08 | **failure** |
| `pipeline-health.yml` | `0 22 * * *` | 2026-08-09 | **failure** |
| `backup.yml` | `30 13 * * *` | 2026-08-09 | **failure** |
| `us-positions.yml` | `30 13 * * 1-5` | none yet | first eligible run 2026-08-10 13:30 UTC |

**D.1.a — `backup.yml` has never succeeded.** Two runs, two failures (2026-08-08, 2026-08-09). It
fails in an `apt-get` step: `packages.microsoft.com` returns 403 and the repo is "no longer signed",
exit code 100 — `scripts/backup_irreplaceable.sh` is never reached. **The irreplaceable-data backup
(themes, theses, thesis_revisions, theme_holdings, macro_theses) has been non-functional since the
Render exit.** At discovery this compounded with 4,869 lines of local-only Track B work; that
preservation risk is now mitigated by draft PR #80, while the backup failure itself remains open.

**D.1.b — `derive_fundamentals_pit` has failed 4 consecutive weekly runs** (2026-07-18, 07-25,
08-01, 08-08; `TimeoutError`). Last success 2026-07-11 — 30 days. `check_cron_health` has correctly
reported it daily since 2026-07-31 and is itself in `failure` as a result. This is why the PIT base
is 11 symbols.

**D.1.c — `us-positions` has not failed.** Its workflow is `active`; its first eligible scheduled run
is 2026-08-10 13:30 UTC. The real finding is a **bounded coverage gap**: `check_us_positions` last
ran 2026-08-05 under Render, so 2026-08-06 and 08-07 (Thu/Fri) had no US position check. This is the
alert protecting the single live holding. Separately, `30 13 * * 1-5` is **09:30 ET — US market
open, not close**; the workflow header describing it as "after NYSE close" is wrong and the check
will run against a stale prior close.

> **Update 2026-08-12 (this appendix stays a dated 08-10 evidence record; correction noted, not
> rewritten):** the schedule fix is in a branch diff on `claude/ops-housekeeping-0812` —
> `us-positions.yml` moves to `30 21 * * 1-5` (17:30 ET under EST, 16:30 ET under EDT, after the
> 16:00 ET close on both sides of the DST boundary) with the header corrected. `render.yaml:654`
> still declares `30 13 * * 1-5`; that copy belongs to D.1.d's orphaned-Render set. Live status is
> tracked at `roadmap-state.md` defect #5.

**D.1.d — 9 jobs are orphaned.** Declared in `render.yaml`, absent from every workflow, and stopped
executing. `render.yaml` was last touched 2026-07-21 — before the Render exit — and its header still
claims to be "the source of truth for what Render runs."

**UNVERIFIED:** whether the Render services are suspended or deleted. `$RENDER_API_KEY` is not in the
shell environment, so the live service list could not be read. The inference that Render stopped
executing rests on `job_runs` recency, not on the Render API. James may need to supply the key.

### D.2 — Per-job disposition manifest (proposed; execution requires a separate work order)

| Job | Last run | Proposed disposition | Basis |
|---|---|---|---|
| `retrain_model_a` | 2026-06-06 (failure) | **RETIRE** | ML shelved; rule #11 |
| `generate_signals` | 2026-08-05 | **RETIRE** | rule #11 — no capital consumer |
| `compute_factor_scores` | 2026-08-01 | **RETIRE** | degenerate 0.000 output; already declared retired in `weekly-research.yml:16-18` |
| `check_model_staleness` | 2026-08-05 | **RETIRE** | monitors a shelved engine |
| `build_portfolio` | 2026-08-01 (`blocked`) | **RETIRE for now** | allocator dormant — gate returns 0 approved models by design |
| `compute_opportunity_cost` | 2026-08-01 | **DECIDE** | brief consumer exists, but ranking path is rule #11-adjacent |
| `track_signal_outcomes` | 2026-08-02 | **DECIDE** | ML lineage, but it is the only maturation harness; Stage 5 may want the pattern |
| `detect_theme_stages` | 2026-08-05 | **ADOPT** | moat layer 3 (theme stewardship); model-independent |
| `eval_alpha_factors` | never scheduled | **DEFER to Stage 2** | belongs to the research registry |

**Decision requested:** Appendix F decision 5 (scheduler target). Until it is answered,
`render.yaml`'s "source of truth" header is factually wrong and should be corrected or the file
retired — that correction is itself part of the later work order, not Stage 0.

---

## Appendix E — Prototype disposition

A tested research-to-decision prototype is preserved on the draft PR #81 branch. It is not on
`main`, is not adopted, and is not in production.

> **SUPERSEDED 2026-08-12 by commit `7aa8507` (PR #87).** The paragraph above is retained as the
> record of the position from 2026-08-10 until the adoption merge; it is no longer true. PR #87 is
> the "separately reviewed PR" that F7 below requires: the reviewed engine was adopted from the
> preserved #81 snapshot onto a fresh branch from `main` and merged, so
> `asxos/domain/decision_engine/types.py` **is on `main`, is adopted, and is the executable
> canonical contract** (B.2/B.4). PR #81 itself was closed as superseded on 2026-08-11 with its
> branch `claude/decision-engine-prototype` @ `c6ff3c3` retained
> (`docs/session-handoff-2026-08-11.md:119`). What has **not** changed: the adopted engine remains
> **read-only and synthetic** — no real-data path, no capital path (see B.5).

| Path | Content |
|---|---|
| `asxos/domain/decision_engine/types.py` | the contracts (Appendix B) |
| `asxos/domain/decision_engine/demo.py` | positive + negative control cases |
| `asxos/domain/decision_engine/renderer.py` | HTML render |
| `asxos/prototype/app.py` | read-only cockpit (`make decision-demo`, port 8790) |
| `asxos/brief/templates/decision_engine_prototype.html.j2` | HTML surface |
| `tests/test_decision_engine_prototype.py` | **7 tests, all passing** (verified 2026-08-10, `.venv` Python 3.12.11) |
| `Makefile` | modified — adds the `decision-demo` target (the only tracked file altered) |

**Verified behaviour of the preserved fixtures.** Unknown-field-rejecting, shallow-frozen Pydantic
contracts; float input rejected recursively so capital values stay Decimal-exact; `EvidencePacket`
rejects any item with
`known_at > knowledge_cutoff` (a real point-in-time gate) and requires `expires_at > knowledge_cutoff`;
`ChallengeResult` rejects a non-independent author and forbids `pass` alongside a blocking finding;
`PortfolioAssessment` forces a failed constraint into `avoid`/`abstain`/`exit_review` and zero size;
`DecisionPacket` blocks capital-deployment states while `missing_or_uncertain_inputs` is non-empty;
`DecisionCase.validate_identity_chain` rejects any thesis or challenge citing evidence outside the
frozen packet. Two controls run end-to-end: a synthetic `initiate` with a size range, and an
`abstain` with a zero size range forced by unresolved tradeability and concentration.

These checks do **not** establish deep immutability or complete capital safety. The independent
review found ten adoption blockers, including mutable nested manifest data, format-only hashes,
`revise`/unknown-constraint gate bypasses, incomplete temporal coherence, and visually actionable
expired packets. The complete record is Appendix I.2 and PR #81.

**Governor ruling F7: AMEND AND ADOPT.** PR #81 completes only the preservation half. Adoption as
the canonical executable contract requires every Appendix B.3 and I.2 blocker to close in a
separately reviewed PR. Its evidence is synthetic and it has no database or agent binding —
adoption is of the corrected contracts, not of the demo data.

**Handling constraint:** evolve this selected design through the later adoption PR; do not create a
parallel fourth contract definition. PR #81 remains preservation-only and is not the branch on
which to conceal or silently resolve its disclosed findings.

**Preservation record:** Appendix I and PR #81.

---

## Appendix F — Governor rulings (James, 2026-08-10)

All eight are **RULED**. One carries a named blocker (F4). These are architecture and contract
decisions; **none of them authorises implementation.** Each names the work order that must precede
any action.

### F1 — Benchmark: **RULED**

The canonical AUD benchmark is the **official S&P/ASX 200 Accumulation Index (XJOAI)**.

- `AXJO.INDX` may remain **price-context only** and **must never carry a total-return label**.
- **If licensed history is not yet available, report benchmark measurement as `unavailable`.** Do
  **not** silently substitute a proxy. An honest gap outranks a plausible wrong number.
- Data acquisition (licence, provider, backfill) is a **later approved work order**.

### F2 — Global / non-ASX exposure: **RULED**

Use a **separately reported global sleeve** initially. Do **not** blend HUBS or any future global
holding into the ASX benchmark. Revisit a blended policy benchmark only when global exposure becomes
a deliberate, material allocation.

### F3 — Evaluation windows and packet expiry: **RULED**

Observe outcomes at **21, 63 and 126 trading days**.

Default `DecisionPacket.expires_at`:

| `recommendation_state` | Default expiry |
|---|---|
| `initiate` · `add` · `trim` · `exit_review` | **5 trading days** |
| `watch` · `avoid` · `abstain` | **21 trading days** |

**All states expire earlier** on any of: a material event, stale evidence, a constraint change, or a
portfolio-snapshot change.

> These are **contract defaults, not trading instructions.** Expiry governs how long a decision
> artifact remains admissible, not when to transact.

### F4 — Risk mandate: **DEFERRED, with a named blocker**

> **Blocker: "James must complete the capital/risk calibration before Stage 4."**

James-specific numeric loss and drawdown limits are deferred. Until the calibrated mandate exists,
these **hard universal gates** apply and are not deferrable:

1. **No leverage** by default.
2. **No Model A capital input** (CLAUDE.md rule #11).
3. **No action with unresolved tradeability or ownership** (e.g. ESS locks).
4. **No action on stale or missing decision-critical evidence.**
5. **No broker execution** — the personal-advice firewall is unchanged.

Volatility, beta, correlation and drawdown remain **reporting-only** until the calibrated mandate
says otherwise.

**Stage 1 evidence work is explicitly NOT blocked by this deferral.**

### F5 — Scheduler: **RULED**

**Dagster** is the target orchestration owner for the evidence/research asset graph.

- Existing schedules may remain **only as explicitly time-bounded safety coverage** until cutover.
- **No new GitHub production schedules.**
- Stage 1 must deliver the **deployment, cost and cutover work order** *before* Dagster is installed
  or deployed.

This supersedes §11.2's open choice and confirms §11.2's position that GitHub is CI/release, not
production scheduling. The Appendix D.2 manifest executes under that later work order.

### F6 — Object store: **RULED**

**AWS S3, `ap-southeast-2`**, with: versioning · **Object Lock in governance mode** · encryption ·
least-privilege credentials · lifecycle policy · **a separately observed restore test**.

**No bucket or credential creation is authorised by this Stage 0 PR.**

This closes E7: immutable raw storage is adopted, not deferred, so the Stage 1 replay/lineage exit
gate stands as written.

### F7 — Prototype: **RULED — AMEND AND ADOPT**

Preserve it separately (see Appendix I) and **close the B.3 conformance gaps before any real-data
use**. Preservation is not adoption or merge authority.

### F8 — Canonical decision contract: **RULED — the `types.py` design**

Selected, subject to the five mandatory amendments in **B.3** (canonical `security_id`;
`evidence_tier` split from `data_mode`; explicit `model_independence`; typed tax-assessment
reference; the explicit state→verdict mapping).

Per **B.2**, Appendix B remains the canonical **logical** contract until a reviewed
prototype/adoption PR merges; `types.py` becomes the executable canonical contract **only on that
merge**. **No code changes belong in this PR.**

---

## Appendix G — Stage 0 exit gate: status

| # | Gate | Status |
|---|---|---|
| 1 | James approves one exact PR commit SHA/digest | ✅ **MET** — James approved digest `d6d888a` on 2026-08-10 and merged it as `9ede7ad` (PR #79). This document became canonical on that merge |
| 2 | Single canonical target architecture; competitors superseded or uncommitted | ✅ **MET** — this document; the three backlogs carry NOT-A-QUEUE banners; the convergence sprint and live-slice brief are superseded and never committed |
| 3 | `roadmap-state.md` is the single live queue, mapped to Stages 0–6 | ✅ **MET** |
| 4 | The eight Appendix F decisions answered, or deferred with a named blocker | ✅ **MET** — seven ruled; **F4 deferred with the named blocker** *"James must complete the capital/risk calibration before Stage 4"* |
| 5 | Authority-file amendments applied | ✅ **MET** — James authorised the exact Appendix H text on 2026-08-10; it landed in PR #79 to `portfolio-policy.md`, `docs/README.md`, and `north-star.md`. The arbi deny rules remain intact and arbi did not self-grant authority |
| 6 | Parked work preserved, not lost | ✅ **MET** — both branches are now live in remote draft PRs: `claude/rules-integrity-build` @ `3f6fd51` (PR #80, PARKED / DO NOT MERGE) and `claude/decision-engine-prototype` @ `c6ff3c3` (PR #81, PROTOTYPE / DO NOT MERGE, all ten findings disclosed). Both are labelled and draft; neither is authorised for merge. Nothing in this preservation scope now lives only on one laptop |
| 7 | No implementation has occurred | ✅ **MET** — `REQUIRED_MIGRATIONS` still 95, applied migrations still end at 0041, PR #79 was documentation-only, migration 0042 unapplied |

**Stage 0 is COMPLETE** (2026-08-10). All seven gates are met; this document is canonical on `main`.

**Completion is not implementation authority.** Stage 0 ratified an objective, a set of contracts and
a queue — nothing more. Each subsequent stage requires its own approved work order, and per F1, F5
and F6 three of the ruled decisions each explicitly name a *later* work order before any action
(benchmark data acquisition; Dagster deployment/cost/cutover; S3 bucket and credential creation).
Stage 1 has **not** been authorised by the completion of Stage 0.

**Known-blocked at Stage 4:** the F4 capital/risk calibration. Stage 1 is not blocked by it.

## Appendix H — Amendments to guard-protected authority files

**Status: APPLIED IN THIS PR under explicit governor authorisation (2026-08-10); final digest
approval remains pending.**

James explicitly authorised these three amendments. Arbi's self-protection remained intact:
`.claude/settings.json` carries hard `permissions.deny` entries preventing arbi from writing them
or lifting its own boundary:

```
line 56   "Edit(/docs/README.md)"
line 57   "Edit(/docs/product/north-star.md)"
line 72   "Edit(/docs/product/portfolio-policy.md)"
line 45   "Edit(/.claude/settings.json)"      ← so arbi cannot lift its own boundary
```

That last line is the point: the deny list is self-protecting by design, and arbi routing around it —
via a different tool matcher, a shell heredoc, or any other technicality — would be exactly the
self-granting of authority the control exists to prevent. **Arbi did not attempt a workaround.**
The already-authorised text was applied in a separate governor-directed editing session; no deny
rule was removed or weakened.

Files arbi *did* amend, because they are arbi-owned and not on the deny list: `roadmap-state.md`
("arbi reads and refreshes this"), `arbi-operating-backlog.md`, `cleanup-backlog.md`,
`next-session-backlog.md`.

The applied text below is retained as the ratification record and reflects the **final governor
rulings** (Appendix F), not the earlier draft.

### H.1 — `docs/product/portfolio-policy.md`

**(a)** Under **Objectives**, **replace** the `Benchmark` and `Return / drawdown targets` bullets
with:

```markdown
- **Benchmark (amended 2026-08-10, governor ruling F1):** the canonical AUD benchmark is the
  **official S&P/ASX 200 Accumulation Index (XJOAI)**, measured after tax and costs. Alpha is the
  point; matching the index is failure of the thesis, not success of the tool.
  - `AXJO.INDX` (`asxos/domain/portfolio/monitor_loader.py:34`) is EODHD's **price** index. It may
    remain **price-context only** and **must never carry a total-return label**.
  - **If licensed XJOAI history is not available, report benchmark measurement as `unavailable`.**
    Do **not** silently substitute a proxy. Data acquisition is a later approved work order.
- **Global exposure (F2):** report a **separate global sleeve**. Do not blend HUBS or any future
  global holding into the ASX benchmark until global exposure is a deliberate, material allocation.
- **Return / drawdown targets:** **DEFERRED (governor ruling F4, 2026-08-10)** with a named blocker:
  **"James must complete the capital/risk calibration before Stage 4."** arbi does not assume a
  number. Until the calibrated mandate exists, volatility, beta, correlation and drawdown are
  **reporting-only**, and these hard universal gates apply and are not deferrable: no leverage by
  default · no Model A capital input (rule #11) · no action on unresolved tradeability or ownership ·
  no action on stale or missing decision-critical evidence · no broker execution.
  Stage 1 evidence work is **not** blocked by this deferral.
```

**(b)** Insert a new section after **Objectives**:

```markdown
## Measurement contract (amended 2026-08-10 — `target-architecture.md` Appendix C)

Governor ruling: performance is measured **after tax, cash-flow-adjusted, benchmark-relative**.
Five quantities, computed and reported **separately** — never collapsed into a single score:

1. **after-cost portfolio TWR** — selection/process skill, neutral to contribution timing
2. **after-tax portfolio TWR** — skill net of the tax consequences of the decisions taken
3. **money-weighted return / IRR** — the actual wealth outcome
4. **benchmark-relative result**
5. **tax / franking / FX bridge** — the reconciliation explaining the gap between the above

A figure is not comparable to anything until these conventions are fixed: external-flow timing
(start/end-of-day + the sub-period breaking rule), valuation cutoff and timezone, realised vs
unrealised tax treatment, franking gross-up basis and refundability, FX convention for non-AUD
lots, and **whether the benchmark is compared pre-tax or under a stated tax assumption**.

**Tax framing (governor correction, 2026-08-10).** Tax is **not guaranteed alpha**. It is a
quantifiable implementation advantage and a decision constraint **whose benefit must be measured,
not asserted**. Plain return vs index is invalid under irregular contributions — that is why TWR
and MWR are reported separately rather than as one number.
```

### H.2 — `docs/README.md`

**(a)** In **Read first, in order**, insert as new item 3 and renumber:

```markdown
3. `product/target-architecture.md` — **the ratified target (2026-08-10).** asxos is a
   research-to-capital-decision-to-learning engine; the brief is an experience layer over an
   immutable decision. Read its Errata §0 and Appendix F (the eight decisions reserved for James)
   before proposing work
```
and amend the `roadmap-state.md` line to read "**the single live queue** (Stages 0→6)".

**(b)** Replace the **Risk** row (currently "none built (v1 is risk-blind by design)"), which reads
as a contradiction against `portfolio-policy.md`'s declared constraint table:

```markdown
| Risk | **Policy** exists (`product/portfolio-policy.md` — sector cap, position count, CGT rules,
and the accepted v1 co-movement blindness); **no enforcement engine is built** beyond the
allocator's constraint waterfall (`../.claude/rules/portfolio-conventions.md`). The numeric risk
*mandate* is **DEFERRED** — blocker: "James must complete the capital/risk calibration before
Stage 4" (`product/target-architecture.md` F4). Until then vol/beta/correlation/drawdown are
**reporting-only**, under five non-deferrable universal gates. Design notes:
`model-a-audit-and-extension-plan-2026-07-04.md` Part C |
```

**(c)** Amend the **Product vision / program state** row to name
`product/target-architecture.md` as the ratified target and `product/roadmap-state.md` as the single
live queue.

**(d)** Amend the **Backlog / session state** row: `next-session-backlog.md` is now
**reference-only**; the single queue is `product/roadmap-state.md`.

### H.3 — `docs/product/north-star.md`

The charter still centres the morning brief ("a morning briefing and trade-framework…"). The
ratified output is the decision-and-learning engine. Proposed insert after "The Output":

```markdown
## The reframe (ratified 2026-08-10)

The output is **better investment decisions and outcomes**, benchmark-relative and risk-controlled —
not a brief, and not feature count. The brief remains the experience layer over an immutable
decision and must carry no financial logic of its own. The canonical target is
`target-architecture.md`; the three-layer moat below is *how* the engine earns its edge, not a
substitute for it.

This does not relax any non-negotiable: rule #11 (Model A quarantine) stands, the personal-advice
firewall is unchanged, and Decimal-only domain arithmetic is unchanged.
```

### H.4 — Housekeeping (not authority-protected, deferred to the remediation work order)

- `docs/product/session-handoff-2026-07-17.md` is **misfiled** — it lives in `product/`, so the
  `docs/session-handoff-*.md` glob that `CLAUDE.md` and `README.md` instruct sessions to use will
  never find it. Move to `docs/`.
- `render.yaml`'s header still claims to be "the source of truth for what Render runs" while 9 of
  its crons no longer execute. Correct or retire it — Appendix D.2, after decision 5.

---

## Appendix I — Preservation record

Preservation is **not adoption and not merge authority**. Both branches below are draft, marked DO
NOT MERGE, and exist so that tested work stops living on a single laptop.

| Branch | Commit | Status |
|---|---|---|
| `claude/rules-integrity-build` | `3f6fd51` | ✅ **PRESERVED** — PR #80, **PARKED / DO NOT MERGE**; review loop incomplete (security-engineer, refactoring-expert, technical-writer never completed); red-team findings attached; **migration 0042 unaltered and unapplied** |
| `claude/decision-engine-prototype` | `c6ff3c3` | ✅ **PRESERVED** — PR #81, **PROTOTYPE / DO NOT MERGE**; review complete with **CHANGES REQUIRED**; all ten findings disclosed (I.2); nine paths, 1,279 insertions, snapshot exactly as reviewed |

Both are draft and labelled. Neither may be merged, and migration 0042 may not be applied, without a
separate governor decision.

### I.1 — Prototype preservation record

The independent review loop completed 2026-08-10 on staged-diff key `570be24bb3b1`. Checks passed:
7 focused tests · ruff · mypy · `git diff --cached --check` · staged scope confirmed as exactly the
nine intended paths.

**Consolidated verdict: CHANGES REQUIRED for adoption or merge; ACCEPTABLE TO PRESERVE as a draft
PROTOTYPE / DO NOT MERGE PR provided every finding is disclosed.** The review authorises no real
data, production use, adoption, merge, or Stage 1 work.

The snapshot was preserved **exactly as reviewed** — no fixes implemented, because implementing them
would have invalidated the review key. The key was re-verified byte-identical at commit time.

**Process note, recorded because the distinction is easy to lose.** The preservation commit was
initially blocked, and the blocker was **not** the review gate. `.claude/hooks/review-gate.sh`
defines its marker as recording that "the subagent review loop **has run** for that exact staged
diff" (header, lines 4–7), states it "cannot itself spawn an agent or prove one ran," has **no
concept of a verdict**, and names exactly one dishonesty — writing the marker without running the
loop. A "changes required" verdict is therefore fully compatible with it. The actual blocker was the
Claude Code auto-mode classifier, a separate harness-level control that refused the marker write
regardless of review status. **No workaround was attempted**, and no false or verdict-laundering
marker was ever written or described; the governor wrote the marker after the loop completed.

### I.2 — Adoption blockers (disclosed on PR #81)

Ten findings, **all CLOSED as of commit `7aa8507` (PR #87)** — the architect verified each against
the merged code on 2026-08-12. **These are adoption blockers, not preservation blockers.**

> **Read the list below as the PR #81 disclosure record, not as the state of `main`.** It is
> preserved verbatim (it was accurate on 2026-08-10) and deliberately not rewritten. The
> requirements that closed it are folded into **B.1** above and governed by **B.4**; finding 10's
> five B.3 amendments are likewise closed by the same merge.

1. A **blocking/revise challenge can still accompany `initiate`**.
2. An **unknown constraint can still permit capital deployment**.
3. `constraints_checked` is **not reconciled** to `PortfolioAssessment`.
4. Hashes validate **format, not content integrity** — the decision hash does not commit to upstream
   artifact contents.
5. `frozen=True` is **shallow**: `model_and_prompt_manifest` is mutable.
6. Cross-artifact `as_of` / cutoff / expiry / `created_at` / `observed_at` and **timezone invariants
   are incomplete**.
7. **Expired packets remain visually actionable.**
8. **Stage 0 F3 expiry defaults are not implemented.**
9. Renderer states **do not implement the ruled state→verdict mapping**.
10. **All five B.3 amendments remain open** — `security_id`, `evidence_tier`/`data_mode`,
    `model_independence`, typed tax reference, state→verdict mapping.

Findings 1, 2 and 7 are the capital-safety ones: each would let an artifact that should have been
stopped appear actionable.

