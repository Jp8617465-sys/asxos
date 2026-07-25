# Investment Case Lineage v1

**Normative wire shape:** [`../schemas/investment-case-lineage-v1.schema.json`](../schemas/investment-case-lineage-v1.schema.json)

## Purpose

`investment-case-lineage-v1` is the typed, hash-addressed chain that prevents a
portfolio proposal, sizing decision, promotion decision, or staged order from
appearing without a governed research case. It is an audit artifact, not a
recommendation, score, order, approval, or execution record.

The same `caseLineage` definition is embedded by the downstream contracts. A
generic source-name/hash bag is never sufficient for capital lineage.

## Stages

The lineage grows monotonically:

```text
RESEARCH_REVIEWED
  -> EVALUATION_FROZEN
  -> PROPOSAL_BUILT
  -> SIZE_DECIDED
  -> ORDER_STAGED
```

Each stage requires every typed reference from the prior stage:

- `RESEARCH_REVIEWED`: thesis/revision, immutable report candidate or version,
  review context, review cycle, and deterministic eligibility decision.
- `EVALUATION_FROZEN`: current monitor watermark, evaluator configuration,
  evaluation record, and evaluation policy.
- `PROPOSAL_BUILT`: James-ratified construction and risk policies plus the
  deterministic portfolio proposal.
- `SIZE_DECIDED`: immutable sizing decision.
- `ORDER_STAGED`: staging policy, James evidence-language promotion decision, and
  immutable staged-order set.

An exact replay may return the same lineage ID and hash. A changed reference or
hash creates a new lineage version; it never edits the prior chain.

### Artifact-first transition protocol

An artifact never contains a hash reference to itself. Portfolio proposal,
sizing-decision, and staged-order-set payloads embed only the last completed
predecessor lineage. The producer validates and canonically hashes the new
artifact first, then creates a separate immutable lineage artifact that advances
the stage and references the new hash. The artifact write and lineage advance
are atomic. A failed lineage write leaves neither a partial transition nor an
authoritative later-stage state.

## Hashing

Every contract uses RFC 8785 canonical JSON and SHA-256. The digest is calculated
after removing exactly `/canonical_hash/payload_sha256`; all other fields,
including the exclusion rule, are hashed. The dossier harness recomputes root
fixture hashes and rejects drift. Opaque upstream references remain synthetic
only when no in-dossier fixture represents that upstream artifact.

## Authority and boundaries

- James alone ratifies construction, risk, evaluation, staging, and promotion
  policy.
- Model A, signals, SHAP, legacy allocator scores, and signal-ranked opportunity
  cost are absent from every lineage reference and producer.
- No lineage stage grants broker connectivity or execution authority.
- `ORDER_STAGED` is the system terminal stage. It does not mean submitted,
  placed, filled, or reflected in live holdings.
- Missing, stale, ambiguous, hash-mismatched, or future-effective references fail
  closed and produce no later-stage lineage.
