"""
Tests for M-Theme-Stage-Detection: stage_classifier.py.

Covers:
- 6 × stage inputs → expected labels + conditions_fired
- None return on insufficient price history (<30d)
- classifier_version constant is stable
- themes.stage invariant: classifier never touches themes.stage (job test)

Waterfall order (spec Part 6.2 predicate waterfall):
  1. mature:              momentum_slow + breadth_high
  2. late-retail:         retail_spike OR (sentiment_high + breadth_high)
  3. mainstream:          breadth_high (pct_above_200d ≥ 0.80)
  4. broad-institutional: breadth_emerging (pct_above_50d ≥ 0.50)
  5. early-institutional: sentiment_high (no breadth threshold met)
  6. early:               default (no conditions fired)
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.themes.stage_classifier import (
    CLASSIFIER_VERSION,
    ClassifierInput,
    StageThresholds,
    classify_stage,
)

_T = StageThresholds()   # default thresholds


def _inp(**kwargs) -> ClassifierInput:
    """Build ClassifierInput with sensible defaults for untested fields."""
    defaults = {
        "price_history_days": 60,
        "pct_above_50d_ma": None,
        "pct_above_200d_ma": None,
        "avg_weekly_move_pct": None,
        "news_sentiment": None,
        "retail_mention_ratio": None,
    }
    defaults.update(kwargs)
    return ClassifierInput(**defaults)


class TestClassifyStageLabels:
    def test_early_default(self):
        """No conditions fired → default 'early' stage."""
        result = classify_stage(_inp(), _T)
        assert result is not None
        label, conditions = result
        assert label == "early"
        assert conditions == []

    def test_early_institutional_sentiment(self):
        """High sentiment but no breadth threshold → early-institutional."""
        result = classify_stage(_inp(news_sentiment=Decimal("0.70")), _T)
        assert result is not None
        label, conditions = result
        assert label == "early-institutional"
        assert any("sentiment_high" in c for c in conditions)

    def test_broad_institutional_breadth_50d(self):
        """≥50% holdings above 50d MA → broad-institutional."""
        result = classify_stage(_inp(pct_above_50d_ma=Decimal("0.60")), _T)
        assert result is not None
        label, conditions = result
        assert label == "broad-institutional"
        assert any("breadth_emerging" in c for c in conditions)

    def test_mainstream_breadth_200d(self):
        """≥80% holdings above 200d MA → mainstream (beats broad-institutional)."""
        result = classify_stage(
            _inp(pct_above_50d_ma=Decimal("0.85"), pct_above_200d_ma=Decimal("0.82")), _T
        )
        assert result is not None
        label, conditions = result
        assert label == "mainstream"
        assert any("breadth_high" in c for c in conditions)

    def test_late_retail_retail_spike(self):
        """Retail mention spike → late-retail (beats mainstream in waterfall)."""
        result = classify_stage(
            _inp(
                pct_above_50d_ma=Decimal("0.90"),
                pct_above_200d_ma=Decimal("0.85"),
                retail_mention_ratio=Decimal("1.60"),  # > 1.50 threshold
            ),
            _T,
        )
        assert result is not None
        label, conditions = result
        assert label == "late-retail"
        assert any("retail_spike" in c for c in conditions)

    def test_late_retail_sentiment_plus_high_breadth(self):
        """High sentiment AND high breadth → late-retail."""
        result = classify_stage(
            _inp(
                pct_above_200d_ma=Decimal("0.82"),
                news_sentiment=Decimal("0.70"),
            ),
            _T,
        )
        assert result is not None
        label, _ = result
        assert label == "late-retail"

    def test_mature_momentum_slow_plus_breadth_high(self):
        """Slow momentum AND high breadth → mature (top of waterfall)."""
        result = classify_stage(
            _inp(
                pct_above_50d_ma=Decimal("0.90"),
                pct_above_200d_ma=Decimal("0.85"),
                avg_weekly_move_pct=Decimal("0.01"),  # < 0.02 threshold
            ),
            _T,
        )
        assert result is not None
        label, conditions = result
        assert label == "mature"
        assert any("momentum_slow" in c for c in conditions)
        assert any("breadth_high" in c for c in conditions)


class TestInsufficientData:
    def test_returns_none_when_less_than_30_days(self):
        """spec Part 6.2: classifier returns None when <30d price history."""
        result = classify_stage(_inp(price_history_days=29), _T)
        assert result is None

    def test_returns_none_when_zero_history(self):
        result = classify_stage(_inp(price_history_days=0), _T)
        assert result is None

    def test_returns_result_at_exactly_30_days(self):
        result = classify_stage(_inp(price_history_days=30), _T)
        assert result is not None


class TestConditionsFired:
    def test_conditions_fired_contains_threshold_values(self):
        """Fired conditions should include the observed value for auditability."""
        result = classify_stage(
            _inp(pct_above_50d_ma=Decimal("0.65"), news_sentiment=Decimal("0.70")),
            _T,
        )
        assert result is not None
        _, conditions = result
        assert any("0.65" in c for c in conditions)

    def test_no_conditions_when_all_below_threshold(self):
        result = classify_stage(
            _inp(
                pct_above_50d_ma=Decimal("0.30"),
                pct_above_200d_ma=Decimal("0.50"),
                news_sentiment=Decimal("0.40"),
            ),
            _T,
        )
        assert result is not None
        label, conditions = result
        assert label == "early"
        assert conditions == []


class TestClassifierVersion:
    def test_version_constant_is_string(self):
        assert isinstance(CLASSIFIER_VERSION, str)

    def test_version_matches_expected(self):
        """Bump this test when CLASSIFIER_VERSION changes (forces intentional review)."""
        assert CLASSIFIER_VERSION == "v1.0"

    def test_custom_thresholds_respected(self):
        """Custom thresholds override defaults; classifier_version is separate."""
        custom = StageThresholds(pct_above_50d_ma_emerging=Decimal("0.30"))
        result = classify_stage(_inp(pct_above_50d_ma=Decimal("0.35")), custom)
        assert result is not None
        label, _ = result
        assert label == "broad-institutional"  # would be 'early' with default threshold 0.50

    def test_stage_field_never_in_conditions(self):
        """Classifier output only touches stage_suggested; never uses the word 'stage='."""
        result = classify_stage(_inp(pct_above_50d_ma=Decimal("0.60")), _T)
        assert result is not None
        _, conditions = result
        for c in conditions:
            assert "stage=" not in c
