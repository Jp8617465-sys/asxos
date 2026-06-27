# Dev-side subagents

Eleven **dev-side** subagents (architecture/quality/docs roles), adapted for asxos
from Edmund Yong's public Claude Code configuration
(`edmund-io/edmunds-claude-code`), plus **two finance-domain conformance agents**
added after a system-architect scoping pass (see bottom). The dev agents help build
and maintain the codebase generally; the finance agents guard spec↔test↔code
conformance in the tax and portfolio domains. All thirteen are advisory by default;
none is a runtime in-product agent (a runtime tax/portfolio LLM is a structural NO —
it would collide with the personal-advice firewall and Decimal-only determinism).

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

## Finance-domain conformance agents (2)

Added after the system-architect scoping pass. Both are **advisory, read-only**
(`Read, Glob, Grep`), and exist for one reason: maintaining spec↔test↔code
conformance — the gap the red team exposed (§7 hidden as "untested", TC-20/21
unimplemented). They are NOT runtime components and never touch the personal-advice
firewall.

- **tax-spec-conformance** — owns `docs/foundation/spec/tax-alpha.md` ↔
  `asxos/domain/tax/*` ↔ `tests/test_tax_*`. Flags spec sections with no covering
  test, code deviating from a cited section, and "untested" framings that hide
  "unimplemented". Use on any tax-touching diff.
- **portfolio-invariant-guard** — owns `.claude/rules/portfolio-conventions.md` ↔
  `asxos/domain/portfolio/*`. Verifies the regulatory firewall, the hard-fail table,
  the *intentional* silent-omit paths, the §5.1 boundary-defer location, and
  Decimal-only. Use on any portfolio-touching diff.

Explicitly **not** built: a signals/ML conformance agent (covered by
`ml-conventions.md` + `targeted-ml-tests`) and any broad "finance reviewer" (too
unaccountable — the value is the spec/rules-anchored narrowness).
