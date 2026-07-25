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

### Comparison semantics (normative)

`NUMERIC_LIMIT` does not carry a single comparison direction. Every numeric
check MUST declare a `comparison`, and the recorded direction is what the
validator asserts. A check that violates its declared comparison is invalid.

`REDUCE` is not an exemption. A reduction is valid only if the post-reduction
`applied_value` satisfies the limit; the pre-reduction `observed_value` may
legitimately sit outside it. `EXACT` and `CAP_APPLIED` are identity and cap
proofs and assert on the same value under either action.

| `comparison` | Asserted on `PASS` | Asserted on `REDUCE` |
|---|---|---|
| `MINIMUM` | `observed_value >= limit_value` | `applied_value >= limit_value` |
| `MAXIMUM` | `observed_value <= limit_value` | `applied_value <= limit_value` |
| `EXACT` | `observed_value == limit_value` | `observed_value == limit_value` |
| `CAP_APPLIED` | `applied_value <= limit_value` | `applied_value <= limit_value` |

`limit_value` is never producer-chosen: it MUST equal the value the registry
below resolves for that code. `source_ref` names the evidence artifact the check
cites and is not by itself the limit's source — `ADV_PARTICIPATION` and `FEES`
combine a cited quantity with a fraction frozen by this policy, and
`LOSS_HEADROOM` cites the risk mandate while its bound is this policy's.
`observed_value` is likewise a recomputed quantity, not an attestation:
`ADV_PARTICIPATION` and `SPREAD` are recomputed from the proposal candidate row,
not read back from the check.

Unqualified `limits.*` below is this policy's `limits` object; risk-policy
fields are named explicitly.

| Code | `comparison` | `limit_value` resolves from |
|---|---|---|
| `TARGET_NOTIONAL` | `EXACT` | proposal target notional for the asset |
| `AVAILABLE_CASH` | `CAP_APPLIED` | snapshot cash x (1 - `limits.available_cash_reserve_fraction`) |
| `ISSUER` | `MAXIMUM` | risk policy `portfolio_limits.max_issuer_weight` |
| `CORPORATE_GROUP` | `MAXIMUM` | risk policy `portfolio_limits.max_corporate_group_weight` |
| `SINGLE_NAME` | `MAXIMUM` | risk policy `portfolio_limits.max_single_name_weight` |
| `SECTOR` | `MAXIMUM` | risk policy `portfolio_limits.max_sector_weight` |
| `THEME` | `MAXIMUM` | risk policy `portfolio_limits.max_theme_weight` |
| `PORTFOLIO_LOSS_AT_STOP` | `MAXIMUM` | risk policy `loss_limits.max_portfolio_loss_at_stop_fraction` |
| `GROSS_EXPOSURE` | `MAXIMUM` | risk policy `portfolio_limits.max_gross_weight` |
| `NET_EXPOSURE` | `MAXIMUM` | risk policy `portfolio_limits.max_net_weight` |
| `RESERVATIONS` | `MAXIMUM` | snapshot reserved fraction (see coverage note) |
| `TURNOVER` | `MAXIMUM` | risk policy `portfolio_limits.max_daily_turnover_weight` |
| `ADV_PARTICIPATION` | `MAXIMUM` | candidate ADV x `limits.maximum_order_adv_fraction` |
| `SPREAD` | `MAXIMUM` | `limits.maximum_spread_fraction` |
| `LOSS_HEADROOM` | `MINIMUM` | `limits.minimum_loss_headroom_aud` |
| `BOARD_LOT` | `MINIMUM` | effective board lot from the classification snapshot |
| `MINIMUM_ORDER` | `MINIMUM` | `limits.minimum_order_aud` |
| `FEES` | `MAXIMUM` | approved notional x `limits.maximum_fee_fraction` |

### Harness coverage (honest scope)

The dossier validator resolves `limit_value` for 17 of the 18 numeric codes and
recomputes `observed_value` for 16. The residue is stated rather than implied:

- `RESERVATIONS.limit_value` has **no ratified source**. No policy expresses a
  reservation cap, so the check is currently an identity against the frozen
  snapshot and is not a binding constraint. Ratifying a reservation cap is an
  S07 requirement, not a validator gap.
- `LOSS_HEADROOM.observed_value` is producer-supplied. Its `MINIMUM` direction
  is asserted, so a headroom below the ratified floor is rejected, but the
  headroom quantity itself is not yet derived from the loss-budget arithmetic;
  that derivation is an S07 implementation requirement.
- `applied_value` is asserted only where a comparison consumes it (`CAP_APPLIED`,
  and any `REDUCE`). For the remaining checks it is wire-shape validated only.

An implementation MUST NOT read this section as permission to leave those values
unconstrained at runtime; it records what the dossier harness proves today.

### Liquidity-cap precedence (normative)

Where this policy and `risk-policy-v1` both express a liquidity cap, **this
policy is authoritative** and the risk policy's value is a non-binding mandate
ceiling. The binding ADV cap is `limits.maximum_order_adv_fraction`; the binding
spread cap is `limits.maximum_spread_fraction`. An implementation that resolves
the ADV cap from `risk-policy-v1.liquidity_limits.max_order_adv_fraction`
permits a materially larger order than this policy allows and is non-conforming.
Where the two disagree, the stricter value MUST additionally be honoured, and
the divergence is reported, never silently resolved.

This precedence is scoped to caps both policies express. Liquidity limits with
no counterpart here — `liquidity_limits.min_adv_aud`,
`max_fill_participation_fraction` and `max_price_age_seconds` — remain resolved
from `risk-policy-v1`.

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
