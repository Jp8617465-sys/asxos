# Thesis Coverage Framework — Universe → Segment → Screen → Thesis

**Status:** proposed
**Scope:** the discovery/triage pipeline that feeds `theses`/`themes`/`theme_holdings`, not the
allocator or capital-deployment path
**Last verified:** 2026-07-11 (live numbers cited below, verified this session)
**Owner:** `requirements-analyst` draft; needs `system-architect` + `backend-architect` sign-off
before build, James sign-off on scope
**Depends on:** `docs/product/roadmap-state.md` (Governance Phase 2c row),
`docs/proposals/governance-first-architecture-2026-06-30.md` (the governance mechanism this
framework must follow verbatim), `m14_candidate_agent_db_role_scoping` (external, parallel — not
redesigned here)
**Superseded by:** N/A

Triggered by James (2026-07-11): "the thesis tracking is an issue — I want coverage on all ASX
universe and we only have 13 or so. we should start and break down from universe, to segment to
stock at a high level." Extended same-day: "one thing to add into your equities like we want also
the etf's etc included in our investment plan not just individual equities" — Tier 0 and Tier 1
below are revised to make instrument kind (not just equity sector) a first-class dimension of
"universe" and "segment" from the start, not a later add-on.

---

## 1. Diagnosis — why coverage is 0.7%, and why "raise the percentage" is the wrong frame

Live numbers (verified this session, ground truth):

| Metric | Value |
|---|---|
| `universe` total rows | 2,403 |
| `universe` active, all `security_kind` | **2,377** — au_equity 1,872 · ETF 471 · hybrid 21 · LIC 13 |
| `theses` total / distinct symbols | 13 / 13 (all `au_equity`; zero ETF/LIC/hybrid coverage) |
| `theses` coverage of active universe | 13 / 2,377 = **0.55%** (13 / 1,872 au_equity-only = 0.69%) |
| `theses.status` breakdown | research 11, active 1 (HUBS, ~100% capital), watching 1 |
| `themes` rows | 1 |
| `theme_holdings` rows / distinct symbols | 1 / 1 |
| `macro_theses` rows | 0 |

**ETFs are not a rounding error on top of equities — they're a quarter of the tracked universe
(471 of 2,377, before hybrids/LICs).** `security_kind` (migration `0037`) already disambiguates
them from `au_equity`, and ETF/LIC ingestion is already wired (ETF Phase-1 `security_kind`
keystone, PR #24; ETF Slice 2a kind-aware ingestion, PR #26) — this framework's job is to make
sure the *coverage* tiers below don't silently mean "equities only" the way the first draft of
this document (and the underlying `theses`/`themes` schema itself) implicitly did.

The 0.7% number, read in isolation, invites the wrong fix ("write more theses"). North-star.md is
explicit that the product is "a small number of opinionated, explainable ideas — not 50 screener
matches" (`docs/product/north-star.md:36`), and moat layer 2 (discipline scaffolding) depends on
the thesis count staying small enough for a 30-day revisit cadence to be humanly honorable
(`migrations/0012_theses_and_themes.sql:119-121`). A framework that pushes toward 1,872 theses
would break the product it's meant to serve. The actual gap is not "too few theses" — it's that
**1,872 symbols have received zero systematic look**, and there is no mechanism between "the
whole universe" and "a fully-articulated, capital-ready thesis" doing that look. Three distinct,
separately-fixable root causes produce this, not one:

**Cause 1 — no intermediate narrowing layer exists in practice.** The only path from `universe`
to `theses` today is the fully manual `enter_thesis()`/`asx thesis open` CLI flow
(`migrations/0012_theses_and_themes.sql` design notes, `asxos/domain/theses/service.py`) — it
requires James to already know which of 1,872 symbols deserves a structured thesis before he
opens one. There is no step that does the 1,872→dozens narrowing *for* him. Coverage caps out
wherever his personal bandwidth caps out.

**Cause 2 — the intermediate layer's schema exists and is essentially unfed.** `themes`/
`theme_holdings` have existed since migration `0012` (theme lifecycle, adjacency, stage
tracking) and sit at 1 row / 1 row today. This is the same class of gap the governance design
doc already names for `theme_holdings.source='llm_inferred'`: "existed since migration 0012 with
zero rows ever written and no approval workflow"
(`docs/proposals/governance-first-architecture-2026-06-30.md:144`). `screening_rules` (migration
`0001`) is a third instance of the same pattern: schema-only since the very first migration,
**zero readers anywhere in `asxos/`** (verified — `grep screening_rules` across `asxos/` returns
no files; the only repo hits are docs, the backup script's table list, and the migration
itself). None of these are "not designed yet" gaps — they're "built, never wired" gaps.

**Cause 3 — the one discovery agent that works sits one rung too high, and its own output queue
is already backed up.** `macro-economist` (Phase 2b, `.claude/agents/macro-economist.md`) is
real, runs, and has produced output — but it proposes *regime-level* macro theses, upstream of
segment and two hops upstream of "stock." `theme-researcher`/`instrument-selector`, the two
agents that would actually touch segment→stock, are "Not started"
(`docs/product/roadmap-state.md:81`). And even macro-economist's own throughput is stalled:
`roadmap-state.md`'s ranked-queue item #3 records **two pending, unresolved `agent_runs`
proposals (#3, #4)** sitting in James's approval queue (`docs/product/roadmap-state.md:168-170`).
Adding more discovery agents without addressing review throughput just grows the same backlog
faster.

None of these three causes involve rule #11 (Model A quarantine, standing per CLAUDE.md #11 and
`docs/model-a-decay-analysis-2026-07-11.md`) — this is a coverage/process gap, not a
signal-quality gap, and the fix must stay model-independent throughout, consistent with
`docs/product/north-star.md` and the ML-shelf decision.

---

## 2. The right unit of "coverage" is not thesis count

Before the tiers: the success metric this framework should target is **"has this segment been
looked at and has a decision been recorded" (pass / promote / reject)**, not "does this symbol
have a thesis." A thesis is deliberately a high-conviction, capital-deployment-ready artifact;
most of the universe should correctly *never* get one. This reframe governs every tier and
success metric below.

---

## 3. Stakeholder / use-case analysis

Single user (James); "stakeholders" here are use cases at each tier, per CLAUDE.md's single-user
context.

| Use case | Actor | Job to be done | Tier |
|---|---|---|---|
| UC1 | James | "Nothing investable should be invisible to any downstream tier." | 0 — Universe (exists) |
| UC2 | James | "Show me, at a glance, which of the 13 sectors have zero theme/thesis presence — where am I structurally blind?" | 1a — Sector |
| UC3 | James | "Give me a small number of named, cross-sector investment narratives that explain *why* a cluster of stocks matters together" (moat layer 3, `north-star.md:45-46`) | 1b — Theme |
| UC4 | James | "Narrow a sector/theme from hundreds of names to a handful worth 10 minutes of my attention, each with cited rationale — I shouldn't do 1,872-wide triage in my head." | 2 — Screening |
| UC5 | James | "The full-thesis mechanism stays exactly as rigorous and human as it is today — just fed by better candidates instead of ad hoc discovery." | 3 — Full thesis (unchanged) |
| UC6 | James | "Every agent-sourced candidate sits in a review queue I can clear in a bounded, predictable time — it should never silently pile up the way the 2 pending macro-thesis proposals have." | Cross-cutting — governance throughput |

---

## 4. The phased tier framework

### Tier 0 — Universe (exists, no work) — spans all instrument kinds, not just equities

2,403 rows, 2,377 active across `au_equity` (1,872), `etf` (471), `hybrid` (21), `lic` (13).
`universe.sector`/`fundamentals.sector` already populated for equities and already load-bearing
elsewhere: it's "the cache the portfolio allocator's sector cap (`constraints.apply_sector_cap`)
groups on" (`migrations/0023_fundamentals_add_sector.sql:6-7`). `universe.security_kind`
(migration `0037`) already disambiguates `au_equity` from `etf`/`lic`/`hybrid`/`us_equity`/
`index`, so this tier's raw data is scoped correctly today — the gap is downstream, in Tier 1's
segmentation logic and every later tier, silently assuming "symbol" means "ordinary share."

**Every tier below applies to the full 2,377, not the 1,872-equity subset.** Concretely:
Tier 1a's sector rollup must report an explicit non-equity bucket (ETF/LIC/hybrid have no GICS
sector); Tier 1b's theme→holding mapping is already instrument-kind-agnostic
(`theme_holdings.symbol` has no kind filter — an ETF can sit in a theme today, e.g. a "broad
market beta" theme holding VAS/VGS, exactly as naturally as a stock); Tier 2's screening
evaluator needs kind-appropriate criteria (below); Tier 3's full-thesis mechanism already works
for any `security_kind` — `enter_thesis()` has no equity-only constraint, it's simply never been
used for a fund because nothing upstream ever surfaced one as a candidate. This framework does
not re-decide *how* ETFs/LICs are ingested, valued, or held — that mechanics is
`docs/proposals/multi-instrument-expansion-2026-07-11.md` and the ETF Slice 1/2 roadmap items
(migration 0037, PR #24/#26). This framework only ensures the *discovery/coverage* pipeline
treats them as first-class citizens from Tier 0 up, not a special case bolted on later.

### Tier 1 — Segment: sector *and* theme, as a hybrid, not a choice between them

**Argument for hybrid (not sector-only or theme-only):**

- **Sector is the free, already-populated, mechanical substrate.** Zero build cost —
  `universe.sector` exists, is already used by the allocator's diversification cap, and the
  13-sector distribution is already known (Basic Materials 779 down to Utilities 24, blank 23).
  It's the only grouping that can be computed *today* with no new schema, no agent, no
  governance.
- **Sector is explicitly NOT a proxy for real economic clustering, per this codebase's own
  documented finding.** `portfolio-conventions.md`'s risk-blindness section states: "The ASX 200
  has tight beta clustering that doesn't map cleanly to GICS sectors — Materials and Financials
  are >40% of the index and move together more than the sector taxonomy implies... A 20-name
  inverse-vol portfolio... can still carry 0.8+ pairwise correlation across half the names"
  (`.claude/rules/portfolio-conventions.md` §v1 risk-blindness invariants). If that's true for
  portfolio construction, it's equally true for discovery: a cross-sector cluster like "lithium
  supply chain" (extraction in Basic Materials, processing in Industrials, financing/royalty
  vehicles elsewhere) is invisible to a sector-only segmentation.
- **Themes are the product-facing segment per the north star, and the schema is already fully
  built and governed.** Moat layer 3 is named "theme stewardship," not "sector stewardship"
  (`north-star.md:45-46`): "James names themes; the system maintains the stock→theme mapping
  with explainable exposure, surfaces adjacencies, tracks where a theme sits on the
  generalisation curve." `themes` carries `adjacent_codes`, a 6-value stage lifecycle, and
  `conviction_band` (`migrations/0012_theses_and_themes.sql:23-51`) — none of which sector has.
  Governance is fully wired: `governance_status`/`source_run_id` + audit triggers on
  `themes`/`theme_holdings` since migration `0035`/`0036`, plus the
  `governed_active_themes`/`governed_active_theme_holdings` gated views.

**Conclusion: sector is the mechanical pre-filter that makes discovery tractable (Tier 1a); theme
is the narrative, human-approved unit that's the actual product surface (Tier 1b).**
Sector-scoping is what lets an agent (or James) work with ~24-780 names instead of 1,872 in one
pass — matching how the 5 existing investment-analysis agents are already scoped per-symbol,
never universe-wide.

**Sector doesn't apply to the 505 non-equity instruments (ETF/hybrid/LIC) — they need a
different Tier 1a lens.** A fund has no GICS sector of its own; its relevant segment is *what it
holds/tracks*: asset class (equity / fixed income / commodity / currency), geography (domestic /
international developed / emerging), and breadth (broad-market beta vs sector/thematic-specific,
e.g. VAS/VGS vs a lithium-miners ETF). This is standard ETF-industry taxonomy, not a new
invention, and it composes cleanly with Tier 1b: a thematic ETF (e.g. a battery-metals ETF)
naturally attaches to the *same* `themes` row as the individual miners it overlaps with — one
theme, mixed-instrument-kind holdings, which `theme_holdings` already supports schema-wise
(no kind filter on `symbol`). **This asset-class/geography/breadth taxonomy is not designed
here** — it's a small, well-scoped follow-on (a lookup table or an enum on `universe`/
`fundamentals` for non-equity rows), flagged for `backend-architect` alongside the Tier 2a
evaluator design, since both land in the same migration/module.

| | Tier 1a — Sector | Tier 1b — Theme |
|---|---|---|
| Unit of work | A per-sector coverage rollup: symbols / theme-linked / thesis-linked, per sector | An approved `themes` row + its `theme_holdings` rows |
| Existing schema used | `universe.sector`, `fundamentals.sector` (fully populated) | `themes`, `theme_holdings`, `governed_active_themes/theme_holdings` views (migration 0012/0035/0036) |
| Net-new | A read-only rollup query/CLI command — no migration | None (schema complete); CLI governance verbs are the gap — see §6 |
| New agent needed? | No — pure SQL | No new agent to *hold* the schema; Tier 2 agents populate it |
| Governance path | None — not investment content, same status as `universe.sector` itself | Existing: human via `asx theme create`/`attach` (DEFAULT `governance_status='approved'`) **or** agent-originated via `agent_runs` → draft → `pending_review` → human `approve`/`reject` — mirrors `macro-economist` exactly |

### Tier 2 — Screening/triage: mechanical pre-filter, then agent-assisted narrowing

**Direct answer to "is `screening_rules` already wired to anything": no.** `grep -r
screening_rules asxos/` returns zero files. It has existed, schema-only, since
`migrations/0001_initial.sql:209-218` (`id, name, source_method, rule_json, is_active,
description`). It is listed in `CLAUDE.md`'s schema reference and in the backup script's table
list (`scripts/backup_irreplaceable.sh`), but nothing reads or writes it. **Two more things
worth flagging about it before reuse:** (1) `.claude/rules/screening-conventions.md`, which
`CLAUDE.md`'s "Auto-activating rules" section claims exists and auto-attaches, **does not exist
on disk** — `.claude/rules/` contains only `api-conventions.md`, `job-conventions.md`,
`ml-conventions.md`, `portfolio-conventions.md` (verified via `Glob`); this is a doc/reality
drift worth fixing alongside this proposal, not designed here. (2) `source_method`'s documented
vocabulary (`shap_threshold | surrogate_tree | curated_composite`, a comment, not a `CHECK`
constraint) is a carryover from the prior dead repo's ML-derived screening approach
(`extract_shap_thresholds.py`, `backtest_screening_rules.py` — confirmed present in the old-repo
forensic audit `docs/foundation/phase-1-audit.md` but **absent from `jobs/*.py`** in the current
`asxos` repo). `shap_threshold`/`surrogate_tree` are Model A artifacts; reusing them under rule
#11 would be exactly the ML-derived screening this task rules out. **Recommendation: tighten
this at reuse-time** — either a real `CHECK (source_method = 'curated_composite')` or a
documented "only `curated_composite` is model-independent-safe, the other two values are
historical and must not be written" note, so nothing accidentally reactivates a SHAP-threshold
rule.

- **2a — Mechanical screen (buildable now, no agent).** Concrete unit of work: wire
  `screening_rules.rule_json` (`curated_composite` only) to an actual evaluator against
  `fundamentals`/`prices`/`universe`, scoped by sector, plus a lightweight results-log (a small
  net-new table, or reuse of the evidence-snapshot pattern) so runs are auditable. This table is
  **not investment content** — it's a data filter, the same category as `prices`/`fundamentals`,
  "re-derivable" and not part of the irreplaceable-table backup set
  (`portfolio_daily_snapshots` is the precedent for this classification, `CLAUDE.md`'s schema
  section). No governance gate needed to *run* a screen; governance only starts once a human or
  agent turns a screen result into a `theme`/`thesis` proposal.
- **2b — Agent-assisted narrowing (blocked on agent DB role scoping).** Concrete unit of work: a
  new discovery agent, `sector-screener`, modeled character-for-character on
  `macro-economist.md`'s template (verified-columns block, numbered procedure, `Read, Glob,
  Grep, mcp__Supabase__execute_sql` tools only, evidence-tier tagging, capped proposal count,
  explicit Boundaries/SELECT-only section). **Recommendation: a fourth sibling agent, not a mode
  bolted onto `theme-researcher`.** `theme-researcher`'s design is explicitly *macro-thesis-
  conditioned* — "given a macro thesis, identifies ASX-investable themes"
  (`governance-first-architecture-2026-06-30.md:896-898`) — a top-down, narrative-first
  reasoning frame. `sector-screener`'s frame is bottom-up and coverage-driven: sweep a sector
  with zero theme/thesis presence and report what's there, independent of whether a macro
  narrative currently favors it. Conflating the two into one agent file with two modes repeats
  exactly the "compounded first-time risk" the design doc explicitly called out when it split
  the original single Phase 2 into 2a/2b (`governance-first-architecture-2026-06-30.md:1073-
  1077`). **Zero output-schema change needed:** `sector-screener` produces
  `ThemeProposal`/`ThemeHoldingProposal` objects — types already specified
  (`governance-first-architecture-2026-06-30.md:463-479`) and `agent_runs.object_type`'s `CHECK`
  constraint already includes `'theme'`/`'theme_holding'` (`migrations/0033_governance_schema_
  core.sql:70`). Per-invocation output should be capped (1-5, mirroring `macro-economist`) — its
  primary deliverable per run is a **coverage snapshot** (sector symbol count / theme-linked
  count / mechanical-screen-pass count / top candidates with cited rationale), from which it
  *may* draft 0-5 proposals, not a mandate to always produce content.

| | Tier 2a — Mechanical screen | Tier 2b — Agent-assisted |
|---|---|---|
| Existing schema reused | `screening_rules` (unwired since migration 0001) | `agent_runs`, `agent_evidence`, `ThemeProposal`/`ThemeHoldingProposal` schemas (Section 4.2 of the governance doc) |
| Net-new | Evaluator code, a `CHECK`-tightened or documented `source_method`, a small results-log table | `.claude/agents/sector-screener.md`, `/discover-sector` slash command (mirrors `/discover-macro`), the shared `create_theme_from_agent_run()`/`create_theme_holding_from_agent_run()` service functions — **confirmed not yet built** (see §6) |
| New agent? | No | Yes — `sector-screener` |
| Governance path | None (data filter) | Identical to `macro-economist`: advisory, read-only, `agent_runs` logged → `asx theme open --from-agent-run` → `asx theme approve`/`reject` (CLI verbs currently missing, see §6) |

### Tier 3 — Full thesis (unchanged mechanism, better-fed inputs)

The existing 13 theses, `enter_thesis()`/`asx thesis open`, entry band/stop/target/timeline
rigor — **no change to this mechanism.** It stays 100% human-authored; agent-drafted full theses
remain explicitly deferred (`m14_candidate_agentic_thesis_drafter`: "No `ThesisProposal` schema
yet — agent-drafted theses can't be created end-to-end," `docs/product/roadmap-state.md:191`;
`governance-first-architecture-2026-06-30.md:480-483`: "No Phase 2 agent in this document
produces a full instrument thesis"). This framework only changes what feeds James's attention
*before* he decides to open one — an approved `theme_holdings` row from Tier 1b/2b, or a Tier 2a
shortlist candidate, replaces ad hoc noticing.

---

## 5. Governance path — every tier, one rule

No tier in this framework ever writes directly to `theses`/`themes`/`theme_holdings`/
`macro_theses`. The path is always: **agent proposes (typed object, evidence-cited) →
`agent_runs` (logged by the orchestrating session, never the agent itself) → `asx <object> open
--from-agent-run <id>` (draft, auto-advances to `pending_review`) → human `asx <object>
approve|reject --reason "..."`** — identical in shape to `macro-economist`/`/discover-macro`/`asx
macro-thesis approve` today. Tiers 0, 1a, and 2a involve no agent and no governance because they
touch no investment content — they're data groupings and filters, the same category as
`universe.sector` or `prices` itself.

---

## 6. What's buildable now vs. blocked

**Buildable now — no dependency on agent DB role scoping, no new agent:**

1. **Tier 1a coverage rollup — LANDED 2026-07-11.** `asx theme coverage`
   (`asxos/domain/themes/service.py::get_coverage_rollup` + `asxos/cli/theme.py`, 29 tests) —
   sector for equities, an explicit non-equity bucket for ETF/hybrid/LIC, pure SQL against
   existing columns (`universe.sector`, `universe.security_kind`, `theme_holdings`, `theses`).
   This is literally the picture James asked for ("break down from universe, to segment...
   understand what's happening," extended to "ETFs etc, not just individual equities") — the
   non-equity rows report as one `(non-equity)` bucket per `security_kind` until the
   asset-class/geography taxonomy (Tier 1, above) lands as its own follow-on.
2. **Tier 2a mechanical screen — LANDED 2026-07-12 (au_equity path).** `screening_rules`
   (unwired since migration 0001) is now wired to a real, SQL-injection-safe evaluator:
   `asxos/domain/screening/{types,evaluator}.py` + `asx screen list`/`asx screen run`
   (`asxos/cli/screen.py`), 38 tests in `tests/test_screening_evaluator.py`. Draft migration
   `migrations/0038_screening_evaluator_wiring.sql` (**NOT yet applied** — James applies via
   `mcp__supabase__apply_migration`) tightens `source_method` to `curated_composite` only via a
   real `CHECK` and adds the `screening_runs` audit log (non-governed, re-derivable — same
   category as `prices`/`fundamentals`). Routed through `backend-architect` per `CLAUDE.md`'s
   routing table as planned. Scope note: the evaluator's base query is `au_equity`-only by
   design (hardcoded `security_kind` filter, not author-controlled) — kind-appropriate
   ETF/LIC/hybrid criteria (asset-class/geography/breadth, not PE/PB fundamentals) remains
   undesigned, per Tier 1's non-equity segmentation note above.
3. **CLI governance verbs for themes.** `asxos/domain/themes/service.py::approve_theme`/
   `reject_theme`/`approve_theme_holding`/`reject_theme_holding` **exist today, confirmed**
   (lines 356, 395, 428, 465) but are **unreachable from any CLI** — `asxos/cli/theme.py` has no
   `approve`/`reject`/`open --from-agent-run` commands, unlike `asxos/cli/macro_thesis.py`, which
   has all three. Wiring these (mirroring `macro_thesis.py`'s exact shape: `--reason` required,
   `_require_personal_use()` gate) is small, low-risk, and reduces Phase 2c's blast radius by
   landing one link of the dependency chain early. **Caveat:** this alone doesn't unlock real
   usage — no draft-producer for `themes`/`theme_holdings` exists yet either (see next point) —
   but it's necessary infrastructure regardless of which agent ships first.
4. **Clear the existing approval backlog.** `roadmap-state.md`'s ranked-queue item #3 — 2 pending
   `agent_runs` proposals (#3, #4) awaiting `asx macro-thesis open --from-agent-run`/`approve`.
   Zero build; directly tests whether Cause 3 (approval throughput) is a real bottleneck before
   adding a fourth potential source of pending proposals.

**Blocked on `m14_candidate_agent_db_role_scoping` (roadmap-state.md ranked-queue item #2 —
placed ahead of Phase 2c "regardless of Model A"):**

5. **`sector-screener` agent build (Tier 2b) and the shared
   `create_theme_from_agent_run()`/`create_theme_holding_from_agent_run()` service functions.**
   These are **confirmed not yet built** — `themes/service.py` has `create_theme()` (human path
   only) but no `_from_agent_run` variant, unlike `theses/service.py::create_thesis_from_agent_
   run()`, which Phase 1 already built. `theme-researcher`/`instrument-selector` need the exact
   same functions, so land them once, shared across all three agents, not duplicated. Every new
   agent sitting next to governed tables repeats the documented, unresolved risk: SELECT-only
   enforcement is prompt-level only, no DB-level backstop, with untrusted RSS-sourced text
   (`regulatory_events`) already adjacent (`.claude/rules/portfolio-conventions.md` §Known gap,
   `m14_candidate_agent_db_role_scoping`). This proposal does not redesign that fix (in progress
   in parallel this session) — it only inherits the same gate `theme-researcher`/
   `instrument-selector` already wait behind.

---

## 7. Success metrics (measurable, not thesis-count)

| Metric | Target | Rationale |
|---|---|---|
| M1 — Sector visibility exists | A sector-coverage rollup (item 1) is runnable and accurate against live counts within 1 week of acceptance | Directly answers James's ask; binary/verifiable |
| M2 — Mechanical screen operational | ≥1 `curated_composite` `screening_rules` row evaluated end-to-end against a real sector, producing a bounded (≤20) logged shortlist | Proves Tier 2a works before any agent is added |
| M3 — Approval-queue health | 0 `agent_runs` rows with `acted_on=FALSE` older than 14 days, at every `/arbi` wake | Mirrors the existing 14-day evidence-staleness bar (`governance-first-architecture-2026-06-30.md` §4.1); directly targets Cause 3 |
| M4 — Segment population (post role-scoping) | `themes` grows from 1 to covering sectors James has explicit conviction in, within 2 quarters of `sector-screener`/`theme-researcher` shipping | Explicitly **not** 13-of-13 sectors or 1,872-of-1,872 symbols |
| M5 — Thesis count discipline | `theses` count stays low and every `active`-status thesis's `revisit_due_at` is honored | Already tracked by existing tooling (`thesis-milestone-monitor`); not re-measured here — a growing thesis count would be a regression, not progress |

---

## 8. Out of scope (explicit)

- Any ML/signal-driven candidate generation, ranking, or scoring — rule #11 is standing
  (`CLAUDE.md` #11, `docs/model-a-decay-analysis-2026-07-11.md`, `north-star.md` non-negotiable
  #1).
- Any direct agent write to `theses`/`themes`/`theme_holdings`/`macro_theses` — always
  `agent_runs` → `pending_review` → human approval, no exceptions, at every tier.
- A 100%-of-universe (or even majority) thesis-coverage target — north-star.md explicitly wants
  a small number of opinionated ideas.
- Building `theme-researcher`/`instrument-selector` end-to-end here — they're already-scoped
  Phase 2c items; this proposal adds `sector-screener` as a sibling and sequences all three
  behind the same prerequisite.
- Resolving `m14_candidate_agent_db_role_scoping` itself — external, parallel, not redesigned
  here.
- Any change to the allocator, portfolio construction, or capital-deployment path —
  `portfolio-conventions.md`'s allocator/brief split is untouched; this framework only affects
  what reaches the *governance* queue, never the *allocation* path.
- Auto-approval/auto-promotion of any kind, at any tier.
- Actually writing the code for items 1-4 in §6 — this document is the proposal; implementation
  is a separate, subsequent step.

---

## 9. Ranked next steps (by leverage)

1. **Ship the Tier 1a sector-coverage rollup.** Zero schema, zero agent, answers James's literal
   question this week.
2. **Wire `screening_rules` to a real `curated_composite` evaluator + results log (Tier 2a),
   scoped by sector.** Route through `backend-architect` for schema/module design. Independently
   useful even before any agent exists.
3. **Wire the missing `asx theme approve|reject|open --from-agent-run` CLI commands** onto the
   already-built `themes/service.py` governance functions. Small, low-risk, unblocks nothing
   alone but removes a link from Phase 2c's dependency chain in advance.
4. **Clear the 2 pending `agent_runs` macro-thesis proposals** (`roadmap-state.md` ranked-queue
   #3) before adding `sector-screener` to the same queue — tests whether Cause 3 is real before
   compounding it.
5. **Design (not build) the `sector-screener` agent spec**, modeled on `macro-economist.md`,
   scoped bottom-up (sector → theme/instrument, coverage-driven) as distinct from
   `theme-researcher`'s top-down (macro thesis → theme, narrative-driven) mode — ready to build
   the moment agent DB role scoping lands, sharing the same
   `create_theme_from_agent_run()`/`create_theme_holding_from_agent_run()` functions
   `theme-researcher`/`instrument-selector` will also need.

---

## 10. Implementation-readiness validation

Before any code lands, per this repo's existing testing-progression convention
(`governance-first-architecture-2026-06-30.md` §4.8):

- [ ] Items 1-2 (§9) reviewed by `backend-architect` for schema/query design before
      implementation.
- [ ] `screening_rules.source_method` reuse explicitly resolves the ML-artifact-vocabulary
      concern (§4) — either a tightened `CHECK` or a documented restriction — before any row is
      written.
- [ ] Item 3's CLI verbs are live-verified against the real `themes_governance_audit`/
      `theme_holdings` triggers in a rolled-back transaction (not mocked tests alone) — per the
      Phase 2a "verification lesson" (`.claude/rules/portfolio-conventions.md` §Verification
      lesson), since the INSERT-then-UPDATE ordering bug already bit this exact trigger pattern
      once.
- [ ] `sector-screener`'s eventual agent file passes the same 6-stage testing progression
      `macro-economist` did (fixture → synthetic end-to-end → read-only production dry-run →
      human review → approval → paper) before first live invocation.
- [ ] `CLAUDE.md`'s agent-count table and `.claude/rules/screening-conventions.md`'s dangling
      reference (confirmed absent from disk) get corrected alongside this work — flagged here,
      not fixed by this proposal.
- [ ] James signs off on the sector-vs-theme hybrid argument (§4) and the "coverage ≠ thesis
      count" reframe (§2) before build starts, since both are judgment calls this analysis
      argues for but does not have authority to finalize.

---

## Files read/cited

- `docs/product/roadmap-state.md`, `docs/product/north-star.md`,
  `docs/model-a-decay-analysis-2026-07-11.md`, `docs/product/ml-engine-shelf-2026-07-11.md`
- `docs/proposals/governance-first-architecture-2026-06-30.md` (full, both halves)
- `.claude/agents/macro-economist.md`, `asxos/cli/macro_thesis.py`, `asxos/cli/theme.py`
- `migrations/0001_initial.sql`, `0012_theses_and_themes.sql`,
  `0023_fundamentals_add_sector.sql`, `0033_governance_schema_core.sql`,
  `0035_macro_theses_and_governance_columns.sql`, `0037_security_kind.sql`
- `asxos/domain/themes/service.py`, `asxos/domain/theses/service.py`
- `.claude/rules/portfolio-conventions.md`, `.claude/rules/` directory listing (confirmed
  `screening-conventions.md` absent)
- `docs/foundation/BUILD_GUIDE.md`, `docs/foundation/phase-1-audit.md`,
  `docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md`, `scripts/backup_irreplaceable.sh`
  (screening_rules cross-references)
