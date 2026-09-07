# asxos — next-session backlog (updated 2026-07-04)

**Status:** current (top half) / partially stale (the 2026-06-28 half — see inline banners)
**Scope:** backlog
**Last verified:** 2026-07-04
**Read priority:** read after the current session-handoff
**Superseded by:** `docs/product/roadmap-state.md` (2026-08-10 programme reframe) — **REFERENCE ONLY.**

> ⚠️ **NOT A QUEUE (2026-08-10).** The single live queue is the Stages 0→6 table in
> `docs/product/roadmap-state.md`. This file keeps itemised detail that the queue does not carry,
> but it may not be read as a next-action list.

---

## Follow-ups logged 2026-07-13 (/arbi wake — monitoring-lane fixes, PR #30)

- **`wealth_state` staleness transparency** (security-engineer Low, PR #30 review). The
  brief's wealth line now reads the latest snapshot on/before the brief date
  (`as_of <= $1 ... LIMIT 1`, `asxos/domain/brief/collectors/wealth_state.py`) — a
  correctness fix, but it carries no snapshot `as_of` or staleness marker, so a stalled
  `snapshot_portfolio` could silently render an old figure as current. Mitigated (a
  stalled job is deadman-alerted, and the complete-day anchor stops a *succeeding* job
  from writing stale-plausible data), so it is a hardening, not a blocker. Follow-up:
  surface the snapshot `as_of` in the wealth line, or mark the section `degraded` when
  `(brief_date − snapshot.as_of)` exceeds a small bound (`asxos/domain/prices/coverage.py::is_stale`
  already exists). Owner: `backend-architect` scope → main loop.

---

## P(-1) — ~~STOP~~ RESOLVED 2026-07-11 (this section is now historical)

> **UPDATE 2026-07-11 — the dispute below is RESOLVED, against Model A.** The decay check ran
> on 19,032 matured `signal_outcomes`: `corr(ml_prob, 21d) = −0.03`, STRONG_BUY 21d −0.09% vs
> HOLD +5.07% (conviction inverted) — **no usable edge**. James **shelved** the ML engine; the
> product is the model-independent moat. Rule #11 is now **standing policy**. See
> `docs/model-a-decay-analysis-2026-07-11.md` + `docs/product/ml-engine-shelf-2026-07-11.md`.
> This P(-1) no longer gates the file — the text below is the 2026-07-04 framing, kept for
> history.

Model A's signal reliability is disputed and unverified (user claim, 2026-07-04:
signal quality collapses within 5 days, reverses by day 21 — a potential
horizon mismatch against this system's multi-month thesis holding periods).
This gates everything else in this file, including the P0 item immediately
below: there is limited point extending the discovery/governance layer if the
model it discovers from can't support the position-holding periods the whole
system assumes. Resolve this first. Full context, what's known, and the
exact next-session action list are in the handoff doc, not repeated here.

---

## P0 — HIGHEST PRIORITY: Governance-first investment process architecture (2026-06-30)

Full design in `docs/proposals/governance-first-architecture-2026-06-30.md` (committed
to the repo — "asxos Investment Process — Governance-First Architecture"). This
supersedes the earlier "Multi-sleeve global architecture" backlog entry that
previously occupied this section: that design went through two rounds of external
architecture review, which found the original combined document unsafe to hand to an
implementation agent (mixed current/proposed/historical state, direct contradictions,
no governance layer for AI-agent-generated investment content) and then found the
first revision's governance layer itself bypassable (service-layer-only enforcement,
non-replayable evidence, raw SQL as an agent artifact, inconsistent approval-state
shapes, free-form JSON invalidation rules). The doc is now a single authoritative,
hardened document — read it in full before continuing this work; do not trust this
summary for anything beyond "what's done" below. (It was authored in a Claude Code
plan-mode session and originally lived only at `~/.claude/plans/` — deliberately
copied into `docs/proposals/` because that path is outside the repo and does not
survive the remote environment's container being reclaimed.)

**Both the discovery-agent process (macro → theme → instrument, "Plan A") and the
multi-sleeve construction layer (thesis/factor/momentum sleeves, "Plan B") live in
that one document now**, with an explicit section on how they coexist (Plan A feeds
discovery, Plan B feeds capital allocation) and a shared precondition (the
contamination-isolation gate below) that both must wait on.

### Done (this session)

- **Phase 0** — `build.py`/`compose.py`/`active_theses.py` signal/model_versions
  queries filtered by model (previously unfiltered, or in `active_theses.py`'s case
  an unparameterized hardcoded literal — a latent bug independent of any new feature,
  and a gap found during Phase 0.5's own security review).
- **Phase 0.5** — `model_versions.approved_for_allocation` gate (migration `0032`,
  applied to prod Supabase; `model_a/v1_5` explicitly grandfathered). All three call
  sites now discover the production model via the shared
  `asxos/domain/models/production_gate.py::resolve_production_model()` helper
  (`WHERE is_active = TRUE AND approved_for_allocation = TRUE`), hard-failing on 0 or
  >1 eligible rows — no model can reach the allocator, the brief, or a thesis card's
  ML driver line without an explicit human approval action. `REQUIRED_MIGRATIONS`
  bumped 85→86. Reviewed by security-engineer, refactoring-expert, technical-writer.
- **Phase 1** — Governance schema: `theses.governance_status`/`source_run_id`
  (migration 0033), `thesis_evidence`/`agent_evidence`/`agent_runs`/`governance_events`
  tables (migration 0033), `thesis_revisions` provenance columns + the
  `theses_governance_audit` trigger (migration 0034 — this codebase's first Postgres
  trigger). New: `asxos/domain/theses/schemas.py` (3 Pydantic proposal models),
  `service.py::create_thesis_from_agent_run()`/`approve_object()`/`reject_object()`,
  `enter_thesis()`'s governance guard, `asx thesis approve|reject` + `open
  --from-agent-run`. `REQUIRED_MIGRATIONS` bumped 86→88. Two judgment calls resolved
  (see the design doc's Progress note): `create_thesis_from_agent_run()` ships as a
  documented, tested stub (no `ThesisProposal` schema exists yet — that's a Phase 2
  gap, `m14_candidate_agentic_thesis_drafter`); `--accept-stale-evidence` overrides
  staleness only, never the zero-evidence check. One design-doc bug found and fixed
  during implementation: the planned single shared trigger function across all 4
  governed tables fails at runtime (PL/pgSQL validates `NEW`/`OLD` field references
  against the trigger's bound table even in unreached `CASE` branches) — replaced with
  a `theses`-specific function; Phase 2 needs its own function(s) for
  `macro_theses`/`themes`/`theme_holdings`, not a naive extension of this one. A
  second bug — found by the post-implementation security review pass — was that the
  trigger's `EXISTS` check never validated `from_status` against
  `OLD.governance_status`, letting a hand-authored (service-layer-bypassing)
  transaction claim an arbitrary prior state; fixed by adding `AND from_status =
  OLD.governance_status`, re-applied to prod, and re-verified with a new adversarial
  check.
- **Phase 2a+2b** — `macro_theses` table + governance columns on `themes`/
  `theme_holdings` (migration 0035: `macro_theses`, `themes.macro_thesis_id`,
  `theme_holdings.holding_id` surrogate, 4 `governed_active_*` views), 3 more
  independent per-table audit triggers (migration 0036 — `macro_theses`/`themes`/
  `theme_holdings`, each modeled on the corrected `theses` trigger, `from_status`
  check included from day one). `REQUIRED_MIGRATIONS` bumped 88→90. New: shared
  `asxos/domain/governance/` package (`transitions.py`'s `apply_governance_transition()`,
  extracted from `theses/service.py` once a 4th call site needed the identical
  `governance_events`-INSERT-then-UPDATE shape; `agent_run_service.py`'s `log_agent_run()`
  — the write side of `agent_runs`/`agent_evidence` Phase 1 never built), a new
  `asxos/domain/macro_theses/` package (own package, not folded into `themes/` — see
  `portfolio-conventions.md`'s module-boundary note), `themes/service.py`'s
  `approve_theme`/`reject_theme`/`approve_theme_holding`/`reject_theme_holding`. New
  CLI: `asx agent-run log`, `asx macro-thesis list|show|open --from-agent-run|approve|reject`.
  New agent: `.claude/agents/macro-economist.md` (the first "discovery" agent —
  proposes content rather than analyzing holdings) + `/discover-macro` slash command.
  Section 5.5 of the design doc had the same shared-trigger-function bug Section 4.7
  already fixed once (`_check_governance_audit('macro_thesis')` via `TG_ARGV`) —
  corrected to match migration 0036, not copied verbatim. One deferral:
  `m14_candidate_macro_thesis_evidence_staleness_check` (no direct `agent_evidence`
  FK on `macro_theses`, unlike `theses`' `thesis_evidence` FK — land when Phase 2c's
  second evidence-heavy agent makes the join-based check worth generalising).
  **Third bug of the governance build, found by Phase 2a's live verification and
  the most serious**: `apply_governance_transition()` (and Phase 1's shipped
  inline ancestor) did UPDATE-then-INSERT — but every audit trigger is `BEFORE
  UPDATE` and checks for the `governance_events` row synchronously at UPDATE
  time, so that order is rejected by the trigger every time. Phase 1's `asx
  thesis approve|reject` would have failed on first real use despite passing
  every mocked test, two review loops, and Phase 1's own manual verification
  (which tested hand-written SQL in the correct order, never the actual
  Python-emitted sequence). Fixed to INSERT-then-UPDATE in the shared helper
  (retroactively fixing theses, which now calls through it), live-verified
  against prod for the theses/themes/macro_theses paths, order pinned by
  `tests/test_governance_transitions.py`. Verification rule encoded in
  `portfolio-conventions.md`: statement ORDER of any governance transition must
  be live-verified against the real triggers — mocks and hand-replicated SQL
  don't count. The Phase 2a+2b review loop caught two more of the same
  mock-invisible class before commit: `log_agent_run()` bound an ISO-8601
  string to the TIMESTAMPTZ `agent_evidence.source_as_of` (asyncpg requires
  datetime — fixed with `fromisoformat` + pinning tests), and `open_thesis()`'s
  `system_default` placeholder INSERT omitted `governance_status`, landing new
  placeholders at the DEFAULT `'approved'` — the exact laundered state
  migration 0035's backfill exists to prevent (fixed: explicit `'draft'` +
  pinning test). Non-blocking residuals from the same review, LOW/INFO,
  fold into later work: (F-3) no service path advances a `draft`
  theme/theme_holding to `pending_review`, so backfilled/placeholder rows are
  unapprovable through code until Phase 2c's producers land; (F-4)
  `log_agent_run()` raises raw TypeError/AttributeError on structurally
  malformed JSON shapes (non-list evidence, non-dict claims) — fail-loud, no
  injection, tidy opportunistically; (F-6) `asx macro-thesis show|list` render
  agent-authored text with Rich markup enabled — consider
  `rich.markup.escape` at the display boundary.

### Next up — data-pipeline fix (user decision 2026-07-02, BEFORE Phase 2c)

A post-Phase-2b critical review found the discovery layer's data sources have
**never contained a row**: `ingest_regulatory` has failed daily for ~5 weeks (33
consecutive `job_runs` failures since its single success on 2026-05-27 — and its
Healthchecks deadman never surfaced this), and **`ingest_market_context` has
never executed in production** (zero `job_runs` rows under any name;
`market_context` has zero rows ever). The market-context job itself EXISTS —
built 2026-06-01, commit 605cb61, with an `asxos-ingest-market-context` cron
entry in `render.yaml` (schedule `45 20 * * 0-4`) — the gap is
deployment/secrets: the Render cron service appears never to have been
provisioned, and its `sync: false` manual secrets (`FRED_API_KEY`,
`HEALTHCHECK_URL_INGEST_MARKET_CONTEXT`) were never set. Consequence:
`market-context-narrator` and `/pm-review`'s MARKET line have been returning
"no snapshot" since they shipped, and `macro-economist` will — correctly, by
design — halt rather than invent a regime. Building Phase 2c's two further
discovery agents before this data flows would add more inert machinery.

Diagnosis is COMPLETE (2026-07-02); the code fixes land in this same commit.
Status per item:

1. **`ingest_regulatory` — diagnosed; code fixes in this commit.** The sources
   were broken three ways: (i) the ATO URL was a dead HTML page (site
   redesign; no stable public feed exists any more) — REMOVED from `SOURCES`,
   re-add tracked as operator item (d) below; (ii) the RBA feed is RSS-CB
   (RSS 1.0/RDF), which the parser could not read, so the one fetchable source
   parsed 0 events on every run since launch — parser fixed; (iii) Treasury
   fails from Render for reasons unverifiable outside Render (gov.au WAFs
   block non-browser clients — even Anthropic server-side fetchers get 403) —
   a browser User-Agent added as the portable mitigation, final verification
   on the next Render run. The deadman hole was two-layer: `JobMonitor` pinged
   Healthchecks only on success, so a daily-failing job sent nothing (fixed —
   failures now ping the `/fail` endpoint), AND
   `HEALTHCHECK_URL_INGEST_REGULATORY` is a `sync: false` manual secret that
   was likely never set on the live cron, so no deadman was ever armed (even
   the single 2026-05-27 success would not have pinged).
2. **`ingest_market_context` — no code work needed.** Job, JobMonitor wiring,
   and the `render.yaml` blueprint entry all exist (see above); what remains
   is entirely provisioning + secrets — operator items (a) below.
3. **Zombie `sync_financial_statements` `running` row (stuck since
   2026-06-27) — diagnosed; fixed in this commit.** The `JobMonitor`
   stale-heal was scoped to same-`as_of` rows only, so a stuck row from a
   prior day was never healed — scope widened in this commit; the zombie row
   itself is being marked `failed` manually.
4. Then run the deferred Phase 2b stage 4-5 for real: `/discover-macro` →
   `asx agent-run log` → `asx macro-thesis open --from-agent-run` → `approve`
   against live data (needs an environment with Postgres wire access — the
   remote sandbox only reaches Supabase via MCP HTTP).

**PROVISIONING UPDATE (2026-07-03, done via Render API from the Claude
session — user-authorized):** a live-state diff against `render.yaml` found
the gap was 12 services, not 1 — **twelve crons defined in render.yaml had
never been created on Render at all** (no Blueprint is connected to the repo,
so nothing ever applied the file; the 17 pre-existing services were created
by hand or via MCP). All 12 were created via the Render API mirroring their
render.yaml specs exactly (env values materialized as local copies, matching
the documented convention in `job-conventions.md`). **10 are resumed and
live** — including the thesis-discipline layer (`check-us-positions`,
`check-au-positions`, `check-thesis-invalidations`), which is the machinery
that would have emailed the HUBS.NYSE stop-breach alert on 2026-06-03 had it
been deployed. **2 remain suspended pending `FRED_API_KEY`:**
`asxos-ingest-market-context` (crn-d93q9onlk1mc739qiucg) and
`asxos-ingest-underlyings` (crn-d93q9pdaeets73eb9c30).

**REMAINING — operator actions:**

- (a) Provide `FRED_API_KEY` (free key at fred.stlouisfed.org) → set it on
  the two suspended crons and resume them. This is the last blocker on
  `market_context` data flowing, and therefore on the whole discovery
  pipeline (`macro-economist` halts by design without a snapshot).
- (b) Healthchecks deadman coverage: create 12 new checks (one per new cron;
  per-job UUID ping-URL convention) and set each
  `HEALTHCHECK_URL_<JOB>` env var on its service. The jobs run fine without
  them (URL is optional in code) but have no deadman until then —
  `check-cron-health` (now live, 22:00 UTC daily) provides interim
  stuck/missing-job email coverage. A Healthchecks.io API key would let the
  Claude session create all 12 checks programmatically.
- (c) Verify the next scheduled `ingest_regulatory` run writes rows (RBA at
  minimum) and confirm whether Treasury now passes with the browser
  User-Agent — the Treasury failure mode is only observable from Render.
  **CLOSED (2026-07-18):** confirmed, negative result — 13+ days of live
  Render runs (2026-07-04 to 2026-07-17) produced zero Treasury rows with
  the UA mitigation active; Treasury has been removed from `SOURCES` (see
  `jobs/ingest_regulatory.py`); this item is closed.
- (d) ATO re-add decision: small open item — the operator must pick a feed
  URL from https://www.ato.gov.au/about-ato/subscriptions in a browser (no
  stable public feed URL exists to hardcode), then re-add it to `SOURCES`.
- (e) ASIC/ASX remain unwired (they never were; the CLAUDE.md schema line has
  been corrected) — wiring them is a separate future decision, not part of
  this fix.
- (f) Longer-term: connect the repo as a real Render Blueprint so
  `render.yaml` pushes auto-sync (the workflow CLAUDE.md non-negotiable #2
  assumes). Needs the dashboard + a careful first-sync preview — 17
  pre-existing hand-created services mean a casual sync could duplicate
  services. Until then, API/MCP creation mirroring render.yaml is the apply
  step, followed by a live-state drift diff.
- (g) Low, code follow-up (security-engineer, 2026-07-03 invalidation-fix
  review): the copy-pasted `_send_alert()` in the six alert jobs
  (`check_us_positions`, `check_au_positions`, `check_thesis_invalidations`,
  `check_model_staleness`, `check_cron_health`, `validate_price_data`)
  interpolates condition/alert text into `<pre>{body}</pre>` without
  `html.escape()`. Single-user-authored content, so exploitation requires
  self-authorship — fix by extracting one shared helper with escaping, not
  six inline patches. Also fold the 12 newly provisioned crons into
  `job-conventions.md`'s pipeline schedule table while in there.

### Security finding — agent DB role scoping (found during Phase 2a+2b PR
review, 2026-07-02; land BEFORE Phase 2c)

security-engineer's review of the full PR diff (5 commits, `9bb8a5f..HEAD`)
found `macro-economist`'s "SELECT-only" constraint is prompt-level only —
`mcp__Supabase__execute_sql` can execute arbitrary SQL, and this diff is the
first time that unrestricted access sits next to a governed table
(`macro_theses`) fed by untrusted RSS content. A successful prompt injection
could in principle hand-write the exact `governance_events` INSERT +
`macro_theses` UPDATE pair the audit triggers require, bypassing human
approval entirely — no technical control stops it today, only the agent's
own instructions. Not introduced by this diff (the same tool-grant pattern
already existed via `market-context-narrator`); narrow attack surface today
(fixed, currently-trusted gov.au sources) and single-user blast radius, so
not treated as a blocker for this PR. Full writeup in
`.claude/rules/portfolio-conventions.md` under
`m14_candidate_agent_db_role_scoping`. Fix shape: a read-only Postgres role
for agent MCP sessions, distinct from the human/CLI role — needs a
`backend-architect` design pass (how the MCP server picks a role per
session isn't yet clear) before Phase 2c adds two more discovery agents on
the same pattern.

### Not started

- **Phase 2c** — `theme-researcher` + `instrument-selector` agents. Pattern
  proven by 2b; deliberately deferred until the data pipeline above feeds real
  context (user decision 2026-07-02).
- **Phase 3** — Executable thesis invalidation (`invalidation_indicator_registry` +
  evaluation job). Weigh immediately after the data-pipeline fix — it serves the
  thesis discipline loop directly (see HUBS.NYSE below).
- **Phase 4** — `/pm-review` integration (5→7 agents) + brief invalidation subsection.
- **Plan B** (multi-sleeve) — unchanged in substance from the prior backlog's B1-B11
  blockers / FC1-FC6 findings; full detail preserved in the plan file's Section 8.
  Still requires Phase 0.5 (now done) before it can start. **HUBS.NYSE still needs a
  `thesis_revisions` entry** (stop $230 violated, pm-review = EXIT-CANDIDATE, no
  revision logged) — this is a portfolio decision, not blocked on any of the above,
  and re-flagged by the 2026-07-02 review: it is the exact failure mode the thesis
  model exists to prevent, and only James can supply the revision reasoning.

See the plan file for full schema DDL, CLI command specs, and phase completion
criteria before starting Phase 1.

---

# asxos — next-session backlog (open follow-ups, as of 2026-06-28)

Open items left after branch `claude/edmund-yong-subagent-wecr3g` (SMSF CGT
break-even fix + spec §5.4, 4 Design-MED items, shared-project audit, migrations
0029/0030). Grouped by priority. Each line: what + why + governing file / owner.

Source docs: `docs/db-shared-project-audit-2026-06-28.md`,
`docs/design-med-2026-06-28.md`, `docs/archive/proposals/cgt-break-even-amendment-2026-06-28.md`,
`docs/backlog-test-coverage.md`, and CLAUDE.md "Known coverage gaps" /
"Known test environment gaps".

---

## P1 — spec-governed / correctness

- ~~**TC-20 Div 296 cost-base reset (s 296-50)**~~ — **CLOSED** (spec v1.5).
  Implemented in `positions.py` (election path via `div296_realised_gains` from
  `cost_base_div296`) and tested in `tests/test_tax_positions.py` TC-20 section
  (`:354-413`). The "## TC-20 kickoff" section below is a historical record only —
  do not re-run it.
- ~~**TC-21 45-day franking warning (s 207-145)**~~ — **CLOSED** (session
  2026-06-29). Implemented in `dividends.py::check_45_day_warnings_smsf` + wired into
  `tax_view_smsf()`. Four tests cover the positive case and three boundary cases.
- ~~**SMSF ECPI-on-CGT numeric path is unverified**~~ — **CLOSED** (session
  2026-06-29). TC-24 added to spec §11 (v1.4) with matching test
  `test_tc24_smsf_ecpi_stacks_with_cgt_discount`. Implementation was already correct.

## P2 — endpoints / honesty completions

- **opportunity_cost Phase-5 producer** — add `current_net_expected_return
  NUMERIC(18,6)` to `opportunity_cost_scenarios`, populated by the producer with the
  same CGT-friction model applied to the held position, so the screen becomes a true
  delta (`delta = net − current`). The 2026-06-28 rename
  (`_MEANINGFUL_DELTA → _MEANINGFUL_NET_LEVEL`) only made the level-screen honest; it
  is a stopgap, not the endpoint. Governing: `docs/design-med-2026-06-28.md` Item 2;
  schema change → `backend-architect`.
- **Test-coverage sprint** — ~31 confirmed-untested gaps remain in
  `docs/backlog-test-coverage.md` (33 minus the two now closed: `cgt_break_even_price`
  and any others marked COVERED). Highest-value is P0 there: `api/main.py` lifespan /
  migration-drift / REQUIRED_MIGRATIONS has zero tests on success or RuntimeError
  branches (CLAUDE.md non-negotiable #1). See that doc for the full per-file list and
  the mock pattern.
  **CLOSED 2026-08-22 — the named P0 item is done; the rest of the sprint stands.**
  `tests/test_api_main.py` covers `_check_migration_drift` (below-required raises,
  at-required passes, above-required passes, skip-by-config short-circuits), the lifespan
  (success plus both hard-fail branches) and `/health` (200 / 503). The above-required
  test is the load-bearing one: it pins the guard as `count < REQUIRED_MIGRATIONS`
  rather than `!=`, which is what keeps the API booting during an apply-then-bump window
  (2026-08-21: ledger 97, constant 96). Note the referenced path moved —
  `docs/backlog-test-coverage.md` is now `docs/archive/backlog-test-coverage.md`, and its
  `:16` entry carries the same superseded claim.
  **Postscript 2026-09-02:** the count guard described above is itself gone —
  `REQUIRED_MIGRATIONS` was deleted 2026-08-23 in favour of the name-set diff in
  `asxos/schema_drift.py`, so the "apply-then-bump window" it protected no longer exists.
  The paragraph stands as the record of why that test was written; the mechanism it
  describes is historical.

## P3 — DB tidy-ups (optional, low risk) and CI / scope

- **Drop schema `archive_dropped_20260628`** — the 14 archived tables from the 0030
  wipe (CTAS backup). Drop once confident nothing is needed from it, to reclaim space.
  Governing: `docs/db-shared-project-audit-2026-06-28.md` §3.
- **Drop ~12 orphaned foreign trigger/helper functions** — left inert by 0030
  (e.g. `update_model_versions_timestamp` / `update_updated_at_column`). They were not
  dropped because dropping shared-named ones could affect kept asxos triggers; verify
  none are referenced by an asxos trigger before dropping. Governing: audit doc §3.
- **Drop empty `public.schema_migrations` leftover** — confirm it is the dead foreign
  leftover and not asxos's live migration-tracking table before dropping. Governing:
  audit doc (inventory §1). The live ledger the drift check reads is
  `supabase_migrations.schema_migrations`, compared by migration *name* set
  (`asxos/schema_drift.py`) since 2026-08-23 — the `REQUIRED_MIGRATIONS` count named
  here previously no longer exists.
- **Make `full-check` a REQUIRED status check** — needs a paid GitHub plan to enforce
  server-side branch protection. Meanwhile the pre-push hook + CI signal cover it; the
  user runs `make install-hooks` locally. Governing: CLAUDE.md (CI / `full-check`).
- **break-even: thread the user's real marginal rate into the position monitor** —
  currently the disclosed `0.45` default flows through `cgt_break_even_price()`. Real
  per-user rate is **out of v1 scope**, noted only. Governing:
  `docs/archive/proposals/cgt-break-even-amendment-2026-06-28.md` + spec §5.4.

---

## TC-20 kickoff (next session)

> **COMPLETED — HISTORICAL RECORD (banner added 2026-07-04).** TC-20 was implemented
> and tested (spec v1.5); see `asxos/domain/tax/positions.py` + `tests/test_tax_positions.py`
> TC-20 section. Do NOT re-run this kickoff. Retained for the worked example and
> process shape only.

**Branch:** create a new `claude/**` branch from `main` after PR #9 merges.

**Task:** Implement TC-20 — Div 296 cost-base reset (s 296-50, spec §6.4/§6.5).

**State entering the session:**
- `SMSFConfig.div296_election_made` (bool) — consumed only for a static advisory
  string; the actual election branching logic is unimplemented.
- `SMSFConfig.div296_reset_date` (date) — never consumed anywhere.
- `holding_lots.cost_base_div296` column (migration 0001) — initialised to
  `cost_base_normal` on lot creation; never written post-reset or read in any
  gain-computation path.
- `div296_liability()` in `div_296.py` receives `ncg.net_capital_gain` (computed
  from `cost_base_normal`). The spec requires a separate Div-296 earnings figure
  computed from `cost_base_div296` when the election is made.
- The depreciated-asset warning body (`positions.py`) is a static string; actual
  detection of which lots are depreciated is not implemented.

**Files to read first:**
- `docs/foundation/spec/tax-alpha.md` §6.4, §6.5, §11 (TC-20 row absent — must
  be added as spec amendment)
- `asxos/domain/tax/div_296.py` (full)
- `asxos/domain/tax/positions.py` lines 148–160 (current Div 296 earnings path)
- `asxos/domain/tax/types.py` — `SMSFConfig`, `HoldingLot`, `Div296Outcome`
- `migrations/0001_*.sql` — `holding_lots` schema (dual cost-base columns)

**TC-20 worked example (spec §11):**
Acquired 2020-01-01 $50,000; MV at 2026-06-30 $80,000; disposed 2027-01-01
$100,000; SMSF accumulation; election made.
- Fund CGT (ordinary): gain $50,000 → 1/3 discount → net $33,333 → tax 15% = $5,000.
- Div 296 earnings (reset base): gain $20,000 → 1/3 discount → included $13,333.

**Mandatory implementation order:**
1. Read spec §6.4, §6.5, §11 in full.
2. Consult `tax-spec-conformance` agent on the proposed spec amendment.
3. Amend spec (v1.5): add TC-20 to §11 matrix; flesh out §6.4 disposal branching
   (ordinary CGT vs Div 296 paths); add §13 change log entry.
4. Implement in `positions.py`: when `config.div296_election_made is True`,
   compute a separate Div-296 gain using `cost_base_div296` and feed it (not
   `ncg.net_capital_gain`) into `div296_liability()`.
5. Add depreciated-asset detection (lot where `cost_base_div296 > current_mv` at
   reset date) to replace the static §6.5 advisory with a data-driven warning.
6. Tests: pin TC-20 worked example across all five output fields.
7. Full review loop (security-engineer / refactoring-expert / technical-writer)
   before committing. review-gate marker required.

**Governance:** CLAUDE.md non-negotiable #8 — spec amendment first, then code.
No schema changes needed (dual cost-base columns exist from migration 0001).
Estimated scope: 6–10 hours.
