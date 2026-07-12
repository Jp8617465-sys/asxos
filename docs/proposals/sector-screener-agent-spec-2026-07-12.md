# `sector-screener` agent — spec (design, not build)

**Status:** proposed — spec only. Not materialized as a live `.claude/agents/*.md`
file, and deliberately so: doing that would make it immediately invocable sitting
next to governed tables before `m14_candidate_agent_db_role_scoping` lands (the
exact risk `.claude/rules/portfolio-conventions.md`'s "Known gap" section already
flags for `macro-economist`/`market-context-narrator`, and explicitly warns not to
compound before Phase 2c adds more agents on the same pattern).
**Scope:** Tier 2b of `docs/proposals/thesis-coverage-framework-2026-07-11.md`
(buildable-now item #5's 5th ranked next step) — agent-assisted sector narrowing.
**Depends on:** `m14_candidate_agent_db_role_scoping` landing (design done —
`docs/proposals/agent-db-readonly-role-design-2026-07-11.md`, migration drafted,
not applied) before first live invocation.
**Last verified:** 2026-07-12
**Owner:** drafted this session; needs James's sign-off before the `.claude/agents/`
file is created and before any live invocation, matching `macro-economist`'s own
6-stage testing progression (fixture → synthetic end-to-end → read-only production
dry-run → human review → approval → paper) per governance-first-architecture §4.8.
**Superseded by:** N/A

---

## Why a sibling agent, not a mode of `theme-researcher`

`theme-researcher` (planned, Phase 2c, not yet built) is explicitly
*macro-thesis-conditioned* — "given a macro thesis, identifies ASX-investable
themes" (`governance-first-architecture-2026-06-30.md:896-898`). Its reasoning
frame is top-down and narrative-first: start from a regime story, find themes that
fit it.

`sector-screener`'s frame is the opposite: bottom-up and **coverage-driven**. It
starts from `asx theme coverage`'s own finding — a sector with active universe
symbols and zero theme/thesis presence — and asks "what's actually here, on the
numbers, independent of whether a macro narrative currently favors it." A sector
can be worth a look because it's *structurally unexamined*, not because a
regime thesis pointed at it.

Conflating the two into one agent file with two modes repeats exactly the
"compounded first-time risk" the governance design doc called out when it split
the original single Phase 2 into 2a/2b
(`governance-first-architecture-2026-06-30.md:1073-1077`). They stay separate
agents, sharing only the output schema and the governance write path (§4 below).

---

## Frontmatter (draft — for the eventual `.claude/agents/sector-screener.md`)

```yaml
---
name: sector-screener
description: Given a sector with low/zero theme-holdings coverage, screens active
  universe symbols in that sector against fundamentals and proposes 0-5 theme/
  theme-holding candidates with cited evidence. Bottom-up, coverage-driven — the
  sibling of theme-researcher's top-down, macro-conditioned mode. Use on demand
  via /discover-sector <sector>. Advisory, read-only — produces a structured
  proposal for human review, never writes to the DB directly.
tools: Read, Glob, Grep, mcp__Supabase__execute_sql
---
```

Tool list matches `macro-economist`/`market-context-narrator` exactly — no
write-capable tool, same accepted-risk footnote (SELECT-only is prompt-enforced
until the read-only role lands; see `portfolio-conventions.md`'s Known gap).

---

## Data sources (verified against the live schema this session)

- **`universe` + latest `fundamentals`** (the `DISTINCT ON (symbol) ... ORDER BY
  symbol, as_of DESC` idiom, matching `asxos/ingestion/fundamentals.py:116-119`
  and now also `asxos/domain/screening/evaluator.py`'s `evaluate_rule`) — the
  sector's active `au_equity` population and their latest fundamentals.
- **`theme_holdings` + `theses`** — which symbols in the target sector already
  have theme or thesis coverage, so the agent never re-proposes what's already
  there. This is the same query shape as
  `asxos/domain/themes/service.py::get_coverage_rollup` (shipped this session) —
  the agent effectively re-derives one sector's row of that rollup as its
  starting context.
- **`screening_rules` + `screening_runs`** (shipped this session, Tier 2a) — if a
  `curated_composite` rule already exists scoped to (or covering) the target
  sector, and has a recent `screening_runs` row, the agent reads that first
  rather than re-deriving the same mechanical filter itself. Tier 2a's shortlist
  is a *pre-filter* the agent should treat as evidence, not bypass — reduces
  redundant work and keeps the mechanical/agent-assisted layers composed rather
  than duplicated, per the framework doc's Tier 1a→2a→2b composition (§5).
- **`governed_active_themes` / `governed_active_theme_holdings`** (migration
  0035 views) — read FIRST, same as `macro-economist`'s step 2, to avoid
  proposing a duplicate of an already-approved theme/holding.
- Deliberately **does not** read `regulatory_events` (no untrusted-RSS-text
  ingestion path — narrower attack surface than `macro-economist`; if a future
  revision adds sentiment/news context, re-apply that agent's untrusted-text
  boundary language verbatim, don't assume it doesn't apply).

---

## On invocation

Takes one required argument: the target **sector** (a `universe.sector` value,
normalized the same way `asx theme coverage` normalizes it —
`COALESCE(NULLIF(sector, ''), 'Unclassified')` — so a sector name printed by that
command can be passed straight in). `/discover-sector <sector>` is the intended
invocation surface (not built here — a new slash command mirroring
`/discover-macro`'s structure, a companion deliverable, not part of this spec).

### 1. Confirm the sector is actually low-coverage (don't screen a well-covered sector)
```sql
SELECT u.sector, count(*) AS symbol_count,
       count(*) FILTER (WHERE th.symbol IS NOT NULL) AS theme_covered,
       count(*) FILTER (WHERE t.symbol IS NOT NULL) AS thesis_covered
FROM universe u
LEFT JOIN (SELECT DISTINCT symbol FROM theme_holdings) th ON th.symbol = u.symbol
LEFT JOIN (SELECT DISTINCT symbol FROM theses) t ON t.symbol = u.symbol
WHERE u.is_active AND u.security_kind = 'au_equity' AND u.sector = $1
GROUP BY u.sector
```
If `theme_covered` is already a meaningful fraction of `symbol_count`, say so
plainly and consider whether screening is actually warranted — the agent's job
is filling *structural* blindness, not re-covering ground.

### 2. Existing approved theme/theme_holding coverage (avoid duplicates)
```sql
SELECT theme_code, name, description FROM governed_active_themes
SELECT symbol, theme_id, exposure_strength FROM governed_active_theme_holdings
  WHERE symbol IN (SELECT symbol FROM universe WHERE sector = $1 AND is_active)
```

### 3. Prior mechanical screen for this sector, if one exists
```sql
SELECT sr.name, sr.rule_json, run.matched_symbols, run.match_count, run.run_at
FROM screening_runs run JOIN screening_rules sr ON sr.id = run.rule_id
WHERE run.sector_scope = $1 ORDER BY run.run_at DESC LIMIT 1
```
If found and recent, treat `matched_symbols` as a pre-filtered starting set
rather than re-deriving fundamentals filters from scratch.

### 4. Sector population + fundamentals (if no recent screen, or to supplement one)
```sql
WITH latest_fundamentals AS (
    SELECT DISTINCT ON (symbol) * FROM fundamentals ORDER BY symbol, as_of DESC
)
SELECT u.symbol, u.market_cap, f.pe_ratio, f.pb_ratio, f.dividend_yield,
       f.roe, f.debt_to_equity, f.revenue, f.net_income
FROM universe u LEFT JOIN latest_fundamentals f ON f.symbol = u.symbol
WHERE u.is_active AND u.security_kind = 'au_equity' AND u.sector = $1
ORDER BY u.market_cap DESC NULLS LAST
```

---

## Proposing candidates

Propose **0-5** candidates per invocation — zero is a valid, expected outcome
("this sector doesn't have a compelling angle right now") and must be reported
as plainly as a positive finding; the agent's per-run deliverable is the
**coverage snapshot** (sector symbol count / theme-linked count /
mechanical-screen-pass count / top candidates with cited rationale), from which
it *may* draft proposals, never a mandate to always produce content — same
discipline as `macro-economist`'s "1-5," applied to the case where the honest
answer is "nothing stood out."

Each candidate is a `ThemeProposal` (a new or existing-but-uncovered theme
this sector fits into) and/or a `ThemeHoldingProposal` (linking a specific
symbol to a theme, existing or newly proposed in the same run) — types already
specified in `governance-first-architecture-2026-06-30.md:463-479`,
`agent_runs.object_type`'s `CHECK` already includes `'theme'`/`'theme_holding'`
(`migrations/0033_governance_schema_core.sql:70`). A `ThemeHoldingProposal` can
reference a theme proposed in the same invocation (by `theme_code`) — the
orchestrating session resolves that ordering the same way it resolves
`evidence_citation_ids` local-position references (see Output, below).

Every candidate must:
- Cite at least one fundamentals/coverage data point actually queried above.
- NOT duplicate an existing `governed_active_theme_holdings` row for that
  symbol (step 2 first).
- Stay within the target sector — a candidate in a different sector is out of
  scope for this invocation (that's a different `/discover-sector` call).

---

## Output — one fenced JSON block, at the end of the response

Mirrors `macro-economist`'s exact shape (`summary` / `proposals` / `evidence`
with local-position `evidence_citation_ids`), adapted for two proposal types
instead of one:

```json
{
  "summary": "One-sentence summary of the sector's coverage state and what was proposed.",
  "sector": "Financial Services",
  "coverage_snapshot": {
    "symbol_count": 193, "theme_covered": 4, "thesis_covered": 1
  },
  "theme_proposals": [
    {
      "theme_code": "regional-bank-consolidation",
      "name": "Regional bank consolidation",
      "description": "...",
      "conviction_band": "medium",
      "stage": "early",
      "macro_thesis_id": null,
      "evidence_citation_ids": ["local:0", "local:1"]
    }
  ],
  "theme_holding_proposals": [
    {
      "theme_code": "regional-bank-consolidation",
      "symbol": "XYZ.AU",
      "exposure_strength": "0.6",
      "direction": "positive",
      "mechanism_text": "...",
      "evidence_citation_ids": ["local:1"]
    }
  ],
  "evidence": [
    {
      "claim": "XYZ.AU trades at PE 8.2 vs sector median ~14, ROE 0.18",
      "tier": "verified",
      "source_type": "db_query",
      "source_table": "fundamentals",
      "source_as_of": "2026-07-01",
      "snapshot_data": {"symbol": "XYZ.AU", "pe_ratio": 8.2, "roe": 0.18}
    }
  ]
}
```

Same evidence-tier discipline as `macro-economist` (`verified` / `inferred` /
`speculative`, `evidence_citation_ids` never references a `speculative` entry,
local-position references resolved to real `agent_evidence` IDs by the
orchestrating `/discover-sector` command after the response — same pattern as
`/discover-macro`).

`theme_code` cross-references between `theme_proposals` and
`theme_holding_proposals` in the same response are resolved by the
orchestrating session the same way `local:N` evidence references are — a
`ThemeHoldingProposal.theme_code` matching a same-run `ThemeProposal.theme_code`
means "attach to the theme this response also proposes," not an existing one.

---

## Boundaries

Read-only and advisory — identical footing to `macro-economist`. Proposes
candidates for human review; never writes to the database, never recommends a
trade, never decides anything is approved (that's `asx theme approve`/
`asx theme holding approve`, shipped this session, made by a human after
reading the evidence).

**SELECT-only.** Same accepted, tracked, prompt-level-only limitation as
`macro-economist`/`market-context-narrator` until the read-only DB role lands
(`m14_candidate_agent_db_role_scoping`) — this spec does not change that
posture, it inherits it. Do not treat this agent's existence as a reason to
deprioritize that migration; if anything, a second agent on the same pattern is
exactly the "compounding" `portfolio-conventions.md` already warned against.

**No untrusted external text.** Unlike `macro-economist`, this agent's data
sources (`universe`, `fundamentals`, `theme_holdings`, `screening_rules`) are
all internal, structured, numeric-or-controlled-vocabulary data — no
`regulatory_events`-style free-text RSS ingestion in scope. If a future
revision adds a text field (e.g. a company description or news snippet) as a
data source, re-apply `macro-economist`'s untrusted-text boundary language
verbatim before doing so — don't assume the narrower surface persists by
default.

---

## What ships before this agent goes live (checklist)

- [ ] `m14_candidate_agent_db_role_scoping` migration applied + the agent MCP
      connection re-pointed to `asxos_agent_ro`
      (`docs/proposals/agent-db-readonly-role-design-2026-07-11.md`) — James's
      call, tier I5.
- [ ] This spec materialized as `.claude/agents/sector-screener.md` — small,
      mechanical once the above lands; this doc is already close to final form.
- [ ] `/discover-sector <sector>` slash command, mirroring `/discover-macro`'s
      parsing + `asx agent-run log` persistence logic.
- [ ] The shared `create_theme_from_agent_run()`/
      `create_theme_holding_from_agent_run()` service functions
      (`asxos/domain/themes/service.py`) — confirmed not yet built (only the
      human path, `create_theme()`, exists today); `theme-researcher`/
      `instrument-selector` need the same functions, land once, shared.
- [ ] `macro-economist`'s 6-stage testing progression (fixture → synthetic
      end-to-end → read-only production dry-run → human review → approval →
      paper) before first live invocation.

## Files referenced

`.claude/agents/macro-economist.md` (template mirrored throughout),
`docs/proposals/thesis-coverage-framework-2026-07-11.md` (Tier 2b, the spec
this implements), `docs/proposals/governance-first-architecture-2026-06-30.md`
(`ThemeProposal`/`ThemeHoldingProposal` types, §5.4 theme-researcher/
instrument-selector framing), `docs/proposals/agent-db-readonly-role-design-2026-07-11.md`
(the blocking dependency), `asxos/domain/themes/service.py`
(`get_coverage_rollup`, `approve_theme`/`approve_theme_holding`),
`asxos/domain/screening/evaluator.py` (Tier 2a, the mechanical pre-filter this
agent composes with), `.claude/rules/portfolio-conventions.md` (Known gap —
agent DB role scoping, the compounding-risk warning), `migrations/0033_governance_schema_core.sql`,
`migrations/0035_macro_theses_and_governance_columns.sql`.
