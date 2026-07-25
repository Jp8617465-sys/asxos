# Paper Order v1

`paper-order-v1` is an evaluator-internal simulated order derived from one valid
paper intent under a frozen fill model.

**Machine contract:** [`paper-order-v1.schema.json`](../schemas/paper-order-v1.schema.json)

## Causality

`knowledge_cutoff <= intent_recorded_at < order_recorded_at <
first_eligible_market_event_at`. The order fixes quantity, limit price,
effective security-master tick/lot data, participation cap, first eligible
event, expiry, and source hashes. It never reads a same-session or future-known
price.

The state machine is append-only:

`RECORDED -> ELIGIBLE -> PARTIALLY_FILLED -> FILLED | EXPIRED |
CANCELLED_BY_PROTOCOL`.

This object is not `staged-order-set-v1`, is never shown as a real order, and
contains no broker route, account, endpoint, credential, or external order ID.
