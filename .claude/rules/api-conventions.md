---
paths:
  - asxos/api/**
  - tests/**
---

# FastAPI Conventions — asxos

## Hard-fail lifespan (CLAUDE.md non-negotiable #1)

- `asxos/api/main.py` lifespan opens the DB pool, asserts migration drift,
  and warms `get_cache().get("model_a")`. Any of these failing raises and
  the API does not start. Never wrap in `try/except` + `logger.warning(...)`.
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
  from outside Render's network. No rateLimiter, no JWT, no auth chain.
- The crons read Supabase directly — they never call the API.

## Response shape

- snake_case throughout. There is no frontend in v1 — no camelCase boundary.
- Error codes: 400 (validation), 401 (no/bad token), 404 (not found), 500.

## Migrations

- Numbered SQL files in `migrations/`, applied via
  `mcp__supabase__apply_migration` against project `gxjqezqndltaelmyctnl`.
- No `make migrate` runner — `make migrate` only prints the reminder.
- After applying: bump `REQUIRED_MIGRATIONS` in `asxos/api/main.py`.

## Testing

- Unit tests in `tests/test_*.py`. Avoid touching the live DB — mock
  `asxos.db.acquire` and pass synthetic asyncpg `Record`-shaped dicts.
- For ML tests, prefer the real Model A v1_5 artefacts in `models/` over
  a synthetic LightGBM (catches sklearn/LightGBM version drift).
