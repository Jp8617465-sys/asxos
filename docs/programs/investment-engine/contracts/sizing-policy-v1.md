# Sizing Policy v1

`sizing-policy-v1` is the immutable deterministic policy applied between a
portfolio proposal and `sizing-decision-v1`.

**Machine contract:** [`sizing-policy-v1.schema.json`](../schemas/sizing-policy-v1.schema.json)

## Required semantics

The method is `POLICY_CAPPED_BOARD_LOT`. Constraints execute in the registered
order:

```text
classification
  -> target notional
  -> available cash
  -> issuer
  -> corporate group
  -> single-name
  -> sector
  -> theme
  -> portfolio loss-at-stop
  -> gross exposure
  -> net exposure
  -> reservations
  -> turnover
  -> ADV participation
  -> spread
  -> loss headroom
  -> tick rule
  -> board lot
  -> minimum order
  -> fees
```

Classification and tick-rule checks are Boolean preconditions. All other checks
are numeric limit proofs. Numeric steps may only pass or reduce a quantity; no
step can increase the proposal target. Tick-rule validation occurs immediately
before board-lot handling, and fees are always the final check.

Numeric limits use exact six-decimal strings. Construction and risk policies
remain authoritative for portfolio limits; this policy freezes sequencing,
liquidity caps, cash reserve, minimum order, fee guard, rounding, and rejection
behavior. Missing or ambiguous policy input yields `REJECTED_NO_POLICY`;
breach after reduction yields `REJECTED_POLICY_VIOLATION`. There is no implicit
default.

The sizing run must use the same complete classification snapshot recorded by
the proposal. The exact asset row supplies immutable security, issuer,
corporate-group, sector, sorted theme membership, board-lot and tick-rule
identity. Missing, ambiguous, incomplete, inadmissible, or hash-mismatched
classification produces `REJECTED_NO_POLICY`; no quantity is emitted.
An empty `theme_ids` array is valid when it is explicitly present in a complete
classification row.

The policy is James-ratified, versioned, `PAPER_ONLY`, deterministic,
non-executable, and isolated from analytical ranking outputs. A changed limit,
order, rounding rule, or reference starts a new evaluator lineage.
