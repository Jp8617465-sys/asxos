# Harden — Sprint Security + Performance Audit

Uses `security-engineer` and `performance-engineer` agents.
Scope: $ARGUMENTS (sprint name or feature name). Produces `docs/harden/$ARGUMENTS.md`.

## Part 1 — Security (security-engineer)

Run `/security-scan` first. Include its full output in the report.

Additional checks beyond security-scan:
- [ ] JWT expiry checked (access token TTL reasonable, refresh token revocable)
- [ ] OWASP A01-A10 walkthrough on new routes
- [ ] No sensitive data logged (user emails, tokens, PII in log statements)

## Part 2 — Performance (performance-engineer)

### Query analysis
- [ ] N+1 detection: check new routes for loops that query DB per-item — flag any
- [ ] Hot paths use asyncpg (`$1` param syntax) not psycopg2 (`%s`) — check `app/features/*/routes/`
- [ ] `SELECT *` usage — list any in new/changed routes
- [ ] Missing indexes on new tables — check WHERE/JOIN columns

### Caching
- [ ] `/exposure`, `/brief`, `/signals` endpoints — Redis TTL set
- [ ] New endpoints that serve repeated reads — flag if no cache layer
- [ ] EODHD price data — never fetched raw in a hot API path

### Frontend
- [ ] Bundle size delta: `cd frontend && ANALYZE=true npm run build` — report any new large chunks
- [ ] New components — check for unnecessary re-renders (missing `useMemo`/`useCallback` on heavy computations)
- [ ] Target: <200KB gzipped total

### Response times
- [ ] Estimate p95 for new routes based on query plan + data size
- [ ] Flag any route likely to exceed 200ms p95

## Output format

Save to `docs/harden/$ARGUMENTS.md`:

```markdown
# Harden Report — $ARGUMENTS
Date: YYYY-MM-DD

## Security Findings
| Severity | File:Line | Issue | Fix |

## Performance Findings
| Area | Finding | Impact | Fix |

## Summary
- CRITICAL: N
- HIGH: N
- Total findings: N

## Verdict
PASS (0 critical) or BLOCK (N critical findings — must fix before deploy)
```

**Block criteria**: Any CRITICAL finding blocks progress to `/deploy-check`.
