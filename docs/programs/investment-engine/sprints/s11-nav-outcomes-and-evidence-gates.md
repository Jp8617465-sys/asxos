# S11 — Episode outcomes, cohort statistics, and evidence gates

**Initiative:** EVAL-05
**Phase:** prospective-evidence infrastructure
**Weekly outcome:** one derived evaluator digest recomputes all counts, outcomes,
statistics, defects and gates from immutable lower-level records
**Maximum evidence tier:** `PAPER_ONLY`
**Acceptance rows:** AC-45–48
**Depends on:** S10 reconciled branch ledger/NAV; S08 evaluation policy
**Unlocks:** S12 hidden staged-package/rendering capability and the later
post-programme observation runway

## Normative contracts

- `episode-outcome-v1`
- `cohort-statistics-v1`
- `paper-evaluator-v1` (derived digest)
- `evaluation-policy-v1`
- immutable operational/strategy gate decisions
- `promotion-decision-v1` (James-owned; cannot be passed during build by assertion)

## Episode outcomes

Every pre-registered S08 origin remains visible. At the primary 63-session horizon:

- `ENTER_OR_ADD`/`TRIM`/`EXIT` outcomes compare base/stress proposal branches with
  hold over identical dates and starting state;
- `NO_ACTION` and policy/review-rejected origins mature as an explicit no-action
  outcome with proposal equal to hold and zero active idea return;
- unfilled/expired intent stays in the proposed-strategy outcome and its opportunity
  cost/fill failure remains visible;
- open origins remain open; invalid/missing accounting creates an incomplete
  outcome and fails relevant gates; and
- no row is deleted or moved between cohorts after future results are known.

Outcome fields are recomputed from branch NAV/ledger refs: start/end values, external
flows, pre-tax return, after-tax-estimate return, decomposed costs/tax, hold return,
XJO-TR return, active returns, maximum drawdown, fill fraction and source hashes.

## Cohort counts must reconcile

The semantic validator recomputes:

```text
scheduled_origin_count
= open + blocked + rejected + no_action + expired + matured + invalidated

matured_episode_count
= matured actionable + matured rejected/no_action
```

Declared counts that do not equal referenced records fail. A gate cannot pass with
one episode while claiming twenty.

## Primary performance series

For each clean prospective daily observation, preserve paired returns:

```text
portfolio_after_tax_estimate_return
portfolio_stress_after_tax_estimate_return
hold_after_tax_estimate_return
xjo_total_return
cash_return
```

The primary relative statistic for reference `q` is paired log active return:

```text
a_t(q) = ln(1 + portfolio_stress_after_tax_estimate_return_t)
       - ln(1 + q_return_t)

annualised_active_return(q) = exp(252 * mean(a_t(q))) - 1
```

The strategy gate uses the stress branch versus both hold and genuine XJO-TR.
Simple total, TWR and attribution values are also reported and reconciled. A
capital-balance difference is never a return.

## Frozen v1 bootstrap

The evaluation policy preregisters exactly:

- resampling unit: paired daily return tuples, never independently sampled legs;
- method: circular moving-block bootstrap;
- primary block length: 10 consecutive XASX sessions;
- sensitivity block lengths: 5 and 20 sessions;
- repetitions: 100,000;
- PRNG: NumPy `PCG64DXSM` with pinned NumPy version;
- seed: unsigned first 128 bits of SHA-256 over
  `cohort_id|metric_id|evaluation_policy_sha256`;
- statistic: annualised paired log active return above;
- interval: empirical type-1/nearest-rank 10th percentile, a one-sided 90% lower
  bound;
- missingness: a missing paired observation makes that session dirty and resets
  the operational streak; it is never imputed;
- minimum sample: 252 clean prospective paired sessions;
- overlap: episode origins carry dependency groups, but the inferential series is
  continuous daily portfolio return; episode effective sample and cluster
  diagnostics are separately reported; and
- selection: one primary candidate version is frozen before the cohort. All
  attempted versions remain in the candidate-family register. Selecting a later
  winner starts a new prospective cohort; secondary candidates cannot borrow the
  primary cohort.

The locked gate remains `lower_bound > 0`. The report also shows 95% sensitivity
intervals and an economic-materiality hurdle, but neither silently changes the
governor's 90% gate.

## Fill/capacity predicate

```text
five_session_fill_ratio =
  notional filled within five eligible sessions
  / total positive intended notional for all policy-approved paper intents
```

Expired, partial and unfilled positive intent stays in the denominator. A zero
denominator is `indeterminate`, not pass. Rejected/no-action origin counts and
opportunity cost are shown separately. Report actual shadow equity, capital
utilisation, ADV/capacity utilisation and nominated scale curves.

## Operational gate

All predicates are conjunctive and derived:

- at least 30 consecutive complete prospective sessions after the final S12
  frozen lineage and James's observation authorisation;
- bit-identical replay of every qualifying session;
- at least 99.5% of required NAV-days priced;
- zero unresolved material defects in each class:
  price, FX, corporate action, tax, cost, accounting, general data and
  reconciliation;
- genuine point-in-time XJO-TR;
- effective fee schedule and complete tax/accounting coverage;
- structural plus perturbation Model A isolation evidence;
- zero broker-boundary violation; and
- unique effective James-ratified construction, risk and staging policies.

A dirty/indeterminate session resets the streak. S11 development data cannot pass.

## Strategy gate

All predicates are conjunctive and derived under one frozen lineage:

- at least 252 clean prospective paired sessions;
- at least 20 matured pre-registered 63-session origins (overlap is allowed and
  diagnosed);
- positive stress after-tax-estimate/after-cost active return versus hold and
  genuine XJO-TR;
- positive primary one-sided 90% moving-block-bootstrap lower bound for both;
- at least 95% five-session intended-notional fill ratio;
- zero risk/construction/sizing/staging-policy breaches;
- drawdown within James's ratified maximum; and
- complete sample, missingness, rejected/no-action/open/unfilled, capacity,
  regime and candidate-family reporting.

The strategy gate does not alter execution authority.

## Promotion gate

`EVIDENCE_BACKED` additionally requires:

1. passed immutable operational gate decision;
2. passed immutable strategy gate decision;
3. complete frozen evidence packet;
4. explicit James `promotion-decision-v1=APPROVED`.

The evaluator cannot manufacture James's decision. Withdrawal or a material defect
creates a new audit event and removes the label prospectively; history remains.

## Mission decomposition

### Mission S11-A — outcome and gate golden vectors (12h, contracts/tests PR)

- Freeze count reconciliation, no-action/rejected treatment, returns, fill ratio,
  defect materiality and every gate truth table.
- Build `29/30`, `30/30`, reset, `251/252`, 19/20, overlapping 20, one-episode
  false-claim, zero-denominator and failed-predicate fixtures.

### Mission S11-B — outcome/NAV derivation (12h, product PR)

- Implement episode outcome and daily paired-series derivation solely from
  lower-level refs.
- Reconcile every branch, count and decomposition; producer aggregates ignored.

### Mission S11-C — statistics kernel (12h, product PR)

- Implement pinned paired circular moving-block bootstrap and sensitivity outputs.
- Deterministic golden arrays pin PRNG/version/seed/quantile.
- Add selection-family, overlap/effective-sample, missingness and regime reports.

### Mission S11-D — gate service and persistence (12h, product PR)

- Recompute immutable operational/strategy decisions with evidence refs.
- False/inconsistent booleans and counts fail validation.
- Add reset lineage, defect references and James promotion-decision boundary.

### Mission S11-E — independent quant/accounting red-team (8h, evidence PR/review)

- Fresh context attempts denominator editing, look-ahead, benchmark substitution,
  aggregate spoofing, overlap abuse, trivial-capacity pass and promotion spoofing.
- Full deterministic replay, migration and recovery evidence.

## Observability

Emit evaluator/policy/cohort/config/code IDs/hashes, every reconciled count, paired
sample dates, primary/sensitivity statistics, effective sample, fill/capacity,
drawdown, each defect class/reference, gate predicate/reason/reset, replay result
and duration. Never emit an edge label from a failed/indeterminate gate.

## Rollback

Pause outcome/gate writers and presentation, preserve all lower-level evidence,
invalidate affected derived decisions through append-only audit, forward-fix and
start a new cohort for any semantic change. Never change a denominator or fixture
to rescue a result.

## Definition of Done

- [ ] Counts and all aggregates recompute from resolvable lower-level records.
- [ ] Open/rejected/no-action/unfilled outcomes remain visible.
- [ ] The 252/20×63 rule is mathematically coherent with overlapping origins.
- [ ] Bootstrap, estimand, missingness and candidate selection are fully frozen.
- [ ] Operational/strategy booleans cannot pass when any predicate fails.
- [ ] `EVIDENCE_BACKED` structurally requires James's promotion decision.
- [ ] Build data remains `PAPER_ONLY`; elapsed evidence is not fabricated.
- [ ] Migration/replay/recovery/full CI and fresh Opus/Ultra red-team pass.
- [ ] Combined worktree is clean.
