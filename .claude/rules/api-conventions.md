---
paths:
  - app/**
  - tests/**
---

# FastAPI Conventions — ASX Portfolio OS

## Route Structure
- New routes go in `app/features/{domain}/routes/` — NOT in `app/routes/` (legacy)
- Routes must be thin — delegate business logic to services
- One router per feature domain; register in `app/main.py`

## Service Layer
- Services extend `BaseService` from `app/core/service.py`
- BaseService provides `event_bus` singleton and `publish_event()` method
- Cross-feature communication goes through the event bus, not direct service imports

## Repository Layer
- Sync repositories: extend `BaseRepo` from `app/core/repository.py` (psycopg2)
- Async repositories: extend from `app/core/async_repository.py` (asyncpg)
- asyncpg uses `$1, $2, ...` parameter syntax (not `%s`)
- Hot paths (signals, portfolio): MUST use asyncpg with shared pool from `app/core/db.py`
- Auth routes: sync psycopg2 is acceptable

## Auth Chain (always in this order)
`rateLimiter → authenticate → authorize`

Missing any step is a security bug, not a style issue.

## Serialisation Boundary
- Backend produces snake_case exclusively
- Frontend hooks in `frontend/hooks/` handle mapping to camelCase
- Never use camelCase field names in FastAPI models, DB columns, or API responses

## Input Validation
- Pydantic models for ALL request and response bodies — no exceptions
- Zod on the frontend side for all form inputs

## Rate Limiting
- All mutating endpoints (POST/PUT/DELETE) need `@limiter.limit("N/minute")`
- The decorated function MUST have `request: Request` as its first non-self parameter
- Import limiter from `app/middleware/rate_limit.py`

## Event Bus
- New event types must be added to `EventType` enum in `app/core/events/event_bus.py`
- `emit()` transforms snake_case to dot.case: `"model_deployed"` → `"model.deployed"`
- Events are non-fatal: errors in handlers are logged but don't propagate

## Response Format
- Use `ResponseBuilder` pattern — check `app/api/portfolio.py` for the standard shape
- Error codes: 400 (validation), 401 (unauthed), 403 (unauthorised), 404 (not found), 429 (rate limited)

## Database
- Soft deletes: `deleted_at TIMESTAMPTZ` — never `DELETE FROM` on user data
- Every new user-facing table needs RLS policies before first deploy
- Migrations: numbered SQL files in `migrations/`; apply via Supabase MCP
- After migration: run `cd frontend && npx supabase gen types typescript --project-id gxjqezqndltaelmyctnl > types/supabase.ts`
