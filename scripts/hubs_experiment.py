"""
HUBS.NYSE — asxos classifier experiment (2026-06-02).

Runs existing domain classifiers against manually-constructed inputs from
live web data. Zero DB writes, zero new tables. Purely experimental.

Data sources (fetched 2026-06-02):
  - HUBS price: ~$255, 50d MA ~$243.61, 200d MA ~$317.94  [Yahoo Finance]
  - RSI(14): 54.94                                          [Investing.com]
  - Weekly momentum: V-recovery from $183 → $259, ~8% avg weekly move
  - Short interest: 8.7% of shares outstanding             [MarketBeat]
  - Retail sentiment: extremely bullish, extremely high vol [Stocktwits]
  - VIX: 15.32 (May 29 close, declining from ~20 peak)     [CBOE via FRED]
  - US HY OAS: 272bps (tight, compressing from ~350bps)    [FRED BAMLH0A0HYM2]
  - VIX 5d change: approx -8% (declining vol = risk-on)
  - HY OAS 5d change: approx -10bps / -3.5% (tightening)
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date

# ── Stage classifier ─────────────────────────────────────────────────────────
from asxos.domain.themes.stage_classifier import (
    CLASSIFIER_VERSION,
    ClassifierInput,
    StageThresholds,
    classify_stage,
)

# ── Underlying attribution ────────────────────────────────────────────────────
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.types import ThesisUnderlying, UnderlyingDirection

# ── Cross-layer observations ──────────────────────────────────────────────────
from asxos.domain.brief.cross_layer import cross_layer_observations
from asxos.domain.underlyings.attribution import UnderlyingScore


AS_OF = date(2026, 6, 2)

# ─────────────────────────────────────────────────────────────────────────────
# 1. STAGE CLASSIFIER
#    Treating HUBS as a 1-stock "theme".
#    pct_above_50d/200d are binary (1.0 or 0.0) for a single stock.
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("HUBS.NYSE — asxos Stage Classifier")
print(f"as_of: {AS_OF}  |  classifier: {CLASSIFIER_VERSION}")
print("=" * 60)

print("\n── Inputs ──")
print(f"  price:            ~$255  (50d MA $243.61 | 200d MA $317.94)")
print(f"  vs 50d MA:        ABOVE  →  pct_above_50d = 1.0")
print(f"  vs 200d MA:       BELOW  →  pct_above_200d = 0.0")
print(f"  avg weekly move:  ~8%    (V-recovery momentum, volatile)")
print(f"  news_sentiment:   0.72   (Stocktwits: extremely bullish)")
print(f"  retail ratio:     2.5    (message vol: extremely high = 250% of 90d avg)")
print(f"  RSI(14):          54.94  (neutral)")

inputs = ClassifierInput(
    price_history_days=252,
    pct_above_50d_ma=Decimal("1.0"),     # above 50d MA
    pct_above_200d_ma=Decimal("0.0"),    # well below 200d MA ($255 vs $318)
    avg_weekly_move_pct=Decimal("0.08"), # 8% avg weekly move (high volatility, recovery)
    news_sentiment=Decimal("0.72"),      # extremely bullish Stocktwits sentiment
    retail_mention_ratio=Decimal("2.50"), # 250% of 90d avg = clear retail spike
)

result = classify_stage(inputs, StageThresholds())

print("\n── Stage Classifier Output ──")
if result is None:
    print("  RESULT: insufficient data (< 30d)")
else:
    label, conditions = result
    print(f"  STAGE:      {label.upper()}")
    print(f"  CONDITIONS:")
    for c in conditions:
        print(f"    · {c}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. UNDERLYING ATTRIBUTION
#    HUBS's two key macro drivers: VIX and US HY OAS.
#    Both have negative direction (HUBS benefits when they fall).
#    5d moves from current data.
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("HUBS.NYSE — Underlying Attribution")
print("=" * 60)

print("\n── Macro Drivers Configured ──")
print("  VIX:       direction=negative  exposure=0.50  (growth stock: benefits when vol falls)")
print("  US HY OAS: direction=negative  exposure=0.50  (benefits when credit spreads tighten)")

print("\n── 5d Moves (vs prior week) ──")
print("  VIX:       15.32 ← ~16.65   →  -8.0%   (vol compressing, risk-on)")
print("  US HY OAS: 272bp ← ~282bp   →  -3.5%   (credit tightening, risk-on)")

hubs_underlyings: list[ThesisUnderlying] = [
    ThesisUnderlying(
        thesis_id=1,
        underlying_id=1,
        code="vix",
        exposure=Decimal("0.50"),
        direction=UnderlyingDirection.negative,
        last_validated_at=AS_OF,
    ),
    ThesisUnderlying(
        thesis_id=1,
        underlying_id=2,
        code="us_hy_oas",
        exposure=Decimal("0.50"),
        direction=UnderlyingDirection.negative,
        last_validated_at=AS_OF,
    ),
]

moves: dict[int, Decimal | None] = {
    1: Decimal("-8.0"),    # VIX 5d move: -8% (falling vol = good for HUBS, negative direction)
    2: Decimal("-3.5"),    # US HY OAS 5d move: -3.5% (tightening = good for HUBS, negative direction)
}

score = score_thesis_underlying(hubs_underlyings, moves)

print("\n── Attribution Output ──")
print(f"  SCORE:             {score.label.upper()}")
print(f"  WEIGHTED MOVEMENT: {score.weighted_movement:+.2f}%")
print(f"  COMPONENTS:")
for comp in score.component_moves:
    move = comp.get("move_5d_pct") or "n/a"
    contrib = comp.get("contribution") or "n/a"
    print(f"    · {comp['code']}: 5d={move}%  contribution={contrib}  (dir={comp['direction']})")

# ─────────────────────────────────────────────────────────────────────────────
# 3. CROSS-LAYER OBSERVATIONS
#    Regime context: VIX 15 + HY OAS 272bps = risk_on_narrowing
#    (Risk appetite present but not broad participation yet)
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("HUBS.NYSE — Cross-Layer Observations")
print("=" * 60)

print("\n── Regime Context ──")
print("  VIX 15.32 + HY OAS 272bps → risk_on_narrowing")
print("  (Macro environment supportive but not euphoric)")

thesis_scores = [("HUBS.NYSE", "active", score)]
observations = cross_layer_observations("risk_on_narrowing", thesis_scores)

print("\n── Observations ──")
if observations:
    for obs in observations:
        print(f"  · {obs}")
else:
    print("  (no cross-layer signals fired)")

# ─────────────────────────────────────────────────────────────────────────────
# 4. SYNTHESIS
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("SYNTHESIS")
print("=" * 60)

stage_label = result[0] if result else "unknown"
underlying_label = score.label

print(f"""
  Stage classifier:   {stage_label.upper()}
    → Retail spike (2.5x 90d avg) + high sentiment fired.
    → Still below 200d MA — breadth not yet institutionally confirmed.
    → Consistent with a short-covering rally with retail piling in.

  Underlying score:   {underlying_label.upper()} ({score.weighted_movement:+.2f}%)
    → VIX declining + credit spreads tightening = macro tailwind confirmed.
    → Both drivers moving in HUBS's favour this week.

  Cross-layer:        risk_on_narrowing + {underlying_label}
    → {'Macro confirms the move. Watch for regime shift to risk_off — that reverses the drivers fast.' if underlying_label == 'confirming' else 'Mixed signal — macro supports risk assets broadly but stock-specific thesis needs monitoring.'}

  asxos verdict flag: {'⚠ LATE-RETAIL — retail spike + unconfirmed institutional breadth. Classic fade setup above 200d MA.' if stage_label == 'late-retail' else f'{stage_label} — monitor.'}
""")

print("=" * 60)
print("Note: thresholds were calibrated on ASX equities. Retail-mention")
print("ratio of 2.5x is a direct proxy from Stocktwits volume data.")
print("200d MA crossover (~$318) is the key institutional confirmation level.")
print("=" * 60)
