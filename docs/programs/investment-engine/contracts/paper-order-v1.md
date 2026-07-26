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

## Where the causality chain and state machine are enforced

**By the order service built in S09, not by the dossier harness.** The governing
acceptance evidence is AC-37 (no same-session, touch-only or future event may
become an order's first eligible event) and AC-38 (the append-only lifecycle,
including partial, no-fill, expiry and cancellation, as a complete state
machine).

The semantic validator validates this contract against its schema, resolves its
typed references and applies the programme-wide `created_at`/`data_as_of`
chronology rule — but it reads none of `knowledge_cutoff`, `intent_recorded_at`,
`order_recorded_at`, `first_eligible_market_event_at` or `state` on this
contract, and never evaluates the ordering above or any transition. An order
whose first eligible event precedes its own recording, or which jumps straight
from `RECORDED` to `FILLED`, validates today. The tick/board-lot and limit-price
recomputation the harness does perform belongs to `staged-order-set-v1`, which is
a different artifact.
