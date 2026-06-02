"""
HUBS.NYSE — Weekly Position Monitor

Run this each week with updated inputs to get a current read on:
  - Stage classifier: which signals are firing / fading
  - Underlying attribution: is the macro backdrop still supporting HUBS?
  - Scenario confirmation: which of your 6 scenarios is being confirmed/invalidated
  - Decision: hold, tighten stop, or sell early

Update the INPUT BLOCK below each week with fresh data from:
  - HUBS price + 50d MA + 200d MA: finance.yahoo.com/quote/HUBS
  - RSI + retail sentiment: stocktwits.com/symbol/HUBS or investing.com
  - VIX: finance.yahoo.com/quote/%5EVIX
  - US HY OAS: fred.stlouisfed.org/series/BAMLH0A0HYM2
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.domain.themes.stage_classifier import (
    ClassifierInput, StageThresholds, classify_stage, CLASSIFIER_VERSION
)
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.types import ThesisUnderlying, UnderlyingDirection
from asxos.domain.brief.cross_layer import cross_layer_observations
from asxos.domain.tax.cgt import days_to_eligibility, is_discountable

# ─────────────────────────────────────────────────────────────────────────────
# INPUT BLOCK — update these each week
# ─────────────────────────────────────────────────────────────────────────────

AS_OF           = date(2026, 6, 2)     # today's date

# Price levels
CURRENT_PRICE   = Decimal("252")       # HUBS last close (USD)
MA_50D          = Decimal("243.61")    # 50-day simple moving average
MA_200D         = Decimal("317.94")    # 200-day simple moving average

# Sentiment / retail
NEWS_SENTIMENT  = Decimal("0.72")      # 0–1 normalised (Stocktwits bullish ratio)
RETAIL_RATIO    = Decimal("2.50")      # current mentions / 90d avg (1.0 = normal)
AVG_WEEKLY_MOVE = Decimal("0.08")      # avg weekly price move magnitude (0.08 = 8%)

# Macro drivers (5d % change — negative = compressing/falling)
VIX_5D_MOVE     = Decimal("-8.0")      # VIX 5d % change (neg = vol falling = good for HUBS)
HY_OAS_5D_MOVE  = Decimal("-3.5")      # HY OAS 5d % change (neg = tightening = good)

# Regime (from market context — describe the US macro environment)
REGIME_LABEL    = "risk_on_narrowing"

# Position constants — don't change
ACQUIRED        = date(2026, 5, 31)
SHARES          = Decimal("24")
COST_USD        = Decimal("187.54")
STOP_PRICE      = Decimal("230")       # your stop-loss level
TARGET_INST     = Decimal("318")       # institutional confirmation (200d MA)
TARGET_ANALYST  = Decimal("280")       # sell-side consensus
CGT_DATE        = date(2027, 6, 1)     # 12-month CGT discount eligibility

# ─────────────────────────────────────────────────────────────────────────────
T = StageThresholds()

def _above_pct(price: Decimal, ma: Decimal) -> Decimal:
    return Decimal("1.0") if price > ma else Decimal("0.0")

stage_inputs = ClassifierInput(
    price_history_days=252,
    pct_above_50d_ma=_above_pct(CURRENT_PRICE, MA_50D),
    pct_above_200d_ma=_above_pct(CURRENT_PRICE, MA_200D),
    avg_weekly_move_pct=AVG_WEEKLY_MOVE,
    news_sentiment=NEWS_SENTIMENT,
    retail_mention_ratio=RETAIL_RATIO,
)

stage_result = classify_stage(stage_inputs, T)
stage_label, conditions = stage_result if stage_result else ("insufficient_data", [])

underlyings = [
    ThesisUnderlying(thesis_id=1, underlying_id=1, code="vix",
                     exposure=Decimal("0.50"), direction=UnderlyingDirection.negative,
                     last_validated_at=AS_OF),
    ThesisUnderlying(thesis_id=1, underlying_id=2, code="us_hy_oas",
                     exposure=Decimal("0.50"), direction=UnderlyingDirection.negative,
                     last_validated_at=AS_OF),
]
moves = {1: VIX_5D_MOVE, 2: HY_OAS_5D_MOVE}
score = score_thesis_underlying(underlyings, moves)
cross_obs = cross_layer_observations(REGIME_LABEL, [("HUBS.NYSE", "active", score)])

unrealised_pct = ((CURRENT_PRICE - COST_USD) / COST_USD * 100).quantize(Decimal("0.1"))
days_to_cgt = days_to_eligibility(ACQUIRED, AS_OF)
pct_to_stop = ((CURRENT_PRICE - STOP_PRICE) / CURRENT_PRICE * 100).quantize(Decimal("0.1"))
pct_to_200d = ((MA_200D - CURRENT_PRICE) / CURRENT_PRICE * 100).quantize(Decimal("0.1"))

# ─────────────────────────────────────────────────────────────────────────────

STAGE_EMOJI = {
    "early": "🌱", "early-institutional": "🔵", "broad-institutional": "🔵🔵",
    "mainstream": "📈", "late-retail": "⚠️", "mature": "🔴",
}
SCORE_EMOJI = {"confirming": "✅", "mixed": "⚡", "diverging": "❌"}

print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  HUBS.NYSE — Weekly Monitor                         {AS_OF}  ║
╠══════════════════════════════════════════════════════════════════╣
║  Position: {SHARES}×  Cost: ${COST_USD}  Current: ${CURRENT_PRICE}  P&L: +{unrealised_pct}%
║  CGT discount in: {days_to_cgt} days  ({CGT_DATE})
╚══════════════════════════════════════════════════════════════════╝
""")

print("── STAGE CLASSIFIER ─────────────────────────────────────────────")
print(f"  Stage: {STAGE_EMOJI.get(stage_label,'')} {stage_label.upper()}   (classifier {CLASSIFIER_VERSION})")
print()
print("  Signals status:")
print(f"    {'✅' if CURRENT_PRICE > MA_50D else '❌'} Above 50d MA   ${CURRENT_PRICE} {'>' if CURRENT_PRICE > MA_50D else '<'} ${MA_50D}   (need >${MA_50D} to stay emerging)")
print(f"    {'✅' if CURRENT_PRICE > MA_200D else '❌'} Above 200d MA  ${CURRENT_PRICE} {'>' if CURRENT_PRICE > MA_200D else '<'} ${MA_200D}  (need >${MA_200D} for MAINSTREAM re-label)")
print(f"    {'✅' if RETAIL_RATIO >= T.retail_mention_spike_pct else '❌'} Retail spike   {RETAIL_RATIO}× 90d avg  (threshold: {T.retail_mention_spike_pct}×)  {'⚠ high retail, watch for fade' if RETAIL_RATIO >= T.retail_mention_spike_pct else 'normalising — good'}")
print(f"    {'✅' if NEWS_SENTIMENT >= T.news_sentiment_high else '❌'} Sentiment high  {NEWS_SENTIMENT}  (threshold: {T.news_sentiment_high})")
print(f"    {'⚠' if AVG_WEEKLY_MOVE < T.momentum_slowdown_threshold else '  '} Momentum slow  {AVG_WEEKLY_MOVE:.0%}/wk  (< {T.momentum_slowdown_threshold:.0%} = mature signal — not firing)")
print()
print("  What would change the stage:")
print(f"    → MAINSTREAM:  price crosses ${MA_200D}  (you're {pct_to_200d}% away)")
print(f"    → EARLY-INST:  retail ratio falls below {T.retail_mention_spike_pct}× AND sentiment stays high")
print(f"    → EARLY:       retail fades AND price breaks below 50d MA (${MA_50D})")

print()
print("── UNDERLYING ATTRIBUTION ───────────────────────────────────────")
print(f"  Score: {SCORE_EMOJI.get(score.label,'')} {score.label.upper()}  (weighted movement: {score.weighted_movement:+.2f}%)")
print()
for comp in score.component_moves:
    direction_note = "falling = good for HUBS" if comp['code'] == 'vix' else "tightening = good for HUBS"
    move = comp.get('move_5d_pct', 'n/a')
    contrib = comp.get('contribution', 'n/a')
    print(f"  {'✅' if float(contrib or 0) > 0 else '❌'} {comp['code']:<12} 5d move: {move}%   contribution: {contrib}%   ({direction_note})")
print()
print("  What would flip to DIVERGING:")
print(f"    → VIX spikes above ~22–25 (risk-off event)")
print(f"    → US HY OAS widens above ~350bps (credit stress)")
print(f"    → Either 5d move turns positive (vol rising / spreads widening)")

print()
print("── CROSS-LAYER ──────────────────────────────────────────────────")
print(f"  Regime: {REGIME_LABEL}")
for obs in cross_obs:
    print(f"  · {obs}")

print()
print("── SCENARIO CONFIRMATION MATRIX ─────────────────────────────────")

scenarios = [
    ("A", "Sell Now",                    "confirmed" if unrealised_pct > 25 else "pending",
     f"Already at +{unrealised_pct}% — gain is real. Confirmed valid exit anytime.",
     "Price falls below cost basis ($187.54)"),

    ("B", "Stop at $230",                "active" if CURRENT_PRICE > STOP_PRICE else "TRIGGERED",
     f"Stop intact — ${pct_to_stop}% buffer above $230. 50d MA (${MA_50D}) is first warning.",
     f"Price breaks below ${STOP_PRICE} on volume → exit"),

    ("C", "Sell at $280 analyst target", "pending" if CURRENT_PRICE < 280 else "AT TARGET",
     f"${280 - CURRENT_PRICE} USD away ({((280-CURRENT_PRICE)/CURRENT_PRICE*100):.1f}%). Confirmed if retail spike sustains.",
     "Retail ratio falls below 1.5× before price reaches $280"),

    ("D", "Hold to CGT discount (same price)",  "ON TRACK",
     f"{days_to_cgt} days remaining. Position intact, macro confirming. Best risk-adj outcome.",
     "Stop triggered ($230) OR stage flips to EARLY (retail fades + breaks 50d MA)"),

    ("E", "Hold to CGT + price at $318", "in progress" if CURRENT_PRICE < TARGET_INST else "AT TARGET",
     f"${TARGET_INST - CURRENT_PRICE} USD away ({pct_to_200d}%). Confirmed only when 200d MA crossed.",
     "Any of: stop triggered, retail spike fades + no institutional follow-through"),

    ("F", "Blow-off to $350",            "risky",
     "Stage = LATE-RETAIL. Retail spikes are 2–4 week events. This requires rapid continuation.",
     "Retail ratio normalises below 1.5× → momentum gone. Pre-12-month disposal = worst tax."),
]

for code, name, status, confirm, invalidate in scenarios:
    status_icon = {"confirmed":"✅","ON TRACK":"✅","AT TARGET":"🎯","active":"🟡",
                   "pending":"⏳","in progress":"🔵","TRIGGERED":"🔴","risky":"⚠️"}.get(status,"·")
    print(f"\n  {status_icon} Scenario {code}: {name}  [{status}]")
    print(f"     Confirmation:  {confirm}")
    print(f"     Invalidation:  {invalidate}")

print(f"""
── WEEKLY DECISION ──────────────────────────────────────────────

  Stage:      {stage_label.upper()} {STAGE_EMOJI.get(stage_label,'')}
  Underlying: {score.label.upper()} {SCORE_EMOJI.get(score.label,'')} ({score.weighted_movement:+.2f}%)
  Stop gap:   {pct_to_stop}% above $230
  To 200d MA: {pct_to_200d}% above current price

  ┌─────────────────────────────────────────────────────────┐
  │  HOLD — Scenario D on track.                            │
  │  Macro confirming. Stop intact. CGT clock ticking.      │
  │                                                         │
  │  Watch this week:                                       │
  │  · HUBS price vs 50d MA (${MA_50D}) — don't break below │
  │  · VIX: stay below 20  (currently ~15.3)                │
  │  · Retail ratio: watch for fade below 1.5×              │
  │  · HY OAS: stay below 300bps  (currently ~272bps)       │
  └─────────────────────────────────────────────────────────┘

  Next milestone: ${TARGET_INST} (200d MA) → stage re-labels MAINSTREAM
  CGT discount:   {days_to_cgt} days to {CGT_DATE}
""")
