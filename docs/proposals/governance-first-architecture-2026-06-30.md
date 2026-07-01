# asxos Investment Process — Governance-First Architecture

**Document status:** This is the hardened revision of a full rewrite of the prior plan
at this path, after two rounds of external architecture review. Round 1 found the
original combined document unsafe to hand to an implementation agent: it mixed
completed work, current state, proposals, and historical notes with no single
authoritative state, contained direct contradictions (e.g. claiming `sleeves.py` both
exists and doesn't), and had no governance layer for AI-agent-generated investment
content before it could become persistent portfolio state. That produced the rewrite
below. Round 2 confirmed the rewrite's direction was sound and found the governance
layer itself needed hardening: approval enforced only at the service layer (bypassable
by a direct write), evidence recorded as "how it was obtained" rather than "what was
observed" (not replayable), raw SQL as an intermediate agent artifact, three
inconsistent approval-state shapes across four tables, and free-form JSON invalidation
conditions with no closed vocabulary. This revision resolves all of it. Plan A Session
1 (a `macro_theses` table, `market_context` global columns, three discovery-agent
files) was implemented under the pre-review design, then **fully reverted** — both the
DB schema (via Supabase MCP) and the local files — to keep the repo clean while this
redesign happened. **Nothing from that session exists in the repo or the DB today.**

This document was authored during a Claude Code plan-mode session and is committed
here (`docs/proposals/`) rather than left only in the ephemeral plan-mode file
(`~/.claude/plans/`), because the remote execution environment's container is
reclaimed after a period of inactivity — a governance-critical design document that
Phase 1-4 depend on in full must not live somewhere that can disappear.

Every section below is explicitly labeled **[CURRENT]**, **[PLANNED]**, **[FUTURE]**,
or **[HISTORICAL]**. Do not infer status from prose — only the label is authoritative.

**Progress since authoring (update this section, don't let it drift from Section 1):**
- **Phase 0 — done.** `build.py`/`compose.py` signal/model_versions queries filtered
  by the resolved production model instead of being unfiltered.
- **Phase 0.5 — done.** `model_versions.approved_for_allocation` gate (migration
  `0032`, applied to prod Supabase; `model_a/v1_5` explicitly grandfathered).
  `build.py`, `compose.py`, and `asxos/domain/brief/collectors/active_theses.py`
  (a gap found during Phase 0.5's own security review — the V2 brief's actual
  production collector had an unfiltered, unparameterized `model='model_a'` literal
  with no gate at all) all now resolve the production model via the shared
  `asxos/domain/models/production_gate.py::resolve_production_model()` helper before
  reading `signals`, hard-failing on 0 or >1 eligible rows.
- **Phase 1 — done.** `theses.governance_status`/`source_run_id` (migration 0033),
  `thesis_evidence`/`agent_evidence`/`agent_runs`/`governance_events` (migration
  0033), `thesis_revisions` provenance columns + the `theses_governance_audit`
  trigger (migration 0034 — this codebase's first Postgres trigger). New:
  `asxos/domain/theses/schemas.py`, `service.py::create_thesis_from_agent_run()`/
  `approve_object()`/`reject_object()`, `enter_thesis()`'s governance guard,
  `asx thesis approve|reject` + `open --from-agent-run`. **Bug found and fixed
  during implementation, corrects Section 4.7 below:** the single-shared-trigger-
  function design (one function, `TG_ARGV[0]`-dispatched across `theses`/
  `macro_theses`/`themes`/`theme_holdings`) fails at runtime with "record NEW has
  no field macro_thesis_id" — PL/pgSQL validates `NEW`/`OLD` field references
  against the trigger's bound table for every `CASE` branch, not just the one that
  executes at runtime. Fixed with a `theses`-specific function
  (`_check_theses_governance_audit()`, no `TG_ARGV`, no `CASE`). Phase 2 must write
  its own per-table function(s) for `macro_theses`/`themes`/`theme_holdings` — do
  not assume this one generalizes; see migration
  `0034_governance_audit_trigger_and_revision_provenance.sql`'s header comment for
  the full account (confirmed by hitting the error live against Supabase before
  applying the fix). **Second bug found and fixed by a post-implementation security
  review pass, also corrects Section 4.7 below:** the trigger's `EXISTS` check
  validated `object_id`/`to_status`/`xact_id` but never `from_status` against
  `OLD.governance_status` — a hand-authored transaction bypassing `service.py`
  could claim an arbitrary prior state. Fixed by adding `AND from_status =
  OLD.governance_status`; re-applied to prod and re-verified with a new
  adversarial check (spoofed `from_status` now correctly rejected) alongside the
  original two checks (unaudited UPDATE rejected, correctly-audited UPDATE
  accepted).
- **Phase 2-4 — not started.** See Section 7 below.

---

## 1. Authoritative current state

### 1.1 What exists today, verified against the live repo and DB (2026-06-30)

**[CURRENT] Thesis/theme schema (migration 0012, live):**
- `theses` — `thesis_id`, `symbol`, `status` (research→watching→active→exited/expired),
  `thesis_text`, `entry_band_lower/upper`, `stop_price`, `target_price`,
  `timeline_days`, `invalidation_conditions JSONB DEFAULT '[]'` (currently
  `{"condition": TEXT, "status": "active"|"triggered"|"resolved", "note": TEXT|null}`,
  **100% manually set today — nothing evaluates these against live data**),
  `conviction_level` SMALLINT 1-5, `last_revisited_at`, `revisit_due_at` (30-day
  default). No `governance_status` column yet (Section 4 adds it).
- `thesis_revisions` — append-only, 11-value `revision_type` CHECK enum, `diff JSONB`,
  `reasoning TEXT NOT NULL CHECK (reasoning <> '')`. Written exclusively via
  `asxos/domain/theses/service.py` (`open_thesis`, `revise_thesis`, `review_thesis`,
  `enter_thesis`, `exit_thesis`) — always single-shot, always human-initiated today.
  Convention this design extends throughout: `async with conn.transaction()`, an
  allowlist dict (`REVISABLE_FIELDS` in `asxos/domain/theses/types.py`) checked before
  any write, `_serialise()` (`str(Decimal_value)`, never `float()`).
- `themes` — `theme_code` slug, `conviction_band`, `stage` (6-value lifecycle enum),
  `adjacent_codes TEXT[]`, `retired_at` (NULL = active).
- `theme_holdings` — PK `(theme_id, symbol)`, `exposure_strength NUMERIC(8,6)` [0,1],
  `direction`, `mechanism_text`, `source CHECK IN ('user','llm_inferred',
  'system_default')` — **`llm_inferred` has existed since migration 0012 with zero
  rows ever written and no approval workflow.** This is the exact gap Section 4 closes.
- `macro_theses` — **does not exist.** (Reverted; see document status above.)

**[CURRENT] Multi-sleeve / factor infrastructure — verified, resolving a prior
contradiction:**
- `asxos/domain/portfolio/sleeves.py` — **does NOT exist.** Any future blending logic
  must be built from scratch.
- `asxos/domain/research/alpha_eval.py` — **exists** (research domain, not portfolio
  domain — a prior draft misfiled this).
- `asxos/domain/research/factor_scores.py` — **exists** (research domain).
- Migration `0027_research_store.sql` — **exists**, defines 7 tables (`rs_security_master`,
  `rs_corporate_actions`, `rs_financial_statements`, `rs_fundamentals_pit`,
  `rs_factor_scores`, `rs_index_membership`, `rs_estimates`). **Schema-only, zero rows,
  no ingestion jobs wired.**
- `profiles.sleeve_weights_json` — **does not exist.** `profiles.score_weights_json`
  blends `prob_up`/`expected_return` *within* `model_a`, not across models.
- `model_versions` — one row: `model='model_a', version='v1_5', is_active=TRUE`
  (migration 0003). No second model row exists anywhere.
- `asxos/domain/theses/trajectory.py` — exists (pure Decimal thesis-pace classifier).
- `asxos/domain/benchmark/returns.py` — exists (pure Decimal return/alpha math).

**[CURRENT — RESOLVED by Phase 0/0.5, see Progress note above] A live correctness gap
that has now been fixed:** `asxos/domain/portfolio/build.py`, `asxos/brief/compose.py`,
and `asxos/domain/brief/collectors/active_theses.py` used to query `signals` and
`model_versions` without filtering by `model` (or, in `active_theses.py`'s case, with
an unparameterized hardcoded literal and no approval gate at all). All three now
resolve the production model through `asxos/domain/models/production_gate.py` before
reading signals, hard-failing on 0 or >1 eligible rows.

**[CURRENT] Five live investment-analysis agents** (`thesis-coherence-guard`,
`thesis-milestone-monitor`, `benchmark-performance-analyst`, `portfolio-coherence-reviewer`,
`market-context-narrator`), all advisory/read-only (`Read, Glob, Grep,
mcp__Supabase__execute_sql` — no `WebSearch`/`WebFetch` on any of them, confirmed),
feeding `/pm-review [SYMBOL]`. These are **not** being redesigned — they are the
stylistic template the new discovery agents (Section 5) must match: verified-columns
block, numbered procedure, explicit Boundaries section, cited evidence only.

**[CURRENT] `docs/research/alpha-signal-verification.md`** — the only rigorous
edge-validation study in this codebase. Headline finding: Model A's prob_up rank-IC is
**+0.095 (t=1.84) at 5 days**, reversing to **−0.060 (t=−1.83) at 21 days**, on an
effective sample of roughly two independent market episodes once window-overlap is
accounted for. This is the concrete cautionary example Section 4.6 builds on.

**[CURRENT] `docs/maintenance/paper-portfolio-monitoring.md`** — already uses a
`[VERIFIED]/[INFERRED]/[MISSING]` evidence-labelling convention in production
monitoring code. Section 4.2's agent evidence taxonomy aligns with this existing
vocabulary rather than inventing a parallel one (swapping `[MISSING]` for
`[SPECULATIVE]`, which means something different — agent judgment, not absent data).

### 1.2 What is approved (this document, signed off via ExitPlanMode 2026-06-30)

The governance model, schema, and phased sequencing in Sections 4–7 below.

### 1.3 What is proposed but not yet built — nothing exists in the repo for any of this

Everything in Sections 4–7 is **[PLANNED]** unless marked otherwise, except Section
4.4 (Phase 0/0.5, now **[CURRENT]** — see Progress note). No code, no migration, no
agent file for Phase 1 onward exists today.

### 1.4 What must NOT be implemented yet (explicit preconditions)

- **No discovery agent (`macro-economist`, `theme-researcher`, `instrument-selector`)
  may be built or invoked until Phase 1 (Section 7) ships** — the governance schema
  (`thesis_evidence`, `agent_runs`, `theses.governance_status`, `governance_events`,
  the audit trigger) must exist first. This is the direct fix for the gap that caused
  the prior revert.
- **No `macro_theses` row, agent-drafted `theses` row, `theme_holdings.source=
  'llm_inferred'` row may be written except via the structured-proposal service
  functions (Section 4.2).** No raw SQL string generated or executed as an
  intermediate artifact, ever — agents produce typed proposal objects, never SQL.
- **No factor/momentum sleeve work (Plan B, Section 8) may begin** — Phase 0.5 (the
  shared precondition) is now done, so Plan B is unblocked on that front, but nothing
  in Plan B has started.

### 1.5 [HISTORICAL] Prior completed work (compressed — full detail in git history)

These shipped in earlier sessions and are live in production today; they are not
affected by this redesign:
- Stage 1–4 of the original `/pm-review` build (AXJO.INDX benchmark ingestion,
  steady-state SHAP, the 5 investment-analysis agents, the `/pm-review` synthesizer).
- The `.US`-only foreign-suffix bug-class fix (`asxos/domain/prices/fx.py` +
  4 call-site fixes).
- HUBS.NYSE + benchmark "lit up" via the holding-driven fetch (Option B).

---

## 2. Resolved contradictions (changelog)

| Prior claim | Resolution |
|---|---|
| "`sleeves.py` exists, just unwired" vs "`sleeves.py` does not exist" | **Does not exist.** Must be built from scratch if Plan B (Section 8) ever proceeds. |
| "Phase 1 requires no code changes" vs a multi-step Phase 1 with migrations and new modules | Every phase in Section 7 lists concrete file changes. No phase is "no code changes." |
| Hedge funds (Bridgewater/AQR/etc.) cited as validating the approach | Reframed per Section 4.3 — inspiration only, never evidence of validated edge. |
| `theme_holdings.source='llm_inferred'` implied as already-working | Confirmed **zero rows ever written** with this value; Section 4.2 builds the first real workflow for it. |
| Paper-trading period implied to validate "the strategy works" | Reframed per Section 4.6 into five distinct validation tiers; a short paper-trade window proves infrastructure/operational tiers only, never alpha. |
| Approval enforced only at the service-layer (bypassable by a direct write/migration/script) | Section 4.7 — DB-level trigger + FK make an unaudited approval transition literally impossible to write, not just discouraged. |
| Evidence recorded as a re-runnable query (`source_query`) rather than what was actually observed | Section 4.2 — `source_query` dropped; replaced with an immutable `snapshot_data`/`snapshot_hash` pair captured at cite-time. |
| Agent output modeled as raw SQL text (`suggested_sql`) | Section 4.2 — replaced with typed `proposed_object` JSONB validated against a Pydantic schema before any write. |
| Three different approval-state shapes (`theses.origin`/`promoted_at`, `macro_theses.proposed_by`/`approval_state`, bolted-on `themes`/`theme_holdings.approval_state`) | Section 4.1/4.2 — one `governance_status` column, one 6-state enum, identical across all four governed tables. |
| `invalidation_conditions[].metric` as free-form `table`/`column` strings | Section 4.5 — replaced with a closed `invalidation_indicator_registry` lookup; conditions reference an `indicator_code`, never a raw table/column. |

---

## 3. Inspiration vs. evidence — mandatory framing rule [PLANNED, applies immediately]

Any plan, doc, or commit message that references an external fund/framework
(Bridgewater, Tudor, Lone Pine, Tiger Global, AQR, GMO, or any other) **must** use
exactly these three headings, in this order, none omitted:

```markdown
## Inspiration (unvalidated)
[Name the framework. State the one structural idea borrowed. No performance claim.
 Forbidden words: "proven", "validated", "shown to work", "demonstrates edge".]

## Implementation capability (built)
[What code/schema actually exists and runs. Cite the file path. No performance claim.]

## Validated edge (none yet — TBD)
[Default: "No backtested or live statistical evidence exists for this framework as of
 <date>. See docs/research/alpha-signal-verification.md for the only edge-validation
 work in this codebase — note Model A's own signal does not survive that bar (reverses
 sign 5d→21d)." Replace only with an actual study meeting the Section 4.6 bar.]
```

A plan draft naming a fund without all three headings present is incomplete — this
is how the prior document's inspiration-as-validation drift happened, and a forced
empty third section is harder to silently delete than a disclaimer sentence.

This document's own use of Bridgewater's four-quadrant framework (Section 5.1) follows
this structure.

---

## 4. Governance model

### 4.1 Thesis lifecycle [PLANNED]

Keep the existing `research → watching → active → exited/expired` **investment**
state machine as-is — `enter_thesis()` already hard-fails on missing `thesis_text`/
`stop_price`/`target_price`. This is orthogonal to, and must not be conflated with,
the new `governance_status` **provenance/approval** state machine defined in Section
4.2 — `status` answers "is capital deployed," `governance_status` answers "is this
content trustworthy enough to exist/be acted on." A thesis can be `status='research'`
AND `governance_status='approved'` simultaneously (an approved idea, no capital yet) —
that is the ordinary case for a human-authored thesis today.

**Evidence requirement per governance transition** (mechanics defined fully in 4.2):

| Transition | Requirement |
|---|---|
| Agent proposes a thesis (`draft`, agent-originated) | The structured proposal must carry ≥1 evidence citation with `tier != 'speculative'` — enforced before any row is written |
| `draft` → `evidence_complete` | Automatic — service layer checks ≥1 non-speculative `thesis_evidence` row exists; not a manual step |
| `evidence_complete` → `pending_review` | Automatic for agent-originated content (immediate) |
| `pending_review` → `approved` | Human runs `asx thesis approve <id> --reason "..."`; hard-fails on 100%-speculative evidence or any citation older than 14 days (override: `--accept-stale-evidence`) |
| `watching` → `active` (`enter_thesis`, investment lifecycle) | Existing hard-fails unchanged, **plus**: hard-fail unless `governance_status = 'approved'` |

Human-authored theses (the overwhelming common case) are created directly at
`governance_status='approved'` — DEFAULT preserves the existing single-shot CLI flow
with zero added friction. The draft→…→approved crawl is specifically the on-ramp for
agent-originated content; per the "keep new friction proportional" principle, a human
typing `asx thesis open` never touches this state machine.

**Review cadence:** keep the 30-day default for human theses. Agent-originated theses
get a **7-day** cadence while `governance_status` is anything but `approved` (an
unreviewed agent draft sitting a month is a bigger discipline risk than an unreviewed
human one), reverting to 30 days once approved. A conviction-weighted cadence is
**not** built now — flag as `m14_candidate_conviction_weighted_cadence` in
`portfolio-conventions.md`, matching this repo's existing pattern of deferring
uncalibrated heuristics (see `m14_candidate_beta_cap`).

**Retirement vs. invalidation — kept as two distinct concepts, not unified:**
`themes.retired_at` = "is this macro narrative still investable at all" (theme-level).
`theses.invalidation_conditions[].status` = "has a specific fact this position depends
on broken" (thesis-level). `governance_status='retired'` is a third, orthogonal
concept — "is this governance record itself archived" (e.g. an approved macro thesis
whose narrative has played out). Collapsing any of these would conflate different
blast radii. The only mechanical change needed is making invalidation conditions
*executable* (Section 4.5).

**Confidence — reuse `conviction_level`, do not add a second thesis-level field.**
`conviction_level` (1-5) is the human's conviction in the investment decision. The new
per-claim evidence tier (verified/inferred/speculative, Section 4.2) is a property of
an individual agent claim, not the thesis as a whole — different grain, kept separate.

**Data freshness:** a cited evidence row's `retrieved_at` older than **14 calendar
days** at the moment of `asx thesis approve` blocks the transition (hard-fail) unless
the human passes `--accept-stale-evidence "<reason>"`, itself logged as a
`governance_events` row. 14 days, not the thesis's 30-day revisit window, because
macro/theme conditions move faster than position-level review cadence.

### 4.2 AI agent governance [PLANNED]

This is the core mechanism Section 1.4's preconditions exist to protect, and the
layer Section 4.7 makes structurally unbypassable rather than a service-layer
convention alone.

**Evidence tier taxonomy** (aligns with the existing `[VERIFIED]/[INFERRED]/[MISSING]`
convention in `paper-portfolio-monitoring.md`, swapping `[MISSING]` for
`[SPECULATIVE]` since this is a different concept — agent judgment, not absent data):

- **`verified`** — the claim is the literal content of one DB row (or a direct
  aggregate over an explicit printed `WHERE` clause), zero agent interpretation.
  Test: could a human re-run the cited query and get the exact same fact restated?
- **`inferred`** — synthesis across ≥2 `verified` facts into a conclusion that isn't a
  single row anywhere. Test: would undoing the synthesis (looking at the cited facts
  individually) leave room for a different conclusion? If yes, it's inferred.
- **`speculative`** — asserted with no citable DB row behind it — general
  pattern-matching or extrapolation. `source_table`/`snapshot_data` are NULL by
  definition for this tier.

Every claim in an agent's "Findings" section must carry one of these three tags. No
untagged free text in findings (a closing Boundaries paragraph without tags is fine,
matching the 5 existing agents' style).

**Evidence schema — replayable, not just traceable.** The prior draft's
`source_query TEXT` recorded *how* evidence was obtained; queries, schemas, and data
all drift, so a stored query cannot reliably reproduce what was actually seen. Replace
it with an immutable snapshot of the observed values themselves:

```sql
CREATE TABLE thesis_evidence (
    evidence_id      BIGSERIAL    PRIMARY KEY,
    thesis_id        BIGINT       NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    cited_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_agent     TEXT         NOT NULL,  -- matches .claude/agents/<name>.md slug
    tier             TEXT         NOT NULL CHECK (tier IN ('verified','inferred','speculative')),
    claim_text       TEXT         NOT NULL CHECK (claim_text <> ''),
    source_type      TEXT         NOT NULL DEFAULT 'db_query' CHECK (source_type IN ('db_query','external_url')),
    source_table     TEXT,        -- locator only, NULL for speculative; not authoritative
    source_as_of     TIMESTAMPTZ, -- as_of/dt of the cited row, NOT cited_at
    retrieved_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_url       TEXT,        -- reserved for a future web-sourcing agent; unused today (no
                                   -- current agent has WebFetch/WebSearch) — costs nothing to reserve
    snapshot_data    JSONB,       -- the literal row(s) observed at cite-time; NULL only for speculative
    snapshot_hash    TEXT,        -- sha256(canonical_json(snapshot_data)), hex; tamper-evidence
    superseded_at    TIMESTAMPTZ, -- set when re-evaluated and replaced; NULL = live

    CONSTRAINT thesis_evidence_url_requires_external
        CHECK (source_url IS NULL OR source_type = 'external_url'),
    CONSTRAINT thesis_evidence_hash_format
        CHECK (snapshot_hash IS NULL OR snapshot_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT thesis_evidence_snapshot_required_unless_speculative
        CHECK (tier = 'speculative' OR snapshot_data IS NOT NULL)
);
CREATE INDEX idx_thesis_evidence_thesis ON thesis_evidence (thesis_id, cited_at DESC);

CREATE TABLE agent_evidence (
    -- Pre-thesis evidence: macro/theme research that precedes any theses row,
    -- or that informs multiple theses, or that's pure research with no position yet.
    -- Identical evidence-replayability shape to thesis_evidence, no thesis_id FK.
    evidence_id           BIGSERIAL    PRIMARY KEY,
    agent_name             TEXT         NOT NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    claim                   TEXT         NOT NULL CHECK (claim <> ''),
    tier                    TEXT         NOT NULL CHECK (tier IN ('verified','inferred','speculative')),
    source_type             TEXT         NOT NULL DEFAULT 'db_query' CHECK (source_type IN ('db_query','external_url')),
    source_table             TEXT,
    source_as_of              TIMESTAMPTZ,
    retrieved_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_url                  TEXT,
    snapshot_data                JSONB,
    snapshot_hash                 TEXT CHECK (snapshot_hash IS NULL OR snapshot_hash ~ '^[0-9a-f]{64}$'),
    related_symbol                 TEXT,
    related_theme_code               TEXT REFERENCES themes(theme_code),
    promoted_to_thesis_id              BIGINT REFERENCES theses(thesis_id),  -- the join seam
    status                               TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','promoted','dismissed')),
    CONSTRAINT agent_evidence_snapshot_required_unless_speculative
        CHECK (tier = 'speculative' OR snapshot_data IS NOT NULL)
);
```

`snapshot_data` is the literal asyncpg row(s) returned, serialised with the same
`_serialise()` convention `service.py` already uses for `Decimal`/`datetime` values
(`str()`, never `float()`) so the two serialisation contracts don't diverge.
`snapshot_hash = sha256(json.dumps(snapshot_data, sort_keys=True,
separators=(",",":"), default=str)).hexdigest()` — proves `snapshot_data` wasn't
edited after the fact; it does not (and cannot) prove the live table still matches,
which is a weaker, separate guarantee this design doesn't claim.

**Agent output — structured proposals, never raw SQL.** Storing agent-generated SQL
(even unexecuted) is itself a risk: it's an attractive artifact for future automation
or a rushed manual run to just paste and execute. Agents produce typed proposal
objects; the application layer validates and turns them into writes.

```sql
CREATE TABLE agent_runs (
    -- Every agent invocation, whether or not the human acts on it.
    run_id              BIGSERIAL    PRIMARY KEY,
    agent_name          TEXT         NOT NULL,
    invoked_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    subject              TEXT,            -- symbol, theme_code, or NULL for macro-economist
    summary              TEXT         NOT NULL,
    claim_count          INT          NOT NULL DEFAULT 0,
    verified_count       INT          NOT NULL DEFAULT 0,
    inferred_count       INT          NOT NULL DEFAULT 0,
    speculative_count    INT          NOT NULL DEFAULT 0,
    object_type           TEXT CHECK (object_type IN ('macro_thesis','theme','theme_holding','thesis')),
    proposed_object        JSONB,          -- typed by object_type; validated against a Pydantic
                                            -- model before use; NO SQL, no table/column names as data
    acted_on               BOOLEAN      NOT NULL DEFAULT FALSE,  -- flipped only by the approve/reject service fn
    resulting_object_id     BIGINT           -- the created row's PK, whichever table object_type names
);
```
Both `object_type`/`proposed_object` nullable together — an evidence-only run (e.g.
`market-context-narrator`) proposes nothing.

**Structured proposal shapes** (new `asxos/domain/theses/schemas.py`, Pydantic):
```python
class MacroThesisProposal(BaseModel):
    title: str = Field(min_length=1)
    thesis_text: str = Field(min_length=1)
    regime_quadrant: Literal["rising_growth_rising_inflation", "rising_growth_falling_inflation",
                              "falling_growth_rising_inflation", "falling_growth_falling_inflation"]
    horizon_months: int = Field(gt=0, le=36)
    catalyst: str = Field(min_length=1)
    falsifier: str = Field(min_length=1)
    data_signals: list[str] = Field(default_factory=list)
    evidence_citation_ids: list[int] = Field(min_length=1)  # agent_evidence.evidence_id FKs

class ThemeProposal(BaseModel):
    theme_code: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    conviction_band: Literal["low", "medium", "high"]
    stage: Literal["early","early-institutional","broad-institutional","mainstream","late-retail","mature"]
    macro_thesis_id: int | None = None
    evidence_citation_ids: list[int] = Field(min_length=1)

class ThemeHoldingProposal(BaseModel):
    theme_code: str
    symbol: str = Field(pattern=r"^[A-Z0-9]+\.(AU|US)$")
    exposure_strength: Decimal = Field(ge=0, le=1)
    direction: Literal["positive", "negative"]
    mechanism_text: str = Field(min_length=1)
    evidence_citation_ids: list[int] = Field(min_length=1)
```
No `ThesisProposal` type yet — no Phase 2 agent in this document produces a full
instrument thesis (entry band/stop/target/timeline); that capability belongs to a
future agentic thesis-drafter (Plan B historical notes, Section 8) and is explicitly
deferred (`m14_candidate_agentic_thesis_drafter`), not silently assumed.

Every `evidence_citation_ids` entry must reference an `agent_evidence`/`thesis_evidence`
row with `tier != 'speculative'` — validated by the service function before any write,
matching Section 4.1's evidence-requirement table.

`thesis_revisions` also gains provenance columns so it stays the single canonical
timeline for investment-lifecycle events (no UNION needed across tables to answer
"what happened to this thesis"):
```sql
ALTER TABLE thesis_revisions
    ADD COLUMN source TEXT NOT NULL DEFAULT 'human' CHECK (source IN ('human','agent')),
    ADD COLUMN agent_name TEXT,  -- NULL when source='human'
    ADD COLUMN evidence_confidence TEXT CHECK (evidence_confidence IN ('verified','inferred','speculative')),
    ADD COLUMN evidence_citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD CONSTRAINT thesis_revisions_agent_requires_confidence
        CHECK (source = 'human' OR evidence_confidence IS NOT NULL),
    ADD CONSTRAINT thesis_revisions_agent_requires_citation
        CHECK (source = 'human' OR jsonb_array_length(evidence_citations) > 0);
```

**Governance checkpoints — one human-facing action, matching the state machine in
4.1:** `asx thesis approve <id> --reason "..."` / `asx thesis reject <id> --reason
"..."` (new CLI commands, modeled on the existing `--reason`-required pattern) are the
only way `governance_status` reaches `approved`/`rejected` from `pending_review`. Draft
creation itself happens via `asx thesis open SYMBOL --from-agent-run <run_id>` (a new
flag on the existing command): validates `agent_runs.proposed_object` against the
matching Pydantic model, creates the row at `governance_status='draft'`, copies every
cited `verified`/`inferred` evidence row's reference into the object's evidence links,
and — because the evidence requirement is already satisfied by construction (the
proposal schema requires `evidence_citation_ids`) — the service layer immediately
advances `draft → evidence_complete → pending_review` in the same transaction,
recording each transition in `governance_events` (Section 4.7). **Speculative claims
are never copied as citations** — if the human wants one on record, they re-type it
via `revise_thesis` as human-authored `thesis_text`, never as a citable evidence row.
Sets `agent_runs.acted_on=TRUE`, `resulting_object_id`.

No allocator or screening-rule code reads `theses` filtered by `governance_status`
directly — `enter_thesis()`'s new guard (4.1) is the only enforcement point on the
capital-risk path, so this firewall costs **zero changes** to
`asxos/domain/portfolio/*`. Brief/`/pm-review` read surfaces use the gated views
defined in Section 4.7.

**Agent file requirements (for `macro-economist`, `theme-researcher`,
`instrument-selector` when built in Phase 2):** `tools:` frontmatter is `Read, Glob,
Grep, mcp__Supabase__execute_sql` — same read-only grant as the 5 existing agents.
Agents never write to the DB directly; the orchestrating main-loop session writes the
`agent_runs` row immediately after any of the three returns output (the same place
`/pm-review` already owns multi-agent fan-out, since "a subagent can't spawn
subagents" per CLAUDE.md).

### 4.3 Inspiration vs. evidence

Covered in Section 3 above — applies to this entire document, not a separate concern.

### 4.4 Signal contamination prevention [DONE — Phase 0/0.5, see Progress note at top]

**Step A — the read-side filter (shipped first, standalone):**

`asxos/domain/portfolio/build.py`, `asxos/brief/compose.py`, and (found during Phase
0.5's own security review) `asxos/domain/brief/collectors/active_theses.py` used to
query `signals`/`model_versions` with no `model` filter (or, in `active_theses.py`,
with a hardcoded unparameterized literal). Fixed — purely additive, no migration, no
behaviour change against current data (one model exists today).

**Step B — the durable structural gate (shipped second, applied to migration
`0032`):**
```sql
ALTER TABLE model_versions ADD COLUMN approved_for_allocation BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE model_versions SET approved_for_allocation = TRUE
    WHERE model = 'model_a' AND version = 'v1_5';  -- explicit one-time grandfather, not a default
```
All three call sites now discover the production model via the shared
`asxos/domain/models/production_gate.py::resolve_production_model()` helper:
```sql
SELECT model, version FROM model_versions WHERE is_active = TRUE AND approved_for_allocation = TRUE
```
hard-failing (`RuntimeError`) if this returns 0 rows (nothing approved) or >1 row
(multi-sleeve blending is out of v1 scope per `portfolio-conventions.md`). The *gate*,
not a hardcoded name, is load-bearing — a future engineer (or coding agent) cannot
accidentally leak an unapproved model by forgetting to add a filter, because there's no
string to forget; the shared helper is the one place the condition and error messages
live, so the three call sites can't drift apart on the invariant. A new model/sleeve
becomes eligible only via an explicit human-run `asx model approve <model> <version>`
— **this CLI command does not exist yet**; today the only way to flip the bit is a
direct migration/SQL statement via Supabase MCP, same as how migration 0032's
grandfather `UPDATE` was applied.

No `signals` schema change — its PK already scopes rows by model; the FK to
`model_versions` already guarantees referential integrity. `approved_for_allocation`
is a business-rule gate, deliberately a separate concern from that FK.

### 4.5 Executable thesis invalidation [PLANNED]

The prior free-form `metric: {"table": ..., "column": ...}` shape lets a typo or an
agent point at an arbitrary table, and the evaluation job would only discover this at
3am via string-interpolated SQL. Replace it with a closed registry — conditions
reference an `indicator_code`, never a raw table/column:

```sql
CREATE TABLE invalidation_indicator_registry (
    indicator_code       TEXT PRIMARY KEY,
    description            TEXT NOT NULL,
    source_table             TEXT NOT NULL CHECK (source_table IN ('fundamentals','prices','signals','theses')),
    source_column              TEXT NOT NULL,
    value_type                  TEXT NOT NULL CHECK (value_type IN ('numeric','date','text')),
    allowed_comparators           TEXT[] NOT NULL CHECK (allowed_comparators <@ ARRAY['<','<=','>','>=','=','!=']::TEXT[]),
    symbol_filter_required          BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO invalidation_indicator_registry VALUES
    ('nim', 'Net interest margin (bank fundamentals)', 'fundamentals', 'net_interest_margin', 'numeric', ARRAY['<','<=','>','>='], TRUE),
    ('price_vs_stop', 'Latest close vs the thesis stop_price', 'prices', 'close', 'numeric', ARRAY['<','<='], TRUE),
    ('signal_label', 'Latest model_a signal_label for the symbol', 'signals', 'signal_label', 'text', ARRAY['=','!='], TRUE),
    ('prob_up', 'Latest model_a prob_up for the symbol', 'signals', 'prob_up', 'numeric', ARRAY['<','<=','>','>='], TRUE);
```
`source_table`'s CHECK against a closed 4-table list is the actual injection stop —
even a malformed registry row can't reference an arbitrary table. Adding a 5th
queryable table requires a migration that extends the CHECK — friction that routes
schema evolution through review, not through an agent-written JSON blob.

`theses.invalidation_conditions[]` elements become:
```json
{
  "condition": "Net interest margin compresses below 1.8%",
  "metric": {"indicator_code": "nim", "symbol": "CBA.AU", "comparator": "<", "threshold": "1.8", "warning_band_pct": "5"},
  "cadence": "daily", "status": "active",
  "evaluated_at": "2026-06-29T20:55:00Z", "evaluated_value": "1.92", "note": null
}
```
`revise_thesis()`'s existing `invalidation_conditions` write path gains a validation
step: resolve `indicator_code` against the registry, check `comparator = ANY
(allowed_comparators)`, hard-fail otherwise — mirrors the `REVISABLE_FIELDS` allowlist
pattern exactly, just externalized to a DB table so new indicators are added via
migration+seed-row instead of a code change. `metric` stays **nullable** — a condition
can remain pure free text (`metric: null`), staying permanently manual exactly as
today; not every condition is mechanically checkable ("management credibility
deteriorates" has no DB column). The executable path is additive, never a replacement
requirement.

**Four-value status** (unchanged from prior draft): `active` → `warning` (within
`warning_band_pct` of threshold) → `triggered` (threshold crossed) → `resolved`
(human reviewed, deemed no longer live).

**New scheduled job** `asxos-evaluate-invalidations`, daily, **20:54 UTC Sun-Thu**
(after the 20:30-20:50 sync/snapshot/signals block, before `compose_brief` at 21:00).
Fits the existing `JobMonitor` pattern (`asxos/jobs/utils/job_monitor.py`). Builds its
query from a fixed template dict keyed by `source_table`, interpolating only
`source_column` — a value read from the registry (migration-controlled), never from
the JSONB condition or any agent/user input directly:
```python
_QUERY_TEMPLATES = {
    "fundamentals": "SELECT {col} FROM fundamentals WHERE symbol = $1 ORDER BY as_of DESC LIMIT 1",
    "prices":       "SELECT {col} FROM prices WHERE symbol = $1 ORDER BY dt DESC LIMIT 1",
    "signals":      "SELECT {col} FROM signals WHERE symbol = $1 AND model = 'model_a' ORDER BY as_of DESC LIMIT 1",
    "theses":       "SELECT {col} FROM theses WHERE thesis_id = $1",
}
```
Hard-fails (per non-negotiable #10) if a condition's `indicator_code` isn't in the
registry (a data-integrity bug, not transient). Treats a missing/stale referenced row
as hard-fail only if `cadence='daily'` and the most recent available row is >5 trading
days stale (mirrors the existing signals staleness threshold philosophy). `metric:
null` conditions are skipped, not failed — documented correct behaviour.

**On breach: surfaces in the brief, never auto-exits.** The job flips
`invalidation_conditions[].status` to `triggered` and writes a `thesis_revisions` row
(`revision_type='assumption_change'`, auto-generated reasoning citing the indicator/
value/threshold) — a fact-recording write, not a capital action. The brief gains an
"INVALIDATION TRIGGERED (n)" / "INVALIDATION WARNING (n)" subsection. A human decides
the next step via the existing `revise_thesis`/`exit_thesis` commands. Auto-exiting
capital on a mechanical breach would be exactly the irreversible automated capital
action this codebase already keeps human-gated elsewhere (the personal-advice
firewall, `ASXOS_PORTFOLIO_BRIEF_ENABLED` staying `0` through the paper-trade period).

### 4.6 Validation tiers — what paper trading can and cannot prove [PLANNED — vocabulary, applies immediately to any future paper-trade write-up]

| Tier | Proves | Can a 4-week paper-trade window prove it? |
|---|---|---|
| Infrastructure | Pipeline runs end-to-end without crashing | **Yes** — the one tier a short window is sufficient for |
| Operational | A human can act on the output day-to-day | Partially — finds obvious UX friction, not stress-condition survival |
| Execution | Allocations/orders are computed *correctly* from inputs | No — this is a code-correctness property, proven by tests (`portfolio-invariant-guard`, `tax-spec-conformance`), not by watching live output |
| Investment | Recommendations are *sound* given what's known | Partially — enough cycles to judge process quality, not outcome quality (4 weeks of outcomes is noise-dominated) |
| Alpha | Statistically demonstrated, durable predictive edge | **No, categorically not** — ~20 trading days collapses to ~1-2 independent market episodes once overlap is accounted for |

**Concrete proof, not abstraction:** Model A's own IC is +0.095 (5d) reversing to
−0.060 (21d) — the same signal, same model, same universe, flips sign purely by
measurement window. A 5-day paper window would show the positive regime; a 21-day
window would show the reversal. **Neither conclusion is correct** — neither window has
enough independent samples to distinguish skill from noise.

**The actual bar for claiming alpha** (matching `alpha-signal-verification.md` §8, not
inventing a new one): ≥50–100 independent non-overlapping-window market dates,
IC-by-horizon with an effective-N guard, decile-spread and liquidity decomposition,
robustness to an alternate return-definition. Until met, any write-up must say
**"never alpha proof"** (the phrase already used in `paper-portfolio-monitoring.md`)
and specify which of the five tiers above it actually demonstrated.

### 4.7 Bypass prevention [PLANNED — explicit design principle, not an implementation convention]

This system has one operator and no auth layer — "governance" here is not access
control, it is **making an ungoverned write structurally impossible to produce**, so
that a script, a migration, a maintenance utility, or a future Claude Code session
with less context than this one cannot accidentally put agent-drafted or unreviewed
content into a production-facing path.

Three independent layers, each closing a different bypass route:

1. **Provenance cannot be faked.** `theses`, `macro_theses`, `themes`, and
   `theme_holdings` each carry a nullable `source_run_id BIGINT REFERENCES
   agent_runs(run_id)`. Any row claiming agent origin references a real, already-logged
   invocation — there is no way to insert a row that *looks* agent-drafted without the
   audit trail that produced it actually existing first (a dangling reference is a
   plain FK violation).

2. **Approval cannot be shortcut.** A single `governance_status TEXT CHECK (...
   IN ('draft','evidence_complete','pending_review','approved','rejected','retired'))`
   column, identical in name and enum across all four tables, replaces the three
   inconsistent shapes the prior draft used (`origin`/`promoted_at` on `theses`,
   `proposed_by`/`approval_state` on `macro_theses`, a bolted-on `approval_state` on
   `themes`/`theme_holdings`). A shared audit table records every transition:
   ```sql
   CREATE TABLE governance_events (
       event_id     BIGSERIAL PRIMARY KEY,
       object_type  TEXT NOT NULL CHECK (object_type IN ('thesis','macro_thesis','theme','theme_holding')),
       object_id    BIGINT NOT NULL,  -- theses.thesis_id / macro_theses.macro_thesis_id /
                                       -- themes.theme_id / theme_holdings.holding_id (new surrogate, below)
       from_status  TEXT NOT NULL CHECK (from_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
       to_status    TEXT NOT NULL CHECK (to_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
       event_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       reasoning    TEXT NOT NULL CHECK (reasoning <> ''),
       actor        TEXT NOT NULL DEFAULT 'human' CHECK (actor IN ('human','agent')),
       -- Ties this row to the exact transaction that wrote it. Checked by the
       -- trigger below via pg_current_xact_id() equality, not a time window
       -- (see the trigger's own note for why a window is insufficient).
       xact_id      BIGINT NOT NULL DEFAULT pg_current_xact_id()::text::bigint
   );
   CREATE INDEX idx_governance_events_object ON governance_events (object_type, object_id, event_at DESC);
   CREATE INDEX idx_governance_events_xact ON governance_events (object_type, object_id, to_status, xact_id);
   ```
   `theme_holdings`' natural key is composite (`theme_id, symbol`) — it gains a
   surrogate `ADD COLUMN holding_id BIGSERIAL UNIQUE` purely so `governance_events`
   can reference one BIGINT identity uniformly across all four tables, without
   changing its existing PK or any existing query.

   **[CORRECTED during Phase 1 implementation — this block originally specified a
   single shared function across all 4 tables, dispatched via `TG_ARGV[0]` with a
   `CASE` over `NEW.thesis_id`/`NEW.macro_thesis_id`/etc. That fails at runtime with
   "record NEW has no field macro_thesis_id": PL/pgSQL validates `NEW`/`OLD` field
   references against the table the trigger is bound to for EVERY `CASE` branch, not
   just the one that executes — a function bound to `theses` cannot reference
   `NEW.theme_id` even in a branch that never runs. Confirmed by hitting this exact
   error live against Supabase. The corrected, applied version below is
   `theses`-specific — no `TG_ARGV`, no cross-table `CASE`. It also replaces the
   original 5-second `event_at` time-window check with `pg_current_xact_id()`
   equality: a time window has a real bypass gap (a legitimate `governance_events`
   row from an earlier, unrelated transaction within the window would satisfy the
   check for a completely different, unaudited UPDATE on the same object), whereas
   the transaction ID is exact. Phase 2 must write its own per-table function(s) for
   `macro_theses`/`themes`/`theme_holdings` — do not assume this one generalizes;
   see `migrations/0034_governance_audit_trigger_and_revision_provenance.sql`'s
   header comment for the full account.]**

   **[THIRD fix, found by a security review pass after Phase 1 first shipped: the
   `EXISTS` check below originally validated `object_id`/`to_status`/`xact_id` but
   never validated `from_status` against `OLD.governance_status`. A transaction that
   hand-authored a `governance_events` row with a fabricated `from_status` (not
   matching the row's real prior state), followed by the matching `UPDATE`, would
   satisfy the trigger — narrower than a full bypass (still requires hand-authoring
   both statements, deliberately going around `service.py`) but wider than this
   section previously disclosed. `approve_object()`/`reject_object()` were never
   affected (both read `from_status` under `SELECT ... FOR UPDATE` in the same
   transaction, so it's always accurate) — the fix hardens the trigger itself rather
   than relying on callers being well-behaved. Fixed and re-verified live against
   prod (reject unaudited UPDATE; accept correctly-audited UPDATE; reject a
   from_status-spoofed UPDATE) — the code block below reflects the applied fix.]**
   ```sql
   CREATE OR REPLACE FUNCTION _check_theses_governance_audit() RETURNS TRIGGER AS $$
   BEGIN
       IF NEW.governance_status = OLD.governance_status THEN
           RETURN NEW;
       END IF;
       IF NOT EXISTS (
           SELECT 1 FROM governance_events
           WHERE object_type = 'thesis' AND object_id = NEW.thesis_id
             AND from_status = OLD.governance_status
             AND to_status = NEW.governance_status
             AND xact_id = pg_current_xact_id()::text::bigint
       ) THEN
           RAISE EXCEPTION 'governance_status transition from % to % on thesis % '
               'requires a matching governance_events row (same from_status, '
               'to_status) written in the SAME transaction (xact %) -- '
               'use the service-layer approve_object()/reject_object()/draft-creation '
               'functions, not a direct UPDATE.',
               OLD.governance_status, NEW.governance_status, NEW.thesis_id, pg_current_xact_id();
       END IF;
       RETURN NEW;
   END; $$ LANGUAGE plpgsql;

   CREATE TRIGGER theses_governance_audit BEFORE UPDATE OF governance_status ON theses
       FOR EACH ROW EXECUTE FUNCTION _check_theses_governance_audit();
   -- Phase 2: write a properly-tested per-table function (or a dynamic/JSON-
   -- extraction version, validated against real multi-table shapes) when
   -- macro_theses/themes/theme_holdings exist to govern.
   ```
   A migration that does `UPDATE theses SET governance_status = 'approved'` without
   also inserting the matching `governance_events` row in the same transaction simply
   fails. This closes the exact scenario named by review: a direct SQL update, a
   one-off script, or a future AI session trying to shortcut the review step.

3. **Capital cannot be deployed on unapproved content.** `enter_thesis()` — the single
   function that turns a thesis into a live position — hard-fails unless
   `governance_status = 'approved'` (Section 4.1). Every other write path can freely
   produce `draft`/`pending_review` rows; only this one gate matters for capital risk,
   and it is one `if` statement anchored to a DB-enforced column, not a scattered set
   of per-table checks.

**What this deliberately does not attempt:** Postgres role separation (`REVOKE`/
`GRANT`, RLS). A single-role, no-auth, free-tier Supabase project has exactly one
credential in practice (`DATABASE_URL`, shared across every Render job and every
migration — confirmed 29 references in `render.yaml`), and role-based bypass
prevention protects against an untrusted co-tenant this system doesn't have. The FK
and trigger above protect against the actual risk — a trusted actor (human or agent)
taking a shortcut under time pressure — in a way a same-credential actor cannot opt
out of without a deliberate, reviewable schema change.

**Honest limit:** none of this stops a migration that explicitly drops the constraint
or trigger first. That is by design — schema changes already go through deliberate
review (`make check-drift`, sequential migration files, this document). The goal is
to make the *accidental*, *time-pressured*, or *context-poor* bypass impossible, not
to defend against a deliberate decision to remove the governance layer itself.

### 4.8 Testing progression [PLANNED — applies to Phase 2 and any future agent-driven write path]

Before a discovery agent's output ever reaches a human's live Supabase data, it goes
through six ordered stages — no stage may be skipped, and each is a stronger claim
than the last:

1. **Fixture-based testing** — the Pydantic proposal models (4.2) and the service
   functions that consume them (`open_thesis(..., from_agent_run=...)`,
   `approve_object`/`reject_object`) are tested against synthetic in-memory fixtures,
   no DB, no live agent. Proves the *mechanism* is correct.
2. **Synthetic end-to-end proposal generation** — a scripted (non-agent) proposal
   object is pushed through the full pipeline against a real (test/local) DB: draft →
   evidence_complete → pending_review → approve → `enter_thesis()`. Proves the *state
   machine* is correct end-to-end, still without any live agent or live market data.
3. **Read-only production validation** — each discovery agent's actual SQL is
   dry-run against live Supabase via `mcp__Supabase__execute_sql` (read-only) to
   confirm zero column/schema errors, *before* the agent is ever invoked for real.
   Proves the *queries* are correct against production schema.
4. **Human review** — the agent is invoked for real, produces a proposal, and a human
   reads the evidence citations and reasoning before approving. Proves the *content*
   is sound enough for one experienced reviewer to sign off.
5. **Approval** — the `governance_status → approved` transition itself, gated by
   Section 4.7's trigger. Proves the *governance record* is complete and audited.
6. **Paper trading** — only after 1-5 above, and only claiming what Section 4.6's
   tier table says it can claim (never alpha proof from a short window).

Phase 2 (Section 7) is not "done" until stages 1-3 pass for every discovery agent;
stages 4-6 are ongoing operational practice, not one-time implementation gates.

---

## 5. Discovery agents — Layer 1/2/3 of the top-down process [PLANNED — Phase 2, blocked on Phase 1]

### 5.1 Inspiration (unvalidated)

Bridgewater's four-quadrant framework: cross plotting growth direction × inflation
direction into 4 regimes, each favouring different asset classes. This is the
structural idea Section 5.5's `macro_theses.regime_quadrant` borrows.

### 5.2 Implementation capability (built)

Nothing yet for this section — Phase 2 (Section 7) builds the three discovery agents.
What already exists and will be reused: `market_context_current` (regime snapshot),
the FRED + EODHD clients, the `themes`/`theme_holdings` schema, the 5 live
investment-analysis agents as a style template.

### 5.3 Validated edge (none yet — TBD)

No backtested or live statistical evidence exists for the four-quadrant framework as
applied in this codebase. See Section 4.6 for the validation-tier vocabulary any future
claim here must use.

### 5.4 The three discovery agents (built in Phase 2, governed per Section 4.2)

**`macro-economist`** — reads `market_context_current` + `macro_theses` +
`regulatory_events`, synthesizes a regime quadrant + 3-5 macro theses, each claim
tagged verified/inferred/speculative with a replayable evidence snapshot (4.2).
Produces `MacroThesisProposal` objects — never SQL, never a direct write.

**`theme-researcher`** — given a macro thesis, identifies ASX-investable themes with
catalyst/falsifier, ranked by catalyst clarity, falsifiability, instrument
availability. Produces `ThemeProposal` objects.

**`instrument-selector`** — given a theme, finds 3-5 ASX instruments (stocks + ETFs)
by theme purity, operating leverage, balance-sheet quality, liquidity. Produces
`ThemeHoldingProposal` objects (`source='llm_inferred'` on the resulting row — the
first real use of this existing-but-unused enum value).

All three: advisory, read-only, `Read, Glob, Grep, mcp__Supabase__execute_sql` tools
only, never write directly, every claim evidence-tagged per Section 4.2, every
invocation logged to `agent_runs` by the orchestrating session, every proposal run
through the Section 4.8 testing progression before being trusted.

### 5.5 `macro_theses` schema (gated from day one — not exempted)

```sql
CREATE TABLE macro_theses (
    macro_thesis_id      BIGSERIAL    PRIMARY KEY,
    title                 TEXT         NOT NULL,
    thesis_text           TEXT         NOT NULL CHECK (thesis_text <> ''),
    regime_quadrant        TEXT         NOT NULL CHECK (regime_quadrant IN (
                              'rising_growth_rising_inflation', 'rising_growth_falling_inflation',
                              'falling_growth_rising_inflation', 'falling_growth_falling_inflation')),
    horizon_months         SMALLINT     CHECK (horizon_months BETWEEN 1 AND 36),
    catalyst                TEXT         NOT NULL,
    falsifier                TEXT         NOT NULL,
    data_signals             JSONB        NOT NULL DEFAULT '[]',
    source_run_id             BIGINT       REFERENCES agent_runs(run_id),  -- NULL = human-authored
    governance_status          TEXT         NOT NULL DEFAULT 'draft'
                                   CHECK (governance_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
                                -- DEFAULT 'draft' (unlike theses' DEFAULT 'approved') because this
                                -- table is new/empty — its primary output surface is the
                                -- macro-economist agent, so agent-drafted is the expected norm.
    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    retired_at                 DATE
);
CREATE INDEX idx_macro_theses_active ON macro_theses (created_at DESC) WHERE retired_at IS NULL AND governance_status = 'approved';
CREATE TRIGGER macro_theses_governance_audit BEFORE UPDATE OF governance_status ON macro_theses
    FOR EACH ROW EXECUTE FUNCTION _check_governance_audit('macro_thesis');
```
Gated identically to `theses`/`themes` (Section 4.1/4.2/4.7), **not exempted as
"purely human-curated"** — the prior revert happened precisely because the original
`macro_theses` shipped with no governance layer. The evidence-citation record
(`evidence_citation_ids` on the `MacroThesisProposal`) lives in `agent_evidence`, not
duplicated onto this table — `source_run_id` is the join back to `agent_runs`, which
in turn links to the evidence used.

`ALTER TABLE themes ADD COLUMN macro_thesis_id BIGINT REFERENCES macro_theses(macro_thesis_id) ON DELETE SET NULL;`
links themes to their governing macro thesis. `themes`/`theme_holdings` gain the same
`governance_status`/`source_run_id` pair (DEFAULT `'approved'`/NULL for existing
human-authored rows — grandfathered, exactly as `theses`, except `theme_holdings`'
existing `source='system_default'` placeholder rows, which are backfilled to
`governance_status='draft'` specifically, since they are structural placeholders
inserted inline by `open_thesis()`, not reviewed content, and should not masquerade as
approved exposure).

A gated view is the read surface for the brief, `/pm-review`, and any future allocator
code:
```sql
CREATE VIEW active_theses AS
    SELECT * FROM theses WHERE governance_status = 'approved' AND status NOT IN ('expired');
-- + active_themes, active_theme_holdings, analogous WHERE governance_status = 'approved'
```
`WHERE governance_status='approved'` baked into the view rather than relying on every
call site remembering the filter — the same "gate via a structurally-hard-to-bypass
predicate" pattern as Section 4.4's `approved_for_allocation`.

**Naming note:** `asxos/domain/brief/collectors/active_theses.py` (the Phase-0.5-fixed
collector module) is an unrelated pre-existing name — a future `active_theses` SQL
VIEW here would collide lexically only in prose, not in code (Python module vs. SQL
view are different namespaces), but pick a distinct view name (e.g.
`governed_active_theses`) if this reads confusingly when Phase 2 actually implements it.

---

## 6. `/pm-review` integration [PLANNED — Phase 4]

Once Phase 2 ships, add `macro-economist` and `theme-researcher` to the existing
5-agent fan-out (5→7), scoped to read-only "does the macro/theme context support this
position" questions — they do not gain write access in this context either. Update the
verdict template to include a MACRO line. If neither `macro_theses` nor any linked
theme exists yet for a symbol, the synthesis notes "macro layer not yet populated"
rather than forcing a verdict on an evidence gap.

---

## 7. Implementation phases — strict order, explicit dependencies, completion criteria

**Phase 0 — Contamination-isolation Step A [DONE].** `build.py`/`compose.py`/
`active_theses.py` filter every `signals`/`model_versions` query by the resolved
production model; existing test suite green; no behaviour change observable (one
model existed at the time).

**Phase 0.5 — Contamination-isolation Step B [DONE].** `model_versions.
approved_for_allocation` exists (migration 0032), `model_a/v1_5` is explicitly
grandfathered, all three call sites query through the shared
`production_gate.py::resolve_production_model()` gate and hard-fail on 0 or >1
eligible rows.

**Phase 1 — Governance schema [PLANNED].** (Sections 4.1, 4.2, 4.7). Depends on
nothing structurally, but **blocks Phase 2 absolutely** — no discovery agent may be
built before this ships.
Migrations: `theses.governance_status`/`source_run_id` (replacing no prior columns —
this is the first governance column on `theses`), `thesis_evidence`, `agent_evidence`,
`agent_runs` (with `object_type`/`proposed_object`), `governance_events`,
the shared audit trigger function + trigger on `theses`, `thesis_revisions` provenance
columns. New Pydantic schemas (`asxos/domain/theses/schemas.py`):
`MacroThesisProposal`, `ThemeProposal`, `ThemeHoldingProposal`. New service functions
in `asxos/domain/theses/service.py`: the `--from-agent-run` draft-creation path,
`approve_object()`, `reject_object()`. New CLI: `asx thesis open --from-agent-run`,
`asx thesis approve`, `asx thesis reject`. `enter_thesis()` gains the
`governance_status = 'approved'` guard.
*Done when:* Section 4.8 stages 1-2 pass — a synthetic agent-originated thesis can be
proposed, auto-advanced through evidence_complete/pending_review, approved, and
entered end-to-end via fixture and synthetic-DB tests; a thesis with only speculative
evidence is rejected before `pending_review` is ever reached; a direct `UPDATE
theses SET governance_status='approved'` with no matching `governance_events` row
fails against the trigger; `make check` green.

**Phase 2 — Discovery agents [PLANNED].** (Section 5). Depends on Phase 1.
Builds `macro-economist`, `theme-researcher`, `instrument-selector` agent files,
the `macro_theses` table + `themes.macro_thesis_id` FK, `themes`/`theme_holdings`
`governance_status`/`source_run_id` columns + their audit triggers, the
`theme_holdings.holding_id` surrogate key, the gated views (Section 5.5).
*Done when:* Section 4.8 stages 1-3 pass for every discovery agent (fixture tests,
synthetic end-to-end, and a clean read-only dry-run of each agent's SQL via Supabase
MCP); a full macro→theme→instrument→`asx thesis open --from-agent-run`→`asx thesis
approve` cycle completes manually against live data with real, replayable evidence
snapshots (stage 4-5 of 4.8, the first live-operational run).

**Phase 3 — Executable invalidation [PLANNED].** (Section 4.5). Depends on Phase 1
(reuses the `thesis_revisions` provenance shape for auto-generated breach records) and
introduces `invalidation_indicator_registry`, which Phase 2's agents may also
reference — land Phase 3's registry table before or alongside Phase 2 if any
discovery-agent proposal needs to cite an indicator by code; otherwise Phase 3 is
independent of Phase 2.
*Done when:* `asxos-evaluate-invalidations` cron exists in `render.yaml` (disabled
until tested), a synthetic condition referencing a seeded `indicator_code` correctly
transitions active→warning→triggered against test fixtures, hard-fails on an
`indicator_code` not present in the registry.

**Phase 4 — `/pm-review` integration [PLANNED].** (Section 6) + brief invalidation
subsection. Depends on Phase 2 (pm-review) and Phase 3 (brief subsection)
respectively — these can ship as two independent commits once their dependencies are
met.

**Sequencing note:** Phase 1 is the hard gate for any agent-sourced content; do not
skip or weaken it under time pressure, since skipping it reproduces the exact failure
mode that caused the prior revert. Within Phase 1, the audit trigger (4.7) is not
optional scope-cutting — without it, `governance_status='approved'` reverts to a
service-layer convention only, which is precisely what Section 4.7 exists to rule out.

---

## 8. [FUTURE] Plan B — Multi-sleeve global architecture

Unchanged in substance from the prior draft's "MULTI-SLEEVE GLOBAL ARCHITECTURE"
section, with corrections from Section 1.1/2 above: `sleeves.py` must be built from
scratch (confirmed absent), and this plan shares the Phase 0/0.5 contamination
-isolation precondition with Plan A — **that precondition is now done**, so Plan B is
unblocked on that front, though nothing in Plan B has started. Full B1-B11 blocker
detail, FC1-FC6 financial-coherence findings, and the phased Step 1.1-1.7 sequence are
tracked in `docs/next-session-backlog.md`'s "Not started" list, not reproduced here to
keep this document scannable. Any future Plan B write-up that references external
funds/frameworks (AQR for the factor sleeve, GMO for value) must follow Section 3's
three-heading inspiration/capability/validated-edge structure, exactly as this
document does for Plan A.

---

## 9. Verification (end-to-end)

1. `make check` (ruff + mypy + pytest) green after every phase; known sandbox
   collection-error gaps (joblib/lightgbm) excluded per CLAUDE.md.
2. **Phase 0/0.5 — verified done.** `model_versions.approved_for_allocation` exists
   and exactly one row (`model_a`/`v1_5`) is TRUE; `build.py`/`compose.py`/
   `active_theses.py` hard-fail when tested against a synthetic second
   `model_versions` row (0-row and >1-row cases both covered by dedicated tests in
   `tests/test_portfolio_build.py`, `tests/test_brief_compose.py`,
   `tests/test_active_theses_signals.py`).
3. Phase 1: a synthetic agent-originated thesis proposal with only `speculative`
   evidence is rejected before reaching `pending_review`; one with `verified` evidence
   advances to `approved` via `asx thesis approve` and `enter_thesis()` accepts it; a
   direct `UPDATE ... SET governance_status='approved'` with no `governance_events` row
   fails against the trigger (Section 4.7) — test this explicitly, it's the load-bearing
   guarantee of the whole governance layer.
4. Phase 2: dry-run every discovery agent's SQL via `mcp__Supabase__execute_sql`
   (zero column errors) before first live invocation; confirm each agent's output
   deserialises cleanly into its Pydantic proposal model with no raw SQL anywhere in
   `agent_runs.proposed_object`.
5. Phase 3: a fixture thesis with an `indicator_code`-bearing condition correctly
   transitions status under the evaluation job; an unregistered `indicator_code`
   hard-fails; the brief's new subsection renders only on breach.
6. Any future paper-trade write-up explicitly states which Section 4.6 tier(s) it
   demonstrates, and which Section 4.8 testing-progression stage it represents —
   reviewed by `tax-spec-conformance`/`portfolio-invariant-guard`-style scrutiny
   before being shared as a status update.
