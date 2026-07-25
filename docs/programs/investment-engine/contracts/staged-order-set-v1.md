# Staged Order Set v1

`staged-order-set-v1` is a deterministic, expiring, paper-only representation
of proposed orders derived from one valid `SIZED` decision. “Staged” means
recorded for James to inspect; it never means sent, approved, or executable.

**Machine contract:** [`staged-order-set-v1.schema.json`](../schemas/staged-order-set-v1.schema.json)

**Fixture:** [`staged-order-valid.json`](../fixtures/staged-order-valid.json)

## Admission gate and lineage

The staging service MUST fail closed unless all of the following resolve by
typed identifier and canonical hash:

- a `sizing-decision-v1` with `status: SIZED` and
  `eligible_for_staging: true`;
- the exact proposal, construction policy, and risk policy used by sizing;
- a James-ratified, effective `staging-policy-v1`;
- a complete prospective evaluation under the referenced
  `evaluation-policy-v1`; and
- the exact James-authored `promotion-decision-v1`.

The staged-set artifact embeds the completed `SIZE_DECIDED` predecessor lineage.
Its own staging policy and promotion decision are top-level inputs, and it
cannot embed a `staged_order_set_ref` to itself. After the set is canonically
hashed, a separate atomic `investment-case-lineage-v1` artifact advances the
case to `ORDER_STAGED` and carries every upstream research, review, monitor,
evaluation, proposal, sizing, staging-policy, promotion, and staged-set
reference. Hash mismatch, gate regression, withdrawal, staleness, or ambiguity
invalidates the entire set.

Every staged set has passed the operational gate. `EVIDENCE_BACKED` additionally
requires the strategy gate to pass and the referenced James decision to be
`APPROVE_EVIDENCE_BACKED_LANGUAGE`. `UNCALIBRATED` and `PAPER_ONLY` remain
visibly constrained to the matching James decision and evidence language.

## Deterministic staging transform

For each sized line, exact `NUMERIC(18,6)` Decimal arithmetic MUST:

1. read the policy's maximum adverse price fraction;
2. calculate the raw buy or sell limit from the time-stamped reference price;
3. round only in the policy direction to the recorded market tick;
4. allocate quantity by the policy's ordered stage fractions and board-lot
   rules, assigning the residual deterministically to the final stage;
5. derive each `not_before` from the policy session offsets and locked market
   calendar; and
6. derive each stage and set expiry from the policy, never from generated text.

The semantic validator MUST prove stage fractions sum to `1.000000`, stage
quantities sum to the sized quantity, timestamps increase without overlap,
limit/tick arithmetic reconciles, totals reconcile, and expiry follows the last
stage.

## Absolute execution firewall

The closed schema has no account connectivity, credentials, remote endpoint,
routing, submission, modification, cancellation, or external identifier.
External connectivity, automatic approval, and generative order fields are
fixed false; `user_approval` is always `REQUIRED_NOT_GRANTED`. Model A cannot
create, rank, price, size, alter, approve, or transmit any staged item. The v1
workflow ends at `ORDER_STAGED`.
