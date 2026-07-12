# ETF/LIC screening criteria — scoping (design, not build)

**Status:** proposed — scoping only. No code, no migration, no ingestion change.
**Scope:** the still-undesigned piece of `docs/proposals/thesis-coverage-framework-2026-07-11.md`
item 5, sub-item 2 — "the ETF/LIC kind-appropriate criteria (asset-class/geography/breadth for
funds — a small net-new taxonomy) is still not designed." Closes that gap with a concrete,
data-grounded Phase-1 cut.
**Depends on:** nothing for Phase 1 (see below) — Phase 2+ depends on a live EODHD probe against a
real ASX ETF/LIC symbol.
**Last verified:** 2026-07-12
**Owner:** scoped by `requirements-analyst` this session; needs James's sign-off before any build
(new query code touching `asxos/domain/screening/evaluator.py`, which is already-shipped,
review-gated code).
**Superseded by:** N/A

---

## Why this exists

`asxos/domain/screening/evaluator.py` (shipped this session, PR #27) is structurally equity-only:
its `_FIELD_MAP` whitelist (`pe_ratio, pb_ratio, eps, dividend_yield, franking_pct, roe,
debt_to_equity, revenue, net_income, market_cap, sector, latest_close`) comes almost entirely from
the `fundamentals` table, which `jobs/sync_fundamentals.py:57` populates only for
`WHERE is_active AND security_kind = 'au_equity'`. ETF/LIC/hybrid symbols (471 / 13 / 21 rows in
the live universe) never get a `fundamentals` row — every screening field is NULL or meaningless
for a fund today, even though `universe.security_kind` (migration 0037) already classifies them.

This doc scopes what "kind-appropriate screening" should actually mean before any of it is built.

---

## 1. What criteria are actually meaningful

Funds (ETF/LIC) and hybrids are structurally different instruments — this doc scopes **ETF/LIC
only**. Hybrids (income/credit instruments: coupon, call date, maturity, credit quality) need
their own later design; forcing them into a fund vocabulary for symmetry would model something
untrue of the instrument.

For ETF/LIC, the criteria a DIY investor actually filters funds by:

| Dimension | Applies to |
|---|---|
| Asset class (equity/fixed income/commodity/cash/multi-asset) | ETF + LIC |
| Geography / domicile | ETF + LIC |
| Breadth (broad-market beta vs. sector/thematic) | ETF + LIC |
| Cost (management fee / MER) | ETF + LIC |
| Distribution yield (+ AU franking) | ETF + LIC |
| Size / liquidity (AUM, avg daily $ turnover) | ETF + LIC |
| Tracking difference/error (vs. benchmark) | ETF only (index funds) |
| **NAV premium/discount to NTA** | **LIC only** — closed-end funds trade away from NAV by
construction; structurally meaningless for an open-ended ETF (arbitrage keeps price ≈ NAV). Must
be gated to `security_kind = 'lic'`, never offered for `etf`. Confirmed as a real, standard retail
LIC-investing practice, not a novelty (external confirmation: [Strong Money Australia's LIC
premium/discount guide](https://strongmoneyaustralia.com/lic-premiums-and-discounts-complete-guide/)) —
and matches `docs/proposals/multi-instrument-expansion-2026-07-11.md`'s own framing of it as *"a
discipline signal, not a valuation override."* |

---

## 2. Data availability — three honest tiers, not "available vs. not"

Verified against EODHD's own documentation and this repo's existing ingestion code — not assumed.
**Caveat, stated plainly: field *names* are confirmed in EODHD's documented schema; AU-listed-fund
population *depth* is not verified for any of the Tier B/C fields below.** This repo has direct
precedent for exactly this kind of check — `docs/research/probes/2026-06-24-eodhd-gate-closure.md`
is a prior live probe against real EODHD responses before building on assumed field availability.
**A live probe against a real ASX ETF (e.g. `VAS.AU`) and LIC (e.g. `AFI.AU`) is a hard
prerequisite before any Tier B/C build** — this doc alone is not sufficient grounds.

**Tier A — zero new ingestion, ship now:**
- **Liquidity** (avg daily $ volume): purely `prices.volume × prices.close`. `jobs/sync_prices.py`
  scopes by bare `WHERE is_active` (no `security_kind` filter) — every fund symbol already gets
  daily OHLCV today.
- **Distribution yield + AU franking**: derivable from `rs_corporate_actions` (research store),
  which `jobs/sync_corporate_actions.py` already populates weekly for **all** security kinds
  (`asxos/ingestion/security_master.py` explicitly stores "ALL types, unlike `universe`"). No new
  external API call — new internal join/derivation code only, since `evaluator.py`'s base query has
  never touched `rs_corporate_actions` before.

**Tier B — same EODHD endpoint already called for equities, new parser code, gated on a live probe:**
- Asset class/category, geography, cost (MER), AUM — all live in the `/fundamentals/{symbol}`
  endpoint's `ETF_Data` section, which `asxos/ingestion/fundamentals.py::parse_fundamentals` never
  reads today (it only parses the equity-shaped `Highlights`/`Valuation`/`SharesStats`/`General`
  sections). Field names are confirmed; AU population depth is not.

**Tier C — genuine new ingestion, Phase 2+:**
- Tracking difference/error: needs a generalized global-index price feed (today only one index,
  `AXJO.INDX`, is ingested at all).
- NAV/premium-discount to NTA: **not found in EODHD's documented ETF_Data fields at all.** LICs are
  ordinary companies legally, so EODHD may return the equity-shaped payload instead — genuinely
  unverified either way. NTA-per-share is normally self-published by LIC managers via ASX
  announcements, likely a different data source entirely. Highest-uncertainty item in this doc.

**Recommended Phase-1 cut: Tier A only.** Ships the two highest-value DIY filters (liquidity,
yield/franking) with zero new external dependency and no unresolved AU-population-depth risk.
Tier B is a reasonable next increment once the live probe confirms field population; bundling it
into "Phase 1" would treat an unverified dependency as already-available data.

---

## 3. Where this plugs into the evaluator

**Recommendation: extend `_FIELD_MAP` (kind-namespaced), do not touch `source_method`, make
`security_kind` a required top-level rule key.**

- `source_method` stays `'curated_composite'`-only. Its job is model-provenance (hand-authored vs.
  ML-derived, per rule #11), an orthogonal axis to instrument kind — growing a second value would
  undo the exact tightening migration 0038 exists to lock in.
- `security_kind` should **not** become an ordinary whitelisted condition field. `evaluator.py`'s
  own docstring is explicit today: *"is_active/security_kind are NOT whitelisted here — they are
  hardcoded into the base query, never author-controlled."* Letting a rule freely combine
  `pe_ratio > 10 AND security_kind = 'etf'` would be syntactically valid and semantically
  nonsensical — silently returning zero matches instead of erroring, exactly the "silent wrong
  answer" class of bug this codebase's hard-fail discipline exists to prevent.
- Instead: make `security_kind` a **required, single-valued top-level key** (a mandatory sibling of
  the existing optional `sector_scope`), validated against the same enum as
  `universe.security_kind` (`au_equity | us_equity | index | etf | lic | reit | hybrid`). The
  evaluator branches its base query on that value — `au_equity` keeps today's `fundamentals` JOIN;
  `etf`/`lic` join the Tier A/B fund-metadata source once it exists.
- `_FIELD_MAP` entries get an `applies_to` attribute (which kind(s) each field is valid for);
  `parse_rule` hard-fails if a condition's field isn't valid for the rule's declared
  `security_kind` — same shape as the existing text/op type-mismatch hard-fail.
- Open item for `backend-architect`: draft migration `0038_screening_evaluator_wiring.sql`'s
  `screening_runs` audit table logs `sector_scope` but has no `security_kind` column — a fund
  screening run needs a parallel column to keep the audit trail complete.

---

## 4. Calibration check

Per the competitive-gap doc's calibration note ("no competitor does X is not a reason to build
X"):

- NAV premium/discount is **not** a calibration risk — independently confirmed as standard retail
  LIC practice. The actual risk is over-building an NTA time-series/alerting system before
  confirming any cheap data source exists (it's Tier C, least verified).
- Tracking error is real but should sequence last — it needs the most new ingestion, and
  `portfolio-conventions.md` already documents deliberately deferring correlation/beta analytics
  in v1 (`m14_candidate_beta_cap`).
- **"Breadth" as an automated inferred score is the clearest smell.** No direct EODHD field; the
  only path is inferring from sector-weight concentration, itself unverified for AU funds.
  Recommend a manually curated tag (James tags a fund "thematic" once) for Phase 1 instead of
  engineering a novel breadth score — same caveat `portfolio-conventions.md` already states for the
  risk-tolerance→position-count heuristic ("a UX heuristic, not a finance-research-grade model").
- Resist ingesting EODHD's full `ETF_Data` blob (30+ fields, including sustainability ratios,
  Sharpe ratios, etc.) just because it's there — scope the parser to the criteria named in §1 only.

---

## Phase-1 recommendation (summary)

Build only Tier A: a liquidity filter (`prices`-derived, zero new ingestion) and a distribution
yield/franking filter (`rs_corporate_actions`-derived, zero new external call). Both require new
evaluator query code but no new data source and no unresolved vendor-availability risk. Everything
else (asset class, geography, cost, AUM, tracking error, NAV premium/discount) waits on a live
EODHD probe against a real ASX ETF and LIC symbol before any further scoping is trusted.

## Sources

- `asxos/domain/screening/evaluator.py`, `asxos/domain/screening/types.py`
- `.claude/rules/screening-conventions.md`
- `migrations/0001_initial.sql`, `migrations/0037_security_kind.sql`,
  `migrations/0038_screening_evaluator_wiring.sql` (draft), `migrations/0027_research_store.sql`
- `jobs/sync_fundamentals.py`, `jobs/sync_prices.py`, `jobs/sync_corporate_actions.py`
- `asxos/ingestion/eodhd.py`, `asxos/ingestion/fundamentals.py`, `asxos/ingestion/security_master.py`
- `docs/proposals/thesis-coverage-framework-2026-07-11.md`,
  `docs/proposals/multi-instrument-expansion-2026-07-11.md`,
  `docs/product/competitive-gap-analysis-2026-07-11.md`
- `docs/research/probes/2026-06-24-eodhd-gate-closure.md` (precedent methodology)
- [EODHD Fundamental Data API](https://eodhd.com/lp/fundamental-data-api),
  [EODHD ETF Fundamentals Glossary](https://eodhd.com/financial-academy/financial-faq/fundamentals-glossary-etf)
- [Strong Money Australia — LIC premiums and discounts guide](https://strongmoneyaustralia.com/lic-premiums-and-discounts-complete-guide/)
