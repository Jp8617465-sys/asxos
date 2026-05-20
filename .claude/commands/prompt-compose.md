# Compose a Structured Prompt

Use this when you need to create a well-structured prompt for a task
that doesn't fit an existing command.

Follow the WHAT/WHERE/HOW/VERIFY pattern:

```
WHAT: [Describe the specific outcome you need]
WHERE: [List exact files, modules, or systems affected]
HOW: [Specify approach, patterns, libraries, or constraints]
VERIFY: [Define measurable success criteria and edge cases to test]
```

Guidelines:
- Be specific: "Add rate limiting to POST /api/v2/alerts" not "add security"
- Use semantic anchors: name exact patterns, algorithms, or standards
- Specify what NOT to do (negative constraints prevent common mistakes)
- Keep prompts under 500 words — if longer, break into subtasks

For ML tasks, always include:
- Data leakage prevention (T-1 rule)
- Baseline metrics to compare against (MIN_ROC_AUC=0.65)
- FeatureEngine requirement (no inline computation)

For frontend tasks, always include:
- TypeScript strict (no-explicit-any: error)
- Types in frontend/contracts/ (never duplicate)
- snake_case → camelCase at hook boundary only
- Jest 80%+ coverage requirement

For backend tasks, always include:
- Auth chain: rateLimiter → authenticate → authorize
- Pydantic validation on all inputs
- asyncpg for hot paths ($1 param syntax)
- Event bus for cross-feature communication

For Australian financial context, always include:
- ATO/ASIC compliance notes where applicable
- "General information only" disclaimers
- Franking credit and CGT considerations
