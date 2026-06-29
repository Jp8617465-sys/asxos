# Tax alpha specification

Version 1.3. Date 2026-06-28. Audience: an accountant or experienced investor with Australian tax knowledge. Implementation must follow this document; deviations require a version bump and a change log entry. v1.1 integrates the technical audit dated 2026-05-19 (eight issues against the Treasury Laws Amendment (Building a Stronger and Fairer Super System) Act 2026, the Imposition Act 2026, ITAA 1997, ITAA 1936, ITTPA, the Income Tax Rates Act 1986, and the Medicare Levy Act 1986). v1.2 added §8 (Div 775 US equities). v1.3 adds §5.4 (CGT discount break-even heuristic). See section 13 for the full delta history.

## 1. Scope and non-goals

This specification defines the tax treatment for a personal investment intelligence system whose primary asset class is Australian listed equities held in either a personal account or a self-managed superannuation fund (which may be in accumulation, in pension, or in mixed phase). The module computes after-tax dividend yield, after-tax capital gain, Division 296 exposure, and Medicare levy for each position the user holds.

Out of scope for version 1 and explicitly reserved for v2: foreign holdings tax treatment (currency translation, treaty withholding credits, foreign tax offsets); Division 83A treatment for employee share schemes; trust distributions; attribution managed-investment-trust income; partnership income; personal-services income. Also out of v1 scope: mid-year phase changes inside an SMSF; reserve allocations; anti-detriment or death benefit pension transitions; segregation at the individual asset level; the Medicare levy surcharge; Division 293; HELP/HECS repayment interactions; multi-year capital loss carry-forward tracking (v1 accepts the carried-forward loss as a scalar input).

Where the spec says "v1 trusts X as input," that means the system does not derive X — the user or an ingestion process supplies it. Examples: the franking credit on a dividend (trust the share registry statement), the fund pension proportion (trust the annual actuarial certificate), the carried-forward capital loss (trust the prior-year tax return).

## 2. Account types

Two account types. Every position belongs to exactly one. The SMSF type carries an annual pension-proportion parameter that drives the proportionate method under ITAA 1997 s 295-390.

| Account type | Headline rate | Medicare levy | Franking refundable | CGT discount on held > 12 months |
|---|---|---|---|---|
| Individual | Marginal (0 to 45%) | Yes (2%) | Yes | 50% (s 115-100(a)) |
| SMSF | 15% before ECPI exemption | No | Yes (s 67-25, Div 207) | 33⅓% as exact fraction 1/3 (s 115-100(b)) |

The previous v1.0 split between "SMSF accumulation" and "SMSF pension" is removed. The audit (Issue 3) found this split is wrong for any SMSF with a member TSB above $1.6M receiving a retirement-phase income stream: the disregarded small fund assets rule at s 295-387 bars the segregated method for that fund, forcing the proportionate (actuarial) method under s 295-390 across all assets for the entire year. Since the system's primary use case is members at or near the Division 296 threshold, the proportionate method is mandatory in practice.

The SMSF type carries two additional fields:

- `fund_pension_proportion ∈ [0.0, 1.0]` — the actuarial percentage of fund assets supporting retirement-phase liabilities. Set annually from the actuarial certificate. A fully-accumulation fund has 0.0; a fully-pension fund has 1.0; a mixed-phase fund takes the actuarial figure.
- `fund_segregated_eligible: bool` — true only if (i) the fund is 100% retirement-phase for the entire income year, and (ii) no member has a TSB above $1.6M receiving a pension from any source (the DSFA condition at s 295-387). Default false. When true, ordinary fund income on segregated current pension assets is fully exempt under s 118-320.

For individuals, the marginal rate is a user-provided figure per income year. The system does not implement the bracket table.

## 3. Franking credit gross-up

A fully franked or partially franked dividend from an Australian-resident company carries an imputation credit equal to the company tax paid on the underlying profit. The credit is computed per dividend, per security, using the corporate tax rate applicable to that security.

The corporate tax rate is an input on the security, not a global constant. Default value 0.30. For securities classified as base-rate entities under Income Tax Rates Act 1986 ss 23AA, 23AB and LCR 2019/5 — that is, aggregated turnover under $50 million and 80% or less of assessable income being base-rate-entity passive income — the rate is 0.25. The user (or an ingestion process) sets this per security; the system does not classify automatically.

The franking credit on a dividend is calculated as:

> franking_credit = cash_dividend × franking_pct × corporate_tax_rate / (1 − corporate_tax_rate)

The grossed-up dividend income (the amount included in assessable income) is the cash dividend plus the franking credit.

**Implementation note from audit Issue 7**: for listed Australian equities, the franking credit amount and franking percentage are reported on the dividend statement issued by the share registry. The system **trusts the credit amount on the statement as authoritative**. It does not re-derive the franking rate from the underlying company's BRE classification at year-end. The above formula is the validation formula and the fallback when the registry statement does not include a credit value; it is not the production calculation.

Worked example. A 30%-tax-rate company pays a $1,000 fully franked dividend. The franking credit is $1,000 × 1.0 × 0.30 / 0.70 = $428.57. Grossed-up = $1,428.57.

Worked example, base-rate entity. A 25%-tax-rate company pays the same $1,000 fully franked dividend. The franking credit is $1,000 × 1.0 × 0.25 / 0.75 = $333.33. Grossed-up = $1,333.33.

When the franking rate for a security is unknown, default to 0.30 and log a warning. When a dividend record is missing its franking percentage, treat as unfranked (franking_pct = 0). Silent assumption of full franking is forbidden.

## 4. After-tax dividend calculation

The after-tax cash from a dividend depends on account type. The individual path is straightforward. The SMSF path runs the proportionate method under s 295-390 with the fund pension proportion driving the exempt component (ECPI).

### 4.1 Individual

> grossed_up = cash_dividend + franking_credit
> tax_assessed = grossed_up × (marginal_rate + medicare_levy_rate)
> franking_offset = franking_credit if franking_refundable else min(franking_credit, tax_assessed)
> net_tax = tax_assessed − franking_offset
> after_tax_cash = cash_dividend − net_tax

For individuals, `franking_refundable = True` and `medicare_levy_rate = 0.02`. This corrects the Phase A defect (Medicare missing from the v1.0 dividend path).

Worked example, Position 1. 500 CBA shares, full franking, $4.50/share annualised, individual at 37% marginal. Cash $2,250. Franking credit $964.29. Grossed-up $3,214.29. Tax at 39%: $1,253.58. Franking offset $964.29. Net tax $289.29. After-tax cash $1,960.71.

Worked example, individual at 47%. $1,000 fully franked dividend from a 30% company. Credit $428.57. Grossed-up $1,428.57. Tax at 49%: $700.00. Offset $428.57. Net tax $271.43. After-tax cash $728.57.

Worked example, partial franking (50%) for individual at 37%. $1,000 cash dividend, half franked. Franked half ($500) carries credit $214.29. Grossed-up $1,214.29. Tax at 39%: $473.57. Offset $214.29. Net tax $259.28. After-tax cash $740.72.

Worked example, fully unfranked dividend for individual at 37%. $1,000 cash, no franking. Grossed-up = $1,000. Tax at 39%: $390. After-tax cash $610.

### 4.2 SMSF — proportionate method (per s 295-390 and ATO TR 2013/5)

For an SMSF using the proportionate method (i.e. any SMSF subject to the DSFA rule at s 295-387, which in practice is any SMSF where the system's primary use case is the Division 296 threshold member):

> grossed_up = cash_dividend + franking_credit
> exempt_proportion = fund_pension_proportion
> ECPI_component = grossed_up × exempt_proportion
> taxable_component = grossed_up × (1 − exempt_proportion)
> fund_tax_before_offset = taxable_component × 0.15
> franking_offset = franking_credit                                   # full credit retained, refundable under s 67-25 + Div 207
> net_fund_tax = fund_tax_before_offset − franking_offset             # negative result is a refund
> after_tax_cash = cash_dividend − net_fund_tax

The full franking credit remains available regardless of how much of the dividend is ECPI. Per Division 207 ITAA 1997 and the SMSF Annual Return Section D instructions (label E1), franking credits attached to ECPI-exempt dividends are not denied — they are refundable to the complying fund.

Worked example, mixed-phase SMSF with 60% pension proportion. $1,000 fully franked dividend from a 30% company. Cash $1,000. Credit $428.57. Grossed-up $1,428.57. ECPI component $857.14 (60%). Taxable component $571.43 (40%). Fund tax at 15%: $85.71. Franking offset $428.57. Net fund tax = $85.71 − $428.57 = −$342.86 (refund). After-tax cash = $1,000 + $342.86 = $1,342.86.

Worked example, Position 2 (BHP, 1,000 shares, $2.00/share annualised, single-member SMSF in 100% accumulation, fund_pension_proportion = 0.0). Cash $2,000. Credit $857.14. Grossed-up $2,857.14. ECPI component $0. Taxable component $2,857.14. Fund tax at 15%: $428.57. Franking offset $857.14. Net fund tax = $428.57 − $857.14 = −$428.57. After-tax cash $2,428.57. (Unchanged from v1.0.)

Worked example, 100% pension SMSF (fund_pension_proportion = 1.0). Same $1,000 dividend. ECPI = $1,428.57 (entire grossed-up amount). Taxable component = 0. Fund tax = 0. Franking offset = $428.57 (full refund). After-tax cash $1,428.57. (Matches v1.0 SMSF pension worked example.)

### 4.3 45-day holding period warning (s 207-145, qualified-person provisions)

To claim franking credits, a complying SMSF must hold the shares at risk for at least 45 clear days (excluding the day of acquisition and the day of disposal). The $5,000 small-shareholder exemption available to individuals does **not** apply to SMSFs. If the system records a disposal within 45 days of acquisition that involves a dividend paid during the holding period, the system warns the user that franking credits on that dividend may be denied. The system does not enforce or deny credits automatically; it only warns.

Anti-avoidance provisions (s 207-145(1)(b), s 177EA, dividend washing) are out of v1 scope.

## 5. CGT discount and net capital gain (per s 102-5 ITAA 1997)

### 5.1 The 12-month rule

A capital gain qualifies for the discount only if the disposal occurs at least 12 months after acquisition, with both the acquisition day and the CGT event day excluded from the count. Per s 115-25(1) ITAA 1997 and Taxation Determination TD 2002/10, "at least 12 months" requires a clear period of 12 months between acquisition and the CGT event. The practical rule:

> The CGT event must occur on or after the day one year and one day after acquisition.

For acquisition on 11 July 2023, the earliest qualifying disposal is 12 July 2024. For acquisition on 1 January 2024, the earliest qualifying disposal is 2 January 2025. A disposal exactly 365 days after acquisition does not qualify in non-leap-year spans.

For listed shares, acquisition and disposal dates are the **contract dates**, not settlement dates (s 109-5 acquisition table; s 104-10(3) for CGT event A1).

The day-count form `(disposal − acquisition).days >= 365` is unsafe and is rejected by this spec. Use calendar arithmetic: `disposal_date >= acquisition_date + relativedelta(years=1) + timedelta(days=1)`.

### 5.2 Net capital gain computation (per s 102-5 ITAA 1997)

The taxpayer has discretion in the order of applying capital losses (Notes 1 and 2 to s 102-5). The optimal order is to apply losses against non-discount gains first, because a $1 loss against a non-discount gain saves $1 of taxable income, but a $1 loss against a discount gain saves only $0.50 (50% individual) or $0.667 (1/3 super) after the discount. The ATO explicitly endorses this order in its primary guidance page "Using capital losses to reduce capital gains" (last updated 23 June 2025): "If you have any capital gains that are not eligible for the CGT discount, subtract your capital losses from these gains first."

The algorithm:

> Inputs:
>   discount_gains          = list of gains eligible for s 115-100 discount (held > 12 months)
>   non_discount_gains      = list of gains ineligible (held ≤ 12 months, or per s 115-25(3) exclusions)
>   current_year_losses     = scalar
>   carried_forward_losses  = scalar (user-supplied for v1)
>   entity_type             = "individual" | "smsf"
>
> remaining_loss = current_year_losses + carried_forward_losses
>
> # Step 1 (s 102-5 Note 1): apply against non-discount first
> nd_total = sum(non_discount_gains)
> applied_to_nd = min(nd_total, remaining_loss)
> nd_remainder = nd_total − applied_to_nd
> remaining_loss −= applied_to_nd
>
> # Step 2 (s 102-5 Note 2): apply remainder against discount
> d_total = sum(discount_gains)
> applied_to_d = min(d_total, remaining_loss)
> d_remainder = d_total − applied_to_d
> remaining_loss −= applied_to_d
>
> # Step 3 (s 115-100): apply discount to remaining discount gains
> discount_rate = 0.50 if entity_type == "individual" else Fraction(1, 3) if entity_type == "smsf" else 0
> net_capital_gain = nd_remainder + d_remainder × (1 − discount_rate)
>
> # Step 4: if remaining_loss > 0 after both steps, this is a net capital loss carried forward
> net_capital_loss_cf = max(0, remaining_loss)

For SMSFs, the discount applies to the discount-eligible component of fund taxable income only. The ECPI exempt proportion is then applied to the post-discount net capital gain at the fund-income aggregation step (see §4.2). The CGT discount and the ECPI exemption are independent and stack.

Worked example. Discountable gains $30,000, non-discountable gains $10,000, current-year loss $15,000, carried-forward loss $5,000, individual at 37%. Optimal ordering applies $10,000 of CY loss to non-discount (extinguishes it), then $5,000 of CY loss + $5,000 of CF loss to discount, leaving $20,000 of discount gain. Discount $10,000. Net capital gain $10,000. Tax at 39% = $3,900. (The sub-optimal alternative — applying losses against discount first — would produce a net capital gain of $15,000 and tax of $5,850. Optimal ordering saves $1,950.)

### 5.3 Medicare levy on the net capital gain

For individuals, Medicare levy applies to the net capital gain at the same 2% rate, on the same base (the post-discount, post-loss-offset amount included in taxable income via s 102-5). This is automatic by virtue of the levy applying to taxable income under s 251S(1)(a) ITAA 1936. See §7.

### 5.4 CGT discount break-even price (decision-support heuristic)

Governs `cgt_break_even_price()` in `asxos/domain/tax/cgt.py`, surfaced by the position monitor. This is a **decision-support hint, not a tax computation**: it estimates the minimum sale price *today* (before the s 115-100 discount is available) that nets the same after-tax proceeds as deferring the sale until the discount is available, holding the price constant.

**Scope and assumptions (disclose to the user):**

- The price is assumed unchanged at the current price `P` on the date the discount becomes available. A heuristic, not a forecast. It ignores the time value of money, dividends/franking received during the deferral, and transaction costs.
- **Currency.** `P` and `cost` must be expressed in the **same currency**. For US lots, translate per §8.2 before calling; the function performs no Div 775 translation.
- **Effective rate `r_eff`.** Individual: `r_eff = marginal_rate + 0.02` — the marginal rate plus the 2% Medicare levy, because the net capital gain enters taxable income and attracts the levy in *both* the sell-now and sell-later scenarios (§5.3, §7). SMSF: `r_eff = 0.15` (the §2 headline rate), Medicare 0 (§7: the levy does not apply to super funds).
- **Medicare flat-rate validity.** The 2% individual addition is the *above-threshold flat* rate. It does **not** hold for an individual inside or below the §7.1 low-income shade-in band (~$28,011–$35,014 for FY 2026), where the marginal Medicare rate differs and the full vs discounted gain may sit at different points on the shade-in curve. Consistent with §2 ("the system does not implement the bracket table"), the heuristic uses the flat 2% and is only valid for an individual above the §7.1 threshold — the system's primary use case (a member at or near the Division 296 threshold, §2).

**Discount fraction `d`** (§2): 0.5 individual; exact `1/3` SMSF (s 115-100(b)).

**Formula.** Equate sell-now after-tax `P_sell − (P_sell − cost)·r_eff` with sell-later after-tax `P − (P − cost)·d·r_eff` and solve for `P_sell`:

> P_sell = [ P·(1 − r_eff·d) − cost·r_eff·(1 − d) ] / (1 − r_eff)

**The cost coefficient is `(1 − d)`, not `d`** — the two coincide only for individuals (d = 0.5), so an SMSF (d = 1/3) computed with `d` overstates the break-even price.

**None (no meaningful answer) when:**

- already discount-eligible (`days_to_eligibility == 0`, §5.1);
- no unrealised gain (`P ≤ cost`);
- `r_eff ≥ 1` (degenerate — the `(1 − r_eff)` denominator is non-positive). Validation of the marginal-rate *input* per §10 ("rate above 0.5 rejected") is the caller's responsibility; this heuristic does not re-validate it;
- the computed `P_sell ≤ cost` (degenerate: tiny gain, very high rate).

Quantize the result to cents with `ROUND_HALF_UP` (consistent with the CGT ledger convention).

**TC-22 (individual).** P=100, cost=40, marginal_rate=0.45 → r_eff=0.47, d=0.5, not yet eligible. numerator = 100·(1 − 0.235) − 40·0.47·0.5 = 76.5 − 9.4 = 67.1; /0.53 = **126.60**. Round-trip: sell-later nets 100 − 60·0.5·0.47 = 85.90; sell-now @126.60 nets 126.60 − 86.60·0.47 = 85.90. ✓

**TC-23 (SMSF).** P=100, cost=40, r_eff=0.15, d=1/3, not yet eligible. numerator = 100·(1 − 0.05) − 40·0.15·(2/3) = 95 − 4 = 91; /0.85 = **107.06**. Round-trip: sell-later nets 100 − 60·(1/3)·0.15 = 97.00; sell-now @107.06 nets 107.06 − 67.06·0.15 = 97.00. ✓

## 6. Division 296 (per ss 296-30 to 296-45 ITAA 1997 and Imposition Act 2026)

Division 296 imposes additional tax on superannuation earnings attributable to total superannuation balance (TSB) above $3 million, with a higher rate applying above $10 million. Enacted by the Treasury Laws Amendment (Building a Stronger and Fairer Super System) Act 2026 and the Superannuation (Building a Stronger and Fairer Super System) Imposition Act 2026, both with Royal Assent 13 March 2026, commencing 1 July 2026. First assessment year FY 2026-27.

### 6.1 Thresholds and indexation

- **Large superannuation balance threshold (LSBT, "tier 1")**: $3,000,000 at commencement, indexed in $150,000 increments by reference to CPI (s 296-30).
- **Very large superannuation balance threshold (VLSBT, "tier 2")**: $10,000,000 at commencement, indexed in $500,000 increments (s 296-35).

The system reads thresholds via the function:

> div_296_threshold_for_year(financial_year: int) -> tuple[Decimal, Decimal]

For FY 2026-27 this returns `(Decimal("3000000"), Decimal("10000000"))`. Future years are populated as the ATO publishes them. Before publication, querying a future year returns the most recently published values with a `provisional` flag — the flag is exposed in any output that depends on it. Provisional values are never silently substituted.

### 6.2 Inputs

- **TSB reference amount (TSB_ref)**: `max(TSB at start of year, TSB at end of year)` per s 296-40(2). For FY 2026-27 only, the transitional rule at ITTPA s 296-1 mandates `TSB_ref = TSB at 30 June 2027` (closing balance only). This rule is single-year.
- **Earnings**: Division 296 "superannuation earnings" attributable to the member. The redesigned legislation uses **realised fund taxable income, not change in TSB**. For SMSFs this is dividends (grossed-up), interest, rent, net realised capital gains (with the s 115-100 1/3 discount applied), less deductible expenses, attributed via actuarial certificate (s 296-55 + draft regulation 296-55.01). Per Heffron's technical note of 23 March 2026: the starting point is the fund's taxable investment income; the ECPI exemption is **ignored** for Division 296.

### 6.3 Tier 1 and Tier 2 — stacked proportion-of-TSB, not marginal

The methodology is stacked, both tiers using the whole TSB as denominator and applied independently to the same earnings figure. Each is computed against `TSB_ref`.

> # Tier 1 (s 296-40 + Imposition Act cl 4):
> if TSB_ref > LSBT and earnings > 0:
>     p1 = (TSB_ref − LSBT) / TSB_ref
>     tier_1 = earnings × p1 × 0.15
> else:
>     tier_1 = 0
>
> # Tier 2 (s 296-45 + Imposition Act cl 5):
> if TSB_ref > VLSBT and earnings > 0:
>     p2 = (TSB_ref − VLSBT) / TSB_ref
>     tier_2 = earnings × p2 × 0.10
> else:
>     tier_2 = 0
>
> total_div_296 = tier_1 + tier_2

The 0.10 in tier 2 is the additional rate above tier 1. The combined effective rate on earnings attributable to the proportion above $10M is 0.25 (0.15 + 0.10). Implementation must compute tier 2 as `earnings × p2 × 0.10` to avoid double-counting; phrasing the rule as "25% of the slice above $10M" is the effective-rate description, not the legislated mechanism.

Worked example, TSB $3.2M, earnings 5% ($160,000). p1 = ($3.2M − $3M) / $3.2M = 0.0625. Tier 1 = $160,000 × 0.0625 × 0.15 = $1,500. Tier 2 = 0. Total = $1,500.

Worked example, TSB $10.5M, earnings 5% ($525,000). p1 = ($10.5M − $3M) / $10.5M = 0.714286. Tier 1 = $525,000 × 0.714286 × 0.15 = $56,250. p2 = ($10.5M − $10M) / $10.5M = 0.047619. Tier 2 = $525,000 × 0.047619 × 0.10 = $2,500. Total = $58,750.

Worked example, TSB $12M, earnings $100,000 (per Bills Digest No. 48, 2025-26). p1 = 0.75; tier 1 = $100,000 × 0.75 × 0.15 = $11,250. p2 = 0.1667; tier 2 = $100,000 × 0.1667 × 0.10 = $1,667. Total ≈ $12,917.

### 6.4 Transitional cost base reset (per ITTPA s 296-50)

An SMSF (or other small superannuation fund with ≤ 6 members) may make an election to reset the cost base of every CGT asset held at the end of 30 June 2026 to its market value at that date, **for Division 296 purposes only**. Election characteristics:

- **All-or-nothing at fund level.** Applies to every CGT asset held by the fund at 30 June 2026, including assets in unrealised loss. Cherry-picking is not permitted.
- **Lodged in the ATO-approved form by the due date of the fund's 2026-27 annual return.**
- **Irrevocable.**
- **Affects Division 296 calculations only.** Ordinary fund CGT under s 102-5 and s 115-100 continues to use the original cost base.

Each lot in the system carries two cost bases:

- `cost_base_normal` — actual acquisition cost, used for ordinary fund CGT.
- `cost_base_div296` — market value at 30 June 2026 if the election was made, otherwise equal to `cost_base_normal`.

On disposal after 1 July 2026, both calculations run independently. The Division 296 earnings input uses the gain computed from `cost_base_div296` (with the 1/3 discount mirrored per s 115-100). The fund's tax return uses `cost_base_normal`.

Worked example. Asset acquired 1 January 2020 for $50,000, market value at 30 June 2026 $80,000, disposed 1 January 2027 for $100,000, SMSF with election made, accumulation phase, no other CGT events. **Fund CGT**: gross gain $50,000, 1/3 discount $16,667, net $33,333, tax at 15% = $5,000. **Division 296 earnings**: gross gain (reset base) $20,000, 1/3 discount $6,667, included $13,333. The $13,333 is aggregated with other fund earnings, attributed to the member, and runs through §6.3.

Larger APRA funds (more than 6 members) use a different four-year phase-in under ITTPA s 296-60 (out of v1 scope; the system models SMSFs only).

### 6.5 Election warning for depreciated assets

When recommending the election to a user, the system must surface a warning if any fund asset is in unrealised loss at 30 June 2026. Under the as-enacted ITTPA s 296-50, the all-or-nothing rule resets the cost base to market value unconditionally — there is no "greater of cost base or market value" fallback in the legislation. For a depreciated asset, the election locks in a lower cost base for Division 296, eliminating the pre-2026 capital loss from future Division 296 earnings.

> **Pending accountant verification (carried from §10):** whether ATO administrative guidance is expected to introduce a "greater of cost base or market value" interpretation, and whether such guidance would change the recommended election strategy for SMSFs holding any depreciated assets. The spec's current behaviour is to surface the warning and let the user decide; revisit if the ATO clarifies.

### 6.6 Out of v1 scope for Division 296

- Member-level attribution mechanics for multi-member SMSFs (the draft regulation 296-55.01 has not been registered as at 2026-05-19; the system assumes single-member funds for v1, or accepts a user-supplied attribution percentage as input).
- Mid-year transitions (e.g., a member starting a pension on 1 January).
- Reserve allocations.
- Anti-detriment / death benefit pension transitions.

## 7. Medicare levy (per s 251S(1)(a) ITAA 1936 and Medicare Levy Act 1986)

The Medicare levy is applied to **taxable income** for individual taxpayers. Taxable income includes the net capital gain (s 102-5, after losses and after the s 115-100 discount) and the grossed-up dividend income (for franked dividends, this is the cash plus the franking credit). The levy therefore stacks on the marginal income tax rate at the same 2% rate on the same base.

The levy does not apply to super funds (whether accumulation, pension, or mixed phase) and does not apply to companies.

### 7.1 Low-income thresholds

The 2% rate is reduced or zero for individuals below specified income thresholds. For FY 2026 (single), per the May 2026 Federal Budget retroactive increase: no levy below approximately $28,011; full levy at approximately $35,014. The 2024 figures of $26,000 / $32,500 are obsolete and must not be used. The v1 system sources current thresholds from the ATO's annually published "Medicare levy thresholds" page rather than hardcoding them.

### 7.2 Out of v1 scope (Medicare-adjacent)

- **Medicare levy surcharge** (additional 1.0–1.5% for high-income individuals without private hospital cover). Imposed under separate Acts. Not implemented in v1; the user applies a manual adjustment if needed.
- **Division 293** (additional 15% on concessional super contributions for income > $250k). Income definition includes net capital gain. Not implemented.
- **HELP/HECS repayment**. Repayment income includes net capital gain. Not implemented.

## 8. Foreign exchange gain/loss — US equities (Div 775, M15)

### 8.1 Statutory basis

When an Australian resident disposes of a foreign-currency asset (e.g. a US-listed ESPP or stock holding), any gain or loss attributable solely to currency movement is a **forex realisation event** under Division 775 ITAA 1997. This is a separate CGT event from the equity disposal itself.

Key sections:
- **s 775-15** — forex realisation event (gain): forex amount brought to account as ordinary income or included in assessable income.
- **s 775-20** — forex realisation event (loss): deductible under s 775-20(1) or (2).
- **s 775-30 — $250 de minimis**: if the absolute value of the forex gain or loss is ≤ AUD 250 for the income year across all forex realisation events, the taxpayer may elect to disregard all forex gains and losses for that year. System implementation: compute forex gain/loss; if ≤ $250 flag for user attention; do not automatically apply the election (the election is irrevocable for the year and the user must decide).
- **ATO TR 2019/1** — translation rules. The applicable exchange rate for translation is the **Reserve Bank of Australia (RBA) spot rate** on the date of the relevant event. EODHD AUDUSD.FOREX close prices are treated as equivalent to the RBA spot rate for system purposes (system rule, not ATO-mandated; user should verify with an accountant if values are material).

### 8.2 FX gain/loss calculation formula

For a disposed US lot:

```
acquisition_rate = AUDUSD rate on acquired_at (USD per 1 AUD)
disposal_rate    = AUDUSD rate on disposed_at (USD per 1 AUD)

cost_base_aud    = cost_base_usd / acquisition_rate
proceeds_aud     = disposal_proceeds_usd / disposal_rate

fx_gain_aud      = proceeds_aud - cost_base_aud
                 (positive = forex gain = ordinary income under s 775-15)
                 (negative = forex loss = deductible under s 775-20)
```

Note: `fx_gain_aud` is the FX component only, not the equity gain. The equity gain/loss (in AUD) is computed separately via the standard §5 CGT path using `cost_base_normal` and the AUD proceeds.

The **equity CGT gain** and the **Div 775 forex gain** are independent:
- Equity gain is subject to CGT discount (50% for individual held > 12 months; 33⅓% for SMSF).
- Div 775 forex gain is ordinary income or loss — **not** subject to CGT discount.

### 8.3 Implementation contract (M15-7)

`asxos/domain/tax/fx_gain.py` — `fx_capital_gain(lot: HoldingLot) -> Decimal | None`:
- Returns `None` for ASX lots (no `cost_base_usd` / FX fields).
- Returns `None` if any required FX rate is missing (system cannot compute — flag for user).
- Returns `Decimal` (may be positive or negative) for disposed US lots with complete FX data.
- Hard-fails (raises `ValueError`) if `disposal_fx_rate` is zero or negative.
- Hard-fails if `abs(result)` would be arithmetically impossible (sanity check only; no business threshold).

The function does **not** apply the $250 de minimis election. That decision belongs to the user. The calling code in `asxos/domain/tax/positions.py` flags `forex_gain_aud` on each disposed US lot; the user sees the value and makes the election when filing.

### 8.4 Div 775 vs s 104-10 (CGT event A1) — non-overlap

The ATO treats Div 775 and CGT event A1 as distinct events with no double-count. The equity disposal (A1) uses the AUD amount at the time of disposal; the FX movement on the AUD principal is the Div 775 event. Implementation must not add them together — they are reported separately on the tax return.

### 8.5 ESS/ESPP treatment

For ESPP shares (Division 83A), the income inclusion on vesting is the assessable discount. The cost base for CGT and Div 775 purposes starts at the market value on vesting date (not the discounted grant price), per s 130-80 ITAA 1997. **v1 of the system does not implement Division 83A; ESPP lots are imported with the user-supplied cost base and the system treats them as ordinary purchase lots.** The user must verify cost base with an accountant before filing. See §9.

### 8.6 Out of scope for M15

- Treaty withholding credits (US 15% withholding on dividends) — not implemented. User must manually claim foreign income tax offset under s 770-10 ITAA 1997.
- Currencies other than USD — not implemented. System only supports AUDUSD.
- RBA Table F11.1 direct ingestion — EODHD AUDUSD.FOREX is used as the rate source.
- Mid-year average rate election under s 775-45 — not implemented. System uses transaction-date rates only.

## 9. Division 83A — ESS (reserved for v2)

V1 does not implement employee share scheme tax treatment. The spouse's CRM ESPP tranches (per memory) and any other ESS position will produce wrong tax answers in v1; the user must not rely on v1 outputs for any ESS position.

V1 data model accommodation: every position has an `acquisition_type` field defaulting to `"purchase"`. ESS positions are tagged with `"ess_upfront"` or `"ess_deferred"` for v2 to dispatch on. V1 ignores the field.

## 10. Defaults, edge cases, and ambiguity

Each ambiguous case is resolved here. Implementation must follow these resolutions exactly. Departures require a spec amendment.

**Unknown franking rate for a security.** Default the corporate tax rate to 0.30 and log a warning identifying the security. Silent assumption is forbidden.

**Missing franking percentage on a dividend record.** Treat as fully unfranked (franking_pct = 0). Do not assume full franking. Zero franking is a valid common state.

**CGT discount boundary day.** The disposal must occur on or after the date one year and one day after acquisition. A disposal exactly 365 calendar days after acquisition does not qualify in non-leap-year spans (see §5.1). Use calendar arithmetic, not day-count arithmetic.

**Listed-share acquisition and disposal dates.** Use the contract date, not the settlement date (s 109-5 for acquisition; s 104-10(3) for CGT event A1).

**Capital loss optimal ordering.** The taxpayer chooses the order in which losses are applied. The system implements the optimal order (non-discount first) by default. The user can override only by manually supplying a pre-netted gain.

**Capital loss exceeding total gain.** The result is a net capital loss carried forward. v1 stores it as `net_capital_loss_cf`; v1 does not deduct it from the user's ordinary income (capital losses cannot offset ordinary income in Australia). The user provides next year's `carried_forward_losses` as a scalar input — v1 does not automatically track multi-year loss balances.

**Holding period straddling Division 296 commencement.** If the SMSF made the s 296-50 ITTPA election, `cost_base_div296` is the 30 June 2026 market value; otherwise it equals `cost_base_normal`. The fund's ordinary CGT calculation is unaffected by the election.

**Depreciated asset under s 296-50 election.** *Pending accountant verification.* The as-enacted text uses market value unconditionally. A depreciated asset locks in a lower Division 296 cost base, extinguishing the pre-2026 loss from future Division 296 earnings. The system surfaces a warning when any asset is in unrealised loss at the reset date; it does not unilaterally exclude such assets from the election. Revisit once the ATO publishes administrative guidance.

**Marginal rate change mid-year for an individual.** The user provides a single marginal rate per income year. The system does not split the year. If the user's situation changes mid-year (e.g. retirement triggers a bracket drop), they run the calculation twice for the two periods and combine results manually.

**Mid-year phase change inside an SMSF.** The user provides a single `fund_pension_proportion` per income year, matching the actuarial certificate. The system does not model intra-year transitions. Reserve allocations and anti-detriment pension transitions are out of v1 scope.

**Provisional Division 296 thresholds for future years.** The function returns the most recent published values with `provisional=True` for years the ATO has not yet published. The flag must propagate to any output that depends on the value. Pending accountant verification: whether this matches industry practice for projected liability calculations.

**Zero cash dividend with non-zero franking credit.** Rejected as malformed; surface a validation error.

**Negative marginal rate or rate above 0.5.** Rejected by validation.

**45-day holding period violation.** If a disposal is recorded within 45 days of acquisition and a dividend was paid during the holding period, the system warns that franking credits may be denied under s 207-145. It does not unilaterally remove the credit — the user makes the call.

## 11. Test cases

Each case below must be covered by a unit test referencing the spec section.

| ID | Inputs | Expected | Spec ref |
|----|--------|----------|----------|
| TC-01 | $1,000 fully franked dividend, 30% company, individual 37% | After-tax cash $871.43 | §4.1 |
| TC-02 | $1,000 fully franked dividend, 25% base-rate entity, individual 37% | After-tax cash $813.33 | §3, §4.1 |
| TC-03 | $1,000 fully franked dividend, 30% company, individual 47% | After-tax cash $728.57 | §4.1 |
| TC-04 | $1,000 fully franked dividend, 30% company, SMSF accumulation (fund_pension_proportion=0.0) | After-tax cash $1,214.29 | §4.2 |
| TC-05 | $1,000 fully franked dividend, 30% company, SMSF 100% pension (fund_pension_proportion=1.0) | After-tax cash $1,428.57 | §4.2 |
| TC-06 | $1,000 50%-franked dividend, 30% company, individual 37% | After-tax cash $740.72 | §3, §4.1 |
| TC-07 | $1,000 unfranked dividend, individual 37% | After-tax cash $610.00 | §4.1 |
| TC-08 | Position 1 (CBA $2,250 dividend, individual 37%) | After-tax cash $1,960.71 | §4.1 |
| TC-09 | Position 2 (BHP $2,000 dividend, single-member SMSF, fund_pension_proportion=0.0) | After-tax cash $2,428.57 | §4.2 |
| TC-10 | $10,000 gain on asset acquired 2024-01-01, disposed 2025-01-01, individual 37% | Discount NOT eligible. Taxable gain $10,000. Tax $3,900. | §5.1 |
| TC-11 | $10,000 gain on asset acquired 2024-01-01, disposed 2025-01-02, individual 37% | Discount eligible. Net gain $5,000. Tax $1,950. | §5.1, §7 |
| TC-12 | $10,000 gain on asset acquired 2024-01-01, disposed 2025-01-02, SMSF fund_pension_proportion=0.0 | Discount eligible (1/3). Net gain $6,666.67. Fund tax $1,000.00. | §5.1, §5.2 |
| TC-13 | TSB $3.2M, earnings $160,000 | Div 296 liability $1,500 | §6.3 |
| TC-14 | TSB $10.5M, earnings $525,000 | Div 296 liability $58,750 | §6.3 |
| TC-15 | TSB $2,999,999, earnings $150,000 | Div 296 liability $0 | §6.3 |
| TC-16 | TSB $3,000,000, earnings $150,000 | Div 296 liability $0 (proportion = 0) | §6.3 |
| TC-17 | TSB $12M, earnings $100,000 | Div 296 liability $12,917 (tier 1 $11,250 + tier 2 $1,667) | §6.3 |
| TC-18 | Discountable gains $30,000, non-discountable $10,000, CY loss $15,000, CF loss $5,000, individual 37% | Net gain $10,000. Tax $3,900. (Optimal ordering verified.) | §5.2 |
| TC-19 | $1,000 fully franked dividend, 30% company, mixed-phase SMSF fund_pension_proportion=0.60 | After-tax cash $1,342.86 | §4.2 |
| TC-20 | Asset acquired 2020-01-01 for $50,000, MV at 2026-06-30 $80,000, disposed 2027-01-01 for $100,000, SMSF accumulation with s 296-50 election | Fund CGT: net gain $33,333, tax $5,000. Div 296 earnings input: $13,333. | §6.4 |
| TC-21 | Disposal 30 days after acquisition with dividend paid during the period | Warning surfaced; franking credit not auto-removed. | §4.3 |
| TC-22 | Break-even: P=100, cost=40, individual marginal 0.45 (r_eff 0.47), not yet eligible | Break-even sale price $126.60 (sell-now nets = sell-later nets = $85.90) | §5.4 |
| TC-23 | Break-even: P=100, cost=40, SMSF (r_eff 0.15, d=1/3), not yet eligible | Break-even sale price $107.06 (sell-now nets = sell-later nets = $97.00) | §5.4 |

## 12. Authoritative sources

**Division 296 legislation and analysis.** Treasury Laws Amendment (Building a Stronger and Fairer Super System) Act 2026 (Cth); Superannuation (Building a Stronger and Fairer Super System) Imposition Act 2026 (Cth); both received Royal Assent 13 March 2026.

- Parliamentary Library Bills Digest No. 48, 2025-26 (worked examples verifying stacked proportion methodology)
- [Latest update on Division 296 tax as we begin 2026 — Grant Thornton Australia](https://www.grantthornton.com.au/insights/client-alerts/latest-update-on-division-296-tax-as-we-begin-2026/)
- [Division 296 Tax Explained — Heffron](https://landing.heffron.com.au/division-296-news-and-resources)
- [Division 296 Tax: Draft Legislation Released — Heffron](https://www.heffron.com.au/news/division-296-tax-draft-legislation-released)
- [Revised Div 296 legislation introduced — SMS Magazine](https://smsmagazine.com.au/news/2026/02/11/revised-div-296-legislation-introduced/)
- [Division 296 Passed: New Super Tax Rules — Moore Australia](https://www.moore-australia.com.au/news/division-296-superannuation-changes/)
- [Major Changes to Division 296 with No Tax on Unrealised Capital Gains — Yield Financial Planning](https://yieldfinancialplanning.com.au/major-changes-to-division-296-with-no-tax-on-unrealised-capital-gains/)
- [Understanding the new Division 296 superannuation tax changes — BDO Australia](https://www.bdo.com.au/en-au/insights/superannuation/understanding-the-new-division-296-superannuation-tax-changes)
- Heffron technical note (23 March 2026), Sladen Legal, DBA Lawyers, Maddocks / Cleardocs commentary on s 296-50 ITTPA

**ITAA 1997 — Division 296 (inserted by Schedule 1 of the Amending Act).** s 296-30 (LSBT), s 296-35 (VLSBT), s 296-40 (tier 1 earnings), s 296-45 (tier 2 earnings), s 296-55 (member attribution; draft regulation 296-55.01 unregistered as at 2026-05-19).

**ITAA 1997 — superannuation phase methodology.** s 295-385 (segregated method), s 295-390 (proportionate method), s 295-387 (disregarded small fund assets, $1.6M threshold, not indexed).

**ITTPA — transitional cost base.** s 296-50 (small fund election), s 296-60 (large APRA fund four-year phase-in, out of v1 scope), s 296-1 (FY 2026-27 closing-balance-only TSB rule).

**ITAA 1997 — CGT and net capital gain.** s 102-5 (net capital gain computation; Notes 1 and 2 confirm taxpayer's discretion in loss ordering), s 115-25 (12-month rule), s 115-100 (50% individual / 1/3 super discount), s 109-5 (acquisition date table for shares), s 104-10 (CGT event A1).

- [CGT discount — Australian Taxation Office](https://www.ato.gov.au/individuals-and-families/investments-and-assets/capital-gains-tax/cgt-discount)
- [ITAA 1997 section 115-25 — AustLII](https://classic.austlii.edu.au/au/legis/cth/consol_act/itaa1997240/s115.25.html)
- Taxation Determination TD 2002/10 (clear 12-month period interpretation)
- [Using capital losses to reduce capital gains — Australian Taxation Office](https://www.ato.gov.au/individuals-and-families/investments-and-assets/capital-gains-tax/using-capital-losses-to-reduce-capital-gains) (last updated 23 June 2025; endorses non-discount-first ordering)

**ITAA 1997 — franking and refundability.** s 67-25 (refundable franking offset for complying super funds), Division 207 (imputation), Subdivision 207-F (refundability), s 207-145 (45-day qualified-person rule), s 177EA (general anti-avoidance, out of v1 scope).

- [Allocating franking credits — Australian Taxation Office](https://www.ato.gov.au/businesses-and-organisations/corporate-tax-measures-and-assurance/imputation/paying-dividends-and-other-distributions/allocating-franking-credits)
- ATO SMSF Annual Return Section D instructions (label E1, refundable franking offset)

**Income Tax Rates Act 1986 and BRE.** s 23AA (corporate tax rate), s 23AB (base-rate entity passive income), Law Companion Ruling LCR 2019/5 (base-rate entity classification).

- [Changes to company tax rates — Australian Taxation Office](https://www.ato.gov.au/tax-rates-and-codes/company-tax-rate-changes)
- [Demystifying base rate entities — Wolters Kluwer](https://www.wolterskluwer.com/en-au/expert-insights/demystifying-base-rate-entities)

**ITAA 1936 and Medicare Levy.** s 251S(1)(a) (Medicare levy on taxable income); Medicare Levy Act 1986 (rate and threshold mechanics); PwC Australia Federal Budget analysis May 2026 (FY 2026 low-income threshold update).

**Foreign exchange (for v2).** [RBA Statistical Tables — Exchange Rates F11.1](https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv).

Direct fetching of the ATO franking and CGT pages returned 403 during preparation of v1.0; v1.1 confirms via the AustLII statutory text, the audit's verification against the Parliamentary Library Bills Digest, and the cross-referencing of the practitioner sources above. Before implementation cuts code, the final step is a direct read of the compiled Acts on the Federal Register of Legislation.

## 13. Change log

**v1.3, 2026-06-28.** Adds §5.4 (CGT discount break-even price) to give the position-monitor heuristic a governing spec home, and corrects a tax-math error in the existing implementation:
- Added §5.4: the break-even formula `P_sell = [P·(1 − r_eff·d) − cost·r_eff·(1 − d)] / (1 − r_eff)`, derived by equating sell-now and sell-later after-tax proceeds. **The cost coefficient is `(1 − d)`, not `d`** — the prior implementation used `d`, which is correct only for individuals (d=0.5) and overstates the break-even for SMSFs (d=1/3).
- §5.4 effective rate: individual `r_eff = marginal + 0.02` (Medicare applies to the net capital gain on both sides, §5.3/§7); SMSF `r_eff = 0.15` (§2), Medicare 0. Discloses that the flat 2% is valid only above the §7.1 low-income shade-in band.
- Added TC-22 (individual) and TC-23 (SMSF) to the §11 matrix, with round-trip-verified worked numbers. TC-23 is the regression lock against the old `d`-coefficient bug.

**v1.2, 2026-05-27.** M15 US equities extension — §8 rewritten from "reserved for v2" placeholder to full Div 775 specification:
- Added §8.1: statutory basis (s 775-15, s 775-20, s 775-30, ATO TR 2019/1).
- Added §8.2: FX gain/loss formula with cost_base_usd / disposal_proceeds_usd translation.
- Added §8.3: `fx_capital_gain()` implementation contract (M15-7).
- Added §8.4: Div 775 vs CGT event A1 non-overlap rule.
- Added §8.5: ESPP/ESS cost-base note (v1 uses user-supplied cost base; user must verify with accountant).
- Added §8.6: M15 out-of-scope items (treaty withholding, non-USD currencies, RBA direct ingest, mid-year average rate election).

**v1.1, 2026-05-19.** Integrates the technical audit dated 2026-05-19 against the as-enacted Acts. Eight substantive changes:

- **§2 Account types restructured.** Removed "SMSF accumulation" and "SMSF pension" as separate types. Single SMSF type with `fund_pension_proportion ∈ [0.0, 1.0]` and `fund_segregated_eligible: bool`. Rationale: DSFA rule at s 295-387 bars segregation for any SMSF with member TSB > $1.6M receiving a retirement-phase pension, making the proportionate method mandatory in practice. (Audit Issue 3.)
- **§3 Franking gross-up.** Added the rule that the system trusts the franking credit amount on the dividend statement as authoritative; the gross-up formula is the validation and fallback path, not the production calculation. Added LCR 2019/5 and s 23AA/23AB Income Tax Rates Act 1986 citations. (Audit Issue 7.)
- **§4.2 SMSF dividend math.** Rewritten to implement the proportionate method (s 295-390): ECPI exempt component, taxable component, fund tax, full franking offset retention under s 67-25 + Div 207. Added 45-day holding period warning under s 207-145 (§4.3). (Audit Issues 3, 6.)
- **§5 CGT and net capital gain.** Added s 102-5 statutory framework. Added optimal-loss-ordering algorithm per s 102-5 Notes 1 and 2 (apply losses against non-discount gains first). Added TD 2002/10 citation. Added s 109-5 / s 104-10 contract-date rule. (Audit Issues 5, 8.)
- **§6 Division 296.** Restated with full statutory citations (s 296-30 through s 296-45; ITTPA s 296-50). Confirmed stacked proportion-of-TSB methodology (not marginal). Clarified TSB_ref = max(opening, closing) with FY 2026-27 transitional rule (closing only). Replaced "balance × earnings_rate" simplification with realised-fund-taxable-income definition. Added the s 296-50 cost-base-reset election as a fund-level all-or-nothing irrevocable choice; introduced `cost_base_div296` per lot. Added depreciated-asset warning. (Audit Issues 1, 2.)
- **§7 Medicare levy.** Added s 251S(1)(a) ITAA 1936 citation. Updated low-income thresholds to current FY 2026 values from May 2026 Federal Budget. Added MLS, Div 293, HELP/HECS as out-of-scope items. (Audit Issue 4.)
- **§10 Edge cases.** Added depreciated-asset election ambiguity (pending accountant verification). Added mid-year SMSF phase change as out of scope. Added 45-day rule warning behaviour.
- **§11 Test cases.** Updated SMSF cases for `fund_pension_proportion` model. Added TC-17 (Bills Digest $12M example), TC-18 (optimal loss ordering), TC-19 (mixed-phase SMSF dividend), TC-20 (cost base reset on disposal), TC-21 (45-day warning).

**v1.0, 2026-05-19.** Initial specification derived from Phase A verification findings.
