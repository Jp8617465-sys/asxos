# Working memory — 2026-07-14 PR transaction discipline (the #29 auto-close incident)

**Status:** working memory (candidate lessons — not yet promoted)
**Scope:** branch/PR transaction discipline during rebases, force-pushes, and branch reconstruction
**Source run:** merge-2026-07-14 (`arbi-run-ledger.md`); incident reported to James same-turn
**Promotion path:** `/arbi-dream` → `/arbi-promote` (never self-approved)

---

## The incident (verified, not smoothed over)

During the red-team-passed #29 rebase (2026-07-14), a commit+push recovery ran as two
*independent* statements instead of a `&&` chain. The commit failed (its message file had
never been written — the earlier compound that would have written it was denied by the
just-hardened R13 review gate), but the push **executed anyway**, force-pushing the PR
branch at bare `main`. Head momentarily equalled base and **GitHub auto-closed PR #29**.
Recovery: staging was still intact locally; recommitted, force-pushed the real content,
reopened #29, reported the incident to James in the same turn. Nothing lost.

James's verdict: net-positive run; the lesson is not "stop autonomy" but "autonomy needs
stronger branch/PR transaction discipline."

## Candidate lesson L-cand-4 — PR transaction discipline (governor-issued, 2026-07-14)

When recovering, rebasing, or reconstructing any branch that backs a PR:

1. **Chain commit + push + PR-state verification as ONE transaction** — `git commit … && git push … `
   then immediately read the PR's state/head. Never let a push run after a failed commit
   (independent statements are how a bare-base push happens).
2. **Avoid force-pushing a reviewed branch** unless the mission explicitly requires branch
   reconstruction (a rebase ordered by James qualifies; convenience does not).
3. **After any force-push/rebase/branch reconstruction, immediately verify PR state** — head
   sha, base sha, open/closed, diff file count. Do not proceed on assumption.
4. **If GitHub auto-closes a PR because head==base, reopen it and report the incident** — the
   close is mechanical, not a judgement; the reopen must be immediate and the report explicit.
5. **Never smooth over the incident.** Log it in the ledger/decision-log and the session report
   even when fully recovered. (Done for this one: `arbi-run-ledger.md` merge-2026-07-14.)
6. **Prefer fresh branches for unrelated work** — reconstruction risk concentrates on branches
   that accumulate mixed history.

## Candidate lesson L-cand-5 — process slips gate continuation on verified-safe state

Governor addition (2026-07-14): *"If the run discovers a process slip, log it honestly and
continue only if the repo state is verified safe."* Operationally: on any slip, stop new work,
verify the affected refs/PRs/files against expectation (live reads, not memory), log the slip,
then continue. Honest logging is what keeps autonomy expandable; a smoothed-over slip is worth
more lost trust than the slip itself.

## Standing-prompt placement (James's instruction)

Both lessons are to be encoded verbatim into the long-window autonomy prompt (the 12-hour
`/goal` recipe) as a "PR transaction discipline" block — see `docs/product/arbi-goal-recipes.md`
(autonomy unlock pack). They apply to every builder/teammate that touches a branch, not only
the main loop.
