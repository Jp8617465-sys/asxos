# asxos

Personal investment intelligence OS for ASX equities.

Single user. No auth, no frontend, no multi-tenancy. ML signals, SHAP explanations, tax-alpha view over positions, daily morning brief by email.

## Current operating guide

Start here — this README is a stable overview, not a live operating map:

- **Agent guide + non-negotiables:** `CLAUDE.md`
- **Docs map / source-of-truth index:** `docs/README.md`
- **Current session handoff:** `docs/session-handoff-2026-08-08.md`
- **Live deployment source:** `.github/workflows/` (GitHub Actions; Render was deleted 2026-08-12)
- **Canonical schema:** `migrations/`

The "Foundation documents" and "Lessons" sections below are background/history; some foundation docs describe an earlier architecture and carry supersede banners. Check `docs/README.md` status labels before treating any doc as current.

## Architecture

- Python 3.12, FastAPI, Postgres 16 (Supabase).
- Model-independent by design: the ML signal engine ("Model A") is shelved and quarantined from every capital decision (see `docs/model-a-decay-analysis-2026-07-11.md` and rule #11 in `CLAUDE.md`). The product is discipline, tax, themes and ETFs — not a signal engine.
- GitHub Actions workflows driving the daily/weekly pipelines (see `.github/workflows/` for the authoritative list), monitored by Healthchecks.io.
- All operations driven through Claude Code with MCP servers (Supabase, GitHub).
- No dashboard clicks for routine changes — job config lives in git under `.github/workflows/`.

## Foundation documents

See `docs/foundation/` for the full diagnostic, design, and execution planning:

- `phase-1-audit.md` — why we rebuilt
- `phase-2-survives-the-fire.md` — durable knowledge carried forward
- `phase-3-product-redefinition.md` — single-user reframe
- `phase-4-architecture-system-architect.md` — the original architecture evaluation (HISTORICAL: it chose a VPS/systemd/local-Postgres design later superseded by the live GitHub Actions/Supabase stack — see the banner in that file)
- `phase-5-milestones.md` — M1 through M12 milestone definitions
- `phase-a-tax-math-verification.md` — tax code defect audit
- `phase-b-failure-postmortem.md` — root cause of the previous system
- `phase-c-calendar.md` — realistic 14-week timetable
- `BUILD_GUIDE.md` — the executable manual
- `tax-alpha.md` (spec/) — tax module source of truth

## Lessons encoded into this repo

(Quoted from `phase-b-failure-postmortem.md` — the previous system died of these. They are non-negotiable here.)

1. **Hard-fail startup.** `asxos/api/main.py` lifespan raises on any dependency-init failure. No graceful warnings on infrastructure dependencies.
2. **Git-driven service management.** Job config lives in `.github/workflows/`; every routine Supabase operation goes through MCP. No dashboard clicks.
3. **No feature flags for half-deployed features.** If it's not ready, it doesn't merge.
4. **No `user_id`, no auth, no RLS.** Single user.
5. **Centralised fail-fast env var loading.** `asxos/config.py` reads every required var at startup and raises on missing.
6. **Smaller test suite.** ~400 load-bearing tests, not 5,000.
7. **Consolidation milestones.** Every fourth or fifth milestone is verify-and-tidy, not feature-add.
8. **Smaller stack.** One email provider, one monitoring deadman switch, one hosting platform. (The original "eight cron services, ten tables" target has grown with the system — `.github/workflows/` and `migrations/` are the live counts; the principle that survives is: no component without an owner and a deadman.)
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
