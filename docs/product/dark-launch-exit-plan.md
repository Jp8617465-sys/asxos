# Dark-launch exit plan — ship, delete, or keep-dark-with-an-expiry

**Status:** current
**Scope:** every code-complete-but-gated-off surface in asxos. For each one: a **ship / delete /
keep-dark** decision, the reason, an **expiry** if kept dark, and the exact gate that flips it.
Closes risk R4 (built-but-dark ≠ released) by refusing to let a surface sit dark with no decision.
**Last verified:** 2026-07-11 (post ML-shelf; the model-independent product is now THE product)
**Owner:** arbi maintains the decisions + expiries (I2, command-invoked); James owns any decision
that flips a real-capital or firewall gate (those are `james-inbox.md` items).
**Superseded by:** N/A

A dark launch is a promise to decide later. "Later" without a date is how dead code accretes. Every
surface below carries one of three verdicts — **SHIP** (flip the gate on a named condition),
**DELETE** (remove the code; it doesn't serve the moat), or **KEEP-DARK** (justified, with an
expiry date at which arbi re-raises it). No fourth "leave it and forget" state exists.

---

## Surfaces

### 1. Portfolio brief — `ASXOS_PORTFOLIO_BRIEF_ENABLED=0`

- **Verdict: KEEP-DARK · expiry 2026-08-31.**
- **Why:** The M13 allocator brief section is model-independent in its non-signal cards (tax,
  discipline, thesis, regulatory) but the *allocator* path it fronts is dormant policy
  (rule #11 standing; `approved_for_allocation=0`). Shipping the section as-is would front an
  allocator that is deliberately not allowed to run. The valuable model-independent cards already
  reach James through the main brief, so there's no user-facing loss in keeping this off.
- **Gate to ship:** `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` **and** `ASXOS_PERSONAL_USE=1` — but only
  after 4 weeks of paper-trade sign-off (M13.8) **and** the section is re-scoped to display the
  discipline/tax cards *without* implying an allocator recommendation. Until the allocator has a
  revival path (a new model past the decay bar), ship the model-independent cards or nothing.
- **Owner of the flip:** James (firewall gate 1 + capital-adjacent) — a `james-inbox.md` item when
  the paper-trade window closes.

### 2. News / sentiment brief — `ASXOS_NEWS_BRIEF_ENABLED=0`

- **Verdict: SHIP · on the freshness+coverage condition below.**
- **Why:** News/sentiment (`asxos/ingestion/{news,sentiment}.py`, M14a/b) is fully
  model-independent — it feeds the market-context and discipline narrative, not a signal. It
  directly serves the "know the backdrop before it costs money" moat layer and has no rule-#11
  exposure. This is exactly the kind of surface the post-shelf product should turn on.
- **Gate to ship:** `ASXOS_NEWS_BRIEF_ENABLED=1`, once (a) the ingestion cron is green and fresh
  (no stale-feed hard-fail), and (b) `market-context-narrator` confirms the section reads as
  context, never as an implied buy/sell. No capital or firewall gate — arbi-actionable.
- **Owner of the flip:** arbi proposes; main loop flips (reversible ops, no capital).

### 3. V2 brief tree

- **Verdict: KEEP-DARK · expiry 2026-09-30.**
- **Why:** The V2 brief tree (`asxos/domain/brief/collectors/*`, `brief_v2.html.j2`) was designed
  around a *trusted signal engine* that no longer exists (ML shelved). Its model-independent
  collectors (`active_theses`, discipline, tax) are the keepers; the signal-driven framing is
  stale. Deleting now would throw away the reusable model-independent collectors; shipping now
  would ship the stale signal framing. So: keep dark, and use the window to **descope it to the
  model-independent collectors** and retire the "V2 needs a trusted signal engine" framing
  (`ml-engine-shelf-2026-07-11.md` next-action #4).
- **Gate to ship:** the proposed single master gate `ASXOS_V2_BRIEF_ENABLED` (not yet plumbed),
  flipped only after the tree is re-scoped model-independent and its collectors are the same ones
  proven in the live brief. Partial-ship allowed here (collector by collector), unlike the
  portfolio section.
- **Owner of the flip:** arbi drives the re-scope; James flips if any card is capital-adjacent.

### 4. Paper-trade evaluator

- **Verdict: KEEP-DARK · expiry tied to surface #1, re-raise 2026-08-31.**
- **Why:** The paper-trade evaluator (`asxos/domain/portfolio/paper_trade.py`) exists to *earn* the
  4-week sign-off that gates surface #1 — it is the instrument that produces the evidence to ship
  the portfolio brief, so it is correctly dark until that evaluation is actually being run.
  Deleting it would remove the only mechanism that can retire surface #1's KEEP-DARK. It stays,
  unshipped, as scaffolding with a job to do.
- **Gate to ship:** not a user-facing gate — this is an internal evaluator. "Ship" here means
  **start the 4-week paper-trade run** (record its results to feed the M13.8 sign-off), not expose
  output to James. Begins when James decides to open the portfolio-brief evaluation window.
- **Owner of the flip:** James starts the window (it commits to a capital-adjacent evaluation);
  arbi runs and records once started.

---

## Summary

| Surface | Verdict | Gate | Expiry / condition | Flip owner |
|---|---|---|---|---|
| Portfolio brief | KEEP-DARK | `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` + `ASXOS_PERSONAL_USE=1` | 2026-08-31 · re-scope to model-independent cards + 4wk sign-off | James |
| News/sentiment brief | **SHIP** | `ASXOS_NEWS_BRIEF_ENABLED=1` | cron green + reads as context | arbi/main loop |
| V2 brief tree | KEEP-DARK | `ASXOS_V2_BRIEF_ENABLED` (unplumbed) | 2026-09-30 · descope to model-independent collectors | arbi / James |
| Paper-trade evaluator | KEEP-DARK | start the 4wk run (internal) | 2026-08-31 · re-raise with surface #1 | James |

## How arbi uses it

- **Every wake, check no dark surface is past its expiry.** An expired KEEP-DARK is a re-raise: the
  surface must earn a fresh SHIP / DELETE / KEEP-DARK verdict, not silently roll over.
- **Never count a dark-launched surface as delivered** in the scorecard or the brief's "recently
  completed" (risk R4). Built is not released; the ledger is honest about the difference.
- **A SHIP verdict that only arbi can flip, arbi flips** (reversible, non-capital). A SHIP/START
  that crosses a firewall or capital gate becomes a `james-inbox.md` row.
