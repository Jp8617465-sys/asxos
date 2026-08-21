"""Benchmark-relative performance — pure Decimal return math.

``returns`` holds the two primitives (`period_return`, `alpha`); ``outcome`` holds
the per-open-lot, sleeve-separated measurement the V1 brief renders. No DB, no
numpy — Decimal only, per `.claude/rules/portfolio-conventions.md`.

Neither module may difference a `portfolio_daily_snapshots.capital_aud` pair —
see `asxos/domain/brief/collectors/wealth_state.py:101-108` for what that
produced, and `outcome.py`'s docstring for how this package avoids it.
"""
