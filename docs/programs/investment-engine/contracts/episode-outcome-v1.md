# Episode Outcome v1

`episode-outcome-v1` is the immutable maturity result for one scheduled origin.

**Machine contract:** [`episode-outcome-v1.schema.json`](../schemas/episode-outcome-v1.schema.json)

It resolves the origin and five-branch NAV artifact, records identical endpoints,
and reports branch return, maximum drawdown, costs, tax, fill fraction, and
completeness. It derives `PROPOSAL_STRESS` after-cost, after-tax-estimate active
return versus hold and XJO-TR. For episode endpoint returns it reports the
relative-wealth result `(1 + r_stress) / (1 + r_comparator) - 1`; this episode
diagnostic is not substituted for the paired-daily S11 estimand.

An outcome is either `MATURED` or `UNAVAILABLE`. Open, blocked, rejected,
no-action, and invalid origins remain in the evaluator's origin register and do
not require a fabricated outcome. Overlap/dependency groups are preserved so
episode observations are never assumed independent. The semantic validator
recomputes every return and cost field from the referenced NAV/ledger chain.
