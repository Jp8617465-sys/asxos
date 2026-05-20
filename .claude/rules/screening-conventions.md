---
paths:
  - app/features/screening/**
  - app/features/screener/**
  - jobs/extract_shap*
  - jobs/distill_surrogate*
  - jobs/discover_archetypes*
  - jobs/backtest_screening*
  - jobs/refresh_screen*
---

# Screening Engine Conventions

## Rule JSON Format

- Use `"op"` key for operators (NOT `"operator"`)
- Supported operators: `<=`, `>=`, `<`, `>`, `==`, `!=`, `between`
- Combined rules use `"logic": "AND"` or `"OR"`
- Version 2 format is canonical:
  ```json
  {"type": "combined", "version": 2, "logic": "AND", "conditions": [{"feature": "mom_6", "op": ">=", "value": 0.04}]}
  ```

## Feature Table

- Features live in `model_a_features_extended` (wide format, 22 columns + date + symbol)
- Signal data lives in `model_a_ml_signals` (no feature columns)
- Screen matching MUST JOIN `model_a_features_extended` for feature conditions
- Feature columns are prefixed with `f.` in match queries, signal columns with `s.`
- FEATURE_COLUMN_MAP in `app/features/screening/constants.py` is authoritative

## Tables

- `screening_rules` — rule definitions. `source_method`: shap_threshold | surrogate_tree | curated_composite
- `screen_matches` — stock-to-rule matches. `source_type`: rule | archetype
- `screen_backtest_results` — walk-forward OOS metrics per rule
- `stock_archetypes` — K-Means cluster assignments (4 clusters, all stocks assigned)

## Backtest Methodology

- Walk-forward: 1yr train, 6mo test, 3mo step
- Activation: WF efficiency > 0.5 AND hit_rate > 50%
- Curated composites are force-activated (expert-designed, not data-mined)
- Deflated Sharpe Ratio should be computed to control for multiple testing
- `model_a_features_extended` is the feature source for historical backtests (NOT FeatureEngine)

## Display Hierarchy

- API: `GET /api/v2/screens?display=featured` (default) | `all` | `building_block`
- `source_method = 'curated_composite'` — composite strategies shown to users by default
- `source_method IN ('shap_threshold', 'surrogate_tree')` — building blocks, hidden behind toggle

## Threshold Precision

- Percentage features (mom_*, vol_*, ret_*): round to 2dp
- Ratio features (pe_ratio, pb_ratio): round to 1dp
- Binary features (sma200_slope_pos, trend_200): round to 0dp
- Never use 5-6dp precision — it's overfitting to training data

## Survivorship Bias

- All backtests carry `SURVIVORSHIP_DISCLAIMER`
- EODHD only provides currently-listed stocks
- Small/micro-cap results are most affected (2-5% annual inflation estimate)
