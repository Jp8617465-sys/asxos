# Staging Policy v1

**Normative wire shape:** [`../schemas/staging-policy-v1.schema.json`](../schemas/staging-policy-v1.schema.json)

## Purpose

`staging-policy-v1` is the James-ratified deterministic policy for turning an
eligible `SIZED` decision into an exact, expiring, non-routable staged-order set.
It owns limit-price arithmetic, stage fractions, earliest eligible event, expiry,
freshness, and invalidation. It does not own portfolio weights or quantities and
cannot increase the sizing decision.

## Deterministic construction

- Only `LIMIT` representations are permitted.
- The reference price comes from the sizing lineage and must still satisfy the
  configured freshness limit.
- A buy limit is the reference price multiplied by
  `(1 + max_adverse_limit_fraction)`; a sell limit uses
  `(1 - max_adverse_limit_fraction)`.
- The result rounds toward the safer side to the configured ASX tick size.
- Stage fractions are James-ratified, sum exactly to `1.000000`, and are applied
  to the sized quantity in sequence. Integer/board-lot remainders are assigned
  by the declared remainder rule; staging never changes the total.
- No stage precedes the next eligible ASX market event. Stage intervals cannot
  overlap, and expiry follows the last stage.

## Invalidation and failure

Any expiry, stale price/FX/holdings/tax/liquidity input, changed report/review/
monitor/evaluator/policy/proposal/sizing hash, open critical/high finding,
unprocessed material event, gate regression, or arithmetic mismatch invalidates
the entire set. There is no partial route or fallback order.

## Firewall

The policy fixes `PAPER_ONLY`, `non_executable=true`, and system terminal state
`ORDER_STAGED`. It contains no broker, account, route, credential, submission,
modification, cancellation, or external order identifier. James acts outside
ASXOS.
