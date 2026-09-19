# Plan — closing the loop: from brief, to decision, to brokerage instruction

**Status:** SUPERSEDED 2026-09-19 by `plan-2026-09-19-mandate-sleeves-paper-book.md` — James ruled the same day that sleeves pick *and* size on paper and that capital/structure derive from a mandate layer; Phase 1's verbs and Phase 2's staged order survive inside the new plan (sections D and A4). Retained as the dated diagnosis.
**Author:** arbi
**Date:** 2026-09-18
**Evidence base:** `capability-atlas-2026-09-18.md` (same session, all claims re-verified live)
**Supersedes:** nothing. The ranked queue in `roadmap-state.md` remains the live queue;
this plan proposes what should sit at the top of it.

---

## Context — why this plan exists

James asked for everything the platform can do to be run, tested and documented, and then
for a plan to iterate on the brief and build brokerage instructions.

Running it produced an uncomfortable and useful result. **The software is not the problem.**
4,725 tests pass. Thirty jobs run themselves nightly without intervention. The data spine
holds 806k prices and 700k financial statements, fresh to yesterday. The valuation engine
values 1,879 ASX names a week. The morning brief composed nine sections this morning and
correctly raised **four red discipline flags** on a A$7,749 portfolio.

And nothing happened, because **nothing can happen.** James can reply to the brief from his
phone — that channel is built and running (`jobs/apply_github_decisions.py`) — but its entire
vocabulary is three words:

```
APPROVE thesis <id> <reason>
REJECT  thesis <id> <reason>
DISPOSE <packet_id> <verdict> [note]
```
— `asxos/domain/governance/github_commands.py:51`

Those are **governance** verbs. They answer "should this candidate enter the system?"
**None of them answers a discipline event.** There is no `HOLD`, no `EXIT`, no `REVISE`,
no `SNOOZE`. So when the brief says *"HUBS.NYSE: STOP VIOLATED (current 229.58, stop 230)"*
and *"review overdue by 46d"*, there is literally no verb James can type back.

That is the whole diagnosis, and it is small:

> **asxos produces exactly the right evidence and gives James nothing to answer it with.**

The moat this product was built on is layer 2, discipline — *"the system forces a deliberate
revisit when an assumption changes"* (`north-star.md` §1.3). Today the system *observes* and
does not *force*. The plan below closes that gap first, then builds the brokerage-instruction
layer on top of it, because an instruction with no decision behind it is just a stock tip.

---

## What the audit found that this plan must fix

| ID | Finding | Severity |
|---|---|---|
| **D-1** | Regime classifier's credit-stress arm is dead — `_HY_OAS_STRESS = 600` bps vs ingested `2.70` percent. Both legs unfireable; tests encode bps so CI is green. | HIGH |
| **D-2** | Roughly a third of the discovery engine's 35-name passing set are LIC/LIT (at least 8) or A-REIT-shaped (4) NTA vehicles. The residual-income model rediscovers discount-to-NTA and calls it value. | HIGH |
| **D-3** | `tax_settings` has 0 rows. The entire tax engine is built, tested and cannot produce a number. | MEDIUM |
| **D-4** | `position_monitor_runs` has 0 rows, ever. Dead code carrying a live promise. | MEDIUM |
| **D-6** | **The active profile's constraints are mutually unsatisfiable.** `baseline`: `per_name_cap_pct = 10%` of A$7,749 = **A$775**, but `min_position_aud = A$1,000`. No position can be legal. `capital_aud` is also stale (A$6,666.98 vs A$7,749.54 actual). | HIGH |

D-5 (`check_cron_health` red) is incident #327, already tracked and deliberately not re-taken
before Saturday's `weekly-research` fire.

---

## Phase 0 — Make the readings true (before anything is built on them)

Nothing in Phases 1–4 is worth building on a regime label that cannot see credit, a candidate
list dominated by closed-end funds, a tax engine with no rates, or a profile whose caps
contradict each other.

| # | Work | Class | Acceptance criterion |
|---|---|---|---|
| **P0-1** | Fix the HY OAS unit mismatch. Normalise at the ingest boundary (store bps) **or** convert at the classifier; pick one, state it once, and assert the scale in a test that reads a real stored value rather than a fixture. | Amber (investment output) | A stored `us_hy_oas` and the classifier thresholds are on the same scale, proven by a test that would fail under the current code. `regime_rationale` shows a credit leg that *could* fire. |
| **P0-2** | Add `universe.security_kind` (`au_equity \| us_equity \| index \| etf \| lic \| reit \| hybrid`) and backfill. Exclude NTA vehicles from the residual-income funnel, or route them to an NTA-appropriate lens. | Amber (migration + investment output) | The 35-name passing set is re-derived and contains no LIC/LIT. The excluded set is explainable name-by-name. Retires `m14_candidate_security_kind_enum` and the "reject seven on sight" workaround. |
| **P0-3** | Populate `tax_settings` with James's real marginal rate, account type and any ECPI fraction. **James supplies the numbers; arbi wires and verifies.** | Amber | `asx tax-view` returns a real AUD figure for the HUBS lot, and `asx tax-action` states the 2027-06-01 CGT boundary. |
| **P0-4** | Repair the active profile: set `capital_aud` from the latest snapshot (or derive it), and reconcile `per_name_cap_pct` against `min_position_aud` so the pair is satisfiable at current capital. | Amber | A written rule that makes the two consistent at any capital level, with a test at A$7,749 and at A$250,000. |
| **P0-5** | Delete `asx position monitor` **or** wire it. Do not leave it. | Green | Either the command is gone and the nightly jobs are named as the monitor, or `position_monitor_runs` is non-empty. |

---

## Phase 1 — Close the discipline loop (the one that matters)

This is the plan's centre of gravity. Everything else is downstream of it.

### P1-1 — Give the discipline events verbs

Extend the GitHub decision channel from three governance verbs to a vocabulary that can
answer every flag the brief can raise. Each verb writes a `thesis_revisions` row — so every
reply becomes an audited discipline event, which is exactly what the append-only revision log
was built for.

```
HOLD   <SYMBOL> <reason>                 # deliberate "reviewed, no change" — resets revisit clock
EXIT   <SYMBOL> <reason>                 # closes the thesis; triggers the CGT/redeploy view
REVISE <SYMBOL> <field> <value> <reason> # stop / target / timeline / conviction
SNOOZE <SYMBOL> <days> <reason>          # explicit deferral, capped, and it ages louder
```

**Design constraints, non-negotiable:**
- Every verb writes a revision row. A reply is never silent.
- `SNOOZE` is bounded and is itself a discipline event — it defers, it does not dismiss.
- No verb places, sizes or drafts an order. This phase moves *records*, not money.
- Reuse `apply_github_decisions.py`'s existing safety model unchanged: owner-login-only,
  one marker reply per command, re-run is a no-op, GitHub failure never fails the pipeline.
- `EXIT` records the intent; the actual sale is James in his broker (§2).

**Acceptance:** James replies `HOLD HUBS reviewed, thesis intact, stop was wrong` from his
phone and the next morning's brief no longer shows `revisit_overdue` for HUBS, with a
`thesis_revisions` row carrying his reason.

### P1-2 — Make the brief lead with what it wants

Today the brief is a set of nine sections that happen to contain four red flags. Invert it.

- **Open with the ask.** A single block at the top: *"You owe 4 decisions"*, each one line,
  each with the exact verb to reply with.
- **Age it.** A flag that is 46 days old must render **louder** than one raised this morning,
  not identical to it. Today's brief renders a 46-day-overdue review and a same-day stop
  violation with the same weight. Silence must become progressively more expensive.
- **Say what it costs.** Each flag carries the consequence in dollars where one is computable
  (concentration against the 10% cap; CGT state; FX exposure).
- **Keep the brief dumb.** `north-star.md` and the 2026-08-10 reframe: the brief is an
  experience layer over an immutable decision and carries no financial logic. The ageing and
  the ask are rendering; the flags stay in the discipline engine.

**Acceptance:** the top of the brief names the number of outstanding decisions and the exact
reply text for each; a flag's visual weight is a function of its age.

### P1-3 — Set conviction

`conviction_unset on 1/1 theses` disables the size-vs-conviction check entirely. One field,
one command, unblocks a whole class of coherence checking.

---

## Phase 2 — Brokerage instructions

**Only after Phase 1.** An instruction is the output of a decision; without P1-1 there is no
decision to be the output of.

### What this is, exactly

A **brokerage instruction** is a human-executable ticket that James reads on his phone,
retypes into his broker, and that asxos records as an *intent* — never an execution.

New module `asxos/brokerage/`. **Deliberately not `asxos/capital/`**, which stays empty as the
charter's marker for the execution boundary (`AGENTS.md` §2 item 2). The firewall is
structural: nothing in `asxos/brokerage/` may hold a credential, open a network connection to
a broker, or be callable from a scheduled job without a preceding recorded decision.

### What a ticket contains

| Field | Source |
|---|---|
| Symbol, side, quantity | the decision that produced it |
| Order type + limit band | last close + a stated rule, never a model target |
| Which thesis it serves | `theses.thesis_id`, and the revision that authorised it |
| Consequence: concentration | position vs `per_name_cap_pct` before and after |
| Consequence: CGT | discount-eligible date, estimated tax at the configured rate (needs P0-3) |
| Consequence: FX | for offshore names, the AUD/USD assumption, stated |
| What would make this wrong | the invalidation condition, carried from the thesis |
| Expiry | tickets go stale; an unexecuted ticket expires and says so |

### What it must never do

- No broker API. No credential. No `asxos/capital/`.
- No ticket without a `thesis_revisions` row authorising it.
- No ticket sourced from Model A output (rule #11), and none sourced from the
  residual-income model's value as a *price* — `RESPONSE_RULE` (#306) stripped target prices
  and entry bands from that model and this plan does not reinstate them by the back door.
- Class: **Amber**. It is investment output with a real-world effect on read.

**Acceptance:** James receives one ticket for a real decision he made via P1-1, retypes it
into his broker, and `asx journal` + `thesis_revisions` record the intent, the fill and the
variance between them.

---

## Phase 3 — Portfolio shape, without the allocator

The allocator is gated off and **stays** gated off — rule #11 is standing policy and this plan
does not touch it. But James's question — *how does it build me a portfolio?* — still has a
model-independent answer, and D-6 shows the existing framework is currently incoherent.

Build a **shape check**, not an optimiser: the live portfolio measured against James's own
stated profile. Concentration vs `per_name_cap_pct`. Sector exposure vs `sector_cap_pct`.
Cash vs `cash_floor_pct`. FX exposure. Theme coverage. It reports *distance from your own
rules* and never proposes a weight vector.

Today that check would read: **one position, 100% of capital, against a 10% self-imposed cap,
zero cash, 100% unhedged USD, one theme covered.** That is a portfolio construction answer,
and it needs no signal engine at all.

**Acceptance:** a brief section stating, per rule, the profile's target, the live value, and
the gap — with no allocation, no weights, and no model input.

---

## Phase 4 — Learn

- **Complete one outcome episode.** `decision_engine/outcomes.py` + migration 0052 capture t0
  and schedule 21/63/126 sessions. No episode has finished. One completed episode is worth
  more than another capability.
- **Re-score the macro theses against their falsifiers.** Three approved theses, all written
  2026-07-21/22, none re-scored in 58 days — in a product whose stated job is *"monitor a
  thesis and change it when the world changes."* The breadth thesis's own falsifier has
  moved (25.9% → 27.9%) and nobody has ruled on it.
- **Then, and only then**, revisit whether the discovery funnel earns a second lens (#331's
  peer-relative phase (a)).

---

## Sequencing

```
P0-1 ─┐
P0-2 ─┤
P0-4 ─┼─► P1-1 ─► P1-2 ─► P2 (brokerage instructions) ─► P4
P0-3 ─┘         └► P1-3 ─► P3 (shape check)
P0-5 ─ (independent, any time)
```

P0 items are independent of each other and can land in any order or in parallel. **P1-1 is
the gate**: nothing in P2 is meaningful before it.

## The first action

**P1-1 — the discipline verbs.** It is the smallest change that converts four correct
observations into four answerable questions, it reuses a channel that is already running in
production every night, and it is Green-to-Amber rather than structural. If only one thing in
this plan gets built, it should be this one.

## What stays James's (`AGENTS.md` §2)

- **Every real order.** Phase 2 produces a ticket he retypes; asxos never places anything.
- **The P0-3 tax inputs** — his marginal rate and account settings are his to supply.
- **The four live decisions** on the board right now: HUBS (stop violated, review 46d
  overdue, 100% concentration) and CBA (detached ladder, 113d). arbi can draft the options
  and the evidence for each; the call is his.
- **`.claude/**` and `north-star.md`** — unchanged, per §2 and §14.
