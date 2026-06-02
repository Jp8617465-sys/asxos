"""
HUBS ESPP Position — Scenario Analysis (2026-06-02)

Position:  24 shares HUBS.NYSE
Acquired:  May 31, 2026  via ESPP
Price:     USD $187.54/share
FX acq:    AUD/USD 0.7162 on May 31 (1 USD = 1.3962 AUD)

Uses asxos CGT and FX modules exactly as they run for ASX lots.
FX gain under Division 775 is reported SEPARATELY from the equity CGT event.
Stage classifier context: LATE-RETAIL | Underlying: CONFIRMING +5.75%

Disclaimer: This is modelling, not financial advice. Australian ESS rules
(Division 83A) may alter the cost base — consult a tax advisor.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from asxos.domain.tax.cgt import (
    days_to_eligibility,
    is_discountable,
    net_capital_gain,
)
from asxos.domain.tax.types import CapitalGain

# ── Position constants ────────────────────────────────────────────────────────

ACQUIRED        = date(2026, 5, 31)
SHARES          = Decimal("24")
COST_USD        = Decimal("187.54")          # per share
FX_ACQ          = Decimal("0.7162")          # AUD/USD at acquisition
FX_NOW          = Decimal("0.7177")          # AUD/USD today (2026-06-02)
ACCOUNT         = "individual"
MARGINAL_RATES  = [Decimal("0.325"), Decimal("0.390"), Decimal("0.470")]
MARGINAL_LABELS = ["32.5% (incl. Medicare)", "39% (incl. Medicare)", "47% (top + Medicare)"]

TODAY = date(2026, 6, 2)
CGT_DISCOUNT_DATE = ACQUIRED + relativedelta(years=1) + timedelta(days=1)  # spec §5.1

COST_BASE_USD   = SHARES * COST_USD
COST_BASE_AUD   = COST_BASE_USD / FX_ACQ

# ── Scenario price/date pairs ─────────────────────────────────────────────────
# (label, usd_price, disposal_date, note)
SCENARIOS = [
    ("A — Sell Now",
     Decimal("252"),
     TODAY,
     "Lock in 34% USD gain. No CGT discount (held 2 days). Retail spike risk removed."),

    ("B — Hold to 50d MA breakdown / sell at stop",
     Decimal("230"),
     date(2026, 7, 15),  # approx if stops triggered in ~6 weeks
     "Defensive: stop below 50d MA ($243). Accept smaller gain, avoid drawdown if LATE-RETAIL fades."),

    ("C — Sell at analyst consensus target",
     Decimal("280"),
     date(2026, 9, 30),  # ~4 months — within 12-month window
     "Sell at $280 consensus. Still pre-12-month mark → no CGT discount. Best USD outcome pre-discount."),

    ("D — Hold to 12-month CGT discount, sell at current price",
     Decimal("252"),
     CGT_DISCOUNT_DATE,
     f"Hold to {CGT_DISCOUNT_DATE} (spec §5.1 calendar arithmetic). 50% CGT discount on same price."),

    ("E — Hold to 12-month mark, price at 200d MA ($318)",
     Decimal("318"),
     CGT_DISCOUNT_DATE,
     "Best case: institutional confirmation + CGT discount. 200d MA crossover = re-rating to 'mainstream' stage."),

    ("F — Blow-off / late-retail continuation to $350",
     Decimal("350"),
     date(2026, 8, 31),  # retail spike fades within 90 days — pre-12-month
     "LATE-RETAIL continuation. Higher USD return but no discount and FOMO-driven — stage classifier flags fade risk."),
]

# ─────────────────────────────────────────────────────────────────────────────

def aud_gain(usd_price: Decimal, disposal_date: date) -> tuple[Decimal, Decimal, Decimal]:
    """Returns (proceeds_aud, equity_cgt_gain_aud, div775_fx_gain_aud)."""
    # For the FX calc asxos uses AUD/USD rates at acquisition and disposal.
    # We approximate disposal FX as current (for near-term scenarios).
    fx_disposal = FX_NOW  # simplified: same rate for all scenarios

    proceeds_usd = SHARES * usd_price
    proceeds_aud = proceeds_usd / fx_disposal

    # Equity CGT: proceeds AUD minus cost base AUD (both at respective day's rate)
    equity_gain_aud = proceeds_aud - COST_BASE_AUD

    # Div 775: FX gain = cost base re-valued at disposal rate minus original cost base AUD
    # (captures pure currency movement on the USD principal)
    cost_base_at_disposal_rate = COST_BASE_USD / fx_disposal
    div775_fx_gain = cost_base_at_disposal_rate - COST_BASE_AUD

    return proceeds_aud, equity_gain_aud, div775_fx_gain


def tax_on_gain(
    equity_gain_aud: Decimal,
    disposal_date: date,
    marginal_rate: Decimal,
) -> tuple[Decimal, bool, str]:
    """Returns (tax_aud, discountable, note)."""
    discountable = is_discountable(ACQUIRED, disposal_date)
    holding_days = (disposal_date - ACQUIRED).days
    gain = CapitalGain(
        symbol="HUBS.NYSE",
        gain_aud=equity_gain_aud,
        discountable=discountable,
        holding_period_days=holding_days,
    )
    result = net_capital_gain(
        [gain],
        current_year_losses=Decimal("0"),
        carried_forward_losses=Decimal("0"),
        account_type=ACCOUNT,
    )
    tax = result.net_capital_gain * marginal_rate
    note = "50% CGT discount applied" if discountable else "No discount (< 12 months)"
    return tax, discountable, note


# ─────────────────────────────────────────────────────────────────────────────

print("=" * 70)
print("HUBS ESPP — Scenario Analysis  |  asxos CGT + Div 775 engine")
print(f"Position: 24 × $187.54 USD  |  acquired {ACQUIRED}  |  as of {TODAY}")
print(f"CGT discount eligible: {CGT_DISCOUNT_DATE}  (spec §5.1 calendar arithmetic)")
print(f"Cost basis: ${COST_BASE_USD:.2f} USD  =  ${COST_BASE_AUD:.2f} AUD")
print(f"Today's value: ${SHARES * Decimal('252'):.0f} USD  =  ${SHARES * Decimal('252') / FX_NOW:.0f} AUD  (at $252)")
print("=" * 70)

days_left = days_to_eligibility(ACQUIRED, TODAY)
print(f"\nDays until CGT discount eligible: {days_left} days ({CGT_DISCOUNT_DATE})\n")

for label, price, disposal_date, note in SCENARIOS:
    proceeds_aud, equity_gain_aud, fx_gain_aud = aud_gain(price, disposal_date)
    usd_gain = SHARES * (price - COST_USD)

    print(f"{'─' * 70}")
    print(f"Scenario {label}")
    print(f"  Exit price: ${price} USD  |  Date: {disposal_date}")
    print(f"  Note: {note}")
    print()
    print(f"  USD gain:         ${usd_gain:>10.2f}  ({(price/COST_USD - 1)*100:.1f}%)")
    print(f"  Proceeds (AUD):   ${proceeds_aud:>10.2f}")
    print(f"  Equity gain AUD:  ${equity_gain_aud:>10.2f}")
    print(f"  Div 775 FX gain:  ${fx_gain_aud:>10.2f}  (separate line on tax return)")
    print()
    print("  Tax at each marginal rate:")
    for rate, rate_label in zip(MARGINAL_RATES, MARGINAL_LABELS, strict=True):
        tax, discountable, disc_note = tax_on_gain(equity_gain_aud, disposal_date, rate)
        net = equity_gain_aud - tax
        print(f"    {rate_label:<30}  tax=${tax:>8.2f}  net=${net:>8.2f}  [{disc_note}]")
    print()

print("=" * 70)
print("RECOMMENDATION (from asxos classifiers):")
print("""
  Stage:      LATE-RETAIL  → retail spike 2.5x + below 200d MA ($318)
  Underlying: CONFIRMING   → VIX + HY OAS moving in your favour this week
  Regime:     risk_on_narrowing → supportive but not euphoric

  Classifier verdict: the macro tailwind is real but the stage signal says
  retail is already in. Classic fade risk between here and $318.

  Ranked scenarios by risk-adjusted after-tax outcome:

  1st  Scenario D — hold to CGT discount date, sell at current price
       Lowest risk + biggest tax saving vs selling now. Keeps position
       through any further upside. Only risk is 12 months of price exposure.

  2nd  Scenario E — hold to CGT discount + price reaches 200d MA ($318)
       Best absolute outcome if institutional breadth confirms. Stage
       classifier would re-label to 'mainstream' at that point.

  3rd  Scenario A — sell now
       Eliminates concentration risk (you hold job + stock in same co).
       Forgoes CGT discount but removes 12 months of equity risk. Tax cost
       vs D is ~$500–900 AUD depending on marginal rate — the price of
       certainty.

  4th  Scenario C — sell at $280 analyst target
       Slightly better USD return than A but still no CGT discount.
       Only worth it vs A if you believe $280 is reliably achievable
       before December 2026.

  Avoid:
  Scenario F — FOMO continuation to $350. Stage is LATE-RETAIL.
               Retail spikes reverse fast. Pre-12-month disposal with
               the worst tax efficiency.

  ESPP-specific note:
  You have human capital concentration in HubSpot (salary + stock).
  If HubSpot underperforms, you risk both income and investment
  simultaneously. This tilts toward D (hold for tax, not forever) over
  E (hold for price appreciation). The 200d MA at $318 is a natural
  reassessment point if reached.
""")
print("=" * 70)
print("Div 775 note: FX gains/losses are reported separately from equity CGT.")
print("The $250 de minimis election (s 775-30) may apply if total FX gain")
print("across all foreign lots in the year is under $250 AUD.")
print()
print("ESS note: If the ESPP discount was not taxed as income at acquisition")
print("under Division 83A, your cost base may be the market value at purchase")
print("(not $187.54 USD). This significantly reduces future CGT. Verify with")
print("your employer's ESS documentation and a tax adviser.")
print("=" * 70)
