Read CLAUDE.md and PROJECT_STATUS.md first.

Produce a live sprint state snapshot:

1. Git state:
   - Current branch: `git branch --show-current`
   - Commits ahead of main: `git rev-list --count main..HEAD`
   - Open PRs: `gh pr list --state open --json number,title,headRefName`
   - Last 5 commits: `git log --oneline -5`

2. Test state:
   - Backend: `python -m pytest tests/ -q --tb=no -m "not integration and not smoke" 2>&1 | tail -1`
   - Frontend: `cd frontend && npm run test -- --silent 2>&1 | grep -E "Tests:|Test Suites:" | tail -2`

3. Migration state:
   - Latest on disk: `ls migrations/*.sql | sort | tail -1`
   - Count: `ls migrations/*.sql | wc -l`

4. Open issues: `gh issue list --state open --limit 20 --json number,title,labels`

Output as a structured summary. Do NOT start any work — this is informational only.
