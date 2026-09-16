# Risk-register determination — where it lives, and whether it should be authoritative

**Status:** determination by arbi, 2026-09-16, at James's instruction — *"@arbi to determine. Also
should this be authoritative."* — in reply to the audit question *"What is hard coded right now?"*
**Scope:** the constants in `asxos/domain/decision_engine/challenge/rules.py:50-69` that decide
whether a decision packet's proposal can stand, and their duplicates in `profiles`.
**Class of any change this proposes:** the code change is Amber; the register values themselves are
a **P5 capital-policy proposal**, drafted here, not enacted — see §5.
**Every figure measured 2026-09-16 against `main` and the live database.**

## 1. What is there

Eighteen policy constants (plus two private helpers) under the header *"Ratified register values
(ADR §1)"*. They split three ways, and the split matters more than the count:

| Group | Constants | Can it refuse a proposal? | Ratified? |
|---|---|---|---|
| **The mandate** — `REGISTER_RULES`, the first five rules | `CASH_FLOOR_PCT` 7.5 (`# D1`), `GROSS_LEVERAGE_CAP_PCT` 0 (`# D2`), `SECTOR_CAP_PCT` 30 (`# D8`), plus the position cap and the derivatives/shorting bar | **Yes — blocking** | **Yes**, James 2026-08-23 (ADR `:67-74`) |
| **Integrity** | `PRICE_STALE_BLOCKING_DAYS` 10 | Yes — blocking | No, and it does not need to be: "the data is broken" is a fact, not a judgement |
| **Diagnostics** | `CORRELATION_MATERIAL` 0.80, `VALUATION_GAP_MATERIAL_PCT` 25, `IMPLIED_CAGR_MATERIAL_PCT` 30, the four `LIQUIDITY_*`, `VALUATION_EXTREME_*` 5/95, `FUNDAMENTALS_STALE_MATERIAL_DAYS` 200, `PRICE_STALE_MATERIAL_DAYS` 3, `THESIS_AGE_MONITOR_DAYS` 14 | No — `material` or `monitor` only: they require a recorded response, they cannot refuse | No |

**The exception, and it is the finding:** `PRICE_DETACHED_BLOCKING_RATIO = 1.0` sits in the
diagnostic group but `rule_price_detached` emits **`blocking`**. So exactly one *unratified
judgement threshold* can refuse a proposal outright — and it is already an open James ruling,
**backlog D-8** ("pin `price_detached` thresholds — blocking ≥ 1.0, material ≥ 0.25"). The number is
in force ahead of the ruling that was meant to set it.

**Credit where it is due.** The first impression — "the whole risk mandate is 19 magic numbers" — is
wrong. The mandate constants carry their decision ids; the register/diagnostic split is deliberate
and documented in the code; and `REGISTER_RULES` exists precisely so "no register rule failed" is
not confused with "every register rule ran". The defects below are narrow.

## 2. Defect 1 — the two enforcement points disagree about D1

`profiles` holds a second copy of the mandate, and the two halves of the system read different ones:

| | Value | Consumer |
|---|---|---|
| Ratified D1 | cash floor **7.5%** | `rule_cash_floor` (`challenge/rules.py`), used directly as the threshold |
| Active profile | `cash_floor_pct` = **0** | `allocator.py:183,205` and `constraints.py:205`, which compute `target_sum = leverage_cap − cash_floor_pct` |

On the active profile that is `1.0 − 0.0 = 1.0`: **the allocator targets a fully invested book with
zero cash, while the challenger blocks anything leaving less than 7.5% cash.** Two enforcement
points, one ratified decision, opposite answers.

It is latent, not live — the allocator is dormant (`build_portfolio` deleted, Amendment F) and
`rule_cash_floor` returns `evaluated=False` because no authoritative cash source exists (#228). It
bites the moment either half wakes up. `leverage_cap` (1.0) and `GROSS_LEVERAGE_CAP_PCT` (0) are the
same policy in different units — not a contradiction, but the same duplication hazard.

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

**D1, cash floor 7.5% — yes as policy, but it is currently BOTH inoperative and non-binding, and
that should be said plainly rather than left implied.**
- *Inoperative:* `rule_cash_floor` cannot evaluate, because no authoritative cash source exists
  (#228). The floor refuses nothing today.
- *Non-binding at this size:* 7.5% of the live book (A$8,431) is A$632 — below `min_position_aud`
  (A$1,000). At this capital the floor is never the constraint that binds; concentration is. The
  book is **100% one locked employer stock**, which no register value addresses.
- *The ADR already anticipated this:* it is why C1 exists — the live book's zero cash *"blocks every
  proposal at the D1 floor … C1 is the book on which a 10% position produces a real, non-zero
  answer"* (`:199, :211`).
- **Determination:** D1 stays authoritative and unchanged. The honest statement is that it is a
  policy in waiting, and the gap between it and the book is a **concentration** problem, not a
  cash-floor problem. Re-opening the 5–10% range would be optimising a constraint that has never
  bound while ignoring the one that does.

**The diagnostics — no, not as they stand, and the fix is cheap.** Fifteen thresholds decide whether
James is *told* something is a concern. They are not ratified, and they do not need a governor
ruling to exist — but they should be labelled for what they are. **Recommendation:** rename the
header from *"Ratified register values (ADR §1)"* to separate the two groups explicitly, and give
each diagnostic threshold a one-line rationale in place of a bare number. Today a reader cannot tell
`CASH_FLOOR_PCT` (ratified, blocking, James's) from `IMPLIED_CAGR_MATERIAL_PCT` (nobody's, advisory)
— and the header tells them both are ratified.

**`PRICE_DETACHED_BLOCKING_RATIO` — no, not until D-8 is ruled.** This is the one unratified
judgement that can refuse a proposal. Two honest options: (a) James rules D-8 and it joins the
mandate; or (b) it is demoted to `material` until he does, so nothing blocks on an unratified
number. **Recommendation: (b), pending (a)** — a threshold that refuses capital deployment should
not outrun its ruling, and demotion is one line and one revert.

## 5. What arbi will and will not do with this

**Will:** the deduplication in §3 and the labelling in §4 — code and comments, Amber, one revert,
no mandate value changed.

**Will not, without ratification:** change any of D1/D2/D8's *values*, or promote a diagnostic to
blocking. Demoting `price_detached` to `material` is proposed here, not enacted, because it changes
what can refuse a proposal.

**A tension I am naming rather than resolving in my own favour.** `AGENTS.md` §14 lets arbi amend
authority docs by PR, with §2 and `.claude/**` reserved. The portfolio-manager charter makes a
change to capital policy a **P5 proposal, draft-only**. The ADR register is capital policy, so the
two rules point different ways about whether arbi may amend it. I am not settling that by choosing
the reading that grants me more authority. This document is a proposal; the mandate values stand
until James rules, and the §14/P5 conflict itself deserves a one-line ruling.

## 6. Verification

- The contradiction: `SELECT cash_floor_pct, leverage_cap FROM profiles WHERE is_active` returns
  `0.0000, 1.0000`; `CASH_FLOOR_PCT` is `7.5`. After §3, one of the two is derived from the other
  and a test fails if they diverge.
- The register: a test asserts each mandate constant equals its ADR table row.
- `price_detached`: if (b) is taken, `rule_price_detached` emits no `blocking` finding until D-8 is
  ruled, pinned by a test.
- No mandate value changes in any of it — `git diff` on the three ratified constants is empty.
