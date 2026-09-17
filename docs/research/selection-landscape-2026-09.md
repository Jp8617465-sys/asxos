# Investment selection & ideation — what this system can do, what the industry does, and what is worth building

**Date:** 2026-09-17 · **Status:** DRAFT — §1.3's measured "after" state is pending the probe re-run
· **Class:** Green (document)
**Commissioned by James:** *"explore what's possible, what can be done in our current infrastructure and
what is industry standard or pushing the boundary for investment selection scanning/ideation, pattern
recognition as a starting point and extrapolate from there."*

Every number here traces to a `supabase-ro` query run on 2026-09-17 or to a `path:line`. Where a figure
could not be established, this says so rather than estimating it.

---

## §0 — The one-screen summary

**The finding that reorganised this report.** The mission that produced it opened on the premise that no
measured deterministic baseline existed and one had to be built. That premise was false. The
value×quality composite D4 names as the incumbent is **implemented** (`factor_scores.py:79`), the engine
that scores it is **implemented and more rigorous than what was proposed to replace it**
(`alpha_eval.py`), and the comparison D4 #7 requires is **already wired** (`eval_alpha_factors.py:92`).

What was missing was never the engine. It was the **panel**: before this week `rs_factor_scores` held one
usable cross-section — a single date — so every horizon collapsed to roughly one independent observation.

So the honest state of "selection and ideation" here is:

1. **The measurement apparatus is good and underused.** It computes effective (non-overlapping) sample
   size and tells callers to quote the effective t. That is a higher standard than most retail — and some
   professional — factor work applies to itself.
2. **The binding constraint is price history, and only price history.** Fundamentals reach ~20 years and
   include the dead names. Prices reach 435 sessions and exclude them.
3. **The system's real scarcity is not ideas.** It is review throughput and evidence depth. Every
   generator built so far has out-run the capacity to adjudicate what it generates.

**What this report does not contain: a list of stocks.** That is not modesty, it is a hard constraint —
James's own pre-sealed `RESPONSE_RULE` and north-star §1.6 forbid ranked "opportunities" as output. The
deliverable of ideation here is **a queue of falsifiable hypotheses** (§5), each of which must survive
pre-registration before it may inform anything.

---

## §1 — Current capability, measured

### 1.1 The factor stack that exists

| Component | Path | What it does |
|---|---|---|
| Factor computation | `asxos/domain/research/factor_scores.py` | Five sector-neutral categories from PIT fundamentals + prices |
| The incumbent | `factor_scores.py:79` | `_COMPOSITE_CATEGORIES = ("value", "quality")` — commented *"the thing under test"* |
| Panel loader | `asxos/domain/research/alpha_loader.py` | Joins scores forward to prices at `FACTOR_HORIZONS = (21, 63, 126, 252)` |
| Evaluation engine | `asxos/domain/research/alpha_eval.py` | rank-IC, effective sample size, decile spreads, calibration, liquidity split |
| Runner | `jobs/eval_alpha_factors.py` | Prints the report; **writes nothing** |

The five categories (`factor_scores.py:71-79`):

| category | sub-factors |
|---|---|
| value | `earnings_yield`, `book_yield` |
| quality | `roe`, `roa`, `gross_margin`, `operating_margin` |
| momentum | `mom_12_1` |
| low_vol | `neg_vol` |
| yield | `gross_yield` |

**Momentum is one sub-factor of one category, and is not in the composite.** This matters: a standalone
momentum test measures neither the D4 #7 incumbent nor a constituent of it.

### 1.2 What `alpha_eval` already does right

This is the part of the system most worth knowing about, because it is a quality bar already met:

- **`effective_sample_size` (`alpha_eval.py:105`)** — counts *non-overlapping* dates at each horizon.
  Monthly cross-sections at a 126-day horizon overlap ~6:1; naive n would overstate significance ~2.4×.
- **`effective_t`, with the instruction to quote it (`:17-18`)** — *"Callers must quote the effective t."*
- **`monotonic_frac` (`:192`)** — the fraction of adjacent decile steps that increase. A spread can be
  positive while the ladder is noise; this separates them.
- **`top_minus_upper_mid` (`:171`)** — surfaces the *"top decile has no edge"* pathology specifically.
  This is the exact shape of Model A's failure, and the engine looks for it by name.
- **`liquidity_split` (`:227`)** — separates tradable from illiquid names, so an "edge" that lives
  entirely in microcaps cannot masquerade as a portfolio signal.
- **Underpower warnings** — emitted rather than suppressed.

### 1.3 The panel

`rs_factor_scores` per `as_of`, as it stood before this mission:

| as_of | rows |
|---|---|
| 2026-07-02 / 07-09 / 07-16 / 07-23 / 07-30 | 10 / 11 / 11 / 11 / 11 |
| 2026-08-11 | **3,308** |

**One usable cross-section.** The five July dates are 10–11 row stubs from symbol-limited runs. Any
statement that the composite "has been evaluated" was, until now, true only of a single date.

**The measured "after" state is pending, and this section will not be filled in from expectation.**
The first probe dispatch (`factor-probe` run 35173534051) was **cancelled, not completed**: it exposed a
latency defect — `refresh_factor_scores` wrote one row per round-trip, ~13 minutes per cross-section, so
a 21-date panel would have taken ~5 hours against a 60-minute lane timeout. That is fixed separately;
the panel is rebuilt and this section completed only once a run actually finishes.

### 1.4 Data depth — the asymmetry that governs everything

| table | rows | symbols | range | delisted names covered |
|---|---|---|---|---|
| `prices` | 803,958 | 2,457 | 2025-01-02 → 2026-09-16 (**435 sessions**) | **57** of 2,040 |
| `rs_fundamentals_pit` | 54,545 | 3,372 | 1987 → 2026 | **1,515** of 2,040 |

Fundamentals coverage is genuinely broad from ~2004 (1,090 symbols) and substantial by 2008 (1,588
symbols, 1,340 with ROE). **The fundamentals panel is deep and survivorship-clean; the price panel is
neither.** Since every cross-sectional test needs a forward *return*, and returns come from prices,
prices are the single binding constraint on all of §5.

`alpha_loader.py:26-29` already carries the standing warning that at this depth the 126/252d windows
yield *"~1-2 INDEPENDENT dates"*.

### 1.5 Everything else, counted

| surface | live count | reading |
|---|---|---|
| `screening_rules` / `screening_runs` | 2 / 1 | the Tier-2a evaluator works and has been run once |
| `themes` / `theme_holdings` | 1 / 2 | theme stewardship is the thinnest moat layer |
| `theses` (all / approved) | 23 / **2** | governance is real; 0059 closed the default that laundered rows |
| `macro_theses` | 4 | |
| `agent_runs` (total / unacted with a proposal) | 5 / **0** | the review queue has never had a backlog |
| `decision_packets` / `thesis_outcomes` | 3 / 12 | the decision spine runs and is scored |
| `research_hypotheses` / `research_runs` | 1 / 1 | the registry works; one sealed test has been run |
| `rs_estimates` | **0** | earnings-revision factors are not merely unbuilt — there is no data |

**On `agent_runs`: unacted proposals = 0.** A proposed "cap pending proposals at 5" was dropped from this
mission on this number. The recorded 2026-07-16 concern was about *two* proposals sitting 13 days — a cap
at five would never have bound, and expiry discards unreviewed work rather than reviewing it. The
bottleneck is review *throughput*, and a write-side cap does not touch it.

---

## §2 — Industry standard, and how much of it is reachable here

| Technique | Status here | Blocker |
|---|---|---|
| **The five factors** (value, quality, momentum, low-vol, yield) | **Built** — `factor_scores.py` | none |
| **Sector-neutral scoring** | **Built** | none |
| **Piotroski F-score** | Buildable today | needs accruals/CFO fields; `rs_fundamentals_pit` has margins, ROA, equity |
| **Greenblatt magic formula** (EY + ROIC) | Buildable today | ROIC needs invested capital; `net_debt` + `total_equity` present for 2,500/3,372 |
| **PEAD** (post-earnings-announcement drift) | **Not buildable** | requires announcement *dates*; none ingested |
| **Earnings revisions** | **Not buildable** | `rs_estimates` = **0 rows** |
| **Purged / combinatorial-purged CV** | Not built; **required by D4 #4** | needs the deep panel first |
| **Deflated Sharpe + PBO** (Bailey & López de Prado) | Not built; **required by D4 #5** | needs a trial count discipline |
| **t > 3.0** (Harvey, Liu & Zhu 2016) | **Unreachable at current depth** | 435 sessions |

The three "required by D4" rows are the honest answer to *"what is industry standard?"* — the standard is
not a technique, it is a **validation protocol**, and this repo has already written that protocol down
(ADR §1.7). What it has not had is the data depth to execute it.

---

## §3 — The frontier, and which parts are real

- **ASX announcements NLP.** Company announcements are free, structured, and carry a price-sensitive
  flag. **Nothing in this system ingests them.** This is the largest unexploited *free* data source
  available, and it is the prerequisite for PEAD (§2) as well as for event-driven work. Highest-value
  ingestion gap found.
- **LLM-drafted, evidence-cited analysis** — only ever inside `admit_llm_finding`, never as a free-form
  "critique this thesis" prompt (ADR §7 forbids that explicitly: fires on everything, likelihood ratio
  ≈ 1).
- **Regime-conditional factor tilts** — plausible, and the regime classifier exists, but conditioning
  multiplies the trial count and therefore the DSR penalty. Not worth attempting before §5 #1 resolves.
- **A machine-learning successor.** ADR §7 puts this out of scope *until D4's bar is met* — conditional,
  not a ban. The feasibility study (separate `type:research` ticket) answers whether the bar is
  reachable, with the multiple-testing budget computed **before** any model is built. Rule #11 stands
  meanwhile: Model A was measured on 19,032 matured signals and had conviction inverted at the top.

---

## §4 — What is ASX-specific, and therefore actually defensible

This is the part a global factor library does not give you, and it is where the moat is:

1. **Franking.** `factor_scores.py:57` already computes `_GROSS_UP = 0.30/0.70 = 0.428571…`. A
   franking-adjusted total return is the one factor construction that is **materially different for an
   Australian resident investor** and is largely absent from international research. `franking_avg_pct`
   is carried in `rs_fundamentals_pit`.
2. **Tax-aware holding periods.** The CGT 12-month rule is calendar arithmetic already implemented to
   spec. A selection process that is indifferent to the discount boundary is leaving after-tax return on
   the table; this system already knows the boundary per lot.
3. **Concentration.** Materials and Financials dominate the index and co-move more than GICS implies.
   `.claude/rules/portfolio-conventions.md` records that the v1 allocator is explicitly risk-blind to
   this. Any selection work that ignores it will produce a portfolio that is one bet.
4. **Microcap artefacts.** The sub-cent price problem (a recorded +833,230% artefact) is why
   `alpha_eval`'s liquidity split matters more here than on a large-cap universe.

**§4.1 is the single most defensible idea in this document**, and it is model-independent.

---

## §5 — The queue: hypotheses, never names

Ordered by expected information per hour, and each must pass pre-registration before it may inform
anything. **This is the deliverable of "ideation" in this system** — not a shortlist of securities.

| # | Hypothesis | Testable today? |
|---|---|---|
| 1 | The value×quality composite carries positive cross-sectional rank information at 21d in liquid ASX names | **Yes** — being measured now |
| 2 | Franking-adjusted yield outperforms raw yield on an after-tax basis for a resident investor | Yes, partially — needs the deep panel for power |
| 3 | Quality × value beats either leg alone (is the interaction real, or is one leg carrying it?) | Yes — same panel |
| 4 | 12-1 momentum carries rank information in liquid ASX names | Only 7 dates today; needs depth |
| 5 | PEAD exists on the ASX at a retail-tradable horizon | **No** — announcement dates not ingested |
| 6 | A properly-engineered ML successor can clear D4 | Gated on the feasibility study |

**Note the ordering change.** #1 is the incumbent, and it was ranked below momentum in the plan that
opened this mission. That was the error this report exists to correct: momentum is a sub-factor, and
testing it first would have measured the wrong thing while the thing D4 actually names sat unmeasured.

---

## §6 — What "pushing the boundary" honestly means here

Not a more sophisticated model. At N=1, with one operator and a weekly cadence, the frontier is:

1. **Measuring what you already have, properly.** The apparatus outclasses the panel it runs on. Deepening
   the panel is worth more than any new technique.
2. **After-tax, franking-aware construction.** Genuinely differentiated, genuinely under-researched,
   genuinely computable here.
3. **Ingesting announcements.** Free, structured, and untouched.
4. **Raising review throughput, not generation.** The recorded failure is generators without a drain.
   Nothing in this report proposes a new generator.

The boundary is *not* "more signals". It is "fewer claims, each of which survives a pre-registered test".

---

## §7 — Anti-scope, as checks

- No ranked list of securities as product output (`RESPONSE_RULE`, north-star §1.6).
- No read of `signals`, `prob_up`, `shap_factors`, `signal_outcomes`, `model_versions`,
  `paper_portfolio_run_metrics` as a basis for anything (rule #11).
- No ML engine before D4's eight criteria are met and recorded (ADR §7, §1.7).
- No free-form "critique this thesis" prompt, no debate rig, no LLM self-scoring (ADR §7).
- No base-rate challenge before Slice 4 (ADR §7 — the rate would be fabricated).
- Nothing here is advice. Decision-support only (s766B).

---

## Appendix — provenance

Live counts: `mcp__supabase-ro__execute_sql`, 2026-09-17. Code claims: `path:line` against `main` at
`17cb203`. The probe runs as `factor-probe`, a dispatch-only lane carrying `DATABASE_URL` only, at A$0.

**The probe is not a pre-registered test.** It writes no `research_runs` row, seals no hypothesis and
promotes nothing. Its numbers are evidence for a build decision and for this document — they are not a
verdict of record, and must not be cited as one.

**Every Model A claim in §3 was verified against the deleted code directly** (`git show <sha>^:<path>`
at `da64c1b^`), not taken from a summary:

| claim | evidence |
|---|---|
| the deployed artifact was not built by this repo's trainer | `model_a_v1_5_features.json` declares `num_leaves=96, class_weight=balanced, L2=0.6`; `train.py` `DEFAULT_CLF_PARAMS` has `num_leaves=64, reg_lambda=0.4`, no `class_weight` |
| ROC-AUC 0.7097 has no reproducible origin | `git log --all --follow` on `model_a_v1_5_metrics.json` → 3 commits: created at `c0ec166`, then the two deletions. `c0ec166`: *"Models copied from old repo"* |
| the `expected_return` gate was a no-op | `train.py:156` `reg_scale = 10_000.0` (basis points) vs `thresholds.py:27` `expected_return > 0.05` (a fraction) |
| the leakage test permitted a shared boundary date | `test_train_walk_forward.py:63` asserts `max_train_dt <= min_test_dt` — `<=`, not `<` |

Plus: no purge, no embargo, no sample weighting on overlapping 5-day labels; `market_cap` joined on
symbol with no date key; labels on raw `close`, not `adj_close`; the deployed artifact a full-data refit
with no out-of-sample metric of its own.

**Two consequences this report carries forward.** Model A was too compromised to have been a test of the
hypothesis either way — *"underbaked"* is now a forensic finding rather than an impression. And its
**trial count is unrecoverable** (no hypothesis registry existed; tuning demonstrably happened upstream),
so under D4 #5 its headline number cannot be deflated even in principle.

**The caveat that cuts the other way, stated rather than buried.** The 2026-07-11 decay verdict rests on
signal dates that cluster into roughly **two independent market episodes**
(`docs/archive/research/alpha-signal-verification.md`). That is sufficient to retire *that artifact* —
all the verdict claims — and insufficient to close out the signal family. **Rule #11 is unaffected
either way:** it is a rule about Model A's output, and it stands.
