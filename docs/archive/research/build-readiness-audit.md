# ASXOS build-readiness & evidence audit (read-only)

**Date:** 2026-06-22 · **Mode:** read-only audit. **No code changed, no ingestion written, no model replaced.**
**Adopts the review's discipline:** every claim labelled **VERIFIED** (checked in code/data this session) · **INFERRED** (logical, not directly proven) · **SPECULATIVE** (plausible, unproven) · **MISSING** (cannot determine yet). Language is *quarantine, not retire; candidate, not verdict.*

---

## 1. Executive summary

The architecture diagnosis holds: ASXOS fuses **prediction + construction + decision** into one 5-day ML signal. The fix is to separate the layers (research data store → alpha → portfolio → PM/thesis → monitor). But on the evidence, the correct *operational* stance is narrower than "retire and pivot":

- **Quarantine the 5-day ML signal from production selection** (keep it as a measured, paper-only sleeve) — it is weak, not robust, and concentrated in untradable names, but **not disproven** and not to be deleted.
- **Long-horizon value/quality/momentum/low-vol are research candidates**, not approved replacements. They fit the mandate; none is yet tested on ASX.
- **The binding constraint is data.** EODHD *can* supply a real research store (verified below), but the current store is ~1 month deep with quality/growth columns empty. **Map the gap and design the schema before writing any ingestion code.**

## 2. Build / no-build decision: **REVISE FIRST**

Architecture direction is right; inputs are incomplete. Approved *now* (all read-only or additive, no production replacement): research-store **schema proposal**, continued paper monitoring, the diagnostics already built. **Frozen:** new models/features, SHAP, ingestion code, any composite replacement, any live/daily-trading framing, deleting the 5d signal, crowning value×quality.

## 3. Evidence table

| # | Claim | Evidence | Type | Sev | What would settle it | Action |
|---|---|---|---|---|---|---|
| 1 | 5d signal has useful ranking power | rank-IC ~0.095 (adj_close recon), t~1.8; ~2 independent episodes | **VERIFIED-but-underpowered** | High | ≥50 independent dates (signal backfill) | Quarantine; keep measuring |
| 2 | Signal decays by 21d | 5d 0.095 → 10d 0.034 → 21d **−0.060** | **VERIFIED (computed)** | High | More dates | Don't hold ML picks weeks |
| 3 | Portfolio horizon-mismatched | label = 5 trading days (`train.py` FORWARD_RETURN_DAYS=5); profile horizon 10yr, weekly rebalance | **INFERRED (strong)** | High | — (two verified facts) | Separate horizons |
| 4 | `expected_return` uncalibrated | units bug: bp (`train.py:156`) vs fraction (`thresholds.py:27`); range −23.6..+323.9 | **VERIFIED** | Critical | — | Quarantine from scoring |
| 5 | `expected_return` non-predictive | rank-IC 0.05/0.003/−0.04 (5/10/21d) | **VERIFIED (computed)** | High | — | Quarantine; don't delete |
| 6 | prob_up ≥ composite | composite IC ≤ prob IC every horizon (marginal) | **VERIFIED-but-underpowered** | Med | More dates | Prefer prob_up if ML used |
| 7 | Edge concentrated in illiquid names | illiquid IC 0.097 vs tradable 0.065 (t=0.94 ns) | **VERIFIED (computed)** | High | — | Mandatory liquidity filter |
| 8 | Data store insufficient for factor research | fundamentals 1mo, 30 as_of; roe/de/revenue/net_income 0% | **VERIFIED** | Critical | — | Build research store |
| 9 | EODHD supplies the missing data | Financials 35yr; ROE/margins/revenue in Highlights; delisted list (1,986); divs; splits; shares 36yr | **VERIFIED (probed)** — except index membership | High | Probe index membership | See data-gap table |
| 10 | Value×quality is the right first sleeve | mandate fit + academic prior only | **SPECULATIVE** | Med | OOS ASX test after backfill | Research, don't crown |
| 11 | PM/thesis layer underdeveloped | rich `theses` schema + `cli/thesis.py` + `thesis_revisions` exist; **2 rows** | **REFUTED (code) / true (usage)** | Med | — | Populate + add conviction/tax fields |

## 4. Data-foundation gap (read-only; EODHD availability **probed**)

| Category | Stored now | EODHD available? (verified) | PIT-safe path | Priority |
|---|---|---|---|---|
| Adjusted EOD prices | ✓ (`adj_close`, ~1.5yr) | ✓ deeper | yes | have |
| Volume / liquidity | ✓ | ✓ | yes | have |
| Corporate actions (splits/divs) | ✗ | ✓ (`/splits`, `/div`) | yes | **high** |
| Delisted securities (survivorship) | ✗ | ✓ (`exchange-symbol-list?delisted=1` → 1,986) | yes | **high** |
| Security master (PIT listing/delist dates) | partial (universe current-only, `is_active` not PIT) | ✓ | needs build | **high** |
| Market-cap history | ✗ (latest-only) | reconstruct: shares×price | yes | med |
| Shares-outstanding history | ✗ | ✓ (`outstandingShares.annual`, 36yr) | yes | med |
| **PIT fundamentals / ratios** | ✗ (1mo; roe/de/rev/ni NULL) | **statements ✓ 35yr; ratios = current snapshot only** | **must compute from statements lagged to filing date** | **critical** |
| Historical financial statements | ✗ | ✓ (BS/IS/CF yearly 35yr, quarterly ~125) | yes | **critical** |
| Sector/industry history | sector (current) | ✓ (current); history unclear | likely current-only | med |
| Benchmark/index membership history | ✗ | **MISSING / unverified in this API** | — | med (needed for survivorship + benchmark) |
| Dividends + franking | `dividend_yield` partial | divs ✓; franking field **available in probe (1 sample, "100%" string) — coverage/semantics validation required** | yes | med (AU tax edge) |
| Analyst estimates / target | ✗ | `WallStreetTargetPrice` ✓ (current); detailed ratings sparse for AU | snapshot-only | low |

**The critical nuance:** EODHD's `Highlights` ratios (ROE, PE) are a *single current snapshot*. True point-in-time factors must be **computed from the 35-year historical statements, lagged to the disclosure/filing date** — not ingested from Highlights. That is the real design of the backfill, and it's where look-ahead risk lives.

## 5. 5-day ML signal — quarantine assessment

**Conclusion: evidence of a weak, paper-only signal — quarantine from production selection.** (Not "no signal"; not "tradable".)
- IC by horizon, decile spread, liquidity split, calibration: all computed this session (see `alpha-signal-verification.md`). Headline: 5d IC ~0.095, decays/reverses by 21d, top decile no edge, vanishes in tradable universe, ~2 independent episodes → **no statistical power**.
- Permitted future roles (all to be *proven*, not assumed): paper-only sleeve · timing overlay · shortlist input · liquidity-filtered short-horizon sleeve · monitoring. **Not** the long-book selector.
- prob_up-only ≥ composite (marginal) → if the ML sleeve is used at all, prefer `prob_up` and quarantine `expected_return`.

## 6. `expected_return` diagnostic

**VERIFIED non-predictive + mis-scaled** (units bp-vs-fraction; rank-IC ≈0; range −23.6..+323.9). Recommendation, in order of preference: **quarantine from portfolio construction now** (research variant) → **then** decide rename/recalibrate/retrain. **Do not delete** — keep it computable so the `alpha_eval` engine can keep testing whether a fixed/recalibrated version ever adds rank value. (ml-conventions marks thresholds locked — any change needs explicit sign-off.)

## 7. PM / thesis workflow audit

**Built, not adopted.** The `theses` table already supports: thesis text, entry band, stop, target, `timeline_days`, `invalidation_conditions`, themes, actual entry/exit, `revisit_due_at`/`last_revisited_at` (review cadence), analyst buy/neutral/sell + consensus target, `next_earnings_date`, `earnings_notes`. There's a `cli/thesis.py` and an append-only `thesis_revisions` log. **Missing fields:** explicit `conviction_level` and `tax_notes` (CGT/franking). **Smallest useful step:** add those two fields, and *use it* (populate theses for current holdings) — no waiting on the data backfill. This is the one layer that delivers long-horizon value **today**.

## 8. Revised architecture

Unchanged in shape from `operating-model-architecture.md` (research store → alpha → portfolio → PM → monitor), with the corrected stance baked in: the ML signal is **one candidate sleeve that must earn capital through evidence**, value×quality is **a research candidate**, and PM/thesis is **populated, not built**. The one shift: flip the arrow — fundamentals + factors + theses drive the long book; the ML signal is paper-only until proven.

## 9. Implementation sequence (smallest safe)

1. **Read-only EODHD / data-gap report** — ✅ done (§4, this doc).
2. **Research-store schema proposal** — design only, no ingestion code. ← *next*
3. **5d signal quarantine report** — ✅ done (§5 + `alpha-signal-verification.md`).
4. **`expected_return` diagnostic** — ✅ done (§6).
5. **PM/thesis: add `conviction_level` + `tax_notes`, populate** — small, parallelizable, high-value today.
6. **`alpha_eval` hardening** — add a factor-panel loader so it can compare composite / prob_up / expected_return / factor candidates once data lands.
7. **First candidate sleeve research (value×quality)** — **deferred** until the PIT fundamentals backfill exists.

**Gate:** no ingestion code until the schema proposal is reviewed; no composite replacement until `alpha_eval` can compare the variants on real, sufficient data.

## 10. Files inspected (this session)
`asxos/domain/models/train.py`, `thresholds.py`, `model_a.py`, `feature_engine.py`, `signals/loader.py`, `jobs/generate_signals.py`, `jobs/retrain_model_a.py`, `jobs/snapshot_portfolio.py`, `domain/portfolio/*` (build, allocator, types, paper_trade), `cli/thesis.py`+`theme.py` (present), `api/main.py`, `config.py`, `pyproject.toml`, migrations.

## 11. Probes / commands run
Render env-var read (authorized, key never printed) → EODHD read-only probes (`/fundamentals`, `/div`, `/splits`, `exchange-symbol-list?delisted=1`); Supabase read-only SQL (IC by horizon, decile, liquidity split, calibration, fundamentals coverage/nullity, theses/themes counts + schema). No writes.

## 12. Checks run
`alpha_eval` engine: 9/9 pure tests pass; monitor 16/16; `paper_trade` 21/21; ruff clean on new files. (3.11 sandbox; `make check` is the 3.12 CI gate.)

## 13. Open questions (MISSING/UNRESOLVED — to verify before building)

> **Update (gate-closure probe 2026-06-24, after this audit's 2026-06-22 date):** #2 and #3
> are now **RESOLVED**; #1 remains the one open gap. Authoritative status:
> `evidence-log.md` + `probes/2026-06-24-eodhd-gate-closure.md`.

1. **Index-membership history** (ASX200/300) — still **unavailable** from EODHD (`AXJO.INDX` is current-only, 199 names). Needed for survivorship + benchmark. v1 must use a **labeled proxy universe**, never "historical ASX 200". **The one remaining open gap.**
2. ~~Franking~~ — **RESOLVED 2026-06-24** (7 names, >400 divs): `franking` is a string `"<float>%"` (partials common, incl. `25.03%`/`90.47%`), rare NULLs on undeclared/sparse → **store NULL≠0%**; parse `Decimal(s.rstrip('%'))`. `sync_corporate_actions` unblocked.
3. ~~Statement disclosure date~~ — **RESOLVED 2026-06-24**: the future date is one scheduled entry/symbol, dropped by `d ≤ as_of`; both `reportDate` and `filing_date` default to period_end on some periods, so use a **guarded `knowledge_date`** = `max(d for d in (reportDate,filing_date) if period_end < d ≤ as_of) else period_end + lag`. `sync_financial_statements` **unblocked**.
4. **Backfill cost/rate** — ~1,885 symbols × historical fundamentals = many API calls; confirm plan limits (probe showed 100k/day, so feasible, but confirm).
5. **Is the 21d reversal real or sample noise?** Only the signal backfill resolves it.
6. **Schema populated-data validation** — `0027` is applied but all `rs_*` tables are **empty**; constraints, idempotent UPSERTs, identity keys, and sample inserts are unexercised. Validate on real rows before declaring any table done.

---

### Final recommendation: **REVISE FIRST**
The architecture is right; the next move is the **research-store schema proposal** (design, reviewable, no ingestion) plus the small **PM/thesis field additions** — both safe and parallel. Do **not** write ingestion, replace the composite, or deploy capital until the schema is agreed and `alpha_eval` can compare candidates on sufficient data. The 5-day signal stays **quarantined, measured, and alive** — not retired, not trusted.
