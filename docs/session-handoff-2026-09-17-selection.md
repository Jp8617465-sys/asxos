# Session handoff — 2026-09-17 (selection & ideation: the mission whose premise was false)

**Status:** current
**Read priority:** read first
**Session:** interactive, remote, auto mode. James: *"explore what's possible… for investment selection
scanning/ideation, pattern recognition as a starting point"*, then *"Model A was so underbaked… if you
run a full scoping session and mission introducing all agents to properly engineer it, it's still
something worth exploring right?"*
**`main` at close:** `e751595` · 4634 passed / 12 skipped · ruff + mypy clean.

---

## STOP — read first

**I got the mission's central premise wrong, and it was approved on my say-so.** The plan James
approved rested on this, which I asserted and did not verify:

> *"#7 beat the incumbent — a **measured** deterministic baseline to compare against: **none exists**."*

**False.** `factor_scores.py:79` defines `_COMPOSITE_CATEGORIES = ("value", "quality")` and comments it
*"the thing under test"*. `alpha_eval.py` already computes effective non-overlapping sample size, the
effective t it instructs callers to quote, decile spreads with a monotonicity fraction, a
`top_minus_upper_mid` detector, calibration and a liquidity split. `eval_alpha_factors.py:92` already
drives its deciles off `composite_score` — literally the D4 #7 comparison. **~20h of the 62h plan
re-implemented shipped code**, and the test it designed measured a sub-factor rather than the composite
D4 actually names.

The mission was re-scoped mid-flight to **probe first, then decide** (James's ruling). Recorded as
**L54**. Two more lessons: **L55** — two agents converging is not verification (the same two were right
about `alpha_eval` and wrong about A-45, reading a snapshot three hours stale). **L56** — dispatching
the thing is a form of reading the code.

**Rule #11 is untouched.** Nothing this session read or revived `signals`, `signal_outcomes`,
`model_versions` or `paper_portfolio_run_metrics`.

---

## What shipped

| PR | Class | What |
|---|---|---|
| **#318** | Amber | the `factor-probe` dispatch lane — `DATABASE_URL` only, no schedule, `main` checkout, **A$0** |
| **#320** | Green | **a 107× latency fix** — the factor cross-section wrote one row per round-trip |
| **#321** | Green | two D4 corrections proposed to James |
| **#322** | Green | `docs/research/selection-landscape-2026-09.md` |
| **#323** | — | the ML feasibility study (a research *issue*, ships no code) |

**Open for James: #319** — two `.claude/agents/` safety fixes. Not the ten I originally proposed:
eight were hygiene and would have converted 6h of my time into a ten-PR review queue for the one human
bottleneck. The two that gate work: `deep-research-agent` (WebSearch/WebFetch, **zero** boundary
clauses — the weakest in the roster) and `sector-screener` (screening on four columns that are **0
non-NULL across 147,474 rows**).

---

## The result

**The D4 #7 incumbent has no detectable edge.** `composite_score`, measured on 27 cross-sections:

| horizon | IC | effective n | **effective t** |
|---|---|---|---|
| 21d | +0.0340 | 14 | **0.75** |
| 63d | +0.0122 | 6 | 0.42 |
| 126d | −0.0238 | 3 | −0.74 |
| 252d | −0.0589 | 1 | −1.73 |

**Not a verdict on factor investing — a verdict on what 435 sessions can support.** The engine flagged
its own limits without being asked: *"only 3 independent date(s) — NOT decision-grade"*, *"only 1"*,
*"Only 27 signal date(s) total."*

**The negative decile spreads are a microcap artefact, not a short signal.** At 252d the tradable IC is
−0.158 against illiquid −0.020. `liquidity_split` was built for exactly this and it worked.

**`low_vol` is the one interesting cell — and is NOT a finding.** IC +0.1095, effective n 14, effective
t 3.06 at 21d, and not in the composite. But the evaluation examined **24 cells**; five were flagged
significant and **three sit on `effective_n = 1`**. Selecting the best cell from 24 after seeing the
table is the exact failure D4 #5 exists to prevent. It carries a **declared trial count of 24** into any
seal (backlog **R-02**).

---

## The ML question, answered with arithmetic — #323

**Model A was never a test of the hypothesis.** Verified against the deleted code, not a summary:
the deployed `.pkl` could not be reproduced by this repo's trainer (`num_leaves=96/class_weight=balanced`
vs `64`/unset); ROC-AUC 0.7097 came from a file whose commit message says *"copied from old repo"*, with
3 commits and never modified; the `expected_return` gate was a **units no-op** (`reg_scale = 10_000.0`
basis points vs a `> 0.05` fraction, so **+0.05 bp cleared a bar meant to require +5%**); the leakage
test asserts `<=`, not `<`. Plus no purge, no embargo, no sample weighting on overlapping 5-day labels,
non-PIT `market_cap`, raw-close labels, and a full-data refit as the deployed artifact. **Trial count
unrecoverable** — so under D4 #5 its headline number cannot be deflated even in principle.

**The decisive arithmetic.** E[max t] over N independent null trials (Bailey & López de Prado):

| N trials | E[max t] under the pure null |
|---|---|
| 24 *(this session's own probe)* | 1.98 |
| 162 *(a disciplined search)* | 2.70 |
| **~420** | **3.00 — the crossover** |
| 5,832 *(3 arch × 81 hp × 4 feature sets × 6 labels)* | **3.73** |

**D4 #6's `t > 3.0` stops being a bar at ~420 trials.** A conventional ML search clears it *by luck, in
expectation*. The version that could clear it honestly — one architecture, one feature set, one label,
a small grid locked in advance — is a pre-registered parametric test with a flexible functional form,
not machine learning.

**Verdict: D3 stands.** Not because ML was tried and failed — Model A never tested it — but because the
bar D4 sets is one a model *search* cannot honestly clear.

**One number in #323 is flagged as a prior, not a probe:** my recollection that published single-factor
equity ICs run 0.02–0.05. That is training-knowledge, unsourced, and must be confirmed against primary
literature before the verdict is ratified — via `deep-research-agent`, whose boundaries #319 fixes
precisely so its output can be trusted.

---

## Yours (`AGENTS.md` §2 / §14)

1. **#319** — the two `.claude/` agent files. `.claude/` is draft-and-hand-over.
2. **#321** — two D4 corrections. **Both make D4 *harder*, neither touches rule #11.** D4 #3
   ("Survivorship-clean — *Already supported*") is false on the price side: **57 of 2,040** delisted
   names carry a price row, against 1,515 carrying fundamentals. And D4's `signal_outcomes` scoring
   basis is stale since `decision_engine/outcomes.py` shipped Slice 4.
3. **#323** — ratify, amend or reject **D3 stands** into the ADR (`docs/product/` is governor-owned).

**No capital, no north-star change, no spend over cap. Spend this session: A$0.**

---

## Next

**#1 — the ≥10yr delisting-inclusive price backfill (R-01).** Decided on evidence, not assumption. No
new client code needed: `eodhd.py:73` `daily_prices(symbol)` returns full history in one call when
`from_date` is omitted, and `eodhd.py:67` `exchange_symbols_delisted()` already enumerates the dead
names. Membership **must** come from `rs_security_master`, never `universe.is_active`. Two defects it
must carry are written into R-01 — the `[]`-coercion that makes a quota error look like "no history",
and `risk_free_rates` starting only at 2024-01-01.

**#2 — pre-register `low_vol` (R-02), trial count 24.** Needs R-01's depth first: at n=14 and the
measured σ(IC)=0.147, reaching t=3.0 would need a mean IC of 0.12 — roughly triple any plausible
single-factor IC.

**#3 — ASX announcements ingestion.** Free, structured, price-sensitive flagged, and nothing reads it.
The largest unexploited free data source, and PEAD's prerequisite.

The attended session's queue (A-47, A-45, A-34…) is **unchanged** and still ranks as written.

---

## Verified at close

| claim | check |
|---|---|
| sealed nothing | `research_runs` = **1**, `research_hypotheses` = **1** (unchanged) |
| revived nothing | `signal_outcomes` = **60,072** (unchanged, frozen) |
| `prices` untouched | **803,958** rows, `max(dt)` **2026-09-16** (unchanged) |
| the probe's work | `rs_factor_scores` = **27** dates, 71,759 rows, 21/21 jobs succeeded |
| no dependency added | `pyproject.toml` **not modified this mission**. The `[ml]` extra is pre-existing, optional, and not installed by `pip install -e ".[dev]"` |

**Two corrections I made to my own figures mid-session**, both caught by checking rather than reasoning:
momentum clears at **2025-12-31** (253 sessions), not 2026-01-30 — so 8 usable dates at 21d, not 7; and
the old panel was **one** usable cross-section, not "6 dates" — five were 10-row stubs.
