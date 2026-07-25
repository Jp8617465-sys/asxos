# Portfolio Proposal v1

**Normative wire shape:** [`../schemas/portfolio-proposal-v1.schema.json`](../schemas/portfolio-proposal-v1.schema.json)

## Purpose

`portfolio-proposal-v1` is the deterministic output of the James-ratified
`portfolio-construction-policy-v1`. It converts eligible governed investment
cases and the current portfolio into desired weights by the frozen
risk-budget-at-stop method. It is evidence for sizing, not an order, approval, or
broker instruction.

## Required lineage and inputs

The proposal embeds the completed `EVALUATION_FROZEN` predecessor lineage and
carries the exact construction/risk-policy references. It cannot embed a
`portfolio_proposal_ref` to itself. After the proposal is canonically hashed, a
separate atomic `investment-case-lineage-v1` artifact advances the case to
`PROPOSAL_BUILT` and references that proposal hash. It consumes:

- current governed thesis/revision and immutable report;
- deterministic review eligibility and current monitor watermark;
- frozen evaluator configuration, evaluation policy, and gate decision;
- current holdings, tax lots, cash, NAV, sector exposures, and external flows;
- point-in-time prices, stop prices, FX, liquidity, ADV, spread, fees, and
  deterministic tax-engine results; and
- the exact immutable security-classification snapshot and its complete,
  admissible asset row, including security, issuer, corporate group, sector,
  sorted themes, board lot, and effective tick rule; and
- source observation/publication/availability timestamps and content hashes.

Missing or stale input is explicit and fails closed.
Missing, ambiguous, incomplete, inadmissible, ineffective, or hash-mismatched
classification is `REJECTED_INCOMPLETE_INPUT`; the builder never falls back to
labels or inferred taxonomy.

## Deterministic proposal builder

For every eligible candidate, the builder recomputes:

```text
stop_distance_fraction =
  abs(reference_price_aud - thesis_stop_price_aud) / reference_price_aud

effective_stop_distance =
  max(stop_distance_fraction, policy.stop_distance_floor_fraction)

uncapped_target_weight =
  policy.per_case_risk_budget_fraction / effective_stop_distance
```

It then applies every cap in the construction policy's fixed waterfall. Every
numeric check records before, limit, after, action, and source; the classification
check records a true Boolean precondition and the exact snapshot source. No later
cap may increase weight. Final target weights plus cash equal exactly `1.000000`;
current/delta arithmetic is Decimal-exact. Summary exposure arrays recompute
issuer, corporate-group, sector and overlapping-theme weights plus total
portfolio loss-at-stop. Empty, explicitly known theme membership is valid and
produces no theme exposure row. Each target digest covers its complete canonical
payload and is the identity consumed by sizing. Candidate ties use canonical
asset ID only.

AI/LLMs may supply cited qualitative research and review, but may never supply a
numeric weight, stop-risk calculation, cap, quantity, or tie-break. The legacy
signal allocator is not a producer.

## Outcomes

- `BUILT`: at least one included target, exact cash remainder, complete inputs,
  and `eligible_for_sizing=true`.
- `HOLD_CASH`: policy-valid empty/infeasible eligible universe; no targets and no
  sizing.
- `REJECTED_NO_CONSTRUCTION_POLICY`
- `REJECTED_NO_RISK_POLICY`
- `REJECTED_INCOMPLETE_INPUT`
- `REJECTED_INFEASIBLE`

Every non-`BUILT` outcome has no target lines and
`eligible_for_sizing=false`. Diagnostics and candidate inputs remain available
without emitting a partial portfolio. Policy and classification references are
nullable only where the typed rejection means that input could not be resolved.

## Boundaries

The payload fixes `PAPER_ONLY`, exact six-decimal strings, deterministic math,
and `non_executable=true`. It contains no quantity, route, venue instruction,
account, credential, or external order identity.
