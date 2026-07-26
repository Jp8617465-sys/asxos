# S10 — Corporate actions, FX, tax, costs, and daily branch NAV

**Initiative:** EVAL-04
**Phase:** prospective-evidence infrastructure
**Weekly outcome:** every shadow branch reconstructs daily AUD NAV from balanced
ledger records with explicit price, action, FX, fee, cost and tax treatment, or
stops with a typed incomplete reason
**Maximum evidence tier:** `PAPER_ONLY`
**Acceptance rows:** AC-41–44
**Depends on:** S09 simulated fills/settlement/branch ledger; S08 accounting and
benchmark policies
**Unlocks:** S11 outcome/statistics/gate recomputation

## Normative contracts

- `accounting-policy-v1`
- `benchmark-policy-v1`
- `benchmark-snapshot-v1`
- `branch-ledger-v1`
- `branch-nav-v1`
- `tax-profile-v1`
- `trading-calendar-v1`
- effective `fill-model-v1`
- existing deterministic tax engine/specification and a new coverage matrix

## Accounting basis

- Base/reporting currency is AUD.
- Raw unadjusted prices plus explicit corporate-action events drive positions and
  cash. Adjusted close is reconciliation-only.
- Trade-date asset/payable recognition and explicit settlement-date cash transfer
  follow the pinned XASX settlement calendar.
- Every posting is double-entry, append-only and source-hashed.
- Corrections reverse/link; no historical row is edited.
- Every valuation input was available by its session cutoff.
- Quantitative wire/storage values are canonical six-place decimals; quantities
  are integer strings. Currency rounding, unit precision and residual treatment
  come from the accounting policy.

## Corporate actions

Freeze treatment and effective/ex/payment dates for at least:

- cash dividends and franking credits;
- capital returns and special distributions;
- splits/consolidations;
- rights/entitlements;
- spin-offs/demergers;
- symbol/security identifier change;
- merger/takeover/cash-out; and
- delisting or unavailable terminal value.

Unsupported or ambiguous treatment creates a material accounting defect and blocks
NAV/gates for the affected branch. It is never ignored or replaced with adjusted
close.

## FX

V1 capital instruments are XASX/AUD. FX is still required for any inherited
foreign cash, foreign corporate-action component or existing lot basis. The policy
pins source, side/mid convention, timestamp, revision policy and conversion
rounding. Missing/stale FX blocks the affected NAV; it never defaults to one.

## Costs and capacity

Post and report separately:

```text
brokerage
exchange/regulatory fee
spread estimate
market-impact estimate
latency/queue penalty
unfilled opportunity cost
borrow cost (must be zero/not-applicable in long-only v1)
other supported cost
```

Base and stress parameters carry source/effective version. Capacity is reported at
the actual shadow equity and James-nominated scale points using intended notional,
ADV participation, days to liquidate, filled/unfilled fraction and expired intent.
A high fill ratio at trivial capital cannot masquerade as capacity.

## Tax state and label

The continuous shadow portfolio has one isolated hypothetical tax ledger seeded
from the exact James lots, loss carryforwards and profile known at inception.
Each counterfactual episode forks its own identical starting tax state. Episode
branches never share later gains/losses with each other and are not summed into
portfolio tax.

The versioned policy freezes:

- James profile and tax-law/spec version/effective dates;
- lot selection and CGT discount eligibility;
- realized gains/losses and within-branch loss carryforward;
- dividend, franking, withholding and supported distribution treatment;
- realized/unrealized FX;
- annual tax-year accrual/payment convention;
- estimated immediate-liquidation tax liability used in after-tax NAV; and
- unsupported categories/required human inputs.

Report both pre-tax NAV and `estimated_after_tax_liquidation_nav`. The latter
deducts an estimated liability on realized taxable income and hypothetical
immediate liquidation of open lots under the frozen profile. It is labelled
**after-tax estimate**, never a tax return or exact future liability.

If a required profile input or treatment (for example an unsupported managed-fund
distribution) is missing, tax coverage is incomplete and the after-tax/strategy
gate is blocked. The system may still show pre-tax diagnostic NAV with a precise
warning.

## NAV and external flows

Every external flow creates a valuation boundary. TWR chains exact subperiod
returns:

```text
subperiod_return =
  (ending_NAV_before_next_flow - starting_NAV_after_prior_flow)
  / starting_NAV_after_prior_flow

TWR = product(1 + subperiod_return) - 1
```

If the engine cannot value a flow boundary from point-in-time prices/FX, the
session is incomplete; it does not use capital-balance differences or silently
switch to Modified Dietz. XJO-TR receives economically identical flow timing.

Daily `BranchNavV1` reconciles:

```text
cash + receivables - payables
+ marked securities
+ accrued supported income/franking
- accrued fees/costs
- estimated tax liability
= estimated_after_tax_liquidation_nav
```

It also records pre-tax NAV, price coverage, drawdown/high-water mark, turnover,
gross/net exposure and unresolved defects.

## Benchmark

`benchmark-policy-v1` must identify a licensed, point-in-time genuine XJO total
return series, provider, series code, currency, calendar, observation/availability
time and revision policy. Price-only XJO or reconstructed dividends cannot pass.
Each consumed observation is frozen as `benchmark-snapshot-v1`; revised values
append a new immutable observation and cannot rewrite a prior origin. The XJO
branch applies identical external-flow boundaries. Because its published index is
gross of James's personal tax, comparison to the portfolio's after-tax estimate
is labelled a conservative hurdle, not pure alpha.

## Existing code reuse

Brownfield survey per review finding DR-04. Every path and table named below was
read in the repository; where the repository cannot supply what this sprint
assumes, the row says so plainly rather than assuming a capability. This is the
sprint with the largest existing surface **and** the largest sourcing hole.

| What exists today | What this sprint needs | Gap | Decision required |
|---|---|---|---|
| `asxos/domain/tax/` — `positions.py` (`tax_view_individual`, `tax_view_smsf`), `cgt.py` (`is_discountable`, `net_capital_gain`, `days_to_eligibility`, `cgt_discount_rate`), `lots.py` (`select_fifo`, `select_lifo`, `select_min_cgt`), `dividends.py`, `franking.py`, `medicare.py`, `div_296.py`, `fx_gain.py`, `types.py`; spec `docs/foundation/spec/tax-alpha.md` | S10-C's "reuse the tax engine; never duplicate tax formulas in the evaluator" | The engine is pure and **stateless**: it takes `lots` / `realised_gains` / `dividends` plus an `IndividualConfig`/`SMSFConfig` and returns a `TaxView`. It has no branch-isolated tax state, no accumulating within-branch loss carryforward (only the scalar `carried_forward_capital_loss` config input), no withholding, no managed-fund distribution component types, and no `estimated_after_tax_liquidation_nav` | James: the unsupported-category list that blocks the after-tax gate. The adapter is engineering; which absences are *blocking* is a governance call |
| `asxos/domain/tax/cgt.py::is_discountable` — implements spec §5.1 calendar arithmetic (`acquisition + relativedelta(years=1) + timedelta(days=1)`), per CLAUDE.md non-negotiable #6 | `tax-profile-v1` CGT eligibility | The shipped `tax-profile-valid.json` pins `minimum_holding_days: "365"` — a day-count rule that contradicts the very engine this sprint says it reuses (review finding EV-01) | None here. R0-B1 corrects the contract; this row exists so the sprint names the authority it must call rather than reimplementing a rule |
| `rs_corporate_actions` (`0027_research_store.sql`), `asxos/ingestion/corporate_actions.py`, `jobs/sync_corporate_actions.py` — EODHD `/div` and `/splits`; `action_type` is `'split'` or `'dividend'` only; `dividend_amount` uses the as-paid `unadjustedValue`; `franking_pct` parsed with NULL meaning undeclared (not zero) | Frozen treatment for at least eight action classes | **Two of the eight have a source; six do not.** Cash dividends + franking: sourced. Splits/consolidations: sourced. Capital returns and special distributions, rights/entitlements, spin-offs/demergers, symbol/identifier change, merger/takeover/cash-out, and delisting terminal value have **no ingest, no storage and no `action_type` value**. This is review finding EV-07 in concrete terms | James/PROC-01: a corporate-action provider covering the full list, **or** ratify a narrower supported set and accept that every unsupported event blocks NAV for the affected branch. The zero-defect operational gate should not be ratified before this is decided |
| `fx_rates` (`0009_us_equities.sql`: `pair`, `dt`, `rate`, `source`; AUDUSD only), `asxos/domain/prices/fx.py` (`is_foreign_symbol`, `foreign_symbol_sql` — suffix-based, explicitly *not* `universe.currency`), `holding_lots.acquisition_fx_rate`/`disposal_fx_rate`, `asxos/domain/tax/fx_gain.py` (Div 775 / TR 2019/1) | FX source, side/mid convention, timestamp, revision policy, conversion rounding | `fx_rates` carries one pair, a date and a rate — no side/mid marker, no observation timestamp, no revision history, and `jobs/snapshot_portfolio.py` notes the series is effectively monthly. Currency identity is inferred from a symbol suffix, not a data attribute | James: FX provider and convention. Note the sprint's own rule — missing/stale FX blocks NAV and never defaults to one — is the correct behaviour against this table today |
| `asxos/domain/portfolio/monitor.py::CostModel` (`commission_bps=8`, `slippage_bps=5`, explicitly labelled INFERRED placeholders) and `estimate_costs` | Seven separately posted cost lines with source and effective version: brokerage, exchange/regulatory fee, spread, impact, latency/queue, unfilled opportunity cost, borrow | Two hardcoded basis-point constants applied to traded notional. No brokerage schedule, no exchange-fee data, no impact model, no borrow (correctly zero in long-only v1) | James: the actual effective fee schedule for his account — a DEC-SHEET item. Placeholder bps must not survive into a posted cost |
| `asxos/domain/portfolio/monitor.py` — `build_nav_series`, `max_drawdown_pct`, `realised_vol_pct`, `turnover_pct`, `sector_attribution`, `position_perfs`; Decimal-only, no-lookahead-asserting, forward-fill always flagged on the NAV point and in the event log | Daily `branch-nav-v1` recomputed from ledger records with external-flow TWR boundaries | Genuinely reusable: drawdown, realised vol, turnover and attribution are correct pure kernels. **Not reusable as the NAV source**: cash is the constant `inp.cash_aud` for the whole series (no flows, therefore no TWR boundaries), total return uses `adj_close` — which this sprint forbids as an accounting basis — and there are no receivables, payables, accruals or tax terms | Confirm the split explicitly: reuse the drawdown/vol/turnover/attribution kernels, rebuild the NAV series from the ledger. Do not extend `build_nav_series` |
| `portfolio_daily_snapshots.us_holdings_mv_aud` / `us_holdings_cost_aud` / `fx_rate_audusd` / `unrealised_fx_pnl_aud` | AUD/foreign split in NAV reporting | Existing precedent for the AUD-base reporting split; single pair only | None. Reuse the pattern |
| `.claude/rules/portfolio-conventions.md` §"`cost_base_normal` currency" (risk R10): `holding_lots.cost_base_normal` is the **AUD** CGT base, not native currency; `prices.close` and `disposal_proceeds` are native | Any branch valuation touching a foreign lot | This exact currency-mixing error already produced a materially wrong analysis on 2026-07-11 (a flat position reported as −29%). Any evaluator code that divides `cost_base_normal` by `quantity` and compares to a USD close repeats it | None — this is a hazard row. Add a golden vector for a foreign lot to the S10-C set. That rules file is an authority document: cite it, do not amend it here |

## Mission decomposition

### Mission S10-A — accounting/tax decision matrix (12h, contracts/golden PR)

- Inventory existing action/FX/tax/fee/lot coverage and unsupported cases.
- Freeze journal entries, rounding, tax-state isolation, liquidation-tax NAV,
  external-flow TWR and benchmark semantics with Opus/Ultra.
- James supplies required profile inputs; absent values remain explicit blockers.
- Create balanced golden vectors for every supported event and failure.

### Mission S10-B — actions/FX/cost ledger kernels (12h, product PR)

- Implement pure postings and linked corrections.
- Reconcile raw-price action economics and base/stress cost decomposition.
- Property tests for balance, conservation, split invariance and FX round trip.

### Mission S10-C — tax ledger and coverage (12h, product PR)

- Reuse the tax engine; add branch isolation, profile/spec version and coverage
  matrix adapters.
- Golden realized/unrealized, loss, CGT-discount, dividend/franking and unsupported
  vectors.
- Never duplicate tax formulas in the evaluator.

### Mission S10-D — daily NAV/TWR/benchmark (12h, product PR)

- Build `branch-nav-v1` from ledger and source manifests.
- Implement exact flow-boundary TWR, XJO-TR identical-flow branch, drawdown and
  coverage/defect records.
- Recompute from ledger; producer aggregates are ignored.

### Mission S10-E — persistence/recovery/red-team (8h, evidence PR or review)

- Full migration preflight/chain and production-shaped replay.
- Reconcile every branch to the cent and source hash.
- Fresh-context Opus/Ultra reviews accounting, tax, benchmark, capacity,
  point-in-time and correction semantics.

## Required negative evidence

- missing/stale/revised price, FX, action, fee, tax profile, lot or benchmark;
- unsupported action/tax/distribution;
- adjusted-close use as accounting source;
- unbalanced journal, duplicate/conflicting event and correction rewrite;
- external flow without exact valuation boundary;
- tax state leaking between counterfactual branches;
- price-only XJO labelled total return;
- `after_tax_cost_aud` asserted without decomposed recomputable postings;
- Model A/broker/live-holding dependency.

## Observability

Emit config/branch/session/ledger/NAV/policy/source IDs/hashes, price/action/FX/tax/
cost coverage, defects by class/materiality, postings and balance result, pre-tax
and after-tax-estimate NAV, flow count, benchmark provenance, replay match and
duration. Never log private tax-profile bodies.

## Rollback

Pause accounting/NAV writers, retain immutable events, invalidate affected NAV and
gates, deploy compatible prior code and append corrections under a new accounting
lineage. Any material semantic correction restarts prospective evidence.

## Definition of Done

- [ ] Raw prices plus explicit actions fully drive accounting.
- [ ] Every supported event has balanced golden postings and correction behavior.
- [ ] Tax state/profile/coverage are versioned and branch-isolated.
- [ ] Calendar, benchmark observations and tax profile resolve immutable typed hashes.
- [ ] NAV/TWR/XJO-TR recompute from lower-level records and identical flows.
- [ ] Unsupported/missing treatment blocks instead of becoming zero.
- [ ] Cost/capacity decomposition is complete and honest.
- [ ] Migration/replay/recovery/full CI and fresh Opus/Ultra red-team pass.
- [ ] Combined worktree is clean.
