# Market Regime Detection Task

<context>
- Architecture: HMM + Bayesian Online Changepoint Detection
- Soft probability-based transitions between market states
- Regime detection drives: signal weighting, position sizing, user interventions
- Integrates with Model A-D signals and ensemble pipeline
- MacroContext: frozen dataclass in app/features/macro/ — data_date is datetime.date
- Macro data: FRED API (jobs/load_macro.py), cached in DB
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- Regime states must have interpretable labels (bull/bear/sideways/crisis)
- Transitions are soft (probability-weighted), not hard switches
- Must handle ASX trading hours and AU market holidays
- Regime signal must be available before market open for next-day decisions
- MacroContext needs jsonable_encoder(dataclasses.asdict(context)) for JSON serialization
- EODHD rate limits: 100k calls/day — cache aggressively
</constraints>

<verify>
1. Regime labels align with known historical ASX market periods
2. Transition probabilities are calibrated (not overconfident)
3. Signal weighting changes meaningfully across detected regimes
4. Backtest against known events (COVID crash March 2020, GFC 2008)
5. No lookahead bias in regime state computation
</verify>
