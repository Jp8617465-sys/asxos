# Paper Evaluator v1

`paper-evaluator-v1` is a derived, immutable digest over one frozen prospective
evaluation lineage. It does not accept free-standing performance claims. Every
count, return, fill ratio, defect count, bootstrap result, and gate decision is
recomputed from content-addressed lower-level artifacts.

**Machine contract:** [`paper-evaluator-v1.schema.json`](../schemas/paper-evaluator-v1.schema.json)

**Synthetic runway fixture:** [`paper-episode-golden.json`](../fixtures/paper-episode-golden.json)

## Required evidence chain

The digest resolves:

- [`evaluator-config-v1`](evaluator-config-v1.md);
- every scheduled [`evaluation-origin-v1`](evaluation-origin-v1.md), including
  open, blocked, rejected, no-action, invalid, matured, and unavailable rows;
- applicable paper intents, orders, and fills;
- the five-branch [`branch-ledger-v1`](branch-ledger-v1.md) and
  [`branch-nav-v1`](branch-nav-v1.md) artifacts;
- matured [`episode-outcome-v1`](episode-outcome-v1.md) artifacts;
- one [`cohort-statistics-v1`](cohort-statistics-v1.md) result; and
- [`dependency-isolation-evidence-v1`](dependency-isolation-evidence-v1.md)
  proving Model A removal and
  randomisation leave canonical capital/evidence outputs byte-identical.

The five branches are `PROPOSAL_BASE`, `PROPOSAL_STRESS`, `HOLD`, `XJO_TR`, and
`CASH`. They share the same frozen origin state and external-flow timing.

## Cohort and denominator rules

An origin is registered before its outcome. The register can be empty and can
contain any mixture of:

`OPEN | BLOCKED | REJECTED | NO_ACTION | INVALID | MATURED | UNAVAILABLE`.

Counts MUST equal the register, references MUST resolve, and only `MATURED` may
carry a matured outcome reference. No row is deleted or relabelled to improve a
denominator. Reconstructed history is excluded from prospective evidence.

Overlapping 63-session episodes are permitted when their overlap and dependency
groups were frozen at origin. They are never called independent. The primary
inferential series is the `PROPOSAL_STRESS` shadow portfolio's complete
after-cost, after-tax-estimate daily active log return; episode results are
breadth and decision-quality diagnostics.

## Recomputed formulas

The semantic validator uses exact Decimal accounting and the frozen methods:

```text
scheduled_count = count(episode_register)
status_count[s] = count(row.status == s)

fill_fraction_5d =
  sum(filled_notional_within_5_sessions)
  / sum(intended_notional for origins with a recorded trade intent)

daily_active_log_return[t] =
  ln(1 + proposal-stress return[t]) - ln(1 + comparator return[t])

annualised_active_return_vs_comparator =
  exp(252 * mean(daily_active_log_return[t])) - 1

maximum_drawdown =
  max((prior_peak_NAV - current_NAV) / prior_peak_NAV)
```

NAV and Modified Dietz are defined in `branch-nav-v1`. The 63-session episode
diagnostic separately uses relative wealth,
`(1 + r_stress) / (1 + r_comparator) - 1`. The primary circular
moving-block-bootstrap uses the exact protocol stored in
`evaluator-config-v1` and echoed in `cohort-statistics-v1`; mismatch is an
integrity failure.

## Operational gate

All are conjunctive:

- at least 30 consecutive complete prospective sessions under one lineage;
- bit-identical replay;
- priced NAV on at least `0.995000` of required days;
- zero unresolved material price, FX, corporate-action, tax, cost, accounting,
  general-data, settlement, and reconciliation defects;
- genuine point-in-time XJO-TR;
- the effective broker-published fee schedule;
- one effective James-ratified risk policy; and
- passing structural and perturbation dependency-isolation evidence.

Passing yields `UNCALIBRATED_STAGING_ELIGIBLE`. Failure yields
`PAPER_ONLY_HOLD`. This gate never claims investment edge.

The aggregate decision is deterministic: an operational failure remains
`PAPER_ONLY_HOLD`; operational pass plus strategy failure is
`HOLD_UNCALIBRATED`; and both passes produce only
`ELIGIBLE_FOR_JAMES_REVIEW`. The evaluator's maximum tier is
`UNCALIBRATED`; James's separate decision is still required.

## Strategy evidence gate

All are conjunctive:

- at least 252 eligible prospective sessions;
- at least 20 matured, pre-registered 63-session episodes; overlap is declared,
  not prohibited;
- all construction, risk, sizing, staging, fill, cost, tax, accounting,
  calendar, benchmark, evaluator, schema, runtime, and code versions fixed;
- positive after-tax/fee/stress-cost continuous active return versus hold and
  genuine XJO-TR;
- positive empirical Type-1 one-sided 90% circular moving-block-bootstrap
  lower bounds for both, using block 10, 100,000 replicates, and the registered
  NumPy 2.1.1 `PCG64DXSM` seed protocol;
- reported two-sided 95% sensitivity intervals for blocks 5 and 20;
- at least `0.950000` of intended notional filled within five sessions;
- zero policy and mandate drawdown breaches;
- every registered origin retained; and
- the frozen candidate-family multiple-testing diagnostic passes.

Passing makes the immutable evidence packet eligible for James's separate
promotion review. It does not itself permit `EVIDENCE_BACKED` language.
An unavailable bootstrap is represented by an explicit status and `null`
bounds, never a placeholder estimate, and therefore cannot pass this gate.

## Fail-closed boundary

Any missing, stale, unresolved, hash-invalid, non-reproducible, non-finite,
future-available, denominator-edited, mixed-version, or semantically
inconsistent input keeps the lower tier. Evaluation is always `PAPER_ONLY`,
uses simulated fills only, cannot mutate live holdings, and has no broker
capability.
