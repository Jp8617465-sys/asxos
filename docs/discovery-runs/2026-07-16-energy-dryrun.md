# Sector-screener dry run — Energy — 2026-07-16

**DRY RUN — output only. No DB writes. Nothing here is approved or logged.**
This is the sector-screener pipeline's first end-to-end exercise, run as the
spec's **stage-3 read-only production dry run** (`sector-screener-agent-spec-2026-07-12.md`
checklist, and the red-team's output-only requirement). It was produced by the
main loop acting as the agent would, over the **read-only** Supabase MCP
(`supabase_read_only_user`) — SELECT only. It is evidence-only and
model-independent (no Model A; rule #11 not engaged). Whether any of this
becomes a real proposal is a later, attended `/discover-sector` +
`asx theme open --from-agent-run` + human-approve decision — never automatic.

## Why Energy

`asx theme coverage` (run read-only this session): Energy has **115 active
au_equity symbols, 0 theme-covered, 0 thesis-covered** — one of four fully
structurally-blind sectors (Energy, Consumer Defensive, Utilities,
Unclassified). Basic Materials is the larger blind spot (779 symbols) but too
broad for a clean first cycle; Energy is coherent and completely uncovered.

## Coverage snapshot (the per-run deliverable)

| Metric | Value |
|---|---|
| Active au_equity symbols in Energy | 115 |
| …with a positive P/E (earnings-bearing) | 16 |
| …pre-revenue / no positive P/E (explorers) | 99 |
| Sector median P/E (positive-PE names) | 16.38 |
| Theme-covered symbols | 0 |
| Thesis-covered symbols | 0 |
| Existing governed themes touching Energy | 0 |

**Read:** 86% of the Energy universe (99/115) is pre-revenue explorers a
fundamentals value-screen cannot rank — a mechanical screen only has purchase
on the 16 earnings-bearing producers. This is itself the honest finding: the
sector isn't "16 stocks," it's a barbell of ~16 cash-generating producers and
a long tail of binary exploration bets, and only the former is screenable here.

## Candidate (1 theme, 2 holdings) — DRAFT, for human review only

A disciplined screen surfaces **one** coherent angle, not five. Zero would have
been a valid outcome; this one clears the "cite a real number" bar.

**Theme: `energy-value-producers`** — established, earnings-bearing energy
producers trading at or below the sector median P/E (16.38) with positive book
value, distinct from the growth-priced majors (STO P/E 21.3, ALD 108.6, NHC
29.5) and the pre-revenue explorer tail. Bottom-up value, not a macro call.

Holding candidates (both **below** median, positive fundamentals, verified
2026-07-16 fundamentals):
- **WHC.AU** (Whitehaven Coal) — P/E **9.82**, P/B 1.12, div 1.29%, mkt cap
  $6.38B. ~40% below sector median P/E; large, liquid, earnings-bearing.
- **KAR.AU** (Karoon Energy) — P/E **6.21**, P/B **0.71**, div 2.47%, mkt cap
  $1.06B. Trades below book and at the lowest P/E of any positive-earner in
  the sector; oil-weighted (a different sub-driver than WHC's coal — noted so a
  human doesn't read them as one bet).

Deliberately **not** proposed: YAL.AU (P/E 16.6 ≈ median — no discount), the
majors (above median), and all 99 explorers (no positive P/E to screen on).

## Structured output (what `/discover-sector Energy` would log)

This is the exact JSON block the live agent emits; `/discover-sector` would
pass it to `asx agent-run log` (theme first, then holdings). **Not logged here.**

```json
{
  "summary": "Energy is 100% uncovered (115 symbols, 0 themes/theses); a fundamentals value-screen surfaces one below-median-P/E producer cluster (WHC, KAR) against a 99-name pre-revenue explorer tail that cannot be screened this way.",
  "sector": "Energy",
  "coverage_snapshot": {"symbol_count": 115, "theme_covered": 0, "thesis_covered": 0},
  "theme_proposals": [
    {
      "theme_code": "energy-value-producers",
      "name": "Energy value producers",
      "description": "Earnings-bearing ASX energy producers trading at or below the sector median P/E (16.38, 2026-07-16) with positive book value — a bottom-up value cluster distinct from the growth-priced majors and the pre-revenue explorer tail.",
      "conviction_band": "low",
      "stage": "early",
      "macro_thesis_id": null,
      "evidence_citation_ids": ["local:0", "local:1", "local:2"]
    }
  ],
  "theme_holding_proposals": [
    {
      "theme_code": "energy-value-producers",
      "symbol": "WHC.AU",
      "exposure_strength": "0.6",
      "direction": "positive",
      "mechanism_text": "P/E 9.82 vs sector median 16.38 (~40% discount), P/B 1.12, dividend 1.29%; large, liquid, earnings-bearing coal producer.",
      "evidence_citation_ids": ["local:1"]
    },
    {
      "theme_code": "energy-value-producers",
      "symbol": "KAR.AU",
      "exposure_strength": "0.5",
      "direction": "positive",
      "mechanism_text": "P/E 6.21 (lowest positive-earner P/E in the sector), P/B 0.71 (below book), dividend 2.47%; oil-weighted — a different sub-driver than WHC.",
      "evidence_citation_ids": ["local:2"]
    }
  ],
  "evidence": [
    {"claim": "Energy sector median P/E is 16.38 across the 16 positive-earning au_equity names (99 of 115 have no positive P/E).", "tier": "verified", "source_type": "db_query", "source_table": "fundamentals", "source_as_of": "2026-07-16", "snapshot_data": {"total_energy": 115, "with_positive_pe": 16, "median_pe": 16.38}},
    {"claim": "WHC.AU P/E 9.82, P/B 1.12, dividend 3.71%->1.29%, market cap 6.38B.", "tier": "verified", "source_type": "db_query", "source_table": "fundamentals", "source_as_of": "2026-07-16", "snapshot_data": {"symbol": "WHC.AU", "pe_ratio": 9.82, "pb_ratio": 1.12, "dividend_yield": 0.0129}},
    {"claim": "KAR.AU P/E 6.21, P/B 0.71, dividend 2.47%, market cap 1.06B.", "tier": "verified", "source_type": "db_query", "source_table": "fundamentals", "source_as_of": "2026-07-16", "snapshot_data": {"symbol": "KAR.AU", "pe_ratio": 6.21, "pb_ratio": 0.71, "dividend_yield": 0.0247}}
  ]
}
```

## What this dry run proves (and doesn't)

**Proves:** the read-only screen path works end-to-end — coverage query →
fundamentals pull → disciplined 0-5 candidate synthesis → well-formed governed
JSON with verified-tier evidence, all over `supabase_read_only_user`, zero
writes. The `--from-agent-run` open path this branch also adds (PR #50) would
turn that JSON into `pending_review` rows on a human's command.

**Doesn't:** validate the *investment* merit of `energy-value-producers`. A low
P/E in coal/oil is often a cyclical-peak-earnings or terminal-value discount,
not a bargain — exactly the judgment a human makes at `asx theme approve`. The
screen surfaces the candidate; it does not endorse it. It also can't see the 99
explorers, so "Energy" is not "covered" even if this theme were approved.

**Firewall:** evidence-only, no trade direction, no sizing, no capital
recommendation (s766B). Governance path unchanged — nothing reaches `approved`
without a human reading this and running the approve verb.
