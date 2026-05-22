# Australian Tax Task

<context>
- **Source of truth: `docs/foundation/spec/tax-alpha.md` v1.1.** Every change
  to tax math must cite the spec section number it implements. Deviations
  require a spec amendment (CLAUDE.md non-negotiable #8).
- Single user (James). No multi-tenant, no user_id, no compliance
  disclaimers needed — this is a personal tool.
- Implementation: `asxos/domain/tax/`
  - `types.py` — IndividualConfig, SMSFConfig, Dividend, CapitalGain,
    HoldingLot, NetCapitalGain, Div296Outcome, DividendOutcome, TaxView
  - `cgt.py` — §5.1 calendar-arithmetic 12-month rule, §5.2 optimal
    loss ordering
  - `franking.py` — §3 gross-up formula (validation / fallback only;
    trusts statement override per audit Issue 7)
  - `dividends.py` — §4.1 individual, §4.2 SMSF proportionate method
  - `div_296.py` — §6.3 stacked tier-1 + tier-2 proportion-of-TSB
  - `medicare.py` — §7 Medicare levy on taxable income (individuals only)
  - `lots.py` — FIFO / LIFO / min-CGT lot selection on disposal
  - `positions.py` — `tax_view(...)` bundles the four scenarios for the CLI
- CLI: `asx tax-view`, `asx tax-action`, `asx import-holdings <csv>`
- Account types (spec §2): `individual` | `smsf`. The SMSF carries
  `fund_pension_proportion ∈ [0.0, 1.0]` and `fund_segregated_eligible`
  (defaults false). No separate "accumulation" / "pension" types.
- Test cases TC-01..TC-21 in spec §11 — every spec section has a test.

Critical rules:
- §5.1 12-month: `disposal_date >= acquisition_date + relativedelta(years=1) + timedelta(days=1)`.
  Day-count `(disposal - acquisition).days >= 365` is FORBIDDEN by the spec.
- §5.2 loss ordering: apply against non-discount gains first, then discount.
  This is optimal per s 102-5 Notes 1 & 2.
- §2 CGT discount: individual 50%, SMSF exactly 1/3 (`Fraction(1,3)`).
- §3 corporate tax rate: per-security column (`universe.corporate_tax_rate`),
  default 0.30, base-rate entities 0.25.
- §4.1 individual dividend: Medicare levy stacks on the marginal rate.
- §4.2 SMSF dividend: proportionate method, full franking credit retention
  (refundable per s 67-25 + Div 207).
- §6.3 Div 296: stacked tier 1 (15% above $3M) + tier 2 (+10% above $10M),
  each computed against TSB_ref = max(opening, closing). FY 2026-27
  transitional rule uses closing only.
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- All monetary values are `Decimal`. Never `float`. Never mix.
- Cite spec section numbers in code comments and commit messages
- Single-user, no disclaimers, no soft-deletes (no user data to protect)
- Pure functions only — tax modules never touch the DB or network
- The CSV importer (`asx import-holdings`) is the integration boundary
  with persisted state
</constraints>

<verify>
1. Every new tax function has a test referencing the spec section number
2. All 21 spec TC-* cases still pass (`pytest tests/test_tax_*.py`)
3. Calendar arithmetic via `dateutil.relativedelta`, never day-count
4. SMSF CGT discount uses `Fraction(1,3)` not `Decimal("0.3333")`
5. Validation errors on negative marginal rate, marginal rate > 0.5,
   `fund_pension_proportion` outside [0, 1], zero cash + non-zero franking
6. `make check` green
</verify>
