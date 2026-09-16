# Risk-register determination — where it lives, and whether it should be authoritative

**Status:** determination by arbi, 2026-09-16, at James's instruction — *"@arbi to determine. Also
should this be authoritative."* — in reply to the audit question *"What is hard coded right now?"*
**Scope:** the constants in `asxos/domain/decision_engine/challenge/rules.py:50-69` that decide
whether a decision packet's proposal can stand, and their duplicates in `profiles`.
**Class of any change this proposes:** the code change is Amber; the register values themselves are
a **P5 capital-policy proposal**, drafted here, not enacted — see §5.
**Every figure measured 2026-09-16 against `main` and the live database.**

## 1. What is there

**Corrected 2026-09-16 after red-team review — the first draft of this section was wrong.**
I wrote that eighteen constants sit "under the header *Ratified register values (ADR §1)*". They do
not. `rules.py:49` heads **three** constants; `rules.py:54` is a **separate** header reading
*"Data-integrity and diagnostic thresholds (**arbi draft constants**)"*, and the module docstring
names the draft status twice more (`:17-18`, `:25-28`). The code already makes the distinction this
document was drafting a recommendation to introduce. What follows is the corrected reading.

Eighteen policy constants, split three ways by the code itself:

| Group | Constants | Can it refuse a proposal? | Ratified? |
|---|---|---|---|
| **The mandate** — the three under `rules.py:49` | `CASH_FLOOR_PCT` 7.5 (`# D1`), `GROSS_LEVERAGE_CAP_PCT` 0 (`# D2`), `SECTOR_CAP_PCT` 30 (`# D8`) | **Yes — blocking** | **Yes**, James 2026-08-23 — but **D1 is "Ratified, *conditional*"** (ADR `:67`), see §4 |
| **Integrity** | `PRICE_STALE_BLOCKING_DAYS` 10 | Yes — blocking | No, and it does not need to be: "the data is broken" is a fact, not a judgement |
| **Diagnostics** | `CORRELATION_MATERIAL` 0.80, `VALUATION_GAP_MATERIAL_PCT` 25, `IMPLIED_CAGR_MATERIAL_PCT` 30, the four `LIQUIDITY_*`, `VALUATION_EXTREME_*` 5/95, `FUNDAMENTALS_STALE_MATERIAL_DAYS` 200, `PRICE_STALE_MATERIAL_DAYS` 3, `THESIS_AGE_MONITOR_DAYS` 14 | No — `material` or `monitor` only | No, **and the code says so** |

`PRICE_DETACHED_BLOCKING_RATIO = 1.0` is an arbi draft constant that emits `blocking` — the one
unratified threshold that can refuse a proposal, and an open James ruling (**backlog D-8**). My first
draft recommended demoting it. **That recommendation is withdrawn**; §4 explains why it was wrong.

**Credit where it is due.** The first impression — "the whole risk mandate is 19 magic numbers" — is
wrong twice over: it is 18, not 19 (the `decision-log.md` row of the same day says 19 and is
corrected by a later row), and the ratified/draft split is already explicit in the code.

## 2. Defect 1 — a stale duplicate in `profiles`, not two enforcement points disagreeing

**Corrected after red-team review.** My first draft said *"the allocator targets a fully invested
book with zero cash while the challenger blocks below 7.5% — two enforcement points, one ratified
decision, opposite answers."* That overstates it, and it overstates it in the direction that made my
own finding look more serious. **The live path already implements the fix I was recommending:**

| Consumer | Reads | Status |
|---|---|---|
| `portfolio_state.py:244` | `max(CASH_FLOOR_PCT, profile_value)` — docstring: *"The active profile's caps, never looser than the register"*; `sector_cap_pct` uses the mirror `min(...)` | **live, already correct** |
| `sizer.py:68` | pydantic `Field(..., ge=CASH_FLOOR_PCT)` — a sub-floor policy cannot be constructed | **live, already correct** |
| `allocator.py:183,205`, `constraints.py:205` | the raw `profiles` row, `leverage_cap − cash_floor_pct` | **dormant** (`build_portfolio` deleted, Amendment F) |

So the register cannot be undercut by the row on any path that runs today. What remains is real but
smaller: **`profiles.cash_floor_pct = 0` is a stale duplicate that misleads a reader of the row**,
and the dormant allocator would read it raw if it ever woke. That is exactly
`p5-01-risk-calibration-2026-09.md` Consequence 3, filed 2026-09-07, whose fix is already queued as
**C7 ("set 7.5")** awaiting James. This document re-discovered an owned item and should have cited it.

## 3. Determination 1 — where the authoritative copy lives: **in code**

Recommendation: **keep the mandate in code, changed only by reviewed PR.** Not because code is
tidier, but because it is the property James ratified them for:

> *"The blocking tier does not impose new restrictions — it enforces constraints already set …
> Every blocking finding is therefore objective, reproducible, and traceable to a decision made
> deliberately and calmly. **It cannot be argued with in the moment, because it was set outside the
> moment.**"* — ADR `:159`

A constant changed only by reviewed PR has exactly that property. A row arbi can `UPDATE` at runtime
is strictly weaker: it can be changed in the moment, by the agent the constraint exists to bind. The
ADR also records the failure this replaced — before the constants existed, *"the D1 cash floor is a
number in a document rather than an enforced constraint"* (`:108`). Document → code was the fix;
code → row would be a regression.

**So the fix is deduplication, not relocation:**
1. `profiles.cash_floor_pct` / `leverage_cap` / `sector_cap_pct` stop being a second source. Either
   they are derived from the register constants, or they are dropped and the allocator reads the
   register. One name, one home.
2. A test pins each mandate constant to the ADR register table, so a silent edit fails CI.
3. Category-3 policy that legitimately varies by book and by date — the paper book's capital, which
   screen is live, the entry/stop conventions — stays in rows, because it must change without a
   deploy. (The paper book was corrected to this shape today, PR #297.)

## 4. Determination 2 — should it be authoritative? **Mostly yes; three qualifications**

**D2, leverage 0% — yes, unqualified.** Ratified, closed in the ADR (`§5.1 — CLOSED`), and no
evidence disturbs it. A single-user book with no margin facility and no derivatives has nothing to
gain from borrowing capacity it cannot govern.

**D8, sector cap 30% — yes, but inoperative.** The live book holds one position, so a sector cap
cannot bind. It is authoritative and will matter the first time a second name is held.

**D1, cash floor 7.5% — yes, and my first draft's reasoning was wrong in a way worth recording.**
I wrote that D1 is *"currently BOTH inoperative and non-binding"*. The second half inverts the record.

- *Inoperative — correct.* `rule_cash_floor` returns `evaluated=False` because no authoritative cash
  source exists (#228), so the rule itself refuses nothing today.
- *"Non-binding at this size" — wrong, and backwards.* The ADR I cited two lines later says the
  opposite: the live book's cash is 0.00, so D1 *"blocks **every** proposal … and `headroom_max_pct`
  clamps every size to zero"* (`:199`). Post-#228 the outcome is unchanged — `portfolio_state.py:219`
  sets `cash_pct=None` and `sizer.py:109-113` returns zero before the subtraction. **On the live book
  D1 is the maximally binding constraint, not a dormant one.** What #228 changed is the reason
  recorded, not that anything got sized.
- *The A$632-vs-A$1,000 comparison was a category error.* A percentage floor on post-trade cash and a
  minimum position size are not commensurable. The real interaction is `p5-01` Consequence 2: the
  minimum is admissible as a range only when capital ≥ `min_position ÷ per_name_cap` = **A$10,000**.
- **Determination:** D1 stays authoritative and unchanged — but it is *binding to the point of
  blocking everything*, which is precisely why C1 exists. The gap between the register and the book
  is still a **concentration** problem: 100% one locked employer stock, which no register value
  addresses. That is separately ruled (`james-inbox.md:53` — soft-flag 10%, hard trim 20%) with
  enforcement deferred to `m14_candidate_espp_employer_concentration` and **never built**.

**The diagnostics — yes as drafts, and my proposed "fix" was largely already done.** I recommended
relabelling the header to separate ratified from draft. The code already does (§1). The genuine
residue is small: roughly eight of the fifteen carry no rationale comment
(`PRICE_STALE_MATERIAL_DAYS`, both `VALUATION_EXTREME_*`, `IMPLIED_CAGR_MATERIAL_PCT`, three
`LIQUIDITY_*`, `PRICE_DETACHED_MATERIAL_RATIO`). A one-line rationale each — cleanup, correctly
labelled, not the mislabelling problem my first draft described.

**`PRICE_DETACHED_BLOCKING_RATIO` — my recommendation is WITHDRAWN.** I proposed demoting it to
`material` pending D-8, on the principle that an unratified number should not refuse capital
deployment. Red-team review found four independent reasons that was wrong, and I verified all four:

1. **James already ruled it**, 2026-07-16 (`james-inbox.md:54`): *"unsure why cba thesis is still a
   thing — it should be automated"*, read as *build a deterministic `price_detached` check that
   auto-flags*. `price_detached` **is** that automation. Demoting it partly un-builds what he asked
   for, and his standing instruction is the top rung of the `AGENTS.md` §10 ladder.
2. **`north-star.md:61-66`** — a James-owned doc — names this exact thesis as *"the worked example"*
   of the discipline moat's failure mode.
3. **I recommended the opposite nine days ago** (`p5-01` C6: *"keep draft 1.0 / 0.25"*) and my first
   draft flipped with no new evidence.
4. **My own principle refutes it.** I excused `PRICE_STALE_BLOCKING_DAYS` on the ground that "the
   data is broken is a fact, not a judgement". `rules.py:23-29` classifies detachment as *exactly
   that* — a data-integrity failure of the decision basis, which is why it is `blocking` under D14
   rather than a new restriction. I applied my own test to one constant and not the other.

Worse, taken together with the thesis review's Rec 2 (fix or retire CBA), my two documents would have
removed both the symptom and the alarm. **The honest ask is (a) alone: one line on issue #289 closing
D-8, which `p5-01` C6 already teed up.**

## 5. What arbi will and will not do with this

**Will:** the deduplication in §3 and the labelling in §4 — code and comments, Amber, one revert,
no mandate value changed.

**Will not, without ratification:** change any of D1/D2/D8's *values*, or promote a diagnostic to
blocking. Demoting `price_detached` to `material` is proposed here, not enacted, because it changes
what can refuse a proposal.

**A tension I am naming, and a correction about its novelty.** `AGENTS.md` §14 lets arbi amend
authority docs by PR, with §2 and `.claude/**` reserved; the portfolio-manager charter makes a change
to capital policy a **P5 proposal, draft-only**. The two point different ways about the ADR register.
I am not settling that by choosing the reading that grants me more authority. But I should not
present it as a new question either: **I already settled it in practice on 2026-09-07** (`p5-01`
§3-4, drafted P5, draft-only, James did not object). The precedent is draft-only, this document
follows it, and it needs a ruling only if James wants the practice changed.

**What IS genuinely outstanding on D1, and has never been put to him.** The ADR records D1 as
*"Ratified, **conditional**"* (`:67`), and §1.1 `:93-97` names two inputs only James holds — (a)
drawdown tolerance, (b) foreseeable near-term liquidity calls — with *"Neither input has been
stated… Amend if either changes the picture."* He asked whether the register should be authoritative;
the one open James-owned item on its most consequential value is those two questions. They belong on
issue #289.

## 6. Verification

- **§1 correction:** `sed -n '49,70p' asxos/domain/decision_engine/challenge/rules.py` shows two
  headers — `:49` *"Ratified register values (ADR §1)"* over three constants, `:54`
  *"Data-integrity and diagnostic thresholds (arbi draft constants)"* over fifteen. Count is 18.
- **§2 correction:** `portfolio_state.py:244` is `max(CASH_FLOOR_PCT, …)`, `:245` is
  `min(SECTOR_CAP_PCT, …)`, `sizer.py:68` carries `ge=CASH_FLOOR_PCT`. The register cannot be
  undercut on any live path. `profiles` still returns `cash_floor_pct = 0.0000` — the stale row.
- **§4 `price_detached`:** unchanged and still `blocking`; the demotion is withdrawn, so `git diff`
  on all 18 constants is empty.
- **CBA's measured detachment is 2.471264**, not the "~3.4" the thesis review first carried:
  `detachment_ratio` (`rules.py:518-524`) is *distance from the nearest band edge over the band
  midpoint* = (152.50 − 45) / 43.5. The "×detached" figures circulating in five repo documents
  (3.4, 3.5, 2.62, 2.653333, ~4) are price÷band ratios, which is **not the quantity the 1.0
  threshold tests**. One number, one definition — that reconciliation is itself a backlog item.
- **`decision-log.md`'s "19 `Final` constants"** row (2026-09-16) is wrong; 18 is right. The log is
  append-only (`AGENTS.md` §10), so it is corrected by a later row, not edited.
