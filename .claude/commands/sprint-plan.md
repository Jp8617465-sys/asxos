# Sprint Plan

Read `CLAUDE.md` and `docs/foundation/BUILD_GUIDE.md`. Plan sprint $ARGUMENTS.

1. Run `/sprint-state` for current snapshot
2. `gh issue list --state open --json number,title,labels` — open work
3. Cross-check `docs/foundation/BUILD_GUIDE.md` for any milestones still
   uncompleted (M1-M12 should all be done; new work is beyond v1)
4. Identify dependencies: what must be true before this sprint can start?
   (e.g., a migration applied, a model retrained, an MCP available)

Produce a plan with:

- **Sprint goal** (one sentence)
- **Deliverables** table: what / effort S/M/L / dependencies / sections of
  `docs/foundation/spec/tax-alpha.md` cited if tax-adjacent
- **Wave structure** — what can run in parallel
- **Risk register** — what could break the daily pipeline (signal job,
  brief delivery, Model A cache) while this sprint ships
- **Quality gates** — what `make check` + `/security-scan` must produce
  before merge
- **Test baseline** — current count, minimum at sprint end
- **Out of scope** — anything explicitly deferred (link to BUILD_GUIDE
  "Things not here on purpose" or tax-alpha §8 / §9 if v2 territory)

Do NOT generate execution prompts. Plan only.
