# Dev-side subagents

Eleven **dev-side** subagents (architecture/quality/docs roles), adapted for asxos
from Edmund Yong's public Claude Code configuration
(`edmund-io/edmunds-claude-code`), plus **two finance-domain conformance agents**,
**five investment-analysis agents**, **one discovery agent**, and **three
program-management agents** (`arbi` + `arbi-red-team` + `guilfoyle`, see bottom). The
dev agents help build and maintain the codebase; the conformance agents guard
spec↔test↔code correctness; the investment-analysis agents surface evidence-grounded
views on the live portfolio; the discovery agent proposes new investment content for
governance review; arbi sits above them all and prioritises what gets built toward the
product's north star, with arbi-red-team as its adversarial check and `guilfoyle` as
its execution lead (mission-control under arbi via `/arbi-mission` — plans/judges a
mission's task graph, never prioritises). All twenty-two are
advisory by default; none is a runtime
in-product agent (a runtime tax/portfolio LLM is a structural NO — it would collide
with the personal-advice firewall and Decimal-only determinism). The investment-
analysis and discovery agents run in Claude Code sessions only, querying Supabase
directly — they are the interactive layer on top of the automated brief, not a
replacement for it.

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
conformance — the gap the red team exposed (§7 hidden as "untested"; TC-20/21 once
hid as "untested" and have since been implemented). They are NOT runtime components
and never touch the personal-advice firewall.

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

## Investment-analysis agents (5)

Added after the system-architect strategic review (2026-06-29). These are a distinct
category from the conformance agents: they query **live Supabase data** (signals,
prices, theses, holding_lots, portfolio_daily_snapshots) and produce evidence-grounded
analysis of the portfolio's current state. Every output cites a specific data point —
no unanchored opinion. They are the building blocks toward a future portfolio-manager
synthesizer agent. Tools include `mcp__supabase-ro__execute_sql` (read-only DB role;
repointed 2026-07-21 per `m14_candidate_agent_db_role_scoping`).

Their SQL is **verified against the live schema** (Stage 2, 2026-06-29): every column
each agent SELECTs was dry-run against the database. Key column truths to preserve when
editing them: `theses` uses `entry_band_lower/upper`, `timeline_days`, `opened_at`,
`conviction_level` (SMALLINT 1..5), and a `status` column (active = `'active'`;
closed = `'exited'|'expired'`) — NOT `entry_price_*`, `timeline_months`, `thesis_date`,
or any `event_type='closed'` predicate. `thesis_revisions` uses `revision_type` (not
`event_type`). `profiles` exposes `sector_cap_pct`/`per_name_cap_pct`/`excluded_*`
columns — there is **no** `constraints_json`. `signals.model='model_a'`.

- **thesis-coherence-guard** — compares current ML signal SHAP factors against the
  written thesis rationale. Verdicts: COHERENT / NEEDS REVIEW / CONTRADICTED. Invoke
  when a signal label changes on a held position or before committing a thesis revision.
- **benchmark-performance-analyst** — computes portfolio return vs XJO total-return
  benchmark (MTD, YTD, since-inception) and attributes alpha to selection vs
  allocation. AXJO.INDX ingestion is wired (Stage 1); benchmark columns populate once
  `snapshot_portfolio` runs after the index has prices. Uses the pure-Decimal
  `asxos/domain/benchmark/returns.py` helpers.
- **thesis-milestone-monitor** — checks whether each active thesis is on trajectory
  to hit its target within its timeline. Classifies ON TRACK / BEHIND / STALLED /
  STOP VIOLATED / ABOVE TARGET. Distinct from the brief's timeline-expiry check.
- **portfolio-coherence-reviewer** — checks the live portfolio against the user's own
  stated framework: conviction vs position size, signal vs holding, sector vs profile
  cap, stop proximity. Surfaces undocumented deviations only.
- **market-context-narrator** — a 3-sentence backdrop (regime + one macro driver +
  one sentiment/regulatory data point) from `market_context_current`,
  `regulatory_events`, and `signal_sentiment`. The "here's what's going on in the
  market" input to a portfolio review. Every sentence carries a number or named source.

The path to a full portfolio-manager synthesizer, now complete: **Stage 1 (done)** wired
the data pipeline (AXJO.INDX ingestion, steady-state SHAP in the brief, benchmark
rendering); **Stage 2 (done)** corrected and live-validated the analysis agents' SQL and
added the pure-Decimal `theses/trajectory.py` + `benchmark/returns.py` helpers;
**Stage 3 (done)** added the market-context narrator (5th agent); **Stage 4 (done)** is
the `/pm-review [SYMBOL]` slash command that fans out all five agents from the main loop
(a subagent cannot spawn subagents) and synthesizes the "good buy / bad buy / here's why"
read into a verdict — **GOOD HOLD / TRIM / REVIEW / EXIT-CANDIDATE** — with the strongest
evidence for and against, each traced to a cited agent output.

## Discovery agents (1, Phase 2b; 2 more planned in Phase 2c)

Added as part of the governance-first architecture
(`docs/proposals/governance-first-architecture-2026-06-30.md`). A distinct category
from the five investment-analysis agents above: those *analyze* existing holdings;
this one *proposes new content* (a macro thesis, eventually a theme or an instrument)
for human governance review. Same tool boundary as the analysis agents (`Read, Glob,
Grep, mcp__supabase-ro__execute_sql`, SELECT-only — mechanically enforced by the
read-only DB role since the 2026-07-21 repoint, not just the prompt) — it never
writes to the database
itself. Its output is a structured JSON block (see the agent file's own "Output"
section) that a slash command parses and persists via `asx agent-run log`, which a
human then reviews and promotes via `asx macro-thesis approve`.

- **macro-economist** — reads the current market snapshot
  (`market_context_current`), existing approved macro theses
  (`governed_active_macro_theses`), and recent regulatory events, then proposes 1-5
  macro theses tagged to a regime quadrant, each with a catalyst/falsifier and cited
  evidence. Invoked via `/discover-macro`.

Not yet built (Phase 2c): **theme-researcher** (given a macro thesis, proposes
ASX-investable themes) and **instrument-selector** (given a theme, proposes 3-5
ASX instruments/ETFs — the first real use of `theme_holdings.source='llm_inferred'`).

## Program-management agents (2)

**arbi** sits above every other agent: the arbiter of *what gets built*. It reconciles
the scattered roadmaps and the live repo/deploy state into one honest picture, then names
the single highest-leverage next action toward the product's north star. Same tool
boundary as the analysis/discovery agents minus the DB (`Read, Glob, Grep`) —
**advisory, read-only, brief-only**: it never writes to the database, never trades, and
cannot dispatch another agent (a subagent can't spawn subagents; the slash command does
any fan-out). Invoked via **`/arbi`** ("wake up"); **`/arbi-close`** is the closing
bookend that records what shipped and writes the session handoff.

Its operating contract — mission, inputs, output schema, permission tiers, approval
gates, and the Model A / financial-decision boundaries — is
`docs/product/arbi-harness.md`. The Output it measures every recommendation against is
`docs/product/north-star.md`; its reconciled state plus append-only decision-log memory
is `docs/product/roadmap-state.md`; how it's scored is `docs/product/arbi-evals.md`. It
never crosses the personal-advice firewall (s766B) or CLAUDE.md rule #11 (Model A
quarantine).

**arbi-red-team** is arbi's adversarial critic — a gate, not a second brief. Before a
`/arbi` brief's single next-action is acted on, it stress-tests that call against five
failure modes (recency overfit, task-switching, cleanup-mistaken-for-progress, low-trust
memory overriding repo truth, perfectionism blocking a shippable build) and returns a
PASS / CHALLENGE verdict with a file-cited reason for each. Same read-only tool boundary
(`Read, Glob, Grep`); it never proposes its own "one thing," never dispatches, and never
waves through a call that crosses the firewall or rule #11.

**guilfoyle** is arbi's execution lead — mission-control, *under* arbi, invoked via
`/arbi-mission`. arbi decides *what matters*; guilfoyle decides *how* an arbi-approved
mission gets built: it turns a mission envelope into a task graph, assigns each node to a
specialist, sets the execution order, and returns one readiness verdict before the draft
PR. It **plans and judges only** — same read-only boundary (`Read, Glob, Grep`, no `Agent`
tool, because a subagent's `Agent(...)` allowlist is ignored at runtime); the
`/arbi-mission` command's main loop does the spawning, testing, review loop, and draft PR.
It holds no tier above what arbi grants a mission (reversible I0–I4, draft-PR ceiling,
attended only), never sets priority (its only pushback is executability evidence, routed
up), and never merges/deploys/migrates or acts on Model A output for capital.

**reversible-work-builder** (autonomy unlock pack, 2026-07-14) is the mutation counterpart
to guilfoyle's read-only planning: it holds `Edit, Write, Bash` for reversible branch work
only (edit → test → commit through the review gate → `claude/**` push prep), executing one
scoped build node of a guilfoyle-planned mission at a time. Orchestration and mutation never
share a process. Bound by the PR-transaction-discipline block, I5/I6/P5/P6 STOPs, and rule
#11; its charter states honestly that a subagent tools list is not containment — the hooks,
deny/ask rules, branch protection, and James's merge are.
