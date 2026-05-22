# Session Catchup

Read the project state and brief me before we start working.

Do this:
1. `git log --oneline -10`
2. `git status` (current branch, uncommitted changes, worktree state)
3. Read `CLAUDE.md` for current project context
4. Render service health: `mcp__render__list_services` filtered to
   `name LIKE 'asxos-%'` — flag any with `suspended != not_suspended` or any
   recent `dep-*` with `status != live`
5. Supabase freshness check: latest `prices.dt`, latest `signals.as_of`,
   most recent `job_runs` rows for each cron job_name
6. Open tasks: `TaskList` (any pending/in_progress items)

Then summarise:
- **Branch** + purpose (from name + recent commits)
- **Last session** — what was done (from commits + tasks)
- **Open blockers** — pending tasks, failed jobs, stale data
- **Likely next task** — branch name, recent work, last unfinished task

Do NOT start any work. Brief only.
