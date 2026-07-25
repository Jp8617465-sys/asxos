# Investment engine acceptance matrix

**Program:** ASXOS thesis-led investment engine
**Baseline:** `Jp8617465-sys/asxos@9d442de287e123ae090b95838155dc41d76ee5f3`
**Build ceiling:** hidden `PAPER_ONLY`; no elapsed evidence is fabricated
**Terminal system action:** persist non-routable `ORDER_STAGED`; James acts externally

This is the programme-wide executable test oracle. “Pass” requires a deterministic
test, hash-resolving fixture, migration/integration check or genuine prospective
observation. Prose, a producer-supplied boolean, a schema-valid aggregate or an
elapsed-week label is not evidence.

## Locked invariants

| ID | Invariant | Required executable evidence | First locked | Gate |
|---|---|---|---|---|
| AC-01 | James is the only user; no auth, tenancy, new RLS or `user_id` enters the programme path. | Schema/static/migration deny scans. | S01 | Programme |
| AC-02 | No broker client/account/credential/route/endpoint/external-order ID or submit/modify/cancel capability exists; system terminal is `ORDER_STAGED`. | Dependency/import/config/route deny tests and runtime circuit breaker. | S01 | Programme |
| AC-03 | Read-only M02 resolves every deployed Model A job/writer/reader/surface and produces a schema-valid, cross-record-reproducible archive/restore packet plus explicit approval state without runtime mutation. Only separately approved M-A2/M-A3 changes may align authority, disable legacy jobs, observe a real no-write window and make `/pm-review` fail closed. Every new capital boundary denies Model A, signals, SHAP, probabilities, ranks and allocator output regardless of the retirement decision. | Exact class-set/count/range/hash archive and restore comparison, explicit approval/`NOT APPROVED`, then—only when separately authorised—no-write observation, zero-schedule/health dependency scan and legacy-command tombstone; new-path static/perturbation tests always pass. | S01 | Programme |
| AC-04 | AI may research, cite, draft and qualitatively challenge; deterministic code alone owns target weights, risk, tax, accounting, fills, statistics, quantities, prices/stages and gates. | Producer/field-authority negative fixtures and exact replay. | S01 | Programme |
| AC-05 | Wire timestamps are UTC `Z`; hashes use JCS/RFC 8785 excluding the outer hash; database-bound decimals are canonical six-place strings within `NUMERIC(18,6)`, with no negative zero/float. | Schema/semantic/tamper/precision/overflow/rounding tests. | S01 | Programme |
| AC-06 | `(object_type,schema_version)` and exact producer are persisted in the canonical agent-run envelope; legacy rows have an explicit read-only mapping. | Registry/DB round-trip, unknown-version/producer and legacy fixtures. | S02 | Functional |
| AC-07 | The sole v1 thesis producer is the newly implemented `instrument-thesis-drafter`; no nonexistent producer is assumed available. | Agent allowlist/contract/logging tests. | S02 | Functional |
| AC-08 | Every nested citation resolves to knowable, non-speculative, content-hashed evidence and retains field-local order. | Recursive walker, missing/speculative/future/tamper vectors. | S02 | Functional |
| AC-09 | Materialisation creates only a governed research draft through ordered audited transitions; no approval, active position or capital state. | Transition and direct/skip-state denial tests. | S02 | Functional |
| AC-10 | Materialisation is atomic/idempotent: exact retry returns one graph; conflicting acted-on bytes fail; injected crash leaves no partial write. | Concurrency/idempotency/failure-injection DB tests. | S02 | Functional |
| AC-11 | `BrokerReportVersionV1` exists before review and binds exact proposal/run, thesis revision, evidence manifest and investment-case identity/hash. | Integrated chain resolution and missing-link tests. | S03 | Functional |
| AC-12 | Reports are immutable/versioned; changed claim/figure/scenario/intent/risk anchor creates V+1 and V1 remains byte-identical. | CAS/concurrency/old-new snapshot/tamper tests. | S03 | Functional |
| AC-13 | Every capital figure/claim has point-in-time provenance; AI cannot author a James-only case risk anchor. | Figure provenance, chronology and producer-authority tests. | S03 | Functional |
| AC-14 | Report hash is canonical and non-self-referential; corrected evidence appends a new version rather than rewriting history. | JCS golden bytes and correction/replay tests. | S03 | Functional |
| AC-15 | `ReviewContextV1` binds the exact S03 report ID/hash and complete report/thesis/catalyst/falsifier/discipline content. | Context/report tamper and completeness vectors. | S04 | Functional |
| AC-16 | Evidence chronology enforces `published <= available <= retrieved <= knowledge_cutoff <= context_as_of <= generated`; future/revised-late data blocks. | Boundary and contamination vectors. | S04 | Functional |
| AC-17 | All first-pass reviewers receive identical immutable bytes and no database/network tool; source prompt injection is inert. | Adapter capability, packet parity and injection tests. | S04 | Functional |
| AC-18 | Deleting/randomising Model A rows leaves context bytes/hash bit-identical; forbidden query/import/payload tokens fail. | Structural, SQL/import and perturbation tests. | S04 | Programme |
| AC-19 | Five mandatory roles persist blind immutable first passes with exact approved agent/prompt/model/rubric bundles; every finding claim/evidence ref resolves inside the frozen context and every closed finding resolves an append-only James/governance record. | Blind visibility, canonical hash, identity-forgery, dangling-ref, resolution-laundering and duplicate/conflict tests. | S05 | Functional |
| AC-20 | An abstention is retained but does not satisfy a mandatory role unless a linked replacement assessment exists. | Full abstention/replacement truth table. | S05 | Functional |
| AC-21 | `ReviewEligibilityDecisionV1` recomputes `BLOCKED`, `FAIL` or `PAPER_ELIGIBLE` conjunctively; confidence/votes cannot override recomputed freshness/completeness/high/critical findings. | Full synthesis truth table, freshness-label forgery and aggregate-spoof negatives. | S05 | Functional |
| AC-22 | Report candidate bytes, case, context, assessments, findings, governance resolutions and eligibility are append-only and typed/hash-resolvable end to end. | Integrated review-chain, unbound-candidate, cross-case replay, tamper and migration tests. | S05 | Functional |
| AC-23 | Material events are point-in-time, persistent, deduped and correction-linked; they can only alert and propose a governed revision. | Event/correction/idempotency/permission tests. | S06 | Functional |
| AC-24 | A material event invalidates affected current eligibility/staged artifacts until a new report/context/review; it never edits or auto-approves. | Invalidation state and forbidden-write tests. | S06 | Functional |
| AC-25 | Alert latency uses ASX-open time and reports denominator, P50/P95/max, misses and unknown-publication count; empty/unknown cohorts are indeterminate. | Trading-calendar and SLO vectors. | S06 | Operational |
| AC-26 | Required jobs fail loudly, persist `job_runs` and ping deadman only after durable completion. | Failure injection, job record and Healthchecks inventory. | S06 | Operational |
| AC-27 | One unique James-ratified construction/risk/staging policy bundle is effective; missing/ambiguous/future/expired/unsigned values reject with no inferred default. | Policy selection/ratification boundary tests. | S07 | Functional |
| AC-28 | The engine produces target weights from eligible cases by the frozen loss-at-risk algorithm; no opaque target, conviction score, Model A rank or LLM number is accepted. | Formula golden vectors, producer-field denial and full derivation trace. | S07 | Functional |
| AC-29 | Eligible universe resolves report/review/monitor/risk-anchor/portfolio plus exact effective `security-classification-snapshot-v1`; issuer/group/sector/known-theme state/board-lot/tick/provenance missing or ambiguous makes the asset inadmissible. Excluded cases retain stable reasons; v1 capital is long-only XASX/AUD. | Admission/exclusion/foreign/short/stale/tamper/classification/effective-interval vectors. | S07 | Functional |
| AC-30 | Individual caps and one portfolio-wide proportional shrink/repair solve cash, gross, issuer/group, sector/theme, loss, turnover, reservations, liquidity and tax coupling. | Complete multi-cap before/after golden vectors, per-code comparison-direction vectors and policy-resolved `limit_value` mutation tests. | S07 | Functional |
| AC-31 | Input permutation is byte-identical; board lots floor; sells cannot exceed sellable quantity; final whole portfolio is recomputed and every hard check passes. | Metamorphic/property/oversell/rounding tests. | S07 | Functional |
| AC-32 | `SIZED` contains no rejected line and alone sets staging eligibility; rejected construction/policy/breach emits no quantity/stage. | Cross-field semantic fail-open tests. | S07 | Functional |
| AC-33 | Evaluator config pins construction/risk/sizing/staging/fill/accounting/tax/calendar/benchmark/data/code/schema versions and immutable Model A isolation evidence before any origin. | Config completeness/hash/change-reset and dependency-removal/randomisation tests. | S08 | Functional |
| AC-34 | Empty evaluator, zero matured episodes and open/blocked/rejected/no-action/invalid/matured/unavailable origins are representable; counts are not fabricated. | Lifecycle schema/semantic vectors. | S08 | Functional |
| AC-35 | Each origin is pre-registered before future data, carries schedule/dependency group and freezes five economically equivalent branch starts. | Chronology/five-branch/replay/overlap fixtures. | S08 | Functional |
| AC-36 | Reconstructed/development data is permanently excluded from promotion; provider/series/revision identity for genuine XJO-TR and other sources is explicit. | Mode/provider/price-only benchmark negative tests. | S08 | Evidence |
| AC-37 | Paper fills use only a real later eligible event under the frozen base/stress model; same-session/touch-only/future/overfill is impossible. | Fill truth table and provider-source vectors. | S09 | Functional |
| AC-38 | Partial, no-fill, expiry, cancellation and settlement are complete append-only state machines; unfilled intent stays visible. | Multi-session lifecycle/idempotency tests. | S09 | Functional |
| AC-39 | Every paper business event posts balanced append-only ledger legs; corrections reverse/link and crash/retry is atomic. | Double-entry golden vectors, balance and failure injection. | S09 | Functional |
| AC-40 | Paper artifacts cannot mutate live holdings or access broker/Model A surfaces. | Write-boundary/static/dynamic perturbation tests. | S09 | Programme |
| AC-41 | Raw prices and explicit effective-dated actions/FX drive accounting; adjusted close is reconciliation-only; unsupported/missing treatment blocks. | Action/FX/posting golden and unsupported vectors. | S10 | Functional |
| AC-42 | Tax state is versioned and branch-isolated; pre-tax and `after-tax estimate` NAV decompose realized/unrealized tax, fees/costs/franking/FX and coverage. | Tax conformance, branch-leak and incomplete-profile tests. | S10 | Functional |
| AC-43 | Daily NAV and TWR recompute from ledger and exact external-flow valuation boundaries; balance differences or asserted aggregate returns fail. | NAV/TWR/flow/reconciliation/spoof vectors. | S10 | Functional |
| AC-44 | Genuine point-in-time XJO-TR receives identical flows; comparison is labelled conservative after-tax hurdle; capacity reports capital scale/ADV/fill/unfilled costs. | Benchmark identity/flow/capacity/label tests. | S10 | Evidence |
| AC-45 | Evaluator digest recomputes every origin/status/maturity count and branch outcome from resolvable records; declared mismatches fail. | Integrated golden chain and one-row-claiming-20 negative. | S11 | Evidence |
| AC-46 | Strategy protocol uses 252 clean prospective paired daily sessions plus 20 matured pre-registered 63-session origins; origins may overlap and carry dependency/effective-sample diagnostics. | `251/252`, `19/20`, overlapping-20 and denominator vectors. | S11 | Strategy |
| AC-47 | Paired circular moving-block bootstrap exactly matches pinned block/repetition/seed/PRNG/statistic/quantile goldens; candidate selection/version change starts a new cohort. | Deterministic arrays, sensitivity and selection-history tests. | S11 | Strategy |
| AC-48 | Operational/strategy gates recompute every predicate, all eight defect classes, fill/capacity, drawdown, Model A isolation and policy breaches; any false/indeterminate predicate prevents pass. | `29/30`, reset, fail-open/tamper and complete truth-table fixtures. | S11 | Operational/strategy |
| AC-49 | Staged prices/splits/not-before/expiry derive only from ratified staging policy; worst-case notional plus fees never exceeds `SIZED`; no in-place reprice. | Tick/split/expiry/notional/invalidation goldens. | S12 | Functional |
| AC-50 | Every applicable typed case/report/review/monitor/proposal/policy/sizing/evaluator/staging reference and hash resolves; tamper/stale lineage invalidates the whole set. | Integrated cross-contract golden chain and tamper vectors. | S12 | Functional |
| AC-51 | Programme end remains hidden `PAPER_ONLY`; James-visible `UNCALIBRATED` needs 30 clean post-freeze sessions and R3 approval; `EVIDENCE_BACKED` also structurally requires passed strategy evidence and James promotion decision. | Visibility/tier cross-field tests and elapsed-runway evidence. | S12/post | Release |
| AC-52 | James disposition is separate immutable audit and never placement/fill; CLI/brief render the identical persisted version/tier/visibility/lineage/constraints/expiry/firewall truth. | Decision conflict, broker deny and shared-view snapshot tests. | S12 | Functional |

## Cross-cutting delivery gates

Every sprint also must prove:

- additive migration preflight against live dependencies, full-chain apply in a
  clean integration target, compatibility and forward recovery when persistence
  changes;
- exact baseline/head SHAs, scoped files/owners, model-routing log, repair count,
  targeted/full test output, PR list and clean combined worktree;
- Fable-low only on frozen semantics; Opus/Ultra owns architecture, finance,
  tax/accounting/statistics, migrations, capital boundaries and fresh red-team;
- after two failed repairs on the same invariant, escalate rather than weakening
  the invariant, fixture, sample or denominator.

These are sprint-close prerequisites even when they do not receive separate AC IDs.

## Canonical definitions

### Capital path

The capital path begins when an artifact can change James's view of whether, what or
how much to enter, hold, trim or exit. It ends at non-executable `ORDER_STAGED`.
Research-only foreign theses are outside only while they remain mechanically
unable to influence that path. Model A is not a continuing monitor exception:
it is excluded from the capital path now; complete runtime retirement plus an
immutable audit archive is the approval-gated target, not a state this dossier
claims has already occurred.

### Capital Under Discipline

For one complete fresh `as_of`:

```text
eligible_invested_capital_aud =
  sum(abs(current XASX holding market value in AUD))

disciplined_capital_aud =
  sum(abs(market value)) where the holding has:
    current governed thesis revision and immutable report;
    fresh complete evidence;
    passed exact review context/eligibility with no open high/critical finding;
    current monitor watermark with no unresolved material challenge;
    ratified construction/risk policy and deterministic proposal/sizing proof;
    reconciled price, lot, tax and accounting coverage.

capital_under_discipline_pct =
  disciplined_capital_aud / eligible_invested_capital_aud * 100
```

Cash is separate. Missing denominator data makes the percentage unavailable, not a
partial result labelled complete.

### Prospective performance

- Portfolio skill is continuous shadow-portfolio cash-flow-aware TWR versus
  identical-flow genuine XJO-TR, after estimated tax and explicit costs.
- Idea skill is a pre-registered 63-session origin versus hold/no-action.
- Origins may overlap and carry dependency groups. Twenty non-overlapping
  63-session origins would require at least 1,260 sessions and is not the rule.
- Rejected/no-action/unfilled/open outcomes and all attempted candidate versions
  remain visible.

### Clean session

A session counts only after the final S12 frozen bundle and James's shadow
authorisation, when all required jobs complete, every input/accounting/tax/benchmark
coverage predicate passes, replay is identical, no material defect or boundary
violation exists, and every artifact belongs to one lineage. A dirty or indeterminate
session resets the consecutive operational streak.

### Orthogonal states

Investment case, artifact validity, shadow evaluation, evidence tier, deployment
visibility, staged-package state and James disposition are separate. James approval
does not mutate an order set or imply placement/fill.

## Sprint evidence crosswalk

| Sprint | Rows closed | Continuously regressed |
|---|---|---|
| S01 | AC-01–05 | — |
| S02 | AC-06–10 | AC-01–05 |
| S03 | AC-11–14 | AC-01–10 |
| S04 | AC-15–18 | AC-01–14 |
| S05 | AC-19–22 | AC-01–18 |
| S06 | AC-23–26 | AC-01–22 |
| S07 | AC-27–32 | AC-01–26 |
| S08 | AC-33–36 | AC-01–32 |
| S09 | AC-37–40 | AC-01–36 |
| S10 | AC-41–44 | AC-01–40 |
| S11 | AC-45–48 | AC-01–44 |
| S12 | AC-49–52 | AC-01–48 |

## Sprint-close evidence bundle

1. Baseline and head commit SHAs plus refreshed GitHub/migration/live-state facts.
2. Accepted mission instance and model-routing/repair log.
3. Changed-file list mapped to approved ownership and AC rows.
4. Targeted test commands with unabridged counts and negative vectors.
5. Full `make check`/CI evidence; environment gaps separated from regressions.
6. Migration preflight/apply/recovery evidence when applicable.
7. Resolved cross-contract fixture/hash report and replay digest.
8. Surface snapshots for positive, blocked, stale, expired and hidden states.
9. Open risk, rollback trigger, exact recovery owner/action.
10. PR list within ceiling and final combined `git status --short`.
