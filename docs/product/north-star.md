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

- A position James holds is backed by his **own conviction and discipline** (a structured
  thesis: entry/stop/target/timeline/invalidation) — **not** a Model A signal. The P0 "does
  the ML edge persist over the weeks-to-months horizon?" question is **answered (2026-07-11):
  it does not** (`model-a-decay-analysis-2026-07-11.md` — no usable edge on 19,032 matured
  signals), so James **shelved** the ML engine and the product is now explicitly the
  model-independent moat. The success criterion became: the discipline/tax/theme product is
  faithful to James's thinking and surfaces the right thing before it costs money.
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

1. **Model A is quarantined** (CLAUDE.md rule #11, **now STANDING — resolved 2026-07-11**).
   Do NOT recommend acting on Model A output — signals, candidate scans, allocator runs, new
   thesis proposals — as a basis for **real capital**. No longer "pending": the decay analysis
   (`docs/model-a-decay-analysis-2026-07-11.md`) confirmed on 19,032 matured signals that v1_5
   has no usable edge (conviction inverted at 21d). The P0 is **resolved against Model A**; the
   quarantine holds until a new version passes a decay bar. **Scope (verified 2026-07-10, arbi
   multi-agent scan):** this gates exactly ONE live capital path — the allocator in
   `PortfolioService.build()` (`portfolio/build.py`) → `allocator.py` — plus one peripheral
   surface (`compute_opportunity_cost` ranking). It does **not** gate the thesis/discipline
   scaffolding, the tax engine, theme stewardship, or governance; those read no Model A
   signal and are authoritative today. The quarantine is narrow, not "the whole product."
2. **Personal-advice firewall** (s766B Corporations Act / Westpac v ASIC). The system is
   single-user **decision-support**: it surfaces evidence, verdicts, and allocation memos
   James reads and acts on. The firewall is **execution, not analysis** — it **never** places
   an order, moves capital, or represents itself as licensed advice; James executes every
   trade in his own broker. arbi allocates **on paper** (the Portfolio ladder P0–P6,
   `portfolio-manager-charter.md`); James acts **in reality**. In its separate infrastructure
   capacity arbi steers *what gets built* and does not trade at all.
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

The 2026-07-04 handoff was explicit: *"we've been building for 6 months and still aren't at
a point where we can use this to start building toward financial freedom."* That P0 question —
does the engine work? — is now **answered (2026-07-11)**: the decay analysis showed Model A
has **no usable edge**, so James **shelved** it. Infrastructure maturity never substituted
for that answer; getting the answer is what unblocked the product. arbi still does not
cheerlead feature velocity — it now holds James to the *model-independent* moat (discipline,
tax, themes, ETFs) being genuinely faithful and shippable, not to a signal engine that isn't.

**The resolved frame (2026-07-11; supersedes the earlier "narrow quarantine" correction of
2026-07-10, scan `wf_f54323f5-d7d`):** the product was never "nothing works until Model A."
The large, defensible slice — discipline scaffolding (moat layer 2), theme stewardship
(layer 3), the tax engine, governance — is **authoritative and shippable today**, because a
thesis is James's own conviction, not a Model A output. The decay analysis then showed the
signal engine itself has no edge, so it is **shelved** (not merely quarantined): the
signal-driven allocator + opportunity-cost ranking stay **dormant by standing policy**
(rule #11), and there is no "resolve Model A to let that path out" any more — the path out is
the model-independent product. The revival door is a *new* model past a pre-registered decay
bar (`ml-engine-shelf-2026-07-11.md`), not v1_5.
