# Evaluator Config v1

`evaluator-config-v1` is the immutable protocol registered before a prospective
cohort opens. It fixes the candidate family, origin schedule, five
counterfactual branches, every capital-calculation version, and the statistical
protocol. A changed field creates a new lineage and resets all clean-session and
strategy-evidence counts.

**Machine contract:** [`evaluator-config-v1.schema.json`](../schemas/evaluator-config-v1.schema.json)

## Frozen boundary

The configuration pins construction, risk,
[`sizing-policy-v1`](sizing-policy-v1.md), staging,
[`fill-model-v1`](fill-model-v1.md), cost,
[`tax-profile-v1`](tax-profile-v1.md),
[`accounting-policy-v1`](accounting-policy-v1.md),
[`trading-calendar-v1`](trading-calendar-v1.md),
[`benchmark-policy-v1`](benchmark-policy-v1.md), evaluator, code, schema, and
Decimal-context versions. Time-varying observations such as prices,
[`benchmark-snapshot-v1`](benchmark-snapshot-v1.md) levels, tax rates, and fee
schedules remain point-in-time inputs referenced by content hash; their
interpretation is fixed by these versions.

The branch set is exactly:

1. `PROPOSAL_BASE` — the proposed portfolio under the base fill/cost policy;
2. `PROPOSAL_STRESS` — the same decision under the frozen stress fill/cost policy;
3. `HOLD` — no discretionary trades, with actions, income, tax, and flows applied;
4. `XJO_TR` — the genuine XJO total-return reporting hurdle over identical endpoints;
5. `CASH` — no risky position, using the frozen observable cash-return policy.

No branch is a broker instruction or a live holding.

## Origin and statistical protocol

Origins follow a pre-registered trading-session schedule. Overlap is permitted
only when declared. Every origin receives a deterministic dependency group from
its overlapping 63-session horizon; overlap is never described as independence.
Open, blocked, rejected, invalid, no-action, and matured origins all remain in
the cohort registry.

The primary estimand is the `PROPOSAL_STRESS` branch's continuous after-cost,
after-tax-estimate daily log active return against `HOLD` and genuine `XJO_TR`.
For clean paired daily-return tuples \(a_t\), the reported statistic is:

```text
annualised active return = exp(252 * mean(a_t)) - 1
```

The primary inference is a circular moving-block bootstrap. Tuples are ordered
by trading session; a block begins at a uniformly drawn index and wraps with
`source_index mod N`. Concatenated blocks are truncated to exactly `N`
observations. The primary block length is 10 sessions, with 5- and 20-session
sensitivity runs. Each run uses 100,000 replicates.

The seed is the unsigned, big-endian first 128 bits of
`SHA-256(cohort_id + "|" + metric_id + "|" + evaluation_policy_sha256)`.
Random draws use NumPy `2.1.1`, `Generator(PCG64DXSM(seed))`, and
`integers(0, N)` with the upper bound excluded. The primary one-sided 90% lower
bound is the empirical Type-1 nearest-rank 10th percentile. S11 also reports
empirical Type-1 two-sided 95% sensitivity intervals for block lengths 5 and
20. Fewer than 252 clean prospective paired sessions yields `UNAVAILABLE`.
Any dirty paired observation resets the operational evidence streak; no
imputation is permitted.

Episode outcomes are breadth and decision-quality evidence, not independent
daily-return observations.

## Canonical fixture digests

Production artifacts must recompute `canonical_hash.payload_sha256` from the
RFC 8785 canonical payload after excluding only that digest field, then reject
any mismatch before resolving a reference. Repeated-character digests in
repository fixtures are conspicuous synthetic identity placeholders for
cross-contract wiring tests; they are not proof that fixture bytes were
content-addressed and are accepted only in explicit fixture-validation mode.

## Boundary

Evaluation is `PAPER_ONLY`, uses simulated fills, has no broker capability, and
cannot grant advice, approval, placement, or execution. Model A is structurally
outside the protocol; a separate perturbation evidence artifact proves removal
or randomisation leaves canonical outputs unchanged.
