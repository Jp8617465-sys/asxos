# HUBS.NYSE — on-demand position review and forecast

**Status:** current
**Scope:** thesis_id=2 / holding_lots.id=1 — the only real-capital position in the book
**Prepared:** 2026-08-21 (on demand, James)
**Data as-of:** prices/FX/snapshot 2026-08-20 (latest closed session); DB read live
**Method:** direct read of `theses`, `thesis_revisions`, `holding_lots`, `prices`, `fx_rates`,
`portfolio_daily_snapshots`, `holding_news`, `market_context`, `job_runs`, `fundamentals`, `rs_*`,
plus the discipline/trajectory modules replayed by hand against the live row.
**Firewall:** evidence only. Nothing below is a recommendation to buy, sell, hold or trim
(s766B / Westpac v ASIC; `portfolio-conventions.md` Part 0 Q1). Where a price level is named it is
arithmetic against the ladder James himself recorded, not a view on merit.
**Rule #11:** no Model A output is used anywhere in this review. `signals` has **zero rows** for
HUBS.NYSE in any case.

---

## 1. Verdict

**The position is winning and the scaffolding around it is not.**

The trade is up **+27.9% in USD** and **+16.0% in AUD**, beating the XJO total-return benchmark by
**~11 percentage points** since entry, and the trajectory classifier reads **ON TRACK** (40.1% of the
way to target against a 22.2% linear expectation at day 81 of 365 — 1.8x pace).

Every defect found is in the *discipline layer*, which is the product's #1 moat claim:

1. The recorded ladder and the recorded anchor are on **two different price bases**, so the stop
   reads as violated on 77% of sessions since entry. A stop that fires three days in four carries
   no information.
2. The thesis has **not been revised since 2026-07-04** — through a scheduled earnings print that
   moved the stock 19% in a day and that the thesis itself had pre-registered falsifiers for.
   Revisit is **18 days overdue**.
3. `timeline_days = 365` puts the thesis deadline at **2027-05-31**, which is **one day short** of
   CGT-discount eligibility (2027-06-01). The thesis text says "hold to the 12-month CGT discount
   date"; the field encoding it is off by one.
4. The **cost base is still unresolved** — 0.6450 vs 0.7171 acquisition FX is a **A$701** swing and
   the difference between reporting +16.0% and +29.0%.
5. HUBS has **zero rows** in `fundamentals` and in *every* `rs_*` research-store table. The only
   position carrying real money is the one security the research pipeline does not cover.

None of this is currently actionable as a trade — the ESPP window is locked (`tax_notes`,
2026-07-04) — which is exactly why it is worth fixing now, while the cost of being wrong is zero.

---

## 2. Position — the numbers

| | |
|---|---|
| Lot | `holding_lots.id=1`, 24 shares, acquired 2026-05-31, `account_type=individual` |
| Fill | **US$187.54** — confirmed as exactly 85% of the 2026-05-29 close (US$220.63); the 15% ESPP plan discount ties to the cent |
| Last close | **US$239.86** (2026-08-20) |
| Market value | US$5,756.64 → **A$8,096.54** at AUD/USD 0.7110 |
| Booked cost base | **A$6,978.23** (implies acquisition FX 0.6450) |
| Unrealised | **+A$1,118.31 · +16.03%** |
| USD price return | **+27.90%** |
| Realised vol since entry | **89.2% annualised**; 19 of 55 sessions moved >5%; worst day −19.1%, best +14.5% |
| Peak-to-trough | US$262.20 (06-01) → US$170.28 (06-25) = **−35.1%** |

### 2.1 The AUD result is a price win partly given back to FX

Decomposed at the booked 0.6450 entry rate:

| Component | AUD |
|---|---|
| Price effect (at constant entry FX) | **+1,946.76** |
| FX effect (AUD/USD 0.6450 → 0.7110) | **−828.45** |
| **Total unrealised** | **+1,118.31** |

**Break-even in AUD is US$206.73** at today's 0.7110. The position is +27.9% in USD and would be
*flat* in AUD at US$206.73 — a level it closed below as recently as **2026-08-07**. At AUD/USD 0.75
break-even rises to US$218.07; at 0.68 it falls to US$197.72.

> **Defect — `portfolio_daily_snapshots.unrealised_fx_pnl_aud` is mislabelled and mis-signed.**
> The 2026-08-20 row reports `unrealised_fx_pnl_aud = 1118.310084`, which is *total* unrealised
> P&L. The actual FX component is **−828.45** — opposite sign. Any consumer that trusts the column
> name reads an A$828 currency loss as an A$1,118 currency gain. (`jobs/snapshot_portfolio.py`.)

### 2.2 Versus benchmark

XJO total-return level 11,228.5695 (2026-06-01, first post-entry snapshot carrying a benchmark) →
11,785.3080 (2026-08-20) = **+4.96%**.

| Basis | Position | XJO TR | Excess |
|---|---|---|---|
| Booked (FX 0.6450) | +16.03% | +4.96% | **+11.07 pp** |
| If FX is really 0.7171 | +28.99% | +4.96% | **+24.03 pp** |

The benchmark's `trailing_div_yield_pct` is a hardcoded 4.0, so the TR leg is an approximation, not
a measured index. Fine for a directional read; do not quote the excess to two decimals.

---

## 3. The cost-base fork — the highest-value open item

`holding_lots.notes` says *"AUD/USD 0.6450 estimated — update from brokerage statement."*
`theses.tax_notes` (2026-07-04) says the same and flags that vendor FX for 2026-05-31 was **0.7171**.
`fx_rates` shows spot in the 0.714–0.716 band across late May 2026. The project guide asserts 0.6450
is "confirmed against the brokerage statement — an ESPP fill rate that differs from spot."

**These cannot all be true, and the repo has carried the contradiction for seven weeks.**

| If acquisition FX is… | AUD cost base | Unrealised | Return |
|---|---|---|---|
| 0.6450 (booked) | A$6,978.23 | +A$1,118.31 | +16.03% |
| 0.7171 (vendor) | A$6,276.75 | +A$1,819.79 | **+28.99%** |
| **Difference** | **A$701.48** | **A$701.48** | **12.96 pp** |

The 15% plan discount is already fully accounted for in the **share price** (187.54 = 0.85 × 220.63),
so it cannot also explain a 10% FX divergence. A 10% spread on a retail FX conversion is not a
plausible bank margin. The balance of evidence says the 0.6450 figure is wrong and the "confirmed"
claim in the project guide is unsupported — but the brokerage statement is the only thing that
settles it, and only James has it.

This is not cosmetic: an overstated cost base **understates the assessable gain**, and every
downstream AUD number (snapshot series, benchmark excess, the whole `portfolio_outcome_ledger`)
inherits the error.

---

## 4. Discipline state — where the scaffolding is failing

Replaying `asxos/domain/theses/discipline.py` + `trajectory.py` against the live row, as-of
2026-08-20:

| Check | Result |
|---|---|
| `trajectory` | **ON TRACK** — progress 40.1% vs 22.2% linear expectation, day 81/365 |
| `revisit_overdue` | **RED** — due 2026-08-03, **18 days overdue** |
| `timeline` | clear — deadline 2027-05-31, 283 days out |
| `data_sanity` (detached ladder) | does **not** fire — needs live >= 2x target (318); 239.86 is 0.75x |
| `data_sanity_escalation` | does **not** fire — predicated on the same detached-ladder condition |
| `no_stop_set` | does not fire — a stop exists |
| `stop` (via trajectory) | **not violated today** (239.86 > 230) — but see below |

### 4.1 The stop and the anchor are on different price bases

`stop_price = 230` sits **above** `actual_entry_price = 187.54`. That is not a data-entry error —
it is coherent against the *market* price at the time (US$220.63 on 05-29, US$262.20 on 06-01).
But the recorded anchor is the **discounted ESPP fill**, and `classify_trajectory()` compares the
live price to the stop with no knowledge that the two legs come from different bases.

Consequence, measured:

> **43 of the 56 sessions since entry (76.8%) closed at or below US$230**, i.e. the classifier would
> have returned `STOP_VIOLATED` on more than three sessions in four — while the position was, on the
> booked cost base, profitable for most of them.

The stock has crossed the US$230 line **five times in the last month alone** (08-05 above, 08-06
below, 08-13 above, 08-14 below, 08-19 above). A discipline signal that flips weekly and is right
by accident is worse than no signal: it trains the reader to ignore the one alert that matters.

The auto-triggered invalidation condition #1 (*"auto: close=192.120000 below 230 on 2026-07-03"*,
which actually used the 07-02 close — 07-03 was the US Independence Day observance) is the same
artefact, now permanently latched to `triggered` in the JSONB.

**The existing detached-ladder check cannot catch this class of fault.** It tests `live >= 2 x target`
— tuned to the CBA case (target 60 vs live ~168). Here the target is fine and the *stop* is on the
wrong basis. The check is anchored to the wrong leg of the ladder.

### 4.2 The thesis has gone dark through its own scheduled test

`thesis_revisions` holds exactly **one** row for thesis_id=2, dated **2026-07-04** (48 days ago),
and it documents the ESPP lock, not the position.

In the interim the thesis's own pre-registered event fired. From `earnings_notes` — still written in
the **future tense** ("Q2 FY26 print **expected** Tue-Wed Aug 5 2026 AMC") — the falsifiers were:
net adds <10k/qtr · avg sub revenue/customer stalling <= $11,700 CC · NRR <103% · credit consumption
decelerating sharply from +67% QoQ · revenue below the $897M guide · FY26 cut.

What actually happened (prices + `holding_news`):

- **2026-08-05** close US$250.21 — the print lands after the bell.
- **2026-08-06** close **US$202.43 on 8.62M shares** (2.8x the prior session) — **−19.1% in a day**,
  the worst session in the position's life.
- Recovery to US$239.86 by 08-20: **+18.5%** off that close, still **−4.1%** below the pre-print close.
- Coverage in `holding_news` (ids 12–14, 2026-08-13) reports the print as a **beat** — revenue
  **+20% YoY**, rising AI adoption, improving cash generation — alongside management guiding to
  **slower net adds, pressure on net upgrade rates, longer buying cycles, and greater scrutiny of AI
  spend** through the rest of 2026, with pricing changes creating near-term execution pressure.
  Zacks Rank #3 (Hold). The sector framing is "SaaSpocalypse" (id 16, 08-17), with HUBS named
  among the post-earnings disappointments.

So: **the revenue falsifier did not trigger; the net-adds / net-upgrade-rate / buying-cycle
falsifiers point the wrong way and remain unadjudicated.** That is precisely the judgement the
revision trail exists to record, and it has not been recorded. A −19% day on a pre-registered
catalyst is the single highest-information event since entry, and the thesis is silent on it.

### 4.3 The timeline is one day short of the tax outcome it names

- Acquired 2026-05-31. Per non-negotiable rule #6 / spec §5.1, CGT-discount eligibility begins at
  `acquired + relativedelta(years=1) + timedelta(days=1)` = **2027-06-01** (284 days out).
- `thesis_text` says: *"Hold to 12-month CGT discount date (Jun 1 2027)"* — correct.
- `timeline_days = 365` → deadline `opened_at + 365` = **2027-05-31** — **one day early**.

A disposal executed on the thesis's own deadline forfeits the 50% discount. On today's A$1,118.31
gain that is ~A$559 of extra assessable income (~A$218 of tax at a 37% + 2% rate); at the recorded
target it is ~A$1,877 assessable (~A$732). `timeline_days` should be **366**.

This is the cleanest possible example of the product's stated purpose — a discipline field that
quietly costs money — and it is a one-integer fix.

### 4.4 Theme attribution is dangling

`theses.themes = {us-saas-ai, us-equities}`. The `themes` table contains **one** row: `big-4-banks`.
`theme_holdings` contains **one** row: CBA.AU (and it is `governance_status='draft'`, so it does not
appear in `governed_active_theme_holdings`).

Neither theme code exists. HUBS has no `theme_holdings` row. Moat layer 3 (theme stewardship) has
**zero coverage of the only funded position** — the denormalised array is a string that resolves to
nothing.

---

## 5. Data and pipeline coverage for this position

### 5.1 What runs

| Job | Latest | Covers HUBS? |
|---|---|---|
| `sync_prices` | 2026-08-20 OK | yes — via `get_us_holding_symbols()` |
| `snapshot_portfolio` | 2026-08-20 OK | yes — with FX conversion |
| `check_us_positions` | 2026-08-19 OK | yes |
| `check_thesis_invalidations` | 2026-08-20 OK | yes — this is what latched condition #1 |
| `ingest_news` | 2026-08-20 OK | **yes, now** — see 5.3 |
| `compose_brief` | 2026-08-20 OK | yes |
| `ingest_market_context` | 2026-08-20 OK | ASX-only by construction |

### 5.2 What does not run — the research blind spot

**Zero rows for HUBS.NYSE in every one of:** `fundamentals`, `rs_financial_statements`,
`rs_estimates`, `rs_factor_scores`, `rs_security_master`, `rs_corporate_actions`, `signals`.

Root cause is the `universe.is_active` overload documented in `portfolio-conventions.md`. HUBS is
`is_active=FALSE, security_kind='us_equity'`, and the readers filter it out:

- `jobs/sync_fundamentals.py:57` — `WHERE is_active AND security_kind = 'au_equity'`
- `jobs/sync_financial_statements.py:52` — `AND is_active`
- `jobs/validate_price_data.py:84,106,125` — `is_active AND security_kind = 'au_equity'`

Two consequences worth naming:

1. **No fundamental data on the only funded holding.** Every valuation statement in section 4.2
   above comes from third-party news prose in `holding_news`, not from a stored, cited financial.
   The north star says *"every capital-relevant number is Decimal-exact and traces to a cited
   source"* — for this position, none of the fundamentals do, because none exist.
2. **US price data is unvalidated.** `validate_price_data` never inspects HUBS. There is one
   unexplained missing session in the series — **2026-06-30** (a Tuesday; 06-19 Juneteenth and
   07-03 Independence-Day-observed are legitimate closures).

Note also: `security_kind` **exists in production** as an enum-style column (`us_equity` on this
row). The project guide still describes `m14_candidate_security_kind_enum` as deferred and the
suffix conventions as the current mechanism. The column landed; the doc did not follow.

### 5.3 The news surface's ship condition is now met on the evidence

`dark-launch-exit-plan.md` surface #2 was reverted to **UN-SHIPPED** on 2026-08-13 because
condition (a) was void — `holding_news` had zero rows, blamed on a `_normalise_symbol` mapping bug.

**That is no longer the live state.** `holding_news` now holds 9 rows, every one tagged
`HUBS.NYSE`, ingested daily 2026-08-13 → 2026-08-20, with `ingest_news` reporting success on
2026-08-20. The restated condition (a) — *success **and** rows_written > 0 **and** `holding_news`
non-empty* — is satisfied on the data.

One caveat before anyone calls it shipped: the tagging is loose. Of the 9 rows, **4 are primarily
about other companies** (Workday, Salesforce, Atlassian/Cloudflare) and merely mention HubSpot in
passing. The surface is live and non-empty; its precision has not been measured.

### 5.4 Snapshot series has holes on the days that matter

`portfolio_daily_snapshots` is missing **2026-08-04, 2026-08-06 and 2026-08-19**.

**2026-08-06 is the −19% earnings-crash day.** The outcome ledger has no row for the single most
informative session in the position's history. Whatever the results-review lane (P2-03/04/05) is
built to learn from, it cannot learn from a day that was never recorded.

### 5.5 Tax coverage — the one instrument class the spec excludes

The book's only position is an ESPP lot, and `docs/foundation/spec/tax-alpha.md` §8.5 / §9 are
explicit:

> *"v1 of the system does not implement Division 83A; ESPP lots are imported with the user-supplied
> cost base and the system treats them as ordinary purchase lots."*
> *"…any other ESS position will produce wrong tax answers in v1; the user must not rely on v1
> outputs for any ESS position."*

Under Div 83A the assessable discount is income at the taxing point and the CGT cost base resets to
**market value at that point** (s 130-80), not the discounted grant price. The discount here is
US$33.09/share x 24 = **US$794.16**. The system models none of it.

**Spec-to-schema gap:** §9 states the v1 accommodation is that *"every position has an
`acquisition_type` field defaulting to `purchase`"*, with ESS rows tagged `ess_upfront` /
`ess_deferred` for v2 to dispatch on. **`acquisition_type` does not exist anywhere in the repo** —
not in `holding_lots`, not in any migration, not in any Python file. The accommodation was specified
and never built, so the sole ESS lot in the book is untagged and structurally indistinguishable
from an ordinary purchase. Its ESS nature survives only as free text in `notes` and `tax_notes`.

Div 775 (FX realisation on disposal, spec §8) **is** implemented — `asxos/domain/tax/fx_gain.py`.
Given the −A$828 FX component above, that leg will matter on disposal.

---

## 6. Market backdrop

From `market_context` (2026-08-20, classifier v1.0): regime **`risk_off_orderly`**. AVIX 10.85 (well
under both the 22 elevated and 30 extreme thresholds), VIX 16.01, US HY OAS 2.73% (far from the
4.50% elevated trip), US 10y-2y +0.46. The only rule firing is **`breadth_200_thin`** — 33.0% of the
ASX above its 200d MA against a 40% threshold. RBA cash rate 4.35%, AUD/USD 0.7110.

Read plainly: **no credit or volatility stress; the "risk-off" label is being carried almost
entirely by thin breadth.** That is a domestic-equity breadth measure and has limited bearing on a
US SaaS holding — but it is the regime the invalidation condition *"macro regime shifts to
risk_off_disorderly"* is tested against, and `risk_off_orderly` is not `risk_off_disorderly`. That
condition remains untriggered and correctly so.

Sector-wise, `holding_news` id 16 (2026-08-17) frames the backdrop as the "SaaSpocalypse" — AI
disruption fears and enterprise software budget concerns, with HUBS named among the disappointments,
partially rebutted by later Atlassian/Cloudflare prints. Ancillary: KeyBanc expects software M&A to
accelerate (id 17), with Silver Lake's reported approach for Workday as the catalyst.

---

## 7. Forecast

### 7.1 Ladder arithmetic — what each level is worth

At 24 shares and AUD/USD 0.7110, against the booked A$6,978.23 cost base. **This is arithmetic on
James's own recorded ladder, not a price prediction or a recommendation.**

| Level | US$/sh | MV AUD | Unrealised AUD | Return |
|---|---|---|---|---|
| Recorded target (200d MA) | 318.00 | 10,733.05 | +3,754.82 | **+53.8%** |
| Pre-print close (08-05) | 250.21 | 8,447.68 | +1,469.45 | +21.1% |
| **Last close (08-20)** | **239.86** | **8,096.54** | **+1,118.31** | **+16.0%** |
| Recorded stop | 230.00 | 7,763.71 | +785.48 | +11.3% |
| **AUD break-even** | **206.73** | **6,978.23** | **0** | **0.0%** |
| Post-print low close (08-06) | 202.43 | 6,833.09 | −145.14 | −2.1% |
| ESPP fill price | 187.54 | 6,330.46 | −647.77 | −9.3% |

The last row is the one to sit with: **at the price he paid, the position is down 9.3% in AUD**,
purely on currency. Everything above break-even is a US$32-per-share buffer built since entry.

**Sensitivity.** At 89.2% annualised realised vol, a one-standard-deviation 90-day move on
US$239.86 spans roughly **US$140 – US$340**. That band contains the stop, the break-even, the fill
price and the target. The honest forecast is that the recorded ladder does not discriminate at this
volatility — over a single quarter, this position can reach any level on that table.

### 7.2 Dates on the clock

| Date | Days | Event |
|---|---|---|
| 2026-08-31 | 10 | Portfolio-brief dark-launch **expiry** (`dark-launch-exit-plan.md` #1) — a decision falls due |
| 2026-09-16→18 | 26 | HubSpot UNBOUND flagship event (from `earnings_notes`) — an unmonitored catalyst |
| ~2026-11 | ~75 | Q3 FY26 print — `next_earnings_date` still reads 2026-08-05 and needs rolling |
| 2027-05-31 | 283 | Thesis timeline deadline **as encoded** (one day early — §4.3) |
| **2027-06-01** | **284** | **CGT-discount eligibility** (rule #6 / spec §5.1) |

### 7.3 What the shipped and planned build will do for this position

**Already merged, and it helps here:**

- **#130 detached-ladder escalation** — real, but blind to this thesis: it keys on
  `live >= 2 x target`, and the fault here is a stop on the wrong basis (§4.1).
- **#129 per-lot outcome vs benchmark on the V1 brief** — directly relevant; this is the surface
  that should have been showing the +11pp excess daily.
- **#132 job-failure banner made capable of firing** — relevant to the missing 08-06 snapshot.
- **#73 news renders state instead of vanishing** — and news is now genuinely flowing (§5.3).
- **0043 `price_revisions`** — applied, 0 rows; would catch a restated HUBS close if EODHD revised one.

**Approaching, and it does not help here yet:**

- **Portfolio brief (dark, expiry 2026-08-31)** — gated behind the allocator, which is dormant under
  rule #11 (`build_portfolio` last succeeded 2026-07-11 and now logs `blocked`). The exit plan's own
  guidance is to ship the **model-independent** cards or nothing. For a one-position book the
  allocator has nothing to allocate; the discipline/tax cards are the entire value.
- **P2-03/04/05 results-review lane** (merged) — a deterministic reviewer + independent challenger
  over historical results. Its input quality is capped by §5.4: it cannot review 2026-08-06.
- **Stage 1 evidence foundation / P3-01 Dagster / SB1-01 snapshot freeze** — infrastructure. None
  changes the five defects above.
- **#142 segment valuation → selection → exposure architecture** — the right long-run frame, and the
  reason §5.2's blind spot matters: a valuation layer that cannot see the funded holding's
  fundamentals starts one position short.

**The honest summary:** the roadmap is building the *engine* while the *only live position* is
carrying five unfixed data and discipline defects. Every item in §8 is hours of work, not a stage.

---

## 8. Open items, ranked

| # | Item | Why it ranks here | Owner |
|---|---|---|---|
| 1 | **Resolve the acquisition FX from the brokerage statement** | A$701 of cost base; drives CGT, every AUD return, and the outcome ledger. Blocked on a document only James holds. Correct the project guide either way. | James |
| 2 | **Revise the thesis for the 2026-08-05 print** | 18 days overdue, 48 days silent, through a −19% pre-registered catalyst. Adjudicate the net-adds / NRR / buying-cycle falsifiers; roll `next_earnings_date`; move `earnings_notes` out of the future tense. | James (revision), system (cadence) |
| 3 | **Re-base the ladder, or teach the checks about basis** | The stop fires on 77% of sessions. Either restate stop/target against the recorded 187.54 anchor, or give `discipline.py` an explicit anchor-basis concept so an ESPP fill and a market-price stop are not silently compared. | Build |
| 4 | **`timeline_days` 365 → 366** | One integer; ~A$218–A$732 of tax; the deadline currently contradicts the thesis text. | James |
| 5 | **Fix `unrealised_fx_pnl_aud`** | Reports total P&L under an FX label, with the opposite sign to the true FX effect. | Build |
| 6 | **Backfill the missing snapshots (08-04, 08-06, 08-19) and the 2026-06-30 price** | The results-review lane cannot learn from days that were never recorded — least of all the crash day. | Build |
| 7 | **Bring US holdings into the research + validation pipelines** | Zero fundamentals and zero price validation on the only funded position. The `security_kind` column already exists to select on — the readers just don't use it. | Build |
| 8 | **Create the `us-saas-ai` / `us-equities` themes, or drop the array** | Moat layer 3 has no coverage of the funded position; the reference is dangling. | James + build |
| 9 | **Add `acquisition_type` per spec §9** | The spec's stated v1 ESS accommodation was never built; the sole ESS lot is untagged. | Build |
| 10 | **Confirm the ESPP lock-window end date** | Open since 2026-07-04. Until it is known, no discipline finding on this position is actionable — which is itself worth stating on the brief. | James |
| 11 | **Fresh SHIP verdict for the news surface** | Condition (a) is now met on the data (§5.3); the surface is sitting in the un-decided state the exit plan forbids. Measure tagging precision first. | arbi → James |

---

## 9. Provenance

Every figure above is a live read taken 2026-08-21 against the production Supabase project, or a
hand-replay of committed code against that data. Sources: `theses` (thesis_id=2), `thesis_revisions`
(1 row), `holding_lots` (id=1), `prices` (56 sessions from 2026-05-31), `fx_rates`,
`portfolio_daily_snapshots`, `holding_news` (9 rows), `market_context` (ctx_id=37), `job_runs`,
`universe`, `themes` / `theme_holdings`, and zero-row confirmations across `fundamentals` and every
`rs_*` table. Code: `asxos/domain/theses/discipline.py`, `trajectory.py`, `jobs/sync_fundamentals.py`,
`jobs/sync_financial_statements.py`, `jobs/validate_price_data.py`, `docs/foundation/spec/tax-alpha.md`
§§5.1, 8, 8.5, 9. No Model A output was read (rule #11); `signals` is empty for this symbol regardless.
