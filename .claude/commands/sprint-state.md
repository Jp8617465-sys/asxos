# Sprint State

Read `CLAUDE.md` first. Produce a live snapshot. Do NOT start any work.

1. **Git state**
   - Branch: `git branch --show-current`
   - Ahead of main: `git rev-list --count main..HEAD`
   - Open PRs: `gh pr list --state open --json number,title,headRefName`
   - Last 5 commits: `git log --oneline -5`
   - Working tree: `git status -s`

2. **Test state**
   - `pytest tests/ -q --tb=no 2>&1 | tail -1`
   - `make check` exit status (without running it — just report what was last green per recent commits)

3. **Migration state**
   - Latest on disk: `ls migrations/*.sql | sort | tail -1`
   - Count on disk: `ls migrations/*.sql | wc -l`
   - `REQUIRED_MIGRATIONS` constant value (grep `asxos/api/main.py`)
   - Applied in Supabase: count from `mcp__supabase__list_migrations`

4. **Open tasks**: `TaskList` — show pending/in_progress only

5. **Open GitHub issues**: `gh issue list --state open --limit 20`

## Output

Structured summary, one block per section. Informational only.
