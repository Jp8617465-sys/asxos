# Evaluation Policy v1

**Normative wire shape:** [`../schemas/evaluation-policy-v1.schema.json`](../schemas/evaluation-policy-v1.schema.json)

## Purpose

`evaluation-policy-v1` owns the frozen operational and strategy evidence
protocol. It is deliberately separate from `risk-policy-v1`: capital limits do
not silently change statistical denominators, and an evidence-policy amendment
does not masquerade as a position-risk decision.

## Prospective cohort

- A lineage begins only after strategy, construction, risk, sizing, tax, cost,
  fill, benchmark, evaluator, schema, and code versions are fixed.
- Reconstructed or backfilled records never qualify.
- Open, blocked, rejected, no-action, invalid, matured, and unavailable origins
  remain in the frozen origin register and counts. Only matured outcomes enter
  return statistics; all exclusions and missing outcomes remain reported.
- Primary-horizon episodes may overlap. Dependence is handled by the frozen
  session-level circular moving-block bootstrap; overlap is never removed
  selectively after observing results.
- Any material semantic/version change opens a new cohort and resets the clean
  streak.

## Operational gate

All conditions are conjunctive: the configured consecutive complete sessions,
bit-identical replay, priced-NAV coverage, zero unresolved material defects,
genuine point-in-time XJO total return, effective broker-published fees, a
James-ratified risk policy, and a versioned structural-plus-perturbation proof
that Model A is absent.

## Strategy gate

The primary branch is `PROPOSAL_STRESS`. For each complete common session and
comparator (`HOLD`, `XJO_TR`), the observation is one paired daily log-active
return tuple. The primary estimand is the continuous stress branch's after-tax
estimate, after-cost daily log-active return and the statistic is:

```text
active_log_return_t = log(1 + proposal_stress_return_t)
                      - log(1 + comparator_return_t)

annualised_paired_log_active_return =
  exp(252 * mean(active_log_return_t)) - 1
```

No imputation is permitted. A session enters a comparison only when the stress
branch and comparator both have complete, point-in-time results for the same
trading session. V1 freezes:

- a circular moving-block bootstrap over tuples ordered by trading session;
- a primary block length of 10 and separately reported sensitivity lengths 5
  and 20;
- circular source indices modulo `N`, concatenated then truncated to exactly
  `N`;
- 100,000 replicates and at least 252 clean paired sessions;
- seed = unsigned big-endian first 128 bits of
  `SHA256(cohort_id|metric_id|evaluation_policy_sha256)`;
- NumPy `2.1.1`,
  `Generator(PCG64DXSM(seed)).integers(0, N)` with an upper-exclusive bound;
- empirical Type-1 nearest-rank 10th percentile for the primary one-sided 90%
  lower bound;
- empirical Type-1 two-sided 95% intervals for the 5/20 sensitivity results;
- positive primary lower bounds for both comparisons;
- minimum sessions and matured 63-session episodes;
- minimum intended-notional fill ratio;
- zero policy breaches and zero mandate drawdown breaches; and
- one pre-registered candidate family with Holm family-wise diagnostics. A
  candidate/version selection change opens a new cohort rather than editing the
  observed family.

A dirty or incomplete session resets the operational clean streak and is
reported; it is never imputed into the inferential series.

The producer persists evidence inputs and recomputes every gate. A supplied
`passed=true` value is never authoritative.

## Claims and authority

Operational passage permits only a James-reviewed `UNCALIBRATED` visibility
decision. Strategy passage plus a separate `promotion-decision-v1` may permit
`EVIDENCE_BACKED` language. Neither gate permits broker execution.
