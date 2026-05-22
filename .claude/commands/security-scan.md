# Security Scan

Scope is much smaller than a multi-tenant SaaS — asxos is single-user, no
auth chain, no RLS, no frontend. The scan focuses on secret leakage,
SQL/code injection, and bearer-token discipline.

Uses the `security-engineer` agent. Files in scope:
`git diff main...HEAD --name-only`

## Checklist

### Secrets & hardcoded values
- [ ] No API keys, tokens, or passwords in source or commit messages
- [ ] `grep -rnE "sk-|eyJ[A-Za-z0-9_-]{20,}|EODHD_API_KEY=|github_pat_|hc-ping\.com/[a-f0-9-]{36}" asxos/ jobs/ tests/ migrations/ scripts/`
  must return nothing
- [ ] `.env*` not committed: `git log --all -- '.env*'`

### Input validation
- [ ] Every new FastAPI route has a Pydantic request/response model
- [ ] No `eval()`, `exec()`, no f-string SQL building
- [ ] CSV import path (`asx import-holdings`) — rejects malformed rows
  cleanly, no partial commit

### Database
- [ ] asyncpg `$1, $2` parameterised queries only — never f-string interp
  for user-supplied values
- [ ] No `DROP TABLE` outside migrations
- [ ] Migrations are idempotent (`IF EXISTS` / `ON CONFLICT`)

### Bearer-token discipline
- [ ] The API requires `ASXOS_API_TOKEN` (see `asxos/config.py`)
- [ ] Crons never call the API — they go direct to Supabase
- [ ] No token logged in plaintext anywhere

### Pickle safety
- [ ] `joblib.load` only against files in `models/` (no untrusted pickle paths)
- [ ] Pickle files committed to git are reviewed (one-time per version bump)

## Output

For each finding:
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **Location**: file:line
- **Issue**: one sentence
- **Fix**: one sentence

**Block criteria**: Any CRITICAL finding (secret leakage, SQL injection,
pickle from untrusted source) must be resolved before `/deploy-check`.
