# Cohort Statistics v1

`cohort-statistics-v1` computes the prospective cohort's primary continuous
active-return evidence under the frozen evaluator protocol.

**Machine contract:** [`cohort-statistics-v1.schema.json`](../schemas/cohort-statistics-v1.schema.json)

## Primary estimand

The resampling unit is a clean paired daily-return tuple from the continuous
`PROPOSAL_STRESS` shadow portfolio and one comparator (`HOLD` or genuine
`XJO_TR`). The stress branch is after frozen stress costs and the frozen tax
estimate. Episode returns are reported with overlap groups and effective sample
size but are not treated as independent daily observations.

For each comparator and complete common-endpoint session,
`a[t] = ln(1 + r_stress[t]) - ln(1 + r_comparator[t])`. The registered
statistic for an ordered sample is `exp(252 * mean(a[t])) - 1`; it is an
annualised relative-wealth rate, not an arithmetic difference of returns.

The artifact records all scheduled/open/blocked/rejected/no-action/invalid/
matured counts and proves that no registered origin was removed. It also pins
the exact circular moving-block-bootstrap statistic, primary and sensitivity
block lengths, repetitions, seed material, deterministic PRNG/runtime,
empirical Type-1 estimator, confidence, missingness behavior, and Decimal
output rounding.

The bootstrap orders clean paired sessions ascending. A block starts at a
uniform draw from NumPy `Generator(PCG64DXSM(seed)).integers(0, N)` under
NumPy `2.1.1`, advances by source index modulo `N`, concatenates blocks, and
truncates to `N`. The primary block length is 10; blocks 5 and 20 produce
two-sided 95% sensitivity intervals. Every run uses 100,000 replicates.

For each `metric_id`, the seed is the unsigned big-endian first 128 bits of
`SHA-256(cohort_id + "|" + metric_id + "|" + evaluation_policy_sha256)`.
The primary one-sided 90% lower bound is the empirical Type-1 nearest-rank
10th percentile. At least 252 clean prospective paired sessions are required.
A dirty observation resets the operational streak and is never imputed.

Candidate-family and trial-registry hashes prevent winner-only reporting.
Family size, selection events, Holm diagnostic results, and
`all_registered_candidates_reported` are mandatory. A strategy-gate pass
requires both locked lower bounds to be positive and the frozen familywise
diagnostic to pass; a later change requires a new evaluator lineage.

Each comparator result is explicitly `COMPLETE` or `UNAVAILABLE`. If the frozen
bootstrap cannot be computed—especially before 252 clean paired sessions—the
primary estimate, primary bound, and both sensitivity intervals are `null`, a
reason code is mandatory, and strategy evidence fails closed. The evaluator
never manufactures a confidence bound from an undersized sample.
