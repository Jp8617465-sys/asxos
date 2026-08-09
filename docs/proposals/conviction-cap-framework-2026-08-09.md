# Conviction / concentration framework — advisory proposal (D3, PR #78 governor rulings)

**Status:** ADVISORY — research input for James to set final numbers against. Nothing here is self-executing; every number below is a *proposed default* with a defensible range, per red-team work order R3 ("governed conviction/cap framework + concentration-threshold unification", `docs/proposals/finance-red-team-2026-08-08.md` §4, decisions D3/D4).

**Firewall:** this is a framework about RULES and their representation. It contains no direction regarding any live position. The locked employer position is discussed solely as a representation problem. All HUBS ESS/CGT facts remain UNKNOWN / NOT RELIABLE per the red-team packet.

**Hard constraint honoured:** none of the current agents' unsourced numbers (40% sector, 20% cash, 5% stop-proximity, severity 10/20 and 3/5 bands) is cited as authority anywhere below. Where they coincidentally survive, they survive on an independent basis.

**Confidence key:** [H] = regulatory text, peer-reviewed research, or this repo's governed prior · [M] = consistent multi-firm practitioner consensus · [P] = governor preference — no external authority; James sets freely.

---

## 1. Per-name cap and sector cap (and book-size scaling; and the locked position)

**External anchors.** The retail-fund regulatory floor for "diversified" is strict: UCITS 5/10/40 (≤5% per issuer, extendable to 10%, with all >5% positions summing ≤40% of NAV) [H — FCA COLL 5.2]; the US 1940-Act diversified-fund test is 5% per issuer over 75% of assets [H]. Advisor practice for individuals is looser: a single stock >5% is "worth addressing," >10% "requires more immediate planning" [M — T. Rowe Price, exact quote verified]; the widely repeated rule of thumb is **10% of investable assets, or 20% if you are restricted from selling** [M — recurs across Schwab/Kiplinger/others; I could not fetch the Schwab origin page directly, so rated M not H]. ASIC's Moneysmart recommends ~**10–15 holdings across different sectors** for a direct-share portfolio [H — Australian regulator's retail guidance]. Against that pull toward diversification, the "Best Ideas" literature (Antón, Cohen & Polk) finds managers' highest-conviction positions outperform their other holdings by ~1–2.5%/quarter — empirical support for a *concentrated, conviction-ranked* book rather than a UCITS-shaped one [H — peer-reviewed]. Diversification research brackets the tradeoff: ~90% of diversification benefit by 12–18 names (Evans & Archer 1968), 30–40 names once costs and rising idiosyncratic vol are counted (Statman 1987; Campbell, Lettau, Malkiel & Xu 2001) [H].

**Repo prior.** The schema's own governed defaults are per-name **10%**, sector **30%** (`migrations/0005_portfolio.sql:29-30`), sector 30% restated in `docs/product/portfolio-policy.md`. The per-name CHECK allows up to 50%. The risk-blindness caveat (`portfolio-conventions.md` I.1 — caps do not protect against co-movement) must attach to any cap table verbatim.

**Should caps scale with book size? Yes.** At the current ~A$7k book, a 10% cap = A$700 positions against an ASX A$500 minimum marketable parcel and ~1–3% brokerage on small trades [M — Stake/Selfwealth/Canstar] — Moneysmart's 10–15 names is mechanically impractical below roughly A$15–25k. Diversification research also says the *first* few names buy most of the risk reduction, so a small book gets most of the benefit from 4–6 names [H — Evans & Archer]. Proposed tier schedule (tier boundaries are [P]):

| Tier | Book size | Per-name cap | Sector rule |
|---|---|---|---|
| 0 | < A$25k | **25%** (⇒ ≥4 names fully deployed) | count-based: **max 2 names per GICS sector** (a %-cap under 50% is unsatisfiable at N=4; derivation, [P]) |
| 1 | A$25k–A$100k | **15%** | 30% (repo prior) |
| 2 | > A$100k | **10%** (repo prior = advisor standard) | 30% |

Defensible ranges: per-name 5% (fund-regulatory strict) → 20% (restricted-stock tolerance / best-ideas concentration); sector 25–40%.

**The locked position — representation: DUAL REPORTING (recommended).** Of the three options: (i) *excluded-from-denominator* is rejected — it hides the book's largest risk, exactly reproducing register #8 (100% single-name flagged by nothing); (ii) *standing documented exception* alone suppresses the alert surface; (iii) **dual reporting** matches both external practice (the rule of thumb applies a *different threshold* — 20% — to restricted positions rather than removing them [M]) and the red-team's own adopted ordering ("enforceability second — instrument constraints demote triggers to ALERT/REVIEW **on the face of the card**", synthesis §3). Concretely: every concentration surface computes and displays **both** the full-book utilisation (truth; the locked breach renders as a standing `LOCKED-RED`, never suppressed, with an unlock-review obligation attached) **and** the free-float utilisation (the actionable ladder over sellable holdings). The lock state lives in R2's instrument-constraints field, not free-text `tax_notes` (register #4).

**DECISION FOR JAMES:** adopt the tier schedule (Tier-0 per-name 25% / max-2-per-sector; 15%/30% at Tier 1; 10%/30% at Tier 2) with dual reporting for locked positions. Alternatives: flat 10%/30% at all sizes (repo prior, impractical at A$7k); flat 20% per-name (restricted-tolerance ceiling); excluded-from-denominator (rejected above but listed for completeness). Tier boundaries A$25k/A$100k are yours to move.

## 2. Employer-stock treatment (the ESPP reality)

**What practice and research say.** FINRA (regulator) names the dual risk explicitly: if the company falters, investments and employment can fail together [H]. Meulbroek (2002, HBS) quantifies the cost: an undiversified employee holding sacrifices on average ~42% of the stock's market value versus a diversified portfolio, with the loss increasing in proportion-of-wealth, holding period, and stock volatility [H — working-paper research]. Advisor consensus caps employer stock at **10–15% of the portfolio, tolerance ~20% while restricted from selling** [M]. ESPP-specific practitioner consensus: the discount is the product; shares are typically sold promptly once sellable and proceeds redeployed, because holding stacks concentration on top of income exposure [M — Plancorp, myStockOptions, EquityFTW, Bogleheads]. No source gives a *quantitative* income+equity correlation limit; the human-capital literature is directional only (employer dollars are worth less per dollar of risk than ordinary equity dollars) — the residual number is [P].

**Proposed rule set.**
1. An `is_employer` flag on the instrument/holding (register #10: currently unrepresentable — no field anywhere swept).
2. Employer stock target cap **10%** of investable assets (lower bound of advisor practice, justified by the income correlation) — and it binds at the **lower** of (employer cap, the position's conviction band, the tier per-name cap). Employer positions never get conviction-band headroom above the employer cap: salary already consumes part of the single-company risk budget [H for direction, P for the exact 10%].
3. While locked: tolerance band up to **20%** renders YELLOW-LOCKED; above 20% renders **LOCKED-RED** as a standing, dated, documented state (Section 1's dual reporting) — visible every day, actionable never, with a mandatory review event scheduled at unlock. Any locked employer position at 100% of book is, by construction, LOCKED-RED for its entire locked life; that is the *correct* representation, not an alert bug to suppress.
4. The lock end date is a first-class nullable field with an `unknown` state that itself renders YELLOW (an unknown constraint on the largest position is information).

**DECISION FOR JAMES:** adopt employer cap 10% (range 5–15%), locked tolerance 20% (range 15–25%), LOCKED-RED standing-state representation with unlock-review obligation. Alternative: treat employer stock under the ordinary per-name cap with only a flag — weaker than all sourced practice.

## 3. Conviction scale semantics (1–5)

**Sourced principles.** Conviction-concentration has empirical payoff (Best Ideas [H]) — a conviction scale that does nothing is a waste of the one edge the literature grants a concentrated investor. But sizing-by-edge is exactly where overbetting lives: Kelly-style sizing magnifies estimation error, and near-universal practice is fractional (¼–½) Kelly precisely because edge estimates are noisy [M — consistent across quant-practice sources]. Two design consequences: (a) conviction→size should be an **advisory band upward, hard cap downward** — the system never forces size up to conviction, but a position *larger* than its conviction band is a breach; (b) the top rung must still sit inside the per-name cap (no "conviction 5 overrides the cap" — that is full-Kelly thinking).

**Proposed operational semantics** (structure sourced by analogy to underwriting practice and this repo's own attestation direction, R9/D4; the specific evidence gates are [P]):

| Level | Meaning | Evidence required (machine-checkable where possible) | Size band (fraction of applicable per-name cap) |
|---|---|---|---|
| 1 | Watchlist / speculative | idea logged; thesis text optional | **0%** — not capital-eligible |
| 2 | Researched | thesis text + written falsifiers; no valuation basis yet | ≤ 25% of cap |
| 3 | Underwritten | full discipline wrapper: coherent entry band (non-degenerate), stop **with semantics enum**, target **with recorded derivation**, timeline, ≥1 machine-parseable invalidation condition; attestation = `underwritten` (R9) | ≤ 50% of cap |
| 4 | Underwritten + differentiated | all of L3 + an explicit variant view vs consensus + falsifiers survived ≥1 earnings/event cycle | ≤ 75% of cap |
| 5 | Exceptional (rare by design) | all of L4 + explicit governor sign-off recorded as a governance event | ≤ 100% of cap |

**Required at activation: yes** — `conviction_level NOT NULL` on any thesis entering `active` (register #28; R3's "conviction required-at-activation" is already the red-team's James-gated recommendation). The existing 1–5 CHECK (`migrations/0026_theses_conviction_tax.sql`) stays; the NULL-allowed default flips for the `active` transition only. Levels 3+ should be unreachable without R9 attestation — conviction is an *evidence grade*, not a mood, and the L3 gate is exactly the malformation lint R1 introduces (13/13 theses currently fail it, register #2).

**Rule or advisory band?** Advisory upward, hard downward (as above): exceeding the band ceiling is a RED + governance event; sitting below it is always fine. A hard bidirectional rule is rejected for v1 — the allocator is dormant (rule #11) and mechanical sizing would be false precision on noisy inputs [M — the fractional-Kelly argument].

**DECISION FOR JAMES:** adopt the 5-level semantics + band fractions (25/50/75/100% of cap) + required-at-activation + hard-cap-downward. Alternatives: 3-level scale (simpler, loses the L4/L5 distinction the Best Ideas result rewards); pure-advisory bands with no breach state (rejected — reproduces register #28's "size-vs-conviction discipline undefined").

## 4. Derived display bands — one ladder, four vocabularies retired

**Sourced principle.** Bank/insurer risk-appetite practice uses a two-threshold ladder on every limit: amber (early warning) at ~**70–80% of the limit**, red at the limit [M — Boston Fed working paper on risk limits; multiple risk-framework practitioner sources]. That is the entire design needed here, applied uniformly:

For every capped quantity, compute utilisation `u = exposure ÷ applicable cap` (Decimal), then: **GREEN** `u < 0.80` · **YELLOW** `0.80 ≤ u < 1.00` · **RED** `u ≥ 1.00` · **LOCKED-RED** = RED where the instrument-constraints field blocks action (standing state per Section 1, never suppressed, never escalated into an action prompt — R7 ordering).

This single ladder replaces: `severity.py::position_concentration`'s hardcoded 10/20 (which also uses the wrong denominator — % of holdings MV, not total capital; and both denominators must exist per Section 1's dual reporting); the profile caps as a separately-worded vocabulary; the coherence agent's 40% sector line (`portfolio-coherence-reviewer.md:83` — retired, unsourced); and the severity bands' independent numbers. Every consumer reads the caps from the active `profiles` row — **no literal thresholds in code or prompts** (that is how four vocabularies happened; register #9). Cash floor and leverage use the same ladder inverted/directly: cash `< 1.25×floor` YELLOW, `< floor` RED; net exposure `> 0.8×` headroom toward the leverage cap YELLOW, `> cap` RED. The agent's "cash > 20% = flag" rule is retired without replacement; if a deployment-lag nudge is wanted it is [P].

**DECISION FOR JAMES:** adopt the 80%/100% two-rung ladder with LOCKED-RED as the only additions, all thresholds read from the profile row. Alternative: three rungs (70/90/100) if you want earlier warning on a concentrated book — also inside sourced practice (70–80% amber range).

## 5. Cash floor and leverage

**Cash floor.** Finding: the live `cash_floor_pct = 0` contradicts the repo's own governed schema default of **5%** (`migrations/0005_portfolio.sql:27` — `DEFAULT 0.05`) [H — repo prior]. External practice locates the real cash buffer at the *household* level: ASIC Moneysmart's emergency-fund guidance is ≥3 months of expenses held outside the investment portfolio [H]. At A$7k scale an in-portfolio floor is operational (brokerage, contingency), not crash protection — the risk-blindness caveat stays true regardless. Recommendation: restore the **5%** floor (repo's own default) *and* add a one-line attestation field that a household emergency fund exists outside the system (Moneysmart-conform); with that attestation recorded, the floor is a deliberate governed value rather than register #29's "hollow protection." An explicit, attested **0%** ("all buffer is held externally") is also defensible — the defect was that 0 was *unset*, not that 0 is indefensible.

**Leverage.** `leverage_cap = 1.0` (no borrowing) is strongly defensible as a deliberate value, not a hole: Moneysmart classes borrowing-to-invest as high-risk with margin-call mechanics that force selling at the worst time [H — Australian regulator retail guidance]; layering leverage on a book that is currently one locked employer name would compound three correlated exposures (equity, income, credit). Recommendation: set **1.0 explicitly** in the governed policy (closing the "[governor to set]" hole in `docs/product/portfolio-policy.md`); any future value >1.0 is a P5 policy change requiring margin-call modelling first. The schema CHECK (1..3) can stand.

**DECISION FOR JAMES:** cash floor 5% + external-emergency-fund attestation (alternative: attested 0%); leverage cap 1.0 explicit (alternative: none defensible for v1 on sourced grounds).

## 6. Stop-proximity and drawdown alert bands

**Stop proximity — derive from volatility, retire the flat 5%.** A fixed 5%-from-stop band means opposite things on a 15%-vol bank and a 45%-vol growth stock. Practitioner stop practice is ATR-denominated: placement at ~2.0–3.5× ATR with the higher multipliers for position-trading horizons [M — StockCharts/TrendSpider/QuantifiedStrategies]; the natural proximity semantics follows: **YELLOW when distance-to-stop ≤ 1× ATR(14)** ("one average day's range from trigger"), **RED at ≤ 0.5× ATR** [derivation from sourced ATR practice; the 1×/0.5× choice itself is P]. Repo has OHLCV, so ATR is computable in Decimal. Precondition (register #11 / R10): price and stop must be same-currency before any distance is computed — the proximity check must refuse, loudly, on a currency mismatch. Secondary sourced note: Kaminski & Lo (2014) show stop rules add value under momentum and subtract it under random-walk returns [H] — which supports R2's `hard_exit|alert_review` semantics enum over any pretence that a fixed stop is research-optimal, and supports ATR-anchored *placement guidance* (2.5–3.5× for this system's weeks-to-months horizon) at authoring time as an R1 lint hint, not a mandate.

**Drawdown bands — the current 3%/5% matches no convention I could find and is miscalibrated for this book.** A concentrated all-equity book inherits single-stock volatility (the live book printed a −19.1% single day, red-team packet E05); 3/5% bands would be near-permanently red — alert fatigue, the opposite of the discipline moat. The sourced fixed-band convention for equities is **10% (correction) / 20% (bear market)** [M — Morningstar/Schwab/CFI standard usage]. Recommended v1: portfolio drawdown **YELLOW at 10%, RED at 20%** from high-water mark; v2 candidate: vol-scaled bands (YELLOW at 1× trailing monthly σ, RED at 2×) once there is history to estimate σ honestly. **Prerequisite either way:** register #15 — with no cash-flow ledger, contributions read as recoveries and withdrawals as drawdowns; any drawdown alert computed off `capital_aud` is unreliable until the ledger exists. The band decision can be taken now; the alert should ship gated on the ledger.

**DECISION FOR JAMES:** stop proximity = ATR-scaled (1×/0.5× ATR(14)), same-currency-enforced (alternative: keep a fixed % only as an explicit fallback when ATR is uncomputable, value yours); drawdown = 10%/20% fixed for v1, vol-scaled as v2 candidate, alert gated on the cash-flow ledger (alternative: keep 3/5% — no sourced basis found; not recommended).

---

## What I could not source (explicit list)

1. **Tier boundaries** (A$25k / A$100k) — [P], no external authority for the cut points, only for the direction (caps must loosen as books shrink).
2. **A quantitative income+equity correlation limit** — the literature (Meulbroek, FINRA) is directional; the 10% employer target is advisor practice, not a derived correlation bound.
3. **Published operational semantics for a 1–5 conviction scale** — no standard exists; the evidence-gate structure is analogical (underwriting/IC practice + this repo's R9), the band fractions are [P].
4. **The 80%-of-cap yellow for *personal* portfolios** — transferred from institutional risk-appetite practice; no retail source.
5. **Any authority for the current 3%/5% drawdown or 5% stop-proximity numbers** — searched; nothing found; consistent with the red-team's "unsourced prompt invention" classification.
6. **Australian-specific employer-stock concentration guidance** — Moneysmart covers diversification generally; no ASIC number for employer-stock percentage exists that I could find. All employer-percentage anchors are US practice.
7. **A "too much cash" threshold** — retired without sourced replacement; [P] if wanted.
8. The Schwab origin page for the "10%/20% if restricted" rule (fetch blocked) — the rule is corroborated across multiple firms but rated [M].

## Repo files load-bearing for this proposal

`/Users/jpcino/Desktop/asxos/docs/product/north-star.md` · `/Users/jpcino/Desktop/asxos/docs/product/portfolio-policy.md` · `/Users/jpcino/Desktop/asxos/.claude/rules/portfolio-conventions.md` · `/Users/jpcino/Desktop/asxos/.claude/worktrees/finance-red-team/docs/proposals/finance-red-team-2026-08-08.md` (register #8–#10, #28–#29; R3/R9; R7 ordering) · `/Users/jpcino/Desktop/asxos/migrations/0005_portfolio.sql:27-30` (governed defaults incl. the 5% cash floor) · `/Users/jpcino/Desktop/asxos/migrations/0026_theses_conviction_tax.sql` · `/Users/jpcino/Desktop/asxos/asxos/domain/brief/severity.py:145-194` (bands to retire) · `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md:83,88,101` (prompt numbers to retire).

Sources:
- [FCA Handbook COLL 5.2 — UCITS investment limits](https://handbook.fca.org.uk/handbook/coll5/coll5s1)
- [Dillon Eustace — Guide to UCITS](https://www.dilloneustace.com/insights/a-guide-to-undertaking-for-collective-investment-in-transferable-securities-ucits-/)
- [Securities Institute — 75-5-10 diversification (1940 Act)](https://securitiesce.com/definitions/6113-75-5-10-diversification/)
- [SEC staff report — threshold limits for diversified funds](https://www.sec.gov/files/staff-report-threshold-limits-diversified-funds.pdf)
- [T. Rowe Price — actions if your portfolio is too concentrated in one equity](https://www.troweprice.com/personal-investing/resources/insights/actions-can-take-if-your-portfolio-is-too-concentrated-in-one-equity.html)
- [Charles Schwab — how to manage stock concentration risk](https://www.schwab.com/learn/story/3-strategies-highly-appreciated-stocks)
- [Kiplinger — conflicted about selling concentrated company stock](https://www.kiplinger.com/investing/stocks/concentrated-company-stock-strategies)
- [FINRA — Concentrate on concentration risk](https://www.finra.org/investors/insights/concentration-risk)
- [FINRA — Love your company stock? What to know](https://www.finra.org/investors/insights/love-your-company-stock-what-to-know)
- [Meulbroek (2002), Company Stock in Pension Plans: How Costly Is It? (HBS)](https://www.hbs.edu/ris/Publication%20Files/02-058_7e51c79e-3ad6-4b75-96bf-d7d7336e1ce9.pdf)
- [Antón, Cohen & Polk — Best Ideas (LSE)](https://personal.lse.ac.uk/polk/research/bestideas.pdf)
- [MDPI review — How many stocks are sufficient for diversification?](https://www.mdpi.com/1911-8074/14/11/551)
- [Benjelloun — Evans and Archer forty years later](https://businessperspectives.org/index.php/journals?controller=pdfview&task=download&item_id=3162)
- [ASIC Moneysmart — Diversification (10–15 holdings)](https://moneysmart.gov.au/how-to-invest/diversification)
- [ASIC Moneysmart — Save for an emergency fund](https://moneysmart.gov.au/saving/save-for-an-emergency-fund)
- [ASIC Moneysmart — Borrowing to invest / margin loans](https://moneysmart.gov.au/how-to-invest/borrowing-to-invest)
- [Kaminski & Lo — When Do Stop-Loss Rules Stop Losses? (SSRN/JFM 2014)](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID968338_code665721.pdf?abstractid=968338&mirid=1)
- [StockCharts ChartSchool — ATR trailing stops](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/atr-trailing-stops)
- [TrendSpider — ATR trailing stops guide](https://trendspider.com/learning-center/atr-trailing-stops-a-guide-to-better-risk-management/)
- [Boston Fed — Managing risk in cards portfolios: risk appetite and limits](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/2024/sra2401.pdf)
- [Morningstar — difference between a bear market and a correction](https://www.morningstar.com/markets/whats-difference-between-bear-market-correction)
- [Charles Schwab — what is a market correction](https://www.schwab.com/learn/story/market-correction-what-does-it-mean)
- [Stake — minimum marketable parcel](https://hellostake.com/au/blog/stake-updates/minimum-parcels)
- [Canstar — investing with $500 (brokerage drag)](https://www.canstar.com.au/online-trading/invest-sharemarket-500/)
- [Plancorp — ESPP selling strategies](https://www.plancorp.com/blog/espp-selling-strategies)
- [myStockOptions — ESPP reasons to sell or hold](https://www.mystockoptions.com/articles/employee-stock-purchase-plans-reasons-to-sell-or-hold-shares)
- [Coriva — Kelly criterion and position sizing in practice](https://coriva.eu.org/en/kelly-criterion-position-sizing/)
- [Astute Investor's Calculus — full vs fractional Kelly](https://astuteinvestorscalculus.com/full-kelly-vs-fractional-kelly/)
