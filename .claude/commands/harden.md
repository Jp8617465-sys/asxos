# Harden — Security + Performance Audit

Uses `security-engineer` and `performance-engineer` agents. Scope:
$ARGUMENTS (feature or sprint name). Saves report to
`docs/harden/$ARGUMENTS.md`.

## Part 1 — Security

Run `/security-scan` first. Include its output verbatim.

Additional spot-checks beyond `/security-scan`:
- [ ] No sensitive data in logs (DATABASE_URL, ASXOS_API_TOKEN,
      RESEND_API_KEY, BACKUP_GITHUB_TOKEN appearing in any
      `log.info/warning/error` call)
- [ ] Bearer-token check on any non-`/health` route exposed by `asxos-api`
- [ ] Pickle artefacts in `models/` reviewed before the commit that
      adds a new version

## Part 2 — Performance

### Query analysis
- [ ] N+1 in new code: scan for `async for` loops that issue a query per
      iteration — flag any
- [ ] All DB code uses asyncpg + `$1, $2` parameter style. No psycopg2 in
      API code paths (`asxos/api/`). Jobs may use psycopg2 only with
      registered numpy adapters.
- [ ] No `SELECT *` in new code
- [ ] New tables have indexes on every column used in a WHERE / JOIN

### Caching
- [ ] Model cache TTL still 60s (`asxos/domain/models/cache.py`) — don't
      raise without thinking about the M9 retrain flip latency
- [ ] EODHD calls are never inside an API request path. Only the daily
      crons hit EODHD; the API reads from Supabase.

### Hot-path latencies
- [ ] `/health`: target p95 < 100ms (current ~780ms cold, ~50ms warm)
- [ ] `asx predict <date>` end-to-end: ~3-5 min on a full 1900-symbol
      universe — that's feature-engine cost, not DB. Don't over-optimise.

### Job duration budgets
- [ ] sync_prices (bulk): < 10s per day
- [ ] sync_fundamentals: < 5 min for ~1900 symbols
- [ ] generate_signals: < 5 min end-to-end
- [ ] compose_brief: < 30s

## Output

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
PASS (0 critical) or BLOCK (N critical findings)
```

**Block criteria**: any CRITICAL blocks `/deploy-check`.
