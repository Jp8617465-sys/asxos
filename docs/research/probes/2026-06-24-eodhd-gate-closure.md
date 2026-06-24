# EODHD gate-closure probe — 2026-06-24 (read-only)

**Purpose:** close the three open questions blocking the research-store build
(`reportDate` PIT semantics, franking coverage/semantics, `sync_security_master`
source-closure). **Read-only:** only HTTP `GET`s; no DB writes; `EODHD_API_KEY` read
from the `asxos-sync-prices` Render service in-process and never printed. Raw API JSON
saved to the session scratchpad (`probe_raw_fundamentals.json`, `probe_raw_div.json`,
`probe_franking_supplementary.json`, `probe_summary.json`).

**Current date at probe:** 2026-06-24. **This file is the reproducible evidence** that
`evidence-log.md` rows point to (replacing the earlier transcript-only basis).

---

## A. `reportDate` historical semantics — `/fundamentals/{sym}` → `Earnings.History[]`

Per symbol: count of history entries carrying a `reportDate`, how many are in the past
(`≤ 2026-06-24`) vs future, and the realised lag (reportDate − period_end, days) on past
entries. Also `filing_date` on recent yearly balance sheets.

| Symbol | hist w/ reportDate | past | future | past lag days (min/median/max) |
|---|---|---|---|---|
| CBA.AU | 37 | 36 | 1 | 33 / 41 / 60 |
| BHP.AU | 82 | 81 | 1 | **0 / 0 / 83** |
| WTC.AU | 28 | 27 | 1 | 34 / 54 / 92 |
| GMG.AU | 22 | 21 | 1 | 42 / 45 / 54 |
| TPW.AU | 28 | 27 | 1 | 26 / 55 / 64 |

**Findings:**
1. **Exactly one future entry per symbol** — the scheduled upcoming FY2026 result
   (e.g. CBA period 2026-06-30 → reportDate 2026-08-11; BHP → 2026-08-17; WTC → 2026-08-26).
   The guard `reportDate ≤ as_of` drops precisely these forecast rows. **Leakage closed.**
2. **Historical `reportDate`s are genuine disclosure dates** (weeks after period end) for
   CBA/WTC/GMG/TPW — median lag 41–55 days.
3. **`reportDate` is NOT uniformly reliable.** BHP's median lag is **0** — many BHP entries
   have `reportDate = period_end` (defaulted, no real lag), the same failure mode as
   `filing_date`. So `reportDate` cannot be trusted blindly.
4. **`filing_date` is also inconsistent.** BHP 2022/2023 yearly had real filing lags
   (period 2022-06-30 → filing 2022-09-06) but 2024/2025 defaulted to period_end; CBA/WTC
   `filing_date` always = period_end. The two fields are **complementary**, each defaulting
   on different periods.

**→ Decision (B1 resolved): UNBLOCK `sync_financial_statements` with a GUARDED anchor**, not
a single preferred field:

```
knowledge_date(period_end, reportDate, filing_date, as_of):
    cands = [d for d in (reportDate, filing_date) if d and period_end < d <= as_of]
    return max(cands) if cands else period_end + LAG_DAYS
```
- `d <= as_of` drops scheduled/future dates → closes the leakage risk.
- `period_end < d` drops the "defaulted to period_end" rows so the lag isn't understated.
- Fallback `period_end + LAG_DAYS` when both fields defaulted. Observed real lags:
  annual ~57–68d (BHP), quarterly ~33–55d. Use a **conservative LAG_DAYS (≥75 calendar
  days for annual, ≥60 for quarterly)**; document the constant; refine later from data.

## B. Franking — `/div/{sym}`

`franking` is present on every dividend object (keys: `date, value, unadjustedValue,
currency, declarationDate, recordDate, paymentDate, period, franking`).

| Symbol | n div | distinct `franking` | nulls |
|---|---|---|---|
| CBA.AU | 67 | `100%` | 0 |
| GMG.AU | 48 | `0%` (unfranked property trust) | 0 |
| QBE.AU | 77 | `10/12/15/20/25/30/35/40/50/60/100%`, **`25.03%`, `14.81%`** | 1 (2026-03-05, most recent) |
| SUN.AU | 77 | `0/100%` | 1 (1997, sparse history) |
| TLS.AU | 57 | `0/49/100%`, **`90.47%`** | 2 (1999, 2003) |
| WBC.AU | 66 | `0/100%` | 1 (2026-05-08, most recent) |
| FMG.AU | 31 | `0/100%` | 1 (2026-03-02, most recent) |

**Findings (B3 resolved):**
- Format is a **string `"<float>%"`** — includes decimals (`25.03%`, `90.47%`), so the parse
  is `float(s.rstrip('%'))`, NOT int. Range 0–100 → fits `NUMERIC(18,6)`.
- **Partial franking is common and real** (not just 0/100).
- **Nulls are rare and meaningful:** they cluster on the *most recent* dividend (franking not
  yet declared) or sparse pre-2003 history. **Store NULL, not 0** — `0%` = explicitly
  unfranked; `NULL` = unknown. The distinction is tax-material.
- Coverage is deep (QBE to 1988; 76/77 non-null).

**Parse rule for `rs_corporate_actions.franking_pct`:**
`NULL if franking in (None,'') else Decimal(franking.rstrip('%'))`.

## C. `sync_security_master` source-closure — `exchange-symbol-list/AU`

- Active list: **2,382** rows. Delisted (`?delisted=1`): **1,986** rows.
- Delisted row keys: `Code, Country, Currency, Exchange, Isin, Name, Type` —
  **NO delisted-date field** (`candidate_delisted_date_fields: []`). → **`delisted_date = NULL`
  v1 fallback is necessary and confirmed**; a delisted date would need per-symbol calls.
- **`Type` taxonomy enumerated** (key off these real strings, not guesses):
  - active: `Common Stock 1877, ETF 471, Preferred Stock 18, FUND 13, Notes 3`
  - delisted: `Common Stock 1828, ETF 120, Preferred Stock 16, FUND 10, Notes 6, BOND 6`
  - union: **`{Common Stock, ETF, Preferred Stock, FUND, Notes, BOND}`** (note: it's
    `Preferred Stock`, not `PREFERRED`).
- **0 duplicate `Code`s** across active + delisted → `_to_symbol` PK-collision risk is
  empirically nil on the full lists.

**→ All §6 source-closure questions CLOSED. `sync_security_master` is unconditionally
approved as the next build** (delisted symbols ingested with `delisted_date = NULL`).

---

## Net gate status after this probe

| Blocker | Before | After |
|---|---|---|
| B1 `reportDate` PIT leakage | hard-blocked | **resolved — unblock with guarded anchor (drop `d > as_of`; require `d > period_end`; else `period_end + lag`)** |
| B3 franking coverage/semantics | unproven (1 sample) | **resolved — `"<float>%"` string, partials common, NULL≠0%, deep coverage** |
| security-master source-closure | open (delisted-date field, Type set) | **resolved — no delisted-date field (use NULL); Type set enumerated; 0 collisions** |
| B4 index-membership history | unavailable | **unchanged — still unavailable; v1 = labeled proxy universe** |
| B2 schema populated-data validation | open | unchanged — validate during `sync_security_master` (its acceptance criteria) |
