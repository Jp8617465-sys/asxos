# Investment engine architecture

**Status:** normative implementation architecture
**Programme boundary:** build through a non-routable `ORDER_STAGED` artifact and a
separate James disposition record; never connect to or act at a broker
**Capital scope for v1:** long-only XASX securities, AUD base currency, James as
the sole governor and user

## North-star loop

ASXOS is a governed, thesis-led investment operating system. Its useful output is
not a generic model score. It is a reproducible answer to:

> Given the evidence that was knowable at the time, James's ratified mandate, the
> current portfolio and tax lots, and the engine's prospective record, what should
> be researched, held, entered, reduced, or exited; what is the maximum
> policy-compliant quantity; what could falsify the case; and what evidence supports
> every step?

```text
verified evidence
  -> ThesisProposal
  -> governed thesis revision
  -> immutable BrokerReportVersion
  -> immutable ReviewContext
  -> blind independent assessments
  -> deterministic ReviewEligibilityDecision
  -> monitored InvestmentCase
  -> deterministic target portfolio
  -> deterministic portfolio-wide sizing
  -> prospective shadow intent and evaluator
  -> expiring staged order set
  -> separate James disposition
  -- programme and system authority stop here --
```

This ordering is mandatory. In particular, the report exists before the review
context that cites it, and construction/risk/sizing policy exists before a
prospective evaluator lineage begins. A later report, policy, construction,
accounting, fill, benchmark, evaluator, or sizing semantic starts a new lineage;
prior records remain audit evidence but cannot be relabelled into the new cohort.

## Institutional separation of duties

| Function | Owns | Must not |
|---|---|---|
| Research drafter | Causal thesis, cited claims, scenarios, catalysts, falsifiers and qualitative capital intent | Approve, write a target weight, size or stage |
| Evidence control | Point-in-time availability, provenance, coverage, freshness and canonical hashes | Express conviction or fill a missing value |
| Blind reviewers | Evidence, valuation, adversarial, portfolio-risk and implementation challenge | See peers' first pass, query live tables or edit the report |
| Eligibility service | Conjunctive completeness/finding/freshness decision | Average opinions or infer a missing assessment |
| Portfolio constructor | Reproducible targets from eligible cases and James-ratified policy | Read Model A, let an LLM choose a number or bypass a hard constraint |
| Risk and sizing kernel | Portfolio-wide constraint solution, lots and exact maximum quantities | Invent policy or increase a permitted target |
| Evaluator/accounting | Causal paper fills, double-entry branches, NAV, tax/cost estimates and prospective gates | Rewrite history or treat reconstruction as prospective |
| Staging kernel | Tick-rounded price, stages, validity and expiry from ratified staging policy | Reprice in place, route, submit or represent a fill |
| James | Ratify policies and case-specific risk anchors; approve/reject/amend; act externally if he chooses | Delegate capital or broker authority to an agent |
| Arbi | Sequence work and assess evidence/north-star progress | Originate a capital action or weaken a gate |

This mirrors institutional functional independence for a user-of-one. It does not
claim separate legal teams, prime-broker infrastructure, execution quality or
independent fund governance.

## Bounded contexts

### 1. Proposal intake

`agent_runs` and `agent_evidence` remain the ingestion boundary. One proposal
registry maps `(object_type, schema_version)` to:

- exact allowed producers;
- a closed JSON Schema validator;
- a recursive citation walker;
- a materializer; and
- legacy-envelope treatment.

Unknown object, version or producer fails before persistence. Complete canonical
proposal bytes are retained. The materializer creates a governed draft only.

### 2. Thesis and immutable report

The existing `theses`, `thesis_revisions`, `thesis_evidence`, governance events and
migration 0040 `report_sections` are reused. `BrokerReportVersionV1` is created
append-only from one exact thesis revision and evidence set. It carries:

- `investment_case_id` and case version;
- proposal, materialization run and thesis-revision identities and hashes;
- full claim/figure evidence references with publication/availability chronology;
- qualitative intent and a separately James-ratified case risk anchor where needed;
- producer/prompt/contract/code versions; and
- a canonical payload hash.

Its initial governance status is review-pending. Review never mutates it. Any
changed claim, figure, intent, risk anchor, catalyst, falsifier or discipline
creates a new report version and therefore a new review context/cycle.

### 3. Point-in-time blind review

`ReviewContextV1` references the exact report version and hash and freezes only
information available at `knowledge_cutoff`. Its evidence chronology enforces:

```text
published_at <= available_at <= retrieved_at <= knowledge_cutoff
knowledge_cutoff <= context_as_of <= generated_at
```

Five mandatory roles receive only the context bytes. Their first passes remain
hidden until all roles have submitted a valid assessment. An abstention does not
satisfy a mandatory role; a replacement assessment is required. The deterministic
`ReviewEligibilityDecisionV1` binds the report, context and every assessment hash
and returns `BLOCKED`, `FAIL` or `PAPER_ELIGIBLE`. Confidence is not a probability,
is never averaged and cannot set capital.

### 4. Monitoring and investment case

An `investment_case_id` survives report revisions. Monitoring persists source
events, availability time, materiality, alert delivery, acknowledgement, review and
disposition separately. A material event invalidates current eligibility and staged
artifacts until a new report/context/review completes. Monitoring proposes; it
never overwrites, approves, sizes or stages.

### 5. Deterministic portfolio construction

The v1 engine deliberately does not reuse the signal allocator or an opaque
mean-variance optimiser. It uses a James-ratified
`PortfolioConstructionPolicyV1` and transparent loss-at-risk budgeting:

1. Materialize and freeze `security-classification-snapshot-v1` from the
   authoritative security master, theme membership and XASX trading rules,
   alongside current settled holdings/lots, pending cash and staged reservations,
   prices/FX, eligible cases and all source hashes. Missing issuer, corporate
   group, sector, known theme-membership state, board lot, tick rule, effective
   interval or provenance makes the affected asset inadmissible; no slug/default
   may be inferred.
2. Admit only long-only cases whose exact report and review decision are current,
   `PAPER_ELIGIBLE`, unchallenged by monitoring and supported by a James-ratified
   case-specific risk-reference price.
3. Translate qualitative intent deterministically:
   `EXIT -> zero`; `HOLD -> current policy-compliant exposure`;
   `ENTER_OR_ADD -> compete for the ratified risk budget`. A `TRIM` request must
   name a James-ratified maximum exposure; otherwise it is blocked.
4. Allocate the available portfolio loss budget equally across eligible
   `ENTER_OR_ADD` cases unless the construction policy contains explicit
   James-ratified per-case budgets. No conviction score, predicted return or model
   rank changes the allocation.
5. For each long case, compute:

   ```text
   stop_distance_fraction =
     (reference_price - risk_reference_price) / reference_price

   raw_target_notional =
     case_loss_budget_aud / stop_distance_fraction
   ```

   A non-positive or missing distance is a typed rejection.
6. Apply the fixed individual cap waterfall: issuer/group, position, thesis loss,
   liquidity/days-to-liquidate, scenario loss and policy-specified tax/turnover cap.
7. Solve coupled cash, gross, sector/theme, turnover, reservation and portfolio-loss
   constraints with one documented proportional shrink. Floor to effective board
   lots, then repair residual breaches in stable
   `(binding-priority, investment_case_id, symbol)` order.
8. Recompute the complete before/after portfolio. If any hard constraint fails,
   reject the whole proposal; do not retain a partly valid `SIZED` result.

The output records every candidate notional, cap, binding constraint, shrink factor,
rounding step, exclusion and final target. An order-permutation test must return
bit-identical output. Diagnostic beta, volatility, covariance/factor exposures and
stress loss may be added only with pinned methods/data. They become hard gates only
when James ratifies corresponding policy values.

This is how the engine creates a real tailored target without allowing an LLM or
Model A to choose weights. James owns the mandate and risk anchors; deterministic
code owns arithmetic and complete portfolio feasibility.

### 6. Prospective evaluator and accounting

The evaluator is assembled from immutable lower-level artifacts rather than
producer-asserted aggregate returns:

- evaluator configuration, dependency-isolation proof and pre-registered origin schedule;
- frozen portfolio, trading-calendar, tax-profile and benchmark observations;
- paper intent, order, fill, cancellation and settlement;
- branch double-entry ledger;
- daily branch NAV;
- episode outcome; and
- cohort statistics and gate decisions.

Each origin freezes five branches: proposal base, proposal stress, hold/no-action,
genuine XJO total return and eligible cash. Open, blocked, rejected, no-action,
invalid, matured and unavailable origins remain visible. They do not disappear
from counts because an outcome is inconvenient.

Portfolio skill uses the continuous shadow portfolio's cash-flow-aware time-weighted
return against an identical-flow XJO-TR series. Idea skill uses pre-registered
63-session episode outcomes versus hold. Origins may overlap; they carry dependency
groups and effective-sample diagnostics. The impossible requirement for 20
non-overlapping 63-session episodes inside 252 sessions is expressly rejected.

Raw prices and explicit corporate actions drive accounting; adjusted close is
reconciliation-only. Tax is an estimate tied to a versioned James profile and
coverage matrix. Unsupported tax treatment, missing lots, price, FX, benchmark,
fee, action or settlement blocks the affected gate.

### 7. Deterministic staging

`StagingPolicyV1` is James-ratified and effective-dated. It owns quote source/age,
buy/sell price formula, effective ASX tick table, stage count/split, `not_before`,
validity, total expiry, market-move invalidation, maximum notional including fees
and no-in-place-reprice rule.

A staged set must resolve the full typed lineage and a valid sizing decision. Its
worst-case notional plus fees cannot exceed the sizing cap. `EVIDENCE_BACKED`
requires immutable passed operational and strategy gate decisions plus a James
promotion decision. A staged set is never a broker order.

## Typed capital lineage

Every capital artifact uses one `InvestmentCaseLineageV1` manifest. Applicable
steps require both stable identity and canonical content hash:

```text
investment case/version
  -> thesis revision
  -> broker report version
  -> review context
  -> review eligibility decision
  -> monitor watermark
  -> construction/risk/sizing/staging policies + trading calendar + portfolio snapshot
  -> portfolio proposal
  -> sizing decision
  -> evaluator configuration + dependency-isolation evidence + gate decisions
  -> benchmark/tax/accounting observations
  -> staged order set
```

Generic `source_hashes` are supplementary; they cannot replace typed foreign
identities. Integrated golden fixtures must resolve every reference and fail on
tampering, staleness or a broken hash.

## Separate state machines

One overloaded lifecycle cannot safely describe every object. These dimensions are
orthogonal:

| Dimension | Canonical states |
|---|---|
| Investment case | `DRAFT`, `REPORT_READY`, `IN_REVIEW`, `PAPER_ELIGIBLE`, `CHALLENGED`, `CLOSED` |
| Artifact | `VALID`, `BLOCKED`, `REJECTED`, `EXPIRED`, `SUPERSEDED` |
| Shadow evaluation | `CONFIGURED`, `SHADOW_ACTIVE`, `INCOMPLETE`, `GATE_FAILED`, `GATE_PASSED` |
| Evidence tier | `PAPER_ONLY`, `UNCALIBRATED`, `EVIDENCE_BACKED` |
| Deployment visibility | `OFFLINE`, `SHADOW_HIDDEN`, `STAGING_ELIGIBLE`, `JAMES_VISIBLE` |
| Staged package | `ORDER_STAGED`, `INVALIDATED`, `EXPIRED` |
| James disposition | `PENDING`, `APPROVED`, `REJECTED`, `AMEND_REQUESTED`, `EXPIRED` |

James approval does not mutate the staged artifact, imply placement or create a
holding. External placement/fill capture is a later separately reviewed scope.

## Transaction and idempotency boundaries

- Materialisation locks the source run and atomically writes thesis, revision,
  evidence, governance event and acted-on linkage.
- Report creation locks the thesis revision and evidence manifest and persists
  canonical bytes once.
- Review creation freezes report/context bytes before any assessment.
- Construction freezes the full portfolio, case and policy snapshots.
- A paper origin freezes intent, policy/configuration and starting state before
  future market data exists.
- A sizing decision freezes the complete vector and cap waterfall.
- A staged set freezes quote/tick/staging policy and gate evidence.

Exact replay returns the existing result. The same idempotency key with different
canonical bytes is an integrity error, never a second write.

## Canonical bytes and arithmetic

- Wire timestamps are UTC `Z`.
- Quantitative database-bound strings use exactly six decimal places, no exponent
  and no negative zero, with range compatible with `NUMERIC(18,6)`. Quantities are
  integer strings.
- Domain arithmetic uses `Decimal` with operation-specific rounding declared by the
  contract. Board-lot quantity always floors; fee/tax currency rounding follows the
  pinned accounting policy.
- Content hashes are SHA-256 of RFC 8785/JCS canonical JSON over the contract
  payload after removing exactly `/canonical_hash/payload_sha256`. Arrays have
  contract-defined order; semantically unordered inputs are sorted before hashing.
- A hash envelope never hashes itself.

## Model A and execution firewalls

Model A is targeted for complete runtime and product-surface decommission under
the separate James-approved `model-a-decommission.md` mission. Historical
artifacts/data remain checksummed and read-only. Capital modules and contracts
may not import, query, encode or derive from Model A, `signals`, SHAP, `prob_up`,
predicted return, signal rank, legacy rebalance or allocator output. Deleting,
denying, or randomising archive access must leave every context, review, target,
gate, sizing and staged output bit-identical.

No programme component contains a broker client, credential, account identifier,
placement URL, route, submit/modify/cancel capability or inferred external fill.
Static deny lists, dependency tests and perturbation tests enforce both boundaries.

## Evidence and release timing

Twelve weeks build a complete hidden `PAPER_ONLY` system. They cannot manufacture
elapsed prospective evidence.

- **Operational gate:** starts only after the final construction, risk, sizing,
  staging, fill, accounting, benchmark and evaluator lineages are frozen. It needs
  30 consecutive clean prospective sessions.
- **Strategy gate:** needs at least 252 prospective sessions and 20 matured
  pre-registered 63-session episodes under the frozen protocol, plus every locked
  performance, fill, policy, drawdown and statistical predicate.
- **Promotion gate:** James separately reviews the immutable evidence packet and
  records a decision.

Therefore S12's honest programme-end ceiling is `PAPER_ONLY` and hidden shadow mode.
After the post-programme runway, R2 may permit `UNCALIBRATED` staging and R3 may make
it James-visible. Only the later strategy plus promotion gates permit
`EVIDENCE_BACKED` language. None permits execution.
