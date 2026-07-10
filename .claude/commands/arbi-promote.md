# arbi promote — candidate → approved memory — `/arbi-promote`

`$ARGUMENTS` = the dream-candidate file (e.g. `dream-candidates/2026-07-13-dream.md`) or the
PR number. Promotion is the single valve from candidate (ladder 7) to approved memory
(ladder 6): **a reviewed PR merge to `main`.** arbi prepares it; **only James merges**
(CODEOWNERS). See `arbi-promotion-gate.md`, `rubrics/arbi-dream-promotion.md`.

## Step 1 — Gate the candidate (grader ≠ producer)

The candidate must be graded in a **separate context** from the run that produced it. Apply
`rubrics/arbi-dream-promotion.md`:
- `completed: true` in the frontmatter (a partial/failed dream is **archived, never
  promoted** — stop here if absent).
- Each proposed lesson **improves at least one** of: state accuracy · repeated-mistake
  reduction · rubric pass rate · blocker prioritisation · handoff quality · scope control.
- It **regresses none** of: safety boundaries · the authority ladder · Model A quarantine ·
  the permission model · the financial-decision boundary.
- Safety items are carried **verbatim**, not summarised.
- For a boundary-adjacent lesson, a fresh-context `security-engineer` review.

## Step 2 — Prepare the promotion (on a branch)

If it passes: append the vetted lessons into `docs/product/memory/approved-lessons.md`
**with provenance** (dream_run_id + input SHAs), and `git mv` the candidate to
`dream-candidates/archive/` marked `promoted`. A lesson whose `proposed_target` is a
**boundary** (rule #11, a permission grant, the firewall) is **not** an ordinary promotion —
it routes to a governance-doc PR that only James may merge (ladder level 0).

## Step 3 — PR → James merges

Open the PR (CI `full-check` must be green; docs-only). **arbi does not merge** — CODEOWNERS
makes James the required reviewer; his merge = promotion to ladder 6. A rejected/partial
candidate is `git mv`'d to `archive/` marked `rejected`/`partial`, never folded in. A bad
promotion is reverted with `git revert`.

## Boundaries

- arbi never self-approves or merges (I6). Promotion is James's merge.
- Never fold a candidate lacking `completed: true`.
- Boundary changes go through James directly, not the ordinary promotion path.
