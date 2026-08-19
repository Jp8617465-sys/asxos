---
paths:
  - asxos/api/**
  - tests/**
---

# FastAPI Conventions — asxos

## Hard-fail lifespan (CLAUDE.md non-negotiable #1)

- `asxos/api/main.py` lifespan opens the DB pool, runs `SELECT 1`, and asserts
  migration drift — that is all (see `main.py:32-44`). Any of these failing raises
  and the API does not start. Never wrap in `try/except` + `logger.warning(...)`.
  There is NO model warm: the `get_cache().get("model_a")` call was removed by
  P1-02 under rule #11. Do not restore it.
- `REQUIRED_MIGRATIONS` constant tracks the expected count in
  `supabase_migrations.schema_migrations`. Bump it on every new migration.

## Routes

- New routes live in `asxos/api/routes/` and are wired in `asxos/api/main.py`
  via `app.include_router(...)`.
- Routes stay thin — delegate logic to `asxos/domain/*` modules.
- Pydantic models for every request and response body. No raw `dict`/`Any`.

## Database

- Async only via `asxos.db.acquire()` → asyncpg pool. Use `$1, $2, ...`
  parameter syntax.
- No psycopg2 in API code paths. (Jobs may use psycopg2 if needed; API does not.)
- NUMERIC(18,6) on every monetary or statistical column from migration 0001
  forward — single-user system, no RLS, no `user_id` anywhere (CLAUDE.md #4).

## Auth

- Single user. The API requires the `ASXOS_API_TOKEN` bearer on every request
  from outside the local network. No rateLimiter, no JWT, no auth chain.
- The scheduled GitHub Actions workflows read Supabase directly — they never call the API.

## Response shape

- snake_case throughout. There is no frontend in v1 — no camelCase boundary.
- Error codes: 400 (validation), 401 (no/bad token), 404 (not found), 500.

## Migrations

- Numbered SQL files in `migrations/`, applied via
  `mcp__claude_ai_supabase-ro__apply_migration` against project `gxjqezqndltaelmyctnl`.
- No `make migrate` runner — `make migrate` only prints the reminder.
- After applying: bump `REQUIRED_MIGRATIONS` in `asxos/api/main.py` to the observed
  `SELECT count(*) FROM supabase_migrations.schema_migrations` (not a guessed +1).
- **PRE-APPLY dependent-object check (required before any `ALTER`/`DROP COLUMN`/
  `DROP TABLE`).** `migrations/` is not a complete picture of the live DB — out-of-band
  objects can exist (e.g. the `stock_universe` view that tripped 0029). Before altering
  a column or dropping an object, run via `mcp__claude_ai_supabase-ro__execute_sql` and handle any
  hit (e.g. drop+recreate the dependent view in the same migration):
  ```sql
  SELECT dependent_ns.nspname AS schema, dependent_view.relname AS view_name
  FROM pg_depend d
  JOIN pg_rewrite r ON r.oid = d.objid
  JOIN pg_class dependent_view ON dependent_view.oid = r.ev_class
  JOIN pg_namespace dependent_ns ON dependent_ns.oid = dependent_view.relnamespace
  JOIN pg_class src ON src.oid = d.refobjid
  JOIN pg_attribute a ON a.attrelid = src.oid AND a.attnum = d.refobjsubid
  WHERE src.relname = '<table>' AND a.attname = '<column>';
  ```
  For a populated table also capture a before-image (`count/max/min`) and re-verify it
  post-apply. See `docs/db-shared-project-audit-2026-06-28.md`.

## Testing

- Unit tests in `tests/test_*.py`. Avoid touching the live DB — mock
  `asxos.db.acquire` and pass synthetic asyncpg `Record`-shaped dicts.
- Model A's training chain and artefacts were retired 2026-08-19 (rule #11's
  quarantine mechanism — `asxos/domain/models/production_gate.py` — stays;
  there is no longer a model to train or test against).
