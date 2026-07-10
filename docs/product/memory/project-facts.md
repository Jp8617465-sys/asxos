# arbi project-facts memory (pointer index — ladder level 4)

**Status:** current · read-only during runs · CODEOWNERS-gated on `main`
**No original content** — points at the durable repo facts arbi should know, which already
live in their authoritative homes. The real files win over this index.

## Durable repo facts (follow these)

- **The docs source-of-truth map:** `../../README.md`
- **Agent guide + stack + schema overview + delegation policy:** `../../../CLAUDE.md`
- **Auto-attaching conventions:** `../../../.claude/rules/` (`api-`, `ml-`, `job-`, `portfolio-conventions.md`)
- **Current program state (reconciled):** `../roadmap-state.md`
- **Live-state probes:** `/sprint-state` + `/catchup` (git/PR/CI · Supabase-ro · Render)
- **Schema is the migrations:** `../../../migrations/` (canonical, through 0036+)
- **Tax spec source of truth:** `../../foundation/spec/tax-alpha.md`
- **Known sandbox test gaps (do not chase):** `../../../CLAUDE.md` (## Known test environment gaps)
- **CI: `full-check` (ruff 0.7.0 + mypy + pytest) + `targeted-ml-tests`.** Pin dev ruff to
  **0.7.0** to match CI (approved-lessons L3). A dev venv lives at `scratchpad/venv312`.

Update this index only when a durable repo convention is added/moved — via reviewed PR.
