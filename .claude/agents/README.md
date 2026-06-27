# Dev-side subagents

Eleven specialised development subagents, adapted for asxos from Edmund Yong's
public Claude Code configuration (`edmund-io/edmunds-claude-code`). Each is a
dev-workflow agent — they help build and maintain the codebase. They are **not**
finance/domain agents (portfolio, tax, signals); those are a separate question
under evaluation.

Claude routes to these contextually based on the task, or you can invoke one
explicitly (e.g. "use the security-engineer to review this").

## Architecture & planning
- **requirements-analyst** — ideas → concrete specs (PRDs, scope, success metrics)
- **system-architect** — scalable architecture, dependency mapping, trade-offs
- **backend-architect** — APIs, schema, auth patterns, fault tolerance
- **frontend-architect** — UI/accessibility (**dormant in v1** — no frontend yet)
- **tech-stack-researcher** — library/tooling choices with pros & cons

## Code quality & performance
- **refactoring-expert** — safe, measurable, behaviour-preserving refactors
- **performance-engineer** — measurement-driven optimisation
- **security-engineer** — zero-trust vulnerability and secrets review

## Documentation & research
- **technical-writer** — docs, runbooks, docstrings
- **learning-guide** — progressive explanations of code and domain concepts
- **deep-research-agent** — multi-source, cited, confidence-rated investigation

## asxos adaptations
The originals target a Next.js/React/Stripe stack. Each agent here was rewritten
to asxos's reality: FastAPI + Supabase Postgres + Python 3.12, NUMERIC(18,6),
no auth/RLS (single user), hard-fail startup, Decimal-only domain arithmetic, and
the tax-alpha spec as source of truth. `frontend-architect` is kept for set
completeness but flagged dormant since v1 has no web UI.

## Tool permissions (blast radius)

Tools are scoped per agent via the `tools:` frontmatter — an agent can only use
what's listed. Advisory agents are read-only and return their output as text for
the main loop to act on; only two agents mutate files.

| Agent | Tools | Can mutate? |
|---|---|---|
| requirements-analyst, system-architect, backend-architect, frontend-architect, tech-stack-researcher, deep-research-agent, learning-guide | Read, Glob, Grep, WebSearch, WebFetch | No |
| security-engineer, performance-engineer | + Bash (run read-only tooling) | No edit/write |
| technical-writer | Read, Glob, Grep, Write, Edit | Docs only |
| refactoring-expert | Read, Glob, Grep, Edit, Write, Bash | Code (its job) |

## How delegation works

These are loaded by Claude Code at session start from `.claude/agents/` — a session
started before a file existed won't see it until reloaded. Invocation is by the
main agent's judgment (matched on the `description`) or explicit user request
("use the security-engineer…"). Nothing auto-runs them. The routing policy that
makes them part of normal dev work lives in the root `CLAUDE.md`
(**Subagents — delegation policy**); the `description` fields carry PROACTIVELY /
MUST BE USED cues that bias automatic delegation toward the right agent.
