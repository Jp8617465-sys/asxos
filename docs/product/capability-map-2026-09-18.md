# Capability map — what asxos can and cannot do, 2026-09-18

**Status:** current
**Owner:** arbi
**Scope:** every production surface, probed live. Written for James's question:
*"what can this platform do, how does it build me a portfolio, what should I do with my money."*
**Method:** every number below is a live probe taken 2026-09-18 against production Supabase
and `origin/main` @ `56ec1dd`, or a cited file and line. Nothing is quoted from an older doc.
Re-derive before trusting; prose rots and this file is not exempt.

---

## 0. The one-paragraph answer

asxos is a **working research and discipline engine whose capital-facing output is held one
step short of an answer, deliberately, by a ruling nobody has made.** It ingests, values and
screens the ASX every week, holds you to your own theses, observes outcomes, and computes
Australian tax correctly. The chain that turns that into *"what should I do with my money"* —
challenge → size → staged order with tax lots — **is built and tested** (`decision_engine/`).
It returns `watch` or `abstain` every time, and will keep doing so until the capital/risk
calibration is ruled. That is **C-13**, it is James's under governor ruling **F4**, and a
ruling-ready proposal has been sitting on `main` since 2026-09-07. This is the whole gap.

> **This section was wrong in the first draft of this document and is corrected here.** The
> draft said the product had "no allocation layer" and "the middle is a documented stub". That
> conflated two different things: the **old Model-A allocator** (`domain/portfolio/build.py`),
> which is dormant by ratified design, with the **new decision chain**
> (`domain/decision_engine/`), which is built and merely ungated. `arbi-red-team` caught it.
> The distinction is the difference between "months of building" and "one decision".

---

## 1. What runs without you

Measured from `job_runs`, 2026-09-18. "Last success" is `max(started_at)` for `status='success'`.

| Job | Runs OK | Last success | Verdict |
|---|---:|---|---|
| `sync_prices` | 86 | 2026-09-17 | healthy |
| `sync_fundamentals` | 79 | 2026-09-16 | healthy |
| `snapshot_portfolio` | 76 | 2026-09-17 | healthy |
| `compose_brief` | 73 | 2026-09-17 | healthy |
| `ingest_news` | 73 | 2026-09-17 | healthy |
| `ingest_sentiment` | 68 | 2026-09-17 | healthy |
| `ingest_regulatory` | 66 | 2026-09-17 | healthy (RBA RSS only) |
| `check_thesis_invalidations` | 63 | 2026-09-17 | healthy |
| `ingest_market_context` | 56 | 2026-09-17 | healthy |
| `validate_price_data` | 51 | 2026-09-17 | healthy |
| `score_macro_theses` | 29 | 2026-09-17 | healthy |
| `compute_factor_scores` | 27 | 2026-09-17 | healthy |
| `materialise_brief_sections` | 18 | 2026-09-17 | healthy |
| `sync_financial_statements` | 11 | 2026-09-16 | weekly |
| `derive_fundamentals_pit` | 10 | 2026-09-16 | weekly |
| `build_decision_packets` | 2 | 2026-09-17 | nightly, new |
| `observe_decision_outcomes` | 2 | 2026-09-17 | nightly, new |
| `run_valuation` | **1** | 2026-09-16 | **one run ever** |
| `discover_opportunities` | **1** | 2026-09-16 | **one run ever** |
| `detect_theme_stages` | 24 | **2026-08-05** | **stopped 44 days ago** |
| `compute_opportunity_cost` | 5 | **2026-08-01** | **stopped** |
| `build_portfolio` | 6 | **2026-07-11** | **stopped; then `blocked` ×3; in no workflow** |
| `check_cron_health` | 33 | 2026-09-16 | **currently failing (41 failures), incident #327** |

Three lanes that look alive in the code are dead in production: **allocation** (§3),
**theme staging**, and **opportunity cost**.

## 2. What it can answer today

These are real, tested, and reachable.

**The weekly scan.** 1,879 ASX equities → 16 names, every exclusion named. Reproduced live
this session; the funnel is `au_equity & is_active` → liquidity (ADV ≥ A$250k, cap ≥ A$100m)
→ valued by the residual-income model → currency-verified → 3-period average ROE > Ke →
value ≥ price under both terminal conventions. 1,306 of 1,879 are `blocked` with a stated
reason rather than silently dropped.

**Thesis discipline.** `theses` + `thesis_revisions` (27 rows) + `check_thesis_invalidations`
(63 runs). Every clock reset is a human keystroke — a machine examination writes a
`packet_examined` revision that deliberately sits outside the brief's answering allowlist
(#325). CBA has been overdue since 2026-06-27 and the system will not stop saying so.

**Australian tax.** The most complete subsystem in the repo. CGT 12-month calendar
arithmetic, the Div 296 cost-base reset (s 296-50), Medicare levy on grossed-up dividends
and net capital gains, the 45-day franking rule (s 207-145), SMSF ECPI stacking on CGT.
Spec-cited, test-pinned (`docs/foundation/spec/tax-alpha.md` v1.5).

**Outcome observation.** `decision_packets` (4) + `observe_decision_outcomes` record t0 and
schedule 21/63/126-session horizons. No alpha claim — one observation is not evidence.

**The daily brief**, seven sections: prices, jobs, discipline, outcome, regulatory, news,
candidates. `EMPTY` and `MISSING` are distinct states by construction.

## 3. The one gate — and the two allocators people confuse

There are **two** allocation paths in this repo. Reading them as one is the single easiest way
to misdiagnose the product.

### 3.1 The old Model-A allocator — dormant by ratified design, not broken

`jobs/build_portfolio.py` → `PortfolioService.build()` fails at two independent gates:

1. `build.py:214` calls `resolve_production_model(required=True)`, needing one row
   `WHERE is_active AND approved_for_allocation`. Live, `model_versions` holds one row —
   `model_a/v1_5`, `approved_for_allocation = **false**` → `ModelGateDormant`.
2. `domain/portfolio/candidates.py::load_allocation_candidates` is a stub that raises: the
   Model A signals read *"is retired. **Nothing was substituted for it**, and the absence is
   deliberate."*

**Both are working as intended.** Gate 1 is rule #11's mechanical enforcement point and
`build.py:196-209` carries a `DO NOT DELETE` banner over it. James ratified
`build_portfolio` **DELETED** on 2026-08-19 (Amendment F). Last success 2026-07-11; in no
workflow. **Reviving this path would execute the opposite of a governor ruling** — it is not
the gap, and it should not be "fixed".

### 3.2 The current chain — built, tested, and gated on one ruling

`jobs/build_decision_packets.py` → `decision_engine/builder.py` → `challenge/` → `sizer.py`
→ `staging.py`. It is model-independent by construction (`sizer.py`: *"Nothing in this module
reads `signals` or imports `asxos.domain.models`"*), and it already does both things the old
path could not:

- **`sizer.py`** — Decimal-only inverse-volatility sizing with the ratified caps (cash floor
  7.5% D1, gross leverage 0% D2, sector 30% D8, profile per-name cap). It deliberately does
  *not* call the whole-book waterfall, because that waterfall's pre-flight hard-fails whenever
  `N × per_name_cap < deployable` — **which is every small book, including James's.**
- **`staging.py`** — a typed, non-executable `StagedOrder`: quantity, limit price, notional,
  and the tax lots `domain/tax/lots` selects (`min_cgt` default, spec §5.5). `not_executable`
  is a `Literal[True]`; no broker, no venue, no credential, no network, no write.

**So the brokerage-instruction surface already exists.** What is missing is permission to make
it non-zero.

### 3.3 The gate itself

`builder.py::derive_state` returns `abstain` if the challenge did not pass, and `watch`
whenever it did but `calibration is None` or tax readiness is not `pass`. Every call site in
the codebase passes `None`, because **no producer of a capital-risk calibration exists** — and
that is policy, not oversight. `portfolio-policy.md`: *"arbi does not assume a number."*
Governor ruling **F4**: *"James must complete the capital/risk calibration before Stage 4."*

A non-`None` calibration today **raises** rather than guessing a direction. That is the design
working: the system refuses to invent the one number that decides how much of James's money is
at risk.

`docs/proposals/p5-01-risk-calibration-2026-09.md` is on `main`: eight parameters, a
recommended default for each, the exact `portfolio-policy.md` diff, and one enumerated ruling.
**That single ruling is the difference between `watch` and an actionable, tax-aware,
broker-ready order draft.**

### 3.4 Two live numbers that will bite the moment it is ruled

- `profiles.baseline.capital_aud = 6,666.98`, last written **2026-07-04** by hand
  (`cli/profile.py:78` is the only writer; there is no reconciliation to the live book, which
  read **8,249.90** on 2026-09-04). With `per_name_cap_pct = 0.10` and
  `min_position_aud = 1,000`, the largest legal position is **A$666.70 against a A$1,000
  minimum** — so `constraints.trim_min_position` (`build.py:245`) would drop every target.
  Tracked as **A-46**, which depends on **C-27** (re-point every `capital_aud` reader at
  `cash_balance_assertions`, treating NULL as unmeasured).
- **An A$8k book cannot hold 20 names at a A$1,000 minimum.** That is arithmetic, not a
  defect. It is also the strongest argument for the ETF/fund lane in §6: a fund is the only
  instrument class that gives this book diversification inside one minimum position.

> **First-draft correction:** this document previously claimed
> `constraints.drop_below_minimum` was dead code with zero callers. **No such function
> exists.** The real one is `trim_min_position` (`constraints.py:272`) and it has a live
> caller at `build.py:245`. Both halves of the original claim were wrong.

## 4. Where the output is still wrong

Reproduced live: of the 16 names the weekly scan passes, **six are listed investment
companies** — FGG, FGX, HM1, LSF, PGF, WQG — carrying `security_kind = 'au_equity'`. A
residual-income model on a LIC is **circular**: the model values the residual over book of
tangible common equity, and a LIC's book value *is* a securities portfolio already marked to
market, so "value vs price" merely restates NTA vs price while presenting itself as an
earnings-based valuation. That is a **38% false-positive rate on the headline output James
reads**, and it is a classification defect, not a model failure.

**Cause, found this session.** `ingestion/universe.py` maps EODHD's `Type` to `security_kind`,
and EODHD types every ASX LIC as `"Common Stock"`. Its `"FUND"` type means *unlisted* managed
funds — live, all 11 `lic` rows carry `0P0000…` Morningstar identifiers (Vanguard, PIMCO,
Bentham, Janus). So the mapping could never classify an ASX LIC. The code said so and deferred
the fix: *"a curated LIC/REIT reclassification is a later refinement"*, justified because
au_equity was *"the safe default that keeps their existing Model A/thesis eligibility"*.
**That justification died with Model A** (PR #144, rule #11) — leaving only the cost.
Fixed this session; see §8.

**BWP.AU is deliberately not in scope.** It is BWP Trust, an A-REIT, and
`portfolio/build.py:52-53` records that A-REITs stay `au_equity` so a genuine delisting is
still force-sold. A REIT's book is marked *property*, not marked securities, so the
circularity argument does not carry. (An earlier note counted it among the misclassified; that
is the A-REIT valuation-domain question, which is separate and unruled.)

An eighth, FML.AU, prints `value_to_price = 6.26` on 24.7% ROE — the cyclical-peak artifact
the model is known to produce. The honest passing set is closer to **eight** than sixteen.

## 5. The macro read it holds — and why you have not seen it

Three `macro_theses` at `approved`, each regime-tagged with a machine-checkable falsifier,
scored nightly by `score_macro_theses` (29 runs):

| id | Quadrant | Claim | Horizon |
|---:|---|---|---:|
| 6 | falling growth / falling inflation | Breadth-led catch-down — 25.9% of ASX above 200d MA under an 8,844 index resolves into orderly risk-off | 6 mo |
| 7 | falling growth / rising inflation | Sticky ~5% AU long end — term premium persists, pressuring REITs/tech/infrastructure, favouring short-duration cash flow | 9 mo |
| 11 | rising growth / falling inflation | No recession signal from rates/credit — US 10y-2y positive (+0.37pp), HY OAS ~275bps vs a 450 bar | 6 mo |

They deliberately bracket each other on the inflation axis, and each states its own limit:
**all three were authored from a single 2026-07-03 snapshot** and say so in their own text.
They are now ~11 weeks old.

**No brief section renders them.** `SECTION_ORDER` (`brief/section.py:26`) has no macro entry.
The regime read exists, is governed, is scored nightly — and reaches no surface James reads.

## 6. The moat layers, by how much of each exists

`north-star.md` §1.3 ranks defensibility. Measured against live rows:

| Layer | Live state |
|---|---|
| Discipline | **Real** — 27 revisions, 63 invalidation runs, the clock invariant holds |
| Tax | **Real** — spec v1.5, the deepest test coverage in the repo, **no brief surface** |
| Themes | **1 approved theme** (`big-4-banks`), 1 approved holding, stager stopped 2026-08-05 |
| ETFs | **487 in universe, zero coverage by any lane** |
| Signals (ML) | Shelved 2026-07-11, quarantined by rule #11 |

The two layers named as the product's moat after the ML shelf — **themes and ETFs** — are the
two with almost nothing in them.

## 7. What this means for the money

One open lot: **HUBS.NYSE**, 24 shares, ESPP, A$6,978.23 cost base, acquired 2026-05-31.
No ASX position at all. Two approved theses (CBA.AU `watching`, HUBS.NYSE `active`).

The platform's honest position on 2026-09-18 is: *here are ten names that look cheap on one
sealed model that failed its own predictive test; here is a macro read from July that reaches
no surface you read; you are 83 days overdue on reviewing CBA; I can size a position and draft
a tax-aware order — and I will return `watch` on every one of them until you rule C-13.*

**So the backlog splits cleanly in two.** What is James's: one ruling (C-13), with the
proposal already written. What is arbi's: everything that makes the answer worth having when
the ruling lands — clean inputs (§4, done this session), a macro surface (§5), and the
fund/ETF lane (§6) that is the only instrument class an A$8k book can actually diversify
into.


---

## 8. Changed this session (2026-09-18)

**LIC reclassification** — `ingestion/universe.py`. A curated set of 45 ASX LICs/LITs is
reclassified out of `au_equity`, removing them from the residual-income sweep
(`valuation/universe.py:74`) and the liquidity screen (`screening/evaluator.py:284,528`).
Six of them were in the current passing set of sixteen.

Two halves, because one without the other does nothing:

- `classify_kind()` applies the curated override **after** the EODHD type map, so newly listed
  LICs classify correctly on first ingestion.
- `refresh_universe` now **reconciles** an existing row whose stored kind predates the
  curation. This matters: `security_kind` was previously written **only on INSERT**, so a row
  misclassified at first ingestion could never be corrected — which is precisely how six LICs
  reached James's candidate card. The branch is deliberately narrow: it corrects only *to*
  `lic`, and only for a curated symbol, so it can never rewrite a hand-set `us_equity`/`index`
  row or churn a row EODHD retypes.

Curation is by ticker, not name pattern: `WQG` ("WCM Global Growth Ltd") contains no
fund/trust/investment token and would be missed, while `CWP` ("Cedar Woods Properties Ltd", a
homebuilder) would be wrongly caught. The set is a **starting** set — not exhaustive, not
self-maintaining; a newly listed LIC lands as `au_equity` until added.

Six tests, all mutation-checked. Suite 4718 → 4724.
