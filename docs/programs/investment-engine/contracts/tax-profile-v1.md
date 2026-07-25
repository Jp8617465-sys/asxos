# Tax Profile v1

`tax-profile-v1` is a James-ratified, point-in-time paper-accounting assumption
set. It supports comparable counterfactual tax estimates; it is not a tax
return, tax advice, or a claim about final liability.

**Machine contract:** [`tax-profile-v1.schema.json`](../schemas/tax-profile-v1.schema.json)

## Required semantics

The profile fixes jurisdiction, entity class, tax year, effective interval,
ordinary-income rate, short- and long-holding capital-gain rates, discount
eligibility, dividend/franking treatment, and opening carried-loss state.
Rates and amounts are exact six-decimal strings. Every assumption is sourced,
available before use, and tied to one immutable profile version.

Each evaluator branch owns an isolated copy of the opening tax state. Losses,
holding periods, credits, and deferred tax are never shared between
counterfactuals. Unknown residency, tax year, rate, lot history, loss state, or
franking entitlement makes the affected branch/date unavailable; zero fallback
is forbidden.

This profile is `PAPER_ONLY`, an estimate, non-filing, non-executable, and
cannot authorize a transaction or evidence promotion.
