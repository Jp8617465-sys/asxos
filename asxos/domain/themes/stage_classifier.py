"""
Theme lifecycle stage classifier — M-Theme-Stage-Detection.

Auto-suggests the lifecycle stage of a theme based on observable signals:
  - Price breadth (% holdings above 50d / 200d MA)
  - Momentum (average weekly price move)
  - News sentiment and retail mention frequency

Classifier version is stamped into stage_metadata on every UPDATE so
historical outputs are auditable. Thresholds are typed in StageThresholds
and versioned via CLASSIFIER_VERSION — bump both on any threshold change.

Stage labels (spec Part 6.2):
  early | early-institutional | broad-institutional | mainstream | late-retail | mature

Non-negotiable: this classifier NEVER writes themes.stage (user-confirmed field).
Only themes.stage_suggested and themes.stage_metadata are auto-updated.

All inputs are Decimal; no numpy. Returns None when insufficient data (<30d prices).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

CLASSIFIER_VERSION = "v1.0"

_STAGE_LABELS = (
    "early",
    "early-institutional",
    "broad-institutional",
    "mainstream",
    "late-retail",
    "mature",
)


@dataclass(frozen=True)
class StageThresholds:
    """All thresholds in one typed structure. Bump CLASSIFIER_VERSION on any change."""

    # Breadth thresholds
    pct_above_50d_ma_emerging: Decimal = Decimal("0.50")     # ≥50% above 50d MA → institutional
    pct_above_200d_ma_consensus: Decimal = Decimal("0.80")   # ≥80% above 200d MA → consensus

    # Sentiment thresholds [0, 1] normalised
    news_sentiment_high: Decimal = Decimal("0.65")

    # Retail mention spike: 150% of 90d avg = mainstream signal
    retail_mention_spike_pct: Decimal = Decimal("1.50")

    # Momentum slowdown: avg weekly move < 2% = late-stage / mature signal
    momentum_slowdown_threshold: Decimal = Decimal("0.02")   # 2% per week


THRESHOLDS = StageThresholds()


@dataclass
class ClassifierInput:
    """Pre-computed signals fed into classify_stage().

    All fields are optional — collector falls back gracefully when data is
    absent. If pct_above_50d_ma is None, that condition is assumed not fired.

    price_history_days: how many days of price data were available for the
    theme's holdings. classify_stage() returns None if < 30.
    """
    price_history_days: int = 0

    pct_above_50d_ma: Decimal | None = None      # fraction [0, 1]
    pct_above_200d_ma: Decimal | None = None     # fraction [0, 1]
    avg_weekly_move_pct: Decimal | None = None   # e.g. 0.035 = 3.5% per week
    news_sentiment: Decimal | None = None        # normalised [0, 1]
    retail_mention_ratio: Decimal | None = None  # current / 90d avg


def classify_stage(
    inputs: ClassifierInput,
    thresholds: StageThresholds = THRESHOLDS,
) -> tuple[str, list[str]] | None:
    """Classify a theme into one of 6 lifecycle stages.

    Returns None when price_history_days < 30 (insufficient data).
    Returns (stage_label, conditions_fired) where conditions_fired is the
    list written to stage_metadata.conditions_fired.

    Predicate waterfall — first match wins:
      1. mature:              momentum slow + very high breadth
      2. late-retail:         retail mention spike OR sentiment very high
      3. mainstream:          pct_above_200d_ma ≥ threshold
      4. broad-institutional: pct_above_50d_ma ≥ threshold
      5. early-institutional: positive sentiment but breadth not yet reached
      6. early:               default (not enough signal for any above)
    """
    if inputs.price_history_days < 30:
        return None

    conditions: list[str] = []

    # Evaluate all conditions
    momentum_slow = (
        inputs.avg_weekly_move_pct is not None
        and inputs.avg_weekly_move_pct < thresholds.momentum_slowdown_threshold
    )
    breadth_high = (
        inputs.pct_above_200d_ma is not None
        and inputs.pct_above_200d_ma >= thresholds.pct_above_200d_ma_consensus
    )
    breadth_emerging = (
        inputs.pct_above_50d_ma is not None
        and inputs.pct_above_50d_ma >= thresholds.pct_above_50d_ma_emerging
    )
    retail_spike = (
        inputs.retail_mention_ratio is not None
        and inputs.retail_mention_ratio >= thresholds.retail_mention_spike_pct
    )
    sentiment_high = (
        inputs.news_sentiment is not None
        and inputs.news_sentiment >= thresholds.news_sentiment_high
    )

    if momentum_slow:
        conditions.append(f"momentum_slow (avg_weekly={inputs.avg_weekly_move_pct})")
    if breadth_high:
        conditions.append(f"breadth_high (pct_above_200d={inputs.pct_above_200d_ma})")
    if breadth_emerging:
        conditions.append(f"breadth_emerging (pct_above_50d={inputs.pct_above_50d_ma})")
    if retail_spike:
        conditions.append(f"retail_spike (ratio={inputs.retail_mention_ratio})")
    if sentiment_high:
        conditions.append(f"sentiment_high (score={inputs.news_sentiment})")

    # Waterfall
    if momentum_slow and breadth_high:
        return "mature", conditions

    if retail_spike or (sentiment_high and breadth_high):
        return "late-retail", conditions

    if breadth_high:
        return "mainstream", conditions

    if breadth_emerging:
        return "broad-institutional", conditions

    if sentiment_high:
        return "early-institutional", conditions

    return "early", conditions
