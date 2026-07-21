# Macro→theme→instrument automation — the discovery loop through the research agents

**Status:** proposed (arbi draft — James-requested 2026-07-21)
**Scope:** sequencing the *identify* half of the macro-thesis lifecycle into an automated,
governance-gated loop run by the discovery/research agents (macro-economist → theme-researcher →
instrument-selector / sector-screener). **Advisory + human-gated at every write** — no direct
agent DB writes, no capital action, no allocator, no Model A. Ever.
**Last verified:** 2026-07-21 (live: `macro_theses` = 2 approved #6/#7; `themes` = 1;
`theme_holdings` = 1; `agent_runs` unacted = 2; the 6 discovery/analysis agents' frontmatter
still points at the dead `mcp__Supabase__execute_sql` — reproduced as a live failure this session)
**Owner:** arbi draft → `system-architect` (the loop as a system) + `backend-architect` (the
shared service functions) → James scope sign-off before build
**Depends on:** `docs/proposals/thesis-coverage-framework-2026-07-11.md` (the tier framework this
operationalises), `docs/proposals/sector-screener-agent-spec-2026-07-12.md`,
`docs/proposals/agent-db-readonly-role-design-2026-07-11.md`,
`docs/proposals/governance-first-architecture-2026-06-30.md` §4.2 (the proposal schemas)
**Superseded by:** N/A

Triggered by James (2026-07-21): "we need to get to a state where the workflow automates this with
our portfolio management and investment research agents." Written the same session macro theses
#6/#7 were approved — which for the first time gives the *next* agent in the chain
(`theme-researcher`) real, approved input to read.

---

## 1. The workflow James is describing already has a designed shape

The discovery hierarchy is **macro → theme → instrument**, and it exists on paper end to end:

| Rung | Agent | Reads | Proposes | Status |
|---|---|---|---|---|
| Macro | `macro-economist` | `market_context_current` | `macro_theses` | **built + live** (produced #3/#4/#6/#7) |
| Theme | `theme-researcher` | `governed_active_macro_theses` | `themes` + `theme_holdings` | **not built** (Phase 2c) |
| Instrument | `instrument-selector` | approved `themes` | `theme_holdings` | **not built** (Phase 2c) |
| (Sibling) | `sector-screener` | `universe`/`fundamentals` by sector | `themes` + `theme_holdings` | **spec'd, not built** (`sector-screener-agent-spec-2026-07-12.md`) |

Every rung follows the **identical governance path** — agent proposes a typed, evidence-cited
object → logged to `agent_runs` (never a direct write) → human `open --from-agent-run` → human
`approve`/`reject`. That path is proven: it's exactly what just carried macro theses #6/#7 to
`approved` this session. So "automate the workflow" is **not** an unbuilt vision — it's finishing
a chain whose first rung works and whose pattern is validated. The honest job of this proposal is
to **sequence the finish and name the one thing genuinely blocking it**, not to re-design it.

## 2. The single real blocker — and this session produced live proof of it

Every downstream agent sits next to governed tables. The security gap
(`m14_candidate_agent_db_role_scoping`, risk-register R2) is that agent SELECT-only access is
**prompt-enforced only** — the underlying `mcp__Supabase__execute_sql` grant can write. The fix
was landed at the infrastructure layer: migration 0039 created `asxos_agent_ro`, and the
`supabase-ro` MCP is live (connects as `supabase_read_only_user`). **The remaining step is
mechanical:** repoint the 6 discovery/analysis agents' frontmatter
(`.claude/agents/*.md`) from `mcp__Supabase__execute_sql` → `mcp__supabase-ro__execute_sql`.

**This session turned that from a theoretical backlog item into a reproduced failure:** invoking
`market-context-narrator` as a subagent failed outright because its frontmatter names a tool that
isn't live — the main loop had to stand in and run the queries by hand. **Every discovery agent
in the chain above hits the identical broken frontmatter.** Until it's fixed, the "automated
workflow" cannot run agent-side at all — it degrades to a human hand-executing each rung (exactly
what happened to #6/#7 this session, and why those two are held for provenance review). The
frontmatter repoint is therefore **precondition zero** for any of this — and it's an afternoon's
work, not a project.

## 3. The build sequence (each step reversible, each gated)

**Step 0 — Repoint the 6 agent frontmatters** (`.claude/agents/*.md` → `mcp__supabase-ro__execute_sql`).
Precondition for everything below; independently correct regardless of this proposal. Verify each
agent can still SELECT and now *cannot* write (the whole point). This subsumes the audit's
"governance triggers are UPDATE-only → direct-INSERT bypass" gap (`session-handoff-2026-07-18.md`).

**Step 1 — Build the shared `_from_agent_run` service functions.** `theme-researcher`,
`instrument-selector`, and `sector-screener` all need
`create_theme_from_agent_run()` / `create_theme_holding_from_agent_run()` — **confirmed not built**
(`themes/service.py` has only the human-path `create_theme()`; coverage-framework §6 item 5). Land
them **once, shared**, modelled on the proven `create_macro_thesis_from_agent_run()` (including its
BEFORE-UPDATE trigger ordering — the INSERT-then-UPDATE lesson in
`.claude/rules/portfolio-conventions.md` that this session re-validated live). Wire the missing
`asx theme approve|reject|open --from-agent-run` CLI verbs at the same time (also confirmed
missing, coverage-framework §6 item 3).

**Step 2 — Ship one agent end-to-end** (recommend `sector-screener` first — it's fully spec'd and
bottom-up/coverage-driven, so it produces value even with only 2 macro theses live; `theme-researcher`
is macro-conditioned and benefits from more approved macro input first). Follow the 6-stage
pre-go-live checklist in its spec. It reads `governed_active_macro_theses` (now non-empty — #6/#7
give it real regime context) and proposes themes for James's review.

**Step 3 — Close the identify→monitor→change loop** by pairing this with the sibling proposal
(`macro-thesis-learning-loop-2026-07-21.md`): approved themes/holdings get the same
falsifier-scoring treatment, so the *research agents* and the *learning loop* compound — the
agents propose, the loop scores whether the proposals held, promoted lessons sharpen the next
proposals.

## 4. What "portfolio management + investment research agents" means honestly

James named two agent families. They map to two **different, already-existing** agent sets, and
the honest distinction matters:

- **Investment *research* agents = the discovery lane** (macro-economist + the unbuilt
  theme-researcher/instrument-selector/sector-screener). These *propose new content*. This
  proposal is about automating **this** lane. On-moat, model-independent, human-gated.
- **Portfolio *management* agents = the `/pm-review` analysis lane** (the 5 read-only agents:
  thesis-coherence, benchmark-performance, thesis-milestone, portfolio-coherence,
  market-context-narrator). These *analyse existing holdings* and already run on demand. Their
  automation is a **scheduling** question (a Routine firing `/pm-review`), not a build — and it's
  already sketched in `portfolio-team-visibility-2026-07-12.md` as a *later, gated* LLM Routine.

**The firewall line stays bright:** neither lane ever places or implies an order (s766B). The
research agents proposing a `theme_holding` is *"this instrument has exposure to this theme"* —
an analytic mapping, not *"buy this."* Turning a proposal into a position remains a human act
through the thesis/discipline layer, never an agent write. Any automation that *sized or staged*
an order is the separate, unbuilt firewall-amendment track (#58, gated on James) — explicitly
**not** in this proposal.

## 5. Out of scope (explicit)

- Any direct agent write to a governed table — always `agent_runs` → human approve, no exceptions.
- Any allocator / capital / order-staging path — this is discovery, not deployment.
- Any Model A / signal input (rule #11 standing).
- Building `theme-researcher`/`instrument-selector` *logic* here — this sequences and unblocks
  them; their agent files follow the `sector-screener` spec's pattern once Step 0/1 land.
- Auto-approval or unattended dispatch of any rung (stays behind the arbi permission ladder).

## 6. Ranked next steps

1. **Step 0 — repoint the 6 agent frontmatters.** Unblocks the entire lane; ~1 session; now
   evidence-backed by a live failure, not a theoretical gap. **Do this first, independent of the
   rest.**
2. **Step 1 — shared `_from_agent_run` functions + `asx theme` governance verbs.** The reusable
   spine all three research agents need.
3. **Step 2 — ship `sector-screener` end-to-end** against its existing spec + 6-stage checklist.
4. **Step 3 — pair with the learning-loop proposal** so identify and monitor compound.

Steps 0–1 are the unglamorous unblock; they're what convert "a human hand-ran the workflow this
session" (#6/#7) into "the agents run it, James reviews." That conversion — not more macro-thesis
volume — is the actual leverage, which is also what `arbi-red-team` argued this session when it
challenged ranking proposal-consumption ahead of fixing the pipe.
