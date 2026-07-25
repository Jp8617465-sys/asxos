# Review Eligibility v1

**Normative wire shape:** [`../schemas/review-eligibility-v1.schema.json`](../schemas/review-eligibility-v1.schema.json)

## Purpose

`review-eligibility-v1` is the deterministic close record for one blind review
cycle over one immutable report candidate and `ReviewContextV1`. It is the only
contract that may establish `PAPER_ELIGIBLE`; reviewer prose, verdict counts,
confidence, or a majority vote cannot do so.

## Deterministic synthesis

Exactly one first-pass assessment is required for each role:

```text
evidence_claims
valuation_scenarios
thesis_adversary
portfolio_risk_fit
implementation_liquidity_tax
```

The service verifies each assessment hash, role, context hash, report candidate
hash, prompt/model/rubric identity, and blind-first-pass control before synthesis.
In v1, `report_candidate_sha256` is exactly the canonical broker-report root hash;
a distinct blinded transform is forbidden until a first-class transform artifact
defines and hashes its bytes. Every downstream lineage must repeat the exact
investment-case ID, report/context identities, and eligibility hash.

- Missing, stale, future-dated, contradictory, or hash-invalid context yields
  `BLOCKED`.
- A missing mandatory role leaves the cycle incomplete; no eligibility record is
  emitted.
- A mandatory-role `ABSTAIN` yields `BLOCKED`. It never counts as a pass.
- Any reviewer `FAIL` or unresolved critical finding yields `FAIL`.
- Any unresolved high finding blocks `PAPER_ELIGIBLE`.
- `PAPER_ELIGIBLE` requires all five non-abstaining assessments, complete/fresh
  context, zero open high/critical findings, and every hard gate true.

Medium/low findings, challenges, accepted risks, resolutions, and dissent remain
visible and hash-linked. Synthesis never edits or downgrades an assessment.
Assessment verdicts, finding counts, freshness state, reviewer identity tuples,
resolution authority, and the decision are recomputed from resolved artifacts;
copied summary fields are never trusted.

## Boundaries

The decision grants permission only to open a prospective paper evaluator. It
does not establish `SHADOW_ACTIVE`, `ADVICE_READY`, sizing, staging, approval, or
execution authority. Model A and broker capability remain structurally absent.
