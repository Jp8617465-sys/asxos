# Dev-side subagents

Eleven **dev-side** subagents (architecture/quality/docs roles), adapted for asxos
from Edmund Yong's public Claude Code configuration
(`edmund-io/edmunds-claude-code`), plus **two finance-domain conformance agents**,
**five investment-analysis agents**, **three discovery agents**, and **three
program-management agents** (`guilfoyle`, `reversible-work-builder`, `arbi-red-team`,
see bottom). The dev agents help build and maintain the codebase; the conformance
agents guard spec↔test↔code correctness; the investment-analysis agents surface
evidence-grounded views on the live portfolio; the discovery agents propose new
investment content for governance review; the program-management three work **under
arbi** on planning, mutation and adversarial review.

**arbi is not in this roster.** arbi is the main session — James's technical chief of
staff (`CLAUDE.md`, `AGENTS.md` §0) — not a subagent. `/arbi` ("wake up") is a ritual
arbi runs itself, and every fan-out below is arbi's, because a subagent cannot spawn
subagents. None of these twenty-four is a runtime in-product agent either (a runtime
tax/portfolio LLM is a structural NO — it would collide with the personal-advice
firewall and Decimal-only determinism). The investment-analysis and discovery agents
run in Claude Code sessions only, querying Supabase directly — they are the interactive
layer on top of the automated brief, not a replacement for it.

Claude routes to these contextually based on the task, or you can invoke one
explicitly (e.g. "use the security-engineer to review this").

## Hard owner→agent table

**This table is canonical.** If a command's or an agent file's copy diverges, this file
wins. `AGENTS.md` §9 routes by work *shape* (one file → `/build`; multi-node reversible
→ `/arbi-mission`; genuinely parallel programme → a team); this table names the *owner*
of each kind of work once the shape is chosen.

| Owner (work shape) | Agent / command | Mutates? |
|---|---|---|
| challenge THE ONE THING or a large envelope | `arbi-red-team` | no |
| mission graph + readiness | `guilfoyle` (plans only) | no |
| one-file / same-file / tiny sequential | `/build` | yes (that file) |
| multi-node reversible mission | `/arbi-mission` main-loop dispatcher | via specialists |
| large parallel (team-shaped only) | `/arbi-team` | via teammates |
| schema / API / write-path / DB design | `backend-architect` | no |
| secrets / permissions / tool blast radius | `security-engineer` | no |
| behaviour-preserving code cleanup | `refactoring-expert` | **code** |
| docs / runbooks / handoffs | `technical-writer` | **docs** |
| module boundaries / structural change | `system-architect` | no |
| feature with no written spec | `requirements-analyst` | no |
| dependency / external service | `tech-stack-researcher` | no |
| hot path | `performance-engineer` | no |
| tax spec↔test↔code | `tax-spec-conformance` | no |
| portfolio invariants | `portfolio-invariant-guard` | no |
| live-portfolio evidence | the 5 investment-analysis agents | no |
| mutation on `claude/**` or `cursor/**` | `reversible-work-builder` | **code/docs** |

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

Tools are scoped per agent via the `tools:` frontmatter — an agent can only use what's
listed. Most hold read-only tools and return their output as text for arbi to act on;
three mutate files: `technical-writer` (docs), `refactoring-expert` (code) and
`reversible-work-builder` (a mission's build node, on a branch).

Every subagent **inherits arbi's standing** (`AGENTS.md` §9). Its `tools:` list bounds
only what it does *itself*, and arbi lands the result — so a `tools:` list is a
blast-radius default, not a containment boundary. What actually holds is mechanical:
the `main` ruleset, secret scanning with push protection, the `.env` denies and the
secrets hook (`AGENTS.md` §13).

| Agent | Tools | Can mutate? |
|---|---|---|
| requirements-analyst, system-architect, backend-architect, frontend-architect, tech-stack-researcher, deep-research-agent, learning-guide | Read, Glob, Grep, WebSearch, WebFetch | No |
| tax-spec-conformance, portfolio-invariant-guard, guilfoyle, arbi-red-team | Read, Glob, Grep | No |
| the 5 investment-analysis agents, the 3 discovery agents | + `mcp__supabase-ro__execute_sql` (read-only DB role) | No |
| security-engineer, performance-engineer | + Bash (run read-only tooling) | No edit/write |
| technical-writer | Read, Glob, Grep, Write, Edit | Docs only |
| refactoring-expert | Read, Glob, Grep, Edit, Write, Bash | Code (its job) |
| reversible-work-builder | Read, Glob, Grep, Edit, Write, Bash | Code/docs on a branch |

## How delegation works

These are loaded by Claude Code at session start from `.claude/agents/` — a session
started before a file existed won't see it until reloaded. Invocation is by arbi's
judgment (matched on the `description`) or explicit user request ("use the
security-engineer…"). Nothing auto-runs them. The routing policy that makes them part
of normal dev work lives in the root `CLAUDE.md` (**Subagents — delegation policy**)
and in the hard owner table above; the `description` fields carry PROACTIVELY /
MUST BE USED cues that bias automatic delegation toward the right agent.

## Finance-domain conformance agents (2)

Added after the system-architect scoping pass. Both are **read-only**
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
category from the conformance agents: they query **live Supabase data**
(prices, theses, thesis_revisions, holding_lots, portfolio_daily_snapshots) and produce
evidence-grounded analysis of the portfolio's current state. Every output cites a
specific data point — no unanchored opinion. They are the building blocks toward a
future portfolio-manager synthesizer agent. Tools include
`mcp__supabase-ro__execute_sql` (read-only DB role; repointed 2026-07-21 per
`m14_candidate_agent_db_role_scoping`).

**None of them reads `signals` (2026-08-21).** PR #144 deleted every writer to that
table and the SHAP producer, leaving it frozen; two of these agents were still reading
it and returning stale Model A output presented as current into `/pm-review`, which
informs real holding decisions. Both were amputated — see the entries below. The
read-only role permits any SELECT, so *not reading it* is the control, not a
permission. Never reintroduce a `signals` read here (rule #11).

Their SQL is **verified against the live schema** (Stage 2, 2026-06-29): every column
each agent SELECTs was dry-run against the database. Key column truths to preserve when
editing them: `theses` uses `entry_band_lower/upper`, `timeline_days`, `opened_at`,
`conviction_level` (SMALLINT 1..5), and a `status` column (active = `'active'`;
closed = `'exited'|'expired'`) — NOT `entry_price_*`, `timeline_months`, `thesis_date`,
or any `event_type='closed'` predicate. `thesis_revisions` uses `revision_type` (not
`event_type`). `profiles` exposes `sector_cap_pct`/`per_name_cap_pct`/`excluded_*`
columns — there is **no** `constraints_json`. There is **no** unique constraint
guaranteeing one active thesis per symbol — resolve one with `ORDER BY opened_at DESC
LIMIT 1` rather than assuming.

- **thesis-coherence-guard** — reads an active thesis's revision cadence and reports
  whether it is being held on evidence or on inertia. Verdicts: EXAMINED / NEEDS
  REVIEW / UNEXAMINED. Lifecycle rows (`opened`, `entered`, `status_change`) do not
  count as re-examination. **Amputated 2026-08-21** — its signal-vs-thesis SHAP steps
  read the frozen `signals` table; it is also no longer in the `/pm-review` fan-out.
  Invoke directly, on demand.
- **benchmark-performance-analyst** — computes portfolio return vs XJO total-return
  benchmark (MTD, YTD, since-inception) and attributes alpha to selection vs
  allocation. AXJO.INDX ingestion is wired (Stage 1); benchmark columns populate once
  `snapshot_portfolio` runs after the index has prices. Uses the pure-Decimal
  `asxos/domain/benchmark/returns.py` helpers.
- **thesis-milestone-monitor** — checks whether each active thesis is on trajectory
  to hit its target within its timeline. Classifies ON TRACK / BEHIND / STALLED /
  STOP VIOLATED / ABOVE TARGET. Distinct from the brief's timeline-expiry check.
- **portfolio-coherence-reviewer** — checks the live portfolio against the user's own
  stated framework: conviction vs position size, sector vs profile cap, cash drag,
  theme coherence, stop proximity. Surfaces undocumented deviations only.
  **Amputated 2026-08-21** — its "signal vs holding" section read the frozen `signals`
  table and emitted an ever-growing staleness counter on a dead SELL label.
- **market-context-narrator** — a 3-sentence backdrop (regime + one macro driver +
  one sentiment/regulatory data point) from `market_context_current`,
  `regulatory_events`, and `signal_sentiment`. The "here's what's going on in the
  market" input to a portfolio review. Every sentence carries a number or named source.
  (`signal_sentiment` is news-sentiment aggregation, **not** Model A output, despite
  the name; `market_context_current` is its own table from migration `0013`.)

The path to a full portfolio-manager synthesizer, now complete: **Stage 1 (done)** wired
the data pipeline (AXJO.INDX ingestion, benchmark rendering; the steady-state SHAP half
was removed by PR #144 with the rest of Model A's producers); **Stage 2 (done)**
corrected and live-validated the analysis agents' SQL and
added the pure-Decimal `theses/trajectory.py` + `benchmark/returns.py` helpers;
**Stage 3 (done)** added the market-context narrator (5th agent); **Stage 4 (done)** is
the `/pm-review [SYMBOL]` slash command that fans out four of the five agents from the
main loop
(a subagent cannot spawn subagents) and synthesizes the "good buy / bad buy / here's why"
read into a verdict — **GOOD HOLD / TRIM / REVIEW / EXIT-CANDIDATE** — with the strongest
evidence for and against, each traced to a cited agent output.

## Discovery agents (3)

Added as part of the governance-first architecture
(`docs/proposals/governance-first-architecture-2026-06-30.md`). A distinct category
from the five investment-analysis agents above: those *analyze* existing holdings;
these *propose new content* (a macro thesis, a theme, a theme holding) for governance
review. Same tool boundary as the analysis agents (`Read, Glob, Grep,
mcp__supabase-ro__execute_sql`, SELECT-only — mechanically enforced by the read-only DB
role since the 2026-07-21 repoint, not just the prompt) — none writes to the database
itself. Each output is a structured JSON block (see each agent file's own "Output"
section) that a slash command parses and persists via `asx agent-run log`, which a
human then reviews and promotes via `asx macro-thesis approve`.

- **macro-economist** — reads the current market snapshot
  (`market_context_current`), existing approved macro theses
  (`governed_active_macro_theses`), and recent regulatory events, then proposes 1-5
  macro theses tagged to a regime quadrant, each with a catalyst/falsifier and cited
  evidence. Invoked via `/discover-macro`.
- **theme-researcher** — top-down and macro-conditioned: given an approved macro
  thesis's regime read, proposes 0-5 ASX-investable theme / theme-holding candidates
  that operationalise it, each tracing back to the macro thesis it derives from.
  Invoked via `/discover-theme [macro_thesis_id]`.
- **sector-screener** — bottom-up and coverage-driven: given one sector that
  `asx theme coverage` shows as structurally unexamined, screens active universe
  symbols against fundamentals and proposes 0-5 theme / theme-holding candidates.
  The deliberate sibling of `theme-researcher` — they share only the output schema and
  the governance write path. Invoked via `/discover-sector <sector>`.

Still unbuilt: **instrument-selector** (given a theme, proposes 3-5 ASX
instruments/ETFs — the first real use of `theme_holdings.source='llm_inferred'`).

## Program-management agents (3)

These three work **under arbi**. arbi itself is the main session, not an agent file
here (`CLAUDE.md`, `AGENTS.md` §0): it decides what gets built, dispatches these,
and lands the result by PR (`AGENTS.md` §8). Each inherits arbi's standing; each
`tools:` list bounds only what that agent does itself.

**guilfoyle** is the mission planner — mission-control *under* arbi, invoked via
`/arbi-mission`. arbi decides *what matters*; guilfoyle decides *how* an approved
mission gets built: it turns a mission envelope into a task graph, assigns each node to
a specialist, sets the execution order, and returns one readiness verdict. It **plans
and judges only** — read-only (`Read, Glob, Grep`, no `Agent` tool, because a subagent's
`Agent(...)` allowlist is ignored at runtime); `/arbi-mission`'s main loop does the
spawning, testing and review loop, and arbi opens and merges the PR. It never sets
priority (its only pushback is executability evidence, routed up), never merges,
deploys or migrates itself, and never acts on Model A output for capital
(`CLAUDE.md` rule #11).

**reversible-work-builder** is the mutation counterpart to guilfoyle's read-only
planning: it holds `Edit, Write, Bash` for reversible branch work only (edit → test →
commit → `claude/**` push prep), executing one scoped build node of a guilfoyle-planned
mission at a time. Orchestration and mutation never share a process. It builds what the
plan specifies; it never plans, prioritises, merges, deploys, migrates, touches the DB
or secrets, or takes any capital action — arbi lands the PR (`AGENTS.md` §8). Its
charter states honestly that a subagent `tools:` list is not containment; the mechanical
floor (`AGENTS.md` §13, the `main` ruleset) is.

**arbi-red-team** is arbi's adversarial critic — a gate, not a second brief. Per
`AGENTS.md` §9, dispatch it when a call is large, or follows a ONE THING that didn't
land: it stress-tests that call against five failure modes (recency overfit,
task-switching, cleanup-mistaken-for-progress, low-trust memory overriding repo truth,
perfectionism blocking a shippable build) and returns a PASS / CHALLENGE verdict with a
file-cited reason for each. Read-only (`Read, Glob, Grep`); it never proposes its own
"one thing" and never waves through a call that crosses the personal-advice firewall
(s766B) or rule #11.

