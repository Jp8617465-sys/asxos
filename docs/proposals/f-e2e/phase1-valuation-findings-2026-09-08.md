# F-VAL/r0 Phase 1 — residual income on the Australian majors

**Method:** residual income on tangible common equity. ROE fades linearly to Ke
over 10 years; **terminal value = book, no perpetual excess return**. Pre-registration
sealed before any model run: `a6912403cd2505fe179e63097e57377a1d2b368c53208d88b9ea3516d45165d0`
(commit `1d05c70`), bear/base/bull at 0.70/1.00/1.20 × each name's own ROTCE, 25/50/25.

## Cost of equity — a stated band, not a measurement

| | |
|---|---|
| risk-free | `0.048310`, as_of 2026-09-08 — FRED `IRLTLT01AUM156N`, the OECD **monthly** long-term yield carried forward. **Not** a daily 10-year ACGB quote. |
| ERP | `0.055`, cited |
| beta | **0.55–0.85, third-party five-year estimates** (Finbox, Simply Wall St, Yahoo Finance), reviewed 2026-09-08. **Cited, not measured** — `AXJO.INDX` holds 71 usable return pairs against a 250-session floor, so beta blocks as a measurement (backlog E-19). |
| **Ke band** | **low `0.078560` · mid `0.086810` · high `0.095060`** |

## The four majors, at knowledge cutoff 2026-09-04

| sym | period | TBVPS | close | P/TBV | ROTCE (avg TCE) |
|---|---|---|---|---|---|
| CBA | 2026-06-30 | 41.928913 | 160.42 | 3.826 | 0.154256 |
| NAB | 2025-09-30 | 18.295019 | 39.25 | 2.145 | 0.119069 |
| ANZ | 2025-09-30 | 20.555049 | 37.95 | 1.846 | 0.090834 |
| WBC | 2025-09-30 | 16.883740 | 34.96 | 2.071 | 0.112121 |

Probability-weighted value at Ke mid, both conventions:

| sym | close | franking-adjusted (primary) | ÷ price | unadjusted | ÷ price |
|---|---|---|---|---|---|
| CBA | 160.42 | 63.54 | 0.396 | 51.65 | 0.322 |
| NAB | 39.25 | 24.66 | 0.628 | 20.21 | 0.515 |
| ANZ | 37.95 | 23.95 | 0.631 | 20.68 | 0.545 |
| WBC | 34.96 | 22.27 | 0.637 | 18.23 | 0.521 |

Franking is adjusted for an **Australian resident holder** — the reason is investor
residency, not the result. Both conventions are published side by side because the
adjustment is worth roughly a fifth of value and rests on an **assumption** input
(`franking_pct`), not a measured one.

## What was varied, and what was not

Beta was swept to zero. **No name crosses market price at any beta**, including
`beta = 0.00` (Ke = risk-free, an economically impossible equity discount), where WBC
reaches 0.709 of price and CBA 0.443.

Across the **plausible** band (0.85 → 0.55) WBC moves 0.623 → 0.651 of price — **2.8
percentage points** — and CBA 1.8. Beta is not the lever.

**This is insensitivity to one input, not robustness of the conclusion.** The input
identified as dominant — the terminal-value convention — was **not varied**. A model
that cannot be moved by an impossible discount rate is being determined somewhere
else, and that somewhere is `terminal value = book`, which prices a four-firm
oligopoly earning ROE above any plausible Ke for three decades as making zero
economic profit in perpetuity. That may still be the right conservative convention to
publish. It is an assumption with a very large coefficient and it is currently the
only input in the model that has not been tested.

## The calibration metric is not yet a calibration metric

"Share of research-queue names valued above market" currently reads **0 of 4**.

**This number cannot be interpreted until a second terminal-value convention exists.**
0-of-4 is equally consistent with the market being wrong and with the method being
harsh, and nothing in Phase 1 separates those two readings. The ADR-review threshold
(near zero after 20 names) should not be actioned on a single-convention series.
This limitation travels with the metric wherever it is reported.

## Standing pre-commitment

If the method values a name below market, **no horizon extension, no growth term and
no terminal excess return will be added to close the gap**. A method revision is an
ADR decision on queue-wide evidence, never on one name. Phase 2 adds a second
convention **universe-wide and alongside** `zero_excess`, never instead of it, with
both persisted and compared — which is what the 0054 discriminator is for.

## Integrity notes carried on every run

- `preferredStockTotalEquity` and `minorityInterest` are **NULL for all four majors**, so
  the "common" in tangible common equity is a stated convention, not a verified one.
- **NAB**: `intangibleAssets` (3,552) **exceeds** `goodWill` (2,070), so the disjointness
  assumed by `TSE − goodwill − intangibles` is unsafe for that name specifically.
- **CBA** carries `currency_null` on its FY26 row — one instance of backlog **C-20**
  (70,393 rows, 10.07%, 1,091 symbols; current through period_end 2026-06-30).
- **ANZ**'s `franking_avg_pct` is **70**, not 100, which is why its franking uplift is
  visibly smaller than its peers'.
- The vendor `rs_fundamentals_pit.roe` field is **net income / period-end equity** on all
  four, confirmed by reconciliation. The model uses net income / **average** tangible
  common equity, recorded as a derived figure with its formula.
