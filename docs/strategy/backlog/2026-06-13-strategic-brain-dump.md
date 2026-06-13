# ASXOS Strategic Investigation Backlog

> **Status:** Parked / Not approved for implementation
> **Owner:** James
> **Date:** 2026-06-13
> **Context:** Captured during production recovery
> **Purpose:** Preserve strategic questions and future architecture ideas
> without allowing them to distract from the current recovery
> **Execution rule:** Do not execute anything in this document until the
> production recovery gate (below) is met.

---

## Production recovery gate

**Do not action any item in this backlog until the minimal daily loop is
demonstrably healthy.** Concretely, do not execute this backlog until ALL of
the following hold:

- Phase 2A is deployed and verified in Render.
- `generate_signals` succeeds after the Phase 2A deploy.
- `ingest_sentiment` succeeds after the Phase 2A deploy.
- `compose_brief` runs with honest freshness/regime display (no fabricated
  "neutral" regime when no signal row exists).
- backup is verified externally through `asxos-backups`, Render logs, or
  Healthchecks.io.
- risky crons such as `retrain_model_a` and `track_signal_outcomes` are
  paused/quarantined or explicitly approved.
- stale signals are cleared.
- Render cron/env architecture is stable enough that the system is not
  failing because of stale per-service secrets.
- the minimal daily loop is green for a defined observation window
  (suggested 7–14 days).

Until every line above is true, this document is reference material only.

---

## 1. Why This Exists

This file captures high-value strategic questions that surfaced during the
ASXOS production-recovery discussion. It exists so those ideas are not lost,
and equally so they do not silently become immediate scope creep.

- These are important ideas, but they are **not** immediate work.
- Current recovery must finish first.
- Strategy should be investigated deliberately, **one topic at a time**.
- The goal is to evolve ASXOS into a *trusted* personal investment
  intelligence OS — not to accumulate more fragile crons, half-trained
  models, or aspirational documents.

A parked backlog is valuable because it prevents good ideas from being
forgotten. It is dangerous if it is read as an approved plan. Treat it as
the former.

---

## 2. Current Recovery Priority

The single priority is making this loop trustworthy:

```
prices -> validate/freshness -> snapshot -> generate_signals -> ingest_sentiment -> compose_brief -> backup
```

Everything else is secondary until this loop is reliable, observable, and
honest about its own data freshness.

### Do-not-distract-recovery note

While recovery is in progress, do **not**:

- begin V2 expansion;
- add new signal families;
- perform a broad Render cron rollout;
- run migration recovery unless explicitly approved;
- retrain ML models until reliability is restored;
- adopt the parallel engine;
- perform a broad env-group rollout except as part of controlled Render
  recovery;
- run autonomous remediation;
- make production mutations driven by review events.

---

## 3. Strategic Themes

Captured concisely but with enough detail to resume each later.

### 3.1 Render Cron Architecture

**Questions**

- Should ASXOS keep many independent Render crons?
- Should it move to one master daily orchestrator?
- Should it use a hybrid model: orchestrator for the daily loop, backup
  separate?
- Should it use a DB queue worker?
- Should some jobs stay as independent crons?
- Should Render be treated as the long-term execution host?
- Should cron definitions be dashboard-managed first and encoded into
  `render.yaml` later?
- Should environment groups become the standard for shared secrets?

**Options to compare**

- many independent crons
- one master daily orchestrator
- hybrid orchestrator + separate backup
- DB queue worker
- always-on background worker
- event-driven review queue
- manual operator-triggered jobs

**What breaks first in each**

- stale service-level `DATABASE_URL`
- schedule collisions
- missing env vars
- build succeeds but run fails
- jobs skipped without a `job_runs` row
- downstream jobs running after an upstream failure
- drift between `render.yaml` and live Render
- poor observability
- no single health view
- single point of failure in the orchestrator
- lack of durable artifacts from the ephemeral cron filesystem

**Likely future direction**

- *Short term:* stabilise the existing minimal crons.
- *Medium term:* introduce a daily orchestrator in shadow mode (alongside,
  not replacing, working crons).
- *Long term:* consider replacing most daily crons with a master
  orchestrator or queue worker once proven.

### 3.2 Shared Environment Group Strategy

**Questions**

- Should ASXOS use a shared Render Environment Group?
- Should `DATABASE_URL` live in a group?
- How do we avoid stale per-service overrides?
- Which services should receive the group first?
- Which secrets must remain service-local?

**Likely policy**

- Create `asxos-prod-shared` only as part of controlled Render recovery.
- Start with `DATABASE_URL` only.
- Link one canary minimal-loop service first.
- Remove stale service-level `DATABASE_URL` overrides — service-level
  variables override env-group values on Render.
- Roll out to minimal-loop services only.
- Do not link dormant/peripheral crons just to silence failures.
- Keep backup tokens, healthcheck URLs, brief/portfolio gates, FRED keys,
  V2 flags, and feature-specific toggles service-local unless explicitly
  approved.

**Minimal-loop services (likely first candidates)**

- `asxos-sync-prices`
- `asxos-validate-price-data`
- `asxos-snapshot-portfolio`
- `asxos-generate-signals`
- `asxos-ingest-sentiment`
- `asxos-compose-brief`
- `asxos-backup-irreplaceable`

**Do-not-link-yet candidates**

- `asxos-retrain-model-a`
- `asxos-track-signal-outcomes`
- FRED / market-context jobs
- regulatory jobs
- V2 / parallel-engine jobs
- dormant/peripheral crons

### 3.3 Master Orchestrator vs Multiple Crons

This is the first major architecture investigation to run later.

**Questions**

- What would a master orchestrator own?
- What would remain separate?
- What is the contract between steps?
- How are retries handled?
- What happens when a step fails?
- Does the orchestrator stop, or continue degraded?
- How is freshness checked?
- How does it prevent stale/fabricated briefs?
- How are job statuses written?
- How do we avoid one giant opaque script?

**Possible orchestrator contract**

```
daily_orchestrator:
  1. acquire run lock
  2. determine trading day / data date
  3. sync prices
  4. validate price freshness
  5. snapshot portfolio
  6. generate signals
  7. ingest sentiment
  8. compose brief ONLY if freshness rules pass, or display clear degradation
  9. trigger/verify backup, or record external backup state
 10. write step-level job_runs
 11. create review events for failures
 12. exit with a clear status
```

**Important:** introduce an orchestrator in **shadow mode** first. Do not
immediately delete working crons.

### 3.4 Event-Driven Review Automation

The idea is automatic *review creation*, not automatic remediation.

**Questions**

- Can ASXOS create review tasks when important events happen?
- Can Claude/Opus reviews be triggered safely?
- What should require human approval?
- Can reviews become a structured product workflow?

**Events that should create reviews**

- job failed N times
- cron missed a scheduled run
- signals stale over threshold
- prices stale over threshold
- backup missing
- backup failed
- model drift detected
- retrain failed or OOM
- data-quality flag created
- feature distribution drift
- signal IC decay
- portfolio drawdown
- position concentration breach
- tax conflict
- thesis contradiction
- large price move
- earnings / regulatory event
- new signal verdict
- manual override
- stale thesis
- unusual cost / slippage
- missing brief section
- drift between docs and code

**Possible tables / objects**

- `ops_events`
- `review_queue`
- `review_decisions`
- `review_artifacts`
- `review_prompts`
- `review_outcomes`

**Automation boundary**

- events may create review items automatically;
- agents may draft review reports or PRs;
- human approval is required before any production mutation;
- no autonomous DB writes or Render mutations from review events until a
  governance model exists.

### 3.5 Quant Research Architecture

**Core questions**

- What is each signal predicting?
- What is the label?
- What is the horizon?
- Are features point-in-time?
- Are prices adjusted correctly?
- Are dividends handled correctly?
- Is the universe survivorship-safe?
- Is raw close used only for tradeability/liquidity?
- What baseline does the signal beat?
- Are costs included?
- Is there enough sample?
- Does it work out-of-sample?
- Does it work across regimes?
- Does it survive sector/size/liquidity neutralization?
- Does it survive transaction costs and turnover?
- Does it improve portfolio outcomes, or only prediction metrics?

**Research stack components to investigate**

- signal registry
- hypothesis docs
- adjusted price policy
- point-in-time universe
- baseline momentum
- rank IC
- quintile spreads
- turnover
- costs
- capacity
- walk-forward validation
- purging / embargo where relevant
- clustered confidence intervals
- multiple-testing controls
- shadow paper book
- promotion gates
- kill criteria
- verdict files
- monthly review

**Evidence required before a signal can influence**

- the brief display
- a watchlist
- a paper portfolio
- a live decision
- an actual trade recommendation

### 3.6 ML and Model Construction

**Questions**

- Are models ranking, classifying, or predicting expected returns?
- What are the labels?
- What are the horizons?
- What is the training universe?
- Are features leakage-safe?
- Is target leakage possible?
- Is publication lag handled?
- Are fundamentals point-in-time?
- Is adjusted-return construction correct?
- How is calibration measured?
- How is drift detected?
- How is retraining triggered?
- What is the baseline?
- When is ML justified?
- When should simple rules win?
- How do we avoid regime overfitting?
- How do we explain model decisions?
- How do we quarantine failed models?

**Possible model lifecycle**

```
RESEARCH -> BACKTEST -> SHADOW -> LIVE -> PROBATION -> RETIRED
```

**ML design principles**

- start with simple rank baselines;
- validate labels before models;
- require walk-forward evidence;
- require calibration / stability checks;
- require feature drift monitoring;
- require a shadow period before influence;
- do not retrain while the daily loop is unstable;
- do not let ML outputs fabricate certainty in the brief.

### 3.7 Portfolio and Risk Architecture

**Questions**

- How should signals become decisions?
- What is the minimum viable decision ledger?
- How should the tax overlay interact with signals?
- How should CGT holding-period constraints affect sell decisions?
- How should liquidity affect sizing?
- How should sector/size/style exposures be monitored?
- What is the risk budget?
- What triggers a portfolio review?
- What is the difference between signal, thesis, alert, recommendation, and
  trade?
- How should ASXOS avoid advice-like outputs unless gates are enabled?
- How is attribution measured?

**Components to investigate**

- decision ledger
- paper book
- position monitor
- tax overlay
- thesis integration
- risk exposures
- portfolio constraints
- drawdown response
- execution assumptions
- tradeability filters
- attribution
- manual override log

### 3.8 Top 1% Hedge Fund Principles, Lean Version

**The question:** What would a top 1% systematic hedge fund do differently,
translated into a solo-user ASXOS platform?

**Principles to translate**

- truthful data before models
- point-in-time discipline
- adjusted returns correctly constructed
- no survivorship bias
- reproducible research runs
- strong baselines
- cost-aware backtests
- portfolio-aware signal evaluation
- shadow portfolios
- attribution
- risk controls
- execution / capacity awareness
- daily monitoring
- incident response
- kill criteria
- model governance
- no production changes without evidence
- automated review creation, not automated unsafe remediation

**Lean equivalent**

- one reliable daily loop
- one canonical data policy
- one research harness
- one signal lifecycle
- one decision ledger
- one paper book
- one review queue
- one monthly attribution report
- one clear operator dashboard
- strict do-not-trust labels for stale/missing data

### 3.9 Scale Scenarios

Scale tests to investigate later.

**Scenarios**

- ASX only
- ASX + US
- 2,000 symbols
- 10,000 symbols
- daily bars only
- fundamentals + news + events
- one signal
- ten signals
- ML ensemble
- shadow portfolio
- tax-aware live decision ledger
- 12 months of operations
- multiple portfolios
- higher-frequency updates
- more data vendors
- broader event ingestion

**For each scenario, later investigate**

- what breaks first
- database bottleneck
- job bottleneck
- API limit bottleneck
- feature-generation bottleneck
- model-training bottleneck
- observability gap
- cost increase
- governance gap
- regulatory risk
- migration path

### 3.10 Product Roadmap Tracks

Roadmap tracks — all **parked**.

**Track A — Reliability**
- Render env group
- minimal loop green
- cron health
- backup observability
- `job_runs` completeness
- orchestrator decision
- event queue

**Track B — Data Truth**
- adjusted price semantics
- dividend policy
- point-in-time universe
- data-quality flags
- stale price handling
- corporate actions
- delisted / inactive symbols
- ASX + US data support

**Track C — Quant Research**
- baseline momentum
- research harness
- signal registry
- verdict files
- walk-forward validation
- cost model
- shadow paper book
- promotion gates

**Track D — ML and Models**
- label audit
- feature audit
- model lifecycle
- drift monitoring
- retrain governance
- calibration
- simple-baseline-first policy

**Track E — Portfolio and Risk**
- decision ledger
- tax overlay
- risk exposures
- position sizing
- thesis integration
- attribution
- execution / cost monitoring

**Track F — Automation and Review**
- `ops_events`
- `review_queue`
- automatic review generation
- Claude / Opus prompt generation
- manual approvals
- incident workflow

**Track G — US Expansion**
- US data ingestion
- FX / currency handling
- US tax distinction, if relevant
- US fundamentals / events
- universe handling
- schedule / timezone handling

---

## 4. Scenario Backlog

All items are **Parked**.

| ID | Topic | Why it matters | Priority | When to revisit | Likely first prompt | Risks if done too early |
|---|---|---|---|---|---|---|
| STRAT-001 | Master orchestrator vs multiple crons | Determines the whole execution model; affects reliability and observability | High | After recovery gate met | "Compare cron vs orchestrator vs queue worker for a solo operator" | Premature rewrite of working crons; new single point of failure |
| STRAT-002 | Render environment group and cron architecture | Stale per-service secrets are a live failure mode | High | During controlled Render recovery | "Design `asxos-prod-shared` rollout with a canary" | Broad rollout linking dormant crons; masking real failures |
| STRAT-003 | DB queue worker vs Render cron | Alternative execution model with better retry semantics | Medium | After STRAT-001 | "Design a DB-backed job queue for ASXOS" | Building infra before the loop is trusted |
| STRAT-004 | Event-driven review queue | Turns failures into structured, reviewable work | Medium | After recovery gate met | "Design `ops_events` + `review_queue`" | Automation mutating prod without governance |
| STRAT-005 | Backup observability and `job_runs` integration | Backup currently has no `job_runs` visibility | High | During recovery | "Make backup write `job_runs` / verify externally" | Treating unverified backups as safe |
| STRAT-006 | Quant research harness | Foundation for trustworthy signals | High | After loop green 7–14 days | "Design the ASXOS research harness" | Research on untrustworthy data |
| STRAT-007 | ML lifecycle and retrain governance | Retrain currently OOMs and is unverified | Medium | After reliability restored | "Design model lifecycle + retrain governance" | Retraining on an unstable loop |
| STRAT-008 | Point-in-time data and adjusted-return semantics | Silent correctness risk in every downstream metric | High | Before any serious research | "Audit adjusted-return + point-in-time policy" | Backtests that look good but leak |
| STRAT-009 | Portfolio decision ledger | Bridges signals to decisions | Medium | After signals trusted | "Design minimum viable decision ledger" | Advice-like outputs without gates |
| STRAT-010 | Tax-aware portfolio decisions | CGT hold-period conflicts with sell logic | Medium | After STRAT-009 | "Design tax overlay / CGT conflict handling" | Misapplied tax logic on real positions |
| STRAT-011 | Top 1% hedge fund principles, lean version | Keeps ambition disciplined and lean | Medium | Ongoing reference | "Translate top-fund discipline to lean ASXOS" | Cargo-culting heavy infra |
| STRAT-012 | ASX + US scaling stress test | Defines scale limits and migration path | Low | After 12 months ASX-only | "Stress-test ASX + US scale scenarios" | Premature multi-market complexity |
| STRAT-013 | Fabrication-proof brief architecture | Brief must never imply false certainty | High | During recovery | "Design honest freshness/degradation in the brief" | Trusting fabricated regime/freshness |
| STRAT-014 | Signal promotion gates and shadow book | Stops unproven signals influencing decisions | High | After STRAT-006 | "Design promotion gates + shadow paper book" | Live influence from unvalidated signals |
| STRAT-015 | Cron failure and stale-secret scenario testing | Reproduces the failure that triggered recovery | High | During recovery | "Enumerate cron/stale-secret failure modes + tests" | Believing the system is robust untested |
| STRAT-016 | Review automation boundaries | Defines what automation may and may not do | High | Before any review automation | "Define automation vs human-approval boundary" | Autonomous prod mutation |
| STRAT-017 | Risk/attribution dashboard | Single operator health + performance view | Medium | After decision ledger | "Design operator risk/attribution dashboard" | Dashboard over untrusted data |
| STRAT-018 | Regulatory/advice firewall review | s766B / Westpac boundary; personal-use gates | High | Before any outward-facing output | "Review advice firewall + personal-use gates" | Surfacing personal-advice outputs |

---

## 5. Do-Not-Execute-Yet List

Do not execute any of the following until the recovery gate is met:

- build a master orchestrator
- delete / recreate all crons
- broad Render env-group rollout
- broad Render blueprint sync
- enable dormant / peripheral crons
- run `track_signal_outcomes`
- restart `retrain_model_a`
- add new signal families
- adopt the V2 / parallel engine
- run broad migration recovery
- train / retrain ML models
- alter thresholds
- alter tax logic
- automate production changes from events
- let review automation mutate DB / Render / Git without human approval
- expand to US equities
- create live / paper trading automation without governance

---

## 6. Revisit Triggers

Come back to this backlog when:

- the minimal loop has been green for 7–14 days;
- `generate_signals` and `ingest_sentiment` succeed post-Phase-2A;
- the brief displays honest freshness/regime state;
- backup is verified;
- the Render env/cron architecture is stabilized;
- stale signals are cleared;
- risky crons are quarantined;
- there are no unexplained missed crons for a defined window;
- the operator has capacity for strategy work;
- and always: before starting any V2 / ML / new-signal work.

---

## 7. First Investigation to Run Later

**Recommended first strategic investigation:**

> "Should ASXOS converge toward a master daily orchestrator, and what should
> that orchestrator's contract be?"

**Why this one first:**

- It affects Render architecture.
- It affects env management.
- It affects job health and observability.
- It affects brief honesty.
- It affects review automation.
- It affects future ML runs.
- It affects scaling to ASX + US.

It is the hinge decision that several other tracks depend on.

---

## 8. Future Opus Prompts

Ready-to-use prompts for later. None are approved to run now.

### Prompt 1 — Master Orchestrator Review

```text
Compare these execution models for ASXOS (solo-operator personal investment
intelligence OS, Python 3.12 + FastAPI + Supabase, running on Render):

  - many independent Render crons
  - one master daily orchestrator
  - a DB queue worker
  - a hybrid model (orchestrator for daily loop, backup separate)
  - an event-driven review queue

For each, analyse:
  - failure modes
  - observability
  - retry semantics
  - cost
  - scale
  - migration path

Then give a single recommendation for a solo operator, with a staged
migration path that does not delete working crons before the replacement is
proven in shadow mode.
```

### Prompt 2 — Quant Research Architecture Review

```text
Design the ASXOS quant research harness. Specify:
  - labels and how they are constructed
  - horizons
  - adjusted-return construction (dividends, splits)
  - point-in-time data discipline
  - universe definition (survivorship-safe)
  - baselines (e.g. momentum)
  - rank IC and quintile-spread evaluation
  - walk-forward validation (with purging/embargo where relevant)
  - transaction-cost model
  - a shadow paper book
  - promotion gates and kill criteria

State the evidence a signal must produce before it may influence the brief,
a watchlist, a paper portfolio, or a live recommendation.
```

### Prompt 3 — ML Model Lifecycle Review

```text
Review the ASXOS ML approach. Address:
  - labels and whether they are well-posed
  - target leakage
  - feature leakage and publication lag
  - model type (ranking vs classification vs expected-return)
  - calibration measurement
  - drift detection
  - retraining cadence and triggers
  - explainability
  - when ML is justified vs when simple signals should win

Propose a model lifecycle (RESEARCH -> BACKTEST -> SHADOW -> LIVE ->
PROBATION -> RETIRED) with the gate criteria between each stage, and a rule
that prevents retraining while the daily loop is unstable.
```

### Prompt 4 — Event-Driven Review Automation

```text
Design an event-driven review system for ASXOS. Specify:
  - an ops_events table (schema + severity levels)
  - a review_queue table
  - review_decisions / review_artifacts
  - the triggers that create review items
  - the automation boundary: what may be automated vs what requires human
    approval
  - the Claude Code / Opus review workflow

Hard constraint: events and agents may CREATE reviews and DRAFT changes, but
no autonomous DB / Render / Git mutation is permitted until a governance
model with human approval exists. Make that boundary explicit in the design.
```

### Prompt 5 — Top 1% Hedge Fund Lean Translation

```text
For a top-tier systematic hedge fund, answer:
  - What would they refuse to trust?
  - What would they measure daily?
  - What would they automate?
  - What would they keep manual?

Then translate each answer into a lean, solo-operator ASXOS equivalent that
does not require a team or heavy infrastructure. Prefer one reliable
instance of each capability (one loop, one research harness, one decision
ledger, one review queue) over breadth.
```

### Prompt 6 — Portfolio Decision Ledger and Tax Overlay

```text
Design for ASXOS:
  - a minimum viable decision ledger
  - how tax-aware logic interacts with signals
  - CGT hold-period conflict handling (calendar arithmetic per spec, never
    day-count)
  - risk exposures and constraints
  - attribution
  - thesis integration
  - manual override handling

Keep the design within the existing single-user, no-auth, NUMERIC(18,6)
constraints, and respect the s766B / personal-use advice firewall.
```

---

## 9. Open Founder Decisions

Decisions James will need to make later:

- many crons vs orchestrator vs queue worker
- when to encode env groups in `render.yaml`
- whether backup should write `job_runs`
- whether to quarantine or delete peripheral crons
- whether to adopt or reject the parallel engine
- whether to revive or replace `track_signal_outcomes`
- when ML retraining can resume
- what evidence is required before a signal affects the brief
- what evidence is required before a signal affects a portfolio decision
- where review artifacts should live: DB, Git, issues, email, or all of these
- how much automation is acceptable before human approval

---

## 10. Final Note

This backlog is intentionally parked. It is valuable because it prevents
strategic ideas from being lost — but it is dangerous if treated as approved
implementation work. ASXOS should return to this only after the production
loop is trustworthy. Stabilise the daily loop first; investigate strategy
deliberately, one topic at a time, afterwards.
