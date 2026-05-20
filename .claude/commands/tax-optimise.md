# Australian Tax Optimisation Task

<context>
- Target: Australian retail investors using TradeSight AI
- Key features: CGT discount timing (12-month hold), tax-loss harvesting,
  franking credit optimisation, super vs personal account differentiation
- Must comply with ATO guidelines — general information only, not personal advice
- Portfolio data: Supabase, user_accounts FK via user_id
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- All tax calculations must reference current ATO rates and thresholds
- CGT discount: only available for assets held > 12 months
- Franking credits: must account for 45-day holding rule
- Super fund rules: different CGT rates (15% accumulation, 0% pension)
- Never present as personal financial advice — always general information
- Wash sale detection: flag repurchases within 30 days of tax-loss sale
- Soft deletes only (deleted_at TIMESTAMPTZ) — never hard-delete user tax data
</constraints>

<verify>
1. Tax calculations match ATO published rates for current FY
2. CGT discount correctly applied only to > 12 month holdings
3. Franking credit calculations account for 45-day holding period rule
4. All user-facing outputs include appropriate disclaimers
5. Edge cases: partial sales, multiple parcels, different acquisition dates
</verify>
