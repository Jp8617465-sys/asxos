# Sprint Close

Read `CLAUDE.md` and `docs/foundation/BUILD_GUIDE.md`. Close the current sprint:

1. Run `make check` — report full suite counts (pytest), ruff + mypy state
2. `git status -s` and `gh pr list --state open`
3. List delivered work: `git log --oneline $(git merge-base main HEAD)..HEAD`
4. Migration delta: any new files in `migrations/`? Did `REQUIRED_MIGRATIONS`
   bump? Are they applied in Supabase (`mcp__supabase__list_migrations`)?
5. Render cron delta: any new entries in `render.yaml`? Did they get
   created on Render (`mcp__render__list_services`)?
6. Outstanding tasks: `TaskList` — anything still in_progress

## Remaining ops actions

Compile a list of what the human (or a separate session) still needs to do:
- Migrations to apply (file present but not in supabase_migrations)
- Env vars to upload (`sync: false` in render.yaml but absent from the
  live service)
- Healthchecks.io URLs to create for any new cron
- Render dashboard tweaks (e.g. `healthCheckPath` if a new web service
  was added — MCP create can't set it)

## Constraints

- Do NOT merge PRs or apply migrations from here — list them as actions
- Do NOT push to main from here — that's `/ship`
- The sprint is "closed" when the action list above is empty OR every
  remaining item is explicitly accepted as deferred

Output: a sprint summary block followed by the action list.
