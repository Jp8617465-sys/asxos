# Phase A — Tax math verification against authoritative sources

Date: 2026-05-19. Verifier: this Claude Code session. Method: code reading plus authoritative-source comparison. No execution — the existing system does not run.

## Headline verdict

The existing tax alpha code is **mostly correct on the cases it covers, but has one present-day defect that affects every individual-account dividend calculation and one future-dated defect that will activate from FY 2027-28**. One feature required for Position 3 is absent entirely. The Phase 2 doc's assertion that "the math is correct" is partially supported and partially misleading.

Per the prompt's stopping rule — "If Phase A surfaces that the tax math has a real bug, stop the entire sequence" — I am stopping before Phase B. The Medicare-levy-on-dividends defect is real and present today.

## Code inventory

| Concept | File | Lines | Status |
|---------|------|-------|--------|
| Franking gross-up | `app/features/tax_alpha/models/tax_config.py` | 44–48 (constants), 201–229 (method) | Implemented for 30% companies only |
| CGT discount tiers | `app/features/tax_alpha/models/tax_config.py` | 29–36, 155–168 | Implemented correctly |
| CGT eligibility (12-month rule) | `app/features/tax_alpha/services/cgt_alert_service.py` | 172–175 | Implemented correctly |
| Division 296 thresholds | `app/features/tax_alpha/models/tax_config.py` | 50–62 | Hardcoded; no indexation |
| Division 296 projection | `app/features/tax_alpha/services/division_296_monitor.py` | 218–250 | Simplified projection; docstring stale |
| Foreign FX translation | — | — | Absent |
| Foreign withholding tax credit | — | — | Absent |
| Division 83A (ESS) | — | — | Absent |
| Medicare levy on dividends | `tax_config.py:201–229` | — | Missing from `after_tax_dividend_yield` |

## Authoritative sources used

Division 296 final legislation: Treasury Laws Amendment (Building a Stronger and Fairer Super System) Bill 2026, passed Senate 10 March 2026, Royal Assent 13 March 2026, commencing 1 July 2026. Confirmed via Grant Thornton, Heffron, SMS Magazine, Moore Australia, BDO Australia, and Yield Financial Planning analyses published February through April 2026.

Critical final-form details from these analyses:

- Thresholds $3M and $10M are indexed to inflation, with the $3M moving in $150,000 increments and the $10M in $500,000 increments. Indexation only triggers when CPI movement would push the base past the next increment.
- Earnings are calculated under "normal tax principles" — only realised earnings (dividends, interest, rent, realised capital gains net of carried-forward losses, with standard CGT discounting applied). The earlier draft that proposed taxing unrealised gains did not pass.
- A transitional cost base mechanism excludes gains accrued before 30 June 2026.
- For FY 2026-27 only, the assessment uses the 30 June 2027 balance rather than the greater of start/end balances.

RBA exchange rates: Table F11.1 daily exchange rates. 15 May 2023 USD/AUD spot 0.6682. (Used for Position 3.)

ATO franking and CGT pages returned 403 to direct fetch but the constants and formulas in the codebase are checked against widely published ATO summaries quoted in the auditing-firm and superannuation-industry sources above.

## Position 1: 500 CBA shares, fully franked, held 18 months, individual at 37% marginal

**Inputs.** CBA pays approximately A$4.50/share annualised (FY24-25 indicative). 500 shares × $4.50 = $2,250 cash dividend. CBA is a large company (turnover well above $50M), so the franking rate is 30%. Holding period 18 months = 547 days, well above the 12-month CGT threshold.

**Authoritative calculation.**

```
Cash dividend:        $2,250.00
Franking credit:      $2,250.00 × 0.30 / 0.70  = $964.29
Grossed-up income:    $2,250.00 + $964.29       = $3,214.29
Income tax at 37%:    $3,214.29 × 0.37          = $1,189.29
Medicare levy at 2%:  $3,214.29 × 0.02          = $64.29
Total tax:            $1,189.29 + $64.29        = $1,253.58
Less franking credit (refundable): $964.29
Net Australian tax:   $1,253.58 - $964.29       = $289.29
After-tax cash:       $2,250.00 - $289.29       = $1,960.71
```

CGT discount: held 547 days, so 50% individual discount applies to any realised gain on disposal. The code returns `eligible_today=True` and `cgt_discount_rate=0.50` for this position — correct.

**What the code produces.** Walking through `TaxConfig.after_tax_dividend_yield(dividend_yield=0.04, franking_pct=1.0)` with `marginal_rate=0.37` and `franking_refundable=True`:

```
franking_credit_yield = 0.04 × 1.0 × 0.4286 = 0.017144
grossed_up_yield      = 0.04 + 0.017144     = 0.057144
tax_on_grossed_up     = 0.057144 × 0.37     = 0.021143
franking_offset       = 0.017144 (refundable path)
after_tax             = 0.04 - 0.021143 + 0.017144 = 0.036001
```

Applied to a $56,000 holding paying 4% yield, the code returns an after-tax yield of 3.60%, or $2,016 of net income. Against the authoritative answer of $1,960.71, the code **overstates after-tax income by $55** on a $2,250 dividend.

**Root cause.** `TaxConfig.after_tax_dividend_yield` at `tax_config.py:221` computes `tax_on_grossed_up = grossed_up * self.marginal_rate` with no Medicare levy added. The companion function `TaxConfig.effective_tax_on_gain` at `tax_config.py:199` correctly applies `self.marginal_rate + self.medicare_levy_rate`. The dividend code path is inconsistent with the capital-gains code path.

**Magnitude.** For an individual at 37% marginal, the error is 2% of the grossed-up dividend per dollar of yield. For a $200,000 portfolio yielding 4% fully franked, the annual understatement of tax is approximately $228. For James personally, with whatever portfolio size he runs through this, the absolute number depends on his actual holdings. The error is structural and present in every individual-account run.

**Verdict.** **Port with fix.** Add the Medicare levy to `after_tax_dividend_yield`. Add a unit test at the exact boundary (a position that produces zero tax without Medicare and a positive figure with it).

## Position 2: 1,000 BHP shares, fully franked, held 8 months, SMSF accumulation

**Inputs.** BHP pays approximately A$2.00/share annualised. 1,000 × $2.00 = $2,000 cash dividend. BHP is a large company, 30% franking. Holding period 8 months = 243 days, below the 12-month CGT threshold.

**Authoritative calculation.**

```
Cash dividend:        $2,000.00
Franking credit:      $2,000.00 × 0.30 / 0.70 = $857.14
Grossed-up income:    $2,857.14
Tax at SMSF accumulation rate 15%: $2,857.14 × 0.15 = $428.57
Less franking credit (refundable for SMSF accumulation): $857.14
Net Australian tax:   $428.57 - $857.14 = -$428.57 (refund)
After-tax cash:       $2,000.00 + $428.57 = $2,428.57
```

Medicare levy does not apply to super funds, so no defect surfaces here. CGT discount eligibility: held 243 days, `days_held >= 365` evaluates False, no discount applies. The code returns no discount — correct.

**What the code produces.** Same walkthrough as Position 1 but with `marginal_rate=0.15`, `franking_refundable=True`, `medicare_levy_rate=0.0`:

```
franking_credit_yield = 0.04 × 1.0 × 0.4286 = 0.017144
grossed_up_yield      = 0.057144
tax_on_grossed_up     = 0.057144 × 0.15     = 0.008572
franking_offset       = 0.017144
after_tax             = 0.04 - 0.008572 + 0.017144 = 0.048572
```

On a notional 4% pre-tax yield, the code produces 4.86% after-tax — which represents a refund of franking credit beyond the tax payable, exactly the expected result for an SMSF in accumulation phase. Translating back to dollars: $2,000 cash + $428.57 refund = $2,428.57. **Matches the authoritative answer exactly.**

**Verdict.** **Port verbatim.** This case is correct.

## Position 3: 200 US-listed shares, USD dividend, held 3 years, SMSF with TSB $3.2M

**Inputs.** USD dividend, indicative $1.00/share quarterly × 4 = $4.00/share annualised. 200 shares × $4.00 USD = $800 USD annual dividend. US-Australia tax treaty caps US withholding tax on portfolio dividends at 15%. Holding period 3 years (well above 12 months). TSB at $3.2M (as of today, hypothetically). Today is 2026-05-19, Division 296 commences 2026-07-01 so first-year exposure applies from then.

**Authoritative calculation, dividend component.**

```
USD dividend:                  $800.00 USD
US withholding tax at 15%:     $120.00 USD withheld at source
Net USD received in fund:      $680.00 USD

Translation to AUD at RBA rate (illustrative 2023-05-15: 0.6682, so 1 USD = 1.4965 AUD):
  Gross AUD dividend:          $800.00 × 1.4965 = $1,197.20
  AUD withholding credit:      $120.00 × 1.4965 = $179.58
  Net AUD received:            $1,017.62

For SMSF accumulation at 15%, foreign-source dividend is assessable in AUD:
  Tax on grossed-up AUD:       $1,197.20 × 0.15 = $179.58
  Foreign tax credit:          $179.58
  Net Australian tax:          $0
  After-tax AUD:               $1,017.62
```

CGT on disposal (3 years held, in AUD terms with FX gain or loss bundled into the AUD cost-base movement): 33.33% SMSF accumulation discount applies. The code's `effective_tax_on_gain` at `tax_config.py:184` will compute this correctly for the AUD-denominated gain — provided the gain has been translated to AUD using the right method, which the existing code cannot do because there is no FX translation layer.

**Division 296 component, today (2026-05-19).**

```
Today's date:                  2026-05-19
Commencement:                  2026-07-01
days_to_commencement:          43
Today's liability:             $0 (not yet commenced)
projected_liability_5pct:      $3.2M × 0.05 × 0.0625 × 0.15 = $1,500
projected_liability_10pct:     $3.2M × 0.10 × 0.0625 × 0.15 = $3,000
```

Where `0.0625 = ($3,200,000 - $3,000,000) / $3,200,000`. The code's `_project_liability` reproduces this exactly for the current year. The status classification is `"tier_1"` (balance between $3M and $10M), `reset_election_available=True` (today is before 2027-06-30). Confirmed correct for FY 2026-27.

**What the code produces for Position 3.** The dividend and CGT components **cannot be computed** because:

- There is no FX translation function anywhere in the codebase. `grep -r "RBA\|fx_rate\|exchange_rate"` in `app/features/tax_alpha/` returns zero hits.
- There is no `foreign_holding_lots` table. The Phase 2 doc's v3 design is unimplemented.
- There is no foreign withholding tax credit calculation. The `franking_offset` path only handles Australian franking, not US-treaty withholding.

The Division 296 projection component is computable and correct for FY 2026-27. For later years, see the indexation defect below.

**Verdict.** **Rewrite from spec.** Position 3 requires three modules the existing code does not have: FX translation against RBA published rates, foreign withholding tax credit treatment, and a `foreign_holding_lots` table. The Division 296 portion is fine for the first year only.

## Defects found, ranked by severity

### Defect 1 (high, present-day): Medicare levy missing from after_tax_dividend_yield

File: `app/features/tax_alpha/models/tax_config.py:201–229`.

`after_tax_dividend_yield` applies `self.marginal_rate` but not `self.medicare_levy_rate`. Every individual-account dividend calculation understates tax by 2% of the grossed-up amount. The capital-gains function on the same dataclass at line 199 applies Medicare correctly. The inconsistency means the same dataclass returns internally inconsistent answers depending on which method is called.

Fix: change line 221 from `tax_on_grossed_up = grossed_up * self.marginal_rate` to `tax_on_grossed_up = grossed_up * (self.marginal_rate + self.medicare_levy_rate)`.

### Defect 2 (medium, future-dated): Division 296 thresholds hardcoded, no indexation

File: `app/features/tax_alpha/models/tax_config.py:50–62`.

`DIV_296_THRESHOLD_TIER_1 = 3_000_000` and `DIV_296_THRESHOLD_TIER_2 = 10_000_000` are module-level constants. The passed legislation indexes both — $3M moves in $150K increments, $10M in $500K increments, triggered by CPI growth. The code will produce correct answers for FY 2026-27 but will start drifting from FY 2027-28 onwards as soon as CPI moves the threshold to $3.15M.

Fix: replace the constants with a function `div_296_threshold_for_year(financial_year: int) -> tuple[Decimal, Decimal]` that reads from an indexation table (sourced from ATO published values once each year). For the first year only, the values are $3M and $10M; subsequent years are populated as the ATO publishes them.

### Defect 3 (medium, present-day for any small-cap holding): Franking gross-up assumes 30% company tax rate

File: `app/features/tax_alpha/models/tax_config.py:44`.

`FRANKING_GROSS_UP_FACTOR = 0.4286` is hardcoded as `0.30 / 0.70`. Base-rate entities (turnover under $50M, taxed at 25%) use `0.25 / 0.75 = 0.3333`. CBA and BHP are not base-rate entities so Positions 1 and 2 are unaffected. Any small-cap holding (Mineral Resources, Domino's Pizza Enterprises, many ASX 200 names below the threshold) will have its franking credit overstated by approximately 13% (the difference between 0.4286 and 0.3333 per dollar of franked dividend).

Fix: gross-up factor must be per-security or at least per-position, set when the security's corporate tax rate is known. The cleanest design is a `franking_rate` field on the security/holding row, defaulting to 0.30 but overridable per holding. The codebase memory note `S22-2.C` describes this exact change as "still pending."

### Defect 4 (low, documentation only): Division 296 docstring describes draft legislation, not passed law

File: `app/features/tax_alpha/services/division_296_monitor.py:13–14`.

The docstring states "Taxable earnings INCLUDES unrealised gains (most controversial aspect)." The final passed legislation does not tax unrealised gains. The docstring is stale by approximately two months. The implementation itself uses `balance * earnings_rate` as a simple forward projection and does not actually distinguish realised from unrealised, so this is a documentation bug rather than a computation bug. Still worth fixing because the docstring is misleading to anyone reading the code to understand the legislation.

### Absent: foreign holdings, RBA FX, withholding tax credit

No code exists for foreign holdings tax treatment. The Phase 2 doc lists `foreign_holding_lots` as an existing v3 design; it is not. James's spouse's CRM ESPP tranches (per memory) and any direct US holdings cannot be tax-treated by the current code. This is a feature gap, not a defect, but it must be built before any of these positions can be modelled.

### Absent: Division 83A (ESS upfront vs deferred)

No code. The spouse's CRM ESPP tranches require this treatment. Not in scope for Positions 1 and 2; relevant for James's broader use case.

## Recommendation

The Medicare-levy defect alone is enough to stop the sequence per the user's stopping rule. The fix is one line of code but the spec around it needs to be written down clearly before porting: every place that computes individual after-tax outcomes — dividend, capital gain, interest, foreign income — must apply Medicare levy unless the account type is super or company.

Before resuming with Phase B and Phase C, I recommend:

1. Decide whether the new tax module is a verbatim port (existing code plus the Medicare fix) or a fresh implementation from a written spec. Given that three of the four real defects above are spec issues rather than implementation issues, a written spec is probably the right starting point.
2. Capture the four defects above as the minimum spec corrections. The Division 296 indexation is non-urgent (FY 2027-28+) but should be in the spec so it doesn't get forgotten.
3. Decide whether foreign holdings and Division 83A are in scope for the rebuild's first quarter. If they are, the spec must cover them and the migration plan must include the `foreign_holding_lots` table. If they're not, the existing single-currency Australian-positions design is fine for M1–M6.

Phase B (failure postmortem) and Phase C (calendar) are paused pending this decision.

## Sources

- [Latest update on Division 296 tax as we begin 2026 — Grant Thornton Australia](https://www.grantthornton.com.au/insights/client-alerts/latest-update-on-division-296-tax-as-we-begin-2026/)
- [Division 296 Tax Explained — Heffron](https://landing.heffron.com.au/division-296-news-and-resources)
- [Division 296 Tax: Draft Legislation Released — Heffron](https://www.heffron.com.au/news/division-296-tax-draft-legislation-released)
- [Revised Div 296 legislation introduced — SMS Magazine](https://smsmagazine.com.au/news/2026/02/11/revised-div-296-legislation-introduced/)
- [Division 296 Passed: New Super Tax Rules — Moore Australia](https://www.moore-australia.com.au/news/division-296-superannuation-changes/)
- [Major Changes to Division 296 with No Tax on Unrealised Capital Gains — Yield Financial Planning](https://yieldfinancialplanning.com.au/major-changes-to-division-296-with-no-tax-on-unrealised-capital-gains/)
- [Understanding the new Division 296 superannuation tax changes — Lexology](https://www.lexology.com/library/detail.aspx?g=693cd3f6-54df-4d56-82dd-eb0fae1261a6)
- [Understanding the new Division 296 tax changes — BDO Australia](https://www.bdo.com.au/en-au/insights/superannuation/understanding-the-new-division-296-superannuation-tax-changes)
- [RBA Statistical Tables — Exchange Rates F11.1](https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv)

## Stop

Stopping per the prompt's instruction. Phase B and Phase C are not started. Awaiting your decision on the spec rewrite question before resuming.
