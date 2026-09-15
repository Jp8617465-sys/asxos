"""Equity valuation — residual income, deterministic, content-addressed.

Pure model: `residual_income.py`, `capm.py`, `numeric.py`.  Contracts and
persistence (F-E2E r2, S1): `contracts.py`, `preregistration.py`,
`universe.py`, `sweep.py`, `repository.py`.  Rule #11 holds throughout —
nothing in this package reads `signals` or `model_versions`
(`inputs.assert_valuation_sql_admissible` screens every statement at import).
"""
