Read CLAUDE.md and PROJECT_STATUS.md.

Close the current sprint:

1. Run full test suite and report counts
2. Check for uncommitted changes: `git status`
3. Check PR status: `gh pr list --state open`
4. List what was delivered (commits since branch creation)
5. Update PROJECT_STATUS.md with:
   - Sprint status
   - New test counts
   - New migration count
   - Any new cron jobs added
   - Issues closed
6. List remaining ops actions (migrations to apply, cron jobs to schedule)
7. Commit: `docs: update PROJECT_STATUS.md for sprint close`

Do NOT merge PRs or apply migrations — list them as actions for the human.
