# ThesisProposalV1

**Normative wire shape:** [`../schemas/thesis-proposal-v1.schema.json`](../schemas/thesis-proposal-v1.schema.json)

This contract extends the existing `ThesisProposal`, `ReportSection`, and `ReportFigure` Pydantic
models with an explicit versioned envelope. It does not replace their prose-only figure/provenance
guards.

## Invariants

- `symbol` is uppercase and ends `.AU` or `.US`; it must exactly equal the agent-run subject.
- `flavour` is `individual_equity` or `etf_fund`.
- Every monetary figure is a decimal string with provenance.
- `cited` figures require evidence; `derived` figures require evidence and a displayed formula.
- `james_input` is human-only and cannot be emitted by an agent.
- Entry lower is not greater than entry upper.
- The normative v1 payload has no Model A or `monitor_only` field. A baseline
  Pydantic passive-monitor extension is rejected by the closed v1 adapter.
  Existing historical values remain only in the checksummed read-only archive;
  they never enter a basis, report, review, target, sizing, evaluator, or staged
  artifact.
- Section kinds are unique.
- At least one evidence citation is required.
- All nested citations participate in logging and materialization verification.
- `timeline_days`, if supplied, is a positive integer.
- The root artifact uses the programme RFC 8785/SHA-256 `canonical_hash`
  envelope; only `/canonical_hash/payload_sha256` is removed while computing it.

## Materialized result

The first consumer creates a governed `research` thesis at `pending_review`, never
an active position. It may preserve the proposal's migration-0040 report sections
as a compatibility projection, but that projection is not an immutable report.
S03 creates `BrokerReportVersionV1` from the exact
proposal/thesis-revision/evidence bytes. Human approval remains separate and never
grants execution authority.

## Failure outputs

Use stable typed codes:

```text
UNKNOWN_CONTRACT_VERSION
UNAUTHORIZED_PRODUCER
SUBJECT_MISMATCH
MALFORMED_CITATION
MISSING_EVIDENCE
SPECULATIVE_EVIDENCE
FORBIDDEN_JAMES_INPUT
INVALID_DECIMAL
INVALID_REPORT_SHAPE
ALREADY_ACTED_CONFLICT
```
