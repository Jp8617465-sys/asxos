# Sprint Close

Read `CLAUDE.md` and `docs/foundation/BUILD_GUIDE.md`. Close the current sprint:

1. Run `make check` — report full suite counts (pytest), ruff + mypy state
2. `git status -s` and `gh pr list --state open`
3. List delivered work: `git log --oneline $(git merge-base main HEAD)..HEAD`
4. Migration delta: any new files in `migrations/`? Did `REQUIRED_MIGRATIONS`
   bump? Are they applied in Supabase (`mcp__supabase__list_migrations`)?
5. Workflow delta: anything changed in `.github/workflows/` — new step,
   changed schedule, changed step order? Config is live on merge to `main`;
   there is no deploy step and nothing to reconcile against
6. Outstanding tasks: `TaskList` — anything still in_progress

## Remaining ops actions

Compile a list of what the human (or a separate session) still needs to do:
- Migrations to apply (file present but not in supabase_migrations)
- Actions secrets to add (a workflow `env:` block names a secret that isn't in
  the repo's Actions secrets yet — otherwise its first scheduled run fails)
- Healthchecks.io URLs to create for any new job, plus the matching
  `HEALTHCHECK_URL_<JOB>` entry in that workflow's `env:` block
- PRs awaiting James's merge (workflow config only goes live on merge to `main`)

## Constraints

- Do NOT merge PRs or apply migrations from here — list them as actions
- Do NOT push to main from here — that's `/ship`
- The sprint is "closed" when the action list above is empty OR every
  remaining item is explicitly accepted as deferred

Output: a sprint summary block followed by the action list.
