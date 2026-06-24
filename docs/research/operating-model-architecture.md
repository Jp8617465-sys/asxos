# Operating-model architecture — how a fund / quant / PM would run asxos

**Date:** 2026-06-22 · **Status:** architecture / strategy (no code changed)
**Grounding:** built on this session's verified findings — the model is a **5-day**
signal (rank-IC ~0.095, not robust, reverses by 21d, concentrated in illiquid
names), `expected_return` is non-predictive, there is **no 6/12-month forecast**,
fundamentals are **~1 month deep with quality/growth columns NULL**, and the
`theses` long-horizon layer is **near-empty (1 theme, 2 theses)**.

---

## 0. The core problem: three jobs fused into one

A hedge fund, a quant, and a portfolio manager use the *same data* with *different
objective functions*. asxos currently collapses all three into one path: a 5-day
ML signal simultaneously **predicts** returns, **constructs** the portfolio, and
**makes the decision** (picks the 20 names). That fusion is why a weak short-term
signal ended up driving a long-horizon buy-and-hold book. The fix is to *separate*
the jobs. The rest of this document architects that separation for your specific
environment: a **single AUD account, long-only, no shorting/leverage, retail
execution, ~1.5 years of data**.

---

## 1. How a HEDGE FUND would approach this (business / strategy)

A fund reasons from **edge → mandate → capacity → risk budget**, then builds
machinery. Three moves asxos is missing:

1. **Separate alpha / construction / execution.** Predicting returns, sizing by
   risk, and minimizing cost are three different disciplines with three different
   review gates. asxos welds them into `build_portfolio`.
2. **Run a *book of sleeves*, not one signal.** Several low-correlation strategies
   (value, quality, momentum, event, short-term), each with its own horizon,
   Sharpe, capacity, blended by risk. One signal = one point of failure — which is
   exactly what happened when the 5-day edge collapsed under scrutiny.
3. **Know what kind of fund this is.** Given the environment, the blunt verdict:
   **this is not, and will never be, a stat-arb shop.** No shorting, no leverage,
   retail execution, one AUD account. The structural edges available are
   **patience, tax (franking + CGT), low turnover, and disciplined factor tilts** —
   not a tradable 5-day forecast. Copy the fund's **discipline** (separation,
   measurement, risk limits, data quality), not its **machinery** (shorting, HFT).

A fund would also refuse to deploy on the current evidence base: *1 month of
fundamentals, ~10 clustered signal dates, ~2 independent market episodes.* That's
a **data-collection project, not a strategy.** Data first.

**Risk function.** A fund has an *independent* risk seat. asxos has a cash floor +
leverage cap but is, by its own conventions, "risk-blind to market-wide
co-movement." A fund would add: aggregate beta cap, sector/factor exposure limits,
drawdown controls, and stress tests (2008/2020-style) — *before* capital.

---

## 2. How a QUANT would approach this (research / measurement)

The quant's first move is what we already did: **measure before believing** — IC,
decay, deciles, cost, capacity, effective-N. The `alpha_eval` engine is the bench.
What a quant adds on top:

1. **A factor library.** Each candidate signal — 5d ML, earnings yield, book
   yield, ROE/quality, 6–12mo momentum, low-vol, short-term reversal — is
   researched *independently* (IC, decay, turnover, capacity, OOS stability), then
   **combined** (IC-weighted or risk-parity) and **decorrelated**.
2. **Match horizon to signal.** A 5d signal → high-turnover sleeve (only if it
   survives costs — ours doesn't in the tradable universe). A value/quality signal
   → low-turnover, long-horizon sleeve. *Different signals belong in different
   books with different rebalance cadences.* This is the resolution to the
   horizon mismatch.
3. **Anti-self-deception discipline:** strict point-in-time data, survivorship
   control, and **multiple-testing awareness** — the more factors you test, the
   more spurious winners you find; require OOS and use deflated Sharpe. Never let
   an uncalibrated regressor (`expected_return`) into production scoring.

**Quant verdict for this environment:** retire the 5d signal as the *selector*
(no tradable edge, can't short); pivot research to **long-horizon factors where
academic priors are strong and turnover is low**; use `alpha_eval` as the OOS gate;
backfill data so the IC/decay/decile numbers actually have statistical power.

---

## 3. How they'd USE THE DATA (data architecture)

Treat data as the asset and split it in two — this is the piece asxos most lacks.

**A. Research store — wide, deep, point-in-time, survivorship-free.** Immutable,
versioned, used only for research/backtests. Proposed components:

| Table | Purpose | Current gap |
|---|---|---|
| `security_master` | every symbol ever listed, with listing/delisting dates, name/ticker changes, GICS | universe is *current-only*; `is_active` not point-in-time → survivorship |
| `prices_adj` | split/div-adjusted OHLCV + raw, with corporate-action log | have `adj_close`; no corp-action log |
| `fundamentals_pit` | **point-in-time** fundamentals, dated to *public disclosure* (not period-end), full factor set | **1 month deep; roe/de/revenue/net_income NULL** |
| `estimates` | analyst consensus + target price + revisions | not ingested |
| `index_membership` | ASX200/300 membership history | absent — needed for survivorship + benchmark |
| `factor_scores` | computed factor exposures per (symbol, date), point-in-time | absent (this is the B build) |

**B. Production store — narrow, current, operational:** the live `signals`,
`rebalance_runs`, `paper_portfolio_*`, `theses`. Already exists.

**Principle:** research happens on the research store (so it's reproducible and
leak-free); production reads only what it needs. asxos conflates them today, and
the research store barely exists — which is *why* nothing here is yet
decision-grade. EODHD provides ~all of the above (historical financials, analyst
estimates, splits/divs); the system currently ingests a sliver. *Verify exact
field/depth availability against the EODHD plan before building.*

---

## 4. How a PORTFOLIO MANAGER would use this data (judgment)

A PM is **not** a quant. The PM allocates across sleeves, sizes by conviction,
manages risk, and supplies the **qualitative overlay models miss** — management
quality, the thesis, catalysts, macro. Data are *inputs to judgment, not an
autopilot.*

**You are the PM.** The data should make you **slower and more disciplined**:
- the quant layer hands you a **ranked shortlist** of cheap-quality names + risk
  metrics;
- you write the **thesis** (layer C, currently empty): entry band / stop / target
  / timeline / conviction, with real reasoning;
- you **size by conviction**, respect **tax** (CGT 12-month, franking), and
  **veto** anything the thesis can't justify;
- the **monitor** is your scoreboard; the **brief** is your morning read.

Your PM edge in a single AUD account is **patience + tax efficiency +
concentration in high-conviction theses + not overtrading** — the opposite of
chasing a 5-day signal.

---

## 5. Target architecture

```
 RESEARCH DATA STORE  (PIT, survivorship-free)            ← FIX FIRST
   security_master · prices_adj · fundamentals_pit · estimates · index_membership
        │
        ▼
 LAYER 1 — ALPHA (quant)      factor library + alpha_eval OOS gate
   sleeves: value · quality · momentum(6–12m) · [5d ML → paper-only/retired]
   → per-name expected-return scores, by horizon, decorrelated
        │
        ▼
 LAYER 2 — PORTFOLIO (quant + risk)   blend sleeves → optimizer
   sector/factor/beta limits · liquidity floor · tax overlay · turnover control
   → target weights
        │
        ▼
 LAYER 3 — PM (you)   theses · conviction sizing · veto · brief
   → long-only, tax-aware, low-turnover book
        │
        ▼
 MONITOR (scoreboard over everything)                    ← already built
```

**The one shift that matters:** today the arrow runs backwards — a 5-day signal
drives selection and the thesis layer is empty. Flip it: **fundamentals + factors
+ theses drive the long book; the ML signal earns its place only as a measured,
paper-only sleeve.**

### Current → target gap

| Capability | Today | Target |
|---|---|---|
| Data | 1.5yr prices; 1mo fundamentals; NULL factors; no survivorship/estimates | PIT research store, full factor set, years deep |
| Alpha | one 5d ML signal doing everything | factor library, multi-horizon sleeves, OOS-gated |
| Construction | inverse-vol + caps, signal-driven, `expected_return` broken | risk-aware blend of sleeves, factor/beta limits, quarantine `expected_return` |
| Decision | model picks 20 names | PM theses + conviction sizing |
| Measurement | `alpha_eval` + monitor ✅ | same, fed with real data |

---

## 6. Sequenced roadmap (best, not easiest)

1. **Data foundation** — ingest the NULL factor columns + backfill PIT
   fundamentals/history + index membership via EODHD → the research store.
   *Everything else is building on sand until this exists.*
2. **B — Layer 1/2:** sector-neutral, liquidity-filtered **value × quality** factor
   score, validated at 126/252d with `alpha_eval`, feeding the allocator
   (replacing the broken composite). Weights from **external priors** until
   internal validation has power.
3. **C — Layer 3:** build out the `theses` workflow so conviction has a home
   *today*, independent of the data backfill.
4. **Blend + risk:** combine sleeves, add aggregate-beta / sector / factor limits,
   turnover control, tax overlay. Paper-only until the monitor shows a positive
   *net* result across regimes.

---

## 7. How not to fool ourselves
- No capital until a **costed, liquidity-filtered, purged-OOS** result is positive
  across **more than one regime** with real statistical power (≫2 episodes).
- Factor weights are **priors, not fits**, until the research store is deep enough.
- Every new factor is one more multiple-testing trap — gate on OOS, not in-sample.
- The monitor + `alpha_eval` effective-N guard stay the referees; if they say
  "not decision-grade," that is the answer, however good the story sounds.

**Bottom line for a single AUD long-only account:** you don't need a hedge fund's
*machinery* — you need its *discipline*. The best asxos is a disciplined,
tax-aware, factor-plus-thesis long-only book where the quant layer keeps you
honest and you (the PM) make patient, high-conviction decisions over years.
