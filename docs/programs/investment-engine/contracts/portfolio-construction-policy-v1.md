# Portfolio Construction Policy v1

**Normative wire shape:** [`../schemas/portfolio-construction-policy-v1.schema.json`](../schemas/portfolio-construction-policy-v1.schema.json)

## Purpose

`portfolio-construction-policy-v1` is the James-ratified, immutable policy that
turns eligible research cases into target portfolio weights. It closes the gap
between qualitative thesis/review and deterministic sizing. An LLM never writes,
suggests, ranks, or changes a target weight.

## Risk-budget-at-stop method

V1 uses an expected-return-free construction rule:

```text
stop_distance_fraction =
  abs(reference_price_aud - thesis_stop_price_aud) / reference_price_aud

effective_stop_distance =
  max(stop_distance_fraction, stop_distance_floor_fraction)

uncapped_target_weight =
  per_case_risk_budget_fraction / effective_stop_distance
```

The producer then applies the policy's cap waterfall, in order, without allowing
a later check to increase an earlier result:

```text
eligibility
  -> classification
  -> stop-risk
  -> issuer
  -> corporate group
  -> single-name
  -> sector
  -> theme
  -> portfolio loss-at-stop
  -> gross exposure
  -> net exposure
  -> cash reserve
  -> turnover
  -> reservations
  -> liquidity/ADV/spread
  -> tax-loss and tax-liability constraints
  -> minimum meaningful target
```

The final target is the smallest permissible weight. Cash is the exact remainder.
The proposal records the value before and after every numeric cap. Classification
is a Boolean precondition immediately after eligibility; it is never represented
as a fabricated numeric cap. Classification must be complete, admissible,
effective at the proposal decision, available by the knowledge cutoff, and no
older than the policy's explicit freshness window.

## Candidate selection and ties

- Only cases with an exact, complete and admissible security-classification
  snapshot row, the required deterministic review eligibility, current report,
  clear monitor watermark, required evaluator state, and fresh point-in-time
  inputs may enter. A present empty `theme_ids` array is complete known
  membership; a missing or ambiguous theme classification is not.
- `ALL_ELIGIBLE` is the only V1 selection method. The policy may cap the number of
  positions; when an otherwise equal boundary must be resolved, canonical
  `asset_id` ascending is the sole tie-break.
- Model scores, probabilities, confidence, prose conviction, and Model A output
  are forbidden ranking or weight inputs.
- Existing holdings are evaluated with the same rules; no incumbent receives an
  undocumented preference.

## Tax, turnover, and fallbacks

The proposal consumes current holdings, lots, cash, sector exposure, liquidity,
fees, and deterministic tax consequences. Cash is used before a discretionary
sale. Required sales use the tax engine's versioned lot-selection result; the
constructor does not reproduce tax math.

Missing policy, stop, price, holdings, lots, FX, liquidity, fee, tax, report,
review, monitor, or evaluator lineage fails closed. An infeasible portfolio
returns a typed rejection or `HOLD_CASH`; it never relaxes a cap, infers a value,
or falls back to the legacy allocator.

## Authority and immutability

Every numeric value is supplied and ratified by James. A policy version is
effective-dated and content-hashed. Any change creates a new version and a new
evaluator/proposal lineage. This policy has no broker field or execution effect.
