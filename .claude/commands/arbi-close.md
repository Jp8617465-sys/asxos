# arbi — stand down — `/arbi-close`

No arguments. The closing bookend to `/arbi`. Run it at the end of a working session so
what got built is captured, the living state stays fresh, and the next wake starts from
truth instead of a stale doc.

You are running the stand-down ritual for yourself. Where `/arbi` reads state and briefs,
`/arbi-close` records what changed this session, updates memory, and writes the handoff the
next session (or the next `/arbi`) will read. This closes the loop: **wake → work → stand
down → wake** — the loop through which understanding compounds instead of resetting each
session.

## Step 1 — Capture the end-state

Run `/sprint-state` for the session's final git/test/migration/task picture. Note what
landed this session: `git log --oneline $(git merge-base main HEAD)..HEAD`, migration
delta, any new/closed PRs, test-count move.

## Step 2 — Update memory (the learning step)

Append to `docs/product/decision-log.md`: today's date, the action named as THE ONE THING
at the last wake, what was actually done about it, and the outcome (done / partial /
deferred / superseded — and *did it work* if known). This is how the loop learns: next
wake, you read this log and check whether the last call held up before making the next one.
Never delete old rows — the log is the audit trail of the project's real trajectory.
A lesson worth carrying forward goes in `docs/product/memory/lessons.md`; a fact that
outlives the session goes in `project-facts.md` (`AGENTS.md` §10).

Then edit `docs/product/roadmap-state.md`:
- **Reconciled position** / **In flight** / **Blocked** — reconcile with what landed.
  Move completed items; unblock anything the session cleared; add anything newly blocked.
- **Ranked next-action queue** — re-rank given the new state.
- **Deferred index** — if the session added a `m14_candidate_*` slug, add its row
  (re-grep with `grep -rn m14_candidate_ .`).
- **Last wake snapshot** — refresh the fenced block with the Step 1 figures.

Surgical edits; don't rewrite what didn't change.

## Step 3 — Write the session handoff

Create or update `docs/session-handoff-YYYY-MM-DD.md` for today's date, following the
existing handoff format (see `docs/session-handoff-2026-07-04.md`): a `Status: current` /
`Read priority: read first` header, a "STOP — read first" block if a P0 is live (the Model
A quarantine stays here until lifted), a session summary of what shipped, and a "yours"
list of anything waiting on James under `AGENTS.md` §2. Keep the honest frame — do not let
feature velocity paper over an open foundation question.

## Step 4 — Commit and merge the handoff

Handoffs and the state doc **must be on `main`** to be seen next session (`docs/README.md`:
"a handoff that lives only on a feature branch is a process defect"). So land them: branch,
`make check`, open the PR ready with its class, wait for required checks on the current
head, and merge (`AGENTS.md` §8). A close that ends with an unmerged handoff has not
closed.

## Boundaries

- Records and hands off. No trades and no real-capital recommendation (personal-advice
  firewall, s766B) — that is `AGENTS.md` §2 and stays James's.
- **Model A quarantine (rule #11)** stays in the handoff's STOP block until a new model
  version passes the pre-registered decay bar and earns `approved_for_allocation`.
- Every claim in the handoff traces to a commit, a probe, or a cited doc line. An
  unsourced number is omitted, not guessed.
