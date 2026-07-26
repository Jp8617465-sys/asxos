# Portfolio Snapshot v1

`portfolio-snapshot-v1` freezes the cash, positions, tax lots, receivables,
payables, and accrued liabilities visible at a portfolio knowledge cutoff.

**Machine contract:** [`portfolio-snapshot-v1.schema.json`](../schemas/portfolio-snapshot-v1.schema.json)

## Required semantics

The snapshot is append-only and content-addressed. Each cash balance, position,
and lot has an immutable internal ID, AUD valuation, source hash, and
availability timestamp. Position quantity equals the sum of complete lot
quantities. XASX position and lot quantities use canonical positive integer
strings, matching proposal, sizing, intent, order, and fill wire contracts;
money and rates remain six-decimal strings. Cash and liability components
reconcile to the reported NAV:

`portfolio_snapshot_id` identifies one immutable revision, while
`portfolio_snapshot_version` records that domain revision. A later cutoff must
mint a new ID/version pair; it may not reuse an earlier artifact ID with a new
digest. The validator enforces that rule within `portfolio-snapshot-v1`; ID
uniqueness *across* contracts is not yet enforced (see
[typed capital lineage](../architecture.md#typed-capital-lineage)).

```text
NAV = cash + positions + receivables
    - payables - accrued_fees - realized_tax_payable
    - deferred_tax_liability
```

Lot, position, component, and NAV totals are recomputed using exact Decimal
arithmetic and are never attested. Missing lots, stale prices, unresolved
actions, unbalanced cash, or a reconciliation difference above `0.000001` makes
the snapshot `INCOMPLETE`. It never assumes a missing holding or liability is
zero.

### Where that recomputation is enforced

By the snapshot service, not by the dossier harness. This contract is introduced
in **S08** (`roadmap.yaml`, `introduced_sprint: S08`) and its totals are consumed
by the S07 construction/sizing path, whose acceptance evidence covers the
recomputation of the resulting portfolio (AC-31: board lots floor, sells cannot
exceed sellable quantity, the final whole portfolio is recomputed and every hard
check passes).

**The semantic validator recomputes none of these totals.** It validates the
snapshot against its schema, recomputes its `canonical_hash` identity, checks
that the copy embedded in `portfolio-proposal-v1` resolves by ID and digest, and
then *reads* `total_nav_aud`, `components.cash_aud` and
`cash_balances[].reserved_aud` as inputs to the proposal and sizing checks. It
never sums lot quantities into a position, never sums positions into
`components`, never evaluates the NAV identity above, and never applies the
`0.000001` reconciliation tolerance or derives `status`. A snapshot whose
`total_nav_aud` contradicts its own components passes the harness, and every
downstream weight and cash check computed from that NAV inherits the error.

The snapshot contains no routeable account details. It is `PAPER_ONLY`,
read-only, non-executable, and cannot write live holdings.
