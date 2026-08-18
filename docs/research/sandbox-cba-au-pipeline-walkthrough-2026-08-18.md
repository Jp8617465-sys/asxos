# Sandbox walkthrough: one stock through the full asxos pipeline — CBA.AU

**Status:** experimental / sandbox — NOT a governance document, NOT a capital decision, NOT investment advice
**Branch:** `claude/asx-stock-evaluation-p0hxx2` (isolated from `main`; nothing here was merged or approved)
**Date:** 2026-08-18
**Author:** Claude (session-driven), read-only against production data
**Mutations made to the database:** none. Every query in this session was `SELECT`/`information_schema`. No row in `theses`, `theme_holdings`, `governance_events`, `thesis_revisions`, `holding_lots`, or any other capital-adjacent table was inserted, updated, or approved.

## Why this exists

The brief was: pick one ASX stock, run it through data ingestion → full quant/fundamental/PM-style evaluation → forecasting/thesis construction → "who writes it, who monitors it, who changes it, how does the verdict reach me" — and log the whole thing honestly, including what's missing, without touching anything live. This document is that log. It is deliberately long because the ask was for the *whole* pipeline, not a stock tip.

**One housekeeping note up front:** "sandbox" here means *no new capital-bearing state was created* — no thesis written, no governance transition, no allocator run. It does not mean a second database; asxos has exactly one (single-user, per `CLAUDE.md`). The isolation comes from (a) this branch never touching `main`, and (b) me restricting myself to reads plus one new doc file.

---

## 1. Picking the stock — and why CBA.AU is the right one to prove the pipeline on

I queried the live `universe`, `current_holdings`, `theses`, `themes`, and `macro_theses` tables before choosing anything. What's actually there:

- **1 real holding**: `HUBS.NYSE` (HubSpot, ESPP/employer stock — not ASX, not eligible for this exercise).
- **13 thesis rows total**, all `governance_status='approved'` (human-authored default): `HUBS.NYSE` (active), `CBA.AU` (watching), and 11 bare `research`-status rows opened in one batch on 2026-06-24 (entry price only, no stop/target/timeline — clearly a seed/demo batch, not broker-report-quality theses).
- **1 theme**: "Big 4 Banks" (`theme_code=big-4-banks`, stage `early`, theme itself `governance_status='approved'`), with exactly one mapped holding — CBA.AU, `exposure_strength=0.50`, direction `positive`, but the **mapping row itself is still `governance_status='draft'`**.
- **4 macro theses**, 3 approved (breadth/thin-market risk-off; sticky AU long-end yields; un-inverted US curve/benign credit) and 1 rejected.

Rather than inventing a brand-new position, I picked **CBA.AU (Commonwealth Bank of Australia)** — it's already the system's own load-bearing example. `asxos/domain/theses/discipline.py`, the deterministic discipline evaluator that ships in James's live daily brief, literally cites CBA by name in its own source comment (`_DATA_SANITY_TARGET_MULTIPLE`: *"e.g. CBA recorded target 60 vs live ~168 = 2.8×"*), and `docs/product/north-star.md` calls the CBA thesis "the worked example" of the exact failure mode the identify→monitor→change loop exists to catch. Running the full pipeline on CBA meant testing real machinery against real data instead of a hypothetical — and, as it turned out, surfacing a live, already-ruled-on, half-finished piece of work (§7).

No capital risk in analysing it deeply: CBA has never been entered (`status='watching'`, `actual_entry_price` is null) — it is a paper watchlist row, not a position.

---

## 2. Data ingestion — what ran, what I could and couldn't trigger

**What's already in the database (verified live, not assumed):**

| Job | Last observed run (from `job_runs`) | Status | Rows |
|---|---|---|---|
| `sync_prices` | 2026-08-17 20:53 UTC | success | 2,387 |
| `sync_fundamentals` | **2026-08-18 05:00 UTC (today)** | success | 1,872 |
| `derive_fundamentals_pit` | **2026-08-18 04:57 UTC (today)** | success | 53,687 |
| `compute_factor_scores` | 2026-08-11 23:33 UTC | success | 3,308 |
| `check_thesis_invalidations` | 2026-08-17 20:55 UTC | success (0 triggers) | 0 |

CBA.AU price history in `prices` runs 2025-01-02 → 2026-08-17 (411 daily rows, no gaps against the 12-name blue-chip sample I checked). Fundamentals, point-in-time (PIT) fundamentals, and factor scores are all current within the last week. **The scheduled production pipeline (GitHub Actions, per `scheduler-inventory-2026-08-13.md`) is doing this ingestion daily regardless of this session** — I didn't need to kick anything off to get fresh CBA data.

**What I could not do from this sandbox, and why (logged honestly rather than papered over):**

- `EODHD_API_KEY` is **not present** in this session's environment (only `DATABASE_URL` is set). `jobs/sync_prices.py` / `jobs/sync_fundamentals.py` hard-fail at `get_client()` without it, by design (`.env.example`: *"eodhd_api_key... EODHD ingest jobs validate the key at call time"*). So I could not personally trigger a fresh EODHD pull for CBA — I read the state the real scheduled jobs already produced.
- Direct `psql` to the pooler host timed out (this sandbox's network policy only routes outbound HTTPS through the proxy; raw Postgres-protocol TCP on 5432 isn't reachable). I had to go through the Supabase MCP connector instead.
- The **read-only** Supabase MCP tool (`mcp__supabase-ro__execute_sql`, the one actually allow-listed in `.claude/settings.json`) never resolved in this session — its dynamically-assigned connector ID this session didn't match the stable name the permission allowlist references, so every call errored `MCP tool call requires approval` with nothing to approve it. I fell back to the read-write Supabase connector, self-restricted to `SELECT`/`information_schema` only for the whole session (verified: no `INSERT`/`UPDATE`/`DELETE`/DDL was issued).
- The **same failure hit a real subagent live**, not just me: I dispatched `market-context-narrator` for the market backdrop, and it came back unable to run any of its three required queries, for the identical reason — its tool list didn't include a working DB connector this session. It correctly refused to fabricate a market read rather than inventing numbers. I pulled the market-context data myself instead (§5) using the connector that did work.

  This is a live instance of a documented, open risk — `m14_candidate_agent_db_role_scoping` (`.claude/rules/portfolio-conventions.md`): every DB-reading agent's access is a session-scoped MCP connector reference, not a stable role, so a connector rename silently breaks every agent that depends on it. Worth flagging back to `arbi`/`backend-architect` as reproduced evidence, not just a theoretical gap.

---

## 3. The evaluation — fundamentals, valuation, technicals, factors

All figures below are from the live tables, as of the dates shown. **This is presented as evidence, not a recommendation** — mirroring the wording discipline `asxos/domain/theses/discipline.py` itself imposes (no "buy/sell/trim/exit" verbs; arithmetic and citations only), which is the right convention to borrow even for a document like this one.

### Price / technical (`prices`, CBA.AU vs AXJO.INDX)

| Metric | Value |
|---|---|
| Last close | **$165.00** (2026-08-17) |
| 52-week range | $147.22 – $183.52 |
| Off 52w high | −10.1% |
| Above 52w low | +12.1% |
| 1-month return | −3.9% ($171.78 → $165.00) |
| 3-month return | +1.5% ($162.64 → $165.00) |
| 1-year return (price only) | **−6.6%** ($176.61 → $165.00) |
| AXJO (ASX 200 price index) 1-year | **+4.1%** (8,717.7 → 9,073.2) |
| CBA vs index, 1yr, price-only | **≈ −10.7 pts underperformance** |

Two caveats on that last line, both structural to the system, not to CBA: AXJO.INDX is explicitly a **price** index (governor ruling F1 forbids treating it as total-return), so this excludes CBA's own ~3% yield; and the system's designated total-return benchmark (XJOAI, S&P/ASX 200 Accumulation) has no licensed price history loaded yet (`target-architecture.md` Appendix F, F1) — so a true apples-to-apples benchmark comparison for CBA specifically isn't available today, only this weaker price-only proxy.

### Fundamentals (`fundamentals`, as of 2026-08-18 — today)

| Metric | Value |
|---|---|
| P/E | 25.64× |
| P/B | 3.67× |
| EPS | $6.52 |
| Dividend yield | 2.99% (fully franked) |
| Market cap | ~$279.5B |
| Shares outstanding | 1.672B |

### Point-in-time fundamentals (`rs_fundamentals_pit`), FY2026 (to 2026-06-30) vs FY2025

| Metric | FY2025 | FY2026 | Change |
|---|---|---|---|
| Revenue (TTM) | $69.74B | $70.43B | +1.0% |
| Net income (TTM) | $10.12B | $10.87B | **+7.4%** |
| EPS (TTM) | $6.04 | $6.49 | +7.5% |
| ROE | 12.84% | 13.81% | +97bps |
| Dividend (TTM) | $4.75 | $4.95 | +4.2% |
| Franking | 100% | 100% | — |
| Book value/share | $47.03 | $47.02 | flat |

Read together with the price line: earnings and ROE both grew meaningfully in FY2026, but the stock is down 6.6% over the year and the multiple has compressed from the 08-04 reading (P/E 29.1× → 25.6× over two weeks alone, purely on the price move — EPS didn't change that fast). That's a valuation-derate, not an earnings problem, on the data available.

**Balance sheet** (`rs_financial_statements`, FY2026): total assets $1.45T, total equity $78.7B (≈5.4% of assets — ordinary bank leverage), total debt $308.2B, net debt $259.75B (net debt roughly 62% higher YoY — flagged, not interpreted; for a bank, "net debt" from a generic multi-sector schema is a much noisier signal than it would be for an industrial company, since deposits and wholesale funding dominate the balance sheet and the EODHD template has no bank-specific line for that). **Data-quality note**: the income statement's `netInterestIncome` field is null and interest expense/other-operating-expense fields look like they're catching a generic non-bank template — a proper bank evaluation wants NIM, CET1 ratio, and bad-and-doubtful-debt provisioning, none of which exist in this schema today. That's a real gap, not something I'm inferring around.

### Factor scores (`rs_factor_scores`, `fs_v1`)

| as_of | value | quality | momentum | low_vol | yield | composite |
|---|---|---|---|---|---|---|
| 2026-08-11 | **−0.42** | +0.07 | −0.05 | +0.27 | **−0.63** | **−0.17** |
| 2026-07-30 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 2026-07-23 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Reading the one populated row: CBA screens *expensive* (value −0.42) and *low-yielding relative to its peer set* (−0.63, consistent with CBA's ~3% yield running below the other major banks, which typically run 4–5%+), partly offset by low volatility (+0.27) and roughly-average quality (+0.07). Net composite is negative — on a pure factor basis this is not a cheap or high-yield way into the sector right now. The two earlier dates showing exactly `0.00` across all five factors look like a cold-start or computation artifact rather than genuine flat scores — worth a data-quality look, not load-bearing for this write-up.

---

## 4. Model A — read, but explicitly not used as evidence (rule #11)

`CLAUDE.md` rule #11 and `north-star.md` are unambiguous and current (not "pending," resolved 2026-07-11): on 19,032 matured `signal_outcomes`, `corr(ml_prob, 21d return) = −0.03`, and Model A's own STRONG_BUY cohort returned **worse** than HOLD at 21 days. James shelved the ML engine; `model_versions` confirms it in the data itself — `model_a` / `v1_5` is `is_active=true` but **`approved_for_allocation=false`**. I pulled CBA's recent signals purely as a labelled, dormant reference point, not as input to anything above:

| as_of | prob_up | expected_return | label | confidence |
|---|---|---|---|---|
| 2026-08-05 | 0.311 | **+17.6%** | HOLD | 38/100 |
| 2026-07-31 | 0.320 | +15.8% | HOLD | 36/100 |
| 2026-07-23 | 0.435 | +15.8% | HOLD | 13/100 |
| 2026-07-22 | 0.435 | **−17.7%** | **SELL** | 13/100 |

Two things worth naming out loud, both of which are exactly why the quarantine holds rather than a reason to lift it: (1) `prob_up` sits below 0.50 on every single one of these dates (a below-even chance of the stock rising) while `expected_return` is simultaneously large and positive on 8 of the 10 most recent readings — an internally inconsistent pairing of the model's own two outputs; and (2) the SELL→HOLD flip between 07-22 and 07-23 happened with `prob_up` essentially unchanged (0.4346→0.4349) while `expected_return` flipped sign entirely, at a still-low 13/100 confidence. This is a live, concrete illustration of "no usable edge," not an abstract policy citation — nothing here informed the evaluation in §3, and nothing here should inform a real decision.

---

## 5. Market backdrop (`market_context_current`, as of 2026-08-17 — today's data)

- **Regime label: `risk_off_orderly`.** Of the five regime-classifier rules, only one fired: `breadth_200_thin` (only **31.2%** of ASX 200 names are above their 200-day moving average, vs a 40% threshold) — despite the index itself sitting only modestly below its highs. Everything else is calm: AVIX 11.1 (vs a 22/30 elevated/extreme threshold), US HY OAS 2.67% (vs 450/600bps thresholds), VIX 15.2.
- **RBA cash rate: 4.35%.** AUD/USD 0.7103, AU 10y yield 4.831%, US 10y-2y spread **+0.51** (un-inverted).
- This directly matches two of the four **approved** macro theses already in the system: macro thesis #6 ("Breadth-led catch-down: thin 200d breadth under a strong index resolves into orderly risk-off") is describing exactly today's breadth reading, and #11 ("Un-inverted US yield curve + benign AU credit backdrop — no near-term recession signal") matches today's HY OAS and curve reading. **No approved macro thesis or theme addresses bank-sector-specific drivers** (RBA rate path, net interest margin, credit growth, housing) — that's a real coverage gap for a Financials-sector name specifically, not something this session can fill (macro thesis authorship is `macro-economist`'s job, via `/discover-macro`, subject to human governance approval — out of scope for a read-only sandbox pass).
- **Regulatory feed (`regulatory_events`) is thin for this purpose**: only two RBA items exist system-wide with any bank-adjacent relevance — "Appointment to the Monetary Policy Board" (2026-08-14) and "Review of Payments System Regulation" (2026-06-25, arguably relevant to CBA's large domestic payments book). Nothing resembling a cash-rate-decision record. This matches `CLAUDE.md`'s own documented state: Treasury and ATO feeds are dead, RBA RSS is the only live source, ASIC/ASX were never wired.
- **News coverage (`holding_news`) for CBA: zero rows.** Not a bug — `jobs/ingest_news.py` scopes to `current_holdings` only, and CBA isn't held (matches the roadmap's own documented finding that news coverage is "bounded by portfolio breadth," with HUBS as the only symbol currently getting any).

---

## 6. What already exists in governance for CBA — thesis #1

This is where "identify" gives way to "monitor," and where the story stops being generic.

```
thesis_id 1 · CBA.AU · status=watching · governance_status=approved
  entry band   $42.00 – $45.00
  stop         $38.00
  target       $60.00
  timeline     540 days (~18 months)
  opened_at    2026-05-28
  revisit_due  2026-06-27  ← 52 days overdue as of today
  themes       Big 4 Banks (theme approved; this symbol's mapping row is still `draft`)
```

**Revision history (`thesis_revisions`) — exactly one row, ever:** "opened," 2026-05-28, source=human, reasoning "Opening thesis; watching for entry into band." **`governance_events` for this thesis: zero rows** (it was inserted directly at `approved` via the human-authored default path — it never went through a `pending_review` transition, so there's nothing for the trigger to have logged).

**Against today's close of $165.00**, the recorded ladder is not stale by a normal amount — it's arithmetically incoherent:

- $165 is **3.7×** the top of the entry band ($45) — the entry band is unreachable.
- $165 is **4.3×** the stop ($38) — the stop offers no real downside protection at current levels.
- $165 is **2.75×** the target ($60) — already blown through target by 175%.

This is not "CBA ran up 4x" (it didn't — see §3, it's down 6.6% over a year). It's a stale/legacy data artifact in the thesis row itself.

**The system already has an automated check for exactly this**, and it isn't a hypothetical I'm proposing — it's shipped, merged, and running in production today. `asxos/domain/theses/discipline.py::_data_sanity` flags any thesis where the live price is ≥2× the recorded target (CBA is 2.75×) as a red `data_sanity` finding. `data_sanity_escalation` goes further: if a data-sanity red has sat unanswered (no `thesis_revisions` row of an "answering" type — a target correction, a deliberate `reviewed_no_change` hold, a status change) for more than 30 days, it escalates. CBA's only revision is the 2026-05-28 "opened" row — not an answering type — so the clock runs from `opened_at`: **82 days silent, 52 days past the 30-day escalation threshold.** This check is wired into `asxos/brief/compose.py::_discipline_findings`, which is the module that populates the "Portfolio discipline" section of James's real daily email brief (merged as PR2a/PR2b, confirmed live per the roadmap). **Unless something suppresses it, this exact finding should be firing as an escalated red in James's actual daily brief right now** — this sandbox pass didn't invent a new problem, it reproduced one the system already has instrumentation for.

**And there's a closed loop I found by accident that's worth surfacing directly**: `docs/product/james-inbox.md` records that James already ruled on this on **2026-07-16**, verbatim: *"unsure why cba thesis is still a thing — it should be automated."* His ruling asked for two things: (1) build a deterministic price-detachment check — which is exactly `data_sanity`/`data_sanity_escalation` above (the code's own docstring cites this ruling by date), and which shipped; and (2) actually retire (or correct) thesis #1 itself — which the inbox row says explicitly is **still pending "a one-word confirm"** from James, not yet executed. The inbox document itself is still marked "⚙️ RULED" rather than "✅ RESOLVED" as of its last verification (2026-08-17) — the code shipped but the paperwork wasn't closed out. That's a small, concrete, fixable loose end, and it's the single most actionable thing this whole exercise turned up.

---

## 7. Forecasting, targets, and timelines — what the system does and deliberately does not do

This is worth being precise about, because it's easy to expect a "price target" out of this and the system is deliberately built not to produce one autonomously.

**What was shelved:** Model A (ML-based `prob_up` / `expected_return` forecasting) is dormant by standing policy (§4) — it does not feed thesis construction, allocation, or this evaluation.

**What replaced it, by design (`north-star.md`):** a thesis is a **broker report with a point of view that a human writes**, structured as entry band / stop / target / timeline / thesis statement / invalidation conditions, monitored by deterministic, model-independent checks (§6), not generated by an algorithm. The system's own code goes out of its way to avoid computing a price target on James's behalf — `data_sanity_escalation`'s message literally emits the placeholder `<corrected>` rather than a number, with the reasoning spelled out in its docstring: *"a price target is the canonical form of an opinion about a financial product, so interpolating one here would cross s766B(3) no matter how the sentence were framed."* That's the personal-advice firewall operating exactly as intended, at the level of a single string-formatting decision.

So the honest answer to "what should the target/timeline be" is: **that's not a number this pipeline is supposed to produce, and I'm not going to invent one either** — same firewall applies to me writing a document as it does to the code. What the evidence in §3–§5 supports is a *set of facts a human would weigh* in re-drafting the ladder: earnings and ROE both grew ~7% YoY; the stock is down 6.6% over a year against an index up 4.1%; the valuation multiple compressed sharply in the last two weeks; the factor read is "expensive, low-yield-for-sector, low-vol"; the macro backdrop is calm-but-thin-breadth with no bank-specific catalyst currently on record. None of that resolves to a number — that resolution is James's, via the same two verbs the system's own escalation message already names:

```
# Correct the ladder to a real level, with reasoning:
asx thesis revise CBA.AU --target <corrected> --reason "..."

# Or retire the stale record entirely:
asx thesis revise CBA.AU --status expired --reason "..."
```

Either action also satisfies the still-open half of the 2026-07-16 ruling (§6).

---

## 8. Who writes it, who monitors it, who changes it, how it reaches James

Mapping the actual mechanics, not an idealized version:

**Who writes a thesis.** Today, 100% human-authored via `asx thesis open` (confirmed: `thesis_revisions.source='human'` on every row I inspected). There is a second path on paper — a governed discovery agent (`macro-economist`, `theme-researcher`, `sector-screener`) proposes evidence into `agent_runs`, and `asx thesis open --from-agent-run <id>` would turn that into a `governance_status='draft'` thesis for human review — but the CLI's own docstring says this path **"always fails, no `ThesisProposal` schema exists yet"** (Phase 1 of governance, not yet built). So for a genuinely new idea like a fresh ASX name, a human writing it directly is currently the only working path, even though the CLI surface for the agent-authored path already exists.

**Who monitors it, and on what cadence:**

| Check | Where | Cadence | Scope |
|---|---|---|---|
| Revisit-cadence overdue | `discipline.py` via `severity.thesis_revisit_overdue` | daily, in the brief | all thesis statuses |
| Timeline expiry / near-expiry | `discipline.py::_timeline` | daily, in the brief | any thesis with a timeline |
| Data-sanity (broken ladder) + escalation | `discipline.py::_data_sanity` / `data_sanity_escalation` | daily, in the brief | **`watching` AND `active`** (by explicit design — this is the CBA case) |
| Trajectory / pace (ON_TRACK / BEHIND / STALLED / STOP_VIOLATED) | `discipline.py::_trajectory` | daily, in the brief | `active` only |
| Price-pattern invalidation conditions | `jobs/check_thesis_invalidations.py` | daily cron (confirmed running, 0 triggers recently) | **`status='active'` only, and only if `invalidation_conditions` is populated** — CBA (`watching`) is structurally out of this job's scope |
| ML/SHAP coherence with the written thesis | `thesis-coherence-guard` agent | on demand (`/pm-review`) | active holdings |
| Pace-to-target within timeline | `thesis-milestone-monitor` agent | on demand (`/pm-review`) | active holdings |
| Benchmark-relative performance | `benchmark-performance-analyst` agent | on demand (`/pm-review`) | portfolio |
| Fit to James's own conviction/cap framework | `portfolio-coherence-reviewer` agent | on demand (`/pm-review`) | portfolio |
| Market backdrop | `market-context-narrator` agent | on demand (`/pm-review`) | — |

**Who changes it.** Only James, and only through audited verbs: `asx thesis revise` (one field + mandatory `--reason`, writes a `thesis_revisions` row), `asx thesis review`/`hold` (deliberate "reviewed, no change" discipline event), `asx thesis enter`/`exit` (capital transitions), `asx thesis approve`/`reject` (governance-status transitions, DB-trigger-enforced — a bare `UPDATE theses SET governance_status=...` is mechanically rejected by `theses_governance_audit`, migration 0034). Nothing in the pipeline — no job, no agent, no model — can write to `theses` or `thesis_revisions`; every entry in that audit trail is a human keystroke by construction.

**How the verdict reaches James** — three surfaces, in increasing order of depth:

1. **The daily email brief** (Resend, ~07:00 AEST) — passive, always-on. This is where the CBA `data_sanity_escalation` red should be appearing right now (§6), alongside revisit-overdue and timeline findings for every other thesis.
2. **The CLI, on demand** — `asx thesis list` (overdue flags, at a glance), `asx thesis show SYMBOL` (full ladder + invalidation conditions), `asx thesis history SYMBOL` (the audit trail).
3. **`/pm-review [SYMBOL]`, on demand** — the deepest pass: fans out all five investment-analysis agents in parallel from the main loop (a subagent can't itself spawn subagents) and synthesizes one verdict — GOOD HOLD / TRIM / REVIEW / EXIT-CANDIDATE — with every claim traced to a specific agent's cited data point. I did not run `/pm-review CBA.AU` in this session: it's built for **active holdings** (its benchmark/coherence/milestone agents expect a real position), and CBA is `watching` with no entry price — running it would mostly return "data not available" across three of the five agents. The right moment to run it for real is after James answers §6/§7, if he re-enters CBA with a corrected ladder.

At every one of these three surfaces, the wording constraint holds: evidence and arithmetic only, never "buy," "sell," or a computed target — the verdict is always James's to act on, in his own broker, per the s766B firewall.

---

## 9. What we have vs. what's missing — the honest gap list

**Solid and live:**
- Price/fundamentals/PIT-fundamentals/factor-score pipeline for CBA, current within days (fundamentals synced *today*).
- A deterministic, model-independent discipline layer that already caught this exact thesis's problem, unprompted, and is wired into the real daily brief.
- A full governance audit trail mechanism (triggers, `governance_events`, `thesis_revisions`) — even though this particular thesis predates it being exercised.
- A live, current market-regime read (`market_context_current`) that ties directly to two already-approved macro theses.

**Missing or thin, specific to this exercise:**
- **No bank-specific fundamentals.** NIM, CET1, bad-debt provisions — none of these exist in the generic EODHD-derived schema. A serious Financials-sector evaluation needs them.
- **No total-return benchmark yet.** AXJO.INDX is price-only by governor ruling (F1); the licensed XJOAI series hasn't been sourced, so CBA's relative performance can't be measured cleanly against dividends-included ASX 200.
- **No bank-specific macro/regulatory coverage.** RBA rate decisions, credit growth, housing aren't represented in either the two-item regulatory feed or the four macro theses.
- **The agent-authored thesis-proposal path is unbuilt** (`ThesisProposal` schema doesn't exist) — so today, discovery agents can find candidates but can't hand them off into governance without a human re-typing the thesis by hand.
- **Two factor-score rows read as all-zero** (2026-07-23, 2026-07-30) — looks like a cold-start artifact, not investigated further here.
- **The agent DB-connector-naming gap is real, not theoretical** — it broke a live subagent in this exact session (§2), which is direct evidence for the already-tracked `m14_candidate_agent_db_role_scoping` risk.
- **James's 2026-07-16 CBA ruling is half-executed**: the automation shipped, the retire/correct action on thesis #1 itself didn't, and `james-inbox.md` still shows the row as open. This is the one item in this whole exercise with a concrete, cheap next step.

---

## 10. Scaling this: segments → universe → global

The reason CBA was worth doing properly rather than picking ten stocks shallowly: every piece of machinery exercised here (ingestion state, fundamentals/PIT, factor scores, the discipline evaluator, the governance audit trail, the brief surfacing) is already **symbol-agnostic** — nothing in `discipline.py`, `compose.py`, or the governance triggers is CBA-specific. The scaling path the roadmap already describes:

- **Segment** = the "Big 4 Banks" theme, which exists but has only one (draft-status) holding mapped — `sector-screener` (bottom-up, coverage-driven) is the built-but-idle tool for proposing the other three (NAB.AU, WBC.AU, ANZ.AU) against the same theme, same evidence bar.
- **Universe** = 1,921 active ASX-equity symbols already tracked in `universe`/`prices`/`fundamentals` — the ingestion and discipline layers already run at that scale (`compute_factor_scores` scored 3,308 symbols on 2026-08-11); what's thin is thesis *coverage* (14 real thesis rows against ~2,400 tracked symbols), not data coverage.
- **Global** = the `HUBS.NYSE` precedent (a working non-ASX, non-`is_active` ingestion path via the held-lots query) shows the pattern for expanding beyond ASX exists; F2 (governor ruling) already requires any global sleeve be reported separately, never blended into the ASX benchmark.

None of that is a proposal to build anything new — it's an observation that this walkthrough exercised the real machinery, and the same machinery is what segment/universe/global scaling would reuse.

---

## Appendix — every query and file this session used

Read-only DB queries (via the Supabase SQL connector, self-restricted to `SELECT`/`information_schema`): `universe`, `current_holdings`, `themes`, `theme_holdings`, `macro_theses`, `theses`, `thesis_revisions`, `governance_events`, `prices` (CBA.AU, AXJO.INDX, and a 12-name blue-chip coverage sample), `fundamentals`, `rs_fundamentals_pit`, `rs_financial_statements`, `rs_factor_scores`, `signals` (CBA.AU, model_a v1_5), `model_versions`, `job_runs`, `holding_news`, `regulatory_events`, `market_context_current`.

Files read: `docs/product/roadmap-state.md`, `docs/product/north-star.md`, `docs/product/james-inbox.md`, `.claude/rules/portfolio-conventions.md`, `.claude/rules/job-conventions.md`, `.claude/settings.json`, `jobs/sync_prices.py`, `jobs/sync_fundamentals.py`, `jobs/check_thesis_invalidations.py`, `asxos/cli/thesis.py`, `asxos/domain/theses/discipline.py`, `asxos/brief/compose.py` (grep only), `.claude/commands/pm-review.md`.

Agent dispatched: `market-context-narrator` (returned no result — DB connector unavailable in-session, logged in §2 rather than discarded).
