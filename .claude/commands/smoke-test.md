# Smoke Test

Run a 5-point health check against $ARGUMENTS (the target URL).

Retry logic: 3 attempts, 5 seconds apart (handles Render cold starts on free tier).

## Checks

**Check 1 — Health endpoint**
`GET $ARGUMENTS/health`
Expected: HTTP 200

**Check 2 — Auth login**
`POST $ARGUMENTS/api/auth/login`
Body: `{"email": "demo@tradesight.ai", "password": "demo123"}`
Expected: HTTP 200 + JSON body containing `access_token`
Save token as `$TOKEN` for Check 4.

**Check 3 — Auth required (no token)**
`GET $ARGUMENTS/api/v1/portfolio`
Expected: HTTP 401

**Check 4 — Authenticated route**
`GET $ARGUMENTS/api/v2/agent/brief`
Header: `Authorization: Bearer $TOKEN`
Expected: HTTP 200

**Check 5 — Public data route**
`GET $ARGUMENTS/api/v2/macro/context`
Expected: HTTP 200

## Output

```
Smoke test: $ARGUMENTS
──────────────────────────────
Check 1  GET /health                ✓ 200
Check 2  POST /api/auth/login       ✓ 200 + token
Check 3  GET /api/v1/portfolio      ✓ 401
Check 4  GET /api/v2/agent/brief    ✓ 200
Check 5  GET /api/v2/macro/context  ✓ 200
──────────────────────────────
Result: PASS (5/5)
```

If any check fails after 3 retries:
```
Check N  [endpoint]  ✗ [actual status] — [error detail]
Result: FAIL — do not proceed to production.
```
