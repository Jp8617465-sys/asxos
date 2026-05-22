# Market Regime Detection Task

<context>
Current implementation: `asxos/domain/signals/regime.py`
- Synthetic ASX200 proxy from the top-10 most-traded symbols (by 20-day median dollar volume)
- 200-day SMA on the proxy close + 20-day slope on the SMA
- Returns `bull` | `bear` | `neutral`:
  - bull: proxy > 200d SMA AND 20d SMA slope > 0
  - bear: proxy < 200d SMA AND 20d SMA slope < 0
  - neutral: anything else (chop, transition, insufficient history)
- Hard switches (no HMM, no Bayesian changepoint detection in v1).
- Applied at signal-generation time in `jobs/generate_signals.py`; the
  output is stored on each signal row in the `regime` column.

Downstream use:
- `apply_regime_thresholds` / `classify_batch` in
  `asxos/domain/signals/thresholds.py` use the regime to tighten the
  STRONG_BUY cutoff in bear and the STRONG_SELL cutoff in bull.
- No macro/FRED inputs in v1 (deferred to v2 per BUILD_GUIDE
  "Things not here on purpose").
</context>

<task>
$ARGUMENTS
</task>

<constraints>
- T-1 rule: regime computed from prices available at the prediction date,
  no lookahead
- Pure function over a (symbol, dt, close, volume) panel — no DB, no network
- Tests in `tests/test_regime.py` use synthetic trended panels (no fixtures)
- Three labels only: bull / bear / neutral. Sideways / crisis are out of scope.
- Edge cases: empty panel → neutral; fewer than 200 trading days of proxy
  history → neutral
- If introducing macro inputs (FRED CPI, RBA cash rate, yield curve),
  that's a v2 task — coordinate with the BUILD_GUIDE before adding new
  ingestion paths
</constraints>

<verify>
1. `pytest tests/test_regime.py` green (bull / bear / neutral / empty /
   short-panel / flat-proxy cases)
2. Regime label appears on each signal row written by
   `jobs/generate_signals.py`
3. `apply_regime_thresholds` boundary tests in `tests/test_thresholds.py`
   still pass (bear tightens STRONG_BUY to 0.70/0.06, bull tightens
   STRONG_SELL to 0.30/-0.06)
4. No lookahead in regime computation (rolling windows with min_periods
   ensure NaN for insufficient history, which short-circuits to neutral)
5. For historical backtest validation: spot-check a known period (e.g.
   COVID crash Mar 2020) returns bear from the proxy panel
</verify>
