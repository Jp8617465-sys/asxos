# Sizing Decision v1

`sizing-decision-v1` records the deterministic conversion of one eligible
portfolio target into policy-capped paper quantities. It is an auditable
decision, never an order.

**Machine contract:** [`sizing-decision-v1.schema.json`](../schemas/sizing-decision-v1.schema.json)

**Fixtures:** [`sizing-valid.json`](../fixtures/sizing-valid.json) ·
[`sizing-origin-valid.json`](../fixtures/sizing-origin-valid.json) ·
[`sizing-no-policy.json`](../fixtures/sizing-no-policy.json)

## Preconditions and lineage

The service MUST resolve the complete typed case lineage, the exact
`portfolio-proposal-v1`, the James-ratified construction, risk, and
`sizing-policy-v1` policies, and the proposal's point-in-time portfolio snapshot.
It MUST reuse the proposal's exact typed
`security-classification-snapshot-v1` reference. Identifiers without matching
canonical hashes are invalid. A successful sizing artifact embeds the completed
`PROPOSAL_BUILT` predecessor lineage and therefore has no
`sizing_decision_ref` to itself. After the artifact is canonically hashed, a
separate atomic `investment-case-lineage-v1` artifact advances the case to
`SIZE_DECIDED` and references that sizing-decision hash. A rejection preserves
the last completed upstream lineage stage rather than claiming that sizing
succeeded; unresolved-input rejection fields, including the classification
reference, are nullable.

There is no implicit or “latest” policy. A missing, ambiguous, expired, or
hash-mismatched construction, risk, or sizing policy produces
`REJECTED_NO_POLICY`, no line items, and `eligible_for_staging: false`.

## Deterministic calculation

Using exact `NUMERIC(18,6)` Decimal arithmetic, the service MUST:

1. prove the proposal's classification snapshot and asset identity;
2. multiply the proposal target delta by point-in-time portfolio NAV;
3. apply target-notional, cash, issuer, group, single-name, sector, theme,
   portfolio-loss, gross/net, reservation, turnover, ADV, spread, and
   loss-headroom checks in the policy's exact order;
4. prove the price against the effective tick rule, then floor quantity to the
   effective board lot;
5. apply minimum-order and final fee checks;
6. reject the whole decision when no permitted size remains; and
7. recompute cash, issuer/group/sector/theme exposures, portfolio loss at stop,
   turnover, fees, and every line/summary reconciliation.

Each `SIZED` line is exclusively `APPROVED` or `REDUCED`; a rejected line is not
representable. Both rejection states require an empty `line_items` array and
cannot be staging-eligible. A mixed “partially rejected but eligible” payload is
therefore schema-impossible.

Every sized line has a stable `line_id` and `line_item_sha256`. The digest is
SHA-256 over RFC 8785 canonical JSON for that line after excluding only
`line_item_sha256`; `line_id` remains in the preimage. Downstream intents use
both values and must match the approved quantity, notional, side, asset, and
reference price exactly.

The semantic validator MUST additionally prove asset uniqueness, ordered
and complete constraint checks, classification and tick-rule Boolean
preconditions, board-lot divisibility, tick alignment, line/target hashes,
line and summary arithmetic, exposure/loss aggregation, exact hash resolution,
and:

`published_at <= available_at <= knowledge_cutoff <= decision_at <= created_at`

## Hard boundary

Model A and every generative model are structurally outside sizing. They cannot
provide a weight, quantity, limit, cap, tie-break, fee, or override. The closed
schema fixes deterministic Decimal math, forbids implicit defaults and
look-ahead, and keeps the artefact `PAPER_ONLY` and non-executable.
