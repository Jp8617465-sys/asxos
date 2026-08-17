"""Benchmark-relative performance — pure Decimal return math.

``returns`` holds the two primitives (`period_return`, `alpha`); ``outcome`` holds
the per-open-lot, sleeve-separated measurement the V1 brief renders. No DB, no
numpy — Decimal only, per `.claude/rules/portfolio-conventions.md`.

The previous version of this docstring named the brief's wealth-state collector as
a consumer. It was not one: that collector's benchmark line was removed after it
printed a false −75.7% loss from a flow-affected `capital_aud` difference
(`asxos/domain/brief/collectors/wealth_state.py:101-108`), and nothing replaced it
until `outcome.py`.
"""
