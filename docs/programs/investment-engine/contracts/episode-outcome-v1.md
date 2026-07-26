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
episode observations are never assumed independent. Every return and cost field
is derived from the referenced `branch-nav-v1`/`branch-ledger-v1` chain and is
never attested by the producer.

## Where that derivation is enforced

The derivation requirement above is enforced by the outcome service built in
**S11** and by its acceptance evidence (AC-45: the evaluator digest must
recompute every origin/status/maturity count and branch outcome from resolvable
records). **It is not checked by the dossier harness.** The semantic validator
resolves this contract's typed references and validates it against its schema,
but recomputes none of `active_return_vs_hold`, `active_return_vs_xjo_tr`,
`active_return_branch`, `mandate_drawdown_breach_count` or
`fill_fraction_within_5_sessions` from the NAV/ledger chain, and never resolves
`branch_nav_ref` to compare endpoints. The nearest harness check does not read
this contract at all: it asserts that `fill_fraction_within_5_sessions`, the
breach counts and the completeness flags are *equal* between
`cohort-statistics-v1` and the evaluator golden fixture — an agreement two
consistently wrong values also satisfy. The shipped fixture is `UNAVAILABLE`
with null returns, so no `MATURED` derivation path is exercised anywhere in the
dossier.
