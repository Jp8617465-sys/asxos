# Branch NAV v1

`branch-nav-v1` derives daily NAV and cash-flow-aware return series for all five
branches from one balanced branch ledger.

**Machine contract:** [`branch-nav-v1.schema.json`](../schemas/branch-nav-v1.schema.json)

For each branch and session:

```text
NAV = cash + positions + receivables
    - payables - accrued_fees - realized_tax_payable - deferred_tax_liability

Modified-Dietz return =
    (ending_NAV - beginning_NAV - external_flows)
    / (beginning_NAV + weighted_external_flows)
```

Costs and tax are expenses, not external flows. Missing price, FX, action,
settlement, tax, fee, or flow timing yields `UNAVAILABLE`; it is never imputed.
The proposal-base, hold, and XJO-TR series share identical eligible endpoints.
Daily active log returns are derived only where both compared daily returns are
complete and greater than `-1`.

Every `XJO_TR` NAV row resolves a typed
[`benchmark-snapshot-v1`](benchmark-snapshot-v1.md) reference for the same
session. Its digest equals `source_snapshot_sha256`. A bare hash, a price-index
substitute, a snapshot from another session, or an incomplete snapshot makes
the row `UNAVAILABLE` and resets any clean-observation streak.
