# Deploy Check — Pre-Production Checklist

Verify every item before deploying to production. Report PASS/FAIL per item.

## Checklist

**Build**
- [ ] `cd frontend && npm run build` — must complete with 0 errors
- [ ] No TypeScript errors: `cd frontend && npm run type-check`

**Database**
- [ ] All pending migration files applied via Supabase MCP
  - List migrations on disk: `ls migrations/*.sql | sort`
  - Confirm the latest has been applied (ask user if unsure)
- [ ] TypeScript types regenerated after last migration: check `frontend/types/supabase.ts` mtime vs latest migration

**Environment variables**
- [ ] New env vars present in Render config (check service env via Render MCP)
- [ ] New env vars present in Vercel config (check project env)
- [ ] No `.env` file committed: `git log --all -- .env`

**Health**
- [ ] Backend `/health` returns 200 (hit staging URL)
- [ ] No open CRITICAL harden findings for this sprint

**CI**
- [ ] PR is merged to `main`
- [ ] All GitHub Actions checks green: `gh run list --branch main --limit 3`

## Output

List each item with PASS ✓ or FAIL ✗.
If all pass: **Ready to deploy. Run /deploy-production to go live.**
If any fail: **Deploy blocked. Fix the items marked ✗ above.**

Do NOT deploy if any item is FAIL.
