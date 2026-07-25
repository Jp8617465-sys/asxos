# Promotion Decision v1

**Normative wire shape:** [`../schemas/promotion-decision-v1.schema.json`](../schemas/promotion-decision-v1.schema.json)

## Purpose

`promotion-decision-v1` records James's explicit decision about output visibility
and evidence language after deterministic gate evidence has been recomputed. It
is not an order approval, broker instruction, trade decision, or execution
permission.

## Decisions

- `HOLD_PAPER_ONLY`: keep the artifact internal and non-actionable.
- `APPROVE_UNCALIBRATED_VISIBILITY`: operational gate passed; James permits a
  visible `UNCALIBRATED` staged decision-support artifact.
- `APPROVE_EVIDENCE_BACKED_LANGUAGE`: operational and strategy gates passed;
  James permits `EVIDENCE_BACKED` language.
- `REJECT_PROMOTION`: James rejects the requested visibility/language change.

The service independently resolves the frozen evaluation policy and gate-decision
hash. `APPROVE_UNCALIBRATED_VISIBILITY` requires a passed operational gate.
`APPROVE_EVIDENCE_BACKED_LANGUAGE` requires both gates, complete evidence, and the
same fixed lineage used by the evaluation.

## Boundaries

Promotion never changes portfolio weights, quantities, order arithmetic, a
staged-order payload, or an investment-case lineage in place. A later withdrawal
is a new decision linked to the prior one. No decision grants broker connectivity
or implies an order was placed or filled.
