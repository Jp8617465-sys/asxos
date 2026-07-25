# ASXOS investment engine — accepted decisions

**Status:** locked for implementation
**Decision date:** 2026-07-24
**Governor:** James
**Change rule:** a later explicit governor decision supersedes a row; delivery
work may clarify mechanics but may not silently weaken a locked boundary.

## Decision register

### DEC-001 — Tailored output, manual execution

**Decision:** Build for James only. The system may produce direct tailored
analysis, a concrete portfolio proposal, deterministic sizing, and an exact
order set in lifecycle state `ORDER_STAGED`. James manually places every trade.

**Hard boundary:** no broker tool, credential, API, session, order submission,
modification, cancellation, routing, or execution automation.

**Implementation consequence:** S01 must reconcile this target with the current
repository's narrower decision-support wording before the new output mode is
enabled. The execution firewall remains absolute.

### DEC-002 — Thesis-led hybrid engine

**Decision:** The engine is thesis-led and hybrid:

- AI researches, cites, drafts, challenges, and reviews;
- deterministic code owns quant calculations, tax, risk, evaluation, sizing,
  and order arithmetic; and
- James owns policy values, approvals, and real-world action.

**Implementation consequence:** prose or model judgement may never directly
write a monetary, percentage, quantity, risk-limit, or order field without a
validated deterministic contract and provenance.

### DEC-003 — Model A excluded from capital contracts

**Decision:** Model A is totally excluded from every capital contract. Its
signals, probabilities, labels, SHAP values, and derived rankings may not set or
influence thesis basis, conviction, risk, sizing, staged orders, evaluator
classification, or promotion.

**Implementation consequence:** Model A is already excluded from capital and
new investment-engine evidence dependencies. Complete runtime/product removal
is the pending, approval-gated target under the staged decommission in
`model-a-decommission.md`; it is not a fact asserted by this dossier.
Historical data, outcomes, model artifacts, configurations, and decay evidence
remain checksummed and read-only. The existing signal-driven allocator and
opportunity-cost ranking remain non-authoritative and become unreachable only
after the corresponding retirement mission closes.

### DEC-004 — Safe proposal materialiser first

**Decision:** Complete the safe `ThesisProposal` materialisation path before
expanding discovery or tailored portfolio output.

**Implementation consequence:** reuse the proposal schema already on `main`;
close the currently stubbed `create_thesis_from_agent_run()` consumer. Agent
content creates a governed draft only. Approval remains a separate human action,
with evidence and transition-order checks intact.

### DEC-005 — Persistent report, review, and monitoring second

**Decision:** After the safe materialiser, complete persistent broker-report
content, review history, and change monitoring.

**Implementation consequence:** reuse `report_sections`, thesis revisions,
governance events, and existing invalidation jobs. The immutable report version
must be created before the review context that binds its ID and hash. Review
eligibility is a separate artifact and never mutates the report. Add linkage and
missing records rather than a parallel document database.

### DEC-006 — Deterministic construction and sizing fail closed

**Decision:** Target construction and sizing are deterministic. All policy values
and case-specific loss anchors are set or ratified by James. Until every required
value is present and ratified, construction and sizing fail closed.

**Canonical outcomes:**

- `PROPOSED`
- `REJECTED_NO_CONSTRUCTION_POLICY`
- `REJECTED_INELIGIBLE_CASE`
- `REJECTED_INFEASIBLE_PORTFOLIO`
- `SIZED`
- `REJECTED_NO_POLICY`
- `REJECTED_POLICY_VIOLATION`

**Implementation consequence:** no target weight, risk budget, stop/loss anchor
or cap is inferred from industry practice, portfolio history, model output or
training knowledge. A missing input can produce a useful rejection artifact,
never an estimated target or order.

### DEC-007 — CLI and brief first; no web

**Decision:** The implementation surfaces are the CLI and daily brief. No web or
mobile interface belongs in the 12-sprint programme.

**Implementation consequence:** acceptance must exercise actual CLI commands
and brief rendering, including calm failure/paper-only states.

### DEC-008 — Repository roadmap manifest is canonical

**Decision:** `docs/product/roadmap.yaml` is the canonical machine-readable
sequencing manifest for this programme.

**Implementation consequence:** it must validate against
`docs/programs/investment-engine/schemas/roadmap.schema.json`. Narrative sprint
documents elaborate the manifest but do not silently contradict it.

### DEC-009 — Twelve weekly outcome sprints

**Decision:** Deliver through 12 weekly, outcome-based sprints. The anchor is the
first programme week after the bootstrap dossier PR merges, not a fabricated
calendar date.

**Implementation consequence:** a sprint closes only on its exit evidence. An
unmet gate remains unmet even if the nominal week ends.

### DEC-010 — Evidence tiers and operational gate

**Decision:** Outputs begin `PAPER_ONLY`. The programme may enter
`UNCALIBRATED` staging only after the operational gate passes: at least 30
consecutive complete sessions under one frozen evaluator version, bit-identical
replay, at least 99.5% priced NAV-days, zero unresolved material accounting or
data defects, genuine XJO-TR, the effective broker fee schedule, Model A
isolation, and a James-ratified risk policy.

**Implementation consequence:** the clean-session clock begins only after the
real construction, risk, sizing, staging, fill, accounting, benchmark and
evaluator lineages are all frozen. A material change resets it. Thirty
re-labelled, reconstructed, pre-freeze or backfilled sessions do not qualify.
The twelve-sprint build therefore ends `PAPER_ONLY`; `UNCALIBRATED` requires an
elapsed post-programme observation runway.

### DEC-011 — Edge-claim gate

**Decision:** An edge claim is prohibited until both of these prospective
minimums are met under the frozen protocol:

- at least 252 prospective sessions; and
- at least 20 matured episodes, each observed through 63 sessions.

The strategy gate also requires positive after-tax, after-fee, stress-cost
results and positive one-sided 90% moving-block-bootstrap lower bounds versus
both hold and XJO-TR, at least 95% of intended notional filled within five
sessions, zero policy breaches, and drawdown inside James's mandate.

**Implementation consequence:** the 12-week programme cannot promote itself to
`EVIDENCE_BACKED` on schedule alone. Failed, open, rejected, and hold episodes
remain in the denominator according to the frozen evaluator rules. Episode
origins may overlap. They must follow a pre-registered schedule, carry dependency
groups and effective-sample diagnostics, and use the frozen dependency-aware
bootstrap. Requiring 20 non-overlapping 63-session episodes inside 252 sessions is
mathematically inconsistent and is not the accepted rule.

### DEC-012 — North-star metrics

**Decision:** The programme is judged by:

1. **Capital Under Discipline** — capital covered by current governed thesis,
   ratified risk policy, deterministic sizing/decision evidence, and active
   monitoring;
2. **material-event alert latency** — P95 event-to-alert below one trading day;
   and
3. **prospective active return** — after tax and costs versus genuine XJO total
   return, reported with drawdown, sample size, and a hold comparison.

**Implementation consequence:** feature count, raw win rate, simulated gross
return, or price-only XJO performance is not a substitute.

### DEC-013 — Model routing

**Decision:** Fable on the lower setting is used only for frozen implementation
work. Opus/Ultra is required for architecture, financial semantics, migrations,
and adversarial review.

**Implementation consequence:** "frozen" means the contract, invariants,
acceptance fixtures, and file scope already exist and no financial meaning is
being chosen during implementation.

### DEC-014 — Repair escalation

**Decision:** After two failed repair cycles on the same acceptance failure,
stop patching locally and escalate to Opus/Ultra for diagnosis and a revised
plan.

**Implementation consequence:** changing the test, fixture, gate, denominator,
or requirement to make the third attempt pass is not a repair.

### DEC-015 — Pull-request ceilings

**Decision:**

- an 8-hour mission normally produces one PR and may produce at most two; and
- a 12-hour mission may produce at most two product PRs plus one evidence/ops
  PR.

**Implementation consequence:** unfinished scope stays unmerged or moves to the
next mission. PR ceilings are maxima, not quotas, and never justify mixing
unrelated financial semantics into one diff.

### DEC-016 — GitHub baseline and supersession truth

**Decision:** The accepted planning base began at `main@e5967487…`. Before the
dossier was written, PR #69 merged and advanced the implementation baseline to
`main@9d442de2…`. PR #68 already salvaged and merged the net-new PR #64 work;
PR #64 is closed.

**Implementation consequence:** do not plan another PR #64 salvage. Treat PR
#69's handoff and migration-count reconciliation as shipped baseline truth.

### DEC-017 — V1 capital universe

**Decision:** The v1 capital path is long-only XASX securities in AUD. Non-XASX
and foreign-currency theses may remain research-only but cannot enter
construction, evaluation, sizing or staging in this programme.

**Implementation consequence:** US tax, benchmark, FX, calendar, settlement and
order semantics are not guessed. Expanding the capital universe requires a new
ratified contract set and prospective lineage.

### DEC-018 — Transparent risk-budget target construction

**Decision:** The engine, not an opaque external input, produces target weights.
V1 uses James-ratified loss-at-risk budgets among current `PAPER_ELIGIBLE` cases.
It does not use a conviction score, predicted return, Model A, signal rank or an
opaque optimiser.

**Implementation consequence:** target construction freezes the complete
portfolio, reservations, eligible cases, case-specific James-ratified
risk-reference prices, and construction/risk policies. It derives raw notionals
from loss budget divided by stop distance, applies individual caps, applies a
single deterministic coupled-constraint shrink, floors board lots, repairs in a
stable order, and recomputes the whole portfolio. Missing or infeasible input
rejects the proposal.

### DEC-019 — Report precedes review

**Decision:** `BrokerReportVersionV1` is immutable and exists before
`ReviewContextV1`. A review decision refers to the exact report and context
hashes; it is not embedded later by mutating the report.

**Implementation consequence:** the implementation sequence is report in S03,
review context in S04, and blind review/eligibility in S05. Any report change
requires a new version, context and review cycle.

### DEC-020 — Typed lineage and orthogonal states

**Decision:** Every downstream capital artifact resolves a shared typed
`InvestmentCaseLineageV1`. Investment-case state, artifact validity, shadow
evaluation state, evidence tier, deployment visibility, staged-package state and
James disposition are separate state machines.

**Implementation consequence:** a generic hash map or a single lifecycle enum is
not sufficient. `ORDER_STAGED` describes a non-routable package. James approval is
a separate audit record and never implies placement or fill.

### DEC-021 — Evidence policy is not capital policy

**Decision:** `risk-policy-v1` contains only mandate, exposure, liquidity, loss
and sizing rules. `evaluation-policy-v1` contains prospective cohort,
benchmark, statistical, evidence-language and reset rules.
`promotion-decision-v1` records James's immutable evidence decision.

**Implementation consequence:** changing a bootstrap or sample threshold does
not silently change the executable risk-policy hash, and an evaluator boolean
cannot promote itself.

### DEC-022 — Recomputable evaluator

**Decision:** `paper-evaluator-v1` is a derived digest over immutable evaluator
configuration, origin, intent, order/fill/settlement, branch ledger, branch NAV,
episode outcome and cohort-statistics artifacts.

**Implementation consequence:** open, blocked, rejected, no-action, invalid,
matured and unavailable origins are representable. Counts, returns, costs, tax,
fill ratio, drawdown, intervals and gates are recomputed from referenced records.
A producer-supplied aggregate alone is not evidence.

### DEC-023 — Deterministic staging policy

**Decision:** Exact staged prices, stages and expiry come only from an effective
James-ratified `staging-policy-v1`.

**Implementation consequence:** quote source and age, side-specific formula,
effective tick table, split, validity, market-move invalidation and no-reprice
rule are pinned. A material input change creates a new sizing/staged artifact.
No in-place repricing and no broker capability are permitted.

### DEC-024 — Canonical financial bytes and honest tax

**Decision:** Capital hashes use RFC 8785/JCS canonical JSON, excluding the outer
hash field. Database-bound decimals use exactly six fractional digits, no
exponent or negative zero, within `NUMERIC(18,6)`; quantities are integer
strings. Tax results are labelled `after-tax estimate` unless the versioned James
profile and coverage matrix are complete.

**Implementation consequence:** contract-specific array ordering and rounding
rules are normative. Unsupported tax/accounting treatment blocks the affected
gate; it is not converted to zero.

### DEC-025 — Recommended runtime decommission with immutable evidence retention

**Ratification status:** pending James's explicit approval in the S01 M02
decommission record.

**Recommended decision:** Model A `v1_5` has no continuing runtime,
product-health, capital,
review, allocator, or evaluator role. Its scheduled writers and exposed product
surfaces are disabled through a separate attended, James-approved implementation
mission. Historical evidence is retained read-only; no destructive table or
artifact deletion is part of the twelve-week programme.

**Implementation consequence if ratified:** S01 M02 inventories and archives the
complete surface and records the decision without runtime mutation. A separate
M-A2 change lands the James-approved authority amendment; only then may M-A3
disable the scheduler/writers, retire the legacy review entry point, update
health controls, and collect naturally elapsed no-write evidence. Until those
separate changes close, the current passive-monitor policy and legacy surface
remain authoritative while Model A stays excluded from capital.
S04–S05 replace review semantics independently; S08–S11 prove evaluator
isolation; S12 proves zero active imports, queries, jobs, fallbacks, or health
dependencies. A future quantitative model is a new pre-registered evidence
programme and cannot revive `v1_5`.

## Canonical contract names

The following names are canonical across every applicable prose contract,
JSON Schema, fixture, code path, and persisted version. The proposal registry is
a code contract; the versioned payloads have normative JSON Schemas.

| Contract | Purpose |
|---|---|
| `proposal-registry` | Code-owned object/version/producer/citation/materializer routing contract |
| `model-a-archive-manifest-v1` | Deterministic checksummed read-only Model A evidence inventory |
| `model-a-archive-restore-evidence-v1` | Attended non-production archive reproduction and exact comparison |
| `thesis-proposal-v1` | Governed evidence-linked research-thesis proposal |
| `review-context-v1` | Immutable point-in-time, Model-A-free reviewer packet |
| `reviewer-assessment-v1` | Blind immutable role assessment |
| `review-eligibility-v1` | Deterministic conjunctive review decision |
| `broker-report-v1` | Immutable versioned evidence-linked broker report |
| `security-classification-snapshot-v1` | Effective-dated security/issuer/group/sector/theme/lot/tick projection |
| `investment-case-lineage-v1` | Typed resolvable capital lineage manifest |
| `portfolio-construction-policy-v1` | James-ratified target-construction rules |
| `portfolio-proposal-v1` | Deterministically derived point-in-time desired portfolio state |
| `risk-policy-v1` | James-owned capital risk and sizing mandate |
| `sizing-decision-v1` | Deterministic sizing result or fail-closed rejection |
| `staging-policy-v1` | James-owned staged-price, split, validity and expiry rules |
| `staged-order-set-v1` | Exact, expiring, non-executable order staging package |
| `evaluation-policy-v1` | Prospective cohort, statistics, gates and language rules |
| `promotion-decision-v1` | James's immutable decision over an evidence packet |
| `evaluator-config-v1` | Frozen evaluator and implementation lineage |
| `evaluation-origin-v1` | Pre-registered origin and five branch identities |
| `paper-intent-v1` | Non-routable paper delta intent |
| `paper-order-v1` | Non-routable simulated order instruction |
| `paper-fill-v1` | Later-event causal simulated fill or no-fill result |
| `branch-ledger-v1` | Append-only double-entry shadow branch ledger |
| `branch-nav-v1` | Reconciled daily branch NAV record |
| `episode-outcome-v1` | Open/blocked/matured horizon result |
| `cohort-statistics-v1` | Recomputed prospective statistics and gate predicates |
| `accounting-policy-v1` | Versioned cost, tax, FX, action and rounding semantics |
| `fill-model-v1` | Versioned causal base/stress fill rules |
| `benchmark-policy-v1` | Genuine XJO-TR source, revision and comparison semantics |

Additional locked values:

- benchmark ID: `XJO-TR`
- evidence tiers: `PAPER_ONLY`, `UNCALIBRATED`, `EVIDENCE_BACKED`
- staged lifecycle state: `ORDER_STAGED`
- gates: `operational_gate`, `strategy_gate`, `promotion_gate`

## Interpretation rule

When two documents differ:

1. an explicit later governor decision wins;
2. this register governs the accepted investment-engine target;
3. the current runtime constitution continues to govern live behaviour until a
   reviewed implementation PR changes it;
4. `docs/product/roadmap.yaml` governs sequence and dependencies; and
5. contract schemas govern machine shape.

No interpretation may weaken manual execution, Model A exclusion, fail-closed
risk policy, prospective evidence gates, or honest benchmark reporting.
