# Paper Fill v1

`paper-fill-v1` records one deterministic simulated fill at an actual later
eligible market event.

**Machine contract:** [`paper-fill-v1.schema.json`](../schemas/paper-fill-v1.schema.json)

Every fill resolves the order, fill-model version, market-event hash,
point-in-time quote/bar/volume input, fee schedule, and cost scenario. It
decomposes reference price, spread, slippage, impact, fee, filled quantity,
gross consideration, and total cash effect using Decimal arithmetic.

The semantic validator proves:

- fill time is no earlier than the order's first eligible event;
- cumulative filled quantity never exceeds the order;
- quantity does not exceed the frozen participation cap;
- the limit and conservative trade-through rule pass;
- money and cost components reconcile exactly; and
- `simulated` and `non_executable` remain true.

Missing quotes, ambiguous bars, halts, stale volume, invalid chronology, or an
unknown fee schedule yields no fill rather than an optimistic fallback.
