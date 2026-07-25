# Branch Ledger v1

`branch-ledger-v1` is the append-only, balanced economic event book for all five
branches of one origin.

**Machine contract:** [`branch-ledger-v1.schema.json`](../schemas/branch-ledger-v1.schema.json)

Each event has an immutable ID, effective/available/recorded times, source and
policy hashes, currency, and at least two debit/credit legs. For every event and
currency, total debits equal total credits exactly. Units and money use separate
accounts; corrections reverse and link prior events.

Required branch IDs are `PROPOSAL_BASE`, `PROPOSAL_STRESS`, `HOLD`, `XJO_TR`,
and `CASH`. Each branch begins from the same origin-state hash. Completeness is
reported separately for price, FX, corporate action, fee, cost, tax,
accounting, settlement, and reconciliation. Any missing required class blocks
NAV and gate evidence.

The ledger resolves the effective typed [`tax-profile-v1`](tax-profile-v1.md)
at the root. Every `TAX` event additionally carries that exact typed reference;
its effective time must fall inside the profile interval and its digest must
match the root. Missing, stale, or mismatched tax state makes the branch
`INCOMPLETE`; no tax value is silently treated as zero.
