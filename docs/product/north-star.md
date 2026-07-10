# asxos North Star — "The Output"

**Status:** current
**Scope:** whole repo — the product charter arbi measures every recommendation against
**Last verified:** 2026-07-10
**Read priority:** read after the newest `session-handoff-*.md`
**Owner:** arbi (`.claude/agents/arbi.md`) reads this every wake; humans amend it rarely
**Superseded by:** N/A

This is the stable constitution. It changes rarely. The *living* state — where we are,
what's blocked, what's next — lives in `roadmap-state.md` beside this file. arbi reads
both: this one to know **what "done" means**, that one to know **where we are against it**.

Sourced from `docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md` Part 1 and
`docs/session-handoff-2026-07-04.md` — not invented. If those move, re-derive this.

---

## The Output (what we are building toward)

James's own words for the goal (handoff, 2026-07-04): a system he can *"use to start
building toward financial freedom."* Not feature count — a tool whose read on a position
is worth acting on with real capital, held for months at a time.

Concretely, from the V2 spec §1.1–1.2, the product is:

> A morning briefing and trade-framework for a serious DIY investor that consolidates
> the work already done across half a dozen tabs into one calm, contextual practice —
> what you own, what you're watching, what your theses are doing, where your themes are
> heading.

The wedge (§1.2) is the emotional centre of the product — **trade theses with discipline
around them.** Every position is a structured thesis: entry band · stop · target ·
timeline · thesis statement · theme attribution · invalidation conditions · path-vs-plan
state · opportunity-cost framing. A small number of opinionated, explainable ideas — not
"BHP went up 2%," not 50 screener matches.

## The three-layer moat (§1.3) — the ranking arbi prioritises against

1. **Integration with thought-process** — the morning ritual that thinks the way James
   would with three more hours. Competitor = his own spreadsheet + browser tabs.
2. **Discipline scaffolding** — most DIY investors fail at *exit discipline*, not
   picking. Every position is a structured thesis; the system forces a deliberate revisit
   when an assumption changes. A pre-commitment device against confirmation bias.
3. **Theme stewardship** — James names themes; the system maintains the stock→theme
   mapping with explainable exposure, surfaces adjacencies, tracks where a theme sits on
   the generalisation curve so he isn't caught at peak retail euphoria.

Combined: **disciplined alpha-seeking that's faithful to James's own thinking.** When
arbi ranks next actions, work that advances a more-defensible layer, or unblocks the
thing gating the layers above it, outranks work that polishes a lower one.

## Success criteria (how we know we hit it)

- A position James holds is backed by a signal whose edge actually persists over the
  **weeks-to-months** horizon the thesis assumes — the open question the handoff pins as
  P0 (see Blockers). Until that's answered, nothing else here is load-bearing.
- The morning brief runs end-to-end, un-dark-launched, and James reads it as *his own
  thinking, sharper* — not a data dump.
- Discipline events (stop breach, revisit-due, invalidation) reach him **before** they
  cost money. (The 2026-07-04 session found the HUBS stop breach had gone unseen for
  three weeks because the alert crons had never been provisioned — exactly the failure
  this criterion exists to prevent.)
- Every capital-relevant number is Decimal-exact and traces to a cited source, never a
  model guess or training-knowledge figure.

## Non-negotiables (the firewall arbi must never cross)

These are load-bearing constraints, not preferences. arbi's recommendations live inside
them; it never proposes work that violates one.

1. **Model A is quarantined** (CLAUDE.md rule #11, temporary). Do NOT recommend acting on
   Model A output — signals, candidate scans, allocator runs, new thesis proposals — as a
   basis for **real capital** until the signal-reliability dispute resolves. This is the
   current P0 (`session-handoff-2026-07-04.md`).
2. **Personal-advice firewall** (s766B Corporations Act / Westpac v ASIC). The system
   surfaces evidence and verdicts; it **never** places an order or gives personal
   financial advice — structural even for a single user. arbi is dev-side program
   management: it steers *what gets built*, never *what to trade*.
3. **Single-user.** No auth, no RLS, no `user_id`. James is user-of-one (Path A). Peers
   are a Path-B v2 maybe, never a v1 assumption.
4. **Decimal-only domain arithmetic** and **NUMERIC(18,6)** on every monetary/statistical
   column. No numpy in tax/portfolio domain modules.
5. **Signals are inputs to thesis construction, never outputs** (§1.6). Auto-trading
   signals are not the product.

## Deliberately out of scope for v1 (§1.6)

Property/wealth aggregation · multi-tenant · brokerage execution (James executes in his
broker) · mobile app (CLI + email is v1; web UI is v2) · real-time anything (daily grain)
· signals-as-the-product.

## The honest frame arbi must hold

The handoff is explicit and arbi privileges it over any rosier roadmap doc: *"we've been
building for 6 months and still aren't at a point where we can use this to start building
toward financial freedom."* Infrastructure maturity does not substitute for answering
whether the engine works. arbi does not cheerlead feature velocity; it keeps the P0
foundation question in front of James until it is resolved one way or the other.
