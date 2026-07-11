# Proposal — multi-instrument ASX expansion (ETFs / LICs / all vehicles)

**Status:** proposal / roadmap note — NOT yet built · draft for James's approval
**Scope:** bring ETFs, LICs, REITs, hybrids (all ASX investment vehicles) into asxos as
first-class holdable / valuable / taxable / disciplinable instruments
**Date:** 2026-07-11 · **Owner:** James approves scope; build routed through backend/system-architect
**Provenance:** `requirements-analyst` PRD + `backend-architect` schema design (this session);
triggered by James: *"I want ETFs and all investment vehicles on the ASX involved."*

Today the universe is ASX **`Common Stock` only** — `refresh_universe`
(`asxos/ingestion/universe.py:30`) keeps `Type == "Common Stock"`, so VGS/VAS and every ETF
are excluded (1,873 active symbols, zero ETFs). James holds passive funds the system can't
hold, value, or tax. This is the plan to fix that.

---

## 1. The decisive design call: how is an ETF valued?

**Valuation = the ASX market price (last/close), for every vehicle kind, always. Look-through
to constituents is a SEPARATE exposure/risk capability that never touches a dollar figure on a
holding.**

- An ETF's price ≈ NAV by construction (authorised-participant arbitrage) — the market already
  values the underlying; you do not sum constituents to value it (and for a global ETF like VGS
  you couldn't — its holdings aren't ASX symbols).
- **LIC nuance:** premium/discount to NTA is real, but James transacts at **market price**, not
  NTA — so valuation stays market price; premium/discount becomes a **discipline signal**, not a
  valuation override.
- This keeps `holding_lots` / `current_holdings` / `portfolio_daily_snapshots` mark-to-market
  **completely unchanged** (they already value at `prices.close × qty`, exactly like the held
  US holding HUBS.NYSE). Look-through is additive and can be deferred forever without affecting
  one valuation number.

## 2. Per-kind treatment

| Kind (`security_kind`) | Valuation | In ML/screening? | In allocator? | Discipline model |
|---|---|---|---|---|
| `au_equity` (today) | market price | **yes** | yes | single-name thesis (entry/stop/target/timeline) |
| `etf` | market price (≈NAV) | **no** | no (hand-mandated) | passive mandate: role + target-weight band + distribution + **tracking-difference** |
| `lic` | market price | **no** | no | passive mandate **+ premium/discount-to-NTA band** + franked distribution |
| `reit` | market price | **optionally yes** (equity-like, has fundamentals) | optionally | may keep single-name thesis |
| `hybrid` | market price | **no** | no | income/credit: distribution + call/maturity + credit-event invalidation |
| `us_equity`, `index` | market price | no | no (excluded) | as today (out-of-band) |
| warrant/option (`au_derivative`) | — | no | no | **out of Phase 1** (needs expiry/Greeks model) |

**The passive-mandate "thesis"** reuses the existing `theses` table (its `stop_price`/
`target_price`/`entry_band_*` are already nullable): a mandate is a `theses` row with those
NULL + new nullable columns (`target_weight`, `rebalance_band_pct`, `mandate_role`,
`premium_discount_band`) and a `thesis_kind` discriminator (`single_name_active | passive_mandate`).
The discipline event is **band breach → rebalance**, not price-target hit.

## 3. The keystone + the one load-bearing risk

**Keystone: the `security_kind` enum** (already the deferred `m14_candidate_security_kind_enum`).
`TEXT + CHECK` (matching `underlyings.category`), values
`au_equity | us_equity | index | etf | lic | reit | hybrid`. Migration 0037: add column →
backfill (`au_equity` default; `.INDX`→`index`; foreign suffix→`us_equity`; join
`rs_security_master.security_type='ETF'`→`etf`) → `NOT NULL` + CHECK + index. Only
`etf/index/us_equity/au_equity` are reliably auto-derivable; `lic/reit/hybrid` need enrichment
(GICS Real Estate → reit; curated LIC list; `Preferred Stock/Notes/BOND` → hybrid) — anything
unclassified stays `au_equity` (safe default; ML universe unchanged).

**⚠ The biggest risk — migration ORDERING (do not invert):**
1. Apply 0037 (column + backfill) — behavior-preserving (`au_equity` filter = current active set).
2. **Change every ML/screening reader from `WHERE is_active` → `is_active AND security_kind='au_equity'` BEFORE any ETF is ingested.** (8 readers: `generate_signals`, `retrain_model_a`, `sync_fundamentals`, `signals/loader.py`, `prices/coverage.py`, `validate_price_data`, `ingest_market_context`, `monitor_loader`.)
3. **Only then** change `refresh_universe` to ingest ETF/FUND types.

If ETFs land as `is_active=TRUE` while any reader still says bare `WHERE is_active`, they
**silently enter Model A's training + prediction universe** (zero-filled fundamentals → garbage
signals) — corrupting a model whose reliability is *already* under the rule #11 dispute. "Readers
first, ingestion second" is the whole safety property. Also update `forced_sell_inactive_symbols`
(`build.py:54-58`) → key on `security_kind='au_equity'` (else a held ETF gets auto-liquidated as
a "delisting" — the concrete failure chain), and make `refresh_universe`'s delisting sweep
**per-kind** (never sweep `us_equity`/`index`).

## 4. Phasing + success criteria

| Phase | Delivers | Success criteria |
|---|---|---|
| **1** — hold/value/tax ETFs+LICs | `security_kind` 0037 + reader edits + universe ingest + price-fetch include funds + forced-sell exclusion + passive mandates | James holds VGS.AU+VAS.AU, valued daily in snapshots; ETF disposal → correct CGT (no tax-engine change); `generate_signals`/`retrain` emit **0** signals for any fund (assert in a test); allocator never touches a fund |
| **1b** — distributions/NAV | 0038: `etf_metadata`, `instrument_nav`, `instrument_distributions` + **`tax-alpha.md` amendment** for AMIT cost-base adjustments + LIC cap-gain deduction | distributions tracked; premium/discount + tracking-difference derived; AMIT cost-base handled per spec |
| **2** — look-through exposure | 0039: `etf_holdings(etf_symbol, constituent, weight, as_of)` + exposure-aggregation view (nets direct + fund legs) | "how much BHP do I *really* own?" answerable in one query |
| **3** — overlap/factor/beta | fund overlap warnings, portfolio aggregate beta (closes `m14_candidate_beta_cap`) | overlap warnings fire; one aggregate-beta number in the brief |

**Cheap vs structural:** valuation, CGT-on-disposal, universe widening, passive-mandate fields
are cheap (Phase 1). Structural: the `security_kind` reader audit (the "9+-site migration"),
AMIT/LIC distribution tax (needs spec amendment), constituent look-through (new brittle feed).

## 5. Recommended minimal Phase-1 cut — hold VGS/VAS this week

Ship **0037 (`security_kind` + backfill) + four edits** (Group-A readers → `au_equity`;
`refresh_universe` kind-map + per-kind sweep; `build.py` forced-sell → `au_equity`;
`holdings.py` importer tags kind; `sync_prices` includes funds), then insert VGS.AU/VAS.AU as
`security_kind='etf', is_active=TRUE` + attach a passive mandate. Result: tracked, valued, taxed
(capital-gain path; AMIT deferred to 1b), **invisible to Model A**, never force-sold.

**Reject the tempting one-liner** (insert as `is_active=FALSE` mirroring `AXJO.INDX`): it
re-overloads `is_active` a third time — the exact debt this exists to pay down — and still needs
the forced-sell/sweep edits anyway.

## 6. Why this is worth doing NOW (independent of the Model A P0)

**Rule #11 is moot for passive funds** — no Model A signal ever attaches to an ETF/LIC. So this
expansion advances the discipline/valuation/tax product (north-star moat layers 2–3) on a path
**structurally independent of the Model A signal-reliability dispute.** It's real product progress
that does not wait on the P0.

## 7. Open questions for James (before build)

1. Which funds first? (Confirm VGS.AU + VAS.AU; any LIC — triggers the premium/discount path?)
2. Distributions in Phase 1: manual cash entry (recommended) vs modelled AMIT attribution (needs the `tax-alpha.md` amendment first)?
3. REIT policy: audit which A-REITs are already in as `Common Stock` — keep `au_equity` (retain ML/thesis) or reclassify `au_reit`?
4. Governance: does a passive mandate go through the same `governance_status` approval as a single-name thesis, or auto-approve (as human-authored theses default today)?

**Non-goals:** warrants/options/instalment warrants; running Model A on funds; allocator-
optimising fund weights; intraday NAV; marking LICs at NTA; unlisted managed funds.
