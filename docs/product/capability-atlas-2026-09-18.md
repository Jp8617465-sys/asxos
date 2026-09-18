# asxos Capability Atlas — what this platform actually does

**Status:** current
**Scope:** whole repo + live production state
**Verified:** 2026-09-18, by execution — not by reading docs
**Author:** arbi
**Read priority:** read before asking "can asxos do X?"

This document answers one question: **what can asxos do today, and what can it not do?**
Every claim below was produced by running something or probing live production on
2026-09-18. Where a capability is blocked, the blocker is named. Where a capability is
broken, the defect is cited to a file and line. Nothing here is inherited from an older
doc without re-verification — the repo's own standing lesson is that capability prose
rots (`CLAUDE.md` §Known coverage gaps).

---

## 0. How this was verified

| Probe | Result |
|---|---|
| `pip install -e ".[dev]"` into a fresh 3.12 venv (no `[ml]` extra) | clean |
| `pytest tests/ -q` | **4,725 passed · 13 skipped · 0 failed · 0 collection errors · 27.36s** |
| `python -m asxos.cli.main --help` + every sub-app `--help` | 25 command groups enumerated, all load |
| `asx thesis list` (against prod) | **hangs, killed at 60s** — see §9 |
| Live Supabase read-only probes | 78 tables; ~30 distinct jobs ran in the last 10 days |

The 13 skips are all `MIGRATION_TEST_DATABASE_URL` integration opt-ins, not gaps.
The suite runs **without** `joblib`/`lightgbm`, confirming the Model A deletion (PR #144)
left no import chain behind.

---

## 1. The honest one-paragraph summary

asxos is a **working daily investment-discipline system with one position in it.**
The data spine (prices, fundamentals, point-in-time financials, FX, risk-free rates,
market context) is genuinely deep — 806k price rows, 700k financial-statement rows,
2,464 symbols — and refreshes nightly without intervention. The morning brief composes
nine sections and, as of this morning, is correctly shouting **four red discipline
flags** at a A$7,749 portfolio. The valuation engine values 1,879 ASX names a week and
narrows them to 35 on stated gates. What the platform does **not** do is size a
portfolio (deliberately gated), produce a brokerage instruction (never built), or
learn from an outcome (captures t0 only). And the single most important thing it
produces — this morning's stop violation — has been produced faithfully for weeks and
acted on by nobody.

---

## 2. Capability map

Verdicts: **WORKS** (runs, produces correct output, someone reads it) ·
**IDLE** (runs correctly, output reaches nobody) · **BLOCKED** (built, deliberately
gated off) · **BROKEN** (runs, output is wrong) · **ABSENT** (does not exist).

| # | Capability | Verdict | Evidence |
|---|---|---|---|
| 1 | Market data spine (prices, fundamentals, PIT, FX, rates) | **WORKS** | `prices` 806,250 rows to 2026-09-17; `rs_financial_statements` 700,114; `rs_fundamentals_pit` 54,545; `fx_rates` 108; `risk_free_rates` 32 |
| 2 | Nightly job fleet | **WORKS** | 30 distinct `job_runs` names succeeded in 10 days; 34 modules under `jobs/` |
| 3 | Morning brief (9 sections) | **WORKS** | `brief_section_gold` 2026-09-18: 7 FRESH, 2 EMPTY; 18 days of history; 75 `brief_runs` |
| 4 | Thesis discipline engine | **WORKS** | 4 RED flags emitted this morning — §4 |
| 5 | Equity valuation (residual income) | **WORKS** | `valuation_runs` 1,879 rows at 2026-09-16; funnel in §5 |
| 6 | Opportunity discovery + governance queue | **IDLE** | 35 names pass the gates; 10 were proposed 09-16 and **all 10 rejected**; queue now empty |
| 7 | Macro thesis layer | **IDLE** | 4 `macro_theses`, newest **2026-07-22 — 58 days stale** |
| 8 | Decision packets (broker-report chain) | **IDLE** | 4 packets, all CBA.AU, **all `abstain`** |
| 9 | Theme stewardship | **IDLE** | 1 theme, 2 `theme_holdings` — the moat layer with the least content |
| 10 | Portfolio construction / allocator | **BLOCKED** | `model_versions`: `approved_for_allocation = false` → gate returns 0 rows → hard-fail. Rule #11 working as designed |
| 11 | Tax engine (CGT, Div 296, franking, Medicare) | **BLOCKED** | Code + tests complete; **`tax_settings` has 0 rows** — unconfigured in production |
| 12 | Regime classifier | **BROKEN** | Credit-stress arm dead — §6 |
| 13 | Position monitor | **IDLE** | `asx position monitor` exists; **`position_monitor_runs` = 0 rows, ever** |
| 14 | Benchmark / alpha attribution | **BLOCKED** | ASX sleeve empty (no ASX lots); global sleeve "not applicable" by governor ruling F2 |
| 15 | Outcome learning | **PARTIAL** | t0 capture + 21/63/126-session schedule exist; no episode has completed |
| 16 | Paper trading | **PARTIAL** | 3 `paper_book_snapshots`; 60 `proposed_trades` / 5 `rebalance_runs` are pre-quarantine artefacts |
| 17 | Brokerage instruction / order draft | **ABSENT** | `asxos/capital/` empty by charter; nothing generates a ticket |
| 18 | HTTP API | **MINIMAL** | one route: `GET /health` |
| 19 | Regulatory feed | **DEGRADED** | 7 rows total; RBA RSS only (Treasury + ATO removed as dead) |

---

## 3. What you actually type

The CLI is the product surface. 25 groups, verified loading:

**Discipline (the moat)** — `asx thesis` open · show · list · enter · approve · reject ·
retire · revise · add-section · review · hold · exit · attach-underlying · history ·
update-consensus · log-analyst · set-earnings

**Themes** — `asx theme` create · list · coverage · review · stage · attach · approve ·
reject · open · adjacency · holding

**Macro** — `asx macro-thesis` list · show · open · approve · reject

**Money** — `asx tax-view` · `asx tax-action` · `asx build-portfolio` · `asx propose-trades` ·
`asx portfolio` show/history/paper-review/signoff · `asx profile` init/show/activate/list

**Research & decisions** — `asx screen` list/run · `asx research` run/vp-register ·
`asx candidates build` · `asx decision` build/record-t0/observe/positive-control/dispose/report ·
`asx replay show` · `asx results-review show`

**Ops** — `asx brief [--send]` · `asx journal` add/list/review · `asx position` monitor/history ·
`asx agent-run log` · `asx model` activate/list · `asx news signoff` · `asx arbi` compile/next

Plus 20 GitHub Actions workflows (`daily-brief`, `weekly-research`, `pipeline-health`,
`us-positions`, `backup`, `full-check`, …) and 33 slash commands / 26 subagents.

---

## 4. What the platform told James this morning — verbatim

From `brief_section_gold` where `as_of = 2026-09-18`, section `discipline`:

| Level | Check | Message |
|---|---|---|
| 🔴 RED | `revisit_overdue` | HUBS.NYSE: review overdue by **46d** (due 2026-08-03) |
| 🔴 RED | `trajectory` | HUBS.NYSE: **STOP VIOLATED** (current 229.58, stop 230) |
| 🔴 RED | `concentration` | HUBS.NYSE: **100.0% of portfolio** — concentrated position |
| 🔴 RED | `data_sanity_escalation` | CBA.AU: detached thesis ladder — no answering revision for **113d**; live price 154.01 is **2.6× the recorded target 60** |
| 🟡 YELLOW | `conviction_unset` | conviction unset on 1/1 theses — size-vs-conviction check disabled |
| ℹ️ INFO | `unrealised_return` | HUBS.NYSE: **+22.4%** unrealised since entry (USD 187.54 → 229.58; price only) |

**This is the product working.** The engine is not silent, wrong, or vague. It named the
position, the number, the breach and the command to fix it. The failure is downstream of
the software: nothing consumed it.

---

## 5. The valuation funnel, re-derived live

Reproducing `asxos/domain/discovery/ranker.py::passing` in SQL against
`valuation_runs` at `as_of = 2026-09-16`:

| Gate | Survivors |
|---|---|
| attempted | 1,879 |
| 1. `outcome = 'valued'` | **573** |
| 2. currency verified (drops `currency_unverified`) | **403** |
| 3. quality: 3-period average ROE > Ke mid (≈8.87%) | **198** |
| 4. value: V/P ≥ 1 under **both** the registered convention and the average-ROE sensitivity | **35** |

Liquidity (ADV ≥ A$250k, cap ≥ A$100m) is applied separately in
`jobs/discover_opportunities.py` and cuts 35 → the 16 recorded on 09-16.

**The finding that matters:** of the 35 survivors, **at least eight are listed investment
companies or trusts** (WQG, FGX, FGG, HM1, LSF, TGF, PGF, MEC) and **four more are
A-REIT-shaped** (TIA, BWP, TCF, CWP). That is roughly **a third of the passing set** in
vehicles whose "book value" *is* net tangible assets and whose "ROE" *is* their own portfolio
return. A residual-income model pointed at a closed-end fund does not discover mispriced
earnings power — it rediscovers discount-to-NTA, which is a published, structural feature of
the instrument class, not an edge.

Stated precisely so it is not over-claimed: several other Financial Services names in the set
(PPM, HLI, LFG, CCP) are **operating** lenders and insurers, and the finding does not apply
to them. The classification is by inspection of ticker and sector, not by a `security_kind`
column — because that column does not exist, which is the defect.

This is the already-tracked `universe.security_kind` gap
(`m14_candidate_security_kind_enum`) but its cost is larger than "seven rows to reject on
sight": it is **systematically biasing what the engine proposes**. See the plan, P0-2.

---

## 6. Defects found by this audit

### D-1 — Regime classifier: the credit-stress arm can never fire (HIGH)

`asxos/domain/regime/classifier.py:33-34` sets the thresholds in **basis points**:

```python
_HY_OAS_STRESS = Decimal("600")     # basis points
_HY_OAS_ELEVATED = Decimal("450")
```

`jobs/ingest_market_context.py:258` reads FRED `BAMLH0A0HYM2`, which is published in
**percent**, and stores it raw. Live value at 2026-09-18: `us_hy_oas = 2.70`.

`2.70 > 450` is never true. For `hy_oas_elevated` to fire, US high-yield spreads would
have to reach **45,000 bps**. Both credit legs are dead in production, and today's
`regime_rationale` confirms it: `hy_oas_stress` and `hy_oas_elevated` both
`"fired": false` with `"value": "2.7", "threshold": "600"/"450"`.

**Why CI never caught it:** `tests/test_regime_classifier.py` feeds the bps scale
(400 / 500 / 650). The tests encode one unit, production feeds another, and both are
internally consistent. `asxos/domain/underlyings/service.py:40` also declares
`"unit": "bps"` for this series, so the wrong convention is documented as if intended.

**Consequence:** the regime label — which the macro layer, the brief's framing and any
future sizing rest on — is effectively **breadth + A-VIX only**. Credit stress, the most
reliable early warning of a real drawdown, is invisible to it. Today's `risk_off_orderly`
is driven *solely* by `breadth_200_thin`.

### D-2 — Discovery proposes an instrument class the model mis-handles (HIGH)
See §5. >50% of the passing set are NTA vehicles.

### D-3 — Tax engine is complete and unconfigured (MEDIUM)
`tax_settings` has **0 rows**. Every tax case (TC-11 Medicare, TC-20 Div 296 cost-base
reset, TC-21 45-day franking, TC-24 SMSF ECPI × CGT) is implemented and tested, and none
of it can produce a number for James because the marginal rate, account type and ECPI
fraction were never entered.

### D-4 — The position monitor has never run (MEDIUM)
`asx position monitor` exists, is tested, and `position_monitor_runs` has **0 rows**.
The nightly `check_us_positions` / `check_au_positions` jobs cover alerting, so this is
duplicated intent rather than a hole — but it is dead code carrying a live promise.

### D-6 — The active profile's constraints are mutually unsatisfiable (HIGH)

The active profile `baseline` sets `per_name_cap_pct = 0.10` and `min_position_aud = 1000`.
At the live capital of A$7,749.54 the per-name cap is **A$774.95** — below the A$1,000 floor.
**No position can satisfy both rules**, so the constraint waterfall has no feasible solution
at current capital even if the allocator were unblocked. `capital_aud` on the profile is also
stale (A$6,666.98 recorded vs A$7,749.54 in the latest snapshot).

Separately, this is the number that makes the concentration flag concrete: the brief says
"100.0% of portfolio"; the profile says the cap is **10%**. The live portfolio is a **10×
breach of James's own stated framework.**

### D-5 — `check_cron_health` is red (KNOWN, tracked)
3 failures in 10 days; incident #327, cause 2 fixed in #328, data lands on the Saturday
`weekly-research` fire. Not re-taken here, per the 2026-09-18 handoff.

---

## 7. The live portfolio, measured

| Fact | Value |
|---|---|
| Total capital | **A$7,749.54** (2026-09-17) |
| Cash | **A$0.00** |
| Positions | **1** — HUBS.NYSE, 24 shares |
| Cost base (AUD, CGT) | A$6,978.23 |
| Entry (native) | US$187.54, 2026-05-31 |
| Last close | US$229.58 (2026-09-17) |
| Return, USD | **+22.4%** |
| Return, AUD | **+11.05%** |
| FX drag | AUD/USD 0.6450 at entry → **0.7110** today |
| CGT 12-month discount eligible | **2027-06-01** (256 days away) |
| Stop | 230.00 — **violated** |
| Profile per-name cap | **10%** — the position is **10× over** |
| Profile cash floor | 0% |

The USD-vs-AUD gap is the whole story of this position: **the stock made 22.4% and the
currency took half of it.** A stronger AUD is a direct tax on unhedged offshore holdings,
and asxos measures it correctly — `portfolio-conventions.md` exists precisely because an
earlier review got this wrong and reported HUBS at −29%.

---

## 8. The macro read, from live data only

`market_context` at 2026-09-18 (every figure is a stored value, none is inferred):

| Indicator | Value | Read |
|---|---|---|
| S&P/ASX 200 | **8,732.40**, +0.41% | index near highs |
| % above 50-day MA | **36.6%** | weak |
| % above 200-day MA | **27.9%** | **thin — fires `breadth_200_thin` (<40%)** |
| A-VIX | **12.62** | very calm |
| VIX | 15.44 | calm |
| RBA cash rate | **4.35%** | unchanged |
| AUD/USD | **0.7110** | strong, and rising — up from 0.6450 in May |
| AU 10-year | **5.015%** | sticky-high long end |
| US HY OAS | 2.70% (270bp) | tight — **but see D-1: not actually being read** |
| US 10y−2y | +0.27 | positive, un-inverted |
| Iron ore 62% Fe | **NULL** | **missing input** |
| Regime | **`risk_off_orderly`** | on thin breadth alone |

**What is contributing to what.** The index is 0.4% from strength while only 27.9% of its
constituents are above their own 200-day average. That is a **narrow market**: the
headline is being carried by a small number of large names while the median stock is in
its own downtrend. Volatility is not pricing this — A-VIX at 12.6 is complacent. The AU
long end at 5.0% against a 4.35% cash rate is a positive term premium that keeps
structural pressure on long-duration and yield-substitute equities (REITs, infrastructure,
unprofitable growth). A 0.711 AUD compounds that for anyone holding unhedged offshore
assets — which, today, is 100% of this portfolio.

The three approved macro theses on file (breadth-led catch-down; sticky ~5% AU long end;
un-inverted US curve, no near-term recession signal) are **all still consistent with these
readings** — and all were written on 2026-07-21/22 and have not been re-scored against
evidence since. The falsifier for #6 (breadth) has if anything *strengthened*: breadth was
25.9% when it was written and is 27.9% now.

**Two caveats stated rather than hidden:** iron ore is NULL, so the single biggest ASX
earnings driver is absent from the regime read; and `regulatory_events` holds 7 rows
total, so "what changed in policy" is effectively not covered.

---

## 9. What this platform cannot do

1. **Tell you what to buy.** By design. The allocator is gated off (rule #11), and after
   the sealed value-to-price test returned null (#304), `RESPONSE_RULE` stripped target
   prices, entry bands and ranked opportunities from the discovery output. What survives
   is a reviewable queue, not a recommendation.
2. **Place or draft an order.** `asxos/capital/` is empty by charter. There is no broker
   credential anywhere in this system and no code that formats a ticket.
3. **Measure whether it is any good.** The ASX benchmark sleeve is empty because there are
   no ASX lots. One position, held four months, is not a track record.
4. **Be driven from an agent sandbox.** The CLI cannot open a raw TCP connection to the
   Supabase pooler through the proxy (`asx thesis list` hung and was killed at 60s).
   Everything operational must go through GitHub Actions workflows or the Supabase MCP.
5. **See credit stress.** D-1.

---

## 10. The verdict

The engineering is not the bottleneck. 4,725 tests pass, thirty jobs run themselves
nightly, the data spine is deep and fresh, and the discipline engine produced four
correct, specific, actionable red flags this morning.

**The bottleneck is that the loop does not close.** Evidence is produced and not consumed;
a queue is opened and emptied by rejection; a stop is violated and nothing happens. The
next build should not add a capability. It should make the four flags already on the
screen impossible to ignore, and give them somewhere to go.
