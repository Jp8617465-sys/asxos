# Agent roster — what it offers that nothing asks for

**Status:** current · a survey, nothing enacted
**Scope:** every agent in `.claude/agents/` and command in `.claude/commands/` — which are reachable,
which are blocked, which are idle, and what the idle ones could answer today
**Owner:** arbi. Produced 2026-09-17 at James's instruction — *"need to explore what else they have
to offer"* — alongside the register rework
**Method:** repo files only, no database. Every claim carries a `path:line`. Where a capability is
blocked, the block is named rather than the capability being talked up.

---

## The headline

The roster is 24 agents. **Ten are invoked by no command and no skill**, reachable only if arbi
happens to remember them. And the thinnest moat layer has two fully-unblocked agents that have
**never been run once** — not because they are broken, but because the commands that drive them
have never been invoked.

That is the gap worth James's attention: not missing capability, **unrealised** capability.

---

## 1. Reachability

Invocation is by arbi's contextual judgement (`.claude/agents/README.md:102-108`), so "no call
site" means "only fires if arbi remembers".

**Ten agents have no command or skill call site:** `thesis-coherence-guard`,
`tax-spec-conformance`, `portfolio-invariant-guard`, `backend-architect`, `system-architect`,
`requirements-analyst`, `deep-research-agent`, `tech-stack-researcher`, `learning-guide`,
`frontend-architect` (the last dormant by design — no v1 UI, `README.md:74-75`).

Two have **never appeared in the decision log at all**: `tech-stack-researcher` and
`learning-guide`. `refactoring-expert` and `technical-writer` are reachable only through a skill
(`pr-readiness/SKILL.md:31`), never a command.

**Commands that have never fired.** `/harden` writes to `docs/harden/$ARGUMENTS.md`
(`harden.md:3-4`) and **`docs/harden/` does not exist**. `/discover-sector` and `/discover-theme`
appear nowhere outside their own build records. `/pm-review` has run **twice in fourteen months**
(2026-07-04 and 2026-08-22).

---

## 2. What is genuinely blocked, and by what

**`benchmark-performance-analyst` is hard-blocked, by a ruling and not a defect.** Its own step 1
stops if `portfolio_daily_snapshots.benchmark_tr_level` is empty
(`benchmark-performance-analyst.md:33-38`). The series needs `AXJOA.INDX`
(`jobs/snapshot_portfolio.py:71`), which is absent from `prices` — asserted in five separate
places including `asxos/domain/benchmark/outcome.py:31`. Backlog **E-15** is open and James's, and
governor ruling **F1** forbids a proxy. Four of its five sections are dead; only the per-symbol
disposal return runs, and its comparand is the same missing series.

**Its own file is stale and over-promises.** `benchmark-performance-analyst.md:3` claims
*"AXJO.INDX ingestion is wired (Stage 1); benchmark columns populate once snapshot_portfolio
runs"*. `AXJO.INDX` is the **price** index; the accumulation series is a different symbol. Anyone
reading the agent definition would think this works. **Filed as a doc-truth fix.**

**Two capabilities were amputated on purpose,** both by PR #144 freezing `signals`:
`thesis-coherence-guard`'s SHAP steps and `portfolio-coherence-reviewer`'s signal-alignment
section. Restoration needs a *new* model past a pre-registered decay bar, not merely a writer
reappearing. `CLAUDE.md:285-287` is explicit that no sanctioned route to SHAP evidence exists.

**Two checks are degenerate at the current book size, not blocked.** The live book is 1 open lot
and 1 active thesis, so `portfolio-coherence-reviewer`'s conviction-vs-weight and sector-cap checks
have no cross-section to compare against. Cash drag and stop proximity still bite.

**Not blocked, and worth stating because it is easy to assume otherwise:** `market_context_current`,
`regulatory_events` and `signal_sentiment` all have live daily writers in `daily-brief.yml`, and
`fundamentals` is written weekly. So `market-context-narrator`, `macro-economist`,
`sector-screener`, `theme-researcher` and `thesis-milestone-monitor` are all fully unblocked.

---

## 3. Declared but unbuilt

| Named where | What | State |
|---|---|---|
| `README.md:226-227` | `instrument-selector` | no file — would be the first real use of `theme_holdings.source='llm_inferred'` |
| `roadmap-state.md:1108` | the `/pm-review` 5→7 expansion | **the two extra agents are never named anywhere** — a phantom item |
| capability matrix gap **G9** | an **independent challenger** | no file, yet `ChallengeResult.independent_of_author: Literal[True]` is contract-enforced. A contract-required role with nothing to fill it |
| `CLAUDE.md:321` | `/dashboard-component` | **no file in `.claude/commands/`** — doc rot |

---

## 4. Coverage by moat layer (`north-star.md:76-86`)

- **Layer 1, integration with thought-process.** Served by commands rather than agents. `/thesis`
  is the richest finance command in the repo and fans out **zero** agents.
- **Layer 2, discipline scaffolding.** Densest *and* most hobbled: of four agents, one is blocked
  on E-15, one is unreachable, one is degenerate at one position. And `jobs/check_au_positions.py`
  already emails stop-breach and target-hit daily, so the agents' genuinely unique contribution is
  the **pace math** (progress vs linear expectation, implied annualised required rate) and the
  **cadence math** — which no job computes.
- **Layer 3, theme stewardship — the thinnest.** Against 2,377 actively tracked instruments
  (1,872 equities, 471 ETFs, 21 hybrids, 13 LICs) the register holds 13 theses, 1 theme and
  2 theme-holdings, with **zero ETF, LIC or hybrid coverage** — which is the gap James named
  directly: *"the etf's etc [need to be] included in our investment plan not just individual
  equities."* Two built, unblocked agents address exactly this and have never run.

**Uncovered entirely:** the independent challenger (G9); a `TaxAssessmentReference` producer (G7);
and there is **no finance skill of any kind** (G1) — `.claude/skills/` holds process skills only.

---

## 5. Ranked — the highest-value idle capability

1. **`theme-researcher` against approved macro theses #6/#7.** Its only stop condition — an empty
   approved macro set — was cleared on 2026-07-21. It closes the macro→theme rung of the declared
   macro→theme→instrument hierarchy, and the rung below it does not exist. Zero proposals is a
   valid, expected outcome by its own spec, so it can be run cheaply with an honest chance of a
   null.
2. **`sector-screener` on the ETF/LIC/hybrid blind spot.** Fully unblocked for the *coverage*
   half. **Honest limit:** its steps 1 and 4 filter `security_kind = 'au_equity'`, so screening
   non-equities needs a fund taxonomy it does not carry today. The coverage snapshot works now;
   the screen does not.
3. **`thesis-coherence-guard` on HUBS.** Model-independent after amputation, reads only `theses`
   and `thesis_revisions`. The repo already records what it would return: HUBS has a violated stop
   and an EXIT-CANDIDATE verdict with **no revision logged** — an UNEXAMINED verdict by its own
   rubric. A working capability sitting next to the exact question it was built for, removed from
   the one command that used to call it.
4. **Point `/thesis` at the three agents it currently re-derives inline.** It instructs the main
   loop to compute trajectory with `trajectory.py`'s math, read revision recency, and read
   benchmark-relative return — which are `thesis-milestone-monitor`,
   `thesis-coherence-guard` and `benchmark-performance-analyst` respectively. The unused capability
   is not a new agent; it is three existing ones as a deterministic pre-pass. It would inherit
   "unavailable" for the benchmark leg, which is the correct output.
5. **`market-context-narrator` outside `/pm-review`.** Cheapest to start using, fully unblocked,
   and it already refuses to invent a backdrop when data is missing — the abstention behaviour the
   decision engine wants.

**Deliberately last: `benchmark-performance-analyst`.** Its central question — is this portfolio
generating alpha, or would an index fund have done better — is the most important one the roster
exists to answer, and it is unanswerable today **by ruling, not defect**. Recommending "use it
more" would be inventing a use. It becomes the most valuable agent in the roster the day E-15
closes.

---

## 6. Overlap worth one sweep

Three implementations of "near the stop" exist: `thesis-milestone-monitor`'s verdicts,
`portfolio-coherence-reviewer`'s proximity check, and `jobs/check_au_positions.py` — which is the
one that actually runs daily. `market-context-narrator` and `macro-economist` share two queries
differing only in a 7-day vs 30-day window. Six of thirty command files are deprecated or classed
REJECT for reading the frozen `signals` table, and all six are still loadable.

`theme-researcher` and `sector-screener` overlap by design (top-down vs bottom-up siblings) and
should **not** be consolidated.

---

## What this survey does not do

It enacts nothing, invokes no agent, and proposes no capital action. The filed follow-ups are in
`docs/product/backlog.yaml`; the two doc-truth defects it found — the stale
`benchmark-performance-analyst` description and the missing `/dashboard-component` — are under
`.claude/`, so they are drafted for James rather than landed.
