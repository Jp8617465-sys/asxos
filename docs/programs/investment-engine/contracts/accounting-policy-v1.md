# Accounting Policy v1

`accounting-policy-v1` freezes the economic-accounting semantics used by paper
ledgers, NAV, and outcomes.

**Machine contract:** [`accounting-policy-v1.schema.json`](../schemas/accounting-policy-v1.schema.json)

## Required policy

The policy fixes trade- and settlement-date treatment, chart of accounts,
currency translation, lot selection, corporate-action support, fee and cost
posting, realized and deferred tax treatment, loss carryforward handling,
dividend/franking treatment, rounding, and unsupported-state behavior.

Tax is a versioned estimate over an isolated counterfactual branch using the
James-supplied point-in-time
[`tax-profile-v1`](tax-profile-v1.md). Trade and settlement dates resolve the
same immutable [`trading-calendar-v1`](trading-calendar-v1.md) used by fills
and NAV. It is not an income-tax return. An
unknown tax profile, unsupported distribution/action, ambiguous entitlement,
missing FX/fee schedule, or incomplete loss/lot state makes the affected
branch/date unavailable; it never becomes zero.

Cash, receivables, payables, positions, cost basis, income, fees, stress costs,
realized tax, deferred tax, and external flows have distinct accounts.
Settlement releases reservations and transfers receivables/payables; a fill is
not silently treated as settled cash.
