# Smoke Test

Single-point health check against $ARGUMENTS (target URL, default
`https://asxos-api.onrender.com`).

Retry: 3 attempts × 5s apart (handles Render cold starts).

## Check

```bash
curl -fsS -w "\nHTTP_STATUS:%{http_code}\nTIME:%{time_total}s\n" \
  $ARGUMENTS/health
```

Expected: HTTP 200 with body `{"status":"ok"}`.

Hitting `/health` exercises:
- Render reachability (DNS, TLS, port 10000)
- FastAPI lifespan completed → DB pool open
- Migration drift check passed (`supabase_migrations.schema_migrations`)
- Model cache warmed (active `model_a` row + on-disk pickle present)

If any of these failed during boot, the service would not be `live` and
the curl would not return 200 — there's no degraded mode.

## Output (pass)

```
Smoke test: $ARGUMENTS/health
──────────────────────────────
Status: 200 OK
Body:   {"status":"ok"}
Time:   0.8s
──────────────────────────────
Result: PASS
```

## Output (fail)

```
Smoke test: $ARGUMENTS/health
──────────────────────────────
Status: 502 / timeout / connection refused
Result: FAIL after 3 retries — do not push further changes
```

Next step on FAIL: `/error-triage`.
