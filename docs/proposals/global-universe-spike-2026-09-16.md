# Global-universe data spike (F-E2E r2 S11, backlog A-41)

**Research only. No build, no data pull, no spend committed.** James, 2026-09-16: "find
investment opportunities in the ASX and global investment universe." This spike answers
what a global (non-ASX) opportunity set would cost and what it would need, so r3 can scope
it with a stated A$/day number rather than discovering the cost after building it.

## 1. What exists today (measured)

- `universe` has **2,396 active rows**; only **two** are not `.AU`: `AXJO.INDX` (the ASX 200
  index, price context only) and `HUBS.NYSE` (one held US equity). No ASX-quoted global ETF
  or dual-listed name is in the universe today. [supabase-ro, 2026-09-16]
- `rs_fundamentals_pit` / `rs_financial_statements` are populated for ASX equities only, via
  EODHD's `/fundamentals/{symbol}` endpoint (`asxos/ingestion/eodhd.py:89-90`). `HUBS.NYSE`
  has price history but no fundamentals row — it is not run through the valuation sweep
  (`asxos/domain/valuation/universe.py`'s `security_kind='au_equity'` filter,
  `.claude/rules/portfolio-conventions.md` §"`universe.is_active` overload").
- `EODHD_API_KEY` is already a repo secret, used by `daily-brief.yml` and `weekly-research.yml`
  for prices and ASX fundamentals. The **plan tier and its daily call quota are not visible
  from this session** — that is a billing fact, not a code fact, and needs verification with
  James before any global pull is scoped. [low confidence: plan tier]

## 2. Source options for non-ASX fundamentals

| Source | Coverage | PIT availability | Cost | Confidence |
|---|---|---|---|---|
| **EODHD Fundamentals** (already integrated) | 70+ exchanges globally per EODHD's own listing | Filing/report dates present (same shape this codebase already parses via `derive_knowledge_date`) | Fundamentals Data Feed **€59.99/mo** (≈A$103/mo at AUD/EUR ≈0.581) as a *separate* add-on from the price feed; each fundamentals request consumes **10** of the plan's daily API-call quota | medium — pricing page retrieved 2026-09-16, but James's actual current plan/quota is unverified |
| **SEC EDGAR company facts (XBRL)** | US-listed companies only, via CIK | Filing dates official and immediate (<1 min processing lag per SEC) | **Free**, no key, bulk `companyfacts.zip` nightly archive | high — official U.S. government source, well documented |
| **Financial Modeling Prep (FMP)** | "Ultimate" tier: 70,000+ securities, 60+ exchanges, 46 countries; lower tiers are US/UK/Canada-only | Historical fundamentals; PIT filing-date granularity not confirmed from the pricing page alone | **$19/mo** flat is advertised for one product line; the tier with global coverage ("Ultimate") is priced separately and not confirmed from search alone | low-medium — pricing page structure is unclear on which tier is "$19/mo" vs "Ultimate"; needs a direct quote before relying on the number |

**Recommendation for r3:** SEC EDGAR for a US starter set (free, official, and this codebase
already has a PIT-date parser to reuse) plus the **existing** EODHD subscription extended to
cover non-US names only if a specific ex-US universe is wanted later. Do not add a new paid
provider (FMP) until EODHD's own global fundamentals tier is priced against a real quote.

## 3. Starter universe options

**(a) ASX-quoted global exposure** — ASX-listed international ETFs (e.g. `VEQ`, `IAA`, `ASIA`
per Market Index's ETF list [asxetfs.com, marketindex.com.au, retrieved 2026-09-16]) and the
handful of dual-listed large caps. This needs **no currency conversion or foreign-fundamentals
source at all**: an ETF's own NAV and distribution history come from the same ASX/EODHD price
feed already in place, and the residual-income valuation model this codebase uses does not
apply to a fund (no per-share book value/ROE) — so this path is a **screening and discovery
change, not a fundamentals-source change**. Roughly 20-40 ASX-quoted international ETFs exist;
a weekly refresh is 20-40 extra price-history calls, negligible against the existing EODHD
price-feed cost.

**(b) A US/UK large-cap starter set** — S&P 100 + FTSE 100 ≈ 200 names. Needs real non-AU
fundamentals (option 2's sources), FX conversion for every valuation input
(`asxos/domain/prices/fx.py`, already built for `HUBS.NYSE`), and a currency-aware franking
rule (there is none — see §4). This is a genuine fundamentals-source integration, materially
larger than (a).

## 4. Tax and withholding for non-AU names

- **Franking gross-up (spec §3) is Australian-only.** US and UK dividends carry no franking
  credit; the S9 tax feed already refuses this (`asxos/domain/tax/feed.py::tax_reference_for`
  gates a `pass` on a `.AU` symbol).
- **US withholding**: Article 10 of the US–Australia tax treaty limits withholding on US
  dividends paid to an Australian resident individual to **15%** (down from the US statutory
  30%), conditional on filing IRS Form W-8BEN with the broker/paying agent. [taxsummaries.pwc.com,
  brighttax.com, retrieved 2026-09-16 — high confidence, treaty text is stable]
  `HUBS.NYSE`'s dividend/withholding treatment is out of this codebase's tax module entirely
  today (spec §1 explicitly reserves "foreign holdings tax treatment... treaty withholding
  credits, foreign tax offsets" for v2) — a US-name starter set would need that reservation
  lifted, which is a spec amendment, not a code change alone.

## 5. A$/day estimate

| Option | Extra weekly cost | Extra daily calls (prices) | Under/over A$50/day cap |
|---|---|---|---|
| (a) ASX-quoted global ETFs, screening only | **A$0** — reuses the existing EODHD price feed and subscription | ~20-40/week ≈ 3-6/day | **Under** |
| (b) US/UK 200-name starter, EODHD fundamentals add-on | ≈A$103/mo ÷ 30 ≈ **A$3.40/day**, plus ~200 names × 10 calls/fundamentals-refresh/week ≈ 2,000 calls/week against the plan's daily quota (quota itself unverified) | ~200/day for prices | **Under A$50/day on the subscription cost alone** — but the call-quota headroom against James's actual EODHD plan is unverified and must be checked before committing |
| (b) alternative: SEC EDGAR (US names only) + no new subscription | **A$0** (free, official) | ~200/day for prices only; fundamentals via nightly bulk archive, not per-call | **Under**, and the cheapest path to a real US starter set |

**All estimates here are under the A$50/day cap** (AGENTS.md §2.3), so under the letter of that
rule none of this needs James's sign-off before a build — this spike is filed for scoping and
sequencing, not because it is over the line. The one number that must be confirmed before any
pull is James's actual EODHD plan tier and remaining daily-quota headroom.

## 6. Risks and recommended r3 shape

- **Risk:** `universe.is_active` overload (already a documented `m14_candidate_security_kind_enum`
  gap) makes adding a `security_kind` for a global ETF or US equity another suffix-convention
  patch, not a clean addition, until that enum lands.
- **Risk:** the valuation model (residual income on book value/ROE) does not apply to an ETF at
  all; a global-ETF discovery path needs a different, simpler screen (yield, tracking, expense
  ratio), not a variant of the existing sweep.
- **Risk:** a US-name starter set reopens a spec v1 non-goal (§1: "foreign holdings tax treatment...
  reserved for v2") — that reservation would need a deliberate, James-visible spec amendment,
  not a quiet widening alongside a data-source change.

**Recommended r3 shape, smallest first:**
1. **ASX-quoted global ETFs** (§3a): a discovery/screening extension, zero new cost, zero new
   tax-module surface. The natural next slice after r2's discovery ranker.
2. **US large-cap via SEC EDGAR** (§3b, free path): a genuine new fundamentals source, gated on
   (i) a `security_kind` enum or an equivalent explicit non-AU marker, and (ii) a spec amendment
   lifting the v1 foreign-holdings reservation for at least dividend withholding.
3. Defer a second paid data subscription (FMP or an EODHD tier upgrade) until (1) and (2) show
   the format is worth the recurring cost.

No build in this PR. r3 scoping picks up here.
