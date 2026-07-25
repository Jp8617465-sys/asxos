# Fill Model v1

`fill-model-v1` freezes conservative paper-execution semantics. It is a
simulation policy, not a broker adapter.

**Machine contract:** [`fill-model-v1.schema.json`](../schemas/fill-model-v1.schema.json)

## Frozen rules

- no same-session fills;
- actual later eligible market events only, resolved against the frozen
  [`trading-calendar-v1`](trading-calendar-v1.md);
- quote data is preferred; daily bars use adverse, trade-through-only treatment;
- a touched-but-not-traded-through limit does not fill when sequence is unknown;
- volume participation and order ADV caps are conjunctive;
- partial fills, halts, auctions, stale/missing volume, expiry, and cancellation
  are explicit;
- base and stress costs separately specify spread, slippage, impact, and minimum
  cost floors;
- tick and board-lot rules come from an effective-dated security master; and
- fee schedules are selected by simulated fill time, not evaluator start time.

Every parameter, data-class requirement, rounding mode, and incomplete-state
action is fixed and James-ratified where it could change a capital figure.
