# Security Scan

Uses `security-engineer` agent. Audit changed/new code for security issues.
Scope: files changed since last merge to main (use `git diff main...HEAD --name-only`).

## Checklist

### Authentication & Authorisation
- [ ] Auth chain present on all new routes: `rateLimiter → authenticate → authorize` (in that order)
- [ ] No route skips `authenticate` for user data
- [ ] `token_version` revocation check present where JWT is validated
- [ ] SSE endpoints accept token via `?token=` query param only (not cookie)

### Input Validation
- [ ] Every new FastAPI route has Pydantic request body model — no raw `dict` or `Any`
- [ ] Every new frontend form input is covered by a Zod schema
- [ ] No `eval()`, `exec()`, or dynamic SQL string building

### Data Access & RLS
- [ ] Every new user-facing table has RLS policies (check via Supabase MCP if needed)
- [ ] No `DELETE FROM` on user data — only `UPDATE ... SET deleted_at = NOW()`
- [ ] No raw `user_id` from request body trusted — always from JWT payload

### Rate Limiting
- [ ] All POST/PUT/DELETE endpoints have `@limiter.limit("N/minute")`
- [ ] Rate-limited functions have `request: Request` as first param

### Secrets & Hardcoded Values
- [ ] No API keys, secrets, or credentials in source
- [ ] No hardcoded user IDs, emails, or passwords
- [ ] `grep -r "sk-\|EODHD\|supabase.*key\|jwt.*secret" app/ jobs/ frontend/` — must return nothing

### CORS
- [ ] No wildcard CORS (`"*"`) added — explicit domain list only

## Output

For each finding:
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **Location**: file:line
- **Issue**: one sentence
- **Fix**: one sentence

**Block criteria**: Any CRITICAL finding must be resolved before `/deploy-check`.
