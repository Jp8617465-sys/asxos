# Broker-Report Thesis — Quality Rubric (Phase B)

**Status:** proposed (ships with the Phase B keystone schema)
**Scope:** the per-section quality bar a broker-report individual-investment thesis must meet, and
which parts the `ThesisProposal` schema enforces mechanically vs which are render/review-layer.
**Companion to:** `asxos/domain/theses/schemas.py` (`ThesisProposal` / `ReportFigure` /
`ReportSection`), the Phase A spec + architecture, and the 2026-07-18 design-hardening workflow.
**Owner:** arbi drafts; the renderer (Phase C) and the drafter agent (Phase E) validate against it.
**Superseded by:** N/A

---

## The one load-bearing invariant

Every capital-relevant number is Decimal-exact and traces to a source — **never an LLM guess or
training-knowledge figure** (north-star.md success criteria; CLAUDE.md #5). The schema makes this
structural, not aspirational:

- A number enters a report **only** as a `ReportFigure` with explicit `provenance`
  (`cited` → needs ≥1 evidence ref · `derived` → needs a shown `formula` · `james_input` → James's
  own number). A bare capital-relevant literal in a section `body` (`$130`, `99%`, `28x`, `1,234`)
  is **rejected** — it must become a figure.
- A rule #11 Model A datapoint is a `monitor_only` figure. The schema bars it from **every basis
  section** (moat, capital-allocation, strategy, valuation, verdict); its intended home is the
  `evidence_ledger` (labelled, non-load-bearing). The structural guarantee is "not in a basis
  section," **not** "evidence_ledger only" — a monitor figure is still accepted in the non-basis
  narrative sections (identity, business, risks, position-plan), so confining it to the ledger is a
  render/review bar (see "What the schema enforces vs. defers").

Honest limit (documented, not hidden): the prose-number guard catches the unambiguous forms
(leading currency $/€/£/¥, `%`, thousands separators, multiples). It is a **partial** guard — bare
digits with a word/symbol unit ("fair value 130 dollars", "4.64 EPS", "trades at 28 times"),
spelled-out numbers, and trailing-cent forms ("130c") still slip, because catching them collides
with legitimate prose (years like FY26 / 2050, "20-year moat", "13 theses"). That residual is the
Phase C render + review backstop, not a schema guarantee. Phase C must **resolve and recompute**
`cited`/`derived` figures from live sources, never merely display self-declared provenance (or it
becomes a laundering surface — the design line that must not be crossed).

## Per-section quality bar (the 10 kinds)

| # | Section kind | Broker-grade bar | Fails the bar |
|---|---|---|---|
| 1 | `identity_classification` | symbol/kind/sector/close(cited+dated)/mkt-cap/themes/style-box; style-box derived from cited fundamentals **or** James-labelled with the justifying fundamental | "a quality growth name" — no growth figure, no price date |
| 2 | `business` | what it does + revenue mix + unit economics; segment figures cited; explains the *money mechanism* | "a leading logistics software company" — label, no mechanism |
| 3 | `moat` | rating {none·narrow·wide} + which of the 5 sources + ~20yr durability judgment + **≥1 cited quantified datapoint** (the sharpest bar) | "wide moat — strong brand" — no source, no datapoint, unfalsifiable |
| 4 | `capital_allocation` | rating {exemplary·standard·poor}, assessed *separately* from moat, across balance-sheet · investment-efficacy · distributions, **each cited**. v1 uses ROE-vs-cited-benchmark (ROIC/WACC ingestion deferred) | "exemplary — shareholder-friendly" — no leverage/return/distribution number |
| 5 | `strategy_catalysts` | catalysts **dated and falsifiable** (macro-economist catalyst/falsifier shape) | "ongoing growth and margin expansion" |
| 6 | `risks_bear` | each material risk written as a **monitorable** invalidation condition (feeds `theses.invalidation_conditions`) | "macro headwinds; valuation is full" — neither monitorable |
| 7 | `valuation` | one of {james_input anchor · derived-from-cited-fundamentals (shown formula) · scenario band}; the judgment input (multiple/growth/discount-rate) is james_input **or** cited, never LLM-emitted; discount = computed from cited price + sourced FV; a **zone**, not a Morningstar "star" | a single fair-value point the model produced from "market sense" |
| 8 | `position_plan` | entry/stop/target/timeline internally consistent **and the target reconciles with §7's valuation** (anti-CBA — the north-star stale-thesis failure) | target $95 while §7 FV tops out $70, unreconciled |
| 9 | `verdict_conviction` | James's conviction (1–5), cited to §§3–8, **model-independent** (no Model A as a reason); directive register only once the firewall amendment is ratified | "conviction 5/5 — Model A STRONG_BUY 0.71" (rule #11 + decay-inverted) |
| 10 | `evidence_ledger` | every capital claim in §§1–9 as a tiered (verified/inferred/speculative), snapshotted evidence row; the optional Model A line under a labelled "monitored, not a basis" heading | a moat rating whose only evidence is `speculative`-tier |

## Note-readiness gate (necessary conditions to advance draft → evidence_complete)

Binary/auditable (from the Phase A spec S1–S8): all 10 sections present · moat & capital-allocation
each carry ≥1 non-speculative cited datapoint · zero uncited capital-relevant numbers · valuation
carries no invented number · ≥1 monitorable invalidation condition · target reconciles with the
valuation band · model-independent (no Model A as a reason) · survives a `/pm-review` pass without an
EXIT-CANDIDATE caused by *internal incoherence*. The sufficient condition is James's own: **would he
deploy real capital and hold for months on the strength of this note alone, model-independent?**

## What the schema enforces vs. defers

- **Schema (Phase B, mechanical):** figure provenance (cited→evidence, derived→formula), prose-only
  bodies, monitor_only barred from basis sections, entry-band order, no duplicate section kinds,
  symbol pattern, conviction range, evidence-citation required.
- **Service layer (Phase D/E):** evidence rows are `tier != 'speculative'` (needs a DB round-trip);
  `create_thesis_from_agent_run` copies `agent_evidence` → `thesis_evidence` (else `approve_object`
  hard-fails); governance-transition statement ORDER live-verified (Phase 2a lesson).
- **Render layer (Phase C):** resolve-and-recompute cited/derived figures from live sources;
  target↔valuation reconciliation; the in-words-number residual; HUBS FX (mixed-currency stored
  levels must fail loudly, never render an inverted "approaching stop").
