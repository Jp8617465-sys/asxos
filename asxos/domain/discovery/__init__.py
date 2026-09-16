"""Discovery — the deterministic valuation screen (F-E2E r2 S4).

Turns persisted `valuation_runs` (S1) plus a liquidity screen (`screening`)
into ranked opportunities and, for the top of the list, system-proposed
theses at `pending_review`. No LLM anywhere in the ranker (sprint §6); the
author is `system_screen` (migration 0057), not an agent. Rule #11 holds:
nothing here reads `signals` or `model_versions`.
"""
