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

## Harness coverage of the rules above

The rules above are normative and binding on the producer. They are enforced by
the NAV service built in **S10** and by its acceptance evidence — AC-43 (daily
NAV and TWR recompute from the ledger and exact external-flow valuation
boundaries; balance differences or asserted aggregate returns fail) and AC-44
(genuine point-in-time XJO-TR receives identical flows). What the dossier harness
mechanises is narrower:

| Rule | Harness status |
|---|---|
| `ending_nav_aud` equals the seven-component identity | **Recomputed** for every entry of `branch-nav-valid.json` with exact `Decimal` |
| `benchmark_snapshot_ref` resolves to the in-dossier snapshot | **Enforced** by the generic typed-reference digest check |
| `modified_dietz_return` from beginning NAV, ending NAV and weighted flows | Not recomputed. Format-checked only: `_validate_numeric_wire_shapes` enforces the six-place Decimal string shape because the name ends in `_return` |
| `ending_nav_aud` rolls forward from `beginning_nav_aud` plus flows | Not checked. `beginning_nav_aud` and `external_flows_aud` are format-checked as `*_aud` Decimal strings but never compared across entries |
| Daily active log returns derived only from complete paired returns `> -1` | Not checked. Both fields are format-checked as `*_return` Decimal strings; the derivation is never evaluated |
| `source_snapshot_sha256` equals the resolved benchmark digest | Not checked. The field is format-checked as a `*_sha256` hex string, but never compared with the digest `benchmark_snapshot_ref` resolves to, so the two may disagree |
| Same-session binding between the NAV row and its benchmark snapshot | Not checked — no session-date comparison is made |
| `series_sha256`, `series_status`, `missing_session_count` | Not checked — accepted as declared |

Every `modified_dietz_return` and active-log-return value in the shipped fixture
is `null` under an `UNAVAILABLE` status, so no return-derivation path is
exercised anywhere in the dossier. Do not read a green validator run as evidence
that a NAV series' returns are correct.
