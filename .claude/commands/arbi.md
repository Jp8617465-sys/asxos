# arbi — wake up — `/arbi`

No arguments. Say "wake up" (or run `/arbi`) and arbi tells you where asxos stands and
what to do next.

You are running the wake ritual for **arbi**, the product manager for asxos (single user,
James). arbi is the arbiter of what the software and finance agents build — it reconciles
the scattered roadmaps and the live state into one honest picture and names the single
highest-leverage next action. This is **brief-only**: you gather state, let arbi
synthesize, present the brief, refresh the living state doc, and then **stop**. You do not
start work until James says go.

## Why a slash command and not just the agent

A Claude Code subagent cannot spawn subagents or run shell/MCP probes to gather live
state. The **main loop** can. So this command does the gathering (git, tests, migrations,
Render, Supabase freshness) and the persistence (refreshing `roadmap-state.md`), then
hands the snapshot to the `arbi` subagent for the reconciliation and prioritisation that
is *its* job. Same split as `/pm-review` and `/discover-macro`.

## Step 1 — Capture live state

Run `/sprint-state` (git branch/ahead-of-main/open PRs/last commits/working tree; test
count via `pytest tests/ -q --tb=no 2>&1 | tail -1`; migration state incl.
`REQUIRED_MIGRATIONS` vs applied; open `TaskList`). Then add the `/catchup` freshness
probes: Render service health (`GET api.render.com/v1/services`, `$RENDER_API_KEY`, filter `asxos-%`, flag
suspended/non-live), and Supabase freshness (`MAX(prices.dt)`, `MAX(signals.as_of)`,
recent `job_runs` per cron). If a probe's backing service is unavailable this session,
record the gap — do not invent a value.

## Step 2 — Diff against the last wake

Read the **Last wake snapshot** block at the bottom of `docs/product/roadmap-state.md`.
Compute the delta vs Step 1: new/closed PRs, commit sha change, test count moves, newly
landed migrations, freshness shifts, newly suspended crons. If there is no prior snapshot,
this is the first wake — establish a baseline, no delta.

## Step 3 — Hand off to arbi

Dispatch the `arbi` subagent in one message. Give it, verbatim: the Step 1 snapshot and
the Step 2 delta, plus the **fixed read order** it must follow (its operating contract is
`docs/product/arbi-harness.md`):

1. `CLAUDE.md`
2. the newest `docs/session-handoff-*.md`
3. `docs/README.md`
4. `docs/product/north-star.md`
5. `docs/product/roadmap-state.md`
6. `docs/next-session-backlog.md`
7. `docs/executable-roadmap-2026-07-04.md`
8. open PR notes, if available

arbi returns the brief: STATUS / WHAT CHANGED / NEW BUGS / RISKS / THE PICTURE /
NEXT ACTIONS / DECISIONS NEEDED (James) / BLOCKERS / WHAT NOT TO DO / NEXT PROMPT. Present
it verbatim — do not rewrite its verdict.

## Step 4 — Refresh the living state

**Scheduled/unattended run (PR 7a)? Skip this entire step.** A scheduled read-only dry run
writes nothing — it emits the brief and stops (`arbi-permission-model.md` §Scheduled/unattended
runs). Do Step 4 only for an **interactive, James-invoked** `/arbi`, where James running the
command *is* the authorisation for the I2 write.

Update `docs/product/roadmap-state.md`:
- **Last wake snapshot** — overwrite the fenced block with the Step 1 figures + today's
  timestamp.
- **In flight** — reconcile with the live branch/PR/`TaskList` state.
- **Ranked next-action queue** — apply any re-ranking arbi produced.
Keep edits surgical; do not rewrite sections that didn't change. (This is the one write
this command makes — to a git-tracked doc, never to the database.)

## Step 5 — Stop (brief-only)

End by restating **THE ONE THING** (arbi's action #1) and offering to start it, e.g.
"Say the word and I'll kick off the Model A decay check." **Do not dispatch it, edit code,
or start work.** Wait for James's explicit go.

<!-- Future toggle (not built): an autonomous "dispatch mode" could auto-start action #1.
     James chose brief-only for v1. Keep this a deliberate, separate change. -->

## Boundaries

- Brief + state refresh only. No trades, no order placement, no real-capital
  recommendation — the personal-advice firewall (s766B) is structural.
- **Model A quarantine (rule #11):** never recommend acting on Model A output for real
  capital until the dispute resolves. Recommending we *resolve* it is the whole point.
- Every figure in the brief traces to a probe or a cited doc line — never training
  knowledge or a guess. If ≥2 live probes are unavailable, say the read is state-thin and
  name the gaps rather than forcing a confident picture.
