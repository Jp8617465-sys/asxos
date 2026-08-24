# Daily Brief V2 — target architecture and section spec

**Status:** current (implementation-facing)
**Scope:** the production morning email (`asxos/brief/compose.py` → Resend) and its
staged rebuild. Not the arbi wake brief (`docs/product/rubrics/arbi-daily-brief.md`).
**Owner:** James (governor). Implementation may draft; it may not enact authority files.
**Last updated:** 2026-08-23
**Stage 0 code:** this document's companion PR (canonical template + `SectionResult` seam
+ integrity line). Stages 1–3 are specified here and **not** implemented in that PR.
**Does not replace:** `docs/product/north-star.md` (charter) or
`docs/product/target-architecture.md` (ratified engine). Those remain SoT. This file
is the SoT for *how the daily email is assembled, degraded, and sequenced*.

Historical strategy notes (`docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md`,
`docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md`, 2026-05-28) described a
signal-centric reshape, `asyncio.gather` on one connection, and a Render cron
fleet. They are **not** this spec. Where they conflict, this file wins.

---

## 1. Product role

The daily brief is the **experience layer** over an immutable decision, not the
decision itself (`north-star.md` reframe 2026-08-10; `target-architecture.md` §
brief-as-renderer). It exists so James can start the day knowing whether anything
requires a decision.

It is **model-independent by construction**. `asxos/brief/compose.py` reads no
`signals` / `shap_factors` / `prob_up` / `expected_return` / `signals.regime` and
never calls `resolve_production_model()`. Rule **#11** is standing policy, not a
flag: Model A (`v1_5`) has no usable edge on the 5d/21d horizons this system holds
for — `corr(ml_prob, 21d) = −0.03` on 19,032 matured `signal_outcomes`; STRONG_BUY
21d −0.09% vs HOLD +5.07% (`docs/model-a-decay-analysis-2026-07-11.md`,
`docs/product/ml-engine-shelf-2026-07-11.md`). The brief must **never** imply a
prediction, forecast, ranking, or trade instruction.

The live headline is a `ReviewOutcome` (`asxos/domain/review/status.py`):
`CLEAR` / `ATTENTION` / `BLOCKED` / `EVIDENCE_THIN`. That is a statement about
**evidence quality** over authored theses, holdings, price freshness and job
health. It is not a buy/add/trim/exit signal. `directive_terms()` exists so a
reintroduced ladder is testable.

Most days the correct brief is **nothing to do**. Alarm fatigue is the long-run
failure mode. Blocking the send is reserved for core inputs (snapshot / prices)
that are untrusted. News failing is not core: send with `MISSING`.

---

## 2. Target pipeline

### 2.1 Read-and-assemble, not a smarter composer

Today `collect()` (`asxos/brief/compose.py`) is a single `asyncpg` session with
sequential awaits (complete trading day → holdings count → max price date →
regulatory → job failures → news → portfolio → discipline → CGT boundary →
outcome). That shape cannot be "fixed" with `asyncio.gather`. asyncpg forbids
concurrent operations on one connection (MagicStack/asyncpg #56, #258 →
`InterfaceError`). **Do not** `asyncio.gather` on a shared connection.

The dark V2 composer (`asxos/domain/brief/composer.py`) already `gather`s Phase-2
collectors. Those collectors each call `acquire()` themselves, so they are not
sharing one connection — but they still live-compute at send time, still use a
different `SectionResult` vocabulary (`ok` / `degraded` / `suppressed` /
`failed` / `timeout` / `no_data` in `asxos/domain/brief/types.py`), and still
sit behind `ASXOS_V2_BRIEF_ENABLED` which is unset (KEEP-DARK,
`docs/product/dark-launch-exit-plan.md`, expiry 2026-09-30). Stage 0 does **not**
flip that gate and does **not** rewrite the dark tree.

**Target:** each upstream job writes a durable, timestamped **section artefact**
(gold table or equivalent). The composer **reads and assembles**. Staleness
becomes a stored `computed_at`, degradation is per-section, and tests do not
need a 66 KB god-module.

Medallion is a **discipline**, not a lakehouse:

| Layer | Meaning here | Machinery |
|---|---|---|
| Bronze | raw vendor payloads / job_runs | existing ingest jobs |
| Silver | validated facts (`prices`, `holding_lots`, `theses`, …) | existing Postgres |
| Gold | per-section artefacts the composer may trust | Stage 2 (out of this PR) |

No Spark, no Delta, no object-store layout. Stay on Supabase Postgres.

### 2.2 Orchestration stays GitHub Actions

Render cron was deleted 2026-08-12. The live substrate is
`.github/workflows/daily-brief.yml`:

- `cron: "30 20 * * 0-4"` — 20:30 UTC Sun–Thu = 06:30 AEST Mon–Fri.
- Steps are a **dependency graph**: prices → validate → snapshot → context →
  underlyings → regulatory → news → sentiment → **compose** → post-brief checks.
- A failed step blocks dependents. Post-brief steps run after send so they cannot
  cost the email.
- Honest GHA limits (already in the workflow comments): schedule jitter at busy
  hours; `schedule:` only fires from the default branch; public-repo workflows
  disable after 60 days of inactivity.

**Mitigations (specify, do not rebuild):**

- Keep **Healthchecks.io** dead-man pings via `JobMonitor`
  (`asxos/jobs/utils/job_monitor.py`). Success pings the URL; failure pings
  `/fail`; `blocked` does not ping. This is the correct answer to "did the brief
  run?", not a second orchestrator.
- 20:30 UTC is already off-peak relative to US-business-hours GHA congestion.
  A later Stage may shift to an off-round minute (e.g. `37 20`) — **spec only**.
- Do not introduce Airflow / Dagster / Prefect unless the asset graph has been
  large and stable for >12 months. It has not.

A connection **pool** is an acceptable *interim* if a future stage must overlap
independent reads. It is not the architecture. The architecture is
pre-materialisation. Stage 0 does not add a pool.

### 2.3 Typed contracts already in the repo (do not fork)

| Contract | Path | Role vs the daily email |
|---|---|---|
| `ReviewOutcome` | `asxos/domain/review/status.py` | Headline evidence-quality verdict. Keep as the health-report function. |
| Live `BriefData` | `asxos/brief/compose.py` | Today's email payload. Stage 0 adds `sections` onto it. |
| Dark V2 `SectionResult` / `Brief` | `asxos/domain/brief/types.py` | KEEP-DARK. Different status vocab. Do not mix into the live send path. |
| `EvidencePacket` → `DecisionBrief` | `asxos/domain/decision_engine/types.py` | Research-to-decision prototype (`mode: synthetic_prototype`). Not the morning email. Do not collapse the two. |

Stage 0 introduces a **live** `SectionResult` on the send path
(`asxos/brief/section.py`) with the four-state vocab below. A later stage may
retire the dark V2 type or adapt it; this PR does not.

---

## 3. `SectionResult` contract

```text
SectionResult
  name:         str          # stable id: prices, jobs, discipline, outcome, …
  status:       SectionStatus
  data:         object | None  # section payload; None when MISSING
  computed_at:  datetime | None
  source:       str          # "sql:prices.max(dt)", "fn:evaluate_discipline", …
  error:        str | None     # required when MISSING (and allowed on STALE)
```

`SectionStatus` is a closed `StrEnum`:

| Status | Meaning | Email behaviour |
|---|---|---|
| **FRESH** | Computed within the section's SLA, payload present | Render normally |
| **STALE** | Computed, but past freshness SLA (or unverified ingest) | Render with a visible STALE marker |
| **MISSING** | Collector failed or artefact absent | Render a MISSING marker; **do not omit** |
| **EMPTY** | Collector ran, genuinely nothing to report | Render the empty-state copy; **EMPTY ≠ MISSING** |

EMPTY is a successful quiet day. MISSING is "we could not look". Collapsing them
is the 2026-08 false-green news defect (`NEWS_QUIET` vs `NEWS_UNVERIFIED` in
`asxos/brief/compose.py`).

### 3.1 Four-state degradation

- **Blocking the send** (job non-zero, Healthchecks `/fail`, fallback email):
  reserved for **core** untrusted — the composer cannot open the DB, or **prices /
  the portfolio snapshot** are missing in a way that would make every number a
  fiction. Today's `JobMonitor` + `jobs/compose_brief.py` fallback path stays.
- **News fails → still send**, with the news `SectionResult` = `MISSING` (and the
  existing `NEWS_UNVERIFIED` body copy, which already refuses to claim a quiet
  day).
- A section `MISSING` / `STALE` / `EMPTY` **still renders** with the correct
  marker. Silence is not an acceptable degraded state (CLAUDE.md #10).
- Do not invent a fifth status. Map gated-off features (`NEWS_DISABLED`,
  portfolio gate) to **EMPTY** with `source` naming the gate, or omit them from
  the email body **as they already do** while still listing them on the integrity
  line.

### 3.2 Integrity / lineage line

Always present, above the fold. It is a **structural precondition**, not a
footnote.

Must include:

- prices as-of (`BriefData.data_as_of` / `latest_price_date`)
- other core inputs as-of when already collected
- per-section `SectionStatus`
- the **health-report function**: `ReviewOutcome.status` (`CLEAR` / `ATTENTION` /
  `BLOCKED` / `EVIDENCE_THIN`) as its own always-present line (today's header
  meta). Do not replace it; the integrity line sits beside it.

When a **core** input is `STALE` or `MISSING`, the integrity line is visually a
**warning** (banner / `integrity-warn` class), not `.footnote` grey. Today's
`review.unknowns` freshness banner is preserved; the integrity line is additional
lineage, not a substitute.

---

## 4. Engine inventory

Kind: **SQL** (query) · **FN** (deterministic function) · **ENG** (engine /
collector tree) · **EXISTS** · **DO NOT BUILD**.

| Engine | Kind | Status | Notes |
|---|---|---|---|
| Price completeness / `latest_complete_trading_day` | FN+SQL | EXISTS | `asxos/domain/prices/coverage.py`; core. |
| Holdings count / `current_holdings` | SQL | EXISTS | Live `collect()`. |
| Job problems since previous brief | SQL | EXISTS | `_job_failures`; `JobMonitor` writes `job_runs`. |
| Portfolio discipline | FN | EXISTS | `evaluate_discipline` in `asxos/domain/theses/discipline.py`. Isolated in `collect()`. |
| CGT 12-month boundary | FN | EXISTS | `days_to_eligibility` (`asxos/domain/tax/cgt.py`, spec §5.1 calendar arithmetic). Folded into discipline. Thin seam only. |
| Outcome vs benchmark | FN | EXISTS | `build_outcome_section` (`asxos/domain/benchmark/outcome.py`). Isolated; failure → `EVIDENCE_THIN`, not `BLOCKED`. |
| Regulatory hits on holdings | SQL | EXISTS | `regulatory_events`; RBA RSS only today. |
| Holdings news | SQL | EXISTS | Four `NewsStatus` states already. Sentiment is attribution, **not** a signal. |
| Portfolio adjustments | SQL | EXISTS | Gated `ASXOS_PERSONAL_USE` + `ASXOS_PORTFOLIO_BRIEF_ENABLED`. |
| `ReviewOutcome` classify | FN | EXISTS | Health-report function. Keep. |
| Inverse-vol weighting | FN | EXISTS (allocator) | `inverse_vol_weights` in `asxos/domain/portfolio/allocator.py`. **Defer reactivation as a brief section** to Stage 3. |
| Dark V2 collectors (wealth, theses, watchlist, themes, tax-ops, opportunity cost, underlyings, market context) | ENG | EXISTS, KEEP-DARK | `asxos/domain/brief/collectors/`. Re-scope model-independent; do not flip `ASXOS_V2_BRIEF_ENABLED` to clear a gate. |
| Regime classifier | ENG | EXISTS, not a forecast | `asxos/domain/regime/`. Must not be framed as a prediction. |
| Factor scores | ENG | EXISTS (research store) | `asxos/domain/research/factor_scores.py` writes `rs_factor_scores` for evaluation. **Do not surface as a brief forecast.** |
| Brinson attribution | — | DO NOT BUILD (V1) | No implementation. Stage 3+ only, after gold artefacts. |
| Model A / signals / SHAP | ENG | SHELVED | Quarantine. No brief section. Ever, until a **new** model passes a pre-registered decay bar **and** `approved_for_allocation`. |
| Sentiment-as-signal | — | DO NOT BUILD | `jobs/ingest_sentiment.py` may run; the brief must not treat sentiment as a trade input. |
| Forecast / expected-return section | — | DO NOT BUILD | No validated forecast exists. |
| Airflow / Dagster / Prefect | — | DO NOT BUILD | Stay on GHA. |
| Lakehouse / streaming | — | DO NOT BUILD | Medallion discipline only. |
| Interactive dashboard as primary | — | DO NOT BUILD | Email is v1; no v1 frontend (`north-star.md`). |
| Personalisation / gauges / inline SVG charts | — | DO NOT BUILD | Email constraints below. |
| `asyncio.gather` on a shared asyncpg connection | — | DO NOT BUILD | Use sequential awaits (Stage 0), artefacts (Stage 2), or a pool-per-task interim — never gather on one `conn`. |

**Prioritise in the email (when a section has something to say):** valuation / P&L
(outcome vs benchmark), concentration / sector-cap (discipline),
thesis-invalidation (discipline), CGT-boundary (discipline). Defer factor models
and attribution.

---

## 5. Information design

### 5.1 Principles

- **BLUF / inverted pyramid.** Decision first; context last.
- **Most days: nothing to do.** Quiet is success. Do not invent work.
- **Delta-oriented.** What changed since the previous brief beats a full dump.
- **Visible integrity** over more content. A short honest brief beats a long
  unverified one.
- **No prediction language.** No "likely", "expected return", "signal",
  "STRONG_BUY". `directive_terms()` is the testable ban.

### 5.2 Email constraints

The surface is Resend HTML consumed in mail clients.

- Layout: **tables + inline CSS**. No flex, no grid, no inline SVG.
- Sparklines: **Unicode block characters** (`▁▂▃▄▅▆▇█`), not canvas/SVG.
- Bars: **table-cell width + background-color**, not CSS `linear-gradient` as the
  sole encoding.
- Numbers with **deltas** (signed, tabular-nums), not gauges.
- Outlook / Word HTML engine quirks are real; a specific "Word EOL" date is
  **unconfirmed** — do not cite one.

### 5.3 Cadence map

| Cadence | What belongs |
|---|---|
| **Daily** | Integrity line, `ReviewOutcome`, discipline **exceptions**, CGT-boundary lots inside 30d, concentration breaches, news/regulatory (four-state honest), outcome vs benchmark if cheap |
| **Weekly** | Allocation vs caps (full), theme dashboard, opportunity-cost scenarios, watchlist |
| **Monthly** | Tax operational (franking / Div 296 reminders as **facts**, not advice), CGT harvest window |
| **Quarterly** | Contribution / attribution (Stage 3), factor commentary (only as research, never as a forecast) |

Daily email stays exception-shaped. Weekly/monthly material is linked or
folded below; it does not pad a quiet Monday.

### 5.4 Recommended above-the-fold structure (Stage 1+)

Specified here; **not** implemented in Stage 0 (Stage 0 preserves current section
order except the new integrity line).

1. **Integrity / lineage line** (warning chrome if core `STALE`/`MISSING`)
2. **Health-report function** — `ReviewOutcome` (already present)
3. **BLUF verdict** — one sentence: nothing to do / look at X / cannot look
   (`BLOCKED` / `EVIDENCE_THIN`)
4. **Exceptions only** — discipline findings that are not `info`
5. **Deltas** — what changed vs previous brief (Stage 1)
6. **Below the fold** — outcome table, regulatory, news, gated portfolio
7. **Linked static detail page** for full tables (Stage 1; email stays short)

---

## 6. Build plan

| Stage | What | This PR? |
|---|---|---|
| **0** | Live `SectionResult` seam on `collect()`; integrity/lineage line; one canonical Jinja template; golden snapshots; four-state markers. No BLUF reorder. No gold tables. No migrations. | **Yes** |
| **1** | BLUF reorder / inverted pyramid; delta-oriented "what changed"; linked static detail page. | **Yes (continuation of #175)** |
| **2** | Gold section artefacts (migrations); composer becomes read-and-assemble; optional pool as *interim* only. | Yes (stacked PR; 0047 applied 2026-08-24 by governor grant; this PR drops `brief_section_gold` from `EXPECTED_UNAPPLIED`) |
| **3** | Contribution analysis; inverse-vol as a brief section; Brinson; factors as research commentary. | No — deferred; several items are DO NOT BUILD for V1 |

Stage 0 is a **seam**, not a rewrite. `collect()` keeps returning `BriefData` so
every existing test and the Resend path keep working. `BriefData.sections` is the
hook later stages hang on.

---

## 7. Stage 0 implementation notes (this PR)

1. **`asxos/brief/section.py`** — live `SectionStatus` / `SectionResult`. Do not
   break dark V2 `asxos/domain/brief/types.py`.
2. **`collect()`** assembles a `dict[str, SectionResult]` sequentially on the
   existing connection. No `asyncio.gather`.
3. Failure isolation **only where already safe** for the send path:
   discipline, CGT-boundary, and outcome already catch. News is wrapped so a
   collector exception becomes `MISSING` + `NEWS_UNVERIFIED` body copy (send).
   Prices / holdings count / regulatory / jobs / portfolio still raise — those
   failures already fail the job; changing that would be a send-path behaviour
   change beyond Stage 0.
4. **Canonical template:** `asxos/brief/templates/brief.html.j2` (already renders
   discipline, outcome, four-state news, `ReviewOutcome`). Dark
   `brief_v2.html.j2` is archived under `templates/_archive/` so it cannot drift
   as a second live template. `decision_engine_prototype.html.j2` is a **different
   surface** (`DecisionBrief`) and stays put.
5. Golden snapshots under `tests/golden/brief/` with pinned `computed_at`.
   Degradation tests: `MISSING` / `STALE` / `EMPTY` still render with the marker.

`ASXOS_V2_BRIEF_ENABLED` stays unset. Half-built work stays on the branch; no
new feature flags.

---

## 8. Caveats (do not launder into facts)

- **Do not cite** an unverified "NN/g 55%" (or similar) figure for above-the-fold
  attention. No such measurement is in this repo.
- **Alarm-fatigue percentages** from other industries are analogical. Use them
  as design intuition, not as asxos telemetry.
- **Outlook Word rendering engine "EOL"** is unconfirmed. Constrain HTML because
  mail clients are hostile, not because of a dated rumour.

---

## 9. Explicit DO NOT BUILD

- Prediction / signal / Model A / SHAP / expected-return section
- Sentiment as a trade signal
- Orchestration platform (Airflow / Dagster / Prefect) now
- Lakehouse / streaming
- Interactive dashboard as the primary brief
- Personalisation
- Gauges / flex / grid / inline SVG
- Brinson attribution or factor models **in the V1 email**
- `asyncio.gather` on a shared asyncpg connection
- Flipping `ASXOS_V2_BRIEF_ENABLED` to "clear" the KEEP-DARK item
- Migrations (including `0042`) / production DB writes / Stage 2 gold tables
  in the Stage 0 PR

---

## 10. How to verify Stage 0

```bash
pytest tests/test_brief_section.py tests/test_brief_stage0.py tests/test_brief_compose.py tests/test_brief_composer.py tests/test_brief_v2_caveat.py -q
```

Expect: integrity line present; `FRESH`/`STALE`/`MISSING`/`EMPTY` markers render;
canonical template is `brief.html.j2`; `collect()` still returns `BriefData` with
the same email sections as before aside from the integrity line; no `signals`
query (existing `test_collect_never_queries_model_versions_or_signals`).
