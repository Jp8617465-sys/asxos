# S07 — Portfolio construction, ratified policies, and deterministic sizing

**Initiatives:** PORT-01, ENG-02
**Phase:** capital-boundary engineering
**Weekly outcome:** a complete portfolio snapshot and eligible case set produce one
reproducible target/delta vector and exact board-lot quantities, or one typed
whole-portfolio rejection
**Maximum evidence tier:** `PAPER_ONLY`
**Acceptance rows:** AC-27–32
**Depends on:** S05 current `PAPER_ELIGIBLE` case lineage; S06 monitor watermark
**Unlocks:** S08's first honest evaluator configuration and prospective origin

## Why this sprint changes the north star

This is the missing engine between “good research” and “a size James can inspect.”
It improves Capital Under Discipline because every desired exposure has a current
case, independent review, monitoring watermark, ratified policy and complete
constraint proof. It mirrors an institutional portfolio-construction/risk split:
research may express qualitative intent, James owns the mandate and risk anchors,
and deterministic code alone creates numbers.

It is not the legacy signal allocator, a weighted score or a generic optimiser.

## Normative inputs

- `investment-case-lineage-v1`
- `portfolio-construction-policy-v1`
- `risk-policy-v1`
- `sizing-policy-v1`
- `staging-policy-v1` (ratified now so the evaluator lineage is final)
- `trading-calendar-v1`
- `security-classification-snapshot-v1`
- `portfolio-proposal-v1`
- `sizing-decision-v1`
- exact S03 report, S05 review eligibility and S06 monitor watermark
- exact effective-dated `security-classification-snapshot-v1`, materialized from
  the authoritative XASX security master, theme membership and trading rules
- settled holdings/tax lots, cash, unsettled cash, pending commitments and
  unexpired staged reservations
- price, liquidity, FX and effective fee inputs

V1 rejects non-XASX instruments, short targets and non-AUD capital output.

## Fixed construction algorithm

### Admission

An investment case is admitted only when:

1. the full typed lineage resolves and hashes verify;
2. the latest review decision is `PAPER_ELIGIBLE`;
3. the report/context/review is fresh under policy;
4. the monitor watermark has no unresolved material challenge;
5. qualitative intent is one of `ENTER_OR_ADD`, `HOLD`, `TRIM`, `EXIT`;
6. James has ratified a case-specific risk-reference price and, for `TRIM`, a
   maximum exposure; and
7. all required security, price, liquidity, lot and classification inputs exist.

Every exclusion is retained with a stable reason. A missing mandatory case input
blocks that case. Missing portfolio-wide input rejects the whole proposal.

### Target derivation

For each long `ENTER_OR_ADD` case:

```text
stop_distance_fraction =
  (reference_price - risk_reference_price) / reference_price

case_loss_budget_aud =
  min(
    explicit James-ratified case budget when present,
    equal share of remaining portfolio loss budget
  )

raw_target_notional_aud =
  case_loss_budget_aud / stop_distance_fraction
```

Non-positive stop distance is invalid. `EXIT` targets zero. `HOLD` targets current
exposure after hard-cap clipping. `TRIM` targets the lower of current exposure and
the James-ratified maximum.

Apply the machine contract's fixed waterfall, recording every precondition,
source, comparison direction, before/limit/after value, and action. Each numeric
check's direction and limit resolution are fixed by the `sizing-policy-v1`
registry, not chosen by the producer:

1. eligibility, then complete effective classification;
2. stop risk, then issuer, corporate-group, single-name, sector and theme
   exposure;
3. total portfolio loss at stop;
4. gross exposure, net exposure, cash reserve, turnover and reservations;
5. liquidity/ADV/spread and deterministic tax constraints; and
6. minimum viable target.

Classification is a Boolean precondition, not a synthetic weight cap. Empty
`theme_ids` is valid complete membership; missing or ambiguous membership fails
closed.

Then solve coupled portfolio constraints:

1. form the entire unrounded delta vector;
2. reserve fees, unsettled cash, pending commitments and existing staged notional;
3. apply one proportional shrink for cash, gross, issuer/group/sector/theme,
   portfolio-loss, reservations and turnover constraints;
4. prove the effective tick rule, then floor quantities to effective board lots;
5. repair residual breaches in stable
   `(constraint_priority, investment_case_id, symbol)` order;
6. recompute the complete before/after portfolio, loss-at-risk and fees; and
7. reject the whole output unless every hard constraint passes.

No line may be `REJECTED` inside a `SIZED` result. Reordering input cases must
produce bit-identical canonical output.

### Diagnostic risk

The proposal reports issuer/group/sector/theme concentration, days to liquidate,
scenario loss, beta, volatility, correlation/factor exposure, risk contribution
and capacity at policy-nominated capital scales when supported by pinned data.
Unknown diagnostics remain explicit. They are hard gates only when James marks
the exact metric/method/version as mandatory in policy.

## State and failure outcomes

Construction:

- `BUILT`
- `HOLD_CASH`
- `REJECTED_NO_CONSTRUCTION_POLICY`
- `REJECTED_NO_RISK_POLICY`
- `REJECTED_INCOMPLETE_INPUT`
- `REJECTED_INFEASIBLE`

Sizing:

- `SIZED`
- `REJECTED_NO_POLICY`
- `REJECTED_POLICY_VIOLATION`

Only `BUILT` plus a complete `SIZED` result may seed S08. Nothing in S07 creates
a James-visible staged order.

## Additive persistence

After live dependency inspection, add immutable effective-dated construction,
risk and staging policy versions/ratifications; frozen portfolio snapshots;
proposal headers/line items/checks; sizing headers/line items/checks; and typed
lineage manifests. Reuse holdings, lots and security master rather than cloning
them. Store referenced snapshot IDs/hashes.

All financial database values use `NUMERIC(18,6)`. Separate artifact status,
evidence tier and James ratification; do not overload one lifecycle. Allocate no
migration number until the attended preflight.

## Existing code reuse

Brownfield survey per review finding DR-04. Every path and table named below was
read in the repository; where the repository cannot supply what this sprint
assumes, the row says so plainly rather than assuming a capability.

| What exists today | What this sprint needs | Gap | Decision required |
|---|---|---|---|
| `asxos/domain/portfolio/build.py` (`PortfolioService.build`), `allocator.py`, `constraints.py`, `rebalance.py`, `volatility.py`, `jobs/build_portfolio.py` — inverse-vol/composite-score allocator driven by `signals` and `resolve_production_model()` | A loss-at-stop constructor driven by investment-case lineage with no model input | Target derivation is different in kind, not degree. The legacy path is also currently inert: `resolve_production_model(required=True)` hard-fails at 0 approved models, which is rule #11's mechanical state | James: legacy allocator disposition — freeze in place, tombstone, or coexist. This sprint must not silently inherit it |
| `rebalance_runs` / `target_allocations` / `proposed_trades` (`migrations/0005_portfolio.sql`) | Immutable proposal/sizing headers, line items and per-check rows carrying direction, limit, source and action | `target_allocations` is model-shaped (`prob_up`, `expected_return`, `signal_label`, `inv_vol_score` columns); `target_allocations.constraint_log` (JSONB, `migrations/0005_portfolio.sql:156`) records a per-run log, but no table records per-check rows carrying direction, limit, source and action | New additive tables. Decide whether the legacy three are retained read-only or dropped from the product surface |
| `profiles` (`0005_portfolio.sql`): `capital_aud`, `cash_floor_pct`, `leverage_cap`, `per_name_cap_pct`, `sector_cap_pct`, `excluded_sectors`, `excluded_symbols`, `min_position_aud`, `defer_near_boundary_sells`, `score_weights_json`, plus the `set_active_profile()` exactly-one-active function | Immutable effective-dated `risk-policy-v1` / `portfolio-construction-policy-v1` with ratification audit: loss budgets, issuer and corporate-group caps, theme caps, turnover, liquidity limits | `profiles` is one mutable row with no ratification audit and no version history. It has no loss budget, no issuer/corporate-group/theme/turnover field, and no liquidity limits at all | James: whether the existing profile values seed the DEC-SHEET defaults or are superseded outright. `score_weights_json` is model-scoring machinery and has no successor here |
| `holding_lots` / `current_holdings` view (`0001_initial.sql`), `portfolio_daily_snapshots` + `jobs/snapshot_portfolio.py` | Settled holdings, unsettled quantity, sellable quantity, pending commitments, unexpired staged reservations, observed cash (PC-04/PC-05) | `holding_lots` has no settlement date and no reservation concept; `current_holdings` is exactly `disposed_at IS NULL`. **There is no cash ledger** — `jobs/snapshot_portfolio.py` derives `cash_aud = cash_floor_pct × capital_aud` from the profile (see its own docstring: "a conservative estimate. A real cash ledger replaces this after M13.8") | James: where observed cash and settlement state come from. Without one of these, the PC-05 cash-solvency floor checks a configured constant, not a balance |
| `universe` (`symbol`, `sector`, `currency`, `market_cap`, `is_active`, `security_kind` via `0037_security_kind.sql`) and `rs_security_master` (`0027_research_store.sql`: `name`, `exchange`, `currency`, `security_type`, `gics_sector`, `gics_industry`, `isin`, `listed_date`, `delisted_date`) | `security-classification-snapshot-v1`: issuer, corporate group, effective board lot, effective tick band, ADV, theme membership, effective-dated | **The repository has no issuer identifier, no corporate-group identifier, no board-lot column and no tick table** — a repo-wide search for `board_lot`/`tick_size` returns zero hits. Derivable today: ADV from `prices.volume` (BIGINT, present since `0001`); sector from `universe.sector`/`rs_security_master.gics_sector`; theme membership from `theme_holdings.exposure_strength` (`0012_theses_and_themes.sql`) | James: source for issuer, corporate group, board lot and tick band — licensed feed (fold into PROC-01), a hand-maintained ratified table, or ratify that the issuer/group caps and board-lot flooring are structurally blocked until a source exists. Do not synthesise them |
| `asxos/domain/prices/coverage.py::latest_complete_trading_day` (row-count heuristic; its own header states "**No holiday calendar (v1, intentional)**") | `trading-calendar-v1`: XASX holidays, session boundaries, next eligible session | No holiday calendar exists. The heuristic infers non-trading days from thin row counts after the fact; it cannot answer "is the next session 2026-01-27" in advance | James: XASX trading-calendar source (shared decision with S08, S09 and S12) |
| `asxos/domain/tax/cgt.py::days_to_eligibility` / `is_discountable` (spec §5.1 calendar arithmetic) and `asxos/domain/portfolio/tax_overlay.py` (`near_boundary_lots`, loss-harvest tagging with its Part IVA / TR 2008/1 disclaimer) | Step 5's "deterministic tax constraints" in the waterfall | Direct reuse. `tax_overlay` currently types against the legacy `ProposedTrade`/`HoldingSnapshot` dataclasses in `asxos/domain/portfolio/types.py`, so an adapter is needed, not a rewrite | None. Reuse; do not restate the calendar rule |
| `asxos/cli/_common.py::_require_personal_use()` and `asxos/jobs/_helpers.py::require_personal_use_job()` (`ASXOS_PERSONAL_USE=1`, s766B firewall) | Same firewall on every new entry point | None — the pattern is intact and mandatory | None. Inherit it |
| `asxos/domain/models/production_gate.py::resolve_production_model` and `model_versions.approved_for_allocation` | Nothing. The new engine must not read it | Legacy `build.py` calls it at `required=True`; any shared helper lifted out of `build.py` drags the model gate in transitively | None — this is a prohibition row. The isolation test must cover the import graph, not just the query |

## Mission decomposition

The weekly outcome is delivered by bounded missions, not one oversized PR.

### Mission S07-A — contract and James decision sheet (8h, one docs/tests PR)

- Inventory current profile/constraint/security-master fields and gaps.
- Produce an input sheet with no recommended values: field, unit, allowed range,
  consequence, source and `JAMES_INPUT_REQUIRED`.
- Freeze algorithms, formulas, coupled-constraint treatment, tie-breaks,
  Decimal/rounding and all reason codes with Opus/Ultra.
- Create golden/no-policy/infeasible/tamper/order-permutation fixtures.
- Exit: James has ratified every value or the expected output is a typed rejection.

### Mission S07-B — policy persistence (12h, product PR + optional migration evidence PR)

- Migration preflight and `pg_depend` inspection.
- Add immutable construction/risk/staging policies and ratification audit.
- Implement effective unique selection, diff, expiry and hash verification.
- Exercise zero/multiple/future/expired/unsigned/conflicting policy cases.
- Exit: no implicit default can reach the kernel.

### Mission S07-C — pure portfolio constructor (12h, one product PR)

- Implement admission, loss-budget target derivation, cap waterfall, proportional
  shrink, stable repair and full recomputation as pure Decimal code.
- Add property/metamorphic tests for input-order invariance, monotonic caps,
  scale behavior, no negative zero and full hash replay.
- Exit: every golden vector and negative vector is exact.

### Mission S07-D — sizing and persistence integration (12h, one product PR)

- Freeze complete portfolio/reservation snapshot.
- Convert target deltas to board-lot quantities, including sellable/unsettled
  quantity and tax-lot constraints.
- Persist one atomic proposal/decision/check graph and attended CLI show/diff.
- Failure injection proves no partial `SIZED` artifact.

### Mission S07-E — independent capital red-team (8h, evidence-only PR or review)

- Fresh-context Opus/Ultra reviews finance, risk, tax, migration, Model A and broker
  boundaries.
- Run order-permutation, stale/tamper, constraint-coupling, security-master
  boundary and production-shaped replay suites.
- Exit: complete frozen version bundle is handed to S08; any semantic change after
  this point starts a new evaluator lineage.

## Required golden vectors

- no/multiple/unratified policies;
- exact stop-distance boundary and non-positive distance;
- equal risk budgets, explicit per-case budget and stable tie;
- issuer/group/single/sector/theme/cash/gross/turnover/portfolio-loss coupling;
- ADV, days-to-liquidate, capacity scale, spread and fee cap;
- current position, unsettled quantity, pending cash/reservations and oversell;
- `ENTER_OR_ADD`, `HOLD`, `TRIM`, `EXIT`;
- board-lot floor, tick/security-master effective-date change and minimum notional;
- tax-lot choice/unsupported tax treatment;
- stale report/review/monitor/price/liquidity/policy;
- Model A perturbation and forbidden import/query;
- input permutation returns byte-identical result;
- exact worst-case notional plus fees does not exceed the cap.

## Observability

Emit identities/hashes, admitted/excluded counts and reason codes, before/after
cash/exposure/loss/turnover/capacity, every binding constraint, shrink factor,
rounding/repair count, policy versions, freshness, duration and replay result.
Never log private policy or report bodies.

## Rollback and invalidation

Stop constructors/sizers, retain immutable policies/decisions, invalidate affected
downstream artifacts through a new audit record, deploy compatible prior code and
forward-fix. Never edit a ratified policy or historical decision. Any financial
semantic correction invalidates S08+ prospective evidence and restarts the clean
cohort.

## Definition of Done

- [ ] The engine itself deterministically produces targets; no opaque target input remains.
- [ ] Every admitted asset resolves the complete current case lineage.
- [ ] Every policy/risk anchor is James-ratified or output rejects.
- [ ] Sizing and next-eligible-session rules resolve exact policy/calendar versions.
- [ ] Coupled constraints are portfolio-wide and input-order invariant.
- [ ] `SIZED` contains no rejected line and every hard post-state check passes.
- [ ] Construction, risk, sizing and staging versions are frozen before S08.
- [ ] Model A and broker boundary perturbation/static tests pass.
- [ ] Migration/replay/forward-recovery evidence and full CI pass.
- [ ] Fresh-context Opus/Ultra red-team passes and the combined worktree is clean.
