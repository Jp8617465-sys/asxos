# Paper broker research reports — VAS and WES

**Status:** research input / not a canonical `DecisionPacket`
**Provenance:** hand-authored exploratory research. This document did **not** come through
`render_broker_report()` and is not evidence that the render surface produced it. The only
renderer output that counts is an artifact written by `asx decision report` from a persisted
`DecisionCase`, carrying a `delivery_receipts` row whose `render_sha256` matches its bytes.

**As-of:** 7 September 2026 (unless an individual source says otherwise)
**Purpose:** exercise the broker-report render surface with one ETF and one ordinary ASX equity, while making every missing decision input explicit.

> This document is single-user decision-support research for James, not licensed financial advice. It is not an order and does not authorise a purchase, sale, sizing change, or broker action. It uses no Model A output. A live report must be rendered from an admitted immutable `DecisionCase`; this is the cited source brief required to build that case.

## Executive decision

| Instrument | Role being tested | Model recommendation | Why it stops there |
|---|---|---|---|
| VAS | Australian-equity core / benchmark sleeve | **Constructive vehicle; REVIEW portfolio fit** | It is the clean default implementation for a deliberately chosen Australian-equity sleeve. It is not a reason to increase Australian-equity exposure or a substitute for global diversification. |
| WES | Ordinary-equity satellite positive control | **WATCH, not immediate ADD** | The business quality is evident, but the current price appears to require sustained earnings delivery while debt, capex and lithium execution are rising. |

`REVIEW` is the canonical human-memo verdict for a `watch`, `avoid`, or `abstain` state. It is not a disguised buy rating. The correct autonomous action is to keep evidence current and raise a paper case only when the missing gates are supplied.

The useful investment conclusion is therefore asymmetric: **VAS is a sensible instrument if the portfolio first decides it wants more Australian-market beta; WES is a company to watch for a better risk/reward entry or a clearer growth inflection.** Neither conclusion is a personal recommendation or broker instruction.

## 1. VAS — Vanguard Australian Shares Index ETF

### What is verified

- VAS seeks to track the **S&P/ASX 300 Index before fees, expenses and tax**. It is exposure to Australian listed shares and property trusts; it is not a stock-selection thesis. [Vanguard product overview](https://www.vanguard.com.au/adviser/invest/etf?portId=8205&tab=overview)
- Vanguard lists a **0.07% p.a. management fee**, zero indirect costs on its product page, and characterises the risk as **high to very high** with a suggested **7+ year** timeframe. [Vanguard product overview](https://www.vanguard.com.au/adviser/invest/etf?portId=8205&tab=overview)
- The issuer reported A$26.19bn AUM as at 31 July 2026 and an estimated intraday NAV of A$111.45 as at 2 September. The official month-end NAV was A$113.1066 at 28 August. NAV is an instrument value, not necessarily the ASX execution price. [Vanguard overview](https://www3.vanguard.com.au/adviser/invest/etf?portId=8205&productType=etf) [Vanguard prices](https://www.vanguard.com.au/adviser/invest/funds-and-etfs?productType=etf&tab=prices)
- The issuer’s stated trailing average annual total returns, as at 31 July 2026, were 5.79% for one year, 10.24% p.a. for five years and 7.78% p.a. for ten years. These assume reinvested distributions and are historical, not expected returns. [Vanguard performance table](https://www.vanguard.com.au/adviser/invest/funds-and-etfs)
- Vanguard’s published composition example identifies CBA as its largest holding (9.93% as at 24 July 2026). That is enough to show that VAS removes single-company selection risk but does **not** remove Australian market, sector, or top-holding concentration. [Vanguard overview](https://www.vanguard.com.au/adviser/invest/etf?portId=8205&tab=overview)

### Broker-style case

**Investment question:** is VAS the right vehicle for a deliberate Australian-equity sleeve, after accounting for existing Australian holdings and the intended global sleeve?

**Constructive case.** It is a low-cost, rules-based way to obtain broad ASX exposure. The objective, benchmark, fee and underlying market are legible. Its value proposition is therefore implementation discipline—not insight into whether the Australian market will rise.

**Bear case.** Buying VAS can duplicate an existing Australian equity book, especially large financials and resources. It adds market-cap-weighted Australian equity risk, not global diversification. It also retains equity drawdown risk, distribution variability, index changes, tracking difference, bid/ask spread, brokerage and tax consequences.

### Investment stance and price context

**Research stance: constructive on the vehicle; neutral on adding exposure today.** VAS is attractive because it is a simple, low-cost method of obtaining the intended exposure. It has no proprietary earnings catalyst or valuation edge: its return will be the Australian market return less costs, subject to tracking and implementation frictions.

The delayed 7 September market close was about A$112.63, versus an official 28 August month-end NAV of A$113.1066. Those dates differ, so the comparison is **not** a premium/discount conclusion; it is a reminder that a real report needs same-time NAV and executable-price captures. [Delayed VAS market history](https://twelvedata.com/markets/186123/etf/asx/vas/historical-data) [Official NAV page](https://www.vanguard.com.au/adviser/invest/funds-and-etfs?productType=etf&tab=prices)

**What would make it an ADD in a general model portfolio?** Not a lower headline price alone. The model needs evidence that the portfolio is underweight its deliberate Australian-equity sleeve, that direct shares do not already recreate the same bank/resources exposure, and that the global sleeve remains intentional. If those conditions are true, VAS is preferable to trying to choose the next individual Australian winner for the core allocation.

**Falsifiers / monitor conditions.** Re-open the instrument assessment if the benchmark objective, management fee, PDS, index methodology, creation/redemption mechanics, tracking difference, liquidity or distribution-tax character changes. The PDS/document page recorded changes affecting VAS on 1 September 2026; a real pipeline must capture and diff those documents rather than assume an old product description remains true. [Vanguard PDS and offer documents](https://www.vanguard.com.au/personal/support/pds-and-offer-documents)

### Required gates before any paper action

1. Whole-portfolio exposure: current Australian equities, direct-stock look-through, super/other accounts in scope, and deliberate global allocation.
2. Exact benchmark rule: distinguish the fund benchmark (S&P/ASX 300) from the portfolio/outcome benchmark; compare total-return series on a defined provider and treatment basis.
3. Product integrity inputs: dated PDS, holdings, distribution components, tracking difference, NAV and executable price/spread from a permitted source.
4. Capital/risk calibration: loss/drawdown and concentration rules; the current architecture explicitly keeps these owner-specific inputs unresolved.
5. Tax applicability and readiness: distributions/franking must feed the deterministic tax layer; the current typed tax reference has no production producer.

## 2. WES — Wesfarmers Limited

### What is verified

- Wesfarmers reported FY26 statutory NPAT of A$2.874bn. Excluding FY25 significant items, NPAT grew 8.3%; revenue grew 3.4% to A$47.274bn. [Wesfarmers FY26 results](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-20260826214539.pdf?sfvrsn=5483afbb_0)
- FY26 divisional earnings grew at Bunnings (+5.1%), Kmart (+6.0%) and WesCEF (+18.5%), while Officeworks fell 22.2%. The same release identifies temporary working-capital investment and supply disruption exposure in WesCEF and Health. [Wesfarmers FY26 results](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-20260826214539.pdf?sfvrsn=5483afbb_0)
- Operating cash flow fell 6.5% to A$4.272bn and net financial debt increased 25.1% to A$5.295bn. The company expects FY27 net capex of A$1.3–1.5bn, including about A$200m for Mt Holland expansion; it also expects borrowing costs to be higher. [Wesfarmers FY26 results](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-20260826214539.pdf?sfvrsn=5483afbb_0)
- Covalent Lithium refinery ramp-up was affected by odour issues. The issuer expects production rates to accelerate in the second half of FY27 as mitigation solutions are implemented. This is a measurable execution dependency, not background colour. [Wesfarmers FY26 results](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-20260826214539.pdf?sfvrsn=5483afbb_0)
- The announced FY26 ordinary dividend was 222 cents per share, fully franked. The subsequent update set the final-dividend payment date at 7 October 2026; the disclosure is a currency-information update, not a new operating result. [Wesfarmers FY26 results](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-20260826214539.pdf?sfvrsn=5483afbb_0) [ASX dividend update](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/update-dividend-distribution-wes-20260903034219.pdf?sfvrsn=863afbb_0)

### Broker-style case

**Investment question:** do durable retail operations and a diversified portfolio justify a single-company allocation after a valuation, execution-risk and portfolio-overlap test?

**Constructive case.** The FY26 release evidences broad operating contributions, with Bunnings and Kmart delivering earnings growth and positive operating leverage despite cost pressure. The company also reported free cash flow growth, an increased ordinary dividend and stated continued capacity to invest. These are evidence-backed operating observations, not a forecast.

**Bear case.** The same result shows higher debt, lower operating cash flow, a materially higher FY27 investment programme, Officeworks transformation pressure and refinery ramp risk. A tougher household/mortgage backdrop is relevant: the RBA held the cash rate at 4.35% on 11 August, described policy as somewhat restrictive and said inflation remained high with downside growth risks. [RBA decision](https://www.rba.gov.au/media-releases/2026/mr-26-19.html)

### Investment stance and price context

**Research stance: WATCH, rather than immediate ADD.** WES is a strong collection of Australian operating businesses, and the FY26 result supports that quality assessment. The issue is not whether Bunnings and Kmart are good businesses; it is whether the current share price already assumes that their resilience, operating leverage and newer growth platforms will keep delivering while the capital programme and lithium ramp absorb cash.

At a delayed 7 September reference price around A$77.44–78.15, FY26 basic EPS of A$2.534 implies a trailing P/E of roughly **30.5–30.8×**. The A$2.22 fully franked ordinary dividend implies roughly **2.8–2.9% cash yield** before an investor-specific tax treatment. These are mechanical observations, not a target price. [Wesfarmers FY26 results](https://www.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-20260826214539.pdf?sfvrsn=5483afbb_0) [Delayed WES market data](https://au.marketscreener.com/quote/stock/WESFARMERS-LIMITED-6491330/consensus/)

An external consensus feed, which is not yet a permitted production source, reported FY27 average EPS of A$2.72 and an average target near A$77.09. At a price around A$77.44 that is approximately **28.5×** that consensus EPS: the market is not pricing WES as a distressed or neglected business. Treat this only as a cross-check, since the rights, timestamps and contributor methodology must be made explicit before ASXOS admits consensus to a packet. [Consensus source and methodology note](https://stockanalysis.com/quote/asx/WES/forecast/)

**What changes the stance to ADD?** One of two things: (1) a meaningful valuation reset without damage to the core Bunnings/Kmart earnings thesis, producing an agreed margin of safety; or (2) evidence that FY27 earnings/cash conversion and the lithium ramp are exceeding the growth/capital assumptions already embedded in the valuation. **What changes it to AVOID?** Persistent cash/debt deterioration, a material refinery delay, or retail earnings slowing while the high valuation remains.

**Falsifiers / monitor conditions.** The paper thesis fails or must be revised if: (a) Bunnings/Kmart earnings quality deteriorates across two reported periods; (b) working-capital or debt growth is not explained by reversible investment and outpaces operating cash generation; (c) refinery remediation/ramp milestones slip materially; (d) capex, borrowing cost or capital allocation changes invalidate the declared cash-flow assumptions; or (e) a valuation using a pre-declared method no longer clears the required return.

**Events worth monitoring.** The next clear governance/event marker is the AGM on 29 October 2026. The issuer has also published FY26 results, annual report, presentation and the Mt Holland final investment decision in its current announcement archive; an automated evidence agent should watch that archive and hash every newly material disclosure. [Wesfarmers announcements](https://www.wesfarmers.com.au/investor-centre/company-performance-news/asx-announcements)

### Required gates before any paper action

1. A point-in-time price and valuation methodology, including explicit assumptions, sensitivity and required return. Mechanical P/E or dividend-yield calculations alone do not decide value.
2. A real ASX trading-session calendar and licensed/approved adjusted EOD price provider.
3. Portfolio look-through: direct WES ownership, VAS overlap, sector/theme exposure and concentration.
4. Tax assessment data sufficient to produce the typed readiness reference.
5. An independently produced challenge result; no current in-repo challenger surface supplies one.

## 3. Shared market context

The RBA’s current cash-rate target is 4.35%, effective 12 August 2026, with the next scheduled decision on 29 September. The Bank says financial conditions are restrictive, inflation is still too high and consumer spending is slowing gradually. This is a macro condition to monitor, not an input that can by itself generate an ETF or WES rating. [RBA cash-rate overview](https://www.rba.gov.au/cash-rate-target-overview.html) [RBA August decision](https://www.rba.gov.au/media-releases/2026/mr-26-19.html)

This context has different implications:

- **VAS:** it is broad exposure to that Australian macro regime, not protection from it.
- **WES:** its retail and commercial divisions face the demand/cost backdrop directly, while WesCEF also carries commodity, supply-chain and project-specific risks.

## 4. Product gaps exposed by this run

| Gap | Why it matters | Smallest correct next increment |
|---|---|---|
| No real evidence manifest | Web links are not immutable inputs. | Store source URI, retrieval timestamp, document hash, observed/known times and permitted-use metadata. |
| No real ASX calendar | Packet expiry is trading-session based. | Add a verified ASX session-calendar adapter with a source/version and holiday tests. |
| No price-provider contract | A webpage snapshot is not reproducible valuation data. | Define provider, adjustment rule, timestamps, licensing and corporate-action policy. |
| No ETF-specific research adapter | A stock thesis misses benchmark, NAV, tracking, holdings and distribution mechanics. | Add a typed ETF evidence adapter; do not bend an issuer-results adapter until it breaks. |
| No independent challenger producer | `ChallengeResult` is enforced in code but not produced. | Create a read-only challenger route over the frozen evidence manifest. |
| No tax-readiness producer | Tax prose cannot satisfy an action gate. | Build a deterministic `TaxAssessmentReference` adapter over verified holdings/distributions. |
| Capital/risk mandate unresolved | Any number would be invented. | Record James’s loss, drawdown, concentration and sleeve rules as a versioned policy input. |
| Rendering was synthetic only | A good contract had no report surface for real cases. | This branch adds a pure Markdown renderer that consumes an admitted `DecisionCase`; it adds no second recommendation contract. |

## 5. Agent and code routing

The repo already contains model-independent finance capability: `benchmark-performance-analyst`, `thesis-milestone-monitor`, `portfolio-coherence-reviewer` (requiring its Model A residue to be removed), `market-context-narrator`, deterministic tax/portfolio code and the typed decision engine. The missing specialised role is an **ETF integrity analyst**.

That agent should be read-only and produce only a source manifest plus structured observations:

```text
issuer/PDS/index/holdings/distributions/NAV/price source
  -> point-in-time ETF evidence packet
  -> independent challenge
  -> deterministic portfolio + tax readiness
  -> DecisionPacket
  -> broker report renderer
  -> James disposition
```

It must not determine tax, choose a personal allocation, create a trade or mount broker credentials. Those remain deterministic/human-gated boundaries.

## 6. Version-control path

- `F-E2E/r1` remains the ordinary-equity Stage 4 positive-control programme; **WES** can supply its research fixture.
- Treat **VAS** as a separate ETF reference vertical. It must not be used to claim Stage 4 completion, because Stage 4 explicitly calls for an ordinary ASX equity.
- Land this renderer/report as one small draft PR. Follow with independent short PRs for: source manifest, ASX calendar, ETF adapter, challenger, tax readiness and portfolio-policy input. Each should begin from fresh `main` and carry the parent/revision trailers.
