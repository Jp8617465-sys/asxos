# arbi memory — the second brain (git-native)

**Status:** current
**Scope:** arbi's persistent memory, implemented in git
**Last verified:** 2026-09-10
**Owner:** arbi (`AGENTS.md` §10)
**Superseded by:** N/A

arbi has no trained weights and no managed memory store — its memory **is these git-tracked
files**. They are arbi's to write directly, on the branch, merged with the work that taught
the lesson (`AGENTS.md` §10). There is no candidate/approved split, no dream job and no
promotion gate: those existed to keep an untrusted writer away from a trusted file, and
`AGENTS.md` §2 now names the three things that are actually reserved.

---

## The map

| File | Content |
|---|---|
| `lessons.md` | What arbi learned, appended when learned. Ends with the authority-pointer section folded in from the retired `authority-lessons.md`. |
| `project-facts.md` | Facts that outlive a session — things arbi should know that are not rules a hook enforces. |
| `working/*.md` | Raw per-run notes. One append-only file per run, so parallel branches never conflict. |
| `playbooks/*.md` | Reusable procedures worth running the same way twice (e.g. the product reality sweep). |

The audited run history is not in this directory and is not duplicated here: it is
`../decision-log.md` (append-only, never delete a row), `../roadmap-state.md`,
`../risk-register.md`, `../arbi-run-ledger.md` and the dated `../../session-handoff-*.md`.

## The one rule that survives

**A wrong lesson is corrected in place, with a `decision-log.md` row saying what changed and
why.** Never silently rewrite memory — the row is what makes a correction auditable rather
than a memory that quietly drifted.

## Where memory sits in the ladder

`AGENTS.md` §10: James's current instruction → live state (git, CI, Supabase) →
`AGENTS.md` and `CLAUDE.md` → other repo docs → **arbi's memory** → the transcript.

Memory sits *below* repo truth. A lesson here that contradicts the live code, the migrations
or the newest handoff is stale: fix the lesson, not the repo. `arbi-red-team` challenge 4
exists to catch exactly that inversion.

Read `decision-log.md` **first** each wake — did the last ONE THING hold up? — then the
lessons. A call that didn't pan out is data; don't re-issue it unchanged.
