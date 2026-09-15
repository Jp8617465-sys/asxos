# Baseline inquiry — the ASX universe through the valuation model, live, 2026-09-16

**Status:** current — a dated capability baseline, re-run at the F-E2E r2 sprint close for a
before/after (`scripts/research/baseline_inquiry.sql`, parity `scripts/research/parity_check.py`).
**Prompted by:** James, 2026-09-16 — *"run a live inquiry and map the full ASX investments,
ETFs etc included … how would you recommend to structure my portfolio and what investments would
be valued and recommended? … run this first so we have a live baseline of capability."*
**Frame:** a memo under `docs/product/portfolio-manager-charter.md` — model-independent
(`model_independence: model-independent`; rule #11 holds, nothing here reads `signals` or
`model_versions`), every figure traces to a query run on 2026-09-16 against production through
the read-only connector, and **a recommendation is not an order**. Personal use only
(`ASXOS_PERSONAL_USE`, s766B firewall). Nothing was written to production.
**Baseline:** `main` @ `2991d62`. Inputs: `rs_fundamentals_pit` latest usable row per symbol
(periods to 2026-06-30), `prices` to 2026-09-14, `market_context` 2026-09-15 (rf 4.831%),
AUDUSD 0.7134.

## 1. The answer in one screen

- **What the system can do today, live:** value **572 of 1,880** active ASX equities on the
  residual-income model (402 clean, 170 flagged *currency unverified*), rank them within 17 GICS
  sectors and 109 industries, and screen them for liquidity. It cannot value ETFs, cannot measure
  beta, has no non-ASX fundamentals, and none of this is scheduled or reaches the brief — which is
  exactly what the r2 sprint wires.
- **What it finds:** among the 335 liquid valued names (ADV ≥ A$250k, market cap ≥ A$100m),
  **42** are priced below the pre-registered value, **23** of those also survive a 3-period-average
  ROE (the robust set, §4). They are overwhelmingly **REITs below book, listed investment
  companies at a discount to their assets, and cyclicals at high trailing ROE** — plus a handful of
  operating businesses (Helia, Credit Corp, Harvey Norman, Yancoal, Karoon, Pepper Money, Emeco).
- **What it does not find:** growth compounders. The registered convention prices every business
  as earning zero excess return after year 10, so CSL (loss year), WiseTech (0.29× value/price),
  Objective (0.38×), CBA (0.44×) all screen as expensive. **10 of James's 12 research theses screen
  as expensive or cannot be valued** (§5). That is a property of the convention, not evidence the
  theses are wrong — and it is the single most important calibration fact this baseline records.
- **Portfolio structure (§7):** the real book is A$8,431, 100% HubSpot (ESPP, locked), cash zero
  — nothing to restructure until new capital arrives; every new dollar to the passive core until
  HUBS is below the 20% hard trigger (**≈ A$33,700** of new capital). For a declared paper book of
  A$100,000: 7.5% cash, ~60% passive core (VAS / VGS / VGAD, chosen by class and liquidity, not by
  value), ~32% satellite of at most six names from the robust set at ≤ 10% each, LIC exposure
  capped at 15%, REITs at 15%, no name above its entry band.

## 2. The universe, mapped

| Kind | Active | ADV ≥ A$50k | ≥ A$250k | ≥ A$1m | Notes |
|---|---|---|---|---|---|
| `au_equity` | 1,880 | 931 | 592 | 381 | 1,868 carry GICS sector + industry; 1,768 have a year of prices |
| `etf` | 486 | 403 | 276 | 134 | `market_cap` NULL and `sector` blank for all; prices start **2026-07-10** (no 3m/12m returns yet) |
| `hybrid` | 18 | 16 | 13 | 3 | not valued |
| `lic` | 12 | 1 | 1 | 1 | not valued as a kind (LICs classified as `au_equity` are valued on book, §4) |

**Valuation coverage of the 1,880 equities (the gate histogram):**

| Status | n | Meaning |
|---|---|---|
| `roe_nonpositive` | 1,084 | loss-making on trailing twelve months — no residual-income basis |
| `valued` | 402 | positive book, positive ROE, reporting currency AUD or USD |
| `valued_currency_unverified` | 170 | same, but `rs_fundamentals_pit.currency` NULL/blank (backlog C-20) — **valued and flagged**, not hidden |
| `book_nonpositive` | 142 | negative or zero book value per share |
| `currency_other` | 41 | reports in a currency other than AUD/USD — no FX step available |
| `no_pit` | 40 | no point-in-time fundamentals row |
| `roe_missing` | 1 | |

**Value/price distribution (zero-excess, Ke mid 8.681%):** valued names p10 0.24 · p25 0.40 ·
p50 **0.69** · p75 1.15 · p90 1.55; 127 of 402 at or above price. Currency-unverified names run
richer (p50 0.93, 80 of 170) — they skew to small caps with thin disclosure.

## 3. Segment table (GICS sector, liquid = ADV ≥ A$250k)

| Sector | Active | Valued | Valued liquid | Median value/price | Median ROE − Ke | Candidates | Median 12m return | Mkt cap A$bn |
|---|---|---|---|---|---|---|---|---|
| Materials | 668 | 101 | 62 | 0.53 | +3.9 pp | 5 | +36.8% | 1,271 |
| Financials | 179 | 126 | 60 | 0.77 | +0.5 pp | 10 | −6.1% | 927 |
| Health Care | 148 | 29 | 16 | 0.39 | +2.0 pp | 0 | −16.1% | 265 |
| Industrials | 135 | 75 | 48 | 0.42 | +2.2 pp | 2 | +8.1% | 250 |
| Energy | 137 | 32 | 22 | 0.85 | −1.4 pp | 2 | +13.6% | 210 |
| Consumer Discretionary | 109 | 59 | 33 | 0.57 | +3.8 pp | 4 | −29.0% | 200 |
| Real Estate | 61 | 45 | 33 | **1.25** | +0.4 pp | **16** | −18.3% | 166 |
| Communication Services | 57 | 22 | 11 | 0.40 | −1.2 pp | 0 | −20.7% | 156 |
| Consumer Staples | 49 | 18 | 11 | 0.58 | −2.9 pp | 0 | −16.2% | 108 |
| Information Technology | 130 | 39 | 22 | 0.31 | +3.8 pp | 0 | −19.6% | 81 |
| Utilities | 23 | 6 | 2 | 0.74 | +2.8 pp | 1 | +12.2% | 62 |
| (six small or legacy-taxonomy sectors) | 164 | 20 | 15 | — | — | 2 | — | 118 |

Read: the model's candidates cluster where price is near book (REITs after the rate cycle,
LICs at NTA discounts) and where trailing ROE is cyclically high (miners). Sectors priced on
growth (IT, Health Care, Communication) produce **zero** candidates by construction.

## 4. What is valued and would be recommended — and under which convention

**Counts among the 335 liquid valued names:**

| Convention | Candidates (value ≥ price, ROE > Ke) | Median value/price |
|---|---|---|
| zero-excess, trailing ROE (**pre-registered**) | **42** | 0.59 |
| fading-excess w = 0.5 (illustrative, *not* pre-registered) | 59 | 0.66 |
| zero-excess at 3-period-average ROE (sensitivity) | 35 | 0.55 |
| **both** zero-excess and average-ROE (**robust set**) | **23** | — |

**The robust set (REPORT D), ranked by the lower of the two value/price ratios.** Target =
probability-weighted value at Ke mid, franking-adjusted; bear = 0.70× ROE scenario.

| Symbol | Name | Sector · industry | Close | Target | Bear | V/P (min) | ROE ttm / 3-yr | Payout | ADV A$k | Cap A$m | 12m | Yield | Flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WAA | WAM Active | Financials · Capital Markets (LIC) | 0.98 | 2.70 | 2.18 | 2.24 | 0.20 / 0.14 | 0.22 | 439 | 150 | +2% | 7.3% | ccy unverified |
| KCN | Kingsgate Consolidated | Materials · gold | 5.48 | 9.08 | 5.61 | 1.51 | 0.50 / 0.47 | 0.09 | 7,781 | 1,415 | +88% | 1.8% | ccy unverified; cyclical |
| PPM | Pepper Money | Financials · Consumer Finance | 1.745 | 2.61 | 2.31 | 1.50 | 0.12 / 0.12 | 1.00 | 578 | 784 | −19% | 14.9% | payout clipped at 1.0 |
| WQG | WCM Global Growth | Financials · Capital Markets (LIC) | 1.97 | 2.87 | 2.50 | 1.46 | 0.12 / 0.15 | 0.38 | 480 | 570 | +4% | 5.4% | |
| PE1 | Pengana Private Equity | Energy(mis-tagged) · LIT | 1.415 | 2.58 | 2.16 | 1.38 | 0.17 / 0.09 | 0.20 | 782 | 384 | +6% | 4.6% | ccy unverified |
| EHL | Emeco Holdings | Industrials · equipment | 1.12 | 1.53 | 1.36 | 1.36 | 0.10 / 0.10 | 0.00 | 631 | 588 | −4% | — | |
| FGX | Future Generation Australia | Industrials(mis-tagged) · LIC | 1.26 | 1.69 | 1.52 | 1.34 | 0.09 / 0.09 | 0.74 | 405 | 525 | −5% | 7.5% | |
| BWP | BWP Trust | Real Estate · Retail REIT | 3.58 | 5.20 | 4.57 | 1.32 | 0.12 / 0.09 | 0.35 | 4,730 | 2,780 | −3% | 5.4% | ROE includes revaluations |
| HM1 | Hearts and Minds | Financials · Capital Markets (LIC) | 2.83 | 3.69 | 3.42 | 1.30 | 0.06 / 0.09 | 0.91 | 766 | 657 | −16% | 6.5% | |
| AIS | Aeris Resources | Materials · copper | 0.47 | 1.22 | 0.88 | 1.30 | 0.30 / 0.12 | 0.00 | 5,050 | 713 | +36% | — | ccy unverified; cyclical |
| **HLI** | Helia Group | Financials · Insurance | 5.42 | 6.71 | 5.64 | 1.23 | 0.24 / 0.23 | 1.00 | 5,218 | 1,441 | −5% | 20.7% | yield includes specials; run-off risk |
| PGF | PM Capital Global Opportunities | Financials · Capital Markets (LIC) | 3.18 | 4.11 | 3.34 | 1.21 | 0.20 / 0.18 | 0.26 | 1,728 | 1,935 | +22% | 4.1% | |
| **KAR** | Karoon Energy | Energy · oil & gas | 1.835 | 2.18 | 1.92 | 1.19 | 0.12 / 0.18 | 0.44 | 11,031 | 1,278 | +13% | 5.7% | USD reporter, converted |
| **HVN** | Harvey Norman | Consumer Disc. · Broadline Retail | 4.13 | 5.00 | 4.44 | 1.18 | 0.11 / 0.10 | 0.68 | 9,847 | 5,196 | −42% | 7.0% | book includes property |
| **YAL** | Yancoal Australia | Energy · coal | 6.15 | 7.20 | 6.76 | 1.17 | 0.05 / 0.13 | 1.00 | 19,647 | 8,213 | +16% | 9.5% | thermal coal; James's exclusion list is empty |
| CWP | Cedar Woods Properties | Real Estate · developer | 6.57 | 8.13 | 7.10 | 1.16 | 0.12 / 0.10 | 0.43 | 1,019 | 556 | −12% | 5.0% | |
| KKC | KKR Credit Income Fund | Energy(mis-tagged) · LIT | 2.07 | 2.35 | 2.17 | 1.13 | 0.08 / 0.10 | 1.00 | 965 | 729 | −12% | 9.7% | ccy unverified |
| **CCP** | Credit Corp Group | Financials · Consumer Finance | 13.78 | 16.84 | 14.78 | 1.13 | 0.12 / 0.09 | 0.44 | 5,611 | 963 | −16% | 4.9% | |
| FGG | Future Generation Global | Financials · Capital Markets (LIC) | 1.585 | 1.77 | 1.62 | 1.12 | 0.08 / 0.11 | 0.64 | 499 | 643 | +1% | 4.9% | |
| FML | Focus Minerals | Materials · gold | 2.20 | 12.95 | 6.34 | 1.10 | 0.74 / 0.25 | 0.00 | 614 | 628 | +236% | — | peak-cycle ROE; avg-ROE value 2.42 |
| RG1 | Regal Partners Global | Financials · Asset Mgmt (LIC) | 2.57 | 4.60 | 3.61 | 1.09 | 0.23 / 0.10 | 0.21 | 944 | 605 | +44% | 4.7% | ccy unverified |
| LSF | L1 Long Short Fund | Financials · Capital Markets (LIC) | 4.75 | 7.80 | 5.99 | 1.05 | 0.25 / 0.13 | 0.17 | 2,221 | 2,970 | +45% | 3.6% | |
| PPC | Peet | Real Estate · developer | 1.68 | 2.07 | 1.76 | 1.03 | 0.16 / 0.11 | 0.52 | 1,982 | 787 | −2% | 6.8% | ccy unverified |

Bold = operating businesses whose thesis type is "earning above cost of equity, priced below
value" rather than "assets at a discount". Eleven of the 23 are LICs/LITs (a discount-to-NTA
thesis, itself diversified), five are property.

**The top of the unfiltered list is a warning, not a pick.** By trailing ROE alone, Metro Mining
(ROE 0.76, value/price **94×**) and Focus Minerals (5.9×) lead REPORT C; at 3-year-average ROE
Metro falls to 0.92× and Cromwell Property to 0.70×, Premier Investments to 0.99×. Trailing ROE
at a cycle peak is the model's largest single distortion; the sprint's ranker uses the average
(S4), and the prereg's multiplicative levers were designed for exactly this reason.

## 5. Target prices, horizons and James's existing theses

**Per-name outputs the baseline gives** (conventions James can change; recorded here so the sprint
proposes theses in exactly this shape): target = probability-weighted value at Ke mid; entry band
upper = 0.80 × target (20% margin of safety), lower = 0.65 × target; stop = 0.80 × entry upper
(20% drawdown from entry); horizon 12 months to re-test. Annualised return if price converges to
target in 1 / 2 / 3 years, plus yield (grossed up for franking at 30/70 for a resident):

| Symbol | Close | Target | Bear | Upside | 1y | 2y | 3y | Yield (grossed) | Entry ≤ | Stop |
|---|---|---|---|---|---|---|---|---|---|---|
| HLI | 5.42 | 6.71 | 5.64 | +24% | +24% | +11% | +7% | 20.7% (26.8%) | 5.37 | 4.29 |
| CCP | 13.78 | 16.84 | 14.78 | +22% | +22% | +11% | +7% | 4.9% (7.0%) | 13.47 | 10.78 |
| HVN | 4.13 | 5.00 | 4.44 | +21% | +21% | +10% | +7% | 7.0% (10.0%) | 4.00 | 3.20 |
| YAL | 6.15 | 7.20 | 6.76 | +17% | +17% | +8% | +5% | 9.5% (13.6%) | 5.76 | 4.61 |
| KAR | 1.835 | 2.18 | 1.92 | +19% | +19% | +9% | +6% | 5.7% (5.7%) | 1.74 | 1.40 |
| PPM | 1.745 | 2.61 | 2.31 | +50% | +50% | +22% | +14% | 14.9% (21.3%) | 2.09 | 1.67 |
| EHL | 1.12 | 1.53 | 1.36 | +37% | +37% | +17% | +11% | — | 1.22 | 0.98 |
| KCN | 5.48 | 9.08 | 5.61 | +66% | +66% | +29% | +18% | 1.8% | 7.26 | 5.81 |
| BWP | 3.58 | 5.20 | 4.57 | +45% | +45% | +21% | +13% | 5.4% | 4.16 | 3.33 |
| LSF | 4.75 | 7.80 | 5.99 | +64% | +64% | +28% | +18% | 3.6% (5.1%) | 6.24 | 4.99 |
| PGF | 3.18 | 4.11 | 3.34 | +29% | +29% | +14% | +9% | 4.1% (5.9%) | 3.29 | 2.63 |
| WQG | 1.97 | 2.87 | 2.50 | +46% | +46% | +21% | +13% | 5.4% (7.7%) | 2.30 | 1.84 |
| HM1 | 2.83 | 3.69 | 3.42 | +30% | +30% | +14% | +9% | 6.5% (9.3%) | 2.95 | 2.36 |

Where close is already inside the entry band (HLI, CCP, HVN, YAL, KAR, HM1, PGF, CWP), the
system would propose the thesis at once; where close is above it (PPM, KCN, BWP, LSF, WQG, EHL),
it would propose a *watching* thesis with the band as the trigger. These are convergence
arithmetic, not forecasts: nothing here says *when* price meets value, and the outcome loop
(21 / 63 / 126 sessions) has not yet observed a single name.

**James's twelve research theses, same lens** (zero-excess / fading-excess / average-ROE
value-to-price):

| Symbol | zx | fx | avg3 | 3-yr ROE | Read |
|---|---|---|---|---|---|
| ATR | 1.66 | 2.03 | 0.61 | −0.08 | trailing ROE is a one-off; ADV A$38k, below the liquidity floor |
| BLX | 0.64 | 0.70 | 0.69 | 0.16 | |
| CBA | 0.44 | 0.48 | 0.43 | 0.13 | reported-book 67.50 vs 154.97; tangible-base Phase 1 run withdrew it on `currency_null` (now AUD) |
| OCL | 0.38 | 0.53 | 0.39 | 0.34 | currency unverified |
| WTC | 0.29 | 0.29 | 0.31 | 0.11 | currency unverified |
| KPG | 0.16 | 0.17 | 0.17 | 0.13 | |
| TPW | 0.16 | 0.14 | 0.16 | 0.05 | currency unverified |
| NEC · WA1 · BAP · EBR · LLC | — | — | — | negative | not valued: trailing ROE ≤ 0 |

One of twelve screens as undervalued and it is illiquid. Under the charter this is *evidence*,
not a verdict on the theses: the model has no growth term by pre-commitment, and the Phase 1 note
("the terminal-value convention is the only input not yet tested") stands. The sprint persists
**both** conventions side by side (0054's discriminator exists for this) so the queue-wide
calibration metric — share of names valued above market — becomes interpretable.

## 6. ETFs — mapped, not valued

No holdings, MER or index data exist for any ETF, and their price history begins 2026-07-10, so
there is no valuation and no trailing return. Classification is by **name keyword**; liquidity is
the 90-session ADV.

| Class | n | Liquid (≥ A$250k) | Most liquid (ADV A$m) |
|---|---|---|---|
| ASX broad | 14 | 13 | VAS 36.4 · A200 21.0 · IOZ 15.0 · STW 10.1 |
| ASX factor / sector / active | 51 | 36 | VHY 16.8 · ETPMAG 7.5 · VAP 4.5 · MVW 4.2 · AQLT 3.0 |
| Global unhedged | 146 | 88 | VGS 32.9 · IVV 23.4 · NDQ 13.7 · BGBL 10.9 · QUAL 9.6 · VEU 8.8 |
| Global hedged | 46 | 24 | VGAD 11.8 · IHVV 9.3 · HGBL 7.0 |
| Diversified multi-asset | 25 | 9 | VDHG 5.2 · DHHF 2.7 · VDGR 2.3 |
| Credit / bond | 64 | 36 | VBND 8.7 · SUBD 6.7 · VAF 5.2 · QPON 4.9 |
| Government / inflation bond | 20 | 12 | VGB 5.0 · ILB 2.9 · AGVT 2.0 |
| Cash | 7 | 4 | AAA 20.9 · BILL 3.7 · MMKT 3.2 |
| Commodity / crypto | 30 | 22 | PMGOLD 13.5 · GOLD 12.5 · GDX 8.6 |
| Leveraged / complex | 38 | 15 | GEAR 6.4 · BBOZ 5.0 (excluded from any structure below) |
| Thematic | 9 | 4 | XMET 1.1 |
| Unclassified | 36 | 13 | EMKT, IKO, IJR, JEME, F100, IVE, JEPI … |

## 7. Portfolio structure — a recommendation, not an order

**Backdrop (2026-09-15):** classifier regime `risk_off_orderly`; ASX 200 8,749.9 with 28.5% of
constituents above their 200-day average; AVIX 14.1 (calm); RBA cash 4.35%; 10-year 4.831%;
AUDUSD 0.7134. Benchmark measurement is **unavailable** (no licensed XJOAI series, policy F1);
`AXJO.INDX` is price-only context.

**The real book, today.** A$8,431, one lot: 24 HUBS.NYSE at US$187.54 (ESPP, locked), cash A$0,
unrealised FX loss A$894 at 0.7134. Profile `balanced`: per-name cap 10%, sector cap 30%, minimum
position A$1,000, cash floor 0, leverage cap 1. Employer-stock ceiling (2026-07-13 ruling): soft
flag 10%, hard trim trigger 20%, enforcement "dilute with new capital". The book is 100% employer
stock by construction, so there is nothing to sell and nothing to size: **the only structural
action is where new money goes.** Arithmetic: HUBS falls below the 20% trigger once total capital
exceeds A$42,155, i.e. after **A$33,700** of new contributions; below 10% after A$75,900. With a
A$1,000 minimum position and a 10% cap, no satellite position is feasible until the book is
≥ A$10,000 per name-slot — practically, until it is ≥ A$25,000.

**So, for the real book:** every new dollar to the passive core in a 60 / 40 split of ASX broad
(VAS or A200) and global unhedged (VGS or BGBL), until HUBS is under 20%. That is not a value
call; it is the cheapest, most liquid way to dilute a single-name, single-currency, single-employer
exposure, and it is what the policy already says.

**The declared paper book (A$100,000, arbi-declared, paper only — not P5-01 calibration):**

| Sleeve | Weight | Contents | Why |
|---|---|---|---|
| Cash | 7.5% | AAA | `target-architecture.md` floor; the profile's 0% is a setting, not a policy |
| Core — ASX broad | 30% | VAS (ADV A$36m) | the benchmark exposure the theses are measured against |
| Core — global unhedged | 20% | VGS | the separately-reported global sleeve (policy F2); unhedged keeps the AUD diversifier |
| Core — global hedged | 10% | VGAD | halves the currency bet on the global sleeve |
| Satellite — operating businesses | ≤ 20% | up to four of HLI · CCP · HVN · KAR · YAL · PPM · EHL at ≤ 5% each, only inside the entry band | the model's actual finds; four names at 5% respects the 10% cap with room to add on a bear-scenario price |
| Satellite — discount-to-assets | ≤ 12.5% | at most two LICs (PGF · LSF · WQG · HM1) and one REIT/developer (BWP · CWP) at ≤ 5% | a different thesis type (NTA discount); capped so "cheap" does not become "all funds" |

Sizing is equal-weight placeholder: the inverse-vol sizer exists (`sizer.py`) but is pinned to
zero until the paper book has a writer (sprint S3). Sector caps hold (Financials ≤ 30% including
LICs). Deliberately excluded: leveraged/complex ETFs; any name outside its entry band; any name
where the average-ROE value is below price (Metro Mining, Cromwell, Premier); Focus Minerals and
Aeris on peak-cycle ROE; anything with ADV under A$250k.

**Caveats the charter requires, stated:** the allocator is risk-blind to ASX beta clustering — the
caps above do not protect against co-movement, and REITs plus rate-sensitive LICs move together;
capital preservation in a 2008/2020 drawdown is James's responsibility. Coal (YAL) is on the list
because James's `excluded_sectors` is empty — an exclusion is a one-line profile change.

## 8. Capability scorecard (the baseline the sprint is measured against)

| Question | Today | Changes with |
|---|---|---|
| Value an ASX equity from point-in-time fundamentals | **yes**, 572 names, by hand through SQL | S1 makes it weekly and persisted |
| Value the whole universe | partial: 1,084 loss-makers and 142 negative-book names have no basis; 746 rows lack a currency | C-20 currency backfill; a second method for loss-makers is r3+ |
| Target price, bear/base/bull, Ke band | **yes** (§5) | S1 persists; S4 writes them into theses |
| Entry band / stop / horizon | yes, by a stated convention | S4; James can change the convention |
| Compare within sector / industry | **yes**, 1,868 tagged | S6 renders it |
| Realised 3/6/12-month returns for context | equities yes; ETFs **no** (history from 2026-07-10) | time |
| Measure beta | **no** (71 AXJO sessions vs 250 floor) | M3 backfill |
| Value an ETF | **no** (no holdings/MER/index data) | r3 data spike |
| Global equities | **no** non-ASX fundamentals | r3 spike with a spend estimate |
| Challenge a thesis independently | code exists, hand-run, 2 packets ever | S2 + S5 on a schedule |
| Put any of this in the daily brief | **no** | S6 |
| James approves or disposes from a phone | **no** | S8 |
| Learn from outcomes | t0/observe exist, never scheduled | S7 |
| Benchmark after tax vs XJOAI | **unavailable** by policy | licensed series (James) |

## 9. Method notes and limits (for the record)

- Parity: the SQL reproduces `value_per_share` to ≤ 0.000001 on CBA, NAB, WES, BHP, WTC at all
  three Ke points (`scripts/research/parity_check.py`).
- Base: **reported book** (`book_value_ps`, `roe`), not tangible common equity. On that base NAB is
  25.96 (0.67× price) vs 24.66 on the Phase 1 tangible base; CBA 67.50 (0.44×). Both conventions
  should be persisted; the sprint's S1 records `return_base` per run.
- Payout = dividend / EPS clipped to [0, 1], 0 when EPS ≤ 0 or no dividend (486 names had both
  inputs). Clipping at 1.0 (Wesfarmers, Pepper Money, Helia, Yancoal) holds book flat rather than
  shrinking it — a conservative simplification, stated.
- Franking: `franking_avg_pct` as reported; 0 where absent. Company tax 30%.
- Ke band is the cited **bank** beta band applied universe-wide; a sector-specific Ke is not
  available until beta can be measured. Value moves ~2–3% across the band (Phase 1 finding holds).
- USD reporters converted at spot 0.7134; `currency_other` (41 names) not valued.
- The fading-excess convention (w = 0.5) is shown only alongside the registered one and only as
  a count; the standing pre-commitment (no terminal excess added to close a gap) is intact.
- No writes; no `signals`; no capital action. Re-run after the sprint with the same file and
  compare REPORT B to `valuation_runs`.
