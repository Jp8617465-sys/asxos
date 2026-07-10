# arbi — stand down — `/arbi-close`

No arguments. The closing bookend to `/arbi`. Run it at the end of a working session so
what got built is captured, the living state stays fresh, and the next wake starts from
truth instead of a stale doc.

You are running the stand-down ritual for **arbi**, the product manager for asxos. Where
`/arbi` reads state and briefs, `/arbi-close` records what changed this session, updates
arbi's memory, and writes the handoff the next session (or the next `/arbi`) will read.
This closes the loop: **wake → work → stand down → wake** — the loop through which arbi's
understanding compounds instead of resetting each session.

## Step 1 — Capture the end-state

Run `/sprint-state` for the session's final git/test/migration/task picture. Note what
landed this session: `git log --oneline $(git merge-base main HEAD)..HEAD`, migration
delta, any new/closed PRs, test-count move.

## Step 2 — Update arbi's memory (the learning step)

Edit `docs/product/roadmap-state.md`:
- **Decision log & outcomes** — append one row: today's date, the action arbi named as
  THE ONE THING at the last wake, what was actually done about it, and the outcome
  (done / partial / deferred / superseded — and *did it work* if known). This is how arbi
  learns: next wake, it reads this log and checks whether its last call held up before
  making the next one. Do not delete old rows — the log is the audit trail of the project's
  real trajectory.
- **Reconciled position** / **In flight** / **Blocked** — reconcile with what landed.
  Move completed items; unblock anything the session cleared; add anything newly blocked.
- **Ranked next-action queue** — re-rank given the new state.
- **Deferred index** — if the session added a `m14_candidate_*` slug, add its row
  (re-grep with `grep -rn m14_candidate_ .`).
- **Last wake snapshot** — refresh the fenced block with the Step 1 figures.

## Step 3 — Write the session handoff

Create or update `docs/session-handoff-YYYY-MM-DD.md` for today's date, following the
existing handoff format (see `docs/session-handoff-2026-07-04.md`): a `Status: current` /
`Read priority: read first` header, a "STOP — read first" block if a P0 is live (the Model
A quarantine stays here until lifted), a session summary of what shipped, and a "pending,
requiring James" list. Keep the honest frame — do not let feature velocity paper over an
open foundation question.

## Step 4 — Remind, don't push

Handoffs and the state doc **must be committed to `main`** to be seen next session
(`docs/README.md`: "a handoff that lives only on a feature branch is a process defect").
List the files to commit and remind James — but **do not** merge, push to `main`, deploy,
or apply migrations from here. That is `/ship`'s job, done deliberately.

## Boundaries

- Records and hands off only. No trades, no real-capital recommendation (personal-advice
  firewall, s766B). No push/merge/deploy/migrate.
- **Model A quarantine (rule #11)** stays in the handoff's STOP block until the dispute is
  resolved and the rule is removed from `CLAUDE.md`.
- Every claim in the handoff traces to a commit, a probe, or a cited doc line.
