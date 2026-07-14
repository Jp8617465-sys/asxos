# arbi goal recipes — long-window autonomy prompts

**Status:** current (autonomy unlock pack, 2026-07-14)
**Scope:** the vetted prompt recipes for long reversible-work windows (`/goal`, overnight/12-hour runs)
**Last verified:** 2026-07-14
**Owner:** James launches; arbi/Guilfoyle execute; changes to a recipe's *boundaries* are boundary changes (James approves)
**Superseded by:** N/A

A recipe is a **pre-vetted envelope**, not a suggestion: the boundaries in it are binding for
the whole window. Recipes grew from real runs (the 2026-07-11 8-hour window; the 2026-07-13
overnight window; the 2026-07-14 merge train + incident) — per the deferred `goal-recipes`
item in PR #31, they are encoded now that there are real missions to generalise from.

---

## Recipe R1 — the 12-hour high-output reversible window

Launch (after the prerequisites in `runbooks/reversible-work-window.md`):

```
/goal For the next 12 hours, run an asxos high-output reversible development window.

Use arbi to choose THE ONE THING.
Run arbi-red-team.
Then hand execution to Guilfoyle.

Guilfoyle may use:
- reversible-work-window skill
- arbi-mission skill
- agent teams only when the mission benefits from parallel work (agent-team-mission skill)
- max 4 teammates
- plan approval required before teammate implementation
- separate file ownership per teammate
- draft PRs only

Substantive target:
- 3–5 meaningful product/code/live-ops PRs
- final run record PR does not count
- at least 70% product/code/live-ops
- max one meta/autonomy PR unless it directly unlocks work

Hard floor:
- no merge/deploy/main push
- no raw DB write/migration
- no raw Render mutation
- no secrets
- no capital/broker execution
- no authority-file change as active truth
- no branch-only artifact once ready

PR transaction discipline:
- After any rebase, force-push, or branch reconstruction, immediately verify PR state.
- If a PR auto-closes because head briefly equals base, reopen it and report the incident.
- Do not force-push a reviewed branch unless the mission explicitly requires branch reconstruction.
- Prefer fresh branches for unrelated work.
- Chain commit + push + PR-state verification as one transaction when recovering a branch.

If the run discovers a process slip, log it honestly and continue only if the repo state is
verified safe.

If James boundary is hit:
- log JAMES_NEEDED
- preserve artifact
- pivot to next independent reversible task

Morning report:
- decisions needed
- completed PRs
- skipped/deferred
- risks found
- recommended merge order
```

**Provenance of the discipline block:** governor-issued 2026-07-14 after the recovered #29
auto-close incident — L-cand-4 and L-cand-5 in
`memory/working/2026-07-14-pr-transaction-discipline.md`, quoted here **by governor
instruction** (the lessons are still working-memory candidates pending `/arbi-dream` →
`/arbi-promote`; a recipe may quote a governor instruction directly, it may not promote a
lesson). The block binds **every builder/teammate that touches a branch**, not only the main
loop.

## Recipe R2 — the bounded 8-hour overnight window (the 2026-07-13 shape)

The proven smaller sibling: same hard floor and discipline block as R1, with — max 3 draft
PRs · self-paced hourly cadence with a hard stand-down time · THE ONE THING chosen by arbi +
red-team-gated before build · JAMES_NEEDED pivot rule · stop early at the PR ceiling. Use
when the queue has one clear lane rather than a broad target.

## Recipe rules (all recipes)

1. **arbi decides, red-team challenges, Guilfoyle orchestrates, builders mutate** — the roles
   never blur mid-window (`guilfoyle-mission-control.md`).
2. Reversible I0–I4 only; **the draft PR is the durable stopping point** (L-cand-3). Never
   merge/ready-for-review inside a window without explicit James instruction.
3. On any slip: stop, verify-safe with live reads, log, then continue (L-cand-5).
4. The window ends with a ledger row (`arbi-run-ledger.md`) and the morning report — the
   report is part of the window, not optional.
5. Recipes are launched by James (attended grant for the window). A *scheduled* unattended
   window remains gated on the PR 7b preconditions (`arbi-permission-model.md`) — no recipe
   overrides that.
