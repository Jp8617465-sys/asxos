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
digest.

```text
NAV = cash + positions + receivables
    - payables - accrued_fees - realized_tax_payable
    - deferred_tax_liability
```

The semantic validator recomputes lot, position, component, and NAV totals using
exact Decimal arithmetic. Missing lots, stale prices, unresolved actions,
unbalanced cash, or a reconciliation difference above `0.000001` makes the
snapshot `INCOMPLETE`. It never assumes a missing holding or liability is zero.

The snapshot contains no routeable account details. It is `PAPER_ONLY`,
read-only, non-executable, and cannot write live holdings.
