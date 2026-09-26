# Sealed agent numbers — WBC.AU fixture, F-E2E positive control

**Sealed 2026-09-07, before James entered his.** These are the agent's numbers for the
agreement-rate datapoint (S0 metric). **They do not enter the thesis row.** James's numbers do.
If this file's commit is not an ancestor of the commit recording James's numbers, the ordering
broke and the datapoint is discarded.

**WBC.AU is a fixture symbol for this run.** Test input. This file is not advice, not an order,
and authorises nothing. The book it is sized against is the C1 *paper* book (ADR D15).

---

## 1. Evidence pack — all measured at knowledge cutoff 2026-09-04

| Fact | Value | Source |
|---|---|---|
| Last close | `34.960000` | `prices`, dt `2026-09-04` |
| 52-week high | `42.950000` | `prices`, trailing 365d |
| 52-week low | `33.680000` | `prices`, trailing 365d |
| 50-day mean close | `35.921900` | `prices` |
| 200-day mean close | `37.735700` | `prices` |
| Median dollar volume, 60d | `152,900,296` AUD | `prices`, `avg(close*volume)` |
| Price rows available | `425` | `prices` |
| P/E | `16.699500` | `fundamentals`, as_of `2026-08-29` |
| P/B | `1.636000` | `fundamentals`, as_of `2026-08-29` |
| EPS | `2.030000` | `fundamentals`, as_of `2026-08-29` |
| Dividend yield | `0.045700` (4.57%) | `fundamentals`, as_of `2026-08-29` |
| Market cap | `115,765,362,688.000000` AUD | `fundamentals`, as_of `2026-08-29` |
| Sector | Financial Services | `universe` |

### What the evidence does not contain

Three fundamental fields are **NULL** for every WBC.AU row: `franking_pct`, `roe`,
`debt_to_equity`. Any claim about franking credits, capital efficiency or balance-sheet
leverage is therefore **unsupported by this evidence pack**, and I make none. A bank thesis
that cannot see ROE or gearing is missing the two measures that matter most for a bank.
That absence is the single largest reason the conviction below is low.

### The shape the numbers sit in

Price `34.960000` is **below both** the 50-day (`35.921900`) and 200-day (`37.735700`) means,
and sits `1.280000` above the 52-week low against `7.990000` below the 52-week high — the lower
quartile of its own year. P/E `16.6995` is not obviously cheap for a major Australian bank on
`EPS 2.030000`; the de-rating is in the price, not yet demonstrably in the earnings.

---

## 2. Sealed numbers

| Field | Value |
|---|---|
| Entry band | `33.500000` – `35.200000` |
| Stop | `31.500000` |
| Target | `40.000000` |
| Timeline | `18` months |
| Conviction | `2` of 5 |

## 3. Consequence reasoning — what each number mechanically causes

**Entry band `33.500000`–`35.200000`.** The last close `34.960000` falls **inside** this band, so
`detachment_ratio` (`challenge/rules.py`, the canonical definition — the line number this
once cited, 429-435, has since moved) returns exactly `0` and `rule_price_detached`
emits no finding. This is the deliberate consequence: CBA's band `42–45` against a close of
`160.42` measures `2.653333` from the band **edge** and blocks. A band chosen around the
observed price is what makes this a positive control rather than a second negative one. The
lower bound sits below the 52-week low so a further drift down does not immediately invalidate
the plan; the upper bound sits below the 50-day mean so it is not chasing.

**Stop `31.500000`.** `9.897597%` below the last close, and `6.472743%` below the 52-week low —
placed beneath the year's floor so ordinary volatility does not trigger it, and a breach means
the security has made a new low rather than merely wobbled. Mechanically, a non-NULL stop is one
of `enter_thesis`'s five hard-fails (`theses/service.py:678-704`); without it the thesis cannot
reach `active` at all.

**Target `40.000000`.** `+14.416476%` from `34.960000`, over 18 months, is an implied CAGR of
**`9.40%`**. `rule_implied_growth` (`rules.py:354`) raises a material finding above `30%`, so
this passes with a wide margin — deliberately. A target set at the 52-week high `42.950000`
would imply `~15.9%` CAGR, still passing, but it would be an assertion that the de-rating fully
reverses inside the horizon, which nothing in the evidence pack supports.

**Timeline `18` months.** Long enough that the target does not require a re-rating inside one
reporting cycle; short enough that `rule_thesis_age` (`rules.py:401`, monitor at 14 days to
`revisit_due_at`) forces revisits well inside it. Shortening it to 6 months would nearly triple
the implied CAGR toward the `30%` bar without changing a single fact about the business.

**Conviction `2` of 5.** Driven by the three NULL fields above, not by the price. I can see what
WBC.AU costs and I cannot see what it earns on equity or how it is geared. On the C1 paper book
(`25,000.000000` AUD, 100% cash), a 10% position is `2,500.000000` AUD ≈ `71` shares at
`34.960000`, leaving post-trade cash at `90%` — clearing the D1 floor of `7.5%` with room. A
conviction of 4–5 would be a claim the evidence cannot carry.

## 4. What would change these numbers

- `roe` and `debt_to_equity` becoming non-NULL: could move conviction in either direction, and
  is the single highest-value missing input.
- A close below `33.680000` (the 52-week low) before entry: the band's lower bound is then
  inside a falling range and should be re-cut, not held.
- `franking_pct`: at a 4.57% yield, franking materially changes the after-tax return and none of
  the tax reasoning above is complete without it.
