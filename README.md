# asxos

Personal investment intelligence OS for ASX equities.

Single user. No auth, no frontend, no multi-tenancy. ML signals, SHAP explanations, tax-alpha view over positions, daily morning brief by email.

## Architecture

- Python 3.12, FastAPI, Postgres 16 (Supabase).
- LightGBM Model A producing daily signals with inline SHAP factors.
- Eight Render cron services driving the daily pipeline, monitored by Healthchecks.io.
- All operations driven through Claude Code with MCP servers (Render, Supabase, GitHub).
- No Render dashboard clicks for routine changes — `make check-drift` enforces parity between `render.yaml` and deployed state.

## Foundation documents

See `docs/foundation/` for the full diagnostic, design, and execution planning:

- `phase-1-audit.md` — why we rebuilt
- `phase-2-survives-the-fire.md` — durable knowledge carried forward
- `phase-3-product-redefinition.md` — single-user reframe
- `phase-4-architecture-system-architect.md` — the chosen architecture
- `phase-5-milestones.md` — M1 through M12 milestone definitions
- `phase-a-tax-math-verification.md` — tax code defect audit
- `phase-b-failure-postmortem.md` — root cause of the previous system
- `phase-c-calendar.md` — realistic 14-week timetable
- `BUILD_GUIDE.md` — the executable manual
- `tax-alpha.md` (spec/) — tax module source of truth

## Lessons encoded into this repo

(Quoted from `phase-b-failure-postmortem.md` — the previous system died of these. They are non-negotiable here.)

1. **Hard-fail startup.** `asxos/api/main.py` lifespan raises on any dependency-init failure. No graceful warnings on infrastructure dependencies.
2. **MCP-driven service management.** Every routine Render or Supabase operation goes through MCP. No dashboard clicks.
3. **No feature flags for half-deployed features.** If it's not ready, it doesn't merge.
4. **No `user_id`, no auth, no RLS.** Single user.
5. **Centralised fail-fast env var loading.** `asxos/config.py` reads every required var at startup and raises on missing.
6. **Smaller test suite.** ~400 load-bearing tests, not 5,000.
7. **Consolidation milestones.** Every fourth or fifth milestone is verify-and-tidy, not feature-add.
8. **Smaller stack.** Eight cron services, ten tables, one email provider, one monitoring deadman switch.
9. **No graceful warnings in infrastructure code.** Fail loudly.
10. **Spec-first for non-trivial domain logic.** See `docs/foundation/spec/tax-alpha.md`.

## Quickstart

```bash
make install      # create venv, install deps
make dev          # run API at 127.0.0.1:8788
make check        # ruff lint + mypy + pytest
```

For full execution sequence, read `docs/foundation/BUILD_GUIDE.md` Part 5 (M1-M12).

## License

Private. Not for distribution.
