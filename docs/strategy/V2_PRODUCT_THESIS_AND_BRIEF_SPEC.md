---
title: V2 Product Thesis & Brief Specification
location: docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md
status: working draft (locked for next milestone scoping)
auto_activate:
  agents:
    - system-architect
  skills:
    - feature-plan
review_cadence: at every milestone close; full review monthly during build
owner: james
last_updated: 2026-05-28
---

<!--
================================================================================
CLAUDE CODE — USE OF THIS DOCUMENT
================================================================================

This is the canonical strategic and product reference for the project as of
2026-05-28. It supersedes earlier positioning (SMSF-specific app, signal-
centric architecture). It is the authoritative source for:

  - What the product is
  - Who it's for
  - What "good" looks like (the worked example morning brief in Part 7)
  - What the data model needs to support
  - What the next milestones are, in what order

When working from this document:

  1. Invoke the `system-architect` agent for any architectural decision that
     touches the thesis-data-model, the brief composer, the regime classifier,
     or the underlying-attribution module.

  2. Invoke the `/feature-plan` skill before promoting any milestone listed in
     Part 8 from "planned" to "in progress." Each milestone needs a feature
     plan generated against it.

  3. Treat Part 7 (worked example morning brief) as the visual specification.
     If your design produces a brief that does not resemble Part 7, you have
     drifted from the spec. Surface the drift and ask before proceeding.

  4. Treat Parts 1-3 as immutable in this revision. Parts 4-10 are subject to
     refinement as implementation reveals constraints, but changes require
     explicit acknowledgement in the changelog at the bottom of this file.

  5. Memory drift notice: any prior session's `userMemories` block about this
     project may describe a stale incarnation (SMSF positioning, signal-
     centric architecture, 72-user state, Vercel frontend, 5,040 tests).
     THIS DOCUMENT is the current truth. Part 11 contains suggested memory
     edits to clear stale context.

If the routing layer does not auto-activate the above:

  /route
  /feature-plan @docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md

================================================================================
-->

# V2 Product Thesis & Brief Specification

Working name: TradeSight (placeholder; the name isn't the point yet)
Status: working draft, locked for next milestone scoping
Author: James, with strategic conversation 2026-05-28

## Table of contents

1. [Strategic thesis](#part-1--strategic-thesis)
2. [The morning ritual product](#part-2--the-morning-ritual-product)
3. [The snapshot](#part-3--the-snapshot)
4. [Market context layer](#part-4--market-context-layer)
5. [Underlying drivers layer](#part-5--underlying-drivers-layer)
6. [Data model](#part-6--data-model)
7. [Worked example morning brief](#part-7--worked-example-morning-brief)
8. [Build sequence](#part-8--build-sequence)
9. [Stress test](#part-9--stress-test)
10. [Open questions](#part-10--open-questions)
11. [Memory edits](#part-11--memory-edits)
12. [Changelog](#changelog)

---

## Part 1 — Strategic thesis

### 1.1 — One-sentence pitch

A morning briefing and trade-framework for serious DIY investors that consolidates the work they're already doing across half a dozen tabs into one calm, contextual practice — what you own, what you're watching, what your theses are doing, where the themes you believe in are heading.

### 1.2 — The wedge

**Trade theses with discipline around them.**

Not "BHP went up 2%." Not "here are 50 stocks matching your screen." A small number of opinionated, explainable, structured trade ideas, each with:

- Entry band (where we see value, as a range, not a number)
- Stop loss (where the trade is exited if wrong)
- Target price (what we're aiming for)
- Timeline (over what period)
- Thesis statement (why we believe what we believe)
- Theme attribution (which named theme this belongs to)
- Invalidation conditions (the structured set of facts that, if changed, mean the thesis is broken)
- Current path-vs-plan state (where we are on the journey)
- Opportunity cost framing (what else could this capital do)

This is not a feature. It is the product's emotional centre. The user evangelises this when it works.

### 1.3 — The three-layer moat

Three layers, in order of how defensible they are for a solo builder:

**Layer 1 — Integration with thought-process.** The morning ritual that thinks the way the user would think if they had three more hours. The competitor is the user's own spreadsheet plus three browser tabs, not Sharesight or Stock Doctor or Simply Wall St.

**Layer 2 — Discipline scaffolding.** Most DIY investors don't fail at picking — they fail at exit discipline. The platform captures every position as a structured thesis (entry/stop/target/timeline/invalidation conditions) and forces a deliberate revisit when any assumption changes. The competitor is the user's own willpower, which loses to confirmation bias every time. The system is a pre-commitment device.

**Layer 3 — Theme stewardship.** The user names themes they believe in; the system maintains the stock-to-theme mapping with explainable exposure strength, surfaces adjacencies, and tracks where each theme sits on a generalisation curve. Not "we identify themes before you" — "you identify themes, we systematise and stress-test them so you don't get caught at peak retail euphoria."

The combined moat is: **the user gets disciplined alpha-seeking that's faithful to their own thinking.**

### 1.4 — Who it's for

- DIY investor with $200k+ portfolio (enough that 0.5% optimisation matters, not so much they have a private banker).
- Has opinions and themes they believe in. The platform amplifies their own thinking; it doesn't replace it.
- Active enough to want discipline, not so active they want intraday tools.
- Already actively researching, just doing it inefficiently across multiple tools.
- Australian first (the tax engine is real differentiation; the regulatory framework is one James understands).
- Path A v1: James only. Path B v2: peers (single-figure handfuls, manual onboarding, no marketing).

### 1.5 — Why now

- LLM tooling makes structured thesis extraction from prose feasible (the user dictates a thesis; the system structures it).
- The combination of structured theses + LLM-assisted theme mapping + Australian tax engine does not exist as a single product anywhere in the market.
- Generalist tools (Bloomberg, Sharesight, Stock Doctor, Simply Wall St) treat the user as a data consumer. This treats them as an analyst with a thinking partner.
- Australian tax regime changes (Div 296, CGT discount reform) create active demand for tooling among serious DIYs.

### 1.6 — What's deliberately out of scope for v1

- Property and broader wealth aggregation (quarterly, long-term roadmap, not v1).
- Multi-user, multi-tenant (Path A is single-user James-as-user-id-1).
- Brokerage execution (manual execution by the user in their broker; the system surfaces, never trades).
- Mobile app (CLI + email brief is v1; web UI is v2).
- Real-time anything (daily-grain throughout).
- Auto-trading signals as the product (signals are inputs to thesis construction, never outputs).

---

## Part 2 — The morning ritual product

### 2.1 — Core principle

The product is the answer to three questions, every morning, in under five minutes on quiet days and 15-45 minutes on demanding days:

1. **What happened?** (Wealth, positions, market.)
2. **What's next?** (Watchlist, ideas, decisions surfaced.)
3. **Am I on course?** (Allocation, themes, theses tracking their plans.)

The product is a *practice*, not a tool. Tools are bought; practices are subscribed to.

### 2.2 — Section structure

The brief contains 8 numbered sections plus a snapshot at the top and a section-health footer at the bottom. Order is fixed; presence of each section is data-dependent (a section may be absent if it has no content).

| # | Section | What it answers |
|---|---|---|
| (top) | **Snapshot** | What needs my attention today, in one screen? |
| 1 | Wealth state | What did my portfolio do yesterday? |
| 2 | Market context | What regime are we in? |
| 3 | Active theses | Where are my open positions vs. their plans? |
| 4 | Watchlist | What is the system stress-testing for me? |
| 5 | Underlying drivers | What are the commodities/currencies/rates doing? |
| 6 | New ideas | What is the system suggesting I consider? |
| 7 | Allocation health | Am I still inside my structure? |
| 8 | Theme dashboard | Where are my named themes sitting? |
| 9 | Tax & operational | Anything time-sensitive? |
| 10 | Opportunity cost | When relevant (a decision surfaced in s3), what are the alternatives? |
| (footer) | Section health | Is anything stale or broken in the data pipeline? |
| (footer) | What this brief is asking of you | Priority-ordered list of decisions surfaced |

### 2.3 — Decision-surfacing prompts

Every section that surfaces a decision uses a consistent vocabulary of severity:

- 🟢 = informational, no action required, or action is optional and low-stakes.
- 🟡 = attention needed — a deadline approaches, an assumption has shifted modestly, a watchlist trigger fired, a cap is being approached.
- 🔴 = decision required today — a thesis is impaired, a stop has been breached, a cap has been exceeded.

Severity is **computed**, not assigned. Each rule is a pure function from data to severity. The rules live in `asxos/domain/brief/severity.py` (or wherever the brief domain lives) and are tested independently of brief rendering.

### 2.4 — Tone and language guidelines

The brief is a thinking partner, not a compliance officer.

- **Active voice, plain English.** "MIN approaching target" not "Threshold of target_price has been reached."
- **Show reasoning, not just conclusions.** Every decision-surfacing prompt explains *why* in one short sentence.
- **Calm by default.** Even on bad mornings, the language is even-keeled. The data does the work; the prose doesn't editorialise.
- **No financial advice language.** "The system has surfaced this for your review" not "We recommend you sell."
- **Affirmative health always present.** Every snapshot and every section includes at least one clause about what *is* OK alongside what isn't. This is non-negotiable (Part 3.5).

---

## Part 3 — The snapshot

### 3.1 — Design principles

The snapshot is the contract: if nothing in the snapshot needs you, you can close the email and get on with your day. Five design choices that make this work:

1. **Three numbers, one line.** Portfolio value + day change + benchmark comparison. The "am I OK?" answer.
2. **Coloured signal counts, not detail.** 🔴/🟡/🟢 with a count and a single-clause descriptor. The snapshot's job is "is there anything?", not "here's how to handle it."
3. **Severity ordering, not section ordering.** Red items first regardless of which section they live in. Snapshot is structured around the user's attention budget.
4. **One affirmative line about what's healthy.** Load-bearing — without it, the user checks each section anyway, defeating the snapshot's purpose.
5. **Two anchors at the bottom — time and triage.** "Estimated time to act" sets expectation. "If you only do one thing today" is the triage call when there are multiple competing demands.

### 3.2 — Quiet morning example

```
Portfolio $487,340 (+0.12%) · benchmark +0.08% · YTD +250bps

🟢 No decisions surfaced today.
🟢 Market regime: risk-on, broadening (no contradicting signals)

All theses tracking · all caps respected · cash at 5.0% floor · no operational issues

Brief below is informational. Estimated time to skim: ~3 minutes.
```

### 3.3 — Normal morning example (matches Part 7 worked example)

```
Portfolio $487,340 (+0.45%) · benchmark +0.31% · YTD +250bps

🟡 Market regime: risk-on, narrowing breadth (A-VIX +12% w/w)

🔴 1 thesis impaired (CSL — 52 days since revisit, assumption shifted)
🟡 2 theses need attention (MIN approaching target · NVDA CGT boundary in 18d)
🟢 1 watchlist entry triggered (BHP entered entry band)
🟢 1 new idea surfaced (GMG — ai-infrastructure adjacency)

All allocation caps respected · cash at 5.0% floor · no operational issues

Estimated time to act on all decisions: ~15 minutes.
If you only do one thing today: address CSL.
```

### 3.4 — Stress morning example

```
Portfolio $487,340 (−2.8%) · benchmark −1.4% · YTD +90bps

🔴 Market regime: risk-off, disorderly (A-VIX spiked +47%, credit blowing out)

🔴 Portfolio drawdown exceeded 2% threshold — see section 1
🔴 3 theses breached stop loss overnight (XYZ, ABC, DEF)
🔴 Materials sector cap exceeded (32% vs 30% limit)
🟡 4 other theses impaired by sector move

Cash position intact at 5.0% · defensive theses (CSL, COH) holding

This brief contains decisions that should be acted on today. Estimated time: 45-60 minutes.
Priority order: stops (s3) → cap breach (s7) → reassess remaining materials theses (s3).
Do not act on new ideas (s6) today.
```

### 3.5 — Implementation notes

These notes are load-bearing for the implementation. They should land in `.claude/rules/brief-conventions.md` when that file is created.

**The snapshot is generated last, not first.** It's a summary of what the rest of the brief found, not a separate query. Each section's collector returns both its rendered content and a structured `{severity, count, headline, section_ref}` tuple. The snapshot composer aggregates the tuples and orders them by severity. This keeps the snapshot honest — it can never drift out of sync with the sections below.

**Severity is computed, not assigned.** Pure functions from data to severity. Tested independently of rendering. Each rule documented inline with the function.

**The "one thing today" triage is a hard rule, not a vibe.** When ≥3 items are 🔴/🟡, the system picks one based on priority ordering:

1. Thesis impairments with overdue revisits
2. Stop-loss breaches
3. Allocation cap breaches
4. Market-regime-driven warnings (e.g. "risk-off disorderly" itself)
5. Opportunity-cost decisions
6. New ideas

The user can override the system's pick, but the system always has one.

**The estimated time should be calibrated, not invented.** First few weeks: hard-coded heuristic (1 minute per 🟢, 3 minutes per 🟡, 8 minutes per 🔴, capped at 60). After 4 weeks of actual use: measured from when the user opened the email to when they ran `asx brief close` or made their last action. Self-correcting estimate.

**The affirmative health line is non-negotiable.** Even on red mornings, the snapshot says what *is* OK alongside what isn't. "Cash position intact" on the stress morning above. This is the difference between a brief that informs and a brief that panics.

---

## Part 4 — Market context layer

### 4.1 — Why this layer

Every individual thesis decision is being made against a market regime. A 🟡 "MIN approaching target" decision means something very different if the market is in a calm uptrend with breadth widening versus if the market is at a 52-week high with breadth narrowing and credit spreads creeping wider. Same thesis, same prices, different decision.

Without a market context layer, the brief implicitly assumes "normal weather." That's the difference between disciplined investing and disciplined investing in a vacuum.

### 4.2 — Four dimensions

**Price and breadth.** The index level alone is misleading. ASX 200 up 1% with 80% of constituents up is broad strength; up 1% with 30% up is mega-cap distortion. Breadth indicators are the leading edge of regime change.

Indicators:

- ASX 200 level + daily change
- Advance/decline ratio
- Percentage of constituents above 50-day MA
- Percentage of constituents at 52-week highs vs. 52-week lows
- Net new highs minus new lows (running 10-day average)

**Volatility regime.** A-VIX (ASX 200 Volatility Index). Low and stable = risk-on, take theses at face value. Rising or spiked = risk-off, tighten stops. Crucially: A-VIX rising while index rises is a late-cycle warning; A-VIX falling from a spike is often a buy signal.

Indicators:

- A-VIX current level
- A-VIX 30-day band position
- A-VIX 5-day change
- A-VIX direction relative to ASX 200 direction (the divergence pattern)

**Macro backdrop.** Four numbers contextualise almost every Australian equity thesis.

Indicators:

- RBA cash rate (current + change since last RBA meeting)
- AUD/USD (current + 5d change + 30d change)
- Australian 10-year government bond yield
- Iron ore 62% Fe spot

Each with a one-line "what changed this week" annotation rather than raw values alone.

**Credit and global signal.** Credit conditions lead equity by 6-12 weeks historically. US matters because ASX correlation is meaningfully high and US is more liquid so often moves first.

Indicators:

- Australian iTraxx CDS index (or US HY OAS as proxy if unavailable)
- US 10y-2y yield curve spread
- S&P 500 trend state (above/below 50d MA, distance from 200d MA)
- VIX (US) for global volatility context

### 4.3 — Regime classifier

The load-bearing piece. Combines the four dimensions into a small number of named regimes that the brief uses to *modulate its tone and recommendations*.

| Regime | Conditions | Brief posture |
|---|---|---|
| **Risk-on / broadening** | Index rising, breadth widening, A-VIX low, credit tight, AUD stable | Permits new positions; can be assertive about ideas; standard stops |
| **Risk-on / narrowing** | Index rising but breadth declining, A-VIX creeping up | Warns: gains concentrated, late-cycle behaviour; prefer existing winners over new entries |
| **Neutral / mixed** | No clear signal | Defaults to position-level reasoning only; suppresses theme-level enthusiasm |
| **Risk-off / orderly** | Index falling, A-VIX elevated but stable, credit modestly wider | Suggests tightening stops, holding cash, not opening new positions; looks for dislocations not themes |
| **Risk-off / disorderly** | Index falling, A-VIX spiking, credit blowing out, breadth collapsing | Explicitly says "do not act on new ideas today"; re-examine existing positions only; consider whether stops should be moved further out to avoid forced selling |

The classifier is not perfect. It will be wrong sometimes. The user can override. But having a named regime in the brief every morning forces both system and user to be honest about context.

Implementation: rules-based v1. Each regime has a set of conditions expressed as Boolean expressions over the indicators. The classifier returns the regime label plus a structured `rationale` array of which conditions fired. The brief surfaces the rationale below the label so the user can audit the call.

### 4.4 — Where it surfaces in the brief

- **Snapshot:** one line, immediately after the wealth state line. "🟡 Market regime: risk-on, narrowing breadth (A-VIX +12% w/w)"
- **Section 2 (Market context):** full breakdown — four sub-blocks for the four dimensions, regime label at top with rationale, "what changed this week" annotations on macro indicators.
- **Thesis cards (Section 3):** when regime is risk-off or risk-on-narrowing, each thesis card adds a single line: "Regime context: late-cycle posture, consider whether sizing should be reduced."
- **New ideas (Section 6):** when regime is risk-off (either kind), new ideas are explicitly suppressed with a single line: "1 idea was identified but is suppressed by current market regime. Re-evaluate when regime classifier returns to neutral or risk-on."

### 4.5 — Data sources and freshness

- ASX 200, breadth, A-VIX: EODHD daily close.
- Macro indicators (cash rate, AUD/USD, bond yields, iron ore): EODHD where available; secondary sources where not.
- Credit indicators: Australian iTraxx is paid; substitute US HY OAS via FRED API (free).
- US indicators (S&P 500, VIX, US 10y-2y): EODHD.

Cron: `jobs/ingest_market_context.py` runs daily at ~20:45 UTC (before signal generation, so the regime classifier can feed into signal interpretation downstream).

Freshness gate: brief requires `market_context.as_of >= CURRENT_DATE - 2 trading days` or section 2 is suppressed with a stale warning in section health.

---

## Part 5 — Underlying drivers layer

### 5.1 — Why this layer

Equities are claims on underlying cash flows, and those cash flows depend on prices the equity doesn't directly reveal. For an Australian portfolio especially, the underlying commodities, currencies, and rates *are the story*. The equity is downstream.

The single most common pattern by which good trades become bad ones: the underlying changes before the price does, and discipline requires acting on the underlying. Detecting that divergence is the analytical edge that justifies a personal trading platform existing at all.

### 5.2 — What to track

**Resources commodities.** Directly drive ~25% of the ASX 200 by weight.

- Iron ore (62% Fe and 65% Fe spot)
- Copper (LME)
- Gold (USD/oz)
- Lithium carbonate (CIF China)
- Thermal coal (Newcastle 6000)
- Met coal (premium hard coking)
- Nickel (LME)
- Alumina / aluminium (LME)
- Uranium (U3O8 spot)

**Currency.**

- AUD/USD (headline)
- AUD/CNY (China-Australia trade link; often leading indicator for resources)
- AUD/EUR
- AUD/JPY
- DXY (US dollar index)

**Rates and curve.**

- Australian 2y, 5y, 10y, 30y government bonds
- The 10y-2y spread (curve shape — flattening from long end = recession warning; steepening from short end = reflation signal)
- RBA cash rate vs market-implied terminal rate from OIS

**Energy.**

- Brent crude
- WTI crude
- Henry Hub natural gas
- JKM (Japan Korea Marker for LNG) — matters specifically for Australian energy plays

**Agriculture.** Lower priority but worth having where Australian exposure is large.

- Wheat
- Beef (CME)
- Dairy

For each underlying: spot, 5-day change, 30-day change, 12-month band position, open interest if available, regime indicator (trending up / consolidating / trending down based on a simple structural rule).

### 5.3 — Thesis-level attribution

Each thesis in the `theses` table has commodity/currency/rate dependencies expressed as a structured field. Example:

```yaml
MIN.AX dependencies:
  - underlying: lithium_carbonate
    exposure: 0.65
    direction: positive  # MIN benefits when lithium rises
  - underlying: iron_ore_62fe
    exposure: 0.25
    direction: positive
  - underlying: aud_usd
    exposure: 0.10
    direction: negative  # MIN benefits when AUD weakens (USD-denominated revenue)
```

The mappings are hand-curated for v1 (LLM-assisted in v2). Each mapping has a `last_validated_at` timestamp. Mappings older than 90 days surface a warning to revalidate.

### 5.4 — The underlying score

Every morning, for each open thesis, the system computes a weighted score: how have the dependencies moved relative to the thesis's expectations?

The score is qualitative, not numeric. It produces one of three states:

- 🟢 **Confirming** — the weighted underlying movement is consistent with the thesis. Example: thesis predicts lithium recovery, lithium is up 4% w/w, AUD stable, iron ore stable. Score confirming.
- 🟡 **Mixed** — some dependencies are confirming, others are not. Brief surfaces which.
- 🔴 **Diverging** — the weighted underlying movement is against the thesis. Example: thesis predicts lithium recovery, lithium is down 7% w/w. Share price unchanged. Score diverging. *This is the divergence detection that justifies the layer.*

The score becomes a column on every thesis card:

```
MIN.AX — Mineral Resources
Entry $51.20 · Now $67.40 (+31.6%, day 247 of 540)
Underlying: 🟢 confirming (lithium +4.2% w/w, iron ore +0.8%, AUD flat)
```

vs.

```
MIN.AX — Mineral Resources
Entry $51.20 · Now $67.40 (+31.6%, day 247 of 540)
Underlying: 🔴 diverging (lithium −7.2% w/w; share price holding on technicals only)
```

When underlying score is 🔴, the thesis card also gets a 🟡 attention flag in the snapshot count, even if the price-based status is otherwise green. The user needs to know the equity is being held up by something other than fundamentals.

### 5.5 — Cross-layer interactions (market context × underlying)

This is where the analytical value compounds. Market regime and underlying score are not independent.

**Confirming case:** Risk-on / broadening market + iron ore in trend up + AUD stable + thesis underlying-score 🟢 = strong confirmation. Brief is permissive about adding to positions.

**Contradicting case:** Risk-on / narrowing market + iron ore rolling over + AUD weakening + thesis underlying-score 🟡 mixed = thesis sits in a market that *looks* fine but has weakening underpinnings. Brief explicitly calls this out: "BHP thesis sits in a narrowing market with weakening commodity backdrop. Consider whether the thesis still warrants the same position size."

**Divergence case:** Risk-off / orderly market + portfolio still positive = user has been lucky or is concentrated in defensive names. Brief asks: "Portfolio outperforming a weakening market — is this defensive positioning by design or coincidence?"

**Hidden risk case:** Risk-on market + thesis price up + underlying-score 🔴 = the share price has decoupled from fundamentals. Brief flags as 🟡 attention even if everything else looks fine.

These cross-layer observations are what makes the platform *think alongside the user*. Implementation: a `cross_layer_observations()` function that takes the market context, the thesis list with underlying scores, and produces 0-3 surfaced observations per brief. Hand-tuned rules for v1; ML-driven pattern detection deferred to v3+.

---

## Part 6 — Data model

These are the new domain objects that the V2 thesis requires. Schemas are illustrative; actual implementation should pass through `system-architect` review before migration is drafted.

### 6.1 — `theses`

One row per open or historical thesis. The core domain object of the system.

```sql
CREATE TABLE theses (
    thesis_id           BIGSERIAL    PRIMARY KEY,
    symbol              TEXT         NOT NULL REFERENCES universe(symbol),
    status              TEXT         NOT NULL,  -- watching | active | exited | expired
    entry_band_lower    NUMERIC(18,6),
    entry_band_upper    NUMERIC(18,6),
    actual_entry_price  NUMERIC(18,6),  -- set when status moves to active
    actual_entry_at     TIMESTAMPTZ,
    stop_price          NUMERIC(18,6) NOT NULL,
    target_price        NUMERIC(18,6) NOT NULL,
    timeline_days       INTEGER       NOT NULL,
    thesis_text         TEXT          NOT NULL,
    invalidation_conditions JSONB     NOT NULL DEFAULT '[]'::jsonb,
    -- Each condition: {description, type, threshold, status: ok|amber|breached, last_checked_at}
    themes              TEXT[]        NOT NULL DEFAULT '{}',
    opened_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ,
    last_revisited_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    revisit_due_at      TIMESTAMPTZ   NOT NULL,  -- system-set based on cadence + assumption changes
    CONSTRAINT theses_status_chk
        CHECK (status IN ('watching', 'active', 'exited', 'expired'))
);

CREATE INDEX idx_theses_status_revisit ON theses(status, revisit_due_at) WHERE status IN ('watching', 'active');
CREATE INDEX idx_theses_symbol ON theses(symbol, opened_at DESC);
```

### 6.2 — `themes`

User-named themes the user believes in.

```sql
CREATE TABLE themes (
    theme_id        BIGSERIAL    PRIMARY KEY,
    theme_code      TEXT         NOT NULL UNIQUE,  -- e.g. "ai-infrastructure"
    name            TEXT         NOT NULL,
    description     TEXT         NOT NULL,
    conviction_band TEXT         NOT NULL DEFAULT 'medium',  -- low | medium | high
    stage           TEXT         NOT NULL DEFAULT 'early',
    -- stage: early | early-institutional | broad-institutional | mainstream | late-retail | mature
    started_at      DATE         NOT NULL,
    retired_at      DATE,
    last_reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT themes_stage_chk
        CHECK (stage IN ('early', 'early-institutional', 'broad-institutional',
                         'mainstream', 'late-retail', 'mature'))
);
```

### 6.3 — `theme_holdings`

Mapping table linking themes to symbols with explainable exposure.

```sql
CREATE TABLE theme_holdings (
    theme_id        BIGINT       NOT NULL REFERENCES themes(theme_id),
    symbol          TEXT         NOT NULL REFERENCES universe(symbol),
    mechanism_text  TEXT         NOT NULL,  -- why this stock benefits from this theme
    exposure_strength NUMERIC(8,6) NOT NULL,  -- [0, 1]
    source          TEXT         NOT NULL,  -- user | llm_inferred | system_default
    last_validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (theme_id, symbol)
);

CREATE INDEX idx_theme_holdings_symbol ON theme_holdings(symbol);
```

### 6.4 — `thesis_revisions`

Append-only log of every change to a thesis. The audit trail that makes the discipline layer real.

```sql
CREATE TABLE thesis_revisions (
    revision_id     BIGSERIAL    PRIMARY KEY,
    thesis_id       BIGINT       NOT NULL REFERENCES theses(thesis_id),
    revised_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revision_type   TEXT         NOT NULL,
    -- opened | assumption_change | target_adjusted | stop_adjusted | timeline_extended
    -- | reviewed_no_change | exited | exited_by_stop | exited_by_target | expired
    diff            JSONB        NOT NULL,  -- before/after of changed fields
    reasoning       TEXT         NOT NULL,
    CONSTRAINT thesis_revisions_type_chk
        CHECK (revision_type IN ('opened', 'assumption_change', 'target_adjusted',
                                 'stop_adjusted', 'timeline_extended', 'reviewed_no_change',
                                 'exited', 'exited_by_stop', 'exited_by_target', 'expired'))
);

CREATE INDEX idx_thesis_revisions_thesis ON thesis_revisions(thesis_id, revised_at DESC);
```

### 6.5 — `thesis_underlyings`

Mapping table linking theses to commodities/currencies/rates they depend on.

```sql
CREATE TABLE thesis_underlyings (
    thesis_id       BIGINT       NOT NULL REFERENCES theses(thesis_id),
    underlying_id   BIGINT       NOT NULL REFERENCES underlyings(underlying_id),
    exposure        NUMERIC(8,6) NOT NULL,  -- [0, 1]; weights for one thesis should sum to ≤ 1
    direction       TEXT         NOT NULL,  -- positive | negative (thesis benefits when underlying rises/falls)
    last_validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thesis_id, underlying_id),
    CONSTRAINT thesis_underlyings_dir_chk
        CHECK (direction IN ('positive', 'negative'))
);
```

### 6.6 — `underlyings`

Master table of commodities, currencies, rates, and indices we track.

```sql
CREATE TABLE underlyings (
    underlying_id   BIGSERIAL    PRIMARY KEY,
    code            TEXT         NOT NULL UNIQUE,  -- e.g. "iron_ore_62fe", "aud_usd"
    name            TEXT         NOT NULL,
    category        TEXT         NOT NULL,
    -- commodity_resources | commodity_energy | commodity_agriculture | currency | rate | index
    unit            TEXT         NOT NULL,  -- usd_per_ton, ratio, percent, etc.
    data_source     TEXT         NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE underlying_prices (
    underlying_id   BIGINT       NOT NULL REFERENCES underlyings(underlying_id),
    as_of           DATE         NOT NULL,
    spot            NUMERIC(18,6) NOT NULL,
    open_interest   NUMERIC(18,6),
    PRIMARY KEY (underlying_id, as_of)
);

CREATE INDEX idx_underlying_prices_asof ON underlying_prices(as_of DESC);
```

### 6.7 — `market_context`

Daily snapshot of market-regime indicators.

```sql
CREATE TABLE market_context (
    as_of           DATE         PRIMARY KEY,
    -- Price + breadth
    asx200_close            NUMERIC(18,6),
    asx200_daily_change_pct NUMERIC(8,6),
    breadth_advance_decline NUMERIC(8,6),
    pct_above_50d_ma        NUMERIC(5,4),
    pct_above_200d_ma       NUMERIC(5,4),
    net_new_highs_lows_10d  INTEGER,
    -- Volatility
    avix                NUMERIC(8,6),
    avix_5d_change_pct  NUMERIC(8,6),
    avix_30d_band_pos   NUMERIC(5,4),
    -- Macro
    rba_cash_rate       NUMERIC(8,6),
    aud_usd             NUMERIC(10,6),
    aud_cny             NUMERIC(10,6),
    aus_10y_yield       NUMERIC(8,6),
    iron_ore_62fe       NUMERIC(18,6),
    -- Credit + global
    itraxx_or_us_hy_oas NUMERIC(8,6),
    us_10y_2y_spread    NUMERIC(8,6),
    sp500_trend_state   TEXT,  -- above_50ma | between | below_50ma
    vix                 NUMERIC(8,6),
    -- Computed
    regime_label        TEXT NOT NULL,
    regime_rationale    JSONB NOT NULL,  -- which conditions fired
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6.8 — `opportunity_cost_scenarios`

Cached forward-simulation results. Recomputed weekly.

```sql
CREATE TABLE opportunity_cost_scenarios (
    scenario_id     BIGSERIAL    PRIMARY KEY,
    thesis_id       BIGINT       NOT NULL REFERENCES theses(thesis_id),
    as_of           DATE         NOT NULL,
    alternative_symbol TEXT      NOT NULL,
    alternative_source TEXT      NOT NULL,  -- watchlist | cash | active_thesis
    expected_return_distribution JSONB NOT NULL,  -- {p10, p25, p50, p75, p90}
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (thesis_id, as_of, alternative_symbol)
);
```

### 6.9 — Migration ordering

Migrations should land in this order to satisfy FK dependencies:

1. `underlyings` (no dependencies)
2. `underlying_prices` (depends on `underlyings`)
3. `themes` (no dependencies)
4. `theses` (depends on `universe`)
5. `theme_holdings` (depends on `themes`, `universe`)
6. `thesis_underlyings` (depends on `theses`, `underlyings`)
7. `thesis_revisions` (depends on `theses`)
8. `market_context` (no dependencies)
9. `opportunity_cost_scenarios` (depends on `theses`)

Each table goes in its own migration file (no combined migrations) so individual changes can be rolled forward independently.

Backup policy: `theses`, `themes`, `theme_holdings`, `thesis_underlyings`, `thesis_revisions` are irreplaceable user data — add to `scripts/backup_irreplaceable.sh`. The rest are re-derivable.

---

## Part 7 — Worked example morning brief

This is the visual specification. Implementation that does not produce a brief resembling this on a typical day has drifted from the spec.

> **Note:** This is a *fabricated* example. Every name, price, and event is invented. It exists as a target visual format, not as factual market data.

---

### Morning brief — Tuesday 02 June 2026

*06:50 AEST · run #142 · 28 active theses · last data 31 May close*

---

#### At a glance

> **Portfolio $487,340 (+0.45%) · benchmark +0.31% · YTD +250bps**
>
> **🟡 Market regime: risk-on, narrowing breadth** (ASX 200 at 52w high, only 47% of constituents above 50d MA, A-VIX +12% this week)
>
> **🔴 1 thesis impaired** (CSL — 52 days since revisit, assumption shifted)
> **🟡 2 theses need attention** (MIN approaching target · NVDA CGT boundary in 18d)
> **🟢 1 watchlist entry triggered** (BHP entered entry band)
> **🟢 1 new idea surfaced** (GMG — ai-infrastructure adjacency)
>
> **All allocation caps respected · cash at 5.0% floor · no operational issues**
>
> *Estimated time to act on all decisions: ~15 minutes. If you only do one thing today: address CSL.*

---

#### 1. Wealth state

Portfolio **$487,340** (▲$2,180, +0.45% yesterday)
Benchmark (ASX 200 TR) **+0.31%** — outperformed by 14bps
YTD **+8.2%** vs benchmark **+5.7%** (+250bps)

Yesterday's movement attribution:

- **MIN.AX +$1,420** — Lithium spot prices firmed on Albemarle production guidance cut. Consistent with your "lithium oversupply unwinding" thesis (started Feb 2026, conviction held).
- **CBA.AX +$680** — Sector rotation into financials post-RBA hold. Not theme-attributed.
- **NVDA −$340** — Mild pullback after Friday's run. Within normal range; thesis unchanged.
- 12 other positions: net +$420.

Cash position: $24,310 (5.0% of capital, at floor). No deployment headroom without selling.

#### 2. Market context

**Regime: 🟡 risk-on, narrowing breadth.**

> Rationale: ASX 200 +0.31% to 52w high; only 47% of constituents above 50d MA (down from 64% a month ago); A-VIX +12% w/w from 13.4 to 15.0 (rising while index rises = late-cycle signal); AUD/USD stable; credit slightly tighter.

| Dimension | State |
|---|---|
| **Price & breadth** | ASX 200 7,825 (+0.31% day, +2.1% w/w, +6.4% YTD). Breadth weakening: 47% above 50d MA. 12 new highs vs 8 new lows. |
| **Volatility** | A-VIX 15.0 (+12% w/w). Below long-term average but trending up alongside index — late-cycle pattern. |
| **Macro** | RBA cash rate 3.85% (held last meeting). AUD/USD 0.658 (stable). Australian 10y 4.12% (+8bps w/w). Iron ore 62% Fe US$119/t (+2.5% w/w). |
| **Credit & global** | US HY OAS 312bps (+5bps w/w, modestly wider). US 10y-2y spread −18bps (still inverted). S&P 500 above 50d MA, +1.8% w/w. VIX 13.2 (low). |

**What this means for the brief today:** Late-cycle posture. New ideas surfaced with extra scrutiny. Existing winners preferred over new entries.

#### 3. Active theses — 3 require attention today

##### 🟡 MIN.AX — Mineral Resources — *thesis approaching target*

> *Lithium oversupply unwinds through 2026 as marginal Chinese capacity exits. MIN is best-positioned ASX pure-play with iron ore optionality through Onslow. Re-rate as spot lithium recovers above US$15k/t.*

| | |
|---|---|
| Entry band | $48–$53 (entered $51.20 × 800 = $40,960) |
| Stop | $42.00 (−18% from entry) |
| Target | $74 over 18m |
| Now | **$67.40** (+31.6%, day 247 of 540) |
| Timeline | 293 days to target deadline |
| Themes | lithium-oversupply-unwinding (primary), iron-ore-mid-cap (secondary) |
| Underlying | 🟢 confirming (lithium +4.2% w/w, iron ore +0.8% w/w, AUD flat) |

**What's changed:** Spot lithium carbonate +4.2% w/w. Albemarle cut 2026 production guidance (this is the kind of marginal-capacity exit your thesis predicted). Three of four invalidation conditions remain met; one (Chinese inventory drawdown) is borderline.

**Decision surfaced:** You're at 91% of target. Two paths:

- Hold to target — 9% upside, 293 days, IRR ~11% annualised assuming target hit.
- Exit now and redeploy — see Section 10 (opportunity cost).

##### 🟡 NVDA — Nvidia — *18-day CGT discount eligibility*

> *AI infrastructure spend is in mid-cycle, not peak. NVDA's data centre revenue compounds 40%+ for at least 6 more quarters. Re-rate driven by sustained gross margin defence.*

| | |
|---|---|
| Entry | US$132 × 60 shares (AUD cost base $11,840 @ 0.665) |
| Stop | US$108 |
| Target | US$210 over 24m |
| Now | **US$167.20** (+26.7%, day 347 of 730) |
| FX | AUD/USD 0.658 (cost basis FX gain +$210 since entry per Div 775) |
| Themes | ai-infrastructure (primary), advanced-semiconductors (secondary) |
| Underlying | 🟢 confirming (US 10y stable, advanced node capex trending up) |

**What's changed:** Q1 earnings beat (revenue +73% YoY, GM 75.3% — ahead of consensus). Theme momentum tracker now reads "late mid-cycle, broad institutional ownership." Watch for first signs of retail euphoria.

**Decision surfaced:** Largest lot reaches CGT discount eligibility in 18 days (20 Jun 2026). If you sell before then, ~$1,800 additional CGT exposure. System has automatically marked any sell signals as `hold` until 20 Jun unless you override. To force-sell anyway: `asx thesis exit NVDA --override-boundary`.

##### 🔴 CSL.AX — CSL Limited — *thesis revisit overdue (52 days)*

> *Behring division margin recovery through 2026 as plasma collection costs normalise. Vifor integration synergies underwrite EPS growth.*

| | |
|---|---|
| Entry | $268 × 50 (entered Jan 2026) |
| Stop | $245 |
| Target | $320 over 12m |
| Now | **$272.40** (+1.6%, day 138 of 365) |
| Themes | healthcare-defensive |
| Underlying | 🟡 mixed (USD strength helps; plasma cost index hasn't fallen) |

**What's changed since last reviewed (10 Apr):** Half-year results came in below your assumed margin trajectory (Behring margin 18.4% vs assumption 20.2%). Plasma collection costs flat, not declining. One of three invalidation conditions is now amber.

**Decision surfaced:** Thesis hasn't been touched in 52 days; a key assumption has shifted. Three options:

- `asx thesis revise CSL` — adjust assumption, recompute target, decide whether to hold
- `asx thesis exit CSL` — accept that the original thesis is impaired
- `asx thesis hold CSL --reason "..."` — explicit decision to hold with reasoning logged

The system will keep surfacing this every morning until one of these is done.

#### 4. Watchlist — 6 names, 1 entering trigger zone

##### 🟢 BHP.AX — entering entry band

| | |
|---|---|
| Entry band | $40.50–$43.20 |
| Current | **$42.80** (in band, 14d) |
| Draft thesis | Iron ore mid-cycle support from China stimulus + Pilbara unit cost leadership. Target $52 over 12m. |
| Themes (proposed) | iron-ore-rebound, australian-dividend-yield |
| Underlying | 🟢 iron ore in trend up; AUD stable |
| Trigger | Entry confirmed when 20-day momentum positive AND iron ore 62% Fe >$118/t for 5 consecutive days. Both met today. |
| Sizing | Suggested $18,500 (3.8% of capital) based on inverse-vol weighting and sector caps |

**Decision surfaced:** `asx thesis open BHP` to convert to active. Or `asx thesis adjust BHP --target 55 --timeline 18m` to customise first.

##### 🟢 Others on watchlist (no action today)

- **ANET** (US, ai-infrastructure adjacency) — outside entry band, $108 vs target entry <$98.
- **CEG** (US, ai-infrastructure power adjacency) — outside band, $245 vs entry <$210.
- **PLS.AX** (lithium pure-play) — in research phase, thesis not drafted. 23 days in workup.
- **JHX.AX** (US housing exposure) — thesis drafted but stop logic unresolved.
- **RIO.AX** (iron ore peer to BHP) — paused, considering whether BHP entry makes RIO redundant.

#### 5. Underlying drivers

**Resources & energy.** Iron ore 62% Fe US$119/t (+2.5% w/w, in trend up, 78% band position). Iron ore 65% Fe US$135/t. Copper US$4.62/lb (consolidating). Gold US$2,340/oz (+1.2% w/w). Lithium carbonate US$13,800/t (+4.2% w/w, **breakout above 6m range**). Brent US$78/bbl (consolidating). LNG (JKM) US$11.20/MMBtu.

**Currency.** AUD/USD 0.658 (stable, 60% band position). AUD/CNY 4.74 (modest weakening). DXY 101.2.

**Rates.** Australian 10y 4.12% (+8bps w/w). 10y-2y spread +52bps (steepening from short end, mild reflation signal). RBA cash 3.85%, OIS implied terminal 3.60% (one further cut priced over next 12m).

**Cross-layer observation:** Lithium breakout (+4.2% w/w, breaking 6m range) confirms MIN thesis but also warrants attention on PLS workup — the same catalyst affecting both. Worth accelerating PLS thesis drafting before entry window closes.

#### 6. New ideas — 1 surfaced for review

##### Idea: **GMG.AX (Goodman Group)** — proposed addition to watchlist

**Why surfaced:** Three signals converged in the last 5 trading days:

- Industrial REITs broke out of 6-month consolidation on data centre demand prints.
- GMG's quarterly update flagged data centre development pipeline at 4.0GW (was 3.4GW in Feb).
- Existing AI infrastructure exposure (NVDA + theme tags) lacks any data centre real estate component — adjacency gap.

**Theme attribution:** ai-infrastructure (adjacent, exposure_strength 0.35) — data centre REITs benefit from hyperscaler buildout but are second-order to chip/cloud names.

**Suggested draft thesis:** Entry band $32.50–$35.00, stop $29, target $42 over 18m. Predicated on data centre development pipeline executing and Australian industrial REIT cap rate stability.

**Regime note:** Market regime is risk-on / narrowing. New ideas surfaced with extra scrutiny today. Consider whether this is worth opening as a watchlist entry vs. waiting for regime to broaden.

**To act:** `asx watchlist add GMG --from-idea 891` to add to watchlist with this draft. Or `asx idea dismiss 891 --reason "..."` to record consideration and rejection.

#### 7. Allocation health

Within structure ✅ (all caps respected)

| Constraint | Current | Limit |
|---|---|---|
| Largest position (MIN) | 11.0% | 12% |
| Sector concentration (Materials) | 28% | 30% |
| Sector concentration (Tech, incl US) | 19% | 25% |
| Cash | 5.0% | ≥5.0% floor |
| Single-theme exposure (ai-infrastructure) | 22% | 25% |
| Leverage | 1.00× | ≤1.00× |

**Drift since last week:** Materials sector +1.2pp (MIN appreciation). No action required; watch if MIN continues running.

#### 8. Theme dashboard

| Theme | Stocks held | Exposure | Stage | Note |
|---|---|---|---|---|
| ai-infrastructure | NVDA, AVGO | 22% | **late mid-cycle** | Watch for retail euphoria signals. |
| lithium-oversupply-unwinding | MIN, PLS (watch) | 11% | early institutional | Thesis playing out per plan. |
| iron-ore-rebound | (none held; BHP entering) | 0% → 3.8% | early | New theme this quarter. |
| australian-dividend-yield | CBA, WBC | 14% | mature | Defensive carry, low conviction. |
| healthcare-defensive | CSL, COH | 9% | mature | CSL thesis impaired — see s3. |

**Adjacency suggestion:** ai-infrastructure exposure is concentrated in chips. Adjacent categories you haven't considered: data centre REITs (GMG surfaced above), power generation (CEG on watchlist), cooling/networking (ANET on watchlist, VRT not yet considered).

**Theme retirement candidate:** australian-dividend-yield has been on "mature" stage for 8 months; you've held conviction-neutral the whole time. Consider whether this is a theme or just a position group you haven't named. `asx theme review australian-dividend-yield`.

#### 9. Tax & operational

- 🟡 **NVDA CGT discount in 18 days** (see s3).
- 🟢 **CBA dividend ex-date 14 Jun** ($2.40/share fully franked = $720 cash + $309 franking credit on 300 shares).
- 🔴 **Loss harvest opportunity: COH** — currently $4,200 unrealised loss on the Mar 2026 lot. If exiting, FY26 tax benefit is meaningful. Note: TR 2008/1 wash-sale considerations apply if you rebuy within ~30 days. This tag is information only; user is responsible for ATO compliance on rebuys.
- 🟢 **Regulatory:** ASIC released updated guidance on Div 296 disclosure obligations 30 May (RG 271 update). No action required on holdings.

#### 10. Opportunity cost — surfaced because MIN approaching target

You're 91% to target on MIN with 293 days remaining. If you exit now at $67.40:

- Gross proceeds: $53,920 (cost base $40,960, gross gain $12,960)
- After CGT discount (held >12 months): estimated $9,720 net gain (37% marginal rate)
- Net redeployable cash: ~$53,000

**Comparative redeployment ranked by current attractiveness:**

1. **BHP** — sizing suggestion $18,500, would deploy ~35% of MIN proceeds. Diversifies sector concentration. Theme overlap minimal.
2. **GMG** — sizing suggestion $15,000 if converted to thesis. Adds ai-infrastructure adjacency. Theme stage early.
3. **Increase cash buffer to 12%** — keeps optionality. Currently at floor; redeploying part to cash protects against drawdown without conviction needed.

This comparison is *not* a prediction that BHP or GMG will outperform MIN. It's an enumeration of where capital could go if you choose to exit. The decision is yours.

To act: `asx thesis exit MIN --redeploy interactive` walks through redeployment with each candidate.

---

#### Section health (last successful ingest)

| Section | Last data | Status |
|---|---|---|
| Wealth state | 2026-05-31 close | ✅ |
| Market context | 2026-05-31 close | ✅ |
| Theses | live | ✅ |
| Watchlist signals | 2026-05-31 | ✅ |
| Underlying drivers | 2026-05-31 | ✅ |
| New ideas | run #142 (06:30 AEST) | ✅ |
| Allocation | recomputed 06:35 AEST | ✅ |
| Themes | last refresh 01 Jun 22:00 UTC | ✅ |
| Tax engine | up to date | ✅ |
| Regulatory ingest | 30 May 21:00 UTC | ✅ |

#### What this brief is asking of you, in priority order

1. **CSL** — make a thesis-revisit decision today (52 days, assumption shifted).
2. **MIN** — decide whether to hold to target or take the opportunity cost analysis seriously.
3. **NVDA** — be aware of the 18-day CGT boundary; don't sell before 20 Jun without explicit override.
4. **BHP** — entry band entered; convert from watchlist to thesis if you want to act.
5. **GMG** — review the new idea and either add to watchlist or dismiss.

*Total time to act on all 5: ~15 minutes.*

---

## Part 8 — Build sequence

### 8.1 — Demoted or cut from previous plans

The V2 reframe materially changes what's worth building next. The following are demoted, deferred, or cancelled:

- **M14c (news-aware allocator).** The composite-score sentiment integration was right under V1 (signal-centric). Under V2 (thesis-centric), news doesn't change the allocator's *score* — it changes whether *a thesis assumption has shifted*. M14c as drafted should not ship; the underlying work folds into "automated thesis-revisit triggers."
- **M14d (extrapolated sentiment for microcaps).** Same reasoning. The extrapolation effort was justified by "every name needs a sentiment score." Under V2, only names with active theses need that depth; everything else is screening.
- **M16 (news-driven investment discovery, as previously scoped).** Possibly absorbed entirely into theme stewardship; possibly killed. Revisit after the thesis layer ships.

### 8.2 — Immediate next milestones

The new top of the queue:

**M-Thesis-1 — Thesis data model and CLI.** ~3-4 days.

- Migrations for `theses`, `themes`, `theme_holdings`, `thesis_revisions`.
- `asx thesis open SYMBOL --entry LO-HI --stop X --target Y --timeline NMo --themes "..."`
- `asx thesis show [SYMBOL]`
- `asx thesis revise SYMBOL`
- `asx thesis exit SYMBOL [--redeploy interactive]`
- `asx thesis list [--status active|watching|exited]`
- `asx theme create CODE --name "..." --description "..."`
- `asx theme review CODE`

**M-Market-Context — Market regime classifier.** ~2-3 days.

- Migration for `market_context`.
- `jobs/ingest_market_context.py` running daily ~20:45 UTC.
- Rules-based regime classifier in `asxos/domain/regime/classifier.py`.
- Tests covering each regime label.

**M-Underlyings — Underlying drivers layer.** ~3-4 days.

- Migrations for `underlyings`, `underlying_prices`, `thesis_underlyings`.
- `jobs/ingest_underlyings.py` (EODHD-driven, secondary source for lithium carbonate).
- `asxos/domain/theses/underlying_attribution.py` — pure function from thesis + underlying snapshots to underlying score.
- `asx thesis attach-underlying SYMBOL --underlying CODE --exposure 0.65 --direction positive`

**M-Brief-Reshape — Morning ritual format.** ~3-5 days.

- Each section returns `(rendered_content, severity_tuple)`.
- New sections 2 (market context), 5 (underlying drivers), 8 (theme dashboard).
- Reshape sections 3 (active theses) and 4 (watchlist) to thesis-card format.
- Section health footer.

**M-Snapshot — Snapshot composer.** ~half a day to one day.

- Builds on the section tuples produced by M-Brief-Reshape.
- Severity ordering, affirmative health line, time + triage anchors.

**M-First-Real-Week — Import holdings and live the ritual.** Variable.

- Import real positions via `asx import-holdings`.
- Open theses for each (using `asx thesis open` on each held name).
- Receive briefs daily for one week.
- Document what's missing, broken, or noise.

### 8.3 — Sequenced (after first real week)

- **M-Thesis-Revisit-Engine.** Automated thesis-revisit triggers based on assumption changes (news, fundamentals, price moves, regime shifts). ~3 days.
- **M-LLM-Thesis-Structuring.** Dictate a thesis as prose; LLM structures it into the `theses` schema. ~3-4 days.
- **M-Opportunity-Cost-v1.** Simple comparative redeployment surfacing (no Monte Carlo). ~2-3 days.
- **M-Theme-Stage-Detection.** Crude rules-based theme stage classifier from news volume + sentiment + price action. ~2-3 days.
- **M-Theme-Adjacency.** LLM-assisted suggestion of adjacent themes to ones the user holds. ~2-3 days.

### 8.4 — Estimated total

From "V2 thesis locked" to "morning ritual on real data for one week": **6-8 weeks of focused work.**

This is substantial. The discipline is to ship each milestone and live with it for at least a few days before opening the next. The forcing function is the first-real-week milestone — the spec is unfalsifiable until briefs are landing in James's inbox with his actual holdings driving them.

---

## Part 9 — Stress test

Five attack vectors on the V2 thesis. Each comes with a mitigation. None invalidates the thesis; all should shape how it ships.

### Attack 1: The discipline layer is the right product, but the user doesn't want it

Most DIY investors who *say* they want discipline don't actually use the systems they buy for it. The system that asks "your thesis said you'd exit at $X — you're at $X — what's your reasoning for holding?" is the system that gets uninstalled because it makes the user feel bad.

**Mitigation:** The discipline scaffolding has to feel like *thinking partner*, not *compliance officer*. Tone of voice matters more than feature set. The brief's "calm by default" rule (Part 2.4) and "affirmative health always present" rule (Part 3.5) are the structural defences. Test this with one real user before scaling.

### Attack 2: Theme stewardship is a feature, not a product

Every brokerage dashboard will build "themed portfolios" in the next 18 months because LLM-driven theme mapping is becoming commodity. Theme dashboard alone might be best-in-class today and table-stakes in 2027.

**Mitigation:** The theme layer is more defensible *combined with* the structured thesis layer than alone. "We map your themes" is a feature. "We track where your theses on those themes are at, force discipline around them, and surface opportunity cost when you're tempted to break your own rules" is harder to copy because it requires the integrated data model. Defend with depth, not feature breadth.

### Attack 3: Trade theses become an engagement metric, not an outcome metric

Risk pattern: user writes 30 theses in week one, revisits none, system surfaces 30 stale theses every morning, user disengages.

**Mitigation:** Forced revisit cadence with light friction — "you haven't looked at your BHP thesis in 45 days; one of these three things has changed since you wrote it; what do you want to do?" Cap the number of open theses (e.g. max 15) so the user is forced to prune. The CSL example in Part 7 demonstrates the pattern.

### Attack 4: Opportunity cost is impossible to do honestly

Forward-comparing two unknown distributions is a mug's game. Every opportunity-cost number is wrong in some specific way. If the user trusts them, they'll make worse decisions than if they'd used heuristics.

**Mitigation:** Opportunity cost is *advisory and qualitative*, never a single number. Comparative ordinal framing only ("ranked by current attractiveness"). Never "you'd make $4,200 more in BHP." The user provides their own probability estimates; the system structures the comparison.

### Attack 5: The build complexity has exceeded the solo-founder threshold

Three core domain objects, opportunity cost simulation, LLM-assisted theme mapping, thesis revisit cadence engine, theme momentum stage detection — substantial work on top of what's already built. The risk is building half of it for two more years and never shipping.

**Mitigation:** Ruthlessly stage. The morning ritual on real data with manually-entered theses is shippable in 6-8 weeks. Auto-theme-mapping is 2 months later. Opportunity cost is later still. Don't try to ship the full thesis at once.

### Things to be careful of (not attacks, but real risks)

**Macro tracking can become an endless feature wishlist.** Every macro indicator is interesting; almost none will change decisions. Discipline: choose the 8-12 indicators that, if they moved, would actually change something the user does. If an indicator can't be paired with "and when this moves X, the brief says Y," it doesn't belong.

**Commodity attribution adds maintenance burden.** Every new thesis needs commodity dependencies declared. Every quarter the dependencies need re-validating. Easy to skip when busy, then quietly degrades accuracy. v1 is hand-curated with a `last_validated_at` timestamp and a brief warning when stale (90+ days).

**LLM-assisted thesis structuring will hallucinate.** When the system structures user prose into the `theses` schema, it will sometimes invent invalidation conditions or misattribute themes. The mitigation is structured human review before any LLM output is committed — same `system-architect` pattern as architectural decisions. Show the user the structured output, ask them to confirm or edit, never commit silently.

**The "what we are watching" workup is the most unscoped piece.** What does a name in "research" status actually look like inside the system, and what changes its status to "draft thesis ready"? This part of the spec is hand-wavy in V2. It will need its own milestone once theses are live.

---

## Part 10 — Open questions

Things to resolve as implementation reveals them.

1. **Naming.** TradeSight is a placeholder. The product needs a name before any user-facing surface ships beyond James. Worth a separate naming exercise once the first-real-week milestone closes and the product feels like a real thing.

2. **The "research phase" of watchlist workup.** Part 5 mentions names in "research" status. What does this mean concretely? What does the system surface about a name being researched? What promotes it to "thesis ready"? Worth scoping after the basic thesis layer ships.

3. **LLM provider.** Anthropic API direct, via your Anthropic Managed Agents evaluation, or via local OSS models for the privacy-sensitive thesis-structuring work? Probably Anthropic API for v1; revisit when usage matters.

4. **Property and broader wealth.** Quarterly, long-term. Schema, integration with banking data, reconciliation with portfolio. Out of v1 scope but worth a one-page spec eventually so the product's eventual shape is in mind.

5. **Multi-user.** Path A is single-user James. The data model uses no `user_id` per existing CLAUDE.md non-negotiable. When Path B comes, the migration is non-trivial. Not yet, but worth a "how do we get there" sketch before too much new code is written that assumes single-user.

6. **Brief delivery channel.** Email via Resend works. Worth considering whether a web view ("open today's brief in browser for interactive elements") is part of v1 or v2. For a one-user system, the email is enough; for any peer rollout, the interactive web view is probably required.

7. **Backtesting the thesis framework.** Once 6+ months of thesis history exists, can the system retrospectively grade decisions? "Of the 23 theses you opened in 2026, X exited at target, Y by stop, Z expired; here's the IRR distribution." This is the validation loop that turns the discipline layer into something measurable. Defer to 2027.

---

## Part 11 — Memory state (corrected 2026-05-28)

**This project's memory directory is empty.** No entries exist at `/Users/jamespcino/.claude/projects/-Users-jamespcino-Projects-asxos/memory/`. There is nothing to clear here.

A prior draft of this section listed items to remove (5,040 tests, 72 users, Vercel, SMSF positioning, Sprint 10/11/12, Screening-First pivot, etc.) — those came from the **separate** `asx-portfolio-os` project memory at `/Users/jamespcino/.claude/projects/-Users-jamespcino-Projects-asx-portfolio-os/memory/`. Memory is scoped per-project-directory in Claude Code's memory system, so those entries do not load when working in this asxos repo. The earlier listing was misdirected.

### Memories that should be created as v1 work proceeds

When the first session opens a memory file for this project, the foundational entries should be:

- **project** — "Project is in V2 product thesis state per docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md (locked 2026-05-28). Wedge: trade theses with discipline around them. Three-layer moat: thought-process integration, discipline scaffolding, theme stewardship."
- **project** — "Current state: CLI-only, single-user (no `user_id` anywhere), pre-revenue, no holdings imported yet, full pipeline never run end-to-end. Backend FastAPI 0.115 + Supabase Postgres. Daily-grain throughout."
- **reference** — "V2 architecture audit lives at docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md. Part M is the resolved decision log. 16-item risk register in Part K."
- **reference** — "Memory for THIS project (asxos) is at `/Users/jamespcino/.claude/projects/-Users-jamespcino-Projects-asxos/memory/`. Do not pull from asx-portfolio-os memory — different project, different codebase, different conventions (notably: asx-portfolio-os memory.md line 55 says `.AU` canonical / `.AX` legacy, which is correct for THAT project; both projects in fact use `.AU`)."

These are suggestions. The first session that creates memory should write them factually, not as copy-paste from this spec.

---

## Part 12 — Architecture decisions (resolved 2026-05-28 via audit)

These 13 decisions were resolved interactively after the system-architect audit at `docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md`. They override or refine the earlier parts where they conflict. Anything below this line supersedes anything above where they disagree.

### 12.1 — Data model

| # | Topic | Decision |
|---|---|---|
| D1 | Symbol format | **`.AU` for Australian, `.US` for US** (e.g. `MIN.AU`, `NVDA.US`). Matches both the existing asxos codebase and the EODHD API convention (data source uses `.AU`). The spec's earlier `MIN.AX` / `NVDA` examples in Part 6 and Part 7 are corrected to this convention. No migration; no translation layer. *Decision revised 2026-05-28 after surfacing the true cost of going `.AX` (EODHD round-trip translation on ~6 ingestion modules).* |
| D2 | Watchlist model | Same `theses` table, distinguished by `status='watching'`. No separate `watchlist` table. Promoting watchlist → active is `UPDATE theses SET status='active', actual_entry_price=..., actual_entry_at=NOW()`. |
| D3 | `theses.status` enum | Extended to `('research', 'watching', 'active', 'exited', 'expired')`. `'research'` = drafted, no entry plan yet. Added in the initial M-Thesis-1 migration, not as a later ALTER. |
| D5 | Daily portfolio snapshot | New table `portfolio_daily_snapshots(as_of, capital_aud, holdings_mv_aud, benchmark_tr_level, ...)`. Daily job at ~21:00 UTC. Required for YTD framing, MTD framing, day-change attribution, and the historical curves the brief leans on. |
| D6 | Theme adjacency | Add `themes.adjacent_codes TEXT[]` column in M-Thesis-1 migration. User-edited via `asx theme adjacency add CODE_A CODE_B`. v2 milestone (`M-Theme-Adjacency`) layers LLM-assisted suggestions on top; v1 is purely manual. |

### 12.2 — Data sources

| # | Topic | Decision |
|---|---|---|
| D4 | ASX 200 TR benchmark | **Compute TR from XJO price + trailing dividend yield**, not the paid XJOAT endpoint. XJO is on the current EODHD plan. Dividend yield from ASX/RBA monthly stats. Accuracy ±~10bps over a year — sufficient for the brief. |

### 12.3 — Compute model

| # | Topic | Decision |
|---|---|---|
| D7 | `opportunity_cost_scenarios` cadence | Piggyback on `build_portfolio` Sat 20:00 UTC. Brief reads cache; freshness gate is the same gate as portfolio build. |
| D8 | Theme stage maintenance | **Auto-detect from price + news in v1.** This pulls M-Theme-Stage-Detection forward from Part 8.3 into the v1 build sequence. Classifier outputs must be **suggestions the user confirms**, not silent writes — the auto-classifier writes to a `themes.stage_suggested` column; user override via `asx theme stage CODE STAGE --note "..."` updates `themes.stage`. The brief reads `themes.stage` (user-confirmed) and surfaces when `stage_suggested != stage`. |
| D9 | `invalidation_conditions.status` computation | Manual in v1 — user edits via `asx thesis revise`. M-Thesis-Revisit-Engine (Part 8.3) automates later from news/fundamentals/regime. |
| D13 | Condition trigger evaluation | **Rolling-window evaluator over `underlying_prices`** on each brief run. No new `condition_history` or `trigger_fires` table in v1. The "5 consecutive days" framing in the worked example uses `SELECT spot FROM underlying_prices WHERE underlying_id=X ORDER BY as_of DESC LIMIT 5` and checks all rows meet threshold. **Backlog (M-Trigger-Quality):** `trigger_fires` log table + daily scoring job + aggregation views to measure which trigger patterns actually predict break-outs. Accepts the cost that the learning loop starts from zero history when it eventually ships. |

### 12.4 — Brief output

| # | Topic | Decision |
|---|---|---|
| D10 | Section 10 (opportunity cost) prose | Jinja template over structured data. The "This comparison is not a prediction..." footer is a fixed string. No LLM in the v1 prose path. |
| D11 | Time-estimate learning | No email open-tracking webhooks in v1. Track `asx brief close` timestamp vs. brief send timestamp. Less precise (user might leave email open in tab) but personal-only system; noise is acceptable. Resend webhook integration is a v2+ candidate if estimates drift badly. |
| D12 | Section 1 attribution | **List news items for any holding that moved >1% intraday.** No causal claims ("X moved because of Y"). The brief surfaces relevant `holding_news` rows; the user makes the connection. LLM-generated causal narratives are explicitly out of v1 scope (high hallucination risk). |

### 12.5 — Resulting build-sequence changes

The spec's Part 8 build sequence is amended:

- **M-Thesis-0 (new prerequisite) ~2-3 days.** Split `asxos/cli/main.py` (1473 lines) into `asx <subcommand>` Typer apps. Scaffold `asxos/domain/{theses,themes,regime,underlyings,brief}/` package skeletons. Add `portfolio_daily_snapshots` table + daily job. This milestone unblocks everything else and must complete before M-Thesis-1. *Symbol migration removed from scope per D1 revision — codebase stays on `.AU` / `.US`.*

- **M-Thesis-1** unchanged in scope, but the migration now includes the `'research'` status, the `themes.adjacent_codes TEXT[]` column, and the `themes.stage_suggested` column for D8.

- **M-Theme-Stage-Detection promoted from Part 8.3 to v1 sequence**, slotting after M-Brief-V2-Sections (renamed from M-Brief-Reshape per audit Part L) and before M-First-Real-Week. Estimated ~3-5 days. Outputs suggestions only — never silent writes.

- **M-Trigger-Quality added to Part 8.3 backlog.** `trigger_fires` log table + daily scoring job + aggregation views. ~3-4 days. Slots after M-First-Real-Week.

- **M-Opportunity-Cost-v1 promoted from Part 8.3 to v1 sequence** per audit Part L recommendation, slotting before M-First-Real-Week. Section 10 of the brief is in the visual spec; the first real week is incomplete without it.

Revised v1 ordering: **M-Thesis-0 → M-Thesis-1 → M-Market-Context → M-Underlyings → M-Brief-Skeleton → M-Brief-V2-Sections → M-Snapshot → M-Opportunity-Cost-v1 → M-Theme-Stage-Detection → M-First-Real-Week.**

Estimated total revised: **7-9 weeks** (was 6-8 per Part 8.4). The modest increase comes from pulling M-Theme-Stage-Detection forward. *Was 8-10 weeks before D1 revision removed the symbol-migration scope from M-Thesis-0.*

---

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | Initial document. Captures V2 thesis from strategic conversation 2026-05-28. Folds in trade thesis layer (entry/stop/target/timeline/opportunity cost), theme stewardship layer, market context layer, underlying drivers layer. Replaces V1 SMSF-specific signal-centric positioning. Demotes M14c/M14d/M16 from previous build plan. |
| 2026-05-28 | Added Part 12 — Architecture decisions. Resolves all 13 open questions from the system-architect audit (`docs/strategy/V2_ARCHITECTURE_AUDIT_AND_DESIGN.md` Part M). Notable changes from the original Part 8 sequence: added M-Thesis-0 prerequisite (CLI split + daily snapshot table + domain scaffolding), promoted M-Theme-Stage-Detection and M-Opportunity-Cost-v1 from Part 8.3 backlog into v1, added M-Trigger-Quality to backlog. |
| 2026-05-28 | Corrected Part 11 — earlier draft listed memory items from the unrelated `asx-portfolio-os` project; this project's memory is empty. Replaced with factual note + suggested foundational entries for first session that opens project memory. |
| 2026-05-28 | Revised D1 (symbol format) — reverted from `.AX`/no-suffix back to codebase + EODHD convention `.AU`/`.US` after surfacing that the EODHD API itself uses `.AU` and going `.AX` would require permanent translation wrapper on ~6 ingestion modules. M-Thesis-0 scope reduced from ~3-4 days to ~2-3 days. Total revised estimate 7-9 weeks. |
| 2026-05-28 | **M-Thesis-0 complete.** CLI split (asxos/cli/main.py 1472→~40 lines, 11 modules), V2 domain scaffolding (theses, themes, regime, underlyings, brief packages), `portfolio_daily_snapshots` table (migration 0011), `jobs/snapshot_portfolio.py` daily cron (20:40 UTC Sun-Thu), `render.yaml` updated with `asxos-snapshot-portfolio`. XJO benchmark soft-degrades to NULL (AXJO.INDX not yet in sync_prices). cash_aud = cash_floor_pct × capital_aud (provisional; real cash ledger after M13.8). |

---

## Cross-references

- `CLAUDE.md` — non-negotiables (Decimal discipline, no user_id, NUMERIC(18,6), hard-fail invariants, render.yaml + check-drift).
- `.claude/rules/portfolio-conventions.md` — existing conventions on rationale_tags, pure/DB split, Decimal purity.
- `.claude/rules/job-conventions.md` — JobMonitor pattern, init_pool/close_pool.
- `docs/maintenance/guards-backlog.md` — 16 guard-clause improvements that should not be blocked by this V2 work but should be considered alongside it.

## For Claude Code: next session prompt

If you are picking this up in a new session, start with:

```
Read docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md in full.

Confirm you understand:
  - The product thesis (Part 1)
  - The morning brief format (Part 7 — the visual spec)
  - The new data model (Part 6)
  - The build sequence (Part 8)

Then ask me which milestone I want to open. Default is M-Thesis-1 (the
thesis data model and CLI).

Do NOT begin implementation without a feature-plan generated via the
/feature-plan skill against the chosen milestone. Do NOT write code based
on memory of earlier conversations — use this document as the source of
truth.
```
