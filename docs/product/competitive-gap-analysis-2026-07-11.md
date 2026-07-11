# Competitive Gap Analysis — asxos (2026-07-11)

**Status:** current
**Scope:** Australian retail-investor tooling landscape vs asxos's model-independent moat
(discipline, tax, theme stewardship) — not the shelved ML/signal layer
**Last verified:** 2026-07-11
**Owner:** `deep-research-agent` (dispatched during James's 8-hour autonomy window); recovered
verbatim from its transcript after a dropped completion notification (see
`docs/product/memory/working/competitive-gap-transcript-report-2026-07-11.md`)
**Superseded by:** N/A

## Calibration note (added 2026-07-11, James)

**"No competitor does X" is not a reason to build X.** James's correction, verbatim: *"Just
because we have something built that no one else does, doesn't mean this is right — never take
what we have as an advantage."* The `[DIFFERENTIATION]` tags below describe competitive
*absence*, not validated user *value* — a capability can be rare because competitors missed it,
or because it isn't actually wanted, or because the specific implementation is wrong even if the
underlying idea is sound. Read every `[DIFFERENTIATION]` tag as **"investigate whether this is
actually right for James,"** not as a build-priority signal on its own. This applies retroactively
to this document's own P1–P6 roadmap implications below — none of them should be sequenced on
"nobody else has this" alone.

## Method & confidence note

Findings are from vendor documentation, help centres, independent review sites, Australian
tax/legal commentary, and ATO-adjacent primary references. Fact is separated from interpretation
throughout. Confidence is rated per claim: **High** = multiple independent or primary sources
agree; **Medium** = single credible source or reconciled-but-conflicting sources; **Low** =
inferred, not directly sourced. Three origin sites (ATO, Heffron, usethesis.com) returned HTTP
403 to automated fetch; those claims lean on search-surfaced summaries and are rated accordingly.

---

## Executive summary

1. **The tax + discipline moat is real white space.** No consumer/retail tool models
   **Division 296**, and the market leader (Sharesight) explicitly says it *cannot* (it can only
   "help estimate" via an unrealised-CGT report). No retail tracker enforces **thesis
   discipline** (structured entry/stop/target/invalidation + revisit cadence) — the closest tool
   (usethesis.com) merely *attaches* a thesis note and is US-only. The **franking 45-day at-risk
   warning** exists only in professional SMSF admin software (Class, BGL Simple Fund 360), never
   in retail trackers. asxos already implements all three. This is the defensible core.
   (Confidence: High)
2. **asxos is already current on the hardest-moving regulation.** Its tax spec v1.5 §6 models the
   *enacted* realised-earnings Division 296 (Royal Assent 13 Mar 2026, commence 1 Jul 2026),
   including the s296-50 cost-base-reset election, dual $3M/$10M thresholds, and CPI indexation —
   not the superseded unrealised/deemed design. A genuine, timely differentiator. (Confidence:
   High)
3. **The real gaps are table-stakes plumbing, not moat features.** asxos lacks broker/CSV trade
   ingestion and automated corporate-actions handling (DRPs, splits, mergers) that every serious
   AU tracker has. For a single power-user this is less about convenience than **data
   integrity** — the differentiated tax engine is only as correct as the lots fed into it (the
   HUBS FX/cost-base incident illustrates the fragility). (Confidence: High)
4. **The regulatory environment favours the single-user design.** The s766B personal-advice
   boundary is safely on the right side for a single-user, non-execution, doesn't-hold-out-as-
   advice tool. The tripwire is any move to multi-user/"peers" or any UX that "nudges" — which
   would import AFSL obligations. (Confidence: High)

---

## Q1 — Competitor-by-competitor (strengths, pricing, weakness on AU tax + on discipline)

Four tiers, because "competitor" means different things for asxos's two moat pillars.

### Tier 1 — AU tax-aware portfolio trackers (the tax-pillar competitors)

**Sharesight** — market leader, Australian-built.
- *Does well:* ATO-ready CGT report using the discount method for >12-month holds and "other
  method" for <12 months; auto-applies the 50% CGT discount by entity type
  (Individual/Trust/SMSF/Company); five sale-allocation methods including **"Minimise CGT"**
  (parcel selection accounting for the discount); captures franking credits on every
  fully-franked dividend and grosses up in the annual taxable-income report; **Unrealised CGT
  report** for tax-loss-sell modelling; auto-tracks trades, dividends, DRPs and 20+ years of
  corporate actions via 200+ broker feeds. (Confidence: High)
- *Pricing:* free up to 10 holdings; AU "Tax" tier around A$59/yr and up; higher tiers by
  holding count. (Confidence: Medium — pricing changes)
- *Weak on (a) AU tax:* **Does not model Division 296** — its own help doc states it "cannot
  directly calculate" it and can only help estimate via the unrealised-CGT report, because it
  can't see total super balance across all funds. **No franking 45-day at-risk warning.** Uses
  the "held more than one year" discount test, not an exposed calendar-precise
  (acquisition + 1yr + 1 day) boundary with near-boundary sell deferral. (Confidence: High for
  Div 296 and 45-day; Medium for calendar-precision)
- *Weak on (b) discipline:* **None.** It tracks performance and tax; there is no thesis object,
  no stop/target/invalidation, no revisit cadence, no pre-emptive discipline alerting.
  (Confidence: High)

**Navexa** — Australian-built challenger.
- *Does well:* solid CGT + dividend tooling; five CGT strategies with manual parcel selection to
  hit a tax-effective outcome; auto-applies the CGT discount; simpler UI than Sharesight.
  (Confidence: High)
- *Pricing:* no permanent free tier; 14-day trial. (Confidence: Medium)
- *Weak on tax:* smaller feature set than Sharesight; no US tax reporting; **no Div 296, no
  45-day at-risk warning.** *Weak on discipline:* none. (Confidence: Medium)

**Snowball Analytics / AllInvestView / taxtallee** — dividend- and asset-coverage-focused
trackers.
- Snowball: strong **dividend** tracking/forecasting + a proprietary "Dividend Rating" and ETF
  look-through ("X-Ray"), but its own docs say **no tax lots / no cost-basis valuations** — so
  it is not a CGT engine at all. AllInvestView is positioned for investors also holding
  bonds/options/custom assets. Both capture franking gross-up. None model Div 296, 45-day, or
  discipline. (Confidence: Medium)

### Tier 2 — research/analysis platforms (adjacent, not tax or discipline)

**Simply Wall St** — visual fundamentals ("Snowflake"), screeners, price-target/valuation,
portfolio integration across ~1,000 brokerages; ~8M users; Premium ~A$10.95/mo, Unlimited
~A$21.50/mo. Not a tax tool; no discipline scaffolding. (Confidence: High)

**Stockopedia** — QVM **StockRanks** (0–100), 350+ screening criteria, 65+ pre-built strategies,
~2,000 ASX/NZX names; ~A$575/yr. Systematic *ranking*, not tax and not discipline. (Confidence:
High)

*Interpretation:* these compete with the **shelved** ML/signal layer, not the moat — so they are
not asxos's real competition post-shelf. Worth noting only to confirm asxos should not re-enter
the "systematic ranking" race.

### Tier 3 — broker-native tracking (Selfwealth, Stake, Pearler)

Lightweight in-app tracking; Pearler has a standalone **franking-credits calculator**; broker
trackers "generally just show the cash dividend without the credit." All three are widely used
precisely *as import sources* for Sharesight/Navexa. No CGT-discount reporting, no Div 296, no
discipline. (Confidence: Medium-High)

### Tier 4 — thesis/discipline & journaling tools (the discipline-pillar competitors)

**Thesis (usethesis.com)** — closest analogue: connects to brokerage, lets you attach an
investment thesis + notes to positions, and sends price/news alerts. But it **supports US
equities/ETFs only**, has **no Australian tax**, and — critically — it *records* a thesis rather
than *enforcing* structured entry/stop/target/invalidation with a mandatory revisit cadence.
(Confidence: Medium — partly from search summary; site returned 403)

**Finbotica / Trademetria / StopLossTracker** — journaling and stop-loss alerting: Finbotica
captures rationale/expectations/exit conditions/outcome; Trademetria adds R-multiples;
StopLossTracker fires trailing/EOD stop alerts. All are US-centric trading journals or
single-purpose alert tools; none combine AU tax, a structured thesis object, and a
governance-grade revisit/invalidation loop. (Confidence: Medium)

*Interpretation:* the discipline market is a scatter of note-taking apps and stop-alert
utilities. **No product fuses disciplined thesis governance with Australian tax intelligence.**
That fusion is exactly asxos's stated moat.

---

## Q2 — Where is the genuine white space?

| Capability | Any consumer tool does it? | asxos status | Verdict |
|---|---|---|---|
| **Division 296 modelling** (realised earnings, $3M/$10M tiers, s296-50 reset election) | **No.** Sharesight explicitly cannot; others silent. | Implemented, spec v1.5 §6, TC-13/14/17/20 | **Genuine differentiation** (High) |
| **Calendar (not day-count) 12-month CGT rule** + near-boundary sell deferral | Trackers use "held >1yr" discount method; "Minimise CGT" is parcel selection, **not** a "wait N days to cross the line" deferral | Implemented: `disposal_date ≥ acquired + relativedelta(years=1) + 1 day`; 30-day boundary-defer in `compute_deltas` | **Differentiation (narrow)** — correctness edge + a deferral behaviour trackers don't have (Medium-High) |
| **Franking 45-day at-risk warning** (s207-145) | Only in **professional SMSF admin** software (Class, Simple Fund 360); **not** in any retail tracker | Implemented: TC-21 `check_45_day_warnings`, wired into `tax_view_smsf()` | **Genuine differentiation at the consumer level** (High) |
| **Enforced thesis discipline** (structured entry/stop/target/invalidation + revisit cadence, surfaced before it costs money) | **No.** usethesis attaches a note; journals record; none enforce a cadence/invalidation loop | Core of the product (theses, thesis_revisions, discipline events) | **Genuine differentiation — the moat** (High) |

**Bottom line:** all four "advanced" capabilities are genuine white space at the consumer level.
Two (Div 296, 45-day) sit only in professional/accountant tooling; two (calendar-precise CGT
deferral, enforced discipline) sit essentially nowhere. asxos already has all four built — the
gap is **surfacing and packaging**, not core engine work.

---

## Q3 — Table-stakes features asxos is missing (that matter for a single power-user)

Ranked by how much they matter to a single serious DIY investor:

1. **Trade/holding-lot ingestion (broker CSV / email / API import).** Every Tier-1 tracker
   auto-imports from CommSec/Stake/Selfwealth/IBKR. asxos requires manual `holding_lots` entry.
   For one user this is survivable, but it is the **single largest table-stakes gap**, and it
   directly threatens the differentiated tax engine: manual entry is where FX/cost-base errors
   enter (cf. the HUBS incident). (Confidence: High)
2. **Automated corporate actions (DRPs, splits, mergers, capital returns, in-specie).**
   Sharesight's 20+ years of corporate-action handling is a core reason people pay. Manual
   handling is both laborious and a correctness risk for CGT cost-base tracking. (Confidence:
   High)
3. **ATO-ready / accountant-ready tax export.** Sharesight's "Tax Pack" (myTax-aligned CGT +
   taxable-income/franking summary) is its killer EOFY feature. asxos computes the numbers but
   does not emit a filing-format export. (Confidence: Medium — inferred from repo scope)
4. **Interactive unrealised-CGT / tax-loss-harvest what-if modeller.** Sharesight/Navexa let you
   model "sell this parcel, net against that loss." asxos has loss-harvest *tagging* (info-only,
   heavy Part IVA/TR 2008/1 disclaimer) and a tax overlay in rebalance, but not an interactive
   planner. (Confidence: Medium)
5. **Dividend income forecasting / DRP schedule.** Snowball/Sharesight forecast forward income.
   asxos tracks dividends but forward-forecasting is not a stated feature. (Confidence:
   Low-Medium)

**Explicitly NOT gaps to chase** (deliberately out of v1 scope per north-star §1.6): web/mobile
UI, real-time data, multi-tenant, brokerage execution. Competitors having slick mobile apps is
not a gap for a CLI+email single-user tool. (Confidence: High)

---

## Q4 — Emerging regulatory risks/opportunities

**Division 296 (opportunity, time-sensitive).** As-enacted position (reconciled across William
Buck, SW Accountants, Accurium, Moore, ATO summaries): Royal Assent **13 March 2026**, commences
**1 July 2026**, first assessments FY2027-28. It taxes **realised** fund earnings (dividends,
interest, rent, realised capital gains — **unrealised gains excluded**, reversing the original
2023 design). Additional **15%** on the earnings proportion attributable to balance between $3M
and $10M (~30% combined with the 15% fund tax), and an **additional 10% (25% total, ~40%
combined)** on the proportion above $10M. Both thresholds **CPI-indexed** ($150k / $500k
increments). Small funds may make an **irrevocable s296-50 election** to reset CGT cost bases to
**market value at 30 June 2026** for Div 296 purposes only. (Confidence: High on design; Medium
on the exact "passed/assented" chronology — see contradictions below.)

*Opportunity for asxos:* the s296-50 election hinges on **market values at 30 June 2026** — a
date just 11 days past. Capturing those reset-date valuations *now* (while fresh) and surfacing
the election trade-off is a concrete, time-boxed, on-moat feature no consumer tool offers.
asxos's single-user nature also **defeats Sharesight's stated blocker** (it can't see TSB across
all funds; asxos can simply take James's TSB as an input).

**s766B personal-advice boundary (risk contained).** Personal advice under s766B(3) requires the
provider to have *considered* the client's objectives/situation/needs; the Westpac appeal (2019
FCAFC 187) confirmed even partial consideration counts. A single-user tool that (a) is the
user's own decision-support, (b) never places orders / moves capital, and (c) doesn't hold
itself out as licensed advice sits clearly on the non-advice side — matching asxos's
non-negotiable #2 (firewall is *execution*, not analysis). **The tripwire is future
multi-user/"peers" expansion or any UX that infers/"nudges" a user's circumstances** — either
would risk classification as personal advice and AFSL obligations. Keep the single-user firewall
load-bearing; treat any peer-expansion proposal as a regulatory-review gate, not a feature
toggle. (Confidence: High)

---

## Contradiction handling (transparency)

- **Div 296 rates looked contradictory across sources** (some "15%/25%", others "30%/40%").
  Reconciled: the **15%/25%** figures are the Div 296 *additional* rates; the **30%/40%**
  figures are the *combined* effective rate including the 15% fund earnings tax. asxos's own
  worked cases confirm the additive structure (TC-17: TSB $12M, earnings $100k → $11,250 tier-1
  at 15% on the (12−3)/12 proportion + $1,667 tier-2 at an extra 10% on the (12−10)/12 slice =
  $12,917). Both framings are correct; they describe different bases. (Confidence: High)
- **"Passed/assented" chronology conflicts:** one thread shows a December 2025 exposure draft
  (Sladen); another shows House 5 Mar / Senate 10 Mar / Assent 13 Mar 2026 (SW Accountants,
  Accurium, Moore) — and asxos's own spec cites Assent 13 Mar 2026. The **enacted-2026** position
  is treated as authoritative for the environment's timeline; the compressed draft-to-assent
  window is Medium confidence but does not change the design asxos must model.
- **usethesis.com feature depth** rests on a search summary (site 403'd); the "US-only,
  attaches-a-note-not-a-cadence" characterisation is Medium confidence.

---

## Roadmap implications for asxos

Six suggestions, prioritised, each flagged **[DIFFERENTIATION]** or **[TABLE-STAKES]**, all
fitting the model-independent moat. None involves an ML/signal engine.

**P1 — Ship the Division 296 "reset-election + realised-earnings" workflow as a first-class
surface. [DIFFERENTIATION, time-sensitive]**
The engine exists (spec §6, TC-20); the gap is a *user-facing decision surface*. Concretely: (a)
capture/confirm **market values as at 30 June 2026** for held lots into `cost_base_div296` now
while fresh; (b) a CLI/brief card that models the s296-50 election trade-off (with the existing
depreciated-lot warning); (c) take James's TSB as an input to compute the tier-1/tier-2
proportions. This is the single most defensible *and* most topical tax feature — no consumer
tool does it, Sharesight publicly cannot, and it exploits asxos's single-user advantage
directly.

**P2 — Fuse the franking-45-day and near-12-month-CGT warnings into the discipline "before it
costs money" lane. [DIFFERENTIATION]**
TC-21 (45-day) and the §5.1 boundary-defer already exist inside the tax module; elevate them
into the **daily brief discipline events** (same lane as stop-breach/revisit-due) so a
near-45-day or near-12-month sell is flagged *pre-emptively*. This is the exact intersection of
the two moats — tax intelligence surfaced through the discipline scaffolding. Only professional
SMSF software has 45-day reports at all, and none frame them as pre-trade discipline. Low build
cost (wiring, not new engine).

**P3 — Prioritise Governance Phase 3 (executable thesis invalidation) + conviction-weighted
revisit cadence as the headline differentiator. [DIFFERENTIATION — the moat]**
The competitor scan is unambiguous: **no product enforces** structured entry/stop/target/
invalidation with a governed revisit cadence. This is Phase 3 (already on the roadmap as "not
started") plus the deferred `m14_candidate_conviction_weighted_cadence`. The competitive
analysis should *raise* its priority: it is the one thing literally nobody else does, and it is
the emotional centre of the product. Frame table-stakes trackers as "they tell you what you own;
asxos tells you when your reason for owning it has broken."

**P4 — Build narrow trade/lot ingestion + corporate-actions handling (CommSec/Stake CSV first).
[TABLE-STAKES — but it protects the moat]**
This is the biggest table-stakes gap, and for a single power-user its value is **data
integrity**, not convenience: the differentiated tax engine is only as correct as its lots (the
HUBS FX error is the cautionary tale). Scope narrowly — a CSV/email importer for the 1–2 brokers
James actually uses, plus DRP/split/capital-return handling — **not** a Sharesight-style
200-broker sync.

**P5 — Add an interactive tax-loss-harvest / unrealised-CGT what-if modeller that respects all
three AU rules at once. [TABLE-STAKES → DIFFERENTIATION when fused]**
Parity with Sharesight/Navexa "Minimise CGT" is table-stakes for a serious AU investor. But
asxos can leapfrog: a harvest planner that simultaneously honours the **calendar 12-month
rule**, the **45-day franking at-risk window**, and the **Div 296 realised-earnings
interaction** would be a combination *no competitor offers*. Keep the Part IVA / TR 2008/1
wash-sale disclaimer verbatim (per portfolio-conventions §I.5); the tool models, it does not
endorse.

**P6 — Emit an ATO/accountant-ready EOFY tax export. [TABLE-STAKES]**
Sharesight's Tax Pack is its retention hook. asxos already computes CGT + franking gross-up;
packaging a myTax-aligned CGT and taxable-income/franking summary closes the one EOFY
table-stakes gap that a power-user notices annually. Lower urgency (EOFY-cyclical) but high
satisfaction-per-effort.

**Sequencing note:** P1 is genuinely time-boxed (the 30-June-2026 reset values are perishable
and the topic is live), so it should jump the queue ahead of current ETF Slice-2 work if the
reset-date valuations aren't yet captured. P2 and P3 are the durable moat and should outrank all
table-stakes (P4–P6). P4 is the one table-stakes item worth doing soon because it protects the
correctness of everything above it. This ordering does not touch the shelved ML engine or rule
#11.

---

## Sources

Division 296 status & design:
- [Better targeted superannuation concessions — ATO](https://www.ato.gov.au/about-ato/new-legislation/in-detail/superannuation/better-targeted-superannuation-concessions)
- [Revamped Division 296 tax pushed back to 1 July 2026 — William Buck](https://williambuck.com/news/in/general/revamped-division-296-tax-pushed-back-to-1-july-2026/)
- [Division 296 tax has passed parliament — SW Accountants & Advisors](https://www.sw-au.com/insights/article/division-296-tax-has-passed-parliament-and-what-it-means-for-large-super-balances/)
- [Div 296 is now law — Accurium](https://www.accurium.com.au/blog/2026/03/div-296-is-now-law-what-you-need-to-know-before-it-starts-on-1-july-2026/)
- [Division 296 Passed — Moore Australia](https://www.moore-australia.com.au/news/division-296-superannuation-changes/)
- [Division 296 Tax Changes Explained: Realised Earnings — Hudson Financial Planning](https://hudsonfinancialplanning.com.au/resources/education-reports/division-296-tax-changes-2025-update/)
- [Division 296 super tax explained — SuperGuide](https://www.superguide.com.au/super-booster/super-tax-accounts-3-million)

Does any tool model Div 296:
- [Division 296 tax and Sharesight — Sharesight Help](https://help.sharesight.com/division-296-tax-and-sharesight/)

Sharesight (tax features, pricing, limitations):
- [Investment Portfolio Tax Reporting — Sharesight AU](https://www.sharesight.com/au/investment-portfolio-tax/)
- [Capital Gains Tax (CGT) Report — Sharesight Help](https://help.sharesight.com/au/capital_gains/)
- [Unrealised CGT Report — Sharesight Help](https://help.sharesight.com/au/unrealised_cgt_report/)
- [Sharesight Review 2025 — Wealth Copilot](https://www.wealthcopilot.com.au/sharesight-review-australia)
- [Sharesight reviews — ProductReview.com.au](https://www.productreview.com.au/listings/sharesight)

Navexa / comparisons / other AU trackers:
- [Navexa: The Intelligent Portfolio Tracker](https://www.navexa.com/)
- [Tax Reporting — Navexa](https://www.navexa.com/au/tax-reporting)
- [Best Sharesight alternatives for Australian investors 2026 — TrackMyShares](https://trackmyshares.com/blog/best-sharesight-alternatives-australia-2026)
- [Best Portfolio Trackers for Australian Investors 2026 — AllInvestView](https://www.allinvestview.com/best-portfolio-tracker-australia/)
- [Snowball Analytics](https://snowball-analytics.com/)

Research platforms:
- [Simply Wall St — Pricing Plans](https://simplywall.st/plans)
- [StockRanks — Stockopedia](https://www.stockopedia.com/stockranks/)
- [Australasian coverage — Stockopedia](https://www.stockopedia.com/learn/our-data/australasian-coverage-462748/)

Broker-native / franking:
- [Franking Credits Calculator — Pearler](https://pearler.com/explore/tools/franking-credits)

Franking 45-day rule:
- [What Is the 45-Day Rule for Franking Credits? — Investax](https://www.investax.com.au/investax_faq/what-is-the-45-day-rule-for-franking-credits)
- [The 45 Day Rule — Class Support](https://support.class.com.au/hc/en-au/articles/360001760656-The-45-Day-Rule)
- [45 Day Holding Period Rule — Simple Fund 360 (BGL)](https://support.sf360.com.au/hc/en-au/articles/360041115192-45-Day-Holding-Period-Rule)
- [Refund of franking credits for individuals — ATO](https://www.ato.gov.au/individuals-and-families/investments-and-assets/shares-funds-and-trusts/investing-in-shares/refund-of-franking-credits-for-individuals)

Thesis-discipline tools:
- [Thesis — Investment Tracker (usethesis.com)](https://www.usethesis.com/)
- [Investment Tracking Journal Software — Finbotica](https://finbotica.com/investment-journal/)
- [StopLossTracker](https://stoplosstracker.com/)

s766B personal-advice boundary:
- [CORPORATIONS ACT 2001 — SECT 766B (AustLII)](https://classic.austlii.edu.au/au/legis/cth/consol_act/ca2001172/s766b.html)
- [ASIC v Westpac case note — MinterEllison](https://www.minterellison.com/articles/case-note-asic-v-westpac-securities-administration-limited-2019-fcafc-187)
- [When is advice 'personal' and not 'general' — Gadens](https://www.gadens.com/legal-insights/when-is-financial-product-advice-personal-and-not-general-under-the-corporations-act-2001-cth/)

Internal asxos references consulted: `docs/product/north-star.md`, `docs/product/roadmap-state.md`,
`docs/foundation/spec/tax-alpha.md` (§6 Division 296, TC-13/14/17/20/21).
