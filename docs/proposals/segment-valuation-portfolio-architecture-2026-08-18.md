# Segment valuation → selection → exposure: the model-independent portfolio architecture

**Status:** ratified 2026-08-19 by James (session ruling) as this repo's forward direction.
The 4 open questions in §8 are closed. This ratification is recorded as Amendment F in a
separate, not-yet-merged branch/PR (the reconciliation work landed in parallel to this one)
— `docs/product/roadmap-state.md` on *this* branch predates that PR and does not yet show
it; do not treat its absence here as the ratification being unrecorded, only unmerged. L0
substrate repair (S1-S4) is now in progress on this branch — see the commit history for
what has actually landed vs. what remains a documented next step (S1's full multi-currency
FX conversion; S4's price backfill execution, which stays James's per the production-write
boundary).
**Author:** agent, at James's direction. Evidence verified live against `asx-portfolio-os`
(`gxjqezqndltaelmyctnl`) on 2026-08-18 via read-only SQL.
**Supersedes as design intent:** `jobs/build_portfolio.py` + `asxos/domain/portfolio/build.py`
(the Model A allocator), ruled DELETED 2026-08-18.

---

## 1. The ask

James's framing, verbatim in substance: the pipelines ingest a lot of data; manipulate it to
form **valuations of market segments**, and from there **which investment selection and
exposure ratios** build a portfolio. Thesis analysis, theme analysis and theme trend stages
build out the briefs.

That is a coherent and buildable product. It is also *not* what `build_portfolio` was.
`build_portfolio` was a signal-conditioned allocator: Model A emitted per-name probabilities,
the allocator ranked them, inverse-vol sized them and emitted target weights. Deleting it does
not delete the portfolio-construction ambition — it removes a **prediction** layer that had no
edge (rule #11) and leaves the **measurement** layer, which is where the moat always was.

This document specifies the measurement architecture, in dependency order, and is explicit
about five data defects that must be fixed first because every number downstream is wrong
without them.

## 2. The constraint that shapes the whole design

The personal-advice firewall (s766B) forbids system-generated ratings, ordinal rankings,
price targets, recommended position sizes, and the word "should". `asxos/domain/review/status.py::directive_terms`
enforces a literal-term ban mechanically; the broader policy is product-level.

Read naively, that appears to forbid the ask. It does not — it dictates **where the objective
function lives**. The reverse-DCF precedent is the template: it is permitted *because the
assumptions are the user's own input*, and a system-default assumption would be advice smuggled
in (`asxos/domain/theses/schemas.py::ReportFigure` enforces `provenance` on every capital number).

Generalised, that gives the design rule for every layer below:

> **The system supplies arithmetic, population hygiene, and consistency checks.
> James supplies the objective — caps, convictions, assumptions, targets.
> The system then reports the *gap* between the framework he declared and the book he holds.**

This is not a compliance workaround; it is better quant practice. Priors stay explicit and
auditable instead of buried in a fitted model — which is precisely the failure Model A
represented. Concretely: the system never emits a target weight. It emits the **feasible set**
implied by James's own declared caps (`decision_engine/types.py::SizeRange` + `ConstraintResult`
already model this), plus the measured consequences of each point in it.

## 3. What the pipelines actually hold (verified)

| Asset | Verified state | Usable for segment valuation? |
|---|---|---|
| `rs_financial_statements` | 694,417 rows; `period_end` 1986-09-30 → 2026-06-30 | Yes — 40 years of BS/IS/CF |
| `rs_fundamentals_pit` | 53,689 rows / 3,360 symbols; median **14 annual snapshots per symbol**; `knowledge_date` 1987-09-13 → 2026-09-13, bitemporal | Yes — the primary substrate |
| ↳ coverage of the live universe | 1,833 of 1,872 active `au_equity` (**98%**) | Yes |
| `rs_corporate_actions` | 38,039 dividends (with `franking_pct`) + 4,592 splits | Yes — franking + total-return repair |
| `prices` | 754,230 rows, but only **2025-01-02 → 2026-08-17** (~1.6 years) | Partially — see defect D4 |
| `rs_security_master` | 4,418 rows; `gics_sector` present on 3,666 (**83%**) | Partially — see defect D3 |
| `universe` | active: `au_equity`=1872, `etf`=482, `hybrid`=18, `lic`=12; 13 distinct sectors, 0 nulls | Partially — see defect D2 |
| `rs_factor_scores` | 3,362 rows, one degenerate cross-section; producer retired from cron | No — rebuild (§6, L2) |
| `rs_index_membership` | **0 rows** | No — no index-membership history, so no true benchmark segment |
| `rs_estimates` | **0 rows** | No — everything is trailing; no forward multiples |

The headline asymmetry: **14 years of fundamentals, 1.6 years of prices.** A valuation multiple
needs both. This single fact governs the sequencing in §7.

## 4. Five defects that must be fixed before any segment number is trustworthy

These were found by computing the aggregate and checking the columns, not by reading code alone.
All five are silent —
they produce plausible-looking numbers rather than errors.

### D1 — The derived PIT table has no currency dimension

`rs_fundamentals_pit` carries `net_income_ttm`, `total_equity`, `book_value_ps` and the rest with
**no `currency` column**, while `prices` are AUD. Every multiple is therefore a cross-currency
ratio. Scale of exposure: of symbols with PIT rows, **612 report in a non-AUD currency and 102
have no recorded currency at all**. Statement rows break down as AUD 562,579 / NULL 52,028 /
USD 38,611 / NZD 13,362 / EUR 5,961 / CAD 3,738 / CNY 3,471 / INR 2,744 / GBP 2,411 / HKD 1,564 /
PGK 1,436 / SGD 1,415 / JPY 808 / NOK 531.

Worked example: `ATM.AU` carries `net_income_ttm` = 7,208.8bn and `total_equity` = 35,298.2bn
against a market capitalisation of A$22.8bn (24,030.8m shares at A$0.95). The internal ratios are
sane (ROE ≈ 20%), so this is a unit/currency artefact, not corrupt data — and it alone drove the
uncorrected Materials segment to a **560.75% earnings yield**.

**Filtering is not a fix.** Restricting to AUD reporters removes BHP, RIO and NEM — which by the
same table's own market caps are A$316bn + A$276bn + A$186bn — and Materials collapses to
A$304bn, provably missing ~A$778bn of itself. Only FX conversion at `knowledge_date` is correct.
`fx_rates` exists (populated by `sync_prices` phase 3) but covers AUDUSD only.

### D2 — `security_kind` under-classifies hybrids, so bank earnings are counted many times

Hybrid and capital-note lines inherit their parent's entire income statement. `CBAPM.AU`,
`CBAPK.AU`, `CBAPJ.AU` and `CBAPI.AU` each carry CBA group net income of ~A$10.1bn and equity of
A$78.8bn; each is then assigned a phantom "market capitalisation" of `hybrid_price × parent share
count` — A$167bn to A$177bn apiece. `WBCPJ.AU` and `WBCPM.AU` show A$351bn and A$369bn; `NABPH.AU`
A$318bn.

`universe` classifies only **18** securities as `hybrid`, but 19 hybrid tickers already have PIT
rows and the CBA/WBC/NAB notes above are still labelled `au_equity`. Consequence: the Financials
segment computes to **A$3,829bn even after the `au_equity` filter** — impossible against a
whole-of-market capitalisation near A$3tn.

### D3 — Two sector vocabularies coexist, plus real misclassifications

`universe.sector` uses Morningstar names; `rs_security_master.gics_sector` uses GICS names. A
`coalesce()` across them splits single segments in two: the raw aggregate returned *both*
"Financials" and "Financial Services", *both* "Materials" and "Basic Materials", *both*
"Health Care" and "Healthcare", *both* "Information Technology" and "Technology", *both*
"Consumer Discretionary" and "Consumer Cyclical", *both* "Consumer Staples" and "Consumer
Defensive" — plus one empty-string segment. BHP is `sector='Basic Materials'`,
`gics_sector='Materials'`.

The gap is not only missing labels (17% of the master has no `gics_sector`) but wrong ones:
`CBAPI.AU` and `WBCPJ.AU` — both bank hybrids — carry `gics_sector = 'Energy'`.

> **Amended 2026-08-20 after dry-running the shipped resolver against production**
> (`segval-live-validation-2026-08-20.md`, F2/F3). Two corrections to the framing above:
>
> 1. **The two columns are not independent vocabularies to reconcile.** Both propagate from the
>    same EODHD `General.Sector` field, so they are blank *together*: of the 757 symbols whose
>    `gics_sector` is unresolvable, 242 have no `universe` row and the remaining 515 have
>    `universe.sector = ''`. The cross-column fallback resolves **0 of 4,418** symbols. Keep it
>    (it is correct, and a genuinely independent source could appear), but it is not the
>    mechanism.
> 2. **The mechanism is alias-normalisation *within* `gics_sector`**, which carries the
>    Morningstar leakage listed above. Measured effect: 3,428 already-canonical pass-through,
>    **233 symbols actually repaired** (5.3%), 757 unresolved (17.1%). The 233 is what kills the
>    duplicate-segment defect; the 757 are unreachable by any resolver change and need an
>    upstream ingestion fix or a named `unclassified` bucket.

### D4 — Price history is 1.6 years, so "cheap versus its own history" is not computable

`prices` starts 2025-01-02. Valuation percentile-versus-own-history — the core relative-value
measurement — needs a decade of the *ratio*, therefore a decade of prices. The fundamentals side
is ready (median 14 annual snapshots); the price side is not.

Separately, `adj_close` equals `close` on **78.06%** of rows. Some adjustment exists, so this is
not the total freeze the handoff describes, but the mechanism concern stands: history is never
re-fetched, so newly-declared dividends and splits do not propagate backward. The repair inputs
are already in the database — 38,039 dividends and 4,592 splits in `rs_corporate_actions`. This
also matters because `detect_theme_stages` (a KEEP) computes breadth and momentum from `prices`,
so its stage suggestions currently rest on a partially-adjusted series.

### D5 — Screening can filter on five fields that are 100% empty

`asxos/domain/screening/evaluator.py` whitelists nine numeric fields on the production
`fundamentals` table. Verified against the live table (138,087 rows):

| Field | Rows populated |
|---|---|
| `pb_ratio` | 138,087 (100%) |
| `pe_ratio` | 46,113 (33%) |
| `dividend_yield` | 37,002 (27%) |
| `roe` | **0** |
| `revenue` | **0** |
| `net_income` | **0** |
| `franking_pct` | **0** |
| `debt_to_equity` | **0** |

`asxos/ingestion/fundamentals.py` never writes those five columns — they exist in the schema
from migration `0001` and have no writer. So a screening rule expressing any quality or income
criterion returns an empty match set and reports it as a legitimate zero, with no error. This is
the most likely reason `screening_rules` and `screening_runs` both sit at 0 rows: the tool is
unusable for the rules a person would naturally write first.

The research store already holds all five (`roe`, `revenue_ttm`, `net_income_ttm`,
`franking_avg_pct`, and `net_debt`/`total_equity`), PIT-correct and with 14 years of history —
which is why L2 below repoints screening rather than backfilling `fundamentals`.

## 5. What is *already* right, and worth saying

Two things came out of the verification intact and genuinely differentiating.

**Franking gross-up works today.** Using `dividend_ttm` and `franking_avg_pct` from
`rs_fundamentals_pit`, the correct comparator for an Australian domestic investor is computable
right now: Financials 3.74% → **5.03%** grossed-up, Communication Services 6.13% → **7.29%**,
Utilities 5.43% → **6.33%**, Consumer Staples 3.49% → **4.96%**. No generic screening tool
produces this. It is a measurement, not a view, so it is firewall-clean.

**The aggregation arithmetic is sound.** Ratio-of-sums with an explicit `pct_cap_profitable`
diagnostic behaved correctly and surfaced the contaminated populations rather than hiding them —
Health Care at 51.5% of capitalisation profitable and Materials at 63.7% are real, informative
facts about the ASX small-cap tail.

## 6. The architecture

One engine, six layers. Each layer is measurement only; the objective function stays with James.

### L0 — Substrate repair (prerequisite, not optional)

| Fix | Work | Unblocks | Status (2026-08-19) |
|---|---|---|---|
| **S1** Add `currency` to `rs_fundamentals_pit`; carry from statements. Full FX conversion deferred (§8.1) — until then, `currency` alone lets a consumer group/filter rather than silently mix units | migration `0044` (drafted, not applied) + `asxos/ingestion/fundamentals_pit.py` (built, tested) | every multiple, once L1 reads `currency` | **Currency column + carry-through built.** FX conversion itself is not — L1 (not yet built) is where a consumer would apply it |
| **S2** Exclude hybrid/capital-note `security_type` values (`Preferred Stock`/`Notes`/`BOND`, verified against live data — bank hybrids are typed `'Notes'` in `rs_security_master`, not a `universe.security_kind` gap as first suspected) from statement ingestion and factor derivation | `jobs/sync_financial_statements.py` + `asxos/domain/research/factor_scores.py` (built, tested) | every cap-weighted aggregate | **Built and tested.** Prevents *future* pollution; existing hybrid rows already in `rs_financial_statements`/`rs_fundamentals_pit` are not backfilled/deleted (a DB write outside this pass's authority) |
| **S3** One versioned segment key: `segment_map(symbol, segment_key, taxonomy_version, effective_from)`. GICS-preferred, Morningstar variants alias-mapped — including within `gics_sector` itself, which was found to carry the same Morningstar leakage as `universe.sector` (verified live 2026-08-19), not just missing values | migration `0045` (drafted) + `asxos/domain/research/segment_map.py` + `jobs/build_segment_map.py` (built, tested) | comparability through time | **Built and tested**, never run against production (no migration applied yet) |
| **S4** Backfill `prices` deeper than 2025-01-02; re-derive `adj_close` from `rs_corporate_actions` | `jobs/sync_prices.py --from` (already supports arbitrary depth) + vendor quota confirmation | percentiles, momentum, vol, theme stages | **Not started.** The backfill run is a production data write outside this session's authority (§8.2); `adj_close` re-derivation is separate, non-trivial financial logic (walking corporate actions to reconstruct historical adjusted closes) deserving its own dedicated pass, not a rushed addition here |

Per this repo's completion discipline (a unit isn't done while its output on live data is unavailable/empty — see `roadmap-state.md` Amendment D): **nothing in this table has rendered against production yet.** Every migration above is drafted, not applied; every job is unit-tested against a fake connection, not run live. The next session's first job is applying `0044`+`0045` and running `build_segment_map`/re-running `sync_financial_statements`+`compute_factor_scores`, then re-checking this doc's own evidence-appendix queries to confirm the previously-impossible numbers now look sane.

> **Update 2026-08-22 — half of that first job is done.** **S1's migration `0044` is APPLIED**
> (2026-08-21, version `20260821080458`, ledger count **97**; `REQUIRED_MIGRATIONS` bumped to
> 97 on 2026-08-22), so `rs_fundamentals_pit.currency` exists in production and the S1 row's
> "drafted, not applied" is superseded. **S3's migration `0045` is still drafted and not
> applied**, and `build_segment_map` has still never run live — S3's status text stands
> unchanged. The paragraph's blanket "every migration above is drafted, not applied" is
> therefore now true of `0045` only. Note the repo file `migrations/0044_*.sql` still carries a
> `DRAFT — NOT APPLIED` header and pre-apply comment figures; that is a known
> file-vs-database divergence handed to James, not evidence the migration is unapplied.

S3 is the ASX-specific one worth doing properly. "Materials" on the ASX is iron ore, gold,
lithium and copper in one bucket, and those do not co-move; a segment key that cannot separate
them will produce valuation aggregates no resources analyst would use. The hook already exists —
`underlyings` carries commodity/macro exposures with attribution and divergence
(`asxos/domain/underlyings/`), so commodity buckets can be a second taxonomy version rather than
a new subsystem.

### L1 — `segment_metrics`: the valuation of market segments

A table keyed `(segment_key, as_of, method_version)` and a weekly job. Construction rules that
matter:

- **Ratio of sums, never average of ratios.** Sum(cap)/Sum(earnings) is what an index-level
  multiple actually is; averaging per-name P/Es explodes on near-zero denominators.
- **Yields, not multiples, as the primary form.** E/P is additive and degrades gracefully through
  zero; P/E does not.
- **Negative earnings handled explicitly**, with `pct_cap_profitable` published alongside every
  metric, as proven in §5.
- Metrics: earnings yield, book yield, FCF yield, dividend yield, **franking-grossed-up yield**,
  segment ROE, net debt/equity, revenue growth, margin trend.
- **Mid-cycle normalised earnings** for cyclicals (long-run median margin × current revenue).
  Trailing E/P on miners is procyclical — peak earnings look cheap at the top. The 40-year
  statement history makes normalisation possible, and it is still measurement.
- **PIT throughout** (`knowledge_date <= as_of`), so the series is replayable.
- **Cross-segment dispersion** as a derived series, feeding `asxos/domain/regime/classifier.py`.
  Wide dispersion is when segment differentiation pays; narrow is when it does not.

Percentile-versus-own-history is the point of this layer, and it is gated on S4.

### L2 — Name-level relative value inside a segment

Rebuild what `rs_factor_scores` was meant to be, with two corrections:

1. **Abstention, not a neutral zero.** The current degenerate 0.000 composite is a missing input
   masquerading as an average name. Gate on `n_factors_present` and emit the existing
   `EVIDENCE_THIN` state instead.
2. **Repoint screening at the research store.** Per D5, five of the nine whitelisted fields are
   100% NULL and have no writer, so quality and income rules silently match nothing. Reading
   `rs_fundamentals_pit` instead makes screens correct *and* historically replayable — the
   walk-forward methodology the screening conventions already describe — and it is strictly less
   work than adding a writer for five columns that the research store already derives.

Firewall line: publishing a percentile per name is a measurement; emitting a ranked shortlist
with a cut is a rating. The layer publishes values and match sets, and James sorts.

### L3 — Theme and thesis overlay

The structural insight: **one aggregation engine, two membership matrices.** A segment is a hard
classification (`segment_map`); a theme is a soft weighting (`theme_holdings.exposure_strength`
with `direction`). Push name-level metrics through the theme matrix and theme-level valuation and
fundamentals come out of the same code that produces segment metrics — no second subsystem.

That yields the map a thematic manager actually works from: **adoption stage × valuation
percentile**, with holdings plotted on it. Stage (`early` → `early-institutional` →
`broad-institutional` → `mainstream` → `late-retail` → `mature`) is the crowding axis; the L1
percentile is the price axis. Early-and-cheap and late-and-expensive are opposite corners, and
naming the corners is not a recommendation — it is a coordinate system with positions on it.

Honest gap: the crowding axis is half-built. `jobs/detect_theme_stages.py` passes
`news_sentiment=None` and `retail_mention_ratio=None` into `classify_stage`, so stage suggestions
currently rest on price breadth and momentum only — themselves affected by D4. The classifier
never writes `themes.stage`; it writes `stage_suggested` and James confirms. Keep that.

### L4 — Exposure ledger and coherence: the replacement for `build_portfolio`

Three components, none of which emit a weight.

**(a) Decompose what is held.** Current book → exposure across segment, theme, commodity
underlying, factor percentile, currency, and tax state (CGT 12-month proximity, franking).
Most machinery exists: `portfolio/constraints.py` for the cap waterfall, `underlyings/attribution.py`,
`tax_overlay.py`, `benchmark/returns.py`.

**(b) Report gaps against James's declared framework.** `profiles` caps (per-name, sector, cash
floor, leverage) plus `themes.conviction_band` plus `theses.conviction_level` are all
user-declared. The system reports divergence between them and the book — a conviction-5 theme
with no exposure, a cap breached, a conviction-2 theme dominating. This is exactly the
`portfolio-coherence-reviewer` agent's job description, finally given a data layer.

**(c) Publish envelopes, not sizes.** `SizeRange` + `ConstraintResult` already express "this range
respects the caps you declared". Risk budgeting (inverse-vol via `portfolio/volatility.py`) is
offered as a **user-parameterised what-if**: James selects the budgeting basis, the system reports
the implied arithmetic and its consequences.

Explicitly **not** rebuilt: any system-generated target weight or ranked candidate list. That is
both what died with Model A and where the firewall sits.

Honest caveat: with one open lot, every decomposition in (a) is degenerate today. This is
machinery for a book of ~20 names, and should be judged on whether it is *correct*, not on
whether it currently says anything interesting.

### L5 — The brief

Segment valuation percentiles and dispersion; the stage × valuation map with positions plotted;
thesis discipline findings (already live and model-independent); coherence gaps from L4; tax
overlay flags. All measurement, all sourced, every number carrying provenance.

## 7. Dependency order

```
S2 (population hygiene) ─┐
S3 (segment key)         ├─► L1 current-cross-section quality ─► L2 ─► L3 ─► L4 ─► L5
S1 (currency + FX)       ─┘                    ▲
S4 (price depth + adj_close rebuild) ──────────┘  (percentiles, momentum, stages)
```

S2 and S3 are cheap, need no vendor calls, and are what make the aggregate credible at all —
they should go first. S1 needs FX pair coverage. S4 is the largest data cost and the widest
unblock: it gates L1 percentiles, L2 momentum factors, L3 stage detection quality, and the
benchmark series simultaneously.

L1 is buildable at "current cross-section only" quality as soon as S1–S3 land. That is already
useful, and it is honest so long as the absence of history is stated rather than papered over.

## 8. Open questions for James — ratified 2026-08-19

1. **FX: convert, not exclude.** §4/D1 already proves exclusion is not a lesser-but-acceptable
   option — it provably drops ~A$778bn of Materials (BHP+RIO+NEM) and is not a real choice, just
   a different wrong number. Full conversion to all reporting currencies is deferred as its
   own follow-up (it needs a sourced multi-currency rate feed, not just code) — **measured
   2026-08-20 as 20 distinct currencies, not the ~12 estimated here**, so scope that slice off
   the measured figure (`segval-live-validation-2026-08-20.md`, F4); L0's S1 ships the
   **interim form S1 itself specifies** — a `currency` column, carried through from source, with
   non-AUD reporters marked `EVIDENCE_THIN` and their excluded capitalisation disclosed rather
   than silently mixed or silently dropped. That interim is itself correct and firewall-clean; it
   is not a workaround pending the real fix, it *is* D1's specified fallback.
2. **Price depth: ratified as an operational step, not a design question — not executed in this
   pass.** Backfilling `prices` deeper than 2025-01-02 is a production data write (real API
   quota, real historical rows landing in the live `prices` table), which stays outside this
   session's authority per the standing Claude-driven-execution boundary on production data
   mutation. `jobs/sync_prices.py --from` already supports an arbitrary-depth backfill (§7); what
   this ratification adds is the target: back-fill to cover the same span `rs_fundamentals_pit`
   already has (median 14 annual snapshots — multi-year, not just "some more days"), confirming
   EODHD's bulk endpoint serves that range before committing to it. James runs it; this document
   no longer blocks on *deciding* the depth, only on *executing* the fetch.
3. **Resource taxonomy: deferred, v2 candidate.** GICS "Materials" is accepted as sufficient for
   L0/L1; a commodity-bucket second taxonomy version (§6, "the ASX-specific one worth doing
   properly") is real future work but does not block S3 landing GICS-preferred, alias-normalised
   segment keys now.
4. **Cadence: deferred to whoever builds L5.** Not a substrate question; revisit once L1-L4 exist
   and there is a real map to decide a cadence for.

## 9. Evidence appendix

All queries read-only against project `gxjqezqndltaelmyctnl` on 2026-08-18.

1. **Substrate audit** — row counts, date ranges, `adj_close` degeneracy, taxonomy coverage,
   empty tables. Produced every figure in §3.
2. **Naive segment aggregate** — `coalesce(gics_sector, universe.sector)`, no currency or
   population filter. Returned Materials at 560.75% earnings yield, Financials at A$5,328bn, and
   the duplicated-vocabulary segments of D3.
3. **Outlier attribution** — ordered by `net_income_ttm` desc. Identified `ATM.AU` (D1) and the
   CBA/WBC/NAB hybrid family (D2), and the `gics_sector='Energy'` misclassifications (D3).
4. **Statement currency distribution** — the 14-currency spread quantifying D1.
5. **Corrected aggregate** — `security_kind='au_equity'`, AUD-only reporters, alias-normalised
   segment names. Produced the credible table in §5 and demonstrated the AUD-filter distortion
   (Materials A$304bn) that motivates FX conversion over exclusion.
6. **Coverage quantification** — 1,833/1,872 universe coverage, 612 non-AUD reporters, 102
   unknown-currency, median 14 annual snapshots per symbol.
7. **Production `fundamentals` column fill rates** — 138,087 rows; `roe`, `revenue`,
   `net_income`, `franking_pct` and `debt_to_equity` all at exactly 0 populated. Produced D5.

Code claims were verified by reading the source, not inferred: `jobs/detect_theme_stages.py`
passes `news_sentiment=None` and `retail_mention_ratio=None`; `SizeRange` and `ConstraintResult`
exist in `asxos/domain/decision_engine/types.py`; `asxos/ingestion/fundamentals.py` contains no
reference to the five empty columns; `asxos/domain/screening/evaluator.py` whitelists them.
