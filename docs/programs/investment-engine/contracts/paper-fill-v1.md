# Paper Fill v1

`paper-fill-v1` records one deterministic simulated fill at an actual later
eligible market event.

**Machine contract:** [`paper-fill-v1.schema.json`](../schemas/paper-fill-v1.schema.json)

Every fill resolves the order, fill-model version, market-event hash,
point-in-time quote/bar/volume input, fee schedule, and cost scenario. It
decomposes reference price, spread, slippage, impact, fee, filled quantity,
gross consideration, and total cash effect using Decimal arithmetic.

Every fill must satisfy, and a conforming producer must prove:

1. fill time is no earlier than the order's first eligible event;
2. cumulative filled quantity never exceeds the order;
3. quantity does not exceed the frozen participation cap;
4. the limit and conservative trade-through rule pass;
5. money and cost components reconcile exactly; and
6. `simulated` and `non_executable` remain true.

Missing quotes, ambiguous bars, halts, stale volume, invalid chronology, or an
unknown fee schedule yields no fill rather than an optimistic fallback.

## Where those proofs are enforced

**The dossier harness proves only 5 and 6.** The semantic validator recomputes
`gross_consideration_aud = filled_quantity × fill_price_aud`, the signed
`total_cash_effect_aud` including `fee_aud`, and the
spread/slippage/impact decomposition against `reference_price_aud`; and the
schema pins `controls.simulated` and `controls.non_executable` to `const: true`,
which is the whole of requirement 6.

**Requirements 1–4 are enforced by the fill service built in S09** and by its
acceptance evidence — AC-37 (only a real later eligible event under the frozen
base/stress model; same-session, touch-only, future and overfill impossible) and
AC-38 (partial/no-fill/expiry/cancellation/settlement as complete append-only
state machines). Beyond the programme-wide numeric/timestamp shape lint, the validator evaluates none of `filled_at`,
`cumulative_filled_quantity`, `participation_fraction`, `eligible_volume` or
`market_event`, and resolves no order for a chronology comparison.
`limit_rule_passed` is a schema `const: true` — a pinned producer declaration
that the rule held, not a derivation of it from the quote/bar input. A fill
fixture that overfills its order, breaches the participation cap or trades
through its limit validates today.
