# Workflow-automation build + governance disposition — 2026-07-22

Attended session (James: "wake up @arbi — then start building the two approved
workflow proposals"). arbi wake → red-team PASS (with riders) → build. This doc
is the on-repo audit record for the **governed DB writes** made this session
(they went through the write-capable Supabase MCP as a governance-faithful
sequence, not the CLI — the sandbox's raw-TCP Postgres is structurally blocked,
asyncpg not importable — so the record lives here, per the 07-21 handoff's
standing rule that such writes are never silent).

Boundaries held: draft-PR ceiling, no merges beyond #66, no capital action,
rule #11 untouched (Model A not engaged — all work is model-independent),
s766B firewall intact. No hand-logged `agent_runs` rows were created (the two
dispositioned rows already existed; the repoint is live so the pipeline is the
path forward).

## 1. agent_runs #6/#7 disposition (James's explicit ruling 2026-07-22)

The CLI path (`asx macro-thesis open --from-agent-run` → `reject`/`approve`) is
unreachable from this sandbox (asyncpg not installed + raw-TCP Postgres blocked
by the proxy). Per James's instruction ("execute via the real CLI path if
reachable, otherwise the documented governance-faithful sequence — full audit
trail either way"), the disposition was executed as a single committing DO block
faithfully replicating `create_macro_thesis_from_agent_run()` +
`reject_object()` / `approve_object()` (guards → INSERT macro_theses → the two
agent auto-advance transitions → `mark_run_acted` → the human decision
transition), each governance transition emitting the load-bearing
INSERT-`governance_events`-then-UPDATE order the BEFORE-UPDATE triggers require.
The exact sequence was **rolled-back-tested against the live triggers first**
(sentinel `DISPOSITION-ROLLBACK-OK`), then committed.

| agent_run | ruling | result macro_thesis | governance_status | reason (verbatim) |
|---|---|---|---|---|
| #6 (breadth deterioration, no vol catalyst — `falling_growth_falling_inflation`) | **REJECT** | **#10** | `rejected` | "superseded by approved macro thesis #6, same evidence base" |
| #7 (un-inverted US curve + benign AU credit — `rising_growth_falling_inflation`) | **APPROVE** | **#11** | `approved` | growth-leg bracket (third quadrant); provenance disclosed: run 7 was manually authored during the 2026-07-21 pre-repoint workaround, mechanically re-verified; James ruling 2026-07-22 |

Post-state: `agent_runs` unacted = **0**; both rows `acted_on=TRUE` with
`resulting_object_id` 10/11. Each result row carries the full 3-step
`governance_events` trail (agent auto-advance ×2 → human decision). **These new
rows #10/#11 are distinct from the already-approved macro_theses #6/#7** (which
came from `agent_runs` #3/#4 and are the ones Layer B annotates) — the
shared-number collision the red-team flagged is kept clean.
`governed_active_macro_theses` now spans three regime quadrants (#6, #7, #11).

## 2. Proposal A Step 1 — theme governance write path, LIVE-FIRE verified

Finding (matches arbi + red-team): the `asx theme approve|reject|open
--from-agent-run` verbs and the shared `create_theme[_holding]_from_agent_run()`
service functions **already exist** (`asxos/cli/theme.py`,
`asxos/domain/themes/service.py`) — the proposal's "confirmed not built" premise
was stale. So Step 1 is *verification*, not a build.

Per the L7/L11 lesson (`.claude/rules/portfolio-conventions.md` §Verification
lesson — mocked tests + hand-replicated SQL both passed for the theses path yet
the real statement order was wrong), the whole theme write path was replayed as
its **emitted statement order** against the **real BEFORE-UPDATE governance
triggers** in a rolled-back transaction: create/approve/reject for both `themes`
and `theme_holdings`, all via INSERT-`governance_events`-then-UPDATE. Result:
sentinel `LIVEFIRE-ROLLBACK-OK` — every positive transition accepted — plus a
**negative control** confirming the trigger *rejects* a bare (no-event) UPDATE
(`OK-trigger-rejected-bare-update`). The path is trigger-safe.

A shared-ordered-log unit test (`tests/test_theme_from_agent_run.py::
test_create_theme_from_agent_run_emitted_order_is_trigger_safe`) now pins the
theme function's novel call pattern around the shared helper (INSERT-event
before UPDATE within each transition; INSERT-themes before both transitions;
`acted_on` last) so the property is guarded in CI, not only by the one-time
live check.

## 3. Proposal A Step 2 — sector-screener materialized

Checklist state (`docs/proposals/sector-screener-agent-spec-2026-07-12.md`):

- [x] agent DB role scoping applied + agents repointed to
      `mcp__supabase-ro__execute_sql` — Step 0 landed in #65.
- [x] shared `create_theme_from_agent_run()` / `create_theme_holding_from_agent_run()`
      — built (PR #50) and **live-fire verified this session** (§2).
- [x] stage-1 fixture / stage-2 synthetic / **stage-3 read-only production
      dry-run** — done 2026-07-16 (`docs/discovery-runs/2026-07-16-energy-dryrun.md`,
      Energy sector, output-only, zero writes).
- [x] `sector-screener` added to `_KNOWN_AGENTS` (`asxos/domain/governance/
      agent_run_service.py`) — the one code change that lets `/discover-sector`
      log its proposals (`ThemeProposal`/`ThemeHoldingProposal` were already in
      `_PROPOSAL_MODELS`).
- [x] `.claude/agents/sector-screener.md` + `.claude/commands/discover-sector.md`
      — **promoted from `docs/agents-staging/` via the sanctioned draft-PR/API
      route** (local writes to `.claude/` are permission-denied — an authority
      surface; go-live is James's merge, an attended/merge-time step per the
      staging header). Content is the staged copy verbatim (already repointed to
      the read-only MCP), staging header stripped.
- [ ] human review → approval → paper — James's gates, unchanged (the remaining
      three of the six stages are his, by design).

Next attended action once merged: `/discover-sector <sector>` against a
still-blind sector (Basic Materials / Consumer Defensive / Utilities /
Unclassified remain 0-covered) → `asx theme open --from-agent-run` → human
approve.
