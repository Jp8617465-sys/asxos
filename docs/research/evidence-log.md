# Research-store source-probe evidence log

**Purpose:** one auditable record of what was *actually observed* from each data-source
probe, so status claims in the research-store docs can be traced to evidence rather than
to optimism. Every row is labeled **verified** (observed directly), **inferred** (one
observation generalised), or **unresolved** (probed but not settled / a hazard found).

**Provenance.** The gating questions were re-probed read-only on **2026-06-24** and the
raw API JSON saved. The reproducible evidence is **`docs/research/probes/2026-06-24-eodhd-gate-closure.md`**
(raw dumps in the session scratchpad). Rows below are promoted to *verified* where that
probe backs them. Earlier-session rows not re-probed stay labeled by their original basis.

**Key never printed.** All EODHD probes read `EODHD_API_KEY` via an authorized Render
env-var read; the key value was never echoed. All probes were read-only `GET`s.

---

## Probe runs

| # | Probe date | Current date at probe | Endpoint | Symbols | Periods/dates tested | Fields observed | Sample count | Null / missing behavior | Caveats | Label |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-22/24 | same | `exchange-symbol-list/AU` | all AU | current listing | `Code, Name, Type, Currency, Isin, Sector` | full list | n/a | — | **verified** (active list present) |
| 2 | 2026-06-24 | 2026-06-24 | `exchange-symbol-list/AU` (+`?delisted=1`) | all AU | current | row keys, `Type` | active **2,382** / delisted **1,986** | delisted payload has **NO date field** | `Type` set = {Common Stock, ETF, Preferred Stock, FUND, Notes, BOND}; 0 dup Codes | **verified** (set + no delisted-date field → use NULL) |
| 3 | 2026-06-24 | 2026-06-24 | `/div/{CBA,GMG,QBE,SUN,TLS,WBC,FMG}.AU` | 7 names | full history (to 1988) | `franking` + 8 other keys | **>400 dividends** | NULL on recent-undeclared / sparse pre-2003; else present | string `"<float>%"` (incl. `25.03%`,`90.47%`); partials common; store NULL≠0% | **verified** |
| 4 | 2026-06-24 | 2026-06-24 | `/fundamentals/{CBA,BHP,WTC,GMG,TPW}.AU` → `Earnings.History[]` | 5 names | full history | `reportDate`, period `date`, `filing_date` | **197 history entries** | exactly 1 future (scheduled) entry/symbol; BHP defaults many to period_end | guarded anchor needed: drop `d>as_of`, require `d>period_end`, else `period_end+lag` | **verified (guard defined)** |
| 5 | 2026-06-24 | 2026-06-24 | `/fundamentals/{5 names}` → financial statements | 5 names | yearly | `filing_date` present | inspected | **inconsistent**: real lag on some periods (BHP 2022/23 ~Sept), defaults to period_end on others | complementary to `reportDate`; neither alone is reliable | **verified** (filing_date alone insufficient; used inside the guarded anchor) |
| 6 | 2026-06-24 | 2026-06-24 | `AXJO.INDX` | AXJO.INDX | current | `Components` | **199** names | n/a | **current snapshot only**; no historical reconstitutions | **verified** (current) / **unresolved** (history unavailable) |
| 7 | prior session | — | `/fundamentals/*` (Financials, Highlights, outstandingShares) | sampled AU | up to 35yr | BS/IS/CF yearly 35yr, ROE/margins/revenue in Highlights (current snapshot), shares 36yr | sampled | quality/growth columns **NULL in our DB today** (ingestion gap, not source gap) | Highlights ratios are a single current snapshot — not PIT | **verified** (depth available) |

`INCOMPLETE` columns above reflect data not captured in the transcript — re-probe to fill.

---

## The gating finding — now RESOLVED (row 4, probe 2026-06-24)

**Was:** a future/scheduled `reportDate` (CBA period 2026-06-30 → reportDate 2026-08-11)
is a genuine look-ahead leakage risk. **Now:** the historical-period probe confirms the
hazard is **one scheduled entry per symbol** (the upcoming FY result), cleanly removed by
the guard `reportDate ≤ as_of`. Historical `reportDate`s are real disclosure dates
(median lag 41–55 days) — **except** they sometimes default to `period_end` (BHP), as does
`filing_date` on other periods.

**Resolution — guarded PIT anchor (closes B1; `sync_financial_statements` UNBLOCKED):**
```
knowledge_date = max(d for d in (reportDate, filing_date) if d and period_end < d <= as_of)
                 else  period_end + LAG_DAYS   # ≥75d annual / ≥60d quarterly, conservative
```
`d <= as_of` drops forecasts; `period_end < d` drops defaulted rows; fallback covers the
both-defaulted case. Full detail: `probes/2026-06-24-eodhd-gate-closure.md` §A.

---

## Promotion checklist

- [x] Franking (row 3): probed 7 names incl. unfranked (GMG 0%) + partials (QBE/TLS) +
      nulls. Format `"<float>%"`; parse `Decimal(s.rstrip('%'))`; store NULL≠0%. **verified.**
- [x] reportDate (row 4): historical probe of 5 names; guard + fallback defined. **verified.**
- [x] Delisted-date field (row 2): `?delisted=1` payload has **no** date field → accept
      `delisted_date = NULL` v1 fallback. **verified / accepted-fallback.**
- [x] security_type taxonomy: `{Common Stock, ETF, Preferred Stock, FUND, Notes, BOND}`.
- [ ] Index history (row 6): **still open** — obtain a true historical-membership source, or
      **label** the v1 universe a cap-rank / broad-tradable **proxy** — never "historical ASX 200".
- [ ] B2 schema populated-data validation: exercised during `sync_security_master` (its
      acceptance criteria), not yet done.

---

## Related docs

- `research-store-schema.md` — authoritative status of each source.
- `build-readiness-audit.md` — the read-only audit this log supports (§13 open questions).
- `sync-security-master-scope.md` — the first ingestion job (acceptance criteria + gate).
