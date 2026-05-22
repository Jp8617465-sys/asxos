# Compose a Structured Prompt

Use when no existing command fits — generate a self-contained prompt for
the task.

Follow the WHAT / WHERE / HOW / VERIFY pattern:

```
WHAT: [the specific outcome]
WHERE: [exact files, modules, migrations affected]
HOW: [approach, libraries, constraints, what NOT to do]
VERIFY: [measurable success criteria, edge cases, tests]
```

## Guidelines

- Be specific: "Add Pydantic validation to POST /tax-view" not "improve API"
- Use semantic anchors: cite exact functions, file paths, spec section numbers
- Include negative constraints ("don't add new tables", "don't bump REQUIRED_MIGRATIONS")
- Keep under 500 words. If longer, split into subtasks

## For ML / signal tasks, always include

- T-1 rule (no lookahead)
- `FeatureEngine` for any feature computation (`asxos/domain/signals/feature_engine.py`)
- Baseline to beat: Model A v1_5 ROC-AUC 0.7097 on 5-fold TimeSeriesSplit
- Validation thresholds: `MIN_ROC_AUC=0.65`, `MAX_DEGRADATION=5%`

## For API tasks, always include

- Pydantic models for request + response
- asyncpg via `asxos.db.acquire()`, `$1` parameter style
- Single user — no auth chain, just `ASXOS_API_TOKEN` bearer
- Hard-fail lifespan — any startup error stops the API, no warnings

## For job tasks, always include

- `JobMonitor` wrapper (`asxos/jobs/utils/job_monitor.py`)
- Idempotent UPSERT writes (`ON CONFLICT DO UPDATE`)
- Healthchecks.io ping URL from env (one per job)
- Gate on upstream `job_runs.status='success'` row if dependent

## For tax tasks, always include

- Cite spec section: `docs/foundation/spec/tax-alpha.md` §<N>
- `Decimal` throughout, never `float`
- Calendar arithmetic via `dateutil.relativedelta` for the 12-month rule
- Pure functions, no DB / network in `asxos/domain/tax/`
