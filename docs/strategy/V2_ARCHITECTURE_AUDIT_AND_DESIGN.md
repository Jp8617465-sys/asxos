---
title: V2 Architecture Audit & End-to-End Design
location: docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md
status: draft (system-architect audit of V2_PRODUCT_THESIS_AND_BRIEF_SPEC)
auditor: system-architect agent
audited_spec: docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md (locked 2026-05-28)
last_updated: 2026-05-28
---

# V2 Architecture Audit & End-to-End Design

## Executive summary

The V2 thesis plugs in. The existing M1-M14a foundation (universe → prices → fundamentals → signals → portfolio build → brief composer → Resend) is structurally compatible with the thesis-centric reframe — the brief composer already returns dataclass sections that compose into a Jinja template (`asxos/brief/compose.py:139-174`), the regulatory firewall (`_require_personal_use()` + `ASXOS_PERSONAL_USE`) is established as a CLI gate (`asxos/cli/main.py:751-763`), the dark-launch double-gate pattern (`ASXOS_PORTFOLIO_BRIEF_ENABLED`) is already wired through `render.yaml`, and the CGT calendar arithmetic is already exposed cleanly via `asxos.domain.tax.cgt.days_to_eligibility` (the exact primitive the brief's "NVDA CGT boundary in 18d" example needs). There is no architectural reason the spec cannot ship.

The top three blockers are: (1) the existing brief composer's `collect()` returns a single `BriefData` dataclass with no severity tuples — the M-Snapshot milestone *requires* a redesign of the section-collector interface, which means M-Brief-Reshape cannot be a "add new sections" pass; it must touch every existing section. (2) The spec's Part 5.3 example uses `MIN.AX` and the existing universe stores AU symbols as `BHP.AU` (per `asxos/cli/main.py:182` `_infer_currency` and the holding_lots FK contract) — the spec needs an exchange-suffix-normalisation pass or the FK joins on `theses.symbol` will silently fail. (3) The Part 5.5 `cross_layer_observations()` function is the load-bearing analytical surface that makes the platform "think alongside the user," and Part 7's worked example references one in section 5 ("Cross-layer observation:") and one in s10 (opportunity cost narrative) — but the spec leaves placement ambiguous; if not nailed down before M-Brief-Reshape, the brief reshape will land without it and the visual spec will fail to match.

Overall confidence: **high** that the system can be built, **medium-high** that the proposed 6-week sequence is achievable, **medium** that the brief on first-real-week will match Part 7 without a second reshape pass. The thesis layer is the right wedge; the existing code is closer to ready than the spec implies (the V1 portfolio/signals/brief pipeline is already producing dataclass-structured output, not just prose).

---

## Part A — Current state assessment

### What's already built (concrete file references)

| Layer | Files | Status |
|---|---|---|
| Universe ingest | `asxos/ingestion/universe.py`, `jobs/sync_universe.py` | M1 done. Weekly Sat 16:00 UTC. |
| Prices | `asxos/ingestion/prices.py`, `jobs/sync_prices.py` | M2 done. Mon-Fri 20:30 UTC. Bulk-by-date one EODHD call. |
| Fundamentals | `asxos/ingestion/fundamentals.py`, `jobs/sync_fundamentals.py` | Daily 18:00 UTC. |
| Signals (Model A v1_5) | `asxos/domain/signals/*`, `asxos/domain/models/*`, `jobs/generate_signals.py` | M6-M9 done. LightGBM + SHAP. |
| Regime classifier (V1) | `asxos/domain/signals/regime.py` | Three-label (bull/bear/neutral) over 200d SMA of top-10 liquidity proxy. **Will need to be superseded by the five-label V2 classifier, not replaced — V1 regime is consumed by `apply_regime_thresholds` in `ml-conventions.md`.** |
| Tax engine | `asxos/domain/tax/{cgt,div_296,franking,medicare,positions,lots,fx_gain,import_csv,dividends}.py` | M10 done. Spec-cited. `days_to_eligibility` is the primitive the V2 brief needs. |
| Holdings | `holding_lots` + `current_holdings` view (migration 0001), `asx import-holdings` CLI | M10/M11. Supports AUD + USD cost bases. |
| Decisions journal | `decisions` table, `asx journal add/list/review` (`asxos/cli/main.py:528-703`) | Done. **The V2 thesis-revision audit log can layer on top of this or sit alongside; see Part C.** |
| Regulatory ingest | `asxos/ingestion/regulatory.py`, `jobs/ingest_regulatory.py` | Done. Daily RSS pull. |
| News + sentiment | `asxos/ingestion/news.py`, `asxos/ingestion/sentiment.py`, `jobs/ingest_news.py`, `jobs/ingest_sentiment.py` | M14a/M14b done. Dark-launched (`ASXOS_NEWS_BRIEF_ENABLED=0`). |
| Portfolio M13 | `asxos/domain/portfolio/{build,allocator,constraints,rebalance,tax_overlay,volatility,profile,paper_trade,types}.py`, `jobs/build_portfolio.py` | Done. `PortfolioService.build()` is the orchestrator. Dark-launched (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`). Weekly Sat 20:00 UTC. |
| Brief composer (V1) | `asxos/brief/compose.py`, `asxos/brief/email.py`, `asxos/brief/templates/`, `jobs/compose_brief.py` | M5 done. Six sections, Jinja-rendered HTML, Resend dispatch. Mon-Fri 21:00 UTC. |
| CLI | `asxos/cli/main.py` (1473 lines, single file) | Typer-based. `asx predict | signal | tax-view | tax-action | journal {add,list,review} | brief | build-portfolio | propose-trades | portfolio {show,history,paper-review,signoff} | profile {init,show,activate,list} | news signoff | import-holdings | model {activate,list}`. |
| JobMonitor + Healthchecks | `asxos/jobs/utils/job_monitor.py` | Async context manager, writes `job_runs`, distinguishes `success`/`blocked`/`failure`. |
| Render IaC | `render.yaml` | 11 services (1 web + 10 cron). MCP-driven mutations only. |
| Backup | `scripts/backup_irreplaceable.sh` | Daily 13:30 UTC. Dumps `holding_lots`, `decisions`, `screening_rules`, `model_versions`, `profiles`. **Needs additions per Part J.** |

### What's reusable

- **The Jinja templating + Resend dispatch pattern.** `render_html(BriefData) → str` + `send_brief(html, as_of) → SendResult` in `asxos/brief/email.py` is the right shape — the V2 reshape replaces the `BriefData` dataclass and the `brief.html.j2` template, nothing structural.
- **The `JobMonitor` async context manager.** Three new cron jobs (`ingest_market_context`, `ingest_underlyings`, eventually a `thesis_revisit_evaluator`) use it as-is.
- **The dark-launch gate pattern.** `ASXOS_PORTFOLIO_BRIEF_ENABLED=0` in `render.yaml` and `ASXOS_NEWS_BRIEF_ENABLED=0` are already plumbed. A `ASXOS_THESIS_BRIEF_ENABLED` gate fits the same mould (suggest a single `ASXOS_V2_BRIEF_ENABLED` master gate covering sections 2, 3, 5, 8, 10 simultaneously, since they share the V2 data model).
- **The `_require_personal_use()` decorator pattern.** Every new `asx thesis | theme | watchlist | idea` command reuses it verbatim.
- **The CGT calendar arithmetic.** `days_to_eligibility(acquired_at, today)` from `asxos/domain/tax/cgt.py:36-40` is the canonical primitive. Part 7's "NVDA CGT boundary in 18d" is a one-liner against it.
- **The profile + capital model.** `profiles` table (M13) holds capital, cash floor, leverage, sector caps, per-name caps — the V2 brief's section 7 (allocation health) reads directly from it. No new schema needed there.

### What's missing

- All five V2 domain layers: `asxos/domain/theses/`, `asxos/domain/themes/`, `asxos/domain/underlyings/`, `asxos/domain/regime/` (new — replaces or supplements the V1 `signals/regime.py`), `asxos/domain/brief/` (new — the section-collector framework; current `asxos/brief/compose.py` is procedural, not collector-based).
- Three new cron jobs: `ingest_market_context`, `ingest_underlyings`, `evaluate_thesis_revisits` (the last is M-Thesis-Revisit-Engine, post-first-real-week).
- 9 new tables per Part 6.
- A FRED API client (for US HY OAS substitution when iTraxx isn't available).
- All `asx thesis | theme | watchlist | idea` CLI commands.

---

## Part B — End-to-end data flow

One full day, traced step by step, in UTC. AEST anchors in parentheses. New V2 steps marked **[NEW]**.

| # | Time UTC | Step | Owner | Depends on | Failure mode |
|---|---|---|---|---|---|
| 1 | 13:30 | Backup irreplaceable tables (now incl. `theses`, `themes`, `theme_holdings`, `thesis_revisions`, `thesis_underlyings`) | `scripts/backup_irreplaceable.sh` | DB reachable, GitHub PAT valid | Healthcheck miss → email alert. Job exits non-zero. |
| 2 | 18:00 | Fundamentals sync (per-symbol EODHD) | `jobs/sync_fundamentals.py` | EODHD API up | UPSERT, idempotent. Stale fundamentals tolerated (`pd.merge_asof` with 45d lag). |
| 3 | 20:30 (06:30 AEST next day) | Prices sync (bulk-by-date one call) | `jobs/sync_prices.py` | EODHD API up | Hard-fail. Downstream `generate_signals` gated on `job_runs.status='success'`. |
| 4 | 20:45 **[NEW]** | Market context ingest (ASX 200 close, breadth, A-VIX, macro, credit, US indices) | `jobs/ingest_market_context.py` | EODHD up; FRED API up (US HY OAS fallback) | Regime classifier hard-fails on missing core indicators (ASX 200, A-VIX). Indicators with documented fallbacks (iTraxx → US HY OAS) degrade gracefully *with explicit substitution flag in `regime_rationale` JSONB*. **Not a silent fallback.** |
| 5 | 20:48 **[NEW]** | Underlyings ingest (commodities, currencies, rates, energy) | `jobs/ingest_underlyings.py` | EODHD up; secondary source for lithium carbonate | Per-underlying UPSERT. Missing underlyings logged to a structured `ingest_warnings` rows section; brief section 5 surfaces affected underlyings as "data stale". |
| 6 | 20:50 (06:50 AEST) | Signals refresh (Model A v1_5) | `jobs/generate_signals.py` | sync_prices ok | GATE: hard-fail if upstream missing. UpstreamBlocked → `job_runs.status='blocked'`, no Healthchecks ping. |
| 7 | 20:52 **[NEW]** | Thesis revisit triggers fire (M-Thesis-Revisit-Engine, post-first-real-week) | `jobs/evaluate_thesis_revisits.py` | signals ok, market_context ok, underlyings ok | Pure recomputation — re-derives `theses.revisit_due_at` based on new conditions. No data lost on failure. |
| 8 | 20:55 | Regulatory ingest (ASIC/RBA/ATO/ASX RSS) | `jobs/ingest_regulatory.py` | RSS endpoints reachable | UPSERT. Soft fallback for individual feeds. |
| 9 | 20:57 | News ingest | `jobs/ingest_news.py` | EODHD news endpoint | Holding-symbol filter. Idempotent. |
| 10 | 21:00 (07:00 AEST) | **Compose brief** (Resend dispatch) | `jobs/compose_brief.py` → `asxos/domain/brief/composer.py` **[NEW path]** | All of 4-9 (with documented degradation) | Per-section freshness gates. Whole brief never hard-fails unless DB itself unreachable. |
| 11 | Saturday 20:00 | Weekly portfolio recompute | `jobs/build_portfolio.py` | signals fresh | Already exists. Continues to feed section 7 (allocation health). |

### Step 10 (compose brief) topological order

The brief composer runs **sections in dependency order**, then aggregates the section-severity tuples into the snapshot. Sections are independent except where noted. Pseudocode:

```
async def compose(as_of) -> Brief:
    async with acquire() as conn:
        # Phase 1: gather shared context (used by multiple sections)
        market_ctx = await collectors.market_context(conn, as_of)    # → section 2 + s3/s6 modulation
        active_theses = await collectors.active_theses(conn, as_of)   # → section 3 (depends on market_ctx + underlying scores)
        underlying_snapshot = await collectors.underlyings(conn, as_of)  # → section 5 (depends on active_theses for attribution)

        # Phase 2: independent collectors (can run concurrently via asyncio.gather)
        wealth, watchlist, ideas, alloc, themes_section, tax_ops, opp_cost = await asyncio.gather(
            collectors.wealth_state(conn, as_of),
            collectors.watchlist(conn, as_of, market_ctx),
            collectors.new_ideas(conn, as_of, market_ctx, active_theses),   # suppressed under risk-off
            collectors.allocation_health(conn, as_of),
            collectors.theme_dashboard(conn, as_of, active_theses),
            collectors.tax_operational(conn, as_of),
            collectors.opportunity_cost(conn, as_of, active_theses),         # surfaces only when a thesis is near-target
        )

        # Phase 3: cross-layer observations (Part 5.5) — needs everything above
        cross_layer = collectors.cross_layer_observations(market_ctx, active_theses, underlying_snapshot)

        # Phase 4: section health roll-up (each collector's freshness metadata)
        section_health = collectors.section_health(conn, as_of, [...all sections...])

        # Phase 5: snapshot composer — aggregates severity tuples, applies "one thing today" triage
        snapshot = build_snapshot(sections, section_health, cross_layer)

    return Brief(snapshot=snapshot, sections=[...], section_health=section_health)
```

**Sequence vs parallel:** the three Phase-1 collectors are inherently sequential because section 3 (theses) consumes the regime label to add the "Regime context: late-cycle posture..." line per Part 4.4, and section 5 (underlyings) consumes the thesis list for attribution scoring. Sections in Phase 2 are read-only against the DB and can run concurrently with `asyncio.gather`. The brief is small enough (a few dozen rows total) that the win from parallelism is marginal; the discipline is having well-defined collector boundaries.

### Failure cascade audit

A section's collector must classify its outcome into one of:

| Outcome | When | Brief behaviour |
|---|---|---|
| `SectionResult.ok(content, severity_tuple)` | All data fresh and complete | Render as normal. |
| `SectionResult.degraded(content, warning, severity_tuple)` | Some inputs stale or missing but section still has substance | Render with a yellow banner at the top of the section + entry in section health. |
| `SectionResult.suppressed(reason)` | Section can't produce anything meaningful (e.g. no underlyings yet, no theses yet) | Section absent from brief. Listed as "—" in section health. |
| `SectionResult.failed(error)` | Collector raised | Section absent + red "[section X errored]" line in section health + entry in `job_runs.error_message`. **The brief still sends.** |

**Cascading silent failures (CLAUDE.md #10 prohibition):** the only acceptable "graceful" path is the four classifications above, each of which writes a row to a new `brief_section_runs` table or extends `job_runs` (recommend extending — `job_runs` already exists for `compose_brief` and adding a `section_name` column is cheaper than a new table). The `compose_brief` job overall still succeeds (Healthchecks pings) as long as the snapshot rendered and the email sent; if section 3 errored, that fact is *visible* in the brief itself (the section-health footer) and in `job_runs` (the brief's `error_message` includes a structured list of failed sections).

**The only hard-fail in the brief path:** the DB pool itself failing to open. Per existing pattern in `asxos/api/main.py` lifespan and `asxos/cli/main.py:_run_brief`, this is a `RuntimeError` and the brief job exits non-zero. Healthchecks miss → email alert. This is correct.

---

## Part C — Schema integration audit

### New tables vs existing schema

**FK target `universe(symbol)`:** existing `universe` has `(symbol TEXT PK, sector, currency, market_cap, is_active)` per migration 0001. The V2 spec proposes `theses.symbol REFERENCES universe(symbol)` and `theme_holdings.symbol REFERENCES universe(symbol)`. **Compatibility:** OK with one caveat — the spec's worked example uses `MIN.AX`, `NVDA`, `CSL.AX`, `BHP.AX` formats, but the existing universe normalises AU symbols to `BHP.AU` (per `asxos/cli/main.py:165-169` `_infer_currency` and `asxos/cli/main.py:172-187` `_ensure_in_universe`). **Resolution required before M-Thesis-1:** decide whether (a) the V2 thesis spec migrates to the existing `.AU` suffix convention (preferred, minimises code change), or (b) the universe gains a new `display_symbol` column. **Recommend (a) — update the spec's example symbol formats in Part 7 to `MIN.AU` etc. and document the convention in `.claude/rules/portfolio-conventions.md`.** US symbols (`NVDA`) also need a suffix — the existing convention is `NVDA.US`.

**No naming collisions:** none of the proposed table names (`theses`, `themes`, `theme_holdings`, `thesis_revisions`, `thesis_underlyings`, `underlyings`, `underlying_prices`, `market_context`, `opportunity_cost_scenarios`) collide with existing tables.

### Reconciliation with `holding_lots` / `current_holdings`

The spec's "active theses" section (section 3) needs to reconcile a thesis with its lots. Four cases exist:

1. **One thesis, one symbol, one lot** — trivial join `theses.symbol = holding_lots.symbol`.
2. **One thesis, one symbol, multiple lots** (e.g. dollar-cost averaging into MIN.AU over a year) — aggregate lots by symbol; thesis card shows the average entry, the per-lot CGT boundaries (the NVDA section in Part 7 explicitly says "Largest lot reaches CGT discount eligibility in 18 days" — the brief should iterate lots and surface the most-imminent one).
3. **A "watching" thesis with no lots yet** (`theses.status='watching'`, the BHP example in Part 7) — no join. The thesis card shows the entry band and waits for entry confirmation.
4. **Lots exist but no thesis covers them** (legacy holdings imported via CSV but never given a thesis) — this is the discovery problem. The brief should surface these in a "Untagged holdings" sub-section under section 3 with a `asx thesis open SYMBOL --import-lot` prompt. Without this, the first-real-week brief is misleading.

**Recommendation:** add a fifth status to the spec — `theses.status` should be `watching | active | exited | expired` per Part 6.1, but the M-First-Real-Week milestone needs a pre-step where every imported lot gets an `active` thesis (even if rough; the LLM-assisted structuring milestone M-LLM-Thesis-Structuring is for refining them later). The spec implies this in Part 8.2 M-First-Real-Week ("Open theses for each (using `asx thesis open` on each held name)"), but it's worth elevating to a hard precondition: **the brief's section 3 must list every held symbol, either as an active thesis or as an untagged-holdings line.**

**Linking design:** no `holding_lot_id` FK on `theses`. The join is on `symbol`. Rationale: a thesis is about the *position*, not a specific lot. Different lots may have different CGT statuses (Part 7 NVDA), different cost bases (DCA), and a single thesis spans all of them. Surface per-lot detail inside the thesis card by joining at render time.

### CGT calendar arithmetic surface

`days_to_eligibility(acquired_at, today)` from `asxos/domain/tax/cgt.py:36-40` is already exposed and uses the correct `relativedelta(years=1) + timedelta(days=1)` arithmetic (spec §5.1). The brief's section 9 (tax & operational) and section 3 (NVDA thesis card) call this directly per lot.

**One gotcha:** the existing `asxos/brief/compose.py:235-257` `_tax_actions` function already calls `days_to_eligibility` and surfaces lots crossing the boundary in next 30d. **The V2 reshape should not duplicate this logic** — it should pull from the same primitive but render into both s3 (thesis card line) and s9 (tax & operational list) without re-querying. Recommend a single `tax_collector.boundary_lots(conn, as_of, window=30)` returning a list keyed by symbol, consumed by both the thesis-card collector and the tax-ops collector.

### Single-user / no-user_id invariant

Reviewed all 9 proposed tables in Part 6. **No `user_id` columns proposed.** The `profiles` table (existing M13) is the single-user-config table per `.claude/rules/portfolio-conventions.md` — the V2 spec does not implicitly assume multi-user anywhere. ✓

### Regulatory firewall gating

The V2 brief composer must be gated by `ASXOS_PERSONAL_USE=1`. **Currently:** `jobs/compose_brief.py` runs with `ASXOS_PERSONAL_USE=1` set in `render.yaml:250-252`. ✓ The composer code itself does not yet check the flag (the existing brief is "informational" and pre-V2 didn't need it); the V2 reshape should add a check at the top of the new `composer.compose()` mirroring `_require_personal_use()` from the CLI.

**Second gate:** I recommend a single new master gate `ASXOS_V2_BRIEF_ENABLED=0` rather than per-section gates. The V2 sections (2, 3, 5, 8, 10) form a coherent product whose dark-launch failure mode is "the brief looks like V1." Per-section gates create combinatorial mess. The existing `ASXOS_PORTFOLIO_BRIEF_ENABLED` covers section 7 (allocation health) and stays — section 7 was M13's gated section.

---

## Part D — Module/package layout

### Proposed `asxos/domain/` tree

```
asxos/domain/
├── theses/                          [NEW]
│   ├── __init__.py
│   ├── types.py                     # Thesis, ThesisRevision, ThesisStatus enum, InvalidationCondition
│   ├── lifecycle.py                 # open/revise/exit/expire — pure state transitions returning Revisions
│   ├── service.py                   # ThesisService — DB I/O, async asyncpg
│   ├── revisit.py                   # revisit cadence logic + assumption-shift detection (M-Thesis-Revisit-Engine)
│   └── underlying_attribution.py    # weighted score function (pure)
│
├── themes/                          [NEW]
│   ├── __init__.py
│   ├── types.py                     # Theme, ThemeHolding, ThemeStage enum
│   ├── service.py                   # ThemeService — DB I/O
│   ├── exposure.py                  # aggregate stock×theme exposure → portfolio-level theme weights (pure)
│   └── adjacency.py                 # LLM-assisted adjacency suggestion (deferred; M-Theme-Adjacency)
│
├── regime/                          [NEW]
│   ├── __init__.py
│   ├── types.py                     # RegimeLabel enum, RegimeRationale dataclass
│   ├── classifier.py                # rules-based predicate evaluator (pure)
│   └── indicators.py                # indicator-loading + missing-indicator handling
│
├── underlyings/                     [NEW]
│   ├── __init__.py
│   ├── types.py                     # Underlying, UnderlyingPrice, UnderlyingCategory enum, UnderlyingScore
│   ├── service.py                   # UnderlyingService — DB I/O
│   ├── attribution.py               # thesis-level dependency vector × underlying movement → 🟢🟡🔴 (pure)
│   └── divergence.py                # divergence-detection rules (pure)
│
├── brief/                           [NEW — supersedes asxos/brief/compose.py]
│   ├── __init__.py
│   ├── types.py                     # SectionResult, SeverityTuple, Snapshot, Brief, Severity enum
│   ├── severity.py                  # all severity-computing pure functions (per Part 2.3 / 3.5)
│   ├── composer.py                  # top-level orchestrator (Phase 1-5 from Part B above)
│   ├── snapshot.py                  # snapshot aggregator (severity ordering + "one thing today" triage + affirmative line)
│   ├── cross_layer.py               # cross_layer_observations(market_ctx, theses, underlyings) → 0-3 observations
│   ├── renderer.py                  # Jinja-based HTML renderer (reused from asxos/brief/email.py)
│   └── collectors/
│       ├── __init__.py
│       ├── wealth_state.py          # section 1 (reuses portfolio service + current_holdings)
│       ├── market_context.py        # section 2 (consumes regime classifier)
│       ├── active_theses.py         # section 3 (joins theses + lots + underlying scores + regime modulation)
│       ├── watchlist.py             # section 4 (theses where status='watching')
│       ├── underlying_drivers.py    # section 5 (latest underlying_prices + thesis-attribution rollup)
│       ├── new_ideas.py             # section 6 (system-surfaced; suppressed under risk-off)
│       ├── allocation_health.py     # section 7 (existing portfolio cap check)
│       ├── theme_dashboard.py       # section 8 (consumes themes + theme_holdings + active_theses)
│       ├── tax_operational.py       # section 9 (CGT boundaries, dividends, regulatory)
│       ├── opportunity_cost.py      # section 10 (opportunity_cost_scenarios)
│       └── section_health.py        # footer
│
├── portfolio/                       [EXISTING — no changes; section 7 reuses]
├── tax/                             [EXISTING — section 9 reuses days_to_eligibility, etc.]
├── signals/                         [EXISTING — section 6 (new ideas) and underlying-attribution consume signals]
├── models/                          [EXISTING — model registry stays]
├── regulatory/                      [EXISTING — section 9 reuses]
└── journal/                         [EXISTING — overlaps with thesis_revisions; see note]
```

**Note on `journal/` vs `theses/`:** the existing `decisions` table is a free-form journal (`asxos/cli/main.py:528-703`). The new `thesis_revisions` is a structured audit log scoped to a thesis. They serve different purposes — keep both, but `asx thesis revise` should *additionally* write a decisions row tagged `[thesis_revision:<thesis_id>]` so the existing `asx journal list` view stays complete.

### Jobs

```
jobs/
├── ingest_market_context.py         [NEW] — 20:45 UTC daily (Sun-Thu)
├── ingest_underlyings.py            [NEW] — 20:48 UTC daily (Sun-Thu)
├── evaluate_thesis_revisits.py      [NEW, post-first-real-week] — 20:52 UTC daily (Sun-Thu)
└── compose_brief.py                 [EXISTING — internals rewritten in M-Brief-Reshape]
```

### CLI surface (see Part I for detail)

```
asxos/cli/
├── main.py                          [existing; keep — but split out V2 subtypers]
├── thesis.py                        [NEW] — asx thesis subtype
├── theme.py                         [NEW] — asx theme subtype
├── watchlist.py                     [NEW] — asx watchlist subtype
├── idea.py                          [NEW] — asx idea subtype
└── brief.py                         [NEW] — asx brief subtype (keep existing `asx brief` for backwards compat)
```

`main.py` at 1473 lines is already at the threshold where it should be split. Recommend extracting existing subtypers (`profile`, `model`, `journal`, `news`, `portfolio`) into their own files in the same pass.

### Dependency arrows

```
brief.composer
    ↓ depends on
    ├── brief.collectors.*
    │       ↓ depends on
    │       ├── theses.service  (active_theses, watchlist)
    │       ├── themes.service  (theme_dashboard)
    │       ├── regime.classifier  (market_context)
    │       ├── underlyings.service  (underlying_drivers, active_theses for attribution)
    │       ├── underlyings.attribution  (active_theses for thesis-level scoring)
    │       ├── portfolio.PortfolioService  (allocation_health)
    │       ├── portfolio.PortfolioService  (wealth_state — read-only)
    │       ├── tax.cgt, tax.dividends  (tax_operational, active_theses)
    │       ├── signals.loader  (new_ideas)
    │       └── regulatory  (tax_operational)
    ├── brief.severity
    ├── brief.snapshot
    └── brief.cross_layer
```

**No circular deps.** The brief domain is purely a *consumer*. Portfolio, tax, signals, theses, themes, underlyings, regime know nothing about the brief.

---

## Part E — Brief composer design

### Section-collector interface

```python
# asxos/domain/brief/types.py

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Severity(Enum):
    GREEN = "green"     # 🟢 informational
    YELLOW = "yellow"   # 🟡 attention needed
    RED = "red"         # 🔴 decision required today


@dataclass(frozen=True)
class SeverityItem:
    """One severity-bearing item produced by a section."""
    severity: Severity
    headline: str               # single clause, sentence-case, ≤ 80 chars
    section_ref: int             # 1-10; for snapshot ordering
    detail_ref: str              # anchor link or item id for "go to" navigation
    triage_priority: int         # 1-6 per Part 3.5; lower = higher priority


@dataclass(frozen=True)
class SectionFreshness:
    """Per-section freshness metadata for the footer."""
    section_name: str
    last_data: str               # ISO date or "live" or "run #N (HH:MM)"
    ok: bool


@dataclass(frozen=True)
class SectionResult:
    """A collector returns one of four variants. Composer dispatches per state."""
    state: Literal["ok", "degraded", "suppressed", "failed"]
    content: str = ""            # rendered HTML/markdown for this section
    items: tuple[SeverityItem, ...] = ()   # severity items (may be empty even on ok)
    freshness: SectionFreshness | None = None
    warning: str = ""            # populated when state="degraded"
    error: str = ""              # populated when state="failed"
```

A collector signature:

```python
async def collect_active_theses(
    conn: asyncpg.Connection,
    as_of: date,
    market_ctx: MarketContext,
    underlying_snapshot: UnderlyingSnapshot,
) -> SectionResult: ...
```

### Snapshot composer algorithm

```python
def build_snapshot(
    sections: dict[str, SectionResult],
    market_regime: RegimeLabel,
    portfolio_value: PortfolioValue,
    affirmative_health_facts: list[str],
) -> Snapshot:
    # 1. Collect all SeverityItems across sections
    all_items = [item for sr in sections.values() for item in sr.items]

    # 2. Group by severity, count
    red = [i for i in all_items if i.severity == Severity.RED]
    yellow = [i for i in all_items if i.severity == Severity.YELLOW]
    green = [i for i in all_items if i.severity == Severity.GREEN]

    # 3. "One thing today" triage — pick from RED first, then YELLOW, by triage_priority
    one_thing = None
    candidates = sorted(red + yellow, key=lambda i: i.triage_priority)
    if candidates:
        one_thing = candidates[0]

    # 4. Affirmative health line (Part 3.5 non-negotiable)
    affirmative = build_affirmative_line(affirmative_health_facts, all_items)

    # 5. Time estimate (Part 3.5: 1min green, 3min yellow, 8min red, cap 60)
    minutes = min(60, len(green) * 1 + len(yellow) * 3 + len(red) * 8)

    return Snapshot(
        portfolio_value=portfolio_value,
        market_regime_line=format_regime_line(market_regime),
        red_items=red, yellow_items=yellow, green_items=green,
        affirmative=affirmative,
        time_estimate_minutes=minutes,
        one_thing=one_thing,
    )
```

### Severity functions (named)

From Part 2.3 / 3.5 / 4.4 / 5.4, eight specific rules I can name. Each lives in `asxos/domain/brief/severity.py` as a pure function.

```python
def severity_thesis_revisit_overdue(thesis: Thesis, today: date) -> Severity:
    """🔴 if revisit_due_at < today - 14 days, 🟡 if < today, 🟢 otherwise."""

def severity_thesis_approaching_target(thesis: Thesis, current_price: Decimal) -> Severity:
    """🟡 if current_price >= 0.90 * target_price, 🟢 otherwise."""

def severity_thesis_stop_breached(thesis: Thesis, current_price: Decimal) -> Severity:
    """🔴 if current_price <= stop_price, 🟢 otherwise."""

def severity_thesis_invalidation_breach(thesis: Thesis) -> Severity:
    """🔴 if any invalidation_condition.status == 'breached', 🟡 if any amber, 🟢 if all ok."""

def severity_underlying_diverging(thesis: Thesis, score: UnderlyingScore) -> Severity:
    """🔴 if score.weighted_score < -threshold, 🟡 if mixed (sign disagreement), 🟢 if confirming.
    Per Part 5.4: when underlying score is 🔴, the thesis also gets a 🟡 attention flag
    in snapshot count even if price-status is green."""

def severity_cgt_boundary(lot: HoldingLot, today: date, window: int = 30) -> Severity:
    """🟡 if 0 < days_to_eligibility(lot.acquired_at, today) <= window, 🟢 otherwise."""

def severity_allocation_cap(constraint_name: str, current: Decimal, limit: Decimal) -> Severity:
    """🔴 if current > limit, 🟡 if current >= 0.95 * limit, 🟢 otherwise."""

def severity_regime(regime: RegimeLabel) -> Severity:
    """🔴 for risk-off/disorderly, 🟡 for risk-on/narrowing or risk-off/orderly,
    🟢 for risk-on/broadening or neutral/mixed."""
```

### Section-health footer

`section_health.py` queries `job_runs` for each upstream job + a new `brief_section_runs` audit table (or `job_runs` extended with `section_name`):

```python
@dataclass(frozen=True)
class SectionHealthRow:
    section_name: str
    last_data: str       # "2026-05-31 close" or "live" or "run #142 (06:30 AEST)"
    status: Literal["ok", "stale", "errored"]

async def collect_section_health(conn, as_of, sections: list[SectionResult]) -> SectionResult:
    rows = []
    for section_name, source_job, freshness_target_days in SECTION_FRESHNESS_RULES:
        last_success = await conn.fetchval(
            "SELECT MAX(as_of) FROM job_runs WHERE job_name = $1 AND status = 'success'",
            source_job,
        )
        # ...classify ok/stale/errored, build row
```

### Partial-pipeline failure handling

| Section | Failure mode | Brief behaviour |
|---|---|---|
| 1 Wealth | DB unreachable | Hard-fail entire brief. |
| 2 Market context | `ingest_market_context` failed today | Section suppressed; footer shows "stale"; snapshot omits regime line OR shows yesterday's with "[stale]" tag. Decision: **show yesterday's with stale tag** — regime is too load-bearing for downstream sections to skip silently. |
| 3 Active theses | `theses` table empty | Section suppressed cleanly (M-Thesis-1 boots empty); brief still renders. |
| 4 Watchlist | (same) | Same. |
| 5 Underlying | `ingest_underlyings` failed | Section degraded — show last-known values with `[stale: N days]` annotation; underlying scores in s3 thesis cards show "data stale" instead of 🟢🟡🔴. |
| 6 New ideas | signal job failed | Section absent. |
| 7 Allocation | `build_portfolio` last run > 14d old | Section degraded — use simple direct query against `current_holdings` + `profiles` for caps. |
| 8 Theme | `themes` empty | Section absent. |
| 9 Tax & op | Always renders (pure on existing tables). | — |
| 10 Opp cost | No thesis near target | Section absent — that's the normal case. |

### Brief output destination

**Both:** stored in DB *and* emitted to Resend. A new `brief_runs` table for replay:

```sql
CREATE TABLE brief_runs (
    brief_id      BIGSERIAL PRIMARY KEY,
    as_of         DATE NOT NULL,
    composed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rendered_html TEXT NOT NULL,
    snapshot_json JSONB NOT NULL,
    section_runs  JSONB NOT NULL,    -- per-section state + error_message + freshness
    resend_message_id TEXT,
    UNIQUE (as_of)
);
```

Rationale: the "time estimate" learning rule (Part 3.5, "After 4 weeks of actual use: measured from when the user opened the email to when they ran `asx brief close`") needs persisted briefs. Also enables `asx brief replay <date>` for retros.

---

## Part F — Regime classifier design

### Decidable predicates from Part 4.2/4.3 indicators

For each regime, walking through one ("risk-on / narrowing"):

```python
# asxos/domain/regime/classifier.py

@dataclass(frozen=True)
class IndicatorSnapshot:
    asx200_close: Decimal
    asx200_5d_change_pct: Decimal
    pct_above_50d_ma: Decimal      # [0, 1]
    pct_above_200d_ma: Decimal
    breadth_advance_decline: Decimal
    net_new_highs_lows_10d: int
    avix: Decimal
    avix_5d_change_pct: Decimal     # e.g. 0.12 for +12% w/w
    avix_30d_band_pos: Decimal      # [0, 1]
    rba_cash_rate: Decimal
    aud_usd: Decimal
    aud_usd_30d_change_pct: Decimal
    aus_10y_yield: Decimal
    iron_ore_62fe: Decimal
    itraxx_or_us_hy_oas: Decimal | None
    itraxx_5d_change_bps: Decimal | None
    us_10y_2y_spread: Decimal
    sp500_trend_state: Literal["above_50ma", "between", "below_50ma"]
    vix: Decimal

@dataclass(frozen=True)
class Condition:
    name: str
    fired: bool
    value: str     # observed value as formatted string
    threshold: str

def classify_regime(snap: IndicatorSnapshot) -> tuple[RegimeLabel, list[Condition]]:
    rationale = []

    # Risk-on / narrowing predicate (Part 4.3):
    # Index rising AND breadth declining AND A-VIX creeping up
    cond_index_rising = Condition(
        name="index_rising",
        fired=snap.asx200_5d_change_pct > Decimal("0.005"),
        value=f"{snap.asx200_5d_change_pct:+.2%} w/w",
        threshold="> +0.5% w/w",
    )
    cond_breadth_declining = Condition(
        name="breadth_declining",
        fired=snap.pct_above_50d_ma < Decimal("0.55"),
        value=f"{snap.pct_above_50d_ma:.0%} above 50d MA",
        threshold="< 55%",
    )
    cond_avix_creeping = Condition(
        name="avix_creeping_up",
        fired=snap.avix_5d_change_pct > Decimal("0.05"),
        value=f"A-VIX {snap.avix_5d_change_pct:+.0%} w/w",
        threshold="> +5% w/w",
    )

    rationale.extend([cond_index_rising, cond_breadth_declining, cond_avix_creeping])

    if cond_index_rising.fired and cond_breadth_declining.fired and cond_avix_creeping.fired:
        return RegimeLabel.RISK_ON_NARROWING, rationale

    # ... fall through to the other regimes in order:
    # 1. risk-off / disorderly  (most severe — checked first)
    # 2. risk-off / orderly
    # 3. risk-on / broadening
    # 4. risk-on / narrowing
    # 5. neutral / mixed  (fallback)
```

**Order matters.** A snapshot can satisfy predicates for multiple regimes. The order from most-severe down ensures risk-off-disorderly wins over risk-on-narrowing when conditions overlap. **Document this in `.claude/rules/regime-conventions.md`** (new file).

### Rationale shape

A list of `Condition` dataclasses, serialized to JSONB in `market_context.regime_rationale`:

```json
[
  {"name": "index_rising", "fired": true, "value": "+2.1% w/w", "threshold": "> +0.5% w/w"},
  {"name": "breadth_declining", "fired": true, "value": "47% above 50d MA", "threshold": "< 55%"},
  {"name": "avix_creeping_up", "fired": true, "value": "A-VIX +12% w/w", "threshold": "> +5% w/w"}
]
```

The brief's section 2 renders this verbatim ("Rationale: ASX 200 +0.31%...; only 47%...; A-VIX +12% w/w from 13.4 to 15.0 (rising while index rises = late-cycle signal)").

### Missing-indicator handling

**Hard rule:** ASX 200 close, A-VIX, and at least one credit indicator (iTraxx OR US HY OAS) must be present. If any missing, `ingest_market_context` fails the job (hard-fail per CLAUDE.md #10) and the brief surfaces regime as "stale (yesterday: X)".

**Soft rule with explicit flag:** for iTraxx specifically, when unavailable, fall back to US HY OAS via FRED and write `regime_rationale` with an additional element `{"name": "credit_source_fallback", "fired": true, "value": "US HY OAS (iTraxx unavailable)", "threshold": "—"}`. This is **not** a silent fallback — the rationale array shows the substitution and the brief renders "Credit: US HY OAS 312bps (iTraxx unavailable — using US HY proxy)".

### Brief rationale surfacing

Per Part 4.4, in section 2 immediately below the regime label. Format:

```
Regime: 🟡 risk-on, narrowing breadth.

> Rationale: <comma-separated condition strings, in order they fired>.
```

### Worked walk-through (risk-on / narrowing, as in Part 7)

Input: ASX 200 +0.31% to 52w high; pct_above_50d_ma = 0.47; A-VIX +12% w/w.

1. Check `RISK_OFF_DISORDERLY`: A-VIX spiking (yes, +12% — but threshold is +30%), credit blowing out (US HY OAS +5bps — far below +50bps threshold), breadth collapsing (47% — below 30% threshold? no). → not disorderly.
2. Check `RISK_OFF_ORDERLY`: index falling (+0.31% — no, it's rising). → no.
3. Check `RISK_ON_BROADENING`: index rising (yes), breadth widening (no — 47% is below 55% and trending down), A-VIX low (15.0 is low absolute but +12% w/w is "creeping"). → no.
4. Check `RISK_ON_NARROWING`: index rising (yes), breadth declining (yes, 47% < 55%), A-VIX creeping (yes, +12% > +5%). → **MATCH**.

Output: `(RegimeLabel.RISK_ON_NARROWING, [cond_index_rising(fired=T), cond_breadth_declining(fired=T), cond_avix_creeping(fired=T)])`.

This matches Part 7's snapshot line verbatim. ✓

---

## Part G — Underlying attribution design

### Scoring function

Per Part 5.4 the score is "qualitative" but must be deterministic. Proposed pure function:

```python
# asxos/domain/underlyings/attribution.py

THRESHOLD_DIVERGING = Decimal("-0.020")   # -2% weighted-movement
THRESHOLD_CONFIRMING = Decimal("0.010")   # +1% weighted-movement
MIXED_SIGN_FRACTION_MIXED = Decimal("0.30")  # if ≥30% of weight pulls opposite direction, label MIXED

@dataclass(frozen=True)
class UnderlyingScore:
    label: Literal["confirming", "mixed", "diverging"]
    weighted_movement: Decimal
    components: list[ComponentMove]   # per-underlying for narrative ("lithium +4.2% w/w, iron ore +0.8%, AUD flat")

@dataclass(frozen=True)
class ComponentMove:
    underlying_code: str
    exposure: Decimal
    direction: Literal["positive", "negative"]
    move_5d_pct: Decimal
    contribution: Decimal   # exposure * sign(direction) * move

def score_thesis_underlying(
    thesis_underlyings: list[ThesisUnderlying],
    underlying_5d_moves: dict[str, Decimal],   # code → 5d % change
) -> UnderlyingScore:
    components = []
    weighted = Decimal("0")
    weight_with_neg_contrib = Decimal("0")
    total_weight = Decimal("0")

    for tu in thesis_underlyings:
        move = underlying_5d_moves.get(tu.underlying_code)
        if move is None:
            continue   # silently omit; surface in section-health if many missing
        signed = move if tu.direction == "positive" else -move
        contribution = tu.exposure * signed
        weighted += contribution
        total_weight += tu.exposure
        if contribution < 0:
            weight_with_neg_contrib += tu.exposure
        components.append(ComponentMove(...))

    # Mixed wins over diverging/confirming when signs disagree meaningfully
    if total_weight > 0 and weight_with_neg_contrib / total_weight >= MIXED_SIGN_FRACTION_MIXED \
            and weight_with_neg_contrib / total_weight <= (1 - MIXED_SIGN_FRACTION_MIXED):
        return UnderlyingScore(label="mixed", weighted_movement=weighted, components=components)

    if weighted <= THRESHOLD_DIVERGING:
        return UnderlyingScore(label="diverging", weighted_movement=weighted, components=components)
    if weighted >= THRESHOLD_CONFIRMING:
        return UnderlyingScore(label="confirming", weighted_movement=weighted, components=components)
    return UnderlyingScore(label="mixed", weighted_movement=weighted, components=components)
```

Thresholds are tunable; document defaults in `.claude/rules/underlying-conventions.md`.

### Window

**5 trading days** — confirmed by Part 5.4 ("+4.2% w/w") and Part 5.3 (the example shows w/w changes). 30-day changes are also shown but used for context, not scoring. **Recommendation:** compute both 5d and 30d on every underlying every day; use 5d for scoring (responsive to divergence); display 30d in section 5 for trend context.

### Stale warning handling

When `thesis_underlyings.last_validated_at` > 90 days for one or more underlyings of an open thesis, the brief surfaces it in **section 3** (the thesis card itself) as a sub-line:

```
Underlying: 🟢 confirming (lithium +4.2% w/w, iron ore +0.8%, AUD flat)
⚠ Underlying mapping last validated 127 days ago — `asx thesis revalidate-underlyings MIN`
```

Not in section 5 (which is about the underlyings themselves, not their mappings) and not in section-health footer (footer is about *data* freshness, not *mapping* freshness — different concept). Rationale: the user takes action per-thesis, so the warning lives where the user looks for that thesis.

A separate aggregate "5 thesis-underlying mappings need revalidation" line goes in section 9 (tax & operational) as a 🟡 reminder.

---

## Part H — Cross-layer observations design

### Function signature

```python
# asxos/domain/brief/cross_layer.py

@dataclass(frozen=True)
class CrossLayerObservation:
    title: str                  # one short clause for the headline
    detail: str                 # one or two sentences
    severity: Severity
    section_anchors: list[int]  # which sections this connects, e.g. [2, 3, 5]

def cross_layer_observations(
    market_ctx: MarketContext,
    theses_with_scores: list[tuple[Thesis, UnderlyingScore]],
    underlying_snapshot: UnderlyingSnapshot,
) -> list[CrossLayerObservation]:
    """Returns 0-3 observations. Hand-tuned rules for v1."""
    observations = []

    # Rule 1 (Part 5.5 confirming case): risk-on/broadening + most active theses confirming
    if market_ctx.regime == RegimeLabel.RISK_ON_BROADENING:
        confirming = [t for t, s in theses_with_scores if s.label == "confirming"]
        if len(theses_with_scores) > 0 and len(confirming) / len(theses_with_scores) >= 0.7:
            observations.append(CrossLayerObservation(
                title="Strong cross-layer confirmation",
                detail=(
                    f"Market regime broadening and {len(confirming)}/{len(theses_with_scores)} "
                    "active theses have confirming underlyings. The portfolio is sailing with "
                    "the wind; consider whether sizing is too conservative."
                ),
                severity=Severity.GREEN,
                section_anchors=[2, 3],
            ))

    # Rule 2 (Part 5.5 contradicting case): risk-on/narrowing + key thesis with weakening underlyings
    if market_ctx.regime == RegimeLabel.RISK_ON_NARROWING:
        for thesis, score in theses_with_scores:
            if score.label == "mixed":
                observations.append(CrossLayerObservation(
                    title=f"{thesis.symbol} sits in narrowing market with weakening underpinnings",
                    detail=(
                        f"{thesis.symbol} thesis sits in a narrowing market with weakening "
                        "commodity backdrop. Consider whether the thesis still warrants the "
                        "same position size."
                    ),
                    severity=Severity.YELLOW,
                    section_anchors=[2, 3, 5],
                ))
                break  # one per brief — don't drown the snapshot

    # Rule 3 (Part 5.5 divergence case): risk-off + portfolio still positive
    if market_ctx.regime in (RegimeLabel.RISK_OFF_ORDERLY, RegimeLabel.RISK_OFF_DISORDERLY) \
            and portfolio_perf.day_pct > Decimal("0"):
        observations.append(CrossLayerObservation(
            title="Portfolio outperforming a weakening market",
            detail=(
                "Portfolio outperforming a weakening market — is this defensive positioning "
                "by design or coincidence?"
            ),
            severity=Severity.YELLOW,
            section_anchors=[1, 2],
        ))

    # Rule 4 (Part 5.5 hidden risk case): risk-on + thesis price up + underlying diverging
    for thesis, score in theses_with_scores:
        if score.label == "diverging" and thesis_price_change(thesis) > 0 \
                and market_ctx.regime in (RegimeLabel.RISK_ON_BROADENING, RegimeLabel.RISK_ON_NARROWING):
            observations.append(CrossLayerObservation(
                title=f"{thesis.symbol} share price decoupled from fundamentals",
                detail=(
                    f"{thesis.symbol} is up while its underlyings diverge. The equity is "
                    "being held up by something other than fundamentals."
                ),
                severity=Severity.YELLOW,
                section_anchors=[3, 5],
            ))

    # Rule 5 (v1 extension): underlying breakout creates watchlist accelerant
    # Per Part 7 section 5: "Lithium breakout (+4.2% w/w, breaking 6m range) confirms MIN
    # thesis but also warrants attention on PLS workup..."
    for u in underlying_snapshot.movers:
        if u.is_breakout and u.move_5d_pct > Decimal("0.04"):
            watchlist_hit = find_watchlist_with_underlying(u.code)
            if watchlist_hit:
                observations.append(CrossLayerObservation(
                    title=f"{u.name} breakout — accelerate {watchlist_hit.symbol} workup",
                    detail=(
                        f"{u.name} breakout ({u.move_5d_pct:+.1%} w/w, breaking range) "
                        f"warrants accelerating {watchlist_hit.symbol} thesis drafting "
                        "before the entry window closes."
                    ),
                    severity=Severity.YELLOW,
                    section_anchors=[4, 5],
                ))

    # Cap at 3 (Part 5.5 spec)
    return observations[:3]
```

### Brief placement

Spec is ambiguous; my call: **section 5 dedicated subsection at the bottom**, plus the snapshot includes cross-layer observations of severity 🟡 or 🔴 in the count (they don't get their own line — they fold into the relevant section's count). Part 7 places one under section 5 ("Cross-layer observation: Lithium breakout..."), and section 10 narrates an opportunity-cost-driven observation — Part 7 thus implicitly supports placement *near the related sections*.

**Final design:** all cross-layer observations rendered in a labelled subsection at the bottom of section 5 ("Cross-layer observations"), AND if severity is 🟡/🔴, the observation contributes a `SeverityItem` to the snapshot count with `section_ref=5`. The user clicks through to s5 to see the detail. This keeps the snapshot honest (counts reflect everything that demands attention) while keeping the narrative coherent (the observation reads as part of the underlyings story).

---

## Part I — CLI surface design

### Current state (already implemented)

From `asxos/cli/main.py`:
- `asx predict` `asx signal` `asx import-holdings` `asx tax-view` `asx tax-action` `asx brief` `asx build-portfolio` `asx propose-trades`
- `asx model {activate,list}`
- `asx journal {add,list,review}`
- `asx profile {init,show,activate,list}` (gated by `_require_personal_use`)
- `asx portfolio {show,history,paper-review,signoff}` (gated)
- `asx news signoff` (gated)

### Proposed V2 additions

All gated by `_require_personal_use()`. All grouped under typer subapps for clarity.

```
asx thesis open <SYMBOL> --entry <LO-HI> --stop <X> --target <Y> --timeline <N>mo --themes <c1,c2,...> [--text "..."]
asx thesis show [<SYMBOL>]
asx thesis revise <SYMBOL> [--assumption "..."] [--target <Y>] [--stop <X>] [--reasoning "..."]
asx thesis exit <SYMBOL> [--redeploy interactive] [--override-boundary] [--reasoning "..."]
asx thesis list [--status active|watching|exited|expired]
asx thesis hold <SYMBOL> --reason "..."
asx thesis attach-underlying <SYMBOL> --underlying <CODE> --exposure <0.65> --direction positive|negative
asx thesis revalidate-underlyings <SYMBOL>

asx theme create <CODE> --name "..." --description "..." [--conviction low|medium|high]
asx theme show [<CODE>]
asx theme review <CODE> [--retire]
asx theme list
asx theme attach <CODE> --symbol <SYMBOL> --mechanism "..." --exposure 0.7

asx watchlist add <SYMBOL> [--from-idea <ID>] [--entry-band LO-HI] [--target Y] [--timeline NMo]
asx watchlist list
asx watchlist remove <SYMBOL>
asx watchlist trigger-check    # one-shot ad-hoc evaluation

asx idea list
asx idea dismiss <ID> --reason "..."
asx idea show <ID>

asx brief                      # already exists; default behaviour preserved
asx brief replay <DATE>        # NEW — replay a stored brief
asx brief close                # NEW — mark today's brief as read (feeds time-estimate learning)
```

### Verb compatibility check

The existing CLI uses imperative verbs (`init`, `show`, `activate`, `add`, `list`, `review`, `signoff`). Proposed V2 verbs (`open`, `revise`, `exit`, `hold`, `attach`, `create`, `dismiss`) are consistent — all imperative, all single-word. ✓

The one mismatch: `asx profile init` vs proposed `asx theme create` and `asx thesis open`. The existing pattern `profile init` is the outlier — recommend **keep both `init` and `create` as aliases for new noun subtypers**, but standardise on `open` for theses (the verb matches the user mental model — "I'm opening a position").

### Interactive flow: `asx thesis exit MIN --redeploy interactive`

The first interactive CLI in the codebase. Pattern:

```python
@thesis_app.command("exit")
def thesis_exit(
    symbol: str,
    redeploy: str | None = typer.Option(None, "--redeploy", help="interactive | cash | <SYMBOL>"),
    override_boundary: bool = typer.Option(False, "--override-boundary"),
    reasoning: str | None = typer.Option(None, "--reasoning"),
):
    _require_personal_use()
    if redeploy == "interactive":
        asyncio.run(_run_thesis_exit_interactive(symbol, override_boundary, reasoning))
    else:
        asyncio.run(_run_thesis_exit_direct(symbol, redeploy, override_boundary, reasoning))

async def _run_thesis_exit_interactive(symbol, override_boundary, reasoning):
    # 1. Show the exit summary (proceeds, CGT, net cash) — table render
    # 2. Show comparative redeployment candidates from opportunity_cost_scenarios
    # 3. For each candidate, prompt: [a]ccept, [s]kip, [q]uit?
    #    Use typer.prompt(...) or rich.prompt.Prompt.ask(...)
    # 4. On accept, write the redeployment plan to decisions journal and queue a thesis open
    # 5. Commit thesis exit + revision row in one transaction
```

**Rich** is already a dependency (`asxos/cli/main.py:15` `from rich.console import Console`). Use `rich.prompt.Prompt` for interactive flow — consistent with existing rich `Console` for output. The interactivity is **opt-in via `--redeploy interactive`** — the default `asx thesis exit SYMBOL` is non-interactive (just records the exit). This keeps CI/test paths non-interactive.

---

## Part J — Operational design

### New Render cron services

Add to `render.yaml`:

```yaml
  - type: cron
    name: asxos-ingest-market-context
    runtime: python
    region: oregon
    plan: starter
    branch: main
    buildCommand: pip install -e ".[ml]"
    schedule: "45 20 * * *"           # 06:45 AEST daily
    command: python jobs/ingest_market_context.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.13
      - key: ASXOS_PERSONAL_USE
        value: "1"
      - fromService: { type: web, name: asxos-api, envVarKey: DATABASE_URL }
      - fromService: { type: web, name: asxos-api, envVarKey: EODHD_API_KEY }
      - key: FRED_API_KEY
        sync: false                   # NEW — US HY OAS substitution
      - key: HEALTHCHECK_URL_INGEST_MARKET_CONTEXT
        sync: false

  - type: cron
    name: asxos-ingest-underlyings
    schedule: "48 20 * * *"           # 06:48 AEST daily
    command: python jobs/ingest_underlyings.py
    # ...same envVar pattern
    envVars:
      - key: HEALTHCHECK_URL_INGEST_UNDERLYINGS
        sync: false

  # Post-first-real-week:
  - type: cron
    name: asxos-evaluate-thesis-revisits
    schedule: "52 20 * * 0-4"         # 06:52 AEST weekdays
    command: python jobs/evaluate_thesis_revisits.py
    envVars:
      - key: HEALTHCHECK_URL_EVALUATE_THESIS_REVISITS
        sync: false
```

**Cadence rationale:**
- Market context daily (incl weekends) so the Monday brief catches Friday close + weekend macro.
- Underlyings daily — many underlyings (commodities) trade weekends elsewhere; even if no data updates, the job runs idempotently.
- Thesis revisits weekday-only — pure recomputation; no point running on days the brief doesn't fire.

Each cron needs a Healthchecks.io UUID provisioned at first deploy. Pattern is per `job-conventions.md`: `HEALTHCHECK_URL_<JOB>`. The UUIDs are set as `sync: false` env vars via `mcp__render__update_environment_variables`.

### Backup policy update

`scripts/backup_irreplaceable.sh` currently dumps `holding_lots`, `decisions`, `screening_rules`, `model_versions`, `profiles`. Per Part 6.9, the V2 irreplaceable additions are:
- `theses`
- `themes`
- `theme_holdings`
- `thesis_underlyings`
- `thesis_revisions`

Edit lines 44-49 of the script to add `--table=theses --table=themes --table=theme_holdings --table=thesis_underlyings --table=thesis_revisions`.

**Re-derivable tables (NOT backed up):** `underlyings`, `underlying_prices`, `market_context`, `opportunity_cost_scenarios`. Source data is EODHD/FRED + the regime classifier (pure function), so they reconstruct from re-running the ingest jobs over the date range.

### Migration ordering verification

Part 6.9 proposes:
1. `underlyings`
2. `underlying_prices`
3. `themes`
4. `theses`
5. `theme_holdings`
6. `thesis_underlyings`
7. `thesis_revisions`
8. `market_context`
9. `opportunity_cost_scenarios`

FK dependency check:
- `underlying_prices → underlyings` ✓ (after #1)
- `theme_holdings → themes (✓ #3), universe (existing)` ✓
- `theses → universe (existing)` ✓
- `thesis_underlyings → theses (✓ #4), underlyings (✓ #1)` ✓ (after #6)
- `thesis_revisions → theses (✓ #4)` ✓ (after #7)
- `opportunity_cost_scenarios → theses (✓ #4)` ✓

**One concern:** if M-Thesis-1 ships only migrations 3-5 and 7 (themes, theses, theme_holdings, thesis_revisions — i.e. without market_context or underlyings), then `asx thesis open` and `asx thesis show` work. M-Market-Context adds #8 (`market_context`), M-Underlyings adds #1, #2, and #6 (`underlyings`, `underlying_prices`, `thesis_underlyings`). The cross-cutting concern: **`asx thesis attach-underlying` requires `thesis_underlyings` which requires `underlyings`**. So M-Underlyings *must* land before users start attaching underlyings to existing theses. This isn't a problem if the milestone sequence in Part 8.2 holds — but it means M-Underlyings cannot be deferred relative to M-Thesis-1's CLI completeness. **Recommend:** M-Thesis-1 ships *without* `attach-underlying`; that command lands in M-Underlyings.

The migration sequence does NOT leave the DB in a state that breaks any existing job mid-deploy. The new tables are all greenfield; no existing job reads from them. The existing brief composer keeps working through the migration phase (V1 sections continue rendering); the V2 sections boot empty (suppressed) until data populates.

### Email module compatibility

`asxos/brief/email.py:24-40` `send_brief(html, as_of) → SendResult` takes an HTML string and a date. The V2 reshape produces HTML via Jinja (same as V1). **No refactor needed.** The new `Brief` dataclass + Jinja template replaces `BriefData` + `brief.html.j2` — `send_brief` is reused as-is.

The one thing worth adding: a `text_fallback` plain-text version. Resend supports it natively (`text=` kwarg in their SDK), and several email clients (Outlook on Windows, older Gmail mobile) render the plain-text version. For a brief this dense, the plain text is a meaningful fallback. Suggest adding in M-Brief-Reshape.

### REQUIRED_MIGRATIONS bump

Per `.claude/rules/api-conventions.md`: each new migration requires bumping `REQUIRED_MIGRATIONS` in `asxos/api/main.py`. The V2 plan adds 9 migrations, so the bump is +9. Spread across the milestones in the order they apply.

---

## Part K — Risk register

Architectural and operational risks (Part 9 of the spec covers product/strategy risks; these are distinct).

| # | Risk | Category | Mitigation | Owner |
|---|---|---|---|---|
| K1 | Symbol-format mismatch between spec examples (`MIN.AX`) and existing universe (`MIN.AU`) → FK joins silently miss | **BLOCKER** | Decide convention before M-Thesis-1; update spec Part 7; document in portfolio-conventions.md | James + system-architect |
| K2 | Brief composer rewrite (`asxos/brief/compose.py` → `asxos/domain/brief/`) is a >1000-line change spanning all sections | **BLOCKER** | Split M-Brief-Reshape into M-Brief-Skeleton (collector framework + existing sections migrated) and M-Brief-V2-Sections (new sections 2, 3, 5, 8, 10). | James |
| K3 | `cross_layer_observations()` placement underspecified; if not nailed down before M-Brief-Reshape, brief drifts from Part 7 visual spec | **BLOCKER** | Specify in this audit (Part H above): section 5 subsection + snapshot contribution. Add to spec changelog. | James |
| K4 | V1 `regime` classifier (`asxos/domain/signals/regime.py`) returns 3-label; signals layer consumes via `apply_regime_thresholds` (`ml-conventions.md`); V2 regime is 5-label — name collision risk | **PER-MILESTONE** (at M-Market-Context) | Keep V1 regime alive as `signals.regime` (bull/bear/neutral) for the threshold-override path; V2 regime lives in `domain/regime/` and is a *consumer* of indicators, never feeds the signal threshold logic. Document the two regimes' distinct purposes in regime-conventions.md. | James |
| K5 | FRED API rate limits / outage when iTraxx unavailable → market_context job silently degrades | **PER-MILESTONE** (at M-Market-Context) | The fallback is the documented degradation path — but it must surface in `regime_rationale` JSONB and in section 2 visibly, not silently. Test the fallback explicitly in the M-Market-Context test suite. | James |
| K6 | `thesis_underlyings.exposure` sums >1.0 if user attaches multiple underlyings without sum-check → score function over-weights | **PER-MILESTONE** (at M-Underlyings) | Add a check in `asx thesis attach-underlying` that raises if the resulting sum > 1.0. Add a DB CHECK constraint? Per-row CHECK can't enforce a sum; use a trigger or accept the soft constraint. **Recommend:** accept soft constraint + CLI validation, document in underlying-conventions.md. | James |
| K7 | `brief_runs` storage growth (1 row per day × HTML body) over 5 years = ~10MB; not a problem; but `snapshot_json` + `section_runs` JSONB grows | **WATCH** | Free-tier Supabase quota is 500MB. At ~50KB per brief × 1250 weekdays/5yr = 62MB. Acceptable. Add a `prune_brief_runs > 18 months` cron in 2027 if needed. | James |
| K8 | Theme retirement workflow undefined — `asx theme review CODE --retire` writes `themes.retired_at` but what happens to `theme_holdings` rows referencing the retired theme? | **PER-MILESTONE** (at M-Thesis-1) | Soft-retire: keep `theme_holdings` rows; brief's section 8 filters out themes with `retired_at IS NOT NULL`; thesis cards still reference the retired theme name with strikethrough. | James |
| K9 | Cross-layer observations rule set is hand-tuned (Part 5.5 explicitly says so); risk of rule sprawl as edge cases accumulate | **PER-MILESTONE** (at every brief-related milestone) | Cap rule count at 8 in v1. Each new rule requires a test case + a spec amendment. Move to ML in v3 per spec. | James |
| K10 | Single `RESEND_API_KEY` + `BRIEF_TO_EMAIL` — if Resend account is suspended (spam classification, billing), no brief delivery and no alert | **WATCH** | Add a `Healthchecks.io` ping inside `compose_brief.py` that only fires AFTER `send_brief()` returns successfully. Current implementation pings in `JobMonitor.__aexit__` regardless of `send_brief` outcome — verify. (Looking at `asxos/jobs/utils/job_monitor.py:112` — Healthchecks ping fires on success status, which is exit-code-based, so a Resend SDK failure WOULD raise and be caught as failure. ✓ — but worth re-verifying.) | James |
| K11 | No backfill story for `market_context` if `ingest_market_context` misses a day — regime classifier wants a trailing window (`pct_above_50d_ma`, `avix_30d_band_pos`) | **PER-MILESTONE** (at M-Market-Context) | The window is computed on each run from `prices` + `underlying_prices` history (which are independently sourced from EODHD bulk), so a missed `ingest_market_context` day just means that day's regime label is missing — next day's run produces a fresh label from current state. **No backfill needed.** Document this in market-context-conventions.md. | James |
| K12 | `theses.invalidation_conditions` JSONB has no schema enforcement — risk of free-form drift, breaks `severity_thesis_invalidation_breach` | **PER-MILESTONE** (at M-Thesis-1) | Define a Pydantic schema for `InvalidationCondition` in `asxos/domain/theses/types.py`. CLI validates before write. DB has a CHECK that fails if `jsonb_typeof(invalidation_conditions) <> 'array'`. | James |
| K13 | `asx thesis exit MIN --redeploy interactive` is the first interactive CLI — tests for interactive flows are fiddly | **WATCH** | Use `typer.testing.CliRunner` with `input="a\nq\n"` for stdin simulation. Three test cases: accept first, skip-then-quit, immediate quit. Acceptable test surface for the value delivered. | James |
| K14 | The 1473-line `asxos/cli/main.py` will become unmanageable with +5 V2 subtypers | **PER-MILESTONE** (at M-Thesis-1) | Split during M-Thesis-1 — extract existing subtypers (`profile`, `model`, `journal`, `news`, `portfolio`) into their own files in the same pass. Otherwise the V2 additions land on top of an already-overweight module. | James |
| K15 | `compose_brief` job timeout — current brief is small; V2 brief composes 10 sections with cross-section dependencies, network calls (EODHD via market_context isn't in compose path but underlyings might be) | **WATCH** | Render free tier cron has a 60-minute timeout. Estimate worst-case V2 brief at 30s. Pure DB reads on a ~50-row dataset. Not a real risk. | James |
| K16 | Watchlist trigger logic (Part 7 BHP example: "Entry confirmed when 20-day momentum positive AND iron ore 62% Fe >$118/t for 5 consecutive days") is not in the spec's data model — Part 6 has no `watchlist_triggers` table | **PER-MILESTONE** (at M-Thesis-1) | Watchlist is just `theses WHERE status='watching'`. The trigger is a structured field on `theses` itself, or a sibling `watchlist_triggers(thesis_id, condition_json, fired_at)` table. **Decision needed.** Recommend embedding in `theses.invalidation_conditions` reused as "entry conditions" when `status='watching'` (semantic overload — same structure for entering and exiting). | James |

---

## Part L — Milestone re-sequencing

The proposed sequence (M-Thesis-1 → M-Market-Context → M-Underlyings → M-Brief-Reshape → M-Snapshot → M-First-Real-Week) is **substantially sound** but needs three changes:

### Recommended sequence

| # | Milestone | Days | Notes |
|---|---|---|---|
| 1 | **M-Thesis-0 (NEW)** | 1 | Pre-flight: split `asxos/cli/main.py`. Add `asxos/domain/{theses,themes,regime,underlyings,brief}/__init__.py` placeholders. Decide symbol-format convention (K1). Update spec Part 7 with normalised symbols. |
| 2 | **M-Thesis-1** | 3-4 | Migrations 3, 4, 5, 7. CLI `asx thesis {open,show,revise,exit,list,hold}`, `asx theme {create,show,review,list,attach}`. No `attach-underlying` yet. |
| 3 | **M-Market-Context** | 2-3 | Migration 8. `asxos/domain/regime/`. `jobs/ingest_market_context.py`. FRED client. New cron in `render.yaml`. |
| 4 | **M-Underlyings** | 3-4 | Migrations 1, 2, 6. `asxos/domain/underlyings/`. `jobs/ingest_underlyings.py`. `asx thesis attach-underlying`. New cron. |
| 5 | **M-Brief-Skeleton (SPLIT-1)** | 2-3 | `asxos/domain/brief/` framework: `SectionResult`, severity functions, `composer.py`, `snapshot.py`. Migrate existing V1 sections (1, 7, 9 conceptually) to the collector pattern. Composer outputs identical brief to V1. **Behavioural-equivalence test** — V1 brief vs V2-composer brief must match for two weeks of historical data. |
| 6 | **M-Brief-V2-Sections (SPLIT-2)** | 3-4 | New sections: 2 (market context), 3 (active theses), 5 (underlying drivers), 8 (theme dashboard), cross-layer observations. |
| 7 | **M-Snapshot** | 1 | Snapshot composer, "one thing today" triage, time-estimate heuristic. Migration: `brief_runs` table. |
| 8 | **M-Opportunity-Cost-v1** | 2-3 | Promoted from "sequenced after first real week" to before — section 10 is referenced in the worked example. Migration 9. Crude comparative-redeployment surfacing (no Monte Carlo). |
| 9 | **M-First-Real-Week** | variable | Import holdings; open theses; receive briefs; document what's missing. |

### Changes from the original sequence

- **Added M-Thesis-0** (pre-flight): hygiene + symbol convention. Resolves K1, K14 before they bite.
- **Split M-Brief-Reshape into M-Brief-Skeleton + M-Brief-V2-Sections.** Per K2: the reshape is a structural change to all collectors, not a "add new sections" pass. M-Brief-Skeleton validates the framework against existing behaviour (the only behaviour available pre-V2); M-Brief-V2-Sections adds the new sections on top of a proven framework.
- **Promoted M-Opportunity-Cost-v1** from post-first-real-week to before. The worked example (Part 7 section 10) is part of the visual spec. First-real-week without section 10 doesn't match the spec.

### Dependency graph (updated)

```
M-Thesis-0
    ↓
M-Thesis-1 ────────────────┐
    ↓                        ↓
M-Market-Context        (CLI usable: open theses, name themes)
    ↓
M-Underlyings ──────────────┐
    ↓                        ↓
M-Brief-Skeleton          (data layer complete; can build briefs)
    ↓
M-Brief-V2-Sections
    ↓
M-Snapshot
    ↓
M-Opportunity-Cost-v1
    ↓
M-First-Real-Week (import holdings; open theses against each; one week of briefs)
    ↓
M-Thesis-Revisit-Engine, M-LLM-Thesis-Structuring, M-Theme-Stage-Detection, M-Theme-Adjacency (per spec Part 8.3)
```

Total revised estimate: **~7-9 weeks** to first-real-week, with the added milestone and the split. Within the spec's "6-8 weeks of focused work" envelope at the low end, slightly over at the high end. Recommend internalising the upper bound.

---

## Part M — What I am NOT certain about

Questions that the spec + codebase don't resolve. These are decision points for James.

**Status:** All 13 questions resolved 2026-05-28 in interactive session. Decisions are captured in `docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md` Part 12. Each question below is annotated with the **RESOLVED:** line that landed.

1. **Symbol format (K1).** Spec uses `MIN.AX`, codebase uses `MIN.AU`. Which wins? My recommendation: codebase convention wins (less code change). Confirm before M-Thesis-0.
   **RESOLVED (revised):** Codebase + EODHD convention wins: `.AU` for AU, `.US` for US. Original decision was `.AX` (override of architect recommendation), reverted after surfacing that EODHD API itself uses `.AU` and going `.AX` would require permanent translation wrappers on ~6 ingestion modules. Spec Part 6 and Part 7 examples corrected accordingly. M-Thesis-0 scope reduced.

2. **Watchlist data model (K16).** Is "watchlist" a separate table or just `theses WHERE status='watching'`? Spec Part 6 has no watchlist table; Part 2.2 and Part 7 treat watchlist as a distinct section. I think the elegant answer is the same table — but worth confirming.
   **RESOLVED:** Same `theses` table, `status='watching'`. No separate watchlist table. Per architect recommendation.

3. **`current_holdings` view + V2 brief section 1 (wealth state).** The V1 brief's section 1 is rudimentary (signal changes, mostly). The V2 brief's section 1 is rich (portfolio value, day change, benchmark comparison, attribution by symbol). The benchmark is ASX 200 TR — is this in `market_context.asx200_close` or is there a separate `benchmark_tr` source? EODHD has ASX 200 TR (XJOAT) but it's a paid endpoint. Need to confirm data source.
   **RESOLVED:** Compute TR from XJO (price-only, on current EODHD plan) + trailing dividend yield from ASX/RBA monthly stats. ±~10bps accuracy over a year — sufficient. No new paid endpoint.

4. **"YTD +250bps" framing.** YTD-vs-benchmark requires storing portfolio value daily (not just current). Is there a `portfolio_values` daily snapshot table I missed, or does this need a new migration? Looking at the schema — there is none. **Probable new requirement.** Recommend adding a `portfolio_daily_snapshots(as_of, capital_aud, holdings_market_value_aud, benchmark_tr_level)` table and a daily snapshot job (or integrate into `build_portfolio` even on non-rebalance days).
   **RESOLVED:** Add `portfolio_daily_snapshots` table + daily ~21:00 UTC job. Part of M-Thesis-0 scope. Per architect recommendation.

5. **`opportunity_cost_scenarios` recompute cadence.** Part 6.8 says "Recomputed weekly." Aligned with `build_portfolio` Sat 20:00 UTC? Or its own cron? My read: piggyback on `build_portfolio` since it has access to the candidate universe + signals already. Confirm.
   **RESOLVED:** Piggyback `build_portfolio` Sat 20:00 UTC. Per architect recommendation.

6. **Theme adjacency surfacing in section 8.** Part 7 section 8 shows "Adjacency suggestion: ai-infrastructure exposure is concentrated in chips. Adjacent categories you haven't considered: data centre REITs (GMG surfaced above)...". This needs *adjacency data* — but `themes` table has no `adjacent_themes` column. Is this a future-only thing (per Part 8.3 M-Theme-Adjacency), or does v1 need a manual `theme_adjacencies` table for the user to declare adjacencies? If the worked example is the visual spec, v1 needs *something* — even if it's a hand-edited `themes.adjacent_codes TEXT[]` column.
   **RESOLVED:** `themes.adjacent_codes TEXT[]` column added in M-Thesis-1 migration. User-edited via `asx theme adjacency add`. M-Theme-Adjacency (v2) layers LLM-assisted suggestions on top. Per architect recommendation.

7. **The "stage" classification for themes.** Part 6.2 enum: `early | early-institutional | broad-institutional | mainstream | late-retail | mature`. Who sets this in v1? The user, per `asx theme review`? Or is M-Theme-Stage-Detection (Part 8.3) the system that maintains it? Part 7 section 8 shows stages already populated. v1 must allow user-set; v2 augments with auto-detection.
   **RESOLVED:** **Auto-detect in v1.** M-Theme-Stage-Detection promoted from Part 8.3 to v1 build sequence (~3-5 days). Override of architect recommendation. Critical constraint: classifier outputs to `themes.stage_suggested`, never silent writes; user confirms via `asx theme stage CODE STAGE` which updates `themes.stage`. Brief reads user-confirmed `themes.stage` and surfaces divergence when `stage_suggested != stage`.

8. **The cross-layer observation in s10 narrative ("This comparison is not a prediction...").** Part 7 section 10 is heavily prose. Is the prose generated by a template (deterministic) or by an LLM (probabilistic)? Spec doesn't say. My read: template — the inputs are structured (gross proceeds, CGT, candidates ranked), so the prose is a Jinja template over them. LLM-driven prose is a clear v2 candidate but a v1 risk (hallucination). Confirm.
   **RESOLVED:** Jinja template over structured data. Fixed footer string for the "not a prediction" disclaimer. No LLM in v1 prose. Per architect recommendation.

9. **Spec contradiction in Part 6 vs Part 8.** Part 6.1 `theses.invalidation_conditions` has `{status: ok|amber|breached}`. Part 8.3 M-Thesis-Revisit-Engine says "Automated thesis-revisit triggers based on assumption changes (news, fundamentals, price moves, regime shifts)." How are the `invalidation_conditions.status` values *computed* before M-Thesis-Revisit-Engine ships? Manual via `asx thesis revise`? My read: yes — v1 is manual; the engine auto-computes. Document this in the M-Thesis-1 feature plan.
   **RESOLVED:** Manual via `asx thesis revise` in v1. M-Thesis-Revisit-Engine (Part 8.3) automates later. Per architect recommendation. To be documented in M-Thesis-1 feature plan.

10. **The "research" status for watchlist names (Part 5 + Part 9 "things to be careful of").** Spec says this is undefined. Same conclusion: `theses.status` adds `'research'` as a fifth value, semantically "drafted but no entry plan yet." Recommend adding it now to the enum so the migration isn't extended later. The Part 6.1 CHECK constraint becomes `CHECK (status IN ('research', 'watching', 'active', 'exited', 'expired'))`.
   **RESOLVED:** Added to enum in M-Thesis-1 migration. Per architect recommendation.

11. **Time-estimate learning (Part 3.5).** "After 4 weeks of actual use: measured from when the user opened the email to when they ran `asx brief close`." This implies an email tracking pixel for open-time and a CLI command for close-time. Open tracking requires Resend webhooks (Resend supports `email.opened` events). Is the user comfortable with this? It's a personal-system-only flow but worth confirming. Alternative: just track `asx brief close` time vs. `compose_brief` send time, ignore open-time. Simpler, less precise.
   **RESOLVED:** No Resend webhooks in v1. Track `asx brief close` timestamp vs. brief send timestamp only. Less precise but acceptable for personal system. Per architect recommendation.

12. **The brief's section 1 attribution ("MIN.AX +$1,420 — Lithium spot prices firmed on Albemarle production guidance cut...").** The narrative ties the day's P&L to a *news event*. This needs:
    - daily P&L per holding (computable from `prices` + `holding_lots`)
    - a relevant news item per holding (the `holding_news` table exists per M14a)
    - a join that says "this news drove this move" — which is *attribution*, hard to compute deterministically. v1 should probably just list news items for symbols that moved >1% and let the user infer the connection.
   **RESOLVED:** List `holding_news` items for any holding that moved >1% intraday. No causal claims. User makes the connection. Per architect recommendation.

13. **One worked-example detail in Part 7 that may be aspirational:** the BHP entry-band trigger ("Entry confirmed when 20-day momentum positive AND iron ore 62% Fe >$118/t for 5 consecutive days. Both met today."). This implies the system tracks *condition history* (5 consecutive days met). Need either a `condition_history` table or a stateful evaluator. The simpler v1: evaluate on every brief run; show "met today" without history. The history-bearing version is a v2 enhancement.
   **RESOLVED:** Rolling-window evaluator over `underlying_prices` on each brief run (no new history table). The "5 consecutive days" framing is honoured by querying the last 5 `underlying_prices` rows. **M-Trigger-Quality added to backlog:** future milestone introducing `trigger_fires` log table + daily scoring job + aggregation views to measure which triggers actually predict break-outs. Accepted cost: learning loop starts from zero history when it eventually ships.

---

## End of audit

This document is best read alongside the spec it audits. The Part A → Part L sequence mirrors the spec's natural reading order; Part M is the conversation list for the next strategy session.

Suggested follow-up: create individual `/feature-plan` artefacts for M-Thesis-0 and M-Thesis-1 once K1, K2, K3 (the three BLOCKERs) are resolved.
