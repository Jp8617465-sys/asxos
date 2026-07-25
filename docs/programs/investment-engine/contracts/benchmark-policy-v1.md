# Benchmark Policy v1

`benchmark-policy-v1` freezes the comparison branches and endpoint rules.

**Machine contract:** [`benchmark-policy-v1.schema.json`](../schemas/benchmark-policy-v1.schema.json)

`XJO_TR` is a genuine point-in-time total-return reporting hurdle resolved
through [`benchmark-snapshot-v1`](benchmark-snapshot-v1.md), with the same
origin, maturity endpoint, [`trading-calendar-v1`](trading-calendar-v1.md), and
external-flow timing as the proposal branch. Comparing a James-specific
after-tax/cost portfolio with a gross index is deliberately labelled a
conservative hurdle, not benchmark-neutral alpha.

`HOLD` retains origin positions and cash, makes no discretionary trades, and
still applies actions, income, tax, costs, and external flows. `CASH` uses an
observable point-in-time cash-rate series with its frozen compounding and tax
treatment. Missing genuine XJO-TR or cash-rate data makes that comparison
unavailable; no price-only index or constant remembered rate may substitute.

Risk-matched and factor diagnostics may be added under a new version, but they
cannot replace the locked XJO-TR and hold comparisons.
