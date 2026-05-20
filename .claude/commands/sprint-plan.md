Read CLAUDE.md, PROJECT_STATUS.md, and the latest discovery report if available.

Plan Sprint $ARGUMENTS.

1. Run /sprint-state to get current status
2. Review open issues: `gh issue list --state open --json number,title,labels`
3. Review PROJECT_STATUS.md roadmap section for planned deliverables
4. Check dependencies: what must be true before this sprint can start?

Produce a sprint plan with:
- Sprint goal (one sentence)
- Deliverables (table: what, effort S/M/L, dependencies)
- Wave structure (which tasks can run in parallel)
- Risk register (what could go wrong, mitigation)
- Quality gates (what must pass before merge)
- Test baseline (current counts, minimum for sprint end)

Do NOT generate execution prompts — that's a separate step.
