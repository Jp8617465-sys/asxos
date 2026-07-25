# Evaluation Origin v1

`evaluation-origin-v1` is the immutable record of one scheduled prospective
decision origin before any outcome is known.

**Machine contract:** [`evaluation-origin-v1.schema.json`](../schemas/evaluation-origin-v1.schema.json)

## Invariants

- `prospective` is true and `reconstructed` is false for gate-eligible origins.
- `published_at <= available_at <= knowledge_cutoff <= opened_at`.
- The schedule sequence, candidate family, dependency group, and every overlap
  group are recorded before maturation.
- The five branch identities and their identical starting-state hash are fixed.
  `starting_state_hash_basis` is
  `PORTFOLIO_SNAPSHOT_CANONICAL_HASH`: the preimage is the RFC 8785 canonical
  payload of the unique
  [`portfolio-snapshot-v1`](portfolio-snapshot-v1.md) manifest artifact,
  excluding only `/canonical_hash/payload_sha256`. The origin and every branch
  copy that artifact's `canonical_hash.payload_sha256`; a logical snapshot ID
  may never be reused for a later revision.
- Portfolio, lots, cash, proposal, report, review, construction, policy,
  benchmark, trading-calendar, price, FX, fee, tax, and action snapshots are
  content-addressed.
- An `OPEN` origin contains exactly one typed `PORTFOLIO`, `PROPOSAL`,
  `BENCHMARK`, `SIZING`, `TAX_PROFILE`, and `TRADING_CALENDAR` manifest row.
  `snapshot_class` is bound to the corresponding contract name; an empty
  `missing_required_inputs` array alone is never sufficient.
  The new typed contracts are
  [`benchmark-snapshot-v1`](benchmark-snapshot-v1.md),
  [`sizing-policy-v1`](sizing-policy-v1.md),
  [`tax-profile-v1`](tax-profile-v1.md), and
  [`trading-calendar-v1`](trading-calendar-v1.md).
- `OPEN`, `BLOCKED`, `REJECTED`, `NO_ACTION`, and `INVALID` are durable origin
  outcomes. They are not deleted to improve a denominator.

A blocked or rejected origin may have no paper intent, but it remains a cohort
member with stable reason codes. Corrections append a new linked artifact; they
never rewrite the origin.
