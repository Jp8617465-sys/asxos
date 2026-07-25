# Risk Policy v1

**Normative wire shape:** [`../schemas/risk-policy-v1.schema.json`](../schemas/risk-policy-v1.schema.json)

## Purpose

`risk-policy-v1` is the immutable James-ratified mandate used by deterministic
portfolio construction and sizing. It contains capital, exposure, liquidity,
loss, and order-size limits only. Operational/statistical evidence thresholds
belong exclusively to `evaluation-policy-v1`.

## Authority and immutability

- James supplies and ratifies every quantitative value. No default is inferred
  from industry practice, history, an LLM, the legacy allocator, or any predictive
  model.
- Exactly one effective policy must match portfolio, paper environment, venue,
  currency, asset class, and decision time.
- A policy ID/version/content hash is immutable. Any change creates a new version
  and resets affected evaluator lineage under the evaluation policy.
- Every capital-domain numeric string has exactly six decimal places and fits
  `NUMERIC(18,6)`. Negative zero and exponent notation are invalid.

## Deterministic limit application

Every applicable cap is evaluated and the most conservative result wins.
Construction records its weight-cap waterfall; sizing repeats quantity/notional
checks after board-lot flooring and fees. A later cap never increases an earlier
result.

The policy covers:

- maximum gross/net, issuer, corporate-group, single-name, sector, theme,
  turnover, and minimum cash;
- minimum ADV, maximum order/filled participation, spread, and price age;
- maximum portfolio loss-at-stop plus position, portfolio, and daily
  loss/drawdown;
- board lot, minimum order notional, cash buffer, fee schedule, and hard-breach
  action.

## Fail closed

Missing, expired, future-effective, ambiguous, unsigned, hash-mismatched,
scope-mismatched, or schema-invalid policy yields a typed rejection and no target,
size, or staged order. This contract is paper-only and has no broker capability.
