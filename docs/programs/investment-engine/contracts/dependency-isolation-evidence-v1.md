# Dependency Isolation Evidence v1

`dependency-isolation-evidence-v1` proves that the investment evidence path has
no structural or behavioral dependency on an excluded analytical subsystem.
It is a negative-control artifact, not an input to ranking, construction,
sizing, accounting, or promotion.

**Machine contract:** [`dependency-isolation-evidence-v1.schema.json`](../schemas/dependency-isolation-evidence-v1.schema.json)

## Required proof

The independent harness records:

- a static import and runtime-lookup scan over the registered capital/evidence
  roots;
- one run with the excluded subsystem removed;
- one run with its readable payload deterministically randomized;
- content hashes for baseline and perturbed input bundles;
- content hashes for every canonical output bundle; and
- byte-for-byte equality after canonical serialization.

Both perturbations run from the same frozen evaluator configuration, source
snapshots, clock, Decimal context, and runtime lock. The randomized run records
its seed hash. A pass requires zero forbidden imports/lookups, both registered
scenarios, and identical canonical outputs for proposal, sizing, paper
intent/order/fill, ledger, NAV, episode, cohort, and evaluator artifacts.

Missing coverage, a harness failure, or any output difference fails closed. The
evidence can establish absence of coupling; it cannot improve a return, score,
position size, gate, or evidence tier.
