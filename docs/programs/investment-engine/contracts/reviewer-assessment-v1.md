# Reviewer Assessment v1

**Normative wire shape:** [`../schemas/reviewer-assessment-v1.schema.json`](../schemas/reviewer-assessment-v1.schema.json)

## Purpose

One immutable blind first-pass assessment of one frozen ReviewContext/report
candidate. The assessment is qualitative evidence consumed by
`review-eligibility-v1`; it cannot set eligibility, portfolio weights, risk
limits, quantities, staged prices, or execution state.

## Reviewer identity and replay

Every assessment pins agent, model, prompt, and role-rubric identities, semantic
versions, and content hashes. The reviewer receives only the exact context
bytes/hash and report candidate hash. Database/network tools and peer first
passes are unavailable.

The dossier harness resolves the complete role-keyed identity tuple against an
exact frozen allowlist; equality among producer-supplied copies is not proof.
Production replaces the synthetic patterned fixture hashes with an immutable
review-cycle bundle registry whose agent/model/prompt/rubric content hashes are
computed from stored bytes and approved by James.

The root uses the programme canonical-hash envelope: RFC 8785 JSON, SHA-256, with
only `/canonical_hash/payload_sha256` excluded before hashing. Exact retry with
the same ID/hash is idempotent; a different payload for the same assessment ID is
an integrity error.

## Roles and verdicts

Required roles:

```text
evidence_claims
valuation_scenarios
thesis_adversary
portfolio_risk_fit
implementation_liquidity_tax
```

Verdicts are `PASS`, `CHALLENGE`, `FAIL`, or `ABSTAIN`. Confidence is descriptive,
not a probability, vote, score, or sizing input. An abstention requires a reason
and blocks eligibility under `review-eligibility-v1`.

## Findings and resolution

Every finding has stable identity/code, severity, status, claim/evidence
references, required action, and uncertainty. `OPEN` has no resolution reference.
`ACCEPTED_RISK` and `RESOLVED` require an immutable James/governance resolution
record and hash. Every claim/evidence reference resolves inside the exact
ReviewContext and the evidence must support one of the referenced claims.

The fixture harness allowlists the one synthetic James resolution as an exact
finding/status/severity/reference tuple, checks `resolution_type == status`, and
requires `resolved_at <= submitted_at`. Production uses a separate append-only
governance-resolution artifact/table so later resolutions never mutate a signed
first pass. Editing a finding is forbidden; later changes append a resolution or
new finding.

Model A, legacy signal/allocator outputs, and broker capability are absent from
the structured payload. Source prose remains inert data.
