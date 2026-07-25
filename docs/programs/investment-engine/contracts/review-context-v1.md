# ReviewContextV1

**Normative wire shape:** [`../schemas/review-context-v1.schema.json`](../schemas/review-context-v1.schema.json)

## Purpose

Give every reviewer the same immutable, point-in-time, model-independent packet. Reviewers receive
the payload and its SHA-256 hash; they do not query Supabase directly.

## Allowlist

- Target thesis and broker-report version.
- Claim register, scenarios, catalysts, falsifiers, and discipline wrapper.
- Verified evidence snapshots with tier, observation, retrieval, and data-as-of times.
- Point-in-time price, fundamentals, financial statements, FX, benchmark, market, regulatory, and
  news inputs.
- Holdings, tax lots, portfolio exposures, and the ratified risk-policy snapshot.
- Explicit missing/stale states and freshness policy.

## Forbidden inputs

Signals, SHAP, `prob_up`, model expected return, Model A/version identifiers, rebalance runs, and
legacy allocator scores are structurally absent. A builder may not include them under generic
`metadata` or `extra` fields.

## Freeze

The controlled loader:

1. Resolves all values as they were knowable at `context_as_of`.
2. Rejects future-observed or unavailable inputs.
3. Enforces `report.data_as_of <= report.created_at <= context_as_of <= generated_at`,
   `evidence.data_as_of <= observed_at <= retrieved_at <= context_as_of`, and
   `holding.source_as_of <= portfolio.as_of <= context_as_of`.
4. Produces explicit freshness and missing-data states. Required freshness inputs
   are unique and complete. `age_seconds` is recomputed as the integer difference
   between `context_as_of` and the frozen source `observed_at`; `FRESH` is valid
   only at or below the policy maximum, `STALE` only above it, `MISSING` only
   without a resolvable source, and future-dated inputs are invalid.
5. Computes `context_sha256` over RFC 8785 bytes after removing the complete
   `/context_sha256` and `/canonical_hash` members. This is the exact reviewer
   packet digest.
6. Persists the exact snapshot before review begins.

The report claim register is reproduced exactly. Every context claim and scenario
evidence ID must resolve inside the same frozen packet; dangling or cross-packet
references fail closed.

The full stored artifact then uses the programme root `canonical_hash` envelope,
computed after setting `context_sha256` and removing only
`/canonical_hash/payload_sha256`. The two digests have different domains and
must not be equated. Any data/rubric change creates a new review cycle and both
hashes change.
