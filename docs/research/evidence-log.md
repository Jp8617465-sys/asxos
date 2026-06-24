# Research-store source-probe evidence log

**Purpose:** one auditable record of what was *actually observed* from each data-source
probe, so status claims in the research-store docs can be traced to evidence rather than
to optimism. Every row is labeled **verified** (observed directly), **inferred** (one
observation generalised), or **unresolved** (probed but not settled / a hazard found).

**⚠ Provenance & incompleteness.** This log is **reconstructed from the session
transcript**, not from a persisted probe artifact. The raw probe JSON was **not** saved
to the scratchpad. Where a value could not be confirmed from the transcript it is marked
`INCOMPLETE` rather than invented. A finding labeled *inferred* or *unresolved* must be
re-probed (read-only) and promoted to *verified* — with the raw output saved here — before
any ingestion code relies on it. Do not upgrade a row's label without a fresh probe.

**Key never printed.** All EODHD probes read `EODHD_API_KEY` via an authorized Render
env-var read; the key value was never echoed. All probes were read-only `GET`s.

---

## Probe runs

| # | Probe date | Current date at probe | Endpoint | Symbols | Periods/dates tested | Fields observed | Sample count | Null / missing behavior | Caveats | Label |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-22/24 | same | `exchange-symbol-list/AU` | all AU | current listing | `Code, Name, Type, Currency, Isin, Sector` | full list | n/a | — | **verified** (active list present) |
| 2 | 2026-06-22/24 | same | `exchange-symbol-list/AU?delisted=1` | all delisted AU | current | symbol list | **1,986** symbols | per-symbol `delisted_date` field name **not confirmed** | survivorship set exists; delisted-date granularity open | **verified** (set) / **unresolved** (delisted-date field) |
| 3 | 2026-06-24 | 2026-06-24 | `/div/CBA.AU` | CBA.AU | recent dividends | `franking` present | **1 dividend object** | unfranked/partial/null behavior **not observed** | value was the **string** `"100%"`, not numeric; one symbol only | **inferred** (field exists; coverage/semantics unproven) |
| 4 | 2026-06-24 | 2026-06-24 | `/fundamentals/CBA.AU` → `Earnings.History[0]` | CBA.AU | period `2026-06-30` | `reportDate=2026-08-11, date=2026-06-30, epsActual/Estimate…` | 1 (most-recent) entry | historical entries **not examined** | **both dates FUTURE vs probe date** → scheduled/forecast, not a disclosure lag | **unresolved (HAZARD)** |
| 5 | 2026-06-24 | 2026-06-24 | `/fundamentals/CBA.AU` → financial statements | CBA.AU | yearly/quarterly | `filing_date` present | inspected | `filing_date` **defaults to period_end** in the cases seen | one symbol; not generalised across the universe | **inferred** (filing_date ≈ period_end, not a real lag) |
| 6 | 2026-06-24 | 2026-06-24 | `AXJO.INDX` | AXJO.INDX | current | `Components` | **199** names | n/a | **current snapshot only**; no historical reconstitutions | **verified** (current) / **unresolved** (history unavailable) |
| 7 | prior session | — | `/fundamentals/*` (Financials, Highlights, outstandingShares) | sampled AU | up to 35yr | BS/IS/CF yearly 35yr, ROE/margins/revenue in Highlights (current snapshot), shares 36yr | sampled | quality/growth columns **NULL in our DB today** (ingestion gap, not source gap) | Highlights ratios are a single current snapshot — not PIT | **verified** (depth available) |

`INCOMPLETE` columns above reflect data not captured in the transcript — re-probe to fill.

---

## The one finding that gates the build (row 4)

**Classification: API returned an expected/scheduled FUTURE report date → genuine
point-in-time leakage risk.** Not a typo, not a stale copied sample. CBA's FY ends
2026-06-30 (which had **not occurred** on the 2026-06-24 probe date); its result is
*scheduled* for ~2026-08-11. `Earnings.History` therefore mixes **forward-scheduled**
earnings dates with historical disclosures. Using `reportDate` as `knowledge_date`
without a guard would let the research store "know" an announcement before it happens.

**Required before `sync_financial_statements`:** a fresh read-only probe of **historical**
`Earnings.History` entries (several past periods, several symbols) confirming
(a) past `reportDate ≤ today` and ≈ actual disclosure, (b) restatement behavior,
(c) same-day-availability cases, (d) how forecast/future entries are flagged. Ingestion
must hard-filter `report_date <= as_of/test_date` and fall back to `period_end + lag`
when `reportDate` is future or missing. **PIT statement ingestion is BLOCKED** until then.

---

## Promotion checklist (to move a row to *verified*)

- [ ] Franking (row 3): probe ≥1 large, ≥1 mid, ≥1 small-cap, ≥1 unfranked, ≥1
      partially-franked name; record the `franking` type/format and null/absent behavior;
      define the string→`NUMERIC(18,6)` parse. Then *verified*.
- [ ] reportDate (row 4): historical-period probe per above; define the future-date guard
      and fallback. Then *verified* (or *use filing_date+lag* if reportDate proves unsafe).
- [ ] Delisted-date field (row 2): confirm the field name in the `?delisted=1` payload, or
      accept the `delisted_date = NULL` v1 fallback. Then *verified* / *accepted-fallback*.
- [ ] security_type taxonomy: enumerate the exact `Type` values EODHD emits for AU.
- [ ] Index history (row 6): obtain a true historical-membership source, or **label** the
      v1 universe a cap-rank / broad-tradable **proxy** — never "historical ASX 200".

---

## Related docs

- `research-store-schema.md` — authoritative status of each source.
- `build-readiness-audit.md` — the read-only audit this log supports (§13 open questions).
- `sync-security-master-scope.md` — the first ingestion job (acceptance criteria + gate).
