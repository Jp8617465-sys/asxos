# Smoke Test — deprecated

**Deprecated. There is no target to hit.** This command curled `/health` on the
hosted API. `asxos-api` was the only non-cron Render service and fell with
Render on 2026-08-12. **The API is currently unhosted** — there is no public URL,
and whether it needs a host at all is an open governor question
(`docs/product/scheduler-inventory-2026-08-13.md` §2 row 1). Do not substitute a
replacement URL.

This becomes relevant again only if the API is re-homed. At that point the check
below is still the right one — `/health` exercising lifespan, DB pool, migration
drift check and model cache in a single request — so it is kept here rather than
deleted:

```bash
curl -fsS -w "\nHTTP_STATUS:%{http_code}\nTIME:%{time_total}s\n" \
  <base-url>/health
```

Expected: HTTP 200 with body `{"status":"ok"}`. Because startup hard-fails
(CLAUDE.md non-negotiable #1), a 200 means boot fully succeeded — there is no
degraded mode.

## What to run instead

The jobs, not the API, are what run on a schedule today. Use `/health-check` for
GitHub Actions run health and Supabase data freshness, and `make dev` +
`curl -fsS http://127.0.0.1:8788/health` to smoke-test the API locally.
