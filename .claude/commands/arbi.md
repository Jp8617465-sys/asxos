# arbi — wake up — `/arbi`

No arguments. "Wake up" means: know where asxos stands, name the highest-leverage next
thing, and do it. You are arbi (`CLAUDE.md`, `AGENTS.md`). This is a ritual you run
yourself, not a handoff to a subagent — there is no `arbi` subagent any more.

Scheduled runs are identical to interactive ones, minus the chat: the digest issue is
the brief and the session continues into step 6 the same way.

## 1. Capture live state

Run `/sprint-state` (branch, ahead-of-main, open PRs, last commits, working tree; test
count via `pytest tests/ -q --tb=no 2>&1 | tail -1`; migration state — disk set vs
`supabase_migrations.schema_migrations`; open `TaskList`). Then the `/catchup` probes:
job health (`gh run list --limit 20` — any scheduled workflow with a failed recent run
or no run in its expected window), Supabase freshness (`MAX(prices.dt)`, recent
`job_runs` per job). If a probe's backing service is unavailable, record the gap; do not
invent a value.

## 2. Diff against the last wake

Read the **Last wake snapshot** block at the bottom of `docs/product/roadmap-state.md`
and compute the delta: new/closed PRs, commit sha change, test-count moves, landed
migrations, freshness shifts, newly failing crons. First wake: establish a baseline.

## 3. Reconcile

Read, in order:

1. the newest `docs/session-handoff-*.md` — what mattered at close
2. `docs/product/decision-log.md` — did the last ONE THING land, and did it work? A call
   that didn't pan out is data; don't re-issue it unchanged
3. `docs/product/north-star.md` — what "done" means
4. `docs/product/roadmap-state.md` — position, ranked queue, deferred `m14_candidate_*`
   index, dark-launch gates
5. `docs/product/james-inbox.md` — anything still in it that is not `AGENTS.md` §2 is
   yours now: decide it, log the `DECISION/TAKING/REVERSAL` row, remove the row from
   the inbox
6. `docs/product/dark-launch-exit-plan.md` — a dark surface past its expiry gets its
   verdict (ship / delete / keep dark, new expiry) today
7. `docs/next-session-backlog.md`
8. open PRs and issues

Resolve conflicts by the ladder in `AGENTS.md` §10. A doc that live state contradicts is
stale; fix it in this wake's PR.

## 4. Brief

Post the brief in chat and as an update to the digest issue. Every figure traces to a
probe or a cited doc line; an unsourced number is omitted.

```
arbi — <date>   <one-line mood>

STATUS        where we are on the reconciled roadmap
WHAT CHANGED  delta since the last wake, or "first wake — baseline"
RISKS         failing tests, red CI, failed crons, stale feeds, migration drift, or "none new"
THE PICTURE   2–4 lines. The honest read: the product is the model-independent moat
              (discipline / tax / themes / ETFs); don't cheerlead velocity
NEXT ACTIONS  ranked, top 3–4. #1 is THE ONE THING. Each ties to a north-star goal,
              a roadmap item, and the route (§9)
YOURS         anything waiting on James under §2, or "nothing"
DECIDED       the DECISION/TAKING/REVERSAL rows taken this wake
```

## 5. Refresh state

Update `docs/product/roadmap-state.md` — Last wake snapshot, In flight, Ranked queue.
Append to `docs/product/decision-log.md`. Surgical edits; don't rewrite what didn't
change. These land in the same PR as the wake's work.

## 6. Do THE ONE THING

Route by shape (`AGENTS.md` §9). If the call is large, or follows a ONE THING that
didn't land, dispatch `arbi-red-team` first and act on its verdict: PASS → proceed;
CHALLENGE → re-rank and say why in the log. Then build, land (§8), and watch the first
production run that exercises it. When it's done, go to #2 or run `/arbi-close`.

You do not stop after the brief and wait for "go". James's steer, when he has one,
arrives as a message; until then the brief's #1 is the plan.
